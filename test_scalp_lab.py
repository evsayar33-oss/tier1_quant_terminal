"""Tests for scalp_lab (v10.0): trade simulator, no look-ahead, noise vs planted intraday edge."""
import math

import numpy as np
import pandas as pd

import scalp_lab as S


def _bars(n=20000, seed=0, ar=0.0, start="2022-01-01", ou=0.0, rw=0.002):
    rng = np.random.default_rng(seed)
    t = pd.date_range(start, periods=n, freq="5min", tz="UTC").as_unit("ms").asi8.astype(float)
    e = rng.normal(0, rw, n)
    r = np.zeros(n)
    for i in range(1, n):
        r[i] = ar * r[i - 1] + e[i]
    x = np.zeros(n)
    if ou:                                                    # planted intraday edge: price oscillates around a slow mean
        k = rng.normal(0, 0.008, n)
        for i in range(1, n):
            x[i] = x[i - 1] * (1 - ou) + k[i]
    c = 100 * np.exp(np.cumsum(r) + x)
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, 0.0005, n)))
    l = np.minimum(o, c) * (1 - np.abs(rng.normal(0, 0.0005, n)))
    v = rng.uniform(100, 200, n)
    tb = v * rng.uniform(0.3, 0.7, n)
    return np.column_stack([t, o, h, l, c, v, tb])


def test_trade_simulator_by_hand():
    o = np.array([100, 100, 100, 100, 100, 100.0])
    h = np.array([100, 100.5, 102.5, 100, 100, 100.0])
    l = np.array([100, 99.5, 99.0, 100, 100, 100.0])
    c = np.array([100, 100, 101, 100, 100, 100.0])
    atr = np.ones(6) * 2.0
    sig = np.array([1, 0, 0, 0, 0, 0], np.int8)
    ok = np.ones(6, bool)
    # long at o[1]=100, tp = 100+1*2 = 102, sl = 100-1*2 = 98 -> bar 2 high 102.5 hits tp
    ei, ret, sd = S._trades(sig, ok, o, h, l, c, atr, 1.0, 1.0, 10, 0.0)
    assert list(ei) == [2] and math.isclose(ret[0], 0.02)
    # same bar touches both stop and target -> the STOP is assumed first
    l2 = l.copy(); l2[2] = 97.0
    ei, ret, _ = S._trades(sig, ok, o, h, l2, c, atr, 1.0, 1.0, 10, 0.001)
    assert math.isclose(ret[0], -0.02 - 0.002)
    # time stop: exit at the close of the last allowed bar
    ei, ret, _ = S._trades(sig, ok, o, np.full(6, 100.4), np.full(6, 99.6), c, atr, 1.0, 1.0, 2, 0.0)
    assert list(ei) == [2] and math.isclose(ret[0], 0.01)


def test_signals_use_only_closed_bars():
    a = _bars(6000, seed=1)
    F1, F2 = S.features(a), S.features(a[:4000])
    for cfg in S.configs()[:13]:
        s1, s2 = S.signal(F1, cfg), S.signal(F2, cfg)
        assert np.array_equal(s1[:4000], s2), cfg


def _run(ar, seed, n_sym=3, ou=0.0, rw=0.002):
    U = {}
    data = {}
    for k in range(n_sym):
        a = _bars(110_000, seed=seed + k, ar=ar, ou=ou, rw=rw)           # ~380 days
        data[f"S{k}USDT"] = a
    months = pd.period_range("2022-01", "2023-01", freq="M")
    U = {str(m): list(data) for m in months}
    cfgs = [c for c in S.configs() if c["fam"] == "mr" and c["hold"] == 24 and c["sl"] == 2.0 and not c["trend"]]
    old = S.HOLDOUT_DAYS
    S.HOLDOUT_DAYS = 120
    try:
        return S.research(U, data, cfgs)
    finally:
        S.HOLDOUT_DAYS = old


def test_noise_has_no_edge_after_costs():
    r = _run(0.0, 10)
    assert r["chosen"]["exam"] < 1.5 and not r["proven"]
    assert all(f["exam_mean"] < 0 for f in r["families"])               # random walk + 0.14% round trip = loss


def test_planted_intraday_mean_reversion_is_found():
    r = _run(0.0, 20, ou=0.05, rw=0.0005)
    fam = {f["family"]: f for f in r["families"]}
    assert fam["Ortalamaya dönüş (z)"]["exam_mean"] > 2.0, fam
    assert "mühürlü" in S.report_md(r)
