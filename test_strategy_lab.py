"""Tests for strategy_lab v5 (perps): no look-ahead, exact vectorised simulator,
honest selection, system-signal alignment, leverage/liquidation."""
import json
import math

import numpy as np
import pandas as pd

import strategy_lab as L


def _ohlc(n=3000, freq="1h", drift=0.0, ar=0.0, seed=0, vol=0.004, end=None, start="2024-10-01"):
    rng = np.random.default_rng(seed)
    e = rng.normal(0, vol, n)
    r = np.zeros(n)
    for t in range(1, n):
        r[t] = drift + ar * r[t - 1] + e[t]
    c = 100 * np.exp(np.cumsum(r))
    o = np.concatenate([[c[0]], c[:-1]])
    wig = np.abs(rng.normal(0, vol / 2, n)) * c
    idx = (pd.date_range(end=end, periods=n, freq=freq, tz="UTC") if end is not None
           else pd.date_range(start, periods=n, freq=freq, tz="UTC"))
    return pd.DataFrame({"Open": o, "High": np.maximum(o, c) + wig, "Low": np.minimum(o, c) - wig, "Close": c}, index=idx)


def _panel_from(h, col_values, asset="BTC", step_h=2):
    """A system panel sampled every 2h: decision time t = close of the bar starting at t-1h."""
    ts = h.index[::step_h] + pd.Timedelta(hours=1)
    df = pd.DataFrame({"asset": asset, "t": ts})
    for k, v in col_values.items():
        df[k] = np.asarray(v)[::step_h][:len(ts)]
    return df


# ---------------------------------------------------------------- reference simulator
def _ref_sim(p, ex, atr, O, H, Lw, C, cost, fund):
    """Plain scalar implementation of the same rules (for cross-checking)."""
    T = len(C)
    r = np.zeros(T)
    cur = 0.0; blocked = 0.0; sl = tp = np.nan; ext = 0.0; ae = 0.0; held = 0
    et = ex["type"]
    for t in range(1, T):
        ps = cur
        f = fund * ps if ps > 0 else 0.0
        rt = ps * math.log(C[t] / C[t - 1]) - f
        if ps != 0 and et in ("sltp", "trail", "time"):
            hit_sl = et in ("sltp", "trail") and ((ps > 0 and Lw[t] <= sl) or (ps < 0 and H[t] >= sl))
            hit_tp = et == "sltp" and not hit_sl and ((ps > 0 and H[t] >= tp) or (ps < 0 and Lw[t] <= tp))
            if hit_sl or hit_tp:
                px = (min(O[t], sl) if ps > 0 else max(O[t], sl)) if hit_sl else tp
                rt = ps * math.log(px / C[t - 1]) - cost * abs(ps) - f
                blocked, cur = ps, 0.0
            else:
                if et == "trail":
                    if ps > 0:
                        ext = max(ext, H[t]); sl = max(sl, ext - ex["k1"] * ae)
                    else:
                        ext = min(ext, Lw[t]); sl = min(sl, ext + ex["k1"] * ae)
                held += 1
                if et == "time" and held >= ex["h"]:
                    rt -= cost * abs(ps)
                    blocked, cur = ps, 0.0
        raw = float(p[t])
        want = raw
        if blocked != 0:
            if raw == blocked:
                want = 0.0
            else:
                blocked = 0.0
        if want != cur:
            rt -= cost * abs(cur) + cost * abs(want)
            if want != 0:
                a = atr[t]
                sl = C[t] - want * ex.get("k1", 0) * a if et in ("sltp", "trail") else np.nan
                tp = C[t] + want * ex.get("k2", 0) * a if et == "sltp" else np.nan
                ext, ae, held = C[t], a, 0
            cur = want
        r[t] = rt
    return r


def test_vectorised_simulator_matches_reference():
    h = _ohlc(1500, seed=7, vol=0.006)
    ctx = L.Ctx(h)
    arr, _ = L._slice_ctx(ctx, 0, ctx.T)
    rng = np.random.default_rng(1)
    P, ex = [], []
    for e in L.EXITS:
        for _ in range(3):
            raw = np.repeat(rng.choice([-1, 0, 1], size=ctx.T // 10 + 1), 10)[:ctx.T]
            P.append(raw.astype(np.int8)); ex.append(e)
    P = np.vstack(P)
    day_idx = np.arange(ctx.T)                       # one "day" per bar -> R == hourly returns
    out = L.simulate_batch(P, ex, np.full(len(P), 0), arr, 0.001, day_idx, ctx.T, fund_long=1e-5)
    for i in range(len(P)):
        ref = _ref_sim(P[i], ex[i], arr["ATR"][0], arr["O"], arr["H"], arr["L"], arr["C"], 0.001, 1e-5)
        assert np.allclose(out["R"][i], ref, atol=1e-6), (i, ex[i])


def test_technical_features_have_no_lookahead():
    h = _ohlc(3000, seed=2)
    d = _ohlc(400, freq="1D", seed=3, vol=0.02, end=str(h.index[-1].date()))
    full = L.Ctx(h, d)
    part = L.Ctx(h.iloc[:2000], d[d.index <= h.index[1999]])
    for k in full.feat:
        assert np.array_equal(full.feat[k][:2000], part.feat[k]), k


def test_system_panel_is_used_only_after_its_decision_time():
    h = _ohlc(400, seed=4)
    vals = np.arange(400, dtype=float) - 200          # increasing, two-sided
    P = _panel_from(h, {"sys::score": vals})
    ctx = L.Ctx(h, None, P)
    x = ctx.feat["sys::score"]
    # bar i closes at idx[i]+1h; the panel row with t == idx[i]+1h is usable at bar i, never earlier
    for i in range(10, 390):
        t_close = h.index[i] + pd.Timedelta(hours=1)
        avail = P[P["t"] <= t_close]["sys::score"].iloc[-1]
        assert x[i] == avail


def test_random_walk_gives_no_proven_rule():
    data, panels = {}, []
    for k, a in enumerate(["SPX", "BTC"]):
        h = _ohlc(8000, seed=10 + k)
        rng = np.random.default_rng(50 + k)
        noise = {"sys::score": rng.normal(0, 1, len(h)), "cat::verdict": rng.choice([-1.0, 0.0, 1.0], len(h)),
                 "sys::entry_allowed": rng.choice([0.0, 1.0], len(h))}
        panels.append(_panel_from(h, noise, a))
        data[a] = {"1h": h}
    old = L.EXITS
    L.EXITS = old[:3]
    try:
        res = L.research(data, pd.concat(panels), source="test")
    finally:
        L.EXITS = old
    for a, r in res["assets"].items():
        assert not r["proven"] and r["kind"] is None, (a, r["wf"], r["best"]["label"])


def test_planted_system_signal_is_found_and_proven():
    """A system output that really predicts the next hours must be found,
    survive walk-forward and beat holding (alpha)."""
    rng = np.random.default_rng(11)
    n = 9000
    sig = np.repeat(rng.choice([-1.0, 1.0], n // 12 + 1), 12)[:n]       # regime of the 'model'
    r = np.concatenate([[0.0], 0.0012 * sig[:-1] + rng.normal(0, 0.004, n - 1)])
    c = 100 * np.exp(np.cumsum(r))
    o = np.concatenate([[c[0]], c[:-1]])
    idx = pd.date_range("2024-11-01", periods=n, freq="h", tz="UTC")
    h = pd.DataFrame({"Open": o, "High": np.maximum(o, c) * 1.0005, "Low": np.minimum(o, c) * 0.9995, "Close": c}, index=idx)
    P = _panel_from(h, {"cat::verdict": sig, "sys::score": sig * 0.5 + rng.normal(0, 0.1, n)}, "BTC", step_h=1)
    old = L.EXITS
    L.EXITS = old[:2]
    try:
        res = L.research({"BTC": {"1h": h}}, P, source="test")
    finally:
        L.EXITS = old
    r_ = res["assets"]["BTC"]
    assert r_["kind"] == "alpha" and r_["path"] == "A", (r_["wf"], r_["wf_alpha_t"], r_["best"]["label"])
    assert "Model" in r_["best"]["label"] or "skor" in r_["best"]["label"].lower(), r_["best"]["label"]


def test_long_beta_is_not_alpha():
    """Rising market, no predictability: holding long beats cash, but no rule may be called alpha."""
    h = _ohlc(9000, seed=21, drift=0.0004, vol=0.004)
    rng = np.random.default_rng(3)
    P = _panel_from(h, {"sys::score": rng.normal(0.5, 1, len(h))}, "SPX")
    old = L.EXITS
    L.EXITS = old[:2]
    try:
        res = L.research({"SPX": {"1h": h}}, P, source="test")
    finally:
        L.EXITS = old
    assert res["assets"]["SPX"]["kind"] != "alpha"


def test_deflated_sharpe_and_effective_trials():
    rng = np.random.default_rng(1)
    x = rng.normal(0.001, 0.01, 700)
    assert L.deflated_sharpe(x, 1000) < L.deflated_sharpe(x, 2)
    base = rng.normal(0, 0.01, 700)
    R = np.vstack([base + rng.normal(0, 0.0005, 700) for _ in range(50)])
    assert L.n_effective(R) < 3
    R2 = rng.normal(0, 0.01, (300, 700))
    assert L.n_effective(R2) > 100


def test_alpha_t():
    rng = np.random.default_rng(3)
    b = rng.normal(0.0005, 0.01, 2000)
    assert abs(L.alpha_t(0.8 * b + rng.normal(0, 0.005, 2000), b)[2]) < 2.5
    assert L.alpha_t(0.5 * b + rng.normal(0.002, 0.005, 2000), b)[2] > 5


def test_leverage_liquidates_on_adverse_move():
    n = 50
    C = np.full(n, 100.0); H = C.copy(); Lw = C.copy()
    Lw[20] = 88.0                                    # -12% wick while long
    pos = np.zeros(n); pos[10:40] = 1
    ent = np.where(pos != 0, 100.0, 0.0)
    hr = np.zeros(n)
    rows = {r["lev"]: r for r in L.leverage_table(hr, pos, ent, H, Lw, C, 8760, 1.0)}
    assert rows[1]["liquidations"] == 0 and rows[5]["liquidations"] == 0
    assert rows[10]["liquidations"] == 1 and rows[10]["final"] < 0.1


def test_playbook_roundtrip_and_live_signal():
    h = _ohlc(6000, seed=5, ar=0.3)
    P = _panel_from(h, {"sys::score": np.random.default_rng(1).normal(0, 1, len(h))})
    old = L.EXITS
    L.EXITS = old[:2]
    try:
        res = L.research({"BTC": {"1h": h}}, P, source="test")
    finally:
        L.EXITS = old
    pb = json.loads(json.dumps(L.playbook(res)))
    live = L.live_signals(pb, {"BTC": {"1h": h}}, P)
    assert live["BTC"]["fresh"] and live["BTC"]["side"] in ("LONG", "SHORT", "FLAT")
    md = L.report_md(res)
    assert "Kaldıraç" in md and "Sistemin kendi sinyalleri" in md


def test_stops_create_no_profit_on_a_random_walk():
    """Stop/target/trailing logic must not manufacture an edge (look-ahead in fills).
    Zero cost, no predictability: averaged over seeds and rules, every exit type
    must perform like the plain signal exit (the first v5 preview bug lifted a
    trailing stop by +4.6 Sharpe on wick-less bars)."""
    diffs = {wick: {i: [] for i in range(1, len(L.EXITS))} for wick in (False, True)}
    for seed in range(4):
        rng = np.random.default_rng(seed)
        n = 8000
        c = 100 * np.exp(np.cumsum(rng.normal(0, 0.007, n)))
        o = np.concatenate([[c[0]], c[:-1]])
        idx = pd.date_range("2024-11-01", periods=n, freq="h", tz="UTC")
        days = pd.date_range(idx[0].normalize(), idx[-1].normalize(), freq="D", tz="UTC")
        di = days.get_indexer(idx.normalize())
        for wick in (False, True):
            if wick:
                hi = np.maximum(o, c) * (1 + np.abs(rng.normal(0, 0.003, n)))
                lo = np.minimum(o, c) * (1 - np.abs(rng.normal(0, 0.003, n)))
            else:
                hi, lo = np.maximum(o, c), np.minimum(o, c)
            ctx = L.Ctx(pd.DataFrame({"Open": o, "High": hi, "Low": lo, "Close": c}, index=idx))
            arr, _ = L._slice_ctx(ctx, 0, ctx.T)
            for src in ("tech:1h:macd:12-26-9", "tech:1h:ema_trend:50", "tech:4h:tsmom:42"):
                p = ctx.position({"d": {"src": src, "op": "sign"}, "f": None, "mode": "LS"})
                out = L.simulate_batch(np.vstack([p] * len(L.EXITS)), L.EXITS, np.zeros(len(L.EXITS), dtype=int), arr,
                                       0.0, di, len(days))
                s = [L.sharpe(out["R"][k]) for k in range(len(L.EXITS))]
                for k in range(1, len(L.EXITS)):
                    diffs[wick][k].append(s[k] - s[0])
    for wick, d in diffs.items():
        for k, v in d.items():
            assert np.mean(v) < 0.5, (wick, L.EXITS[k], np.round(v, 2))
