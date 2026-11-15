"""Offline tests for Tier-1 sentiment collector and quant_superlab handoff.

No live API calls or historical result tables. Optional integration test uses
the actual pinned checkout provided by CI through QUANT_SUPERLAB_DIR.
"""
from __future__ import annotations
import csv
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

import sentiment_30d as observer
import sentiment_superlab_research as bridge


class FakeResponse:
    def __init__(self, timestamp):
        self.timestamp = timestamp

    def raise_for_status(self):
        pass

    def json(self):
        return {"data": [{"timestamp": str(int(self.timestamp.timestamp())),
                          "value": "19"}]}


class FakeAPI:
    def __init__(self, now):
        self.now = now
        self.count = 0

    def get(self, url, params=None, timeout=None):
        self.count += 1
        return FakeResponse(self.now - timedelta(hours=3))


class ResearchBridgeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.old = Path.cwd()
        os.chdir(tmp.name)
        self.addCleanup(os.chdir, self.old)

    def now(self):
        return datetime(2026, 11, 18, 15, 36, tzinfo=timezone.utc)

    def frame(self, now, price=100):
        ix = pd.date_range(end=pd.Timestamp(now-timedelta(hours=1, minutes=35)),
                           periods=60, freq="h", tz="UTC")
        return pd.DataFrame({"Close": np.linspace(price*.9, price, 60)}, index=ix)

    def test_new_manifest_and_real_first_seen(self):
        now = self.now()
        frames = {asset: self.frame(now) for asset in observer.ASSETS}
        grid = {symbol: self.frame(now, 20) for symbol in observer.IV_MAP.values()}
        api = FakeAPI(now)
        payload = {
            "asset_verdicts": {
                "SPX": {
                    "details": [{"faktor_id": "market_breadth", "ham_deger": -0.2}],
                    "market_structure": {"levels": {"levels": [
                        {"kind": "PDH", "price": 103.0}]}},
                    "raw_model_score": 0.4,
                },
            },
            "active_regime_id": "R1",
            "dealer_gamma": {"snapshots": {"SPX": {
                "as_of": now.isoformat(), "gamma_flip": 102.0,
                "net_gex_usd_1pct": -20000000,
            }}},
        }
        a = observer.collect(payload, frames, grid, now=now, session=api)
        self.assertEqual(a["added"], 6)
        self.assertEqual(a["fresh_prices"], 6)
        self.assertEqual(api.count, 1)
        m = json.loads(observer.MANIFEST.read_text())
        self.assertEqual(datetime.fromisoformat(m["end_utc"]) - now, timedelta(days=30))
        rows = observer.load_rows_for_test() if hasattr(observer, "load_rows_for_test") else list(
            csv.DictReader(observer.ROWS.open(newline="", encoding="utf-8")))
        self.assertEqual(len(rows), 6)
        self.assertEqual(set(r["asset"] for r in rows), set(observer.ASSETS))
        self.assertEqual(rows[0]["observed_utc"], observer.timestamp(now))
        self.assertEqual(rows[0]["sentiment_source"], "NONE_NOT_REAL_FNG")
        spx = [r for r in rows if r["asset"] == "SPX"][0]
        self.assertEqual(json.loads(spx["factor_values_json"])["market_breadth"], -0.2)
        self.assertEqual(json.loads(spx["gamma_values_json"])["gamma_flip"], 102.0)
        self.assertEqual(json.loads(spx["market_levels_json"])[0]["kind"], "PDH")
        self.assertEqual(json.loads(spx["aux_diagnostics_json"])["raw_model_score"], 0.4)
        eth = [r for r in rows if r["asset"] == "ETH"][0]
        self.assertEqual(eth["sentiment_source"], "ALTME_BTC_CONTEXT")
        self.assertEqual(eth["sentiment_value"], "19.0")
        self.assertEqual(observer.collect({}, frames, grid, now=now, session=api)["added"], 0)
        self.assertEqual(api.count, 1)  # cached within same day
        self.assertEqual(json.loads(observer.MANIFEST.read_text()), m)

    def test_unclosed_bar_does_not_get_used(self):
        now = self.now()
        frame = pd.DataFrame({"Close": [100.0]}, index=[pd.Timestamp(now-timedelta(minutes=10))])
        result = observer.close_snapshot(frame, now)
        self.assertIsNone(result["price"])
        self.assertEqual(result["status"], "UNCONFIRMED_OR_STALE_BAR")

    def test_post_window_only_records_labels(self):
        now = self.now()
        m = observer.initialize(now)
        after = datetime.fromisoformat(m["end_utc"]) + timedelta(hours=3)
        frames = {asset: self.frame(after) for asset in observer.ASSETS}
        result = observer.collect({}, frames, {}, now=after)
        self.assertEqual(result["status"], "LABEL_GRACE")
        rows = list(csv.DictReader(observer.ROWS.open()))
        self.assertTrue(all(r["data_status"] == "LABEL_ONLY" for r in rows))
        self.assertTrue(all(r["sentiment_value"] == "" for r in rows))
        finished = observer.collect({}, frames, {}, now=after+timedelta(hours=48))
        self.assertEqual(finished["status"], "COMPLETE")

    def test_earliest_daily_signal_and_future_label_only(self):
        start = datetime(2026, 11, 14, tzinfo=timezone.utc)
        manifest = {"start_utc": start.isoformat(),
                    "end_utc": (start + timedelta(days=30)).isoformat()}
        t0 = start + timedelta(days=3, hours=10)
        def record(t, px, fg, status="OBSERVED"):
            return {"asset":"BTC","observed_utc": t.isoformat(),
                    "experiment_id":"x", "data_status":status,
                    "price":str(px), "price_status":"OK",
                    "price_bar_utc":(t-timedelta(hours=2)).isoformat(),
                    "sentiment_status":"OK", "sentiment_value": str(fg),
                    "sentiment_first_seen_utc": (t-timedelta(minutes=1)).isoformat(),
                    "sentiment_published_utc": (t-timedelta(hours=6)).isoformat()}
        rows = [
            record(t0, 100, 15),
            record(t0+timedelta(hours=1), 100, 85), # same day cannot be chosen
            record(t0+timedelta(hours=23), 200, 50), # NOT future outcome
            record(t0+timedelta(hours=24, minutes=5), 110, 50),
        ]
        labels = bridge.sample_days(manifest, rows, "BTC")
        self.assertEqual(len(labels), 1)
        self.assertEqual(labels[0]["feature"], 15)
        self.assertAlmostEqual(labels[0]["forward_24h"], 0.10)
        self.assertEqual(bridge.direction("reversal_25_75", 15), 1)
        self.assertEqual(bridge.direction("momentum_25_75", 15), -1)

    def test_no_data_and_mismatched_experiments_block(self):
        with self.assertRaises(ValueError):
            bridge.load_source("sentiment_30d")
        manifest = observer.initialize(self.now())
        observer.ROWS.write_text("experiment_id,observed_utc,asset\nwrong,2026-11-18T00:00:00+00:00,BTC\n")
        with self.assertRaisesRegex(ValueError, "Cross-experiment"):
            bridge.load_source("sentiment_30d")

    @unittest.skipUnless(os.environ.get("QUANT_SUPERLAB_DIR"), "CI supplies real quant_superlab checkout")
    def test_real_superlab_statistical_import_and_fail_closed_30d(self):
        now = self.now()
        manifest = observer.initialize(now)
        rows = []
        for d in range(29):
            t = now + timedelta(days=d, hours=1)
            for asset in observer.ASSETS:
                price = 100 + d
                rows.append({
                    "experiment_id": manifest["experiment_id"],
                    "observed_utc": t.isoformat(), "asset":asset,
                    "data_status": "OBSERVED", "price_status":"OK",
                    "price":str(price), "price_bar_utc":(t-timedelta(hours=2)).isoformat(),
                    "sentiment_value":"20","sentiment_status":"OK",
                    "sentiment_first_seen_utc":t.isoformat(),
                    "sentiment_published_utc":t.isoformat(),
                    "iv_percentile":"20", "iv_status":"OK",
                    "iv_bar_utc":t.isoformat(),
                })
                t2 = t + timedelta(hours=24, minutes=30)
                rows.append({
                    "experiment_id":manifest["experiment_id"],
                    "observed_utc":t2.isoformat(),"asset":asset,
                    "data_status":"LABEL_ONLY","price_status":"OK",
                    "price":str(price*1.01),
                    "price_bar_utc":(t2-timedelta(hours=2)).isoformat(),
                })
        # Assembled synthetic test rows may share calendar days but never duplicate
        # (hour,asset) on a real ledger. Directly exercise the research function.
        r = bridge.discovery(manifest, rows, {"synthetic_test": True},
            os.environ["QUANT_SUPERLAB_DIR"],
            datetime.fromisoformat(manifest["end_utc"]) + timedelta(hours=50))
        self.assertEqual(r["decision"], "NEED_MORE_INDEPENDENT_PROSPECTIVE_DATA")
        self.assertFalse(r["automatic_trade_approval"])
        self.assertFalse(r["legacy_results_used"])
        self.assertEqual(r["trials_pre_registered"], 72)
        self.assertTrue(r["quant_superlab_git_sha"])


if __name__ == "__main__":
    unittest.main()
