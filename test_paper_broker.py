"""Tests for the paper broker (v3.9): no look-ahead, conservative fills, caps."""
import json
import os
import tempfile

import pandas as pd

import paper_broker as pb


def _write_bars(root, sym, rows):
    os.makedirs(os.path.join(root, "ohlcv_history"), exist_ok=True)
    pd.DataFrame(rows, columns=["timestamp", "Open", "High", "Low", "Close", "Volume"]).to_csv(
        os.path.join(root, "ohlcv_history", sym.replace("=", "_") + ".csv"), index=False)


def _flat_rows(n, start="2026-10-01 00:00", px=100.0, rng=1.0):
    ts = pd.date_range(start, periods=n, freq="h", tz="UTC")
    return [[str(t), px, px + rng / 2, px - rng / 2, px, 0] for t in ts]


def _sig(side="LONG", gate=True, st="🟢 YUKARI"):
    return {"assets": {"BTC": {"side": side, "entry_allowed": gate, "short_term": st}}}


def _setup(rows):
    root = tempfile.mkdtemp()
    _write_bars(root, "BTC-USD", rows)
    return root


def test_fill_is_next_bar_open_not_signal_close():
    rows = _flat_rows(30)
    root = _setup(rows)
    pb.step(_sig(), root)                                  # signal on bar 29 -> order only
    led = json.load(open(os.path.join(root, pb.LEDGER)))
    assert not led["positions"] and "model:BTC" in led["orders"]
    rows.append(["2026-10-02 06:00:00+00:00", 101.0, 101.2, 100.8, 101.0, 0])
    _write_bars(root, "BTC-USD", rows)
    pb.step(_sig(), root)
    led = json.load(open(os.path.join(root, pb.LEDGER)))
    assert led["positions"]["model:BTC"]["entry"] == 101.0          # next bar OPEN


def test_stop_assumed_when_bar_hits_both():
    rows = _flat_rows(30)
    root = _setup(rows)
    pb.step(_sig(), root)
    rows.append(["2026-10-02 06:00:00+00:00", 100.0, 100.2, 99.8, 100.0, 0])
    rows.append(["2026-10-02 07:00:00+00:00", 100.0, 110.0, 90.0, 100.0, 0])   # touches both
    _write_bars(root, "BTC-USD", rows)
    pb.step(_sig(), root)
    led = json.load(open(os.path.join(root, pb.LEDGER)))
    reasons = {t["strategy"]: t["reason"] for t in led["closed"]}
    assert reasons["model"] == "SL" and led["closed"][0]["net_ret"] < 0


def test_flip_exits_at_next_open_and_reverses():
    rows = _flat_rows(30)
    root = _setup(rows)
    pb.step(_sig(), root)
    rows.append(["2026-10-02 06:00:00+00:00", 100.0, 100.2, 99.8, 100.0, 0])
    _write_bars(root, "BTC-USD", rows)
    pb.step(_sig("SHORT", st="🔴 AŞAĞI"), root)
    rows.append(["2026-10-02 07:00:00+00:00", 100.1, 100.2, 99.9, 100.0, 0])
    _write_bars(root, "BTC-USD", rows)
    pb.step(_sig("SHORT", st="🔴 AŞAĞI"), root)
    led = json.load(open(os.path.join(root, pb.LEDGER)))
    assert led["positions"]["model:BTC"]["side"] == "SHORT"
    assert any(t["reason"] == "FLIP" and t["exit"] == 100.1 for t in led["closed"])


def test_gate_closed_means_no_gate_trade():
    rows = _flat_rows(30)
    root = _setup(rows)
    pb.step(_sig(gate=False), root)
    led = json.load(open(os.path.join(root, pb.LEDGER)))
    assert "gate:BTC" not in led["orders"] and "model:BTC" in led["orders"]


def test_stale_order_cancelled_after_market_gap():
    rows = _flat_rows(30)
    root = _setup(rows)
    pb.step(_sig(), root)
    rows.append(["2026-10-03 12:00:00+00:00", 100.0, 100.2, 99.8, 100.0, 0])   # weekend-style gap
    _write_bars(root, "BTC-USD", rows)
    pb.step(_sig("FLAT", st="⚪ YATAY"), root)
    led = json.load(open(os.path.join(root, pb.LEDGER)))
    assert not led["positions"]


def test_time_stop_and_costs():
    rows = _flat_rows(30)
    root = _setup(rows)
    pb.step(_sig(), root)
    rows += _flat_rows(30, start="2026-10-02 06:00")
    _write_bars(root, "BTC-USD", rows)
    pb.step(_sig("FLAT", st="⚪ YATAY"), root)
    led = json.load(open(os.path.join(root, pb.LEDGER)))
    t = [x for x in led["closed"] if x["strategy"] == "model"][0]
    assert t["reason"] == "TIME" and abs(t["net_ret"] + 2 * pb.COST["BTC"]) < 1e-9


def test_scorecard_requires_proof():
    led = {"closed": [{"strategy": "model", "asset": "BTC", "side": "LONG", "net_ret": 0.01, "exit_ts": "2026-10-02 10:00", "reason": "TP"}] * 10,
           "benchmark": {"BTC": {"start": 100, "last": 100}}, "positions": {}, "orders": {}}
    sc = pb.scorecard(led)
    assert sc["model"]["n"] == 10 and not sc["model"]["proven"]
    assert "Paper Trading" in pb.report_md(led, sc)


def _lab(side, entry=None, sl=None, tp=None):
    return {"assets": {"BTC": {"side": "FLAT", "entry_allowed": False, "short_term": "⚪",
                               "lab": {"side": side, "entry": entry, "sl": sl, "tp": tp}}}}


def test_lab_strategy_holds_past_24h_and_exits_on_flat_signal():
    rows = _flat_rows(30)
    root = _setup(rows)
    pb.step(_lab("LONG"), root)
    rows += _flat_rows(40, start="2026-10-02 06:00")           # 40h later, still LONG
    _write_bars(root, "BTC-USD", rows)
    pb.step(_lab("LONG"), root)
    led = json.load(open(os.path.join(root, pb.LEDGER)))
    assert "lab:BTC" in led["positions"] and led["positions"]["lab:BTC"]["sl"] is None
    pb.step(_lab("FLAT"), root)                                 # signal goes flat -> exit order
    rows.append(["2026-10-03 22:00:00+00:00", 100.5, 100.6, 100.4, 100.5, 0])
    _write_bars(root, "BTC-USD", rows)
    pb.step(_lab("FLAT"), root)
    led = json.load(open(os.path.join(root, pb.LEDGER)))
    t = [x for x in led["closed"] if x["strategy"] == "lab"][0]
    assert t["reason"] == "EXIT" and t["exit"] == 100.5 and "lab:BTC" not in led["positions"]


def test_lab_strategy_uses_its_own_stop_distance():
    rows = _flat_rows(30)
    root = _setup(rows)
    pb.step(_lab("LONG", entry=100.0, sl=97.0, tp=106.0), root)
    rows.append(["2026-10-02 06:00:00+00:00", 101.0, 101.2, 100.8, 101.0, 0])
    _write_bars(root, "BTC-USD", rows)
    pb.step(_lab("LONG", entry=100.0, sl=97.0, tp=106.0), root)
    p = json.load(open(os.path.join(root, pb.LEDGER)))["positions"]["lab:BTC"]
    assert abs(p["sl"] - 98.0) < 1e-9 and abs(p["tp"] - 107.0) < 1e-9
