"""Offline, synthetic tests for the study-expiry controller (no network)."""
import csv
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import research_autopilot as ap


def z(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


class AutoDecisionTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        original = Path.cwd()
        os.chdir(self.dir.name)
        self.addCleanup(os.chdir, original)

    def write_manifest(self, end="2026-12-14T06:24:26+00:00"):
        path = Path("research_30d/manifest.json")
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps({
            "experiment_id": "evidence-20261114T062426Z",
            "start_utc": "2026-11-14T06:24:26+00:00",
            "end_utc": end,
            "production_policy": "ADVISORY_ONLY",
            "candidate_policy": "NO_AUTOMATIC_PROMOTION",
        }), encoding="utf-8")

    def test_not_before_deadline(self):
        self.write_manifest()
        self.assertEqual(ap.generate(z("2026-11-22T20:00:00Z"), "decisions"), [])
        self.assertFalse(list(Path("decisions").glob("*.json")))

    def test_phase_transition_and_idempotency(self):
        self.write_manifest()
        created = ap.generate(z("2026-11-24T00:01:00Z"), "decisions")
        self.assertEqual(len(created), 1)
        self.assertEqual(json.loads(created[0].read_text())["assessment"]["decision"],
                         "WINDOW_CLOSED_AWAITING_LABELS")
        self.assertEqual(ap.generate(z("2026-11-24T01:00:00Z"), "decisions"), [])
        # Never invent a final verdict when an entire source ledger is missing.
        blocked = ap.generate(z("2026-11-29T00:00:00Z"), "decisions")
        self.assertEqual(len(blocked), 1)
        self.assertEqual(json.loads(blocked[0].read_text())["assessment"]["decision"], "DATA_UNAVAILABLE")
        self.assertFalse(Path("decisions/tier1_v2_forward-final.json").exists())
        self.assertEqual(ap.generate(z("2026-11-29T03:00:00Z"), "decisions"), [])

    def test_missing_research_manifest_is_reported_once(self):
        first = ap.generate(z("2026-11-22T00:00:00Z"), "decisions")
        self.assertEqual(len(first), 1)
        self.assertEqual(json.loads(first[0].read_text())["assessment"]["decision"], "DATA_UNAVAILABLE")
        self.assertEqual(ap.generate(z("2026-11-22T01:00:00Z"), "decisions"), [])

    def test_v2_uses_only_version_locked_future_graded_rows(self):
        self.write_manifest()
        t0 = z("2026-10-24T00:00:00Z")
        rows = []
        for i in range(112):
            ts = (t0 + timedelta(hours=4*i)).isoformat()
            rows.append({"ts": ts, "asset": "SPX", "logic": ap.LOGIC_V2,
                         "graded_4h": "1", "lean4h": "-1", "ret_4h": "-0.005"})
            # An attractive but INVALID old logic must be ignored.
            rows.append({"ts": ts, "asset": "XAU", "logic": "old",
                         "graded_4h": "1", "lean4h": "1", "ret_4h": "0.005"})
        with open("forecast_ledger.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=rows[0])
            w.writeheader()
            w.writerows(rows)
        generated = ap.generate(z("2026-11-29T00:00:00Z"), "decisions")
        report = json.loads(Path("decisions/tier1_v2_forward-final.json").read_text())
        self.assertEqual(report["assessment"]["per_asset"]["SPX"]["independent_4h_n"], 112)
        self.assertEqual(report["assessment"]["per_asset"]["XAU"]["independent_4h_n"], 0)
        self.assertEqual(report["assessment"]["decision"], "REPLICATE_PROSPECTIVELY")
        self.assertFalse(report["live_orders"])
        self.assertFalse(report["production_logic_modified"])
        self.assertEqual(ap.generate(z("2026-12-01T00:00:00Z"), "decisions"), [])
        self.assertEqual(len(generated), 2)  # window-closed plus final, first run past both

    def test_research_is_never_promoted_from_few_samples(self):
        self.write_manifest()
        path = Path("research_30d/observations.csv")
        rows = []
        t0 = z("2026-11-15T00:00:00Z")
        for k in range(12):
            rows.append({"ts": (t0 + timedelta(hours=4*k)).isoformat(),
                         "experiment_id": "evidence-20261114T062426Z",
                         "asset": "BTC", "market": "spot", "reference_price": str(100+k),
                         "status": "OK_SAMPLE", "imbalance": "0.5"})
        path.parent.mkdir(exist_ok=True)
        with path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=rows[0])
            w.writeheader()
            w.writerows(rows)
        ap.generate(z("2026-12-17T00:00:00Z"), "decisions")
        decision = json.loads(Path("decisions/research30_crypto_flow-final.json").read_text())
        self.assertEqual(decision["assessment"]["decision"], "DATA_INSUFFICIENT")
        self.assertEqual(decision["assessment"]["per_asset"]["BTC"]["status"], "INSUFFICIENT")
        self.assertFalse(decision["live_orders"])

    def test_significance_direction(self):
        self.assertEqual(ap.exact_mcnemar_one_sided(4, 0), 0.0625)
        self.assertEqual(ap.exact_mcnemar_one_sided(0, 4), 1.0)
        self.assertEqual(ap.exact_mcnemar_one_sided(0, 0), 1.0)


if __name__ == "__main__":
    unittest.main()
