"""Tests for strategy_lab (v4.0): no look-ahead, honest selection, stop logic."""
import math

import numpy as np
import pandas as pd

import strategy_lab as L


def _ohlc(n=3000, freq="1h", drift=0.0, ar=0.0, seed=0, vol=0.004, end=None):
    rng = np.random.default_rng(seed)
    e = rng.normal(0, vol, n)
    r = np.zeros(n)
    for t in range(1, n):
        r[t] = drift + ar * r[t - 1] + e[t]
    c = 100 * np.exp(np.cumsum(r))
    o = np.concatenate([[c[0]], c[:-1]])
    wig = np.abs(rng.normal(0, vol / 2, n)) * c
    idx = (pd.date_range(end=end, periods=n, freq=freq, tz="UTC") if end is not None
           else pd.date_range("2024-10-01", periods=n, freq=freq, tz="UTC"))
    return pd.DataFrame({"Open": o, "High": np.maximum(o, c) + wig, "Low": np.minimum(o, c) - wig, "Close": c}, index=idx)


def test_signals_have_no_lookahead():
    df = _ohlc(800)
    for tf in ("1h",):
        for c in L.configs_for(tf):
            if c.get("stop"):
                continue
            full = L.signal(c, df)
            for cut in (400, 650):
                part = L.signal(c, df.iloc[:cut])
                assert np.array_equal(full[:cut], part), L.cfg_id(c)


def test_simulation_has_no_lookahead_with_stops():
    df = _ohlc(800, seed=3)
    c = {"tf": "1h", "fam": "tsmom", "p": 24, "mode": "LS", "stop": (1.5, 3.0)}
    full = L.simulate(c, df, 0.001)
    part = L.simulate(c, df.iloc[:500], 0.001)
    assert np.allclose(full["r"][:500], part["r"]) and np.array_equal(full["pos"][:500], part["pos"])


def test_stop_is_assumed_before_target_and_blocks_reentry():
    idx = pd.date_range("2025-01-01", periods=40, freq="1h", tz="UTC")
    c = np.full(40, 100.0)
    df = pd.DataFrame({"Open": c, "High": c + 0.5, "Low": c - 0.5, "Close": c}, index=idx)
    df.iloc[30, df.columns.get_loc("High")] = 200.0
    df.iloc[30, df.columns.get_loc("Low")] = 50.0
    sig = np.zeros(40)
    sig[20:] = 1.0
    cfg = {"tf": "1h", "fam": "tsmom", "p": 1, "mode": "LS", "stop": (2.0, 4.0)}
    s = L.simulate(cfg, df, 0.0, sig)
    assert s["pos"][29] == 1 and s["pos"][30] == 0 and s["pos"][39] == 0      # stopped, stays out
    assert s["r"][30] < 0                                                    # loss, not the target


def test_random_walk_is_not_proven():
    data = {}
    for k, a in enumerate(["SPX", "BTC"]):
        h = _ohlc(17000, seed=10 + k)
        data[a] = {"1h": h, "4h": L._resample_4h(h), "1d": _ohlc(2500, freq="1D", seed=20 + k, vol=0.015, end="2026-08-10")}
    res = L.research(data, source="test")
    for a, r in res["assets"].items():
        assert not r["proven"], (a, r["wf"], r["best"])
        assert r["best"]["dsr"] < 0.9


def test_planted_trend_is_found():
    data = {}
    h = _ohlc(17000, ar=0.35, seed=5)                  # strong persistence in hourly returns
    data["BTC"] = {"1h": h, "4h": L._resample_4h(h), "1d": _ohlc(2500, freq="1D", seed=6, vol=0.015, end="2026-08-10")}
    res = L.research(data, source="test")
    r = res["assets"]["BTC"]
    assert r["best"]["cfg"]["tf"] == "1h" and r["wf"]["sharpe"] > 1.0 and r["proven"], (r["best"], r["wf"])


def test_deflated_sharpe_penalises_many_trials():
    rng = np.random.default_rng(1)
    x = rng.normal(0.001, 0.01, 700)
    assert L.deflated_sharpe(x, 1000) < L.deflated_sharpe(x, 2)
    # 50 copies of the same idea count as ~1 trial
    base = rng.normal(0, 0.01, 700)
    R = np.vstack([base + rng.normal(0, 0.0005, 700) for _ in range(50)])
    assert L.n_effective(R) < 3


def test_playbook_and_live_signals_roundtrip():
    h = _ohlc(17000, ar=0.25, seed=5)
    data = {"BTC": {"1h": h, "4h": L._resample_4h(h), "1d": _ohlc(2500, freq="1D", seed=6, vol=0.015, end="2026-08-10")}}
    res = L.research(data, source="test")
    import json
    pb = json.loads(json.dumps(L.playbook(res), default=str))
    live = L.live_signals(pb, data)
    assert live["BTC"]["side"] == res["assets"]["BTC"]["signal"]["side"] and live["BTC"]["fresh"]
    assert "Strateji Laboratuvarı" in L.report_md(res)


def test_long_daily_history_path_b():
    h = _ohlc(17000, seed=11)
    d = _ohlc(3650, freq="1D", seed=12, vol=0.02, ar=0.25, end=str(h.index[-1].date()))
    res = L.research({"XAU": {"1h": h, "4h": L._resample_4h(h), "1d": d}}, source="test")
    r = res["assets"]["XAU"]
    assert r["path"] == "B" and r["best"]["cfg"]["tf"] == "1d" and r["proven"]


def test_long_only_beta_in_bull_market_is_not_alpha():
    """Strong drift, no predictability: long-only rules beat cash but not holding."""
    h = _ohlc(17000, seed=31)
    d = _ohlc(3650, freq="1D", seed=32, vol=0.012, drift=0.0012, end=str(h.index[-1].date()))
    res = L.research({"SPX": {"1h": h, "4h": L._resample_4h(h), "1d": d}}, source="test")
    r = res["assets"]["SPX"]
    assert not r["proven"], (r["kind"], r["checks_b"], r["long"])


def test_alpha_t_detects_excess_over_benchmark():
    rng = np.random.default_rng(3)
    b = rng.normal(0.0005, 0.01, 2000)
    assert abs(L.alpha_t(0.8 * b + rng.normal(0, 0.005, 2000), b)[2]) < 2.5   # pure beta -> no alpha
    assert L.alpha_t(0.5 * b + rng.normal(0.002, 0.005, 2000), b)[2] > 5
