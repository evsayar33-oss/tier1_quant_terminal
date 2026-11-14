"""Offline regression tests. Run: python -m unittest discover -s tests -p 'test_research30*.py' -v"""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
import pandas as pd
import research_30d as r
import trade_plan


class Research30Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name) / "research_30d"
        self.patchers = [
            patch.object(r, "ROOT", root),
            patch.object(r, "MANIFEST", root / "manifest.json"),
            patch.object(r, "LEDGER", root / "observations.csv"),
            patch.object(r, "REPORT", root / "report.md"),
        ]
        for p in self.patchers:
            p.start()
            self.addCleanup(p.stop)

    def test_start_idempotent_and_deadline(self):
        now = datetime(2026, 11, 13, tzinfo=timezone.utc)
        a = r.start(now)
        b = r.start(now + timedelta(days=2))
        self.assertEqual(a, b)
        self.assertEqual(a["end_utc"], "2026-12-13T00:00:00+00:00")
        self.assertEqual(a["production_policy"], "ADVISORY_ONLY")

    def test_signed_taker_flow_and_dedup(self):
        raw = [
            {"execId": "a", "time": "1000", "price": "100", "size": "2", "side": "Buy"},
            {"execId": "b", "time": "2000", "price": "100", "size": "1", "side": "Sell"},
            {"execId": "a", "time": "1000", "price": "100", "size": "2", "side": "Buy"},
        ]
        s = r.parse_recent_trades(raw, now_ms=3000)
        self.assertEqual(s["trade_count"], 2)
        self.assertEqual(s["signed_usdt"], 100)
        self.assertAlmostEqual(s["imbalance"], 1 / 3, places=6)
        self.assertEqual(s["status"], "INSUFFICIENT_SAMPLE")

    def test_errors_are_recorded_not_fabricated(self):
        now = datetime(2026, 11, 13, 13, tzinfo=timezone.utc)
        r.start(now)
        with patch.object(r, "fetch_market_sample", side_effect=RuntimeError("both venues blocked")):
            summary = r.collect({"asset_verdicts": {}}, now=now)
        self.assertEqual(summary["errors"], 4)
        self.assertEqual(len(r.read_rows()), 4)
        self.assertTrue(all(x["status"] == "ERROR" for x in r.read_rows()))
        with patch.object(r, "fetch_market_sample", side_effect=RuntimeError("still blocked")) as fetch:
            repeat = r.collect(now=now)
        self.assertEqual(repeat["new_snapshots"], 0)
        self.assertEqual(repeat["retried_snapshots"], 4)
        self.assertEqual(len(r.read_rows()), 4)
        self.assertTrue(all(x["retry_count"] == "1" for x in r.read_rows()))
        self.assertEqual(fetch.call_count, 4)

    def test_expiration_stops_collection(self):
        now = datetime(2026, 11, 13, tzinfo=timezone.utc)
        r.start(now)
        result = r.collect(now=now + timedelta(days=30))
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(r.read_rows(), [])

    def test_legacy_trade_outcome_dtype(self):
        csv_path = Path(self.temp.name) / "trade.csv"
        csv_path.write_text(
            "ts,asset,side,entry,stop,target,confidence,source,pulse,outcome,r_mult,exit_ts,graded,logic\n"
            "2026-11-10T00:00:00+00:00,BTC,1,100,90,120,orta,test,1.2,,, ,0,v2\n"
        )
        d = trade_plan._load(str(csv_path))
        bars = pd.DataFrame(
            [{"High": 105, "Low": 99, "Close": 103}],
            index=pd.to_datetime(["2026-11-10T01:00:00+00:00"]),
        )
        trade_plan.grade(d, {"BTC": bars},
                         pd.Timestamp("2026-11-11T01:00:00+00:00"))
        self.assertEqual(d.iloc[0]["outcome"], "süre doldu")
        self.assertEqual(float(d.iloc[0]["r_mult"]), 0.3)


if __name__ == "__main__":
    unittest.main()
