from pathlib import Path
import json

import numpy as np
import pandas as pd

import component_research as CR
import day_direction as DD
import evidence_windows as EW
import forecast_ledger as FL
import stop_levels as SL
import trade_plan as TP


def frame(start="2026-11-28T00:00:00Z", n=200):
    idx = pd.date_range(start, periods=n, freq="h")
    px = 100 * np.exp(np.cumsum(np.random.default_rng(11).normal(0.0003, .003, n)))
    return pd.DataFrame({"Open": px, "Close": px, "High": px + 1, "Low": px - 1}, index=idx)


def test_missing_model_and_stale_momentum_are_not_proof():
    for status in (None, "NO_MODEL", "NOT_PROVEN_ADVISORY", "unknown"):
        v = {"learned_model_status": status, "current_direction": "YUKARI", "verdict": "AL",
             "recent_move_quality": "UNAVAILABLE", "short_term_parts": {"price_z": 5}}
        assert not SL.model_proven(v)
        assert SL.evidence_short_side(v) == 0
        assert SL.evidence_long_side(v) == 0
    assert SL.model_proven({"learned_model_status": "ACTIVE"})


def test_momentum_rejects_weekend_gaps_and_unfinished_bar():
    f = frame()
    t = f.index[-1] + pd.Timedelta(minutes=3)
    clean = SL.recent_move(f, now=t)
    assert clean["asof"] == f.index[-2].isoformat()
    assert SL.recent_move(f.drop(f.index[-4]), now=t) is None
    assert SL.recent_move(f.iloc[:-8], now=t) is None
    other = dict(clean, asof=(t - pd.Timedelta(hours=3)).isoformat(), z_own=2.0, z=2.0)
    moves = {"BTC": dict(clean, z=1.0, z_own=1.0), "ETH": other}
    SL.pair_consistent(moves)
    assert moves["BTC"]["z"] == 1.0 and moves["ETH"]["z"] == 2.0


def test_exact_24h_end_no_substitution_or_partial_bar():
    f = frame()
    t = f.index[2] + pd.Timedelta(minutes=4)
    start, end = EW.window(t, 24)
    assert EW.grade_endpoint(f, t, 24, end)["status"] == "PENDING"
    ev = EW.grade_endpoint(f, t, 24, end + pd.Timedelta(hours=1))
    assert ev["status"] == "EXACT" and ev["end_price"] == f.loc[end, "Open"]
    bad = EW.grade_endpoint(f.drop(end), t, 24, end + pd.Timedelta(hours=100))
    assert bad["status"] == "MISSING_EXACT_WINDOW"


def test_daily_tournament_does_not_pool_correlated_days_or_infer_asset_proof(tmp_path):
    led = DD.DayDirectionLedger(str(tmp_path / "d.csv"))
    records = []
    for asset in ("SPX", "NQ", "BTC", "ETH", "XAU", "XAG"):
        for day in range(12):
            observed = pd.Timestamp("2026-01-01T00:04Z") + pd.Timedelta(days=day)
            start, end = EW.window(observed, 24)
            records.append({"asset": asset, "logic": "test", "graded": 1, "ret_24h": -.01,
                            "label_schema": EW.SCHEMA, "label_reason": "EXACT",
                            "label_start_utc": start.isoformat(), "label_end_utc": end.isoformat(),
                            "chosen": 0, **{f"c_{c}": -1 if c == "mom4h" else 0 for c in DD.CANDS}})
    led.df = pd.DataFrame(records)
    s = led.stats("test")["mom4h"]
    assert s["n"] == 72 and not s["proven"]
    assert all(not v["proven"] for v in s["asset_evidence"].values())
    assert DD.choose("BTC", {}, {"mom4h": -1}, {"mom4h": {"proven": True, "z": 5}})["side"] == 0


def test_bracket_missing_or_ambiguous_path_and_gap_entry():
    f = frame(n=48)
    t = f.index[0] + pd.Timedelta(minutes=3)
    start, end = EW.window(t, 24)
    f.loc[:, ["Open", "High", "Low", "Close"]] = [100, 101, 99, 100]
    f.loc[start + pd.Timedelta(hours=2), ["High", "Low"]] = [115, 85]
    x = EW.barrier_path(f, t, 24, start + pd.Timedelta(hours=3), 1, 90, 110)
    assert x["outcome"] == "stop" and x["r"] == -1
    assert EW.barrier_path(f.drop(start + pd.Timedelta(hours=1)), t, 24,
                           end + pd.Timedelta(hours=100), 1, 90, 110)["status"] == "MISSING_CONTIGUOUS_PATH"
    assert EW.barrier_path(f, t, 24, end, 1, 101, 110)["status"] == "OPEN_OUTSIDE_BRACKET"
    # Cannot use a forming bar for a settled stop.
    assert EW.barrier_path(f, t, 24, start + pd.Timedelta(hours=2), 1, 90, 110)["status"] == "PENDING"


def test_no_proposal_when_risk_unknown():
    assert TP.plan("BTC", {"day_direction": {"side": 1, "strength": "güçlü"}}, {}, {})["action"] == "none"


def test_component_observer_preserves_neutral_missing_and_no_lookahead(tmp_path):
    f = frame(n=200)
    t = f.index[100] + pd.Timedelta(minutes=2)
    p = tmp_path / "evidence.json"
    r = tmp_path / "report.json"
    v = {"learned_model_status": "NOT_PROVEN_ADVISORY", "current_direction": "YUKARI", "verdict": "AL",
         "recent_move": {"z": 2., "z_own": 2.}, "day_direction": {"side": 0, "source": "yok"},
         "entry_allowed": False, "day_range": {"move": 1., "price": 100.}}
    # Same hour is idempotent; closed market is recorded as an exclusion.
    for when in (t, t + pd.Timedelta(minutes=10)):
        CR.run_cycle({"BTC": v, "SPX": v}, {"BTC": f, "SPX": f},
                     {"SPX": {"session": {"phase": "Kapalı"}}}, now=when, ledger=p, report=r)
    rows = json.loads(p.read_text())["rows"]
    assert len(rows) == 2 and rows[0]["labels"] == {}
    assert rows[1]["eligibility"] == "MARKET_CLOSED"
    CR.run_cycle({"BTC": v}, {"BTC": f}, {}, now=t + pd.Timedelta(hours=30), ledger=p, report=r)
    card = json.loads(r.read_text())["versions"][CR.LOGIC_VERSION]["BTC"]
    assert card["horizons"]["4"]["short"]["active"] == 1
    assert card["horizons"]["4"]["gated"]["neutral"] == 1
    assert card["horizons"]["24"]["day"]["neutral"] == 1
    assert card["horizons"]["4"]["short"]["status"] == "INSUFFICIENT"
    assert json.loads(r.read_text())["no_live_promotion"]


def test_legacy_24h_grade_does_not_calibrate(tmp_path):
    p = tmp_path / "f.csv"
    pd.DataFrame([{"ts": "2026-11-01T00:00:00Z", "asset": "SPX", "logic": FL.LOGIC,
                   "graded_24h": 1, "ret_24h": .01}]).to_csv(p, index=False)
    led = FL.ForecastLedger(str(p))
    assert led.scorecard("SPX")["legacy_24h_unverified"] == 1
    assert "range" not in led.scorecard("SPX")


def test_performance_ci_uses_actual_subsample():
    from performance_ledger import PerformanceLedger, wilson_lower_bound
    rows = [{"a": "BTC", "t": f"2026-01-01T0{i}:00:00Z", "d": 1,
             "o": {"4": -.01 if i % 4 == 0 else .01}} for i in range(8)]
    r = PerformanceLedger._stats(rows, 4, lambda x: x["d"])
    assert r["hit"] == .75 and r["n_indep"] == 2
    assert r["hit_lb95"] == wilson_lower_bound(0, 2)


def test_missing_learned_model_final_gate_blocks_entry():
    from gatekeeper import PreTradeGatekeeper
    g = PreTradeGatekeeper.__new__(PreTradeGatekeeper)
    v = {"learned_model_status": "NO_MODEL", "entry_allowed": True, "verdict": "AL"}
    assert not g.apply_final_entry_gate({"BTC": v})["BTC"]["entry_allowed"]


def test_futures_routine_break_is_not_an_outage_and_gap_open_is_used():
    t = pd.Timestamp("2026-11-25T19:03Z")
    start, end = EW.window(t, 24)
    f = pd.DataFrame({"Open":100.,"High":101.,"Low":99.,"Close":100.},
                     index=pd.date_range(start, end, freq="h"))
    # Existing repository session calendar marks 22:00 UTC the normal break in November.
    gap = pd.Timestamp("2026-11-25T22:00Z")
    reopened = gap + pd.Timedelta(hours=1)
    f = f.drop(gap)
    f.loc[reopened, ["Open", "High", "Low", "Close"]] = [85, 87, 84, 86]
    x = EW.barrier_path(f, t, 24, end+pd.Timedelta(hours=100), 1, 90, 110, asset="SPX")
    assert x["status"] == "EXACT_PATH" and x["outcome"] == "stop"
    assert x["exit_proxy"] == 85 and x["r"] == -1.5 and x["skipped_regular_closure_hours"] == 1
    # An open-session hole is still not an acceptable path.
    assert EW.barrier_path(f.drop(start+pd.Timedelta(hours=1)), t, 24, end+pd.Timedelta(hours=100),
                           1, 90, 110, asset="SPX")["status"] == "MISSING_CONTIGUOUS_PATH"
