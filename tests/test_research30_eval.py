import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import research_30d_enrichment as e
import research_30d_eval as v


class _Response:
    def __init__(self, obj): self.obj = obj
    def raise_for_status(self): pass
    def json(self): return self.obj


class _Session:
    def get(self, url, params=None, timeout=10):
        if "orderbook" in url:
            return _Response({"retCode": 0, "result": {
                "b": [["100", "2"]], "a": [["101", "1"]], "ts": 123}})
        if "open-interest" in url:
            return _Response({"retCode": 0, "result": {"list": [
                {"timestamp": "100", "openInterest": "22"},
                {"timestamp": "200", "openInterest": "23"}]}})
        return _Response({"retCode": 0, "result": {"list": [
            {"fundingRate": "-0.0002", "fundingRateTimestamp": "500"}]}})


class EnrichmentTests(unittest.TestCase):
    def test_snapshots_are_labeled(self):
        s = _Session()
        snap = e.snapshot("BTC", "linear", session=s)
        self.assertEqual(snap["enrichment_status"], "OK")
        self.assertEqual(snap["oi_contracts"], 23)
        self.assertEqual(snap["funding_rate"], -0.0002)
        self.assertGreater(snap["book_imbalance"], 0)

    def test_eval_does_not_use_early_price(self):
        start = datetime(2026, 11, 13, tzinfo=timezone.utc)
        rows = []
        for i, p in ((0, 100), (3, 105)):
            rows.append({"ts": (start + timedelta(hours=i)).isoformat(),
                         "asset": "BTC", "market": "spot", "reference_price": str(p),
                         "imbalance": "0.2", "status": "OK_SAMPLE"})
        self.assertEqual(v.evaluate(rows)["BTC"]["non_overlapping_n"], 0)

    def test_four_hour_label_and_baseline(self):
        start = datetime(2026, 11, 13, tzinfo=timezone.utc)
        rows = []
        for i, p in ((0, 100), (4, 105), (8, 103)):
            rows.append({"ts": (start + timedelta(hours=i)).isoformat(),
                         "asset": "BTC", "market": "spot", "reference_price": str(p),
                         "imbalance": "0.2", "status": "OK_SAMPLE"})
        a = v.evaluate(rows)["BTC"]
        self.assertEqual(a["non_overlapping_n"], 2)
        self.assertEqual(a["direction_hit"], 0.5)
        self.assertEqual(a["always_long_hit"], 0.5)
        self.assertEqual(a["readiness"], "INSUFFICIENT")


if __name__ == "__main__":
    unittest.main()
