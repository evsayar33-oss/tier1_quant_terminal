"""Tier-1 contract checks: H120 result is analysis only and never a signal."""
from __future__ import annotations
import copy
import json
import unittest
from datetime import datetime, timezone

import superlab_feedback as f

NOW = datetime(2026, 11, 19, 17, tzinfo=timezone.utc)
SHA = "f" * 40
NEW = "a" * 40


def report():
    def grade(n):
        return {
            "official_lab_gate": "NOT_RUN",
            "grade": "NOT_ENOUGH_INDEPENDENT_EVIDENCE",
            "observations": n,
            "model_hit": 1.0,
            "always_long_hit": 0.0,
            "bonferroni_12_p": .75,
        }
    return {
        "schema": "QS.h120.tier1_intelligence.v1",
        "source": f.SOURCE,
        "state_branch": f.BRANCH,
        "production_logic": "UNCHANGED",
        "research_only": True,
        "official_gate": "NOT_RUN",
        "asof_utc": "2026-11-19T15:08:28+00:00",
        "tier1_audit_utc": "2026-11-19T11:49:35+00:00",
        "source_commits": {f.SOURCE_AUDIT: SHA},
        "entry_allowed": 0,
        "replication_leads_not_accepts": 0,
        "grades": {"4": grade(4), "24": grade(7)},
    }


def network(data=None, current=SHA, compare_status="ahead"):
    observed = []
    def fetch(url):
        observed.append(url)
        if "/git/ref/heads/" in url:
            return json.dumps({"object": {"sha": (
                SHA if f.SUPERLAB in url else current)}})
        if "/compare/" in url:
            return json.dumps({"status": compare_status, "behind_by": 0})
        if url.endswith("/tier1_h120/latest.json"):
            return json.dumps(data or report())
        raise AssertionError("Unknown remote fetch")
    return fetch, observed


class TestReadOnlySuperlabFeedback(unittest.TestCase):
    def test_production_and_alpha_are_not_promoted(self):
        fn, urls = network()
        view = f.run(fn, NOW)
        self.assertEqual(view["source_status"], "CURRENT")
        self.assertFalse(view["terminal_production_changed"])
        self.assertEqual(view["side_effects"], "NO_STATE_OR_MODEL_WRITES")
        self.assertEqual(view["research_candidates_not_accepts"], 0)
        self.assertEqual(view["grades"]["4"]["observations"], 4)
        self.assertIn("NOT_RUN", f.markdown(view))
        self.assertTrue(all(f.SUPERLAB in u or f.SOURCE in u for u in urls))
        self.assertTrue(all("early_accumulation" not in u for u in urls))

    def test_source_advanced_is_pending_refresh_not_fake_alpha(self):
        fn, _ = network(current=NEW)
        v = f.run(fn, NOW)
        self.assertFalse(v["source_is_current"])
        self.assertEqual(v["source_status"], "UPSTREAM_AUDIT_HAS_NEWER_DATA")

    def test_rejects_source_history_rewrite(self):
        fn, _ = network(current=NEW, compare_status="diverged")
        with self.assertRaisesRegex(ValueError, "HISTORY_DIVERGED"):
            f.run(fn, NOW)

    def test_rejects_future_and_unsigned_studies(self):
        a = report()
        a["asof_utc"] = "2028-11-19T15:08:28+00:00"
        fn, _ = network(a)
        with self.assertRaisesRegex(ValueError, "FUTURE_SOURCE_TIME"):
            f.run(fn, NOW)
        a = report()
        a["official_gate"] = "ACCEPT"
        fn, _ = network(a)
        with self.assertRaisesRegex(ValueError, "UNTRUSTED_H120_FEEDBACK"):
            f.run(fn, NOW)

    def test_rejects_fake_win_rate_success_without_qs_verdict(self):
        a = report()
        a["grades"]["4"]["bonferroni_12_p"] = -1
        fn, _ = network(a)
        with self.assertRaisesRegex(ValueError, "INVALID_RESEARCH_METRIC"):
            f.run(fn, NOW)
        a = report()
        a["grades"]["4"]["grade"] = "ACCEPT"
        fn, _ = network(a)
        with self.assertRaisesRegex(ValueError, "UNTRUSTED_MODEL_GRADE"):
            f.run(fn, NOW)


if __name__ == "__main__":
    unittest.main()
