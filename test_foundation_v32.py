"""Foundation v3.2 regression tests (state safety, leading-factor data
handling, direction-aware entry gate, horizon-accurate settlement,
performance ledger, frozen clock)."""

import json
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import system_clock
from adaptive_regime_thresholds import AdaptiveThresholdStore
from leading_indicators import (
    build_vol_history_frame,
    compute_relative_vol_premium_lead,
    compute_vol_term_structure_lead,
)
from performance_ledger import PerformanceLedger, wilson_lower_bound
from state_schema import load_versioned_json
from timeframe_confluence import TimeframeReliabilityStore


@contextmanager
def _in_tmpdir():
    prev = os.getcwd()
    d = tempfile.mkdtemp()
    os.chdir(d)
    try:
        yield d
    finally:
        os.chdir(prev)
        system_clock.clear_frozen_now()


def _hourly(start, n, start_price=100.0, step=0.1):
    idx = pd.date_range(start, periods=n, freq="1h", tz="UTC")
    close = start_price + step * np.arange(n)
    return pd.DataFrame({"Open": close, "High": close + 0.05, "Low": close - 0.05,
                         "Close": close, "Volume": 1000.0}, index=idx)


# ---------------------------------------------------------------- clock
def test_frozen_clock_roundtrip():
    t = pd.Timestamp("2025-03-04 14:00", tz="UTC")
    system_clock.set_frozen_now(t)
    assert system_clock.now_utc() == t.to_pydatetime()
    system_clock.clear_frozen_now()
    assert abs((system_clock.now_utc() - datetime.now(timezone.utc)).total_seconds()) < 5


# ------------------------------------------------ adaptive store dedupe
def test_threshold_store_obs_id_replaces_instead_of_inflating():
    with _in_tmpdir():
        st = AdaptiveThresholdStore(path="th.json")
        for v in (1.0, 1.1, 1.2):
            st.update("K", v, obs_id="2026-01-05")   # same day, many runs
        st.update("K", 2.0, obs_id="2026-01-06")
        assert list(st._series["K"]) == [1.2, 2.0]
        st.save()
        st2 = AdaptiveThresholdStore(path="th.json")
        assert list(st2._series["K"]) == [1.2, 2.0]
        st2.update("K", 2.5, obs_id="2026-01-06")      # remembered across restarts
        assert list(st2._series["K"]) == [1.2, 2.5]
        st2.update("K", 3.0)                           # no obs_id -> old behavior (append)
        assert list(st2._series["K"]) == [1.2, 2.5, 3.0]


def test_threshold_store_migrates_v1_duplicates():
    with _in_tmpdir():
        with open("adaptive_regime_thresholds_state.json", "w") as fh:
            json.dump({"version": "1.0.0", "series": {"A": [0.0, 0.0, 1.5, 1.5, 0.2]}}, fh)
        st = AdaptiveThresholdStore(path="adaptive_regime_thresholds_state.json")
        assert list(st._series["A"]) == [0.0, 1.5, 0.2]


# ------------------------------------------------------- schema guard
def test_corrupt_state_is_backed_up_not_lost():
    with _in_tmpdir():
        with open("x.json", "w") as fh:
            fh.write("{ this is not json")
        assert load_versioned_json("x.json", "1.0.0") is None
        backups = os.listdir("state_backups")
        assert any(b.startswith("x.json.") and "corrupt" in b for b in backups)


def test_unknown_version_is_not_misread():
    with _in_tmpdir():
        with open("y.json", "w") as fh:
            json.dump({"schema_version": "9.9.9", "cells": {}}, fh)
        assert load_versioned_json("y.json", "1.1.0") is None
        assert any("unknown_version" in b for b in os.listdir("state_backups"))


# ------------------------------------------------- leading indicators
def test_leading_indicators_return_none_on_missing_data():
    empty = pd.DataFrame()
    assert compute_vol_term_structure_lead(empty, empty) is None
    assert compute_relative_vol_premium_lead(empty) is None
    short = _hourly("2026-01-01", 5)
    assert compute_relative_vol_premium_lead(short) is None   # < 20 points -> unknown, not "neutral"


def test_vol_history_frame_uses_daily_baseline_without_same_day_leak():
    daily_idx = pd.date_range("2025-06-01", periods=150, freq="1D", tz="UTC")
    daily = pd.DataFrame({"Close": np.full(150, 15.0) + np.random.default_rng(0).normal(0, 0.5, 150)}, index=daily_idx)
    last_day = daily_idx[-1]
    intraday = _hourly(last_day + pd.Timedelta(hours=10), 3, start_price=25.0, step=0.0)
    frame = build_vol_history_frame(intraday, daily)
    # today's daily bar must not be part of the baseline; the current value is the intraday print
    assert frame.index[-1] == intraday.index[-1]
    assert (frame.index[:-1].normalize() < last_day.normalize()).all()
    val = compute_relative_vol_premium_lead(frame)
    assert val is not None and val < -1.0      # a 25 print vs ~15 norm = strong priced-in risk (bearish lead)


# ------------------------------------------- direction-aware entry gate
def _verdict(verdict, allowed, ltf, mtf, htf, conf):
    return {
        "verdict": verdict, "entry_allowed": allowed, "entry_reason": "x",
        "timeframe_confluence": {
            "available": True, "confluence_score": conf,
            "timeframes": {
                "HTF_1D": {"available": True, "score": htf},
                "MTF_4H": {"available": True, "score": mtf},
                "LTF_1H": {"available": True, "score": ltf},
            },
        },
    }


def test_entry_gate_blocks_signal_against_all_timeframes():
    from gatekeeper import PreTradeGatekeeper
    v = {"BTC": _verdict("SAT", True, 0.21, 0.43, 0.97, 0.62)}   # live bug case
    out = PreTradeGatekeeper.apply_final_entry_gate(PreTradeGatekeeper.__new__(PreTradeGatekeeper), v)
    assert out["BTC"]["entry_grade"] == "C"
    assert out["BTC"]["entry_allowed"] is False
    assert out["BTC"]["verdict"] == "SAT"            # direction itself untouched


def test_entry_gate_grades_a_and_b_and_never_grants():
    from gatekeeper import PreTradeGatekeeper
    gk = PreTradeGatekeeper.__new__(PreTradeGatekeeper)
    v = {
        "A": _verdict("AL", True, 0.3, 0.4, 0.5, 0.45),
        "B": _verdict("SAT", True, -0.2, 0.1, 0.3, 0.05),     # leading short, LTF turned down, HTF mildly up
        "N": _verdict("NÖTR (BEKLE)", True, 0.3, 0.3, 0.3, 0.3),
        "F": _verdict("AL", False, 0.3, 0.4, 0.5, 0.45),       # already blocked elsewhere
    }
    out = gk.apply_final_entry_gate(v)
    assert out["A"]["entry_grade"] == "A" and out["A"]["entry_allowed"] is True
    assert out["B"]["entry_grade"] == "B" and out["B"]["entry_allowed"] is True
    assert out["N"]["entry_allowed"] is False
    assert out["F"]["entry_grade"] == "A" and out["F"]["entry_allowed"] is False


# --------------------------------- timeframe store: horizon settlement
def test_tf_store_grades_at_horizon_not_at_settle_time():
    with _in_tmpdir():
        store = TimeframeReliabilityStore(path="tfc.json")
        s = _hourly("2026-03-02 00:00", 100)["Close"]             # rising
        s.iloc[5:] = s.iloc[5:] - 50.0                            # but crashes after the 4h horizon
        system_clock.set_frozen_now(s.index[0])
        store.record_prediction("SPX", 1, "LTF_1H", 1, float(s.iloc[0]), 4.0, reference_time=s.index[0])
        system_clock.set_frozen_now(s.index[-1])                  # settle ~4 days later
        n = store.settle_due_predictions({"SPX": float(s.iloc[-1])}, price_series={"SPX": s})
        assert n == 1
        cell = store._data["cells"]["SPX|1|LTF_1H"]
        assert cell["hit_ewma"] > 0.5                              # graded on the 4h move (up) -> correct


def test_tf_store_voids_closed_market_window():
    with _in_tmpdir():
        store = TimeframeReliabilityStore(path="tfc.json")
        idx = pd.DatetimeIndex([pd.Timestamp("2026-03-06 20:00", tz="UTC"), pd.Timestamp("2026-03-09 01:00", tz="UTC")])
        s = pd.Series([100.0, 101.0], index=idx)
        system_clock.set_frozen_now(idx[0])
        store.record_prediction("SPX", 1, "LTF_1H", -1, 100.0, 4.0, reference_time=idx[0])
        system_clock.set_frozen_now(idx[-1])
        assert store.settle_due_predictions({"SPX": 101.0}, price_series={"SPX": s}) == 0
        assert store._data["pending"] == []                       # voided, not scored as a miss


# ------------------------------------------------------ performance ledger
def test_performance_ledger_end_to_end():
    with _in_tmpdir():
        df = _hourly("2026-04-01", 200)                             # steadily rising
        grid = {"ES=F": df}
        lookup = lambda g, a: g.get("ES=F", pd.DataFrame())
        ledger = PerformanceLedger(path="pl.json")
        for i in range(0, 60, 6):
            system_clock.set_frozen_now(df.index[i])
            sliced = {"ES=F": df.iloc[: i + 1]}
            ledger.record_cycle({"SPX": {"verdict": "AL", "entry_allowed": True, "entry_grade": "B",
                                         "score": 1.0}}, sliced, lookup, 5)
        # re-running on the same bar must not add a duplicate record
        ledger.record_cycle({"SPX": {"verdict": "AL"}}, {"ES=F": df.iloc[:55]}, lookup, 5)
        assert len(ledger.data["records"]) == 10
        system_clock.set_frozen_now(df.index[-1])
        graded = ledger.settle({"SPX": {"1h": df["Close"], "1d": None}})
        assert graded > 0
        s = ledger.summary()
        assert s["overall"]["24"]["model"]["hit"] == 1.0
        ledger.save()
        ledger.write_report("rep.md")
        assert os.path.exists("rep.md")
        assert PerformanceLedger(path="pl.json").data["records"]


def test_wilson_bound_sane():
    assert 0.0 < wilson_lower_bound(60, 100) < 0.6
    assert wilson_lower_bound(0, 0) == 0.0
