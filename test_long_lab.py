"""Tests for long_lab (v8.0): point-in-time features, sealed exam, simulator, planted edge vs noise."""
import math

import numpy as np
import pandas as pd

import long_lab as LL


def _px(n=3200, seed=0, drift=None, vol=0.012, start="2016-01-01"):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, periods=n, freq="D", tz="UTC")
    d = np.zeros(n) if drift is None else drift
    r = d + rng.normal(0, vol, n)
    c = 100 * np.exp(np.cumsum(r))
    o = c * np.exp(-rng.normal(0, vol / 3, n) * 0)           # open = previous close (no gap) unless noted
    o = np.r_[c[0], c[:-1]]
    hi = np.maximum(o, c) * (1 + np.abs(rng.normal(0, vol / 2, n)))
    lo = np.minimum(o, c) * (1 - np.abs(rng.normal(0, vol / 2, n)))
    return pd.DataFrame({"Open": o, "High": hi, "Low": lo, "Close": c}, index=idx)


def _panel(px, values, asset="BTC"):
    """Replay rows decided at D 00:30 (bars <= D-1)."""
    t = px.index + pd.Timedelta("30min")
    df = pd.DataFrame({"asset": asset, "t": t})
    for k, v in values.items():
        df[k] = v
    return df


def test_features_are_point_in_time():
    px = _px(1500, seed=1)
    P = _panel(px, {"sys::score": np.random.default_rng(1).normal(0, 1, len(px))})
    full = LL.build_features(px, P, None)
    part = LL.build_features(px.iloc[:900], P[P["t"] <= px.index[899] + pd.Timedelta("30min")], None)
    for k in part:
        assert np.allclose(np.nan_to_num(full[k][:900], nan=-9), np.nan_to_num(part[k], nan=-9)), k
    # the value used at the open of day k is the replay row decided at day k 00:30 (data <= day k-1)
    assert np.allclose(full["sys::score"], P["sys::score"].values)
    # technical features only use closes up to the previous day
    c = px["Close"]
    assert np.isclose(full["tech:tsmom:20"][100], math.log(c.iloc[99] / c.iloc[79]))


def test_targets_hold_through_the_period():
    px = _px(400, seed=2)
    x = np.random.default_rng(2).normal(0, 1, 400)
    tg = LL.target(x, px.index, 21, "sign", False)
    m = (px.index.month + 100 * px.index.year).values
    for i in range(1, 400):
        if m[i] == m[i - 1]:
            assert tg[i] == tg[i - 1]


def _ref(T, px, k, cost, fund):
    O, H, Lw, C = (px[c].values for c in ("Open", "High", "Low", "Close"))
    n = len(C)
    tr = np.maximum(H - Lw, np.maximum(np.abs(H - np.r_[C[0], C[:-1]]), np.abs(Lw - np.r_[C[0], C[:-1]])))
    atr = pd.Series(tr).rolling(14, min_periods=5).mean().shift(1).values
    pos = ext = blocked = 0.0
    out = np.zeros(n)
    for t in range(1, n):
        r = pos * math.log(O[t] / C[t - 1])
        want = T[t]
        if blocked != 0 and want == blocked:
            want = 0.0
        if T[t] != blocked:
            blocked = 0.0
        if want != pos:
            r -= cost * abs(want - pos)
            ext = O[t]
        a = atr[t] if np.isfinite(atr[t]) else np.inf
        hit = False
        if want > 0 and Lw[t] <= ext - k * a:
            hit, px_ = True, min(O[t], ext - k * a)
        elif want < 0 and H[t] >= ext + k * a:
            hit, px_ = True, max(O[t], ext + k * a)
        if hit:
            r += want * math.log(px_ / O[t]) - cost * abs(want)
        else:
            r += want * math.log(C[t] / O[t])
        if want > 0:
            r -= fund
        if hit:
            blocked, pos = want, 0.0
        else:
            pos = want
            ext = max(ext, H[t]) if pos > 0 else (min(ext, Lw[t]) if pos < 0 else ext)
        out[t] = r
    return out


def test_simulator_matches_reference():
    px = _px(600, seed=3)
    rng = np.random.default_rng(3)
    T = np.repeat(rng.choice([-1.0, 0.0, 1.0], 600 // 10 + 1), 10)[:600]
    for k in (2.0, 3.0, np.inf):
        ex = {"type": "trail", "k": k} if np.isfinite(k) else {"type": "sig"}
        R, _ = LL.simulate(T[None, :], [ex], px, 0.0008, 0.0003)
        assert np.allclose(R[0], _ref(T, px, k, 0.0008, 0.0003)), k


def test_noise_is_not_proven_and_exam_is_sealed():
    px = _px(3300, seed=4)
    rng = np.random.default_rng(404)                 # independent of the price noise
    P = _panel(px, {f"sys::s{i}": rng.normal(0, 1, len(px)) for i in range(6)})
    prices = px.reset_index().rename(columns={"index": "date"}).assign(asset="BTC")
    res = LL.research(prices, P, None)
    r = res["assets"]["BTC"]
    assert not r["proven"], r["chosen"]
    # changing the exam period's data does not change the chosen rule (sealed)
    px2 = px.copy()
    e0 = px.index[-1] - pd.Timedelta(days=LL.HOLDOUT_DAYS)
    px2.loc[px2.index > e0 + pd.Timedelta(days=2), ["Open", "High", "Low", "Close"]] *= 1.3
    P2 = P.copy()
    P2.loc[P2["t"] > e0 + pd.Timedelta(days=2), "sys::s0"] = 5.0
    r2 = LL.research(px2.reset_index().rename(columns={"index": "date"}).assign(asset="BTC"), P2, None)["assets"]["BTC"]
    assert r2["chosen"]["label"] == r["chosen"]["label"] and r2["chosen"]["train"] == r["chosen"]["train"]


def test_planted_slow_signal_is_found_and_passes_the_exam():
    n = 3300
    rng = np.random.default_rng(505)
    regime = np.repeat(rng.choice([-1.0, 1.0], n // 40 + 1), 40)[:n]          # ~6-week regimes
    px = _px(n, seed=5, drift=0.004 * np.r_[0.0, regime[:-1]], vol=0.012)
    P = _panel(px, {"sys::legacy_score": regime + rng.normal(0, 1.5, n), "sys::noise": rng.normal(0, 1, n)}, "XAU")
    res = LL.research(px.reset_index().rename(columns={"index": "date"}).assign(asset="XAU"), P, None)
    r = res["assets"]["XAU"]
    # the regimes also make prices trend, so momentum may legitimately win; the planted signal must be among the best
    planted = [t for t in r["top"] if "Makro model skoru" in t["label"]]
    assert planted and max(t["exam"] for t in planted) > 1.0, r["top"][:5]
    assert r["proven"], (r["chosen"], r["wf"], r["ok"])
    md = LL.report_md(res)
    assert "mühürlü" in md and "XAU" in md
