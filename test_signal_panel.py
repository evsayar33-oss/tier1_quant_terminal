"""Tests for signal_panel (v5.0): every system output becomes a number, live history is capped."""
import json
import os
import tempfile

import pandas as pd

import signal_panel as SP

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_fixture_terminal_state.json")


def test_flatten_turns_a_real_verdict_into_numbers():
    s = json.load(open(FIX, encoding="utf-8"))
    row = SP.flatten(s["asset_verdicts"]["BTC"], SP.macro_of(s), SP.factor_signs())
    assert len(row) > 60
    assert all(isinstance(v, float) for v in row.values())
    for k in ("sys::score", "sys::live_score", "cat::verdict", "cat::short_term", "sys::entry_allowed", "mac::regime_id"):
        assert k in row, k
    assert any(k.startswith("f::") for k in row)


def test_direction_codes():
    assert SP._dir_code("GÜÇLÜ AL") == 2 and SP._dir_code("AL (LONG)") == 1
    assert SP._dir_code("SAT") == -1 and SP._dir_code("🔴🔴 GÜÇLÜ AŞAĞI") == -2
    assert SP._dir_code("NÖTR (BEKLE)") == 0 and SP._dir_code("⛔ GİRİŞ KAPALI") == 0


def test_history_appends_and_is_capped():
    s = json.load(open(FIX, encoding="utf-8"))
    root = tempfile.mkdtemp()
    old = SP.MAX_HISTORY_ROWS
    SP.MAX_HISTORY_ROWS = 18
    try:
        for h in range(5):
            SP.append_history(s, pd.Timestamp("2026-10-07 10:00", tz="UTC") + pd.Timedelta(hours=h), root)
    finally:
        SP.MAX_HISTORY_ROWS = old
    d = pd.read_csv(os.path.join(root, SP.HISTORY))
    assert len(d) == 18 and d["t"].nunique() == 3 and set(d["asset"]) == set(s["asset_verdicts"])
