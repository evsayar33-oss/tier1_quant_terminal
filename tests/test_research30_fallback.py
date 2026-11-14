"""Offline integration tests for blocked Bybit -> OKX, schema migration and units."""
import csv
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
import requests
import research_30d as r
import research_30d_okx as okx
import research_30d_enrichment as enrichment

NOW = datetime(2026, 11, 14, 7, 22, tzinfo=timezone.utc)
MS = int(NOW.timestamp() * 1000)


class Response:
    def __init__(self, data=None, forbidden=False):
        self.data = data
        self.forbidden = forbidden
    def raise_for_status(self):
        if self.forbidden:
            raise requests.HTTPError("403 Forbidden")
    def json(self):
        return self.data


class FakeExchange:
    def __init__(self):
        self.calls = []
        self.mult = "0.01"
    def get(self, url, params=None, timeout=12):
        self.calls.append((url, params))
        if "api.bybit.com" in url:
            return Response(forbidden=True)
        inst = (params or {}).get("instId", "BTC-USDT")
        asset = inst.split("-")[0]
        if url.endswith("/public/instruments"):
            return Response({"code": "0", "data": [{
                "instId": inst, "ctVal": self.mult, "ctValCcy": asset}]})
        if url.endswith("/market/trades"):
            rows = [
                {"instId": inst, "tradeId": str(i), "ts": str(MS - 3000 + i * 100),
                 "px": "100", "sz": "2", "side": "buy" if i < 15 else "sell"}
                for i in range(25)
            ]
            return Response({"code": "0", "data": rows})
        if url.endswith("/market/books"):
            return Response({"code": "0", "data": [{
                "bids": [["99", "2", "0", "1"]],
                "asks": [["101", "1", "0", "1"]], "ts": str(MS - 1000)}]})
        if url.endswith("/public/open-interest"):
            return Response({"code": "0", "data": [{
                "instId": inst, "oi": "3000", "oiCcy": "30",
                "oiUsd": "3000000", "ts": str(MS - 1000)}]})
        if url.endswith("/public/funding-rate"):
            return Response({"code": "0", "data": [{
                "instId": inst, "fundingRate": "0.0001",
                "fundingTime": str(MS + 3600000)}]})
        raise AssertionError("unexpected endpoint: " + url)


class FallbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name) / "research_30d"
        for name, path in (("ROOT", root), ("MANIFEST", root / "manifest.json"),
                           ("LEDGER", root / "observations.csv"),
                           ("REPORT", root / "report.md")):
            p = patch.object(r, name, path)
            p.start()
            self.addCleanup(p.stop)

    def test_public_403_okx_fallback_and_persistence(self):
        f = FakeExchange()
        r.start(NOW)
        result = r.collect({"asset_verdicts": {}}, now=NOW, session=f)
        self.assertEqual(result["errors"], 0)
        self.assertEqual(result["valid_snapshots"], 4)
        self.assertEqual(result["new_snapshots"], 4)
        rows = r.read_rows()
        self.assertEqual(len(rows), 4)
        for row in rows:
            self.assertEqual(row["venue"], "okx")
            self.assertEqual(row["fallback_from"], "bybit")
            self.assertEqual(row["enrichment_source"], "okx")
            self.assertEqual(row["status"], "OK_SAMPLE")
            self.assertEqual(row["enrichment_status"], "OK")
            self.assertIn("bybit:", row["attempted_sources"])
            self.assertIn("okx: OK_SAMPLE", row["attempted_sources"])
            self.assertEqual(row["book_ts"], str(MS - 1000))
            self.assertNotEqual(row["book_imbalance"], "")
            self.assertNotEqual(row["spread_bps"], "")
            self.assertTrue(row["funding_rate"] if row["market"] == "linear" else not row["funding_rate"])
            self.assertTrue(row["oi_contracts"] if row["market"] == "linear" else not row["oi_contracts"])
        linear = next(x for x in rows if x["asset"] == "BTC" and x["market"] == "linear")
        # 15 buys, 10 sells, each 2 contracts * 0.01 BTC * $100 = $2
        self.assertAlmostEqual(float(linear["buy_usdt"]), 30)
        self.assertAlmostEqual(float(linear["sell_usdt"]), 20)
        self.assertEqual(linear["oi_unit"], "contracts")
        self.assertEqual(linear["contract_value_base"], "0.01")
        self.assertTrue((r.LEDGER).exists())
        self.assertIn("Latest source", r.REPORT.read_text())
        self.assertEqual(r.collect(now=NOW, session=f)["new_snapshots"], 0)

    def test_migrate_old_csv_without_losing_existing_records(self):
        r.start(NOW)
        r.LEDGER.write_text(
            "ts,experiment_id,asset,market,source,trade_count,first_trade_ms,last_trade_ms,"
            "sample_span_s,buy_usdt,sell_usdt,signed_usdt,imbalance,last_trade_price,"
            "reference_price,observed_at_ms,status,detail,extra_future_field\\n"
            + NOW.replace(minute=0,second=0,microsecond=0).isoformat()
            + ",existing,BTC,spot,bybit_public_recent_trade,,,,,,,,,,,123,ERROR,403 Forbidden,KEEP_ME\\n",
            encoding="utf-8",
        )
        # Above string contains literal backslash-n? Convert using exactly one
        # actual CSV newline at setup, then assert no original extras are dropped.
        data = r.LEDGER.read_text().replace("\\n", "\n")
        r.LEDGER.write_text(data, encoding="utf-8")
        f = FakeExchange()
        result = r.collect(now=NOW, session=f)
        self.assertEqual(result["retried_snapshots"], 1)
        rows = r.read_rows()
        self.assertEqual(len(rows), 4)
        recovered = next(x for x in rows if x["asset"] == "BTC" and x["market"] == "spot")
        self.assertEqual(recovered["previous_status"], "ERROR")
        self.assertEqual(recovered["retry_count"], "1")
        self.assertEqual(recovered["venue"], "okx")
        self.assertEqual(recovered["status"], "OK_SAMPLE")
        self.assertIn("extra_future_field", r.LEDGER.read_text().splitlines()[0])
        self.assertEqual(r.read_manifest()["start_utc"], NOW.isoformat(timespec="seconds"))

    def test_no_mixing_and_no_fabricated_units(self):
        f = FakeExchange()
        res = r.fetch_market_sample("BTC", "linear", now_ms=MS, session=f)
        self.assertEqual(res["venue"], "okx")
        e = enrichment.snapshot("BTC", "linear", session=f, venue=res["venue"])
        self.assertEqual(e["enrichment_source"], "okx")
        self.assertEqual(e["oi_contracts"], 3000.0)
        self.assertEqual(e["funding_kind"], "current_or_predicted")
        with self.assertRaises(ValueError):
            enrichment.snapshot("BTC", "spot", session=f, venue="unknown")
        f.mult = "0"
        with self.assertRaises(ValueError):
            okx.get_trades("BTC", "linear", session=f)


if __name__ == "__main__":
    unittest.main()
