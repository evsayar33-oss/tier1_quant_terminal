"""Regression tests: first-seen timestamps, no backdating, costs and paired test."""
import copy
import unittest
from datetime import datetime, timedelta, timezone
from independent_audit import observe, settle, stats, mcnemar_one_sided, append_price_snapshots, fetch_independent_prices

T = datetime(2026,11,14,12,tzinfo=timezone.utc)
M = {"start_utc":"2026-11-14T06:24:26+00:00",
     "end_utc":"2026-12-14T06:24:26+00:00"}


def payload(t, side="SAT"):
    return {"last_updated":t.isoformat(), "asset_verdicts":{
        "BTC":{"verdict":side,"entry_allowed":False},
        "ETH":{"verdict":"NEUTRAL","entry_allowed":False}}}


def px(t, price, asset="BTC"):
    return {"a":asset,"rec":t.isoformat(),"t":(t-timedelta(hours=1)).isoformat(),"p":price}


class TestIndependentAudit(unittest.TestCase):
    def test_first_observed_no_duplicate_and_no_backdating(self):
        store={}
        p=payload(T-timedelta(minutes=2))
        self.assertEqual(observe(p,store,T,M,[px(T-timedelta(minutes=2),100)]),1)
        self.assertEqual(store["calls"][0]["observed_utc"],"2026-11-14T12:00:00Z")
        self.assertEqual(store["calls"][0]["entry_price"],100)
        self.assertEqual(store["calls"][0]["price_source"],"lagged_1h_bar_proxy_NOT_EXECUTABLE")
        self.assertEqual(observe(p,store,T+timedelta(minutes=5),M,[]),0)
        self.assertEqual(len(store["calls"]),1)

    def test_future_observation_not_backfilled(self):
        store={}
        observe(payload(T),store,T,M,[px(T,100)])
        settle(store,T+timedelta(hours=6))
        self.assertEqual(store["calls"][0]["horizons"]["4"]["status"],"PENDING_PRICE")
        settle(store,T+timedelta(hours=60))
        self.assertEqual(store["calls"][0]["horizons"]["4"]["status"],"MISSING_FUTURE_PRICE")

    def test_observed_future_and_hypothetical_costs(self):
        store={}
        observe(payload(T),store,T,M,[px(T,100)])
        observe(payload(T+timedelta(hours=4,minutes=5)),store,
                T+timedelta(hours=4,minutes=5),
                M,[px(T+timedelta(hours=4,minutes=5),90)])
        settle(store,T+timedelta(hours=6))
        o=store["calls"][0]["horizons"]["4"]
        self.assertEqual(o["status"],"GRADED")
        self.assertAlmostEqual(o["gross_return"],0.1)
        x=stats(store,M,T+timedelta(hours=6))["horizons"]["4"]
        self.assertEqual(x["independent_by_asset_n"],1)
        self.assertEqual(x["hypothetical_cost_scenarios_bps"]["20"]["hypothetical_mean_bps"],980)

    def test_stale_publication_does_not_stop_market_poll(self):
        store={}
        append_price_snapshots(store,T,{"BTC":{"price":100,"source":"TEST"}})
        self.assertEqual(observe(payload(T-timedelta(hours=5)),store,T,M,[]),0)
        self.assertEqual(len(store["snapshots"]),6)
        self.assertEqual(store["stale_production_publication_utc"],"2026-11-14T07:00:00Z")

    def test_no_unseen_price_and_entry_gate(self):
        store={}
        observe(payload(T),store,T,M,[])
        self.assertIsNone(store["calls"][0]["entry_price"])
        self.assertEqual(stats(store,M,T)["entry_allowed"],0)

    def test_unchanged_signal_still_records_new_price(self):
        store={}
        p=payload(T)
        prices={"BTC":{"price":100,"source":"TEST"}}
        append_price_snapshots(store,T,prices)
        observe(p,store,T,M,[],prices)
        append_price_snapshots(store,T+timedelta(hours=4,minutes=10),
                               {"BTC":{"price":90,"source":"TEST"}})
        self.assertEqual(observe(p,store,T+timedelta(hours=4,minutes=10),M,[],{}),0)
        settle(store,T+timedelta(hours=6))
        self.assertEqual(store["calls"][0]["horizons"]["4"]["status"],"GRADED")
        self.assertAlmostEqual(store["calls"][0]["horizons"]["4"]["gross_return"],0.1)
        self.assertEqual(stats(store,M,T+timedelta(hours=6))["price_coverage"]["BTC"]["valid"],2)

    def test_missing_price_recovers_within_grace(self):
        store={}
        append_price_snapshots(store,T,{"BTC":{"price":100,"source":"TEST"}})
        observe(payload(T),store,T,M,[],{"BTC":{"price":100,"source":"TEST"}})
        settle(store,T+timedelta(hours=5,minutes=30))
        self.assertEqual(store["calls"][0]["horizons"]["4"]["status"],"PENDING_PRICE")
        append_price_snapshots(store,T+timedelta(hours=4,minutes=30),
                               {"BTC":{"price":110,"source":"TEST"}})
        settle(store,T+timedelta(hours=6))
        self.assertEqual(store["calls"][0]["horizons"]["4"]["status"],"GRADED")

    def test_provider_missing_six_assets_explicit(self):
        class Missing:
            def __init__(self,symbol): self.symbol=symbol
            def history(self,**kw): raise RuntimeError("feed down")
        got=fetch_independent_prices(T,Missing)
        self.assertEqual(set(got),{"SPX","NQ","XAU","XAG","BTC","ETH"})
        self.assertTrue(all(x["price"] is None for x in got.values()))

    def test_exact_paired_p(self):
        self.assertAlmostEqual(mcnemar_one_sided(3,0),0.125)
        self.assertAlmostEqual(mcnemar_one_sided(1,1),0.75)

    def test_nonoverlap_by_asset(self):
        store={}
        for k in range(5):
            t=T+timedelta(hours=k)
            observe(payload(t),store,t,M,[px(t,100-k)])
        settle(store,T+timedelta(hours=7))
        self.assertLessEqual(stats(store,M,T+timedelta(hours=7))["horizons"]["4"]["independent_by_asset_n"],1)


if __name__=="__main__":
    unittest.main()
