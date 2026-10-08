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
def _ref_sim(p, ex, atr, O, H, Lw, C, cost, fund, atrm=None):
    """Plain scalar implementation of the same exit rules (for cross-checking)."""
    T = len(C)
    r = np.zeros(T)
    cur = 0.0; blocked = 0.0; sl = tp = np.nan; ext = 0.0; ae = 0.0; held = 0; entry = 0.0
    part_done = be_done = False
    et = ex["type"]
    k1, k2, k3, bk = ex.get("k1", 0), ex.get("k2", 0), ex.get("k3", 0), ex.get("b", 0)
    for t in range(1, T):
        ps = cur
        side = np.sign(ps); size = abs(ps)
        f = fund * ps if ps > 0 else 0.0
        lr = math.log(C[t] / C[t - 1])
        rt = ps * lr - f
        if ps != 0 and et != "sig":
            has_sl = et in ("sltp", "trail", "be", "part", "vol")
            has_tp = et in ("sltp", "be", "part", "vol")
            hit_sl = has_sl and ((ps > 0 and Lw[t] <= sl) or (ps < 0 and H[t] >= sl))
            hit_tp = has_tp and not hit_sl and ((ps > 0 and H[t] >= tp) or (ps < 0 and Lw[t] <= tp))
            closed = False
            half = hit_tp and et == "part" and not part_done
            if hit_sl or (hit_tp and not half):
                px = (min(O[t], sl) if ps > 0 else max(O[t], sl)) if hit_sl else tp
                rt = ps * math.log(px / C[t - 1]) - cost * size - f
                closed = True
            elif half:
                tpx = max(O[t], tp) if ps > 0 else min(O[t], tp)
                if (ps > 0 and Lw[t] <= entry) or (ps < 0 and H[t] >= entry):
                    rt = 0.5 * side * math.log(tpx / C[t - 1]) + 0.5 * side * math.log(entry / C[t - 1]) - cost - f
                    closed = True
                else:
                    rt = 0.5 * side * math.log(tpx / C[t - 1]) + 0.5 * side * lr - 0.5 * cost - f
                    part_done = True
                    cur = side * 0.5
                    sl = entry
                    ext = H[t] if ps > 0 else Lw[t]
                    tp = np.nan
            if not closed:
                if et == "be" and not be_done and ((ps > 0 and H[t] >= entry + bk * ae) or (ps < 0 and Lw[t] <= entry - bk * ae)):
                    be_done = True
                    sl = max(sl, entry) if ps > 0 else min(sl, entry)
                if (et == "trail" or (et == "part" and part_done)) and not half:
                    kt = k1 if et == "trail" else k3
                    if ps > 0:
                        ext = max(ext, H[t]); sl = max(sl, ext - kt * ae)
                    else:
                        ext = min(ext, Lw[t]); sl = min(sl, ext + kt * ae)
                held += 1
                if et == "time" and held >= ex["h"]:
                    rt -= cost * size
                    closed = True
            if closed:
                blocked, cur = side, 0.0
        raw = float(p[t])
        want = raw
        if blocked != 0:
            if raw == blocked:
                want = 0.0
            else:
                blocked = 0.0
        if want != np.sign(cur):
            rt -= cost * abs(cur) + cost * abs(want)
            if want != 0:
                a = atr[t]
                k2e = k2 * min(max(a / atrm[t], 0.5), 2.0) if (et == "vol" and atrm is not None and atrm[t] > 0) else k2
                sl = C[t] - want * k1 * a if et in ("sltp", "trail", "be", "part", "vol") else np.nan
                tp = C[t] + want * k2e * a if et in ("sltp", "be", "part", "vol") else np.nan
                ext, ae, held, entry = C[t], a, 0, C[t]
            part_done = be_done = False
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
        ref = _ref_sim(P[i], ex[i], arr["ATR"][0], arr["O"], arr["H"], arr["L"], arr["C"], 0.001, 1e-5, arr["ATRM"][0])
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


def _small(fn):
    old_e, old_c, old_k = L.EXITS, L.CADENCES, L.DISC_K
    L.EXITS, L.CADENCES, L.DISC_K = old_e[:2], (1, 24, 168), 12
    try:
        return fn()
    finally:
        L.EXITS, L.CADENCES, L.DISC_K = old_e, old_c, old_k


def test_cadence_holds_position_between_rebalances_and_no_lookahead():
    h = _ohlc(3000, seed=1)
    ctx = L.Ctx(h)
    for cad in (4, 24, 168):
        d = {"src": "tech:1h:ema_trend:50", "op": "z", "thr": 0.5, "cad": cad, "smooth": True}
        x = ctx.direction(d)
        b = ctx.close_h // cad
        assert all(x[i] == x[i - 1] for i in range(1, len(x)) if b[i] == b[i - 1])
        assert np.array_equal(L.Ctx(h.iloc[:2200]).direction(d), x[:2200])


def test_slow_macro_signal_is_found_at_the_weekly_horizon():
    """A signal that predicts the NEXT WEEKS (noisy hour to hour) must be found
    at the weekly horizon even though it is useless at 1h."""
    rng = np.random.default_rng(4)
    n = 12000
    regime = np.repeat(rng.choice([-1.0, 1.0], n // 336 + 1), 336)[:n]          # 2-week regimes
    r = np.concatenate([[0.0], 0.0009 * regime[:-1] + rng.normal(0, 0.006, n - 1)])
    c = 100 * np.exp(np.cumsum(r)); o = np.concatenate([[c[0]], c[:-1]])
    idx = pd.date_range("2024-11-01", periods=n, freq="h", tz="UTC")
    h = pd.DataFrame({"Open": o, "High": np.maximum(o, c) * 1.001, "Low": np.minimum(o, c) * 0.999, "Close": c}, index=idx)
    noisy = regime + rng.normal(0, 3.0, n)                                    # hourly value is mostly noise
    P = _panel_from(h, {"sys::legacy_score": noisy}, "XAU", step_h=1)
    res = _small(lambda: L.research({"XAU": {"1h": h}}, P, source="test"))
    hz = {r["src"]: r for r in res["horizon"]["rows"]}["sys::legacy_score"]
    assert hz["168"] > hz["1"] + 1.0, hz
    assert res["assets"]["XAU"]["kind"] == "alpha", (res["assets"]["XAU"]["path"], res["assets"]["XAU"]["wf"])


def test_combination_discovery_finds_a_pair_and_respects_holdout():
    """Two signals that only work TOGETHER; plus pure-noise data must not pass the holdout."""
    rng = np.random.default_rng(8)
    n = 12000
    a = np.repeat(rng.choice([-1.0, 1.0], n // 24 + 1), 24)[:n]
    b = np.repeat(rng.choice([-1.0, 1.0], n // 24 + 1), 24)[:n]
    edge = np.where(a == b, a, 0.0)                                             # moves only when both agree
    r = np.concatenate([[0.0], 0.0015 * edge[:-1] + rng.normal(0, 0.005, n - 1)])
    c = 100 * np.exp(np.cumsum(r)); o = np.concatenate([[c[0]], c[:-1]])
    idx = pd.date_range("2024-11-01", periods=n, freq="h", tz="UTC")
    h = pd.DataFrame({"Open": o, "High": np.maximum(o, c) * 1.001, "Low": np.minimum(o, c) * 0.999, "Close": c}, index=idx)
    P = _panel_from(h, {"sys::score": a + rng.normal(0, 0.05, n), "sys::live_score": b + rng.normal(0, 0.05, n)}, "BTC", step_h=1)
    res = _small(lambda: L.research({"BTC": {"1h": h}}, P, source="test"))
    combo = res["assets"]["BTC"]["combo"]
    assert combo and combo["chosen"]["d3"] > 1.0, combo and combo["chosen"]
    # noise
    rng = np.random.default_rng(9)
    h2 = _ohlc(12000, seed=9)
    P2 = _panel_from(h2, {"sys::score": rng.normal(0, 1, 12000), "sys::live_score": rng.normal(0, 1, 12000)}, "SPX")
    res2 = _small(lambda: L.research({"SPX": {"1h": h2}}, P2, source="test"))
    assert not res2["assets"]["SPX"]["combo"]["passed"] and res2["assets"]["SPX"]["kind"] is None


def _flat_bars(n=40, px=100.0):
    """Flat at 100 (ATR = 1) until bar 20 (entry at its close), then drifting just above the entry price."""
    idx = pd.date_range("2025-01-01", periods=n, freq="1h", tz="UTC")
    c = np.where(np.arange(n) <= 20, px, px + 0.6)
    o = np.concatenate([[c[0]], c[:-1]])
    hi = np.where(np.arange(n) <= 20, c + 0.5, np.maximum(o, c) + 0.2)
    lo = np.where(np.arange(n) <= 20, c - 0.5, np.minimum(o, c) - 0.2)
    return pd.DataFrame({"Open": o, "High": hi, "Low": lo, "Close": c}, index=idx)


def _run_one(df, sig, ex):
    ctx = L.Ctx(df)
    arr, _ = L._slice_ctx(ctx, 0, ctx.T)
    return L.simulate_batch(sig[None, :].astype(np.int8), [ex], np.array([0]), arr, 0.0, np.arange(ctx.T), ctx.T,
                            fund_long=0.0, keep_hourly=True)


def test_partial_take_profit_closes_half_then_trails():
    df = _flat_bars()
    df.iloc[25, df.columns.get_loc("High")] = 102.5          # entry 100, ATR 1 -> TP1 at 102 is hit at bar 25
    sig = np.zeros(len(df)); sig[20:] = 1
    o = _run_one(df, sig, {"type": "part", "k1": 2.0, "k2": 2.0, "k3": 3.0})
    assert o["pos"][0][24] == 1 and o["pos"][0][25] == 0.5            # half closed at the target
    assert o["state"]["sl"][0] >= 100.0                                 # rest protected at breakeven or better


def test_breakeven_moves_stop_to_entry():
    df = _flat_bars()
    df.iloc[24, df.columns.get_loc("High")] = 101.2           # +1.2 ATR -> breakeven armed (b = 1)
    df.iloc[27, df.columns.get_loc("Low")] = 99.8             # back below entry -> stopped at entry, not at -2 ATR
    sig = np.zeros(len(df)); sig[20:] = 1
    o = _run_one(df, sig, {"type": "be", "k1": 2.0, "k2": 4.0, "b": 1.0})
    assert o["pos"][0][26] == 1 and o["pos"][0][27] == 0
    assert abs(o["hourly"][0][27] - math.log(100.0 / 100.6)) < 1e-9   # filled at the entry price, not at -2 ATR


# ---------------------------------------------------------------- v7: filter + trigger, alternative data
def test_trigger_features_have_no_lookahead():
    h = _ohlc(3000, seed=11)
    d = h.resample("1D").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"})
    full = L.Ctx(h, d)
    part = L.Ctx(h.iloc[:2200], d[d.index + pd.Timedelta(days=1) <= h.index[2199] + pd.Timedelta(hours=1)])
    for k in [k for k in full.feat if k.startswith("trig:")]:
        assert np.array_equal(full.feat[k][:2200], part.feat[k]), k
        assert np.abs(full.feat[k]).sum() > 0, k                       # every trigger fires at least once
    rule = {"trig": "trig:4h:rsi2", "hold": 48, "bias": {"src": "tech:1d:ema_trend:50", "op": "sign", "cad": 24, "smooth": True}}
    assert np.array_equal(full.direction(rule)[:2200], part.direction(rule))


def test_trigger_is_taken_only_in_the_bias_direction():
    h = _ohlc(3000, seed=12)
    ctx = L.Ctx(h)
    base = ctx.direction({"trig": "trig:1h:rsi2", "hold": 12, "bias": None})
    bias = {"src": "tech:1d:ema_trend:20", "op": "sign"}
    filt = ctx.direction({"trig": "trig:1h:rsi2", "hold": 12, "bias": bias})
    b = ctx.direction(bias)
    assert np.all((filt == 0) | (filt == base))                        # the filter only removes trades
    assert np.all((filt == 0) | (np.sign(filt) == np.sign(b)))         # never against the system
    assert (filt != 0).sum() < (base != 0).sum()


def test_system_filter_adds_value_to_a_trigger():
    """Price drifts in the direction of a slow system regime; a mean-reversion trigger is
    random without it. The filter must show a positive lift in BOTH halves."""
    rng = np.random.default_rng(21)
    n = 9000
    regime = np.repeat(rng.choice([-1.0, 1.0], n // 336 + 1), 336)[:n]
    r = np.concatenate([[0.0], 0.0006 * regime[:-1] + rng.normal(0, 0.005, n - 1)])
    c = 100 * np.exp(np.cumsum(r)); o = np.concatenate([[c[0]], c[:-1]])
    idx = pd.date_range("2024-11-01", periods=n, freq="h", tz="UTC")
    h = pd.DataFrame({"Open": o, "High": np.maximum(o, c) * 1.002, "Low": np.minimum(o, c) * 0.998, "Close": c}, index=idx)
    P = _panel_from(h, {"sys::legacy_score": regime + rng.normal(0, 0.3, n)}, "XAU", step_h=1)
    res = _small(lambda: L.research({"XAU": {"1h": h}}, P, source="test"))
    tg = res["trigger"]
    row = [b for b in tg["biases"] if b["src"] == "sys::legacy_score"]
    assert row and max(b["lift"] for b in row) > 0.5, row
    assert max(b["lift1"] for b in row) > 0 and max(b["lift2"] for b in row) > 0
    assert "3b)" in L.report_md(res)


def _alt_frame(h, values, lag_h=30, asset="BTC", col="alt::premium"):
    days = pd.date_range(h.index[0].normalize(), h.index[-1].normalize(), freq="D", tz="UTC")
    return pd.DataFrame({"asset": asset, "t": days + pd.Timedelta(hours=lag_h), col: np.asarray(values)[:len(days)]})


def test_alt_data_is_used_only_after_it_became_known_and_goes_stale():
    h = _ohlc(24 * 90, seed=13)
    days = pd.date_range(h.index[0].normalize(), h.index[-1].normalize(), freq="D", tz="UTC")
    A = _alt_frame(h, np.arange(len(days), dtype=float) + 1.0)
    cot = pd.DataFrame({"asset": "BTC", "t": pd.date_range(h.index[0].normalize() - pd.Timedelta(weeks=20), periods=28, freq="7D",
                                                           tz="UTC") + pd.Timedelta(days=4),
                        "alt::cot_lev_net": np.linspace(-0.2, 0.2, 28)})
    ctx = L.Ctx(h, None, None, pd.concat([A, cot], ignore_index=True))
    close_t = h.index + pd.Timedelta(hours=1)
    x = ctx.feat["alt::premium"]
    for i in range(0, len(h), 7):
        known = A[A["t"] <= close_t[i]]
        exp = known["alt::premium"].iloc[-1] if len(known) else np.nan
        assert (np.isnan(exp) and np.isnan(x[i])) or x[i] == exp, (i, x[i], exp)
    # COT is weekly and lives in the same frame: it is aligned on its own calendar, not blanked by daily rows
    y = ctx.feat["alt::cot_lev_net"]
    last_cot = cot["t"].iloc[-1]
    assert np.isfinite(y[close_t <= last_cot]).all()
    assert np.isfinite(ctx.feat["z::alt::cot_lev_net"][close_t <= last_cot]).all()
    assert np.isnan(y[close_t > last_cot + L.ALT_STALE]).all()          # stale after 15 days
    assert "alt::premium" in ctx.sys_cols and "z::alt::cot_lev_net" in ctx.sys_cols


def test_planted_alt_signal_is_reported():
    rng = np.random.default_rng(22)
    n = 24 * 400
    idx = pd.date_range("2024-11-01", periods=n, freq="h", tz="UTC")
    days = pd.date_range(idx[0], idx[-1].normalize(), freq="D", tz="UTC")
    sig = rng.choice([-1.0, 1.0], len(days) + 2)
    # the value published at day k + 30h predicts the next 24 hours
    known_at = days + pd.Timedelta(hours=30)
    drift = np.zeros(n)
    for k, t in enumerate(known_at):
        i0 = idx.searchsorted(t)
        drift[i0:i0 + 24] = 0.0012 * sig[k]
    r = np.concatenate([[0.0], drift[:-1] + rng.normal(0, 0.005, n - 1)])
    c = 100 * np.exp(np.cumsum(r)); o = np.concatenate([[c[0]], c[:-1]])
    h = pd.DataFrame({"Open": o, "High": np.maximum(o, c) * 1.001, "Low": np.minimum(o, c) * 0.999, "Close": c}, index=idx)
    A = pd.DataFrame({"asset": "ETH", "t": known_at, "alt::taker_buy_sell": sig[:len(days)] * 0.1 + rng.normal(0, 0.01, len(days))})
    res = _small(lambda: L.research({"ETH": {"1h": h}}, None, source="test", alt=A))
    top = res["alt_signals"][0]
    assert top["src"].endswith("alt::taker_buy_sell") and top["mean"] > 1.0, res["alt_signals"][:3]
    assert "3c)" in L.report_md(res)


def test_alt_data_parsers_offline(monkeypatch):
    import io
    import zipfile
    import alt_data

    def zipped(df, name, header=True):
        b = io.BytesIO()
        with zipfile.ZipFile(b, "w") as z:
            z.writestr(name, df.to_csv(index=False, header=header))
        return b.getvalue()

    def fake_get(url, timeout=30, params=None):
        if "metrics" in url and "BTCUSDT" in url:
            day = url.split("-metrics-")[1][:10]
            ts = pd.date_range(day, periods=288, freq="5min")
            return zipped(pd.DataFrame({"create_time": ts.strftime("%Y-%m-%d %H:%M:%S"), "symbol": "BTCUSDT",
                                        "sum_open_interest": 1.0, "sum_open_interest_value": 1e9 * (1 + 0.001 * np.arange(288)),
                                        "count_toptrader_long_short_ratio": 1.2, "sum_toptrader_long_short_ratio": 1.1,
                                        "count_long_short_ratio": 1.5, "sum_taker_long_short_vol_ratio": 0.9}), "m.csv")
        if "premiumIndexKlines" in url and "BTCUSDT" in url:
            day = url.split("-1h-")[1][:10]
            ot = (pd.date_range(day, periods=24, freq="h", tz="UTC").asi8 // 10**6)
            return zipped(pd.DataFrame({"open_time": ot, "open": 0, "high": 0, "low": 0, "close": 0.0002}), "p.csv",
                          header=day.endswith("2"))                       # some archive files have no header
        if "fut_fin_txt" in url:
            dates = pd.date_range("2025-01-07", periods=20, freq="7D")
            rows = []
            for k, d in enumerate(dates):
                for nm, oi in (("BITCOIN - CHICAGO MERCANTILE EXCHANGE", 30000), ("MICRO BITCOIN - CHICAGO MERCANTILE EXCHANGE", 90000)):
                    rows.append({"Market_and_Exchange_Names": nm, "Report_Date_as_YYYY-MM-DD": d.strftime("%Y-%m-%d"),
                                 "Open_Interest_All": oi, "Dealer_Positions_Long_All": 100, "Dealer_Positions_Short_All": 200,
                                 "Asset_Mgr_Positions_Long_All": 5000, "Asset_Mgr_Positions_Short_All": 1000,
                                 "Lev_Money_Positions_Long_All": 1000 + 100 * k, "Lev_Money_Positions_Short_All": 9000})
            return zipped(pd.DataFrame(rows), "FinFutYY.txt")
        if url == alt_data.SOCRATA["disagg"]:                               # zip archive blocked -> public API (JSON)
            dates = pd.date_range("2025-01-07", periods=15, freq="7D")
            return json.dumps([{"market_and_exchange_names": "GOLD - COMMODITY EXCHANGE INC.",
                                "report_date_as_yyyy_mm_dd": d.strftime("%Y-%m-%dT00:00:00.000"),
                                "pct_of_open_interest_all": "100", "open_interest_all": "500000",
                                "m_money_positions_long_all": str(200000 + 1000 * k), "m_money_positions_short_all": "50000",
                                "prod_merc_positions_long": "40000", "prod_merc_positions_short": "240000",
                                "swap_positions_long_all": "10000", "swap__positions_short_all": "90000"}
                               for k, d in enumerate(dates)]).encode()
        return None

    monkeypatch.setattr(alt_data, "_get", fake_get)
    from datetime import datetime, timezone
    cp = alt_data.crypto_panel(days=12, end=datetime(2025, 3, 1, tzinfo=timezone.utc), workers=2)
    assert set(cp["asset"]) == {"BTC"} and len(cp) == 12
    # every value becomes known 30h after its file day starts
    assert (cp["t"].dt.hour == 6).all()
    assert cp["alt::premium"].notna().all() and np.allclose(cp["alt::premium"], 0.0002)
    cot = alt_data.cot_panel(years=1, end=datetime(2025, 6, 1, tzinfo=timezone.utc))
    b = cot[cot["asset"] == "BTC"].reset_index(drop=True)
    assert len(b) == 20 and (b["t"].dt.dayofweek == 5).all()            # Tuesday report -> known Saturday
    assert np.isclose(b["alt::cot_lev_net"].iloc[0], (1000 - 9000) / 30000)  # main contract, micro excluded
    assert np.isclose(b["alt::cot_lev_chg"].iloc[1], 100 / 30000)
    g = cot[cot["asset"] == "XAU"].reset_index(drop=True)
    assert len(g) == 15 and np.isclose(g["alt::cot_mm_net"].iloc[0], 150000 / 500000)
    assert np.isclose(g["alt::cot_swap_net"].iloc[0], -80000 / 500000) and np.isclose(g["alt::cot_mm_chg"].iloc[1], 1000 / 500000)
