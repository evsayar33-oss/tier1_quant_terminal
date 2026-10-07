"""
Strategy Lab (v4.0, Aşama 4) — broad, selection-corrected strategy research
==========================================================================
Question it answers: "Which strategy / timeframe / stop rule has a REAL,
after-cost, out-of-sample edge on SPX, NQ, XAU, XAG, BTC, ETH - and what is it
saying right now?"

Search space (per asset)
  timeframes  1h, 4h (730 days of hourly bars), 1d (up to ~10 years)
  families    tsmom (time-series momentum), ema_trend, ema_cross, donchian
              breakout, bollinger mean-reversion, rsi mean-reversion,
              keltner volatility breakout
  sides       long-short (LS) and long-only (LO, what a spot account can do)
  exits       signal only, or ATR stop/target: 1.5/3, 2/4, 3/6
  -> ~700 configurations per asset, ~4,000 in total.

Honesty machinery (why a winner here is not just luck)
  * no look-ahead: a position decided at the close of bar t earns bar t+1;
    stops/targets are checked on later bars' High/Low (stop first if both).
  * costs on every position change (fee + slippage, per asset).
  * every config is aggregated to a common DAILY return grid so 1h/4h/1d
    compete on equal terms.
  * walk-forward of the SELECTION PROCEDURE: the window is cut into 6 folds;
    for folds 2..6 the best config on all earlier data is chosen and only its
    next-fold result is recorded. That OOS series includes the cost of
    choosing among ~700 candidates.
  * Deflated Sharpe Ratio (Bailey & López de Prado 2014) for the selected
    config, with N = number of configs tried.
  * daily configs are re-checked on the long history (up to 10 years).

A config is "KANITLI" (deployable) only if ALL hold:
  WF-OOS Sharpe >= 0.5 · >= 3 of 5 OOS folds positive · DSR >= 0.90 ·
  >= 30 trades in the window · (1d configs) long-history Sharpe > 0.3.

Outputs: lab_results.json (all tables), lab_playbook.json (per-asset
candidate + live signal), lab_report.md (Turkish report).
CLI:  python strategy_lab.py --source yahoo          (GitHub Actions)
      python strategy_lab.py --source panel --panel validation_reports/factor_panel.csv.gz
"""
from __future__ import annotations

import argparse
import json
import math
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

ASSETS = {"SPX": "ES=F", "NQ": "NQ=F", "XAU": "GC=F", "XAG": "SI=F", "BTC": "BTC-USD", "ETH": "ETH-USD"}
NAMES = {"SPX": "S&P 500", "NQ": "Nasdaq 100", "XAU": "Altın", "XAG": "Gümüş", "BTC": "Bitcoin", "ETH": "Ethereum"}
# one-way cost (fee + slippage) as a fraction of price; perp-exchange level, conservative
COST = {"BTC": 0.0010, "ETH": 0.0010, "SPX": 0.0008, "NQ": 0.0008, "XAU": 0.0008, "XAG": 0.0010}
TF_HOURS = {"1h": 1, "4h": 4, "1d": 24}
STOPS = [None, (1.5, 3.0), (2.0, 4.0), (3.0, 6.0)]
WINDOW_DAYS = 730
FOLDS = 6
LONG_FOLDS = 8
MIN_SELECT_TRADES = 15          # fewer trades in the window -> not eligible as "best"
# Two independent ways to be proven:
#  A) 730-day window, all timeframes: walk-forward OOS t >= 2 (selection-honest),
#     >= 3/5 positive folds, DSR >= 0.90, >= 30 trades
#  B) long daily history (>= 6 years), daily configs only: long walk-forward
#     OOS t >= 2, >= 5/7 positive folds, DSR >= 0.90, >= 30 trades
CRIT = {"wf_t": 2.0, "pos_folds": 3, "dsr": 0.90, "trades": 30,
        "long_t": 2.0, "long_pos_folds": 5, "long_years": 6.0}

FAMILY_TR = {"tsmom": "Momentum (zaman serisi)", "ema_trend": "EMA trend filtresi", "ema_cross": "EMA kesişimi",
             "donchian": "Donchian kırılımı", "boll_mr": "Bollinger ortalamaya dönüş",
             "rsi_mr": "RSI ortalamaya dönüş", "keltner": "Keltner volatilite kırılımı"}

GRIDS = {
    "1h": {"tsmom": [12, 24, 48, 96, 168, 336], "ema_trend": [24, 50, 100, 200, 400],
           "ema_cross": [(12, 48), (24, 96), (50, 200), (100, 400)], "donchian": [24, 48, 96, 168]},
    "4h": {"tsmom": [6, 12, 30, 42, 90, 180], "ema_trend": [20, 50, 100, 200],
           "ema_cross": [(10, 30), (20, 50), (50, 200)], "donchian": [20, 55, 120]},
    "1d": {"tsmom": [5, 10, 20, 60, 120, 250], "ema_trend": [20, 50, 100, 200],
           "ema_cross": [(10, 30), (20, 50), (50, 200)], "donchian": [20, 55, 100]},
}
MR_GRID = {"boll_mr": [(20, 2.0), (20, 2.5), (50, 2.0), (50, 2.5)],
           "rsi_mr": [(2, 10, 90), (2, 5, 95), (14, 30, 70)],
           "keltner": [(20, 1.5), (20, 2.5), (50, 2.0)]}


# =============================================================== configs
def cfg_id(c: dict) -> str:
    p = c["p"] if not isinstance(c["p"], (list, tuple)) else "-".join(str(x) for x in c["p"])
    s = "none" if not c.get("stop") else f"{c['stop'][0]}/{c['stop'][1]}"
    return f"{c['tf']}|{c['fam']}|{p}|{c['mode']}|{s}"


def cfg_label(c: dict) -> str:
    p = c["p"] if not isinstance(c["p"], (list, tuple)) else "/".join(str(x) for x in c["p"])
    stop = "sinyalle çıkış" if not c.get("stop") else f"SL {c['stop'][0]}×ATR · TP {c['stop'][1]}×ATR"
    side = "çift yönlü" if c["mode"] == "LS" else "sadece alış"
    return f"{FAMILY_TR[c['fam']]} ({p}) · {c['tf']} · {side} · {stop}"


def configs_for(tf: str) -> List[dict]:
    out = []
    fams = dict(GRIDS[tf])
    fams.update(MR_GRID)
    for fam, plist in fams.items():
        for p in plist:
            for mode in ("LS", "LO"):
                for stop in STOPS:
                    out.append({"tf": tf, "fam": fam, "p": p, "mode": mode, "stop": stop})
    return out


# =============================================================== indicators
def _ema(x: pd.Series, n: int) -> pd.Series:
    return x.ewm(span=n, adjust=False, min_periods=n).mean()


def _atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    h, l, c = df["High"], df["Low"], df["Close"]
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=n).mean()


def _rsi(c: pd.Series, n: int) -> pd.Series:
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def _hold(events: pd.Series) -> np.ndarray:
    """events: +1/-1 = enter, 0 = exit, NaN = keep previous state."""
    return events.ffill().fillna(0.0).values


def signal(c: dict, df: pd.DataFrame) -> np.ndarray:
    """Target position decided at each bar's CLOSE using data up to that close."""
    C = df["Close"]
    fam, p = c["fam"], c["p"]
    if fam == "tsmom":
        s = np.sign(C / C.shift(p) - 1.0).fillna(0.0).values
    elif fam == "ema_trend":
        s = np.sign(C - _ema(C, p)).fillna(0.0).values
    elif fam == "ema_cross":
        s = np.sign(_ema(C, p[0]) - _ema(C, p[1])).fillna(0.0).values
    elif fam == "donchian":
        hi = df["High"].rolling(p).max().shift(1)
        lo = df["Low"].rolling(p).min().shift(1)
        ev = pd.Series(np.nan, index=df.index)
        ev[C > hi] = 1.0
        ev[C < lo] = -1.0
        s = _hold(ev)
    elif fam == "boll_mr":
        n, k = p
        m, sd = C.rolling(n).mean(), C.rolling(n).std()
        z = (C - m) / sd.replace(0, np.nan)
        ev = pd.Series(np.nan, index=df.index)
        ev[np.sign(z) != np.sign(z.shift())] = 0.0
        ev[z < -k] = 1.0
        ev[z > k] = -1.0
        s = _hold(ev)
    elif fam == "rsi_mr":
        n, lo_, hi_ = p
        r = _rsi(C, n)
        ev = pd.Series(np.nan, index=df.index)
        ev[np.sign(r - 50) != np.sign(r.shift() - 50)] = 0.0
        ev[r < lo_] = 1.0
        ev[r > hi_] = -1.0
        s = _hold(ev)
    elif fam == "keltner":
        n, k = p
        e, a = _ema(C, n), _atr(df, n)
        ev = pd.Series(np.nan, index=df.index)
        ev[np.sign(C - e) != np.sign(C.shift() - e.shift())] = 0.0
        ev[C > e + k * a] = 1.0
        ev[C < e - k * a] = -1.0
        s = _hold(ev)
    else:
        raise ValueError(fam)
    s = np.nan_to_num(np.asarray(s, dtype=float))
    if c["mode"] == "LO":
        s = np.clip(s, 0.0, 1.0)
    return s


# =============================================================== simulation
def simulate(c: dict, df: pd.DataFrame, cost: float, sig: Optional[np.ndarray] = None) -> dict:
    """Per-bar net log returns. r[t] is earned DURING bar t by the position held
    after the close of bar t-1. Returns r, effective position, trade owner ids
    and the final open-trade state (for live signals)."""
    if sig is None:
        sig = signal(c, df)
    C = df["Close"].values.astype(float)
    n = len(C)
    stop = c.get("stop")
    if not stop:
        lr = np.zeros(n)
        lr[1:] = np.diff(np.log(C))
        prev = np.concatenate([[0.0], sig[:-1]])
        r = prev * lr - cost * np.abs(sig - prev)
        pos = sig
        state = {"side": int(sig[-1]), "entry": None, "sl": None, "tp": None}
    else:
        O = df["Open"].values.astype(float)
        H = df["High"].values.astype(float)
        L = df["Low"].values.astype(float)
        atr = _atr(df).values
        sl_k, tp_k = stop
        r = np.zeros(n)
        pos = np.zeros(n)
        cur, ent, s_lv, t_lv, blocked = 0.0, 0.0, 0.0, 0.0, None
        for t in range(1, n):
            rt = 0.0
            if cur != 0.0:
                if cur > 0:
                    if L[t] <= s_lv:
                        rt, cur = math.log(min(O[t], s_lv) / C[t - 1]) - cost, 0.0
                        blocked = 1.0
                    elif H[t] >= t_lv:
                        rt, cur = math.log(t_lv / C[t - 1]) - cost, 0.0
                        blocked = 1.0
                    else:
                        rt = math.log(C[t] / C[t - 1])
                else:
                    if H[t] >= s_lv:
                        rt, cur = -math.log(max(O[t], s_lv) / C[t - 1]) - cost, 0.0
                        blocked = -1.0
                    elif L[t] <= t_lv:
                        rt, cur = -math.log(t_lv / C[t - 1]) - cost, 0.0
                        blocked = -1.0
                    else:
                        rt = -math.log(C[t] / C[t - 1])
            want = sig[t]
            if blocked is not None:
                if want == blocked:
                    want = 0.0          # stay out until the signal itself changes
                else:
                    blocked = None
            if want != cur:
                a = atr[t]
                if want != 0.0 and not (a > 0):
                    want = 0.0          # no ATR yet -> no trade
                rt -= cost * abs(want - cur)
                cur = want
                if cur != 0.0:
                    ent = C[t]
                    s_lv, t_lv = ent - cur * sl_k * a, ent + cur * tp_k * a
            r[t] = rt
            pos[t] = cur
        state = {"side": int(cur), "entry": float(ent) if cur else None,
                 "sl": float(s_lv) if cur else None, "tp": float(t_lv) if cur else None}
    # trade ownership: return of bar t belongs to the trade open after bar t-1;
    # an entry bar's cost belongs to the new trade
    chg = np.concatenate([[pos[0] != 0], (pos[1:] != pos[:-1]) & (pos[1:] != 0)])
    tid = np.cumsum(chg)
    prev_pos = np.concatenate([[0.0], pos[:-1]])
    prev_tid = np.concatenate([[0], tid[:-1]])
    owner = np.where(prev_pos != 0, prev_tid, np.where(pos != 0, tid, -1))
    return {"r": r, "pos": pos, "owner": owner, "entries": chg.astype(int), "state": state}


# =============================================================== statistics
def sharpe(x: np.ndarray, per_year: float = 365.0) -> float:
    x = np.asarray(x, dtype=float)
    if len(x) < 5:
        return 0.0
    sd = x.std(ddof=1)
    return float(x.mean() / sd * math.sqrt(per_year)) if sd > 0 else 0.0


def _norm_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _norm_ppf(p: float) -> float:
    # Acklam's rational approximation (|err| < 1.2e-9)
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02,
         -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01,
         -1.328068155288572e+01]
    cc = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00,
          4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00]
    pl = 0.02425
    if p < pl:
        q = math.sqrt(-2 * math.log(p))
        return (((((cc[0] * q + cc[1]) * q + cc[2]) * q + cc[3]) * q + cc[4]) * q + cc[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > 1 - pl:
        return -_norm_ppf(1 - p)
    q = p - 0.5
    rr = q * q
    return (((((a[0] * rr + a[1]) * rr + a[2]) * rr + a[3]) * rr + a[4]) * rr + a[5]) * q / \
           (((((b[0] * rr + b[1]) * rr + b[2]) * rr + b[3]) * rr + b[4]) * rr + 1)


def deflated_sharpe(x: np.ndarray, n_trials: float) -> float:
    """Probability that the selected strategy's true Sharpe > 0 after correcting
    for the best-of-N selection (Bailey & López de Prado 2014). The null
    dispersion of Sharpe estimates is 1/T (no skill); N is the EFFECTIVE number
    of independent trials (see n_effective), not the raw count of near-copies."""
    x = np.asarray(x, dtype=float)
    T = len(x)
    sd = x.std(ddof=1)
    if T < 30 or sd <= 0:
        return 0.0
    sr = x.mean() / sd
    g = 0.5772156649
    N = max(float(n_trials), 2.0)
    sr0 = math.sqrt(1.0 / (T - 1)) * ((1 - g) * _norm_ppf(1 - 1.0 / N) + g * _norm_ppf(1 - 1.0 / (N * math.e)))
    z = (x - x.mean()) / sd
    skew, kurt = float((z ** 3).mean()), float((z ** 4).mean())
    den = 1 - skew * sr + (kurt - 1) / 4.0 * sr * sr
    if den <= 0:
        return 0.0
    return float(_norm_cdf((sr - sr0) * math.sqrt(T - 1) / math.sqrt(den)))


def n_effective(R: np.ndarray) -> float:
    """Effective number of independent strategies (participation ratio of the
    correlation-matrix eigenvalues). 700 configs that are mostly variations of
    a few ideas count as a few dozen trials, not 700."""
    R = R[R.std(1) > 0]
    if len(R) < 2:
        return 1.0
    ev = np.clip(np.linalg.eigvalsh(np.corrcoef(R)), 0, None)
    return float(max(1.0, ev.sum() ** 2 / (ev ** 2).sum()))


def t_stat(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    sd = x.std(ddof=1) if len(x) > 2 else 0.0
    return float(x.mean() / sd * math.sqrt(len(x))) if sd > 0 else 0.0


def max_dd(daily: np.ndarray) -> float:
    eq = np.cumsum(daily)
    return float(1 - math.exp((eq - np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]).min())) if len(eq) else 0.0


def trade_stats(sim: dict, lo: int = 0, hi: Optional[int] = None) -> dict:
    r, owner = sim["r"][lo:hi], sim["owner"][lo:hi]
    m = owner >= 0
    if not m.any():
        return {"trades": 0, "win": None, "avg_trade": None}
    s = pd.Series(r[m]).groupby(owner[m]).sum()
    return {"trades": int(len(s)), "win": float((s > 0).mean()), "avg_trade": float(s.mean())}


# =============================================================== data
def _closed(df: pd.DataFrame, tf: str, now: datetime) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    end = df.index + pd.Timedelta(hours=TF_HOURS[tf])
    return df[end <= pd.Timestamp(now)]


def _resample_4h(h: pd.DataFrame) -> pd.DataFrame:
    agg = h.resample("4h", label="left", closed="left").agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last"})
    return agg.dropna()


def load_yahoo(now: Optional[datetime] = None, hourly_period: str = "730d", daily_period: str = "10y") -> Dict[str, dict]:
    import yfinance as yf
    now = now or datetime.now(timezone.utc)
    out = {}
    for a, sym in ASSETS.items():
        try:
            t = yf.Ticker(sym)
            h = t.history(period=hourly_period, interval="1h", auto_adjust=False)[["Open", "High", "Low", "Close"]]
            h.index = pd.to_datetime(h.index, utc=True)
            h = _closed(h[~h.index.duplicated()].dropna().sort_index(), "1h", now)
            d = t.history(period=daily_period, interval="1d", auto_adjust=False)[["Open", "High", "Low", "Close"]]
            d.index = pd.to_datetime(d.index.date).tz_localize("UTC")
            d = _closed(d[~d.index.duplicated()].dropna().sort_index(), "1d", now)
            out[a] = {"1h": h, "4h": _closed(_resample_4h(h), "4h", now), "1d": d}
            print(f"[lab] {a}: 1h={len(h)} 4h={len(out[a]['4h'])} 1d={len(d)}", flush=True)
        except Exception as exc:
            print(f"[lab] {a}: veri alınamadı ({exc})", flush=True)
    return out


def load_panel(path: str, hour: int = 20) -> Dict[str, dict]:
    """Preview source: daily closes rebuilt EXACTLY from the walk-forward
    factor panel (past_24h = log return over the previous 24h, sampled at
    `hour` UTC each day). No High/Low -> stops are checked on closes."""
    P = pd.read_csv(path, usecols=["asset", "t", "past_24h"])
    P["t"] = pd.to_datetime(P["t"], utc=True)
    out = {}
    for a, g in P.groupby("asset"):
        g = g[g["t"].dt.hour == hour].sort_values("t")
        lp = g["past_24h"].fillna(0.0).cumsum().values
        c = 100.0 * np.exp(lp - lp[0])
        d = pd.DataFrame({"Open": c, "High": c, "Low": c, "Close": c},
                         index=pd.DatetimeIndex(g["t"].dt.normalize()))
        out[a] = {"1d": d}
    return out


# =============================================================== research
def _daily(sim: dict, df: pd.DataFrame, days: pd.DatetimeIndex) -> Tuple[np.ndarray, np.ndarray]:
    day = df.index.tz_convert("UTC").normalize() if df.index.tz is not None else df.index.normalize()
    pos = days.get_indexer(day)
    ok = pos >= 0
    R = np.bincount(pos[ok], weights=sim["r"][ok], minlength=len(days))
    E = np.bincount(pos[ok], weights=sim["entries"][ok], minlength=len(days))
    return R, E


def _wf(R: np.ndarray, E: np.ndarray, folds: int, min_tr: int = 5) -> dict:
    """Walk-forward of the selection procedure on the daily matrix R (cfg x day)."""
    T = R.shape[1]
    edges = np.linspace(0, T, folds + 1).astype(int)
    oos, picks, fold_ret = [], [], []
    for k in range(1, folds):
        tr = slice(0, edges[k])
        te = slice(edges[k], edges[k + 1])
        mu, sd = R[:, tr].mean(1), R[:, tr].std(1, ddof=1)
        sr = np.where(sd > 0, mu / np.where(sd > 0, sd, 1), -np.inf)
        sr[E[:, tr].sum(1) < min_tr] = -np.inf
        j = int(np.argmax(sr))
        if not np.isfinite(sr[j]):
            oos.append(np.zeros(edges[k + 1] - edges[k]))
            picks.append(None)
            fold_ret.append(0.0)
            continue
        x = R[j, te]
        oos.append(x)
        picks.append(j)
        fold_ret.append(float(x.sum()))
    x = np.concatenate(oos) if oos else np.zeros(0)
    return {"sharpe": sharpe(x), "t": t_stat(x), "ret": float(math.exp(x.sum()) - 1) if len(x) else 0.0,
            "pos_folds": int(sum(1 for f in fold_ret if f > 0)), "n_folds": folds - 1,
            "fold_ret": [round(math.exp(f) - 1, 4) for f in fold_ret], "picks": picks, "oos": x}


def research(data: Dict[str, dict], now: Optional[datetime] = None, source: str = "yahoo") -> dict:
    now = now or datetime.now(timezone.utc)
    res = {"generated_at": now.isoformat(), "source": source, "criteria": CRIT, "assets": {}, "families": [],
           "robust": [], "n_configs": 0}
    fam_rows = []
    robust: Dict[str, List[float]] = {}
    for a, frames in data.items():
        cost = COST[a]
        tfs = [tf for tf in ("1h", "4h", "1d") if tf in frames and frames[tf] is not None and len(frames[tf]) > 300]
        if not tfs:
            continue
        end = min(frames[tf].index[-1] for tf in tfs).normalize()   # common end
        starts = [frames[tf].index[0].normalize() for tf in tfs if tf != "1d"]
        w_start = max([end - pd.Timedelta(days=WINDOW_DAYS)] + starts)
        days = pd.date_range(w_start, end, freq="D", tz="UTC")
        cfgs, Rs, Es = [], [], []
        long_on = "1d" in frames and (frames["1d"].index[-1] - frames["1d"].index[0]).days > WINDOW_DAYS * 1.5
        if long_on:
            d1 = frames["1d"]
            ldays = pd.date_range(d1.index[0].normalize(), d1.index[-1].normalize(), freq="D", tz="UTC")
            li, LR, LE = [], [], []
        for tf in tfs:
            df = frames[tf]
            cache = {}
            for c in configs_for(tf):
                key = (c["fam"], str(c["p"]), c["mode"])
                if key not in cache:
                    cache[key] = signal(c, df)
                s = simulate(c, df, cost, cache[key])
                R, E = _daily(s, df, days)
                if long_on and tf == "1d":
                    x, e = _daily(s, df, ldays)
                    li.append(len(cfgs)); LR.append(x); LE.append(e)
                cfgs.append(c); Rs.append(R); Es.append(E)
                del s                                # keep memory flat (~700 sims per asset)
        R, E = np.vstack(Rs), np.vstack(Es)
        N = len(cfgs)
        res["n_configs"] += N
        srs = np.array([sharpe(x) for x in R])
        n_tr = E.sum(1)
        ranked = np.where(n_tr >= MIN_SELECT_TRADES, srs, -np.inf)   # a "best" with 2 trades is noise
        best = int(np.argmax(ranked)) if np.isfinite(ranked).any() else int(np.argmax(srs))
        wf = _wf(R, E, FOLDS, min_tr=max(3, MIN_SELECT_TRADES // 3))
        neff = n_effective(R)
        dsr = deflated_sharpe(R[best], neff)

        def _lo(i):
            return int(frames[cfgs[i]["tf"]].index.searchsorted(days[0]))

        _memo = {}

        def sims(i):                                  # re-simulate on demand (cheap, deterministic)
            if i not in _memo:
                _memo[i] = simulate(cfgs[i], frames[cfgs[i]["tf"]], cost)
            return _memo[i]

        ts_best = trade_stats(sims(best), _lo(best))
        checks_a = {"wf_t": wf["t"] >= CRIT["wf_t"], "pos_folds": wf["pos_folds"] >= CRIT["pos_folds"],
                    "dsr": dsr >= CRIT["dsr"], "trades": ts_best["trades"] >= CRIT["trades"]}
        proven_a = all(checks_a.values())
        # buy & hold over the same window (daily grid, from the finest frame)
        fdf = frames[tfs[0]]
        bh_sim = {"r": np.concatenate([[0.0], np.diff(np.log(fdf["Close"].values))]),
                  "entries": np.zeros(len(fdf))}
        bh, _ = _daily(bh_sim, fdf, days)
        # B) long daily history: an independent, much longer test for 1d configs
        long, proven_b, checks_b, lbest = None, False, {}, None
        if long_on and li:
            LR, LE = np.vstack(LR), np.vstack(LE)
            lsrs = np.array([sharpe(x) for x in LR])
            lrank = np.where(LE.sum(1) >= CRIT["trades"], lsrs, -np.inf)
            k = int(np.argmax(lrank)) if np.isfinite(lrank).any() else int(np.argmax(lsrs))
            lbest = li[k]
            lwf = _wf(LR, LE, LONG_FOLDS, min_tr=10)
            ldsr = deflated_sharpe(LR[k], n_effective(LR))
            lts = trade_stats(sims(lbest))
            years = len(ldays) / 365.25
            bh_l = np.bincount(ldays.get_indexer(d1.index.normalize()),
                               weights=np.concatenate([[0.0], np.diff(np.log(d1["Close"].values))]), minlength=len(ldays))
            checks_b = {"long_years": years >= CRIT["long_years"], "long_t": lwf["t"] >= CRIT["long_t"],
                        "long_pos_folds": lwf["pos_folds"] >= CRIT["long_pos_folds"], "dsr": ldsr >= CRIT["dsr"],
                        "trades": lts["trades"] >= CRIT["trades"]}
            proven_b = all(checks_b.values())
            long = {"years": round(years, 1), "best_id": cfg_id(cfgs[lbest]), "best_label": cfg_label(cfgs[lbest]),
                    "sharpe": round(float(lsrs[k]), 2), "ret": round(float(math.exp(LR[k].sum()) - 1), 4),
                    "maxdd": round(max_dd(LR[k]), 4), "trades": lts["trades"], "win": lts["win"], "dsr": round(ldsr, 3),
                    "wf_sharpe": lwf["sharpe"], "wf_t": lwf["t"], "wf_ret": lwf["ret"], "wf_pos_folds": lwf["pos_folds"],
                    "wf_folds": lwf["n_folds"], "bh_sharpe": sharpe(bh_l), "bh_ret": float(math.exp(bh_l.sum()) - 1)}
        if proven_a:
            cand, path = best, "A"
        elif proven_b:
            cand, path = lbest, "B"
        else:
            cand, path = best, None
        c_best = cfgs[cand]
        tfdf = frames[c_best["tf"]]
        ts = trade_stats(sims(cand), _lo(cand))
        # top 10 table
        order = [i for i in np.argsort(-ranked)[:10] if np.isfinite(ranked[i])]
        top = []
        for i in order:
            c = cfgs[i]
            t_i = trade_stats(sims(i), _lo(i))
            top.append({"id": cfg_id(c), "label": cfg_label(c), "sharpe": round(float(srs[i]), 2),
                        "ret": round(float(math.exp(R[i].sum()) - 1), 4), "maxdd": round(max_dd(R[i]), 4),
                        "trades": t_i["trades"], "win": None if t_i["win"] is None else round(t_i["win"], 3)})
        st = sims(cand)["state"]
        a_res = {
            "window": [str(days[0].date()), str(days[-1].date())], "n_configs": N, "n_effective": round(neff, 1),
            "best": {"id": cfg_id(c_best), "cfg": c_best, "label": cfg_label(c_best), "sharpe": round(float(srs[cand]), 2),
                     "ret": round(float(math.exp(R[cand].sum()) - 1), 4), "maxdd": round(max_dd(R[cand]), 4),
                     "trades": ts["trades"], "win": ts["win"], "avg_trade": ts["avg_trade"],
                     "dsr": round(dsr if path != "B" else long["dsr"], 3)},
            "wf": {k: v for k, v in wf.items() if k not in ("oos", "picks")},
            "wf_picks": [cfg_id(cfgs[j]) if j is not None else None for j in wf["picks"]],
            "bh": {"sharpe": round(sharpe(bh), 2), "ret": round(float(math.exp(bh.sum()) - 1), 4), "maxdd": round(max_dd(bh), 4)},
            "long": long, "checks_a": checks_a, "checks_b": checks_b, "path": path, "proven": path is not None,
            "signal": {"side": {1: "LONG", -1: "SHORT", 0: "FLAT"}[int(np.sign(st["side"]))],
                       "entry": st["entry"], "sl": st["sl"], "tp": st["tp"],
                       "as_of": str(tfdf.index[-1])},
            "top": top,
        }
        res["assets"][a] = a_res
        # family table + robustness inputs
        for tf in tfs:
            for fam in FAMILY_TR:
                idx = [i for i, c in enumerate(cfgs) if c["tf"] == tf and c["fam"] == fam]
                if not idx:
                    continue
                fwf = _wf(R[idx], E[idx], FOLDS)
                fam_rows.append({"asset": a, "tf": tf, "fam": fam, "best": float(srs[idx].max()),
                                 "median": float(np.median(srs[idx])), "wf": fwf["sharpe"]})
        for i, c in enumerate(cfgs):
            if not c.get("stop"):
                robust.setdefault(cfg_id(c), []).append(float(srs[i]))
    fam_df = pd.DataFrame(fam_rows)
    if not fam_df.empty:
        g = fam_df.groupby(["tf", "fam"]).agg(best=("best", "mean"), median=("median", "mean"), wf=("wf", "mean"),
                                               wf_pos=("wf", lambda s: int((s > 0).sum())), n=("wf", "size")).reset_index()
        res["families"] = g.sort_values("wf", ascending=False).round(3).to_dict("records")
    rob = [{"id": k, "mean_sharpe": round(float(np.mean(v)), 2), "pos_assets": int(sum(x > 0 for x in v)),
            "n_assets": len(v)} for k, v in robust.items() if len(v) >= max(2, len(res["assets"]) - 1)]
    res["robust"] = sorted(rob, key=lambda r: (-r["pos_assets"], -r["mean_sharpe"]))[:12]
    return res


# =============================================================== live use
def playbook(res: dict) -> dict:
    out = {"generated_at": res["generated_at"], "source": res["source"], "assets": {}}
    for a, r in res["assets"].items():
        b = r["best"]
        out["assets"][a] = {"cfg": b["cfg"], "id": b["id"], "label": b["label"], "proven": r["proven"], "path": r.get("path"),
                            "wf_sharpe": r["wf"]["sharpe"], "dsr": b["dsr"], "trades": b["trades"],
                            "signal": r["signal"]}
    return out


def live_signals(pb: dict, data: Optional[Dict[str, dict]] = None, now: Optional[datetime] = None) -> dict:
    """Recompute each asset's candidate strategy on fresh closed bars."""
    now = now or datetime.now(timezone.utc)
    if data is None:
        try:
            data = load_yahoo(now, hourly_period="180d", daily_period="3y")
        except Exception as exc:          # no data source -> weekly snapshot, marked not fresh
            print(f"[lab] canlı veri yok ({exc}); haftalık sinyal kullanılıyor", flush=True)
            data = {}
    out = {}
    for a, p in (pb.get("assets") or {}).items():
        c = dict(p["cfg"])
        if isinstance(c.get("p"), list):
            c["p"] = tuple(c["p"])
        if isinstance(c.get("stop"), list):
            c["stop"] = tuple(c["stop"])
        df = (data.get(a) or {}).get(c["tf"])
        sig = dict(p.get("signal") or {})
        fresh = False
        if df is not None and len(df) > 50:
            st = simulate(c, df, COST[a])["state"]
            sig = {"side": {1: "LONG", -1: "SHORT", 0: "FLAT"}[int(np.sign(st["side"]))], "entry": st["entry"],
                   "sl": st["sl"], "tp": st["tp"], "as_of": str(df.index[-1])}
            fresh = True
        out[a] = {"side": sig.get("side", "FLAT"), "sl": sig.get("sl"), "tp": sig.get("tp"), "entry": sig.get("entry"),
                  "as_of": sig.get("as_of"), "fresh": fresh, "strategy": p["label"], "id": p["id"],
                  "proven": bool(p["proven"]), "wf_sharpe": p["wf_sharpe"], "dsr": p["dsr"], "tf": c["tf"]}
    return out


# =============================================================== report
def _pct(x, d=1):
    return "—" if x is None else f"%{x * 100:+.{d}f}"


def report_md(res: dict) -> str:
    L = ["# 🧪 Strateji Laboratuvarı — Sonuç Raporu", "",
         f"_Üretim: {res['generated_at'][:16]} UTC · kaynak: {res['source']} · denenen konfigürasyon: "
         f"**{res['n_configs']:,}** · tüm getiriler maliyet sonrası (net)_", ""]
    if res["source"] == "panel":
        L += ["> ⚠️ ÖN İZLEME: bu sonuçlar 700 günlük walk-forward panelinden yeniden kurulan GÜNLÜK kapanışlarla "
              "üretildi (yalnızca 1g zaman dilimi, stoplar kapanışla kontrol edildi). 1s/4s ve 10 yıllık günlük "
              "test, GitHub Actions'taki ilk 'Strategy Lab' çalışmasında yapılır.", ""]
    L += ["**Kanıt yolları** (biri yeterli):",
          "- **A — 730 gün, tüm zaman dilimleri:** walk-forward OOS t ≥ 2 · 5 test diliminin ≥ 3'ü pozitif · "
          "Deflated Sharpe ≥ 0.90 · ≥ 30 işlem",
          "- **B — uzun günlük geçmiş (≥ 6 yıl), sadece 1g:** uzun walk-forward OOS t ≥ 2 · 7 dilimin ≥ 5'i pozitif · "
          "Deflated Sharpe ≥ 0.90 · ≥ 30 işlem", "",
          "## 1) Varlık bazında özet", "",
          "| Varlık | Aday strateji | Sharpe | Getiri | Maks. DD | İşlem | Kazanma | WF-OOS Sharpe (t) | + dilim | DSR | "
          "Uzun dönem 1g: WF Sharpe (t) · + dilim | Al-tut Sharpe / getiri | Durum | Şu anki sinyal |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for a, r in res["assets"].items():
        b, w, bh, lg = r["best"], r["wf"], r["bh"], r.get("long")
        state = {"A": "✅ KANITLI (A)", "B": "✅ KANITLI (B)"}.get(r.get("path"), "❌ kanıt yok")
        sg = r["signal"]
        sig = {"LONG": "🟢 AL", "SHORT": "🔴 SAT", "FLAT": "⚪ POZİSYON YOK"}[sg["side"]]
        win = "—" if b["win"] is None else f"%{b['win'] * 100:.0f}"
        lgs = "—" if not lg else f"{lg['wf_sharpe']:.2f} ({lg['wf_t']:+.1f}) · {lg['wf_pos_folds']}/{lg['wf_folds']} · {lg['years']} yıl"
        L.append(f"| {a} | {b['label']} | {b['sharpe']:.2f} | {_pct(b['ret'])} | {_pct(-b['maxdd'])} | {b['trades']} | "
                 f"{win} | {w['sharpe']:.2f} ({w['t']:+.1f}) | {w['pos_folds']}/{w['n_folds']} | {b['dsr']:.2f} | {lgs} | "
                 f"{bh['sharpe']:.2f} / {_pct(bh['ret'])} | {state} | {sig} |")
    L += ["", "_Sharpe/getiri/DD/işlem: adayın son 730 gündeki net sonucu. WF-OOS: her dilimde YALNIZCA geçmişte en iyi "
          "olanı seçip bir sonraki dilimde ölçen prosedürün dışı-örneklem sonucu — yüzlerce aday arasından seçim yapmanın "
          "bedeli dahildir; t ≥ 2 istatistiksel anlamlılık eşiğidir. DSR: etkin deneme sayısına göre düzeltilmiş "
          "'gerçek Sharpe > 0' olasılığı._", ""]
    L += ["## 2) Strateji aileleri (6 varlık ortalaması)", "",
          "| Zaman dilimi | Aile | En iyi Sharpe | Medyan Sharpe | WF-OOS Sharpe | WF pozitif varlık |", "|---|---|---|---|---|---|"]
    for f in res["families"]:
        L.append(f"| {f['tf']} | {FAMILY_TR[f['fam']]} | {f['best']:.2f} | {f['median']:.2f} | {f['wf']:.2f} | {f['wf_pos']}/{f['n']} |")
    L += ["", "## 3) En sağlam çok-varlıklı konfigürasyonlar (stopsuz, tüm varlıklarda aynı ayar)", "",
          "| Konfigürasyon | Ort. Sharpe | Pozitif varlık |", "|---|---|---|"]
    for r in res["robust"]:
        L.append(f"| {r['id'].replace('|', ' · ')} | {r['mean_sharpe']:.2f} | {r['pos_assets']}/{r['n_assets']} |")
    if res["assets"]:
        bh_avg = float(np.mean([r["bh"]["sharpe"] for r in res["assets"].values()]))
        L.append(f"\n_Kıyas: aynı dönemde al-tut ortalama Sharpe {bh_avg:.2f}. 'Sadece alış' (LO) stratejilerin pozitifliğinin "
                 f"bir kısmı piyasanın genel yükselişinden gelir; asıl soru al-tut'tan daha iyi risk/getiri verip vermediğidir._")
    L += ["", "## 4) Varlık bazında ilk 10 konfigürasyon (tam pencere — seçim yanlılığı İÇERİR, tek başına kanıt değildir)", ""]
    for a, r in res["assets"].items():
        L += [f"**{a} — {NAMES[a]}** · pencere {r['window'][0]} → {r['window'][1]} · {r['n_configs']} konfigürasyon", "",
              "| # | Konfigürasyon | Sharpe | Getiri | Maks. DD | İşlem | Kazanma |", "|---|---|---|---|---|---|---|"]
        for k, t in enumerate(r["top"], 1):
            win = "—" if t["win"] is None else f"%{t['win'] * 100:.0f}"
            L.append(f"| {k} | {t['label']} | {t['sharpe']:.2f} | {_pct(t['ret'])} | {_pct(-t['maxdd'])} | {t['trades']} | {win} |")
        if r.get("long"):
            lg = r["long"]
            win = "—" if lg["win"] is None else f"%{lg['win'] * 100:.0f}"
            L.append(f"\n_Uzun dönem ({lg['years']} yıl, 1g): en iyi {lg['best_label']} — Sharpe {lg['sharpe']:.2f}, "
                     f"getiri {_pct(lg['ret'], 0)}, maks. DD {_pct(-lg['maxdd'], 0)}, {lg['trades']} işlem, kazanma {win}, "
                     f"DSR {lg['dsr']:.2f} · WF-OOS Sharpe {lg['wf_sharpe']:.2f} (t {lg['wf_t']:+.1f}), "
                     f"pozitif dilim {lg['wf_pos_folds']}/{lg['wf_folds']} · al-tut Sharpe {lg['bh_sharpe']:.2f}, "
                     f"getiri {_pct(lg['bh_ret'], 0)}_")
        L.append(f"\n_Walk-forward dilim getirileri: {', '.join(_pct(x) for x in r['wf']['fold_ret'])}_\n")
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["yahoo", "panel"], default="yahoo")
    ap.add_argument("--panel", default="validation_reports/factor_panel.csv.gz")
    ap.add_argument("--out", default=".")
    args = ap.parse_args()
    data = load_yahoo() if args.source == "yahoo" else load_panel(args.panel)
    res = research(data, source=args.source)
    os.makedirs(args.out, exist_ok=True)
    slim = json.loads(json.dumps(res, default=str))
    json.dump(slim, open(os.path.join(args.out, "lab_results.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(json.loads(json.dumps(playbook(res), default=str)),
              open(os.path.join(args.out, "lab_playbook.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(os.path.join(args.out, "lab_report.md"), "w", encoding="utf-8").write(report_md(res))
    print(f"[lab] {res['n_configs']} konfigürasyon · kanıtlı: "
          f"{[a for a, r in res['assets'].items() if r['proven']] or 'yok'}", flush=True)


if __name__ == "__main__":
    main()
