"""
Shock Lab (v12.0) — S&P 500 and Nasdaq-100 panics, every method, 1990 → today
=============================================================================
Question: after a shock, WHEN do we buy, HOW do we get out, HOW MUCH do we
size, and UNDER WHICH technical / fundamental conditions does it work?
Everything is tested alone and in combination, under one honesty protocol.

  SHOCKS (~45 definitions): VIX level / spike / z-score, VIX term-structure
      inversion, VVIX and SKEW extremes, index daily drop, drawdown from the
      52-week high, consecutive down days, RSI(2)/RSI(14) washout, Bollinger
      break, credit-spread shock, rate shock, real-yield shock, dollar shock,
      oil shock, financial-stress (NFCI/STLFSI) shock + "any panic" union.
  ENTRIES (6): at the shock close, next open, first up-close, when the VIX
      recedes 10% from its peak, when price reclaims its 5-day average,
      scaled in over 3 days.
  EXITS (~60): fixed hold 5…120 days, %-take-profit/stop grids, ATR
      take-profit/stop grids, %- and ATR-trailing stops, VIX-normalisation
      exit, recovery-to-high exit, trend-break exit (all with a time cap).
      Daily OHLC, stop assumed first inside a bar, gaps fill at the open.
  FILTERS (~32 technical + fundamental, every single one AND every pair):
      trend (200-day), drawdown depth, VIX term state, inflation expectations,
      real-yield trend, credit spreads, yield curve, Fed hiking/cutting,
      financial conditions, jobless-claims recession signal, dollar, oil …
  SIZING / PORTFOLIO: event trades at 1x/2x/3x, overlays on a base position,
      leverage financed at the real 3-month T-bill rate.
  ML GATE: gradient boosting on the event-day state, yearly walk-forward.
  INTRADAY: entry hour after a shock on hourly bars (last ~2 years).
  PROTOCOL: every choice is made on 1990–2016; 2017–today is a SEALED exam.
      The inflation hypothesis found on 2016–2026 is tested on 2003–2016,
      data it has never seen.

CLI: python shock_lab.py --data shock_data --out shock_out
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import os
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    from numba import njit
except Exception:                                            # pragma: no cover
    def njit(*a, **k):
        def deco(f):
            return f
        return deco(a[0]) if a and callable(a[0]) else deco

EXAM_START = pd.Timestamp("2017-01-01")
TRAIN_START = pd.Timestamp("1990-06-01")
COST = 0.0002                     # per side (index futures / ETF)
GAP = 15                          # trading days between two events of the same definition
MAX_HOLD = 120
ASSETS = {"SPX": "^GSPC", "NDX": "^NDX"}


# ================================================================= data
def load(data: str):
    D = pd.read_csv(os.path.join(data, "daily.csv.gz"), parse_dates=["date"])
    px = {s: g.set_index("date").sort_index()[["Open", "High", "Low", "Close"]] for s, g in D.groupby("symbol")}
    fred = None
    p = os.path.join(data, "fred.csv.gz")
    if os.path.exists(p):
        fred = pd.read_csv(p, parse_dates=["date", "avail"])
    hourly = None
    p = os.path.join(data, "hourly.csv.gz")
    if os.path.exists(p):
        hourly = pd.read_csv(p, parse_dates=["time"])
    return px, fred, hourly


def _asof(fred: Optional[pd.DataFrame], sid: str, cal: pd.DatetimeIndex) -> pd.Series:
    """Value known at the CLOSE of each calendar day (availability date <= day)."""
    if fred is None:
        return pd.Series(np.nan, index=cal)
    s = fred[fred.series == sid].sort_values("avail")
    if s.empty:
        return pd.Series(np.nan, index=cal)
    s = s.groupby("avail")["value"].last()
    return s.reindex(cal.union(s.index)).ffill().reindex(cal)


def _rsi(c: pd.Series, n: int) -> pd.Series:
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def _z(x: pd.Series, n: int = 252) -> pd.Series:
    return (x - x.rolling(n, min_periods=n // 3).mean()) / x.rolling(n, min_periods=n // 3).std()


def features(px: Dict[str, pd.DataFrame], fred, asset: str) -> pd.DataFrame:
    """Everything known at the close of each day for one traded index."""
    P = px[ASSETS[asset]]
    cal = P.index
    c, h, l = P.Close, P.High, P.Low
    F = pd.DataFrame(index=cal)
    F["ret1"] = c.pct_change()
    F["ret5"] = c / c.shift(5) - 1
    F["dd52"] = c / c.rolling(252, min_periods=60).max() - 1
    F["ma200"] = c / c.rolling(200, min_periods=150).mean() - 1
    F["ma50"] = c / c.rolling(50, min_periods=40).mean() - 1
    F["rsi2"] = _rsi(c, 2)
    F["rsi14"] = _rsi(c, 14)
    F["boll"] = (c - c.rolling(20).mean()) / c.rolling(20).std()
    dn = (c < c.shift(1)).astype(int)
    F["down_streak"] = dn.groupby((dn == 0).cumsum()).cumsum()
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    F["atr_pct"] = tr.rolling(20).mean() / c
    F["rvol20"] = np.log(c / c.shift()).rolling(20).std() * math.sqrt(252)

    def ycol(sym):
        s = px.get(sym)
        return s.Close.reindex(cal).ffill(limit=3) if s is not None else pd.Series(np.nan, index=cal)
    vix = ycol("^VIX")
    if vix.isna().all():
        vix = _asof(fred, "VIXCLS", cal)
    F["vix"] = vix
    F["vix_chg5"] = vix / vix.shift(5) - 1
    F["vix_z"] = _z(vix)
    F["vix_ma50"] = vix / vix.rolling(50, min_periods=30).mean() - 1
    F["vix_term"] = vix / ycol("^VIX3M")
    F["vvix"] = ycol("^VVIX")
    F["vvix_z"] = _z(F["vvix"])
    F["skew_z"] = _z(ycol("^SKEW"))
    dxy = ycol("DX-Y.NYB")
    F["dxy_z20"] = _z(dxy / dxy.shift(20) - 1)
    oil = ycol("CL=F")
    F["oil_chg20"] = oil / oil.shift(20) - 1
    tnx = ycol("^TNX")
    F["y10_chg20"] = tnx - tnx.shift(20)
    # FRED (point-in-time)
    be = _asof(fred, "T10YIE", cal)
    F["breakeven"] = be
    F["breakeven_z"] = _z(be)
    F["breakeven_chg60"] = be - be.shift(60)
    ry = _asof(fred, "DFII10", cal)
    F["realy_chg20"] = ry - ry.shift(20)
    F["realy_z"] = _z(ry)
    hy = _asof(fred, "BAMLH0A0HYM2", cal)
    F["hy_oas"] = hy
    F["hy_chg20"] = hy - hy.shift(20)
    F["hy_z"] = _z(hy)
    F["curve"] = _asof(fred, "T10Y2Y", cal)
    ff = _asof(fred, "FEDFUNDS", cal)
    F["fed_chg6m"] = ff - ff.shift(126)
    F["nfci"] = _asof(fred, "NFCI", cal)
    F["stlfsi"] = _asof(fred, "STLFSI4", cal)
    ic = _asof(fred, "ICSA", cal)
    F["claims_ratio"] = ic.rolling(20).mean() / ic.rolling(252, min_periods=100).min() - 1   # Sahm-like recession signal
    cpi = _asof(fred, "CPIAUCSL", cal)
    F["cpi_yoy"] = cpi / cpi.shift(252) - 1
    F["tbill"] = _asof(fred, "DGS3MO", cal) / 100.0
    return F


# ================================================================= shocks / entries / exits / filters
def shocks(F: pd.DataFrame) -> Dict[str, np.ndarray]:
    def cross(x: pd.Series, thr: float, up=True) -> pd.Series:
        return (x > thr) & (x.shift(1) <= thr) if up else (x < thr) & (x.shift(1) >= thr)
    S = {}
    for t in (25, 30, 35, 40):
        S[f"VIX {t} üstüne çıktı"] = cross(F.vix, t)
    for t in (0.3, 0.5, 0.8):
        S[f"VIX 5 günde +%{int(t * 100)}"] = F.vix_chg5 > t
    for t in (2, 3):
        S[f"VIX 1y z>{t}"] = F.vix_z > t
    for t in (1.0, 1.1):
        S[f"VIX vade yapısı ters (>{t})"] = F.vix_term > t
    S["VVIX z>2"] = F.vvix_z > 2
    S["SKEW z>2"] = F.skew_z > 2
    for t in (0.02, 0.03, 0.04):
        S[f"endeks günlük −%{int(t * 100)}"] = F.ret1 <= -t
    for t in (0.05, 0.08, 0.10, 0.15, 0.20):
        S[f"zirveden −%{int(t * 100)}"] = cross(F.dd52, -t, up=False)
    for t in (5, 7):
        S[f"{t} gün üst üste düşüş"] = F.down_streak >= t
    S["RSI(2) < 5"] = F.rsi2 < 5
    S["RSI(14) < 25"] = F.rsi14 < 25
    S["Bollinger −2.5σ altı"] = F.boll < -2.5
    S["kredi şoku (HY spread 20g +1.5 puan)"] = F.hy_chg20 > 1.5
    S["kredi spread z>2"] = F.hy_z > 2
    S["faiz şoku (10y 20g +0.5)"] = F.y10_chg20 > 0.5
    S["reel faiz şoku (20g +0.4)"] = F.realy_chg20 > 0.4
    S["dolar şoku (z>2)"] = F.dxy_z20 > 2
    S["petrol şoku (20g +%25)"] = F.oil_chg20 > 0.25
    S["finansal stres (STLFSI>1)"] = cross(F.stlfsi, 1.0)
    S["finansal koşullar sıkı (NFCI>0)"] = cross(F.nfci, 0.0)
    out = {k: v.fillna(False).values for k, v in S.items()}
    out["HERHANGİ bir panik (birleşim)"] = np.any(np.vstack([out[k] for k in out if not k.startswith(("faiz", "reel", "dolar", "petrol", "finansal koşullar"))]), axis=0)
    return out


def decluster(mask: np.ndarray, gap: int = GAP) -> np.ndarray:
    idx = np.where(mask)[0]
    keep, last = [], -10 ** 9
    for i in idx:
        if i - last > gap:
            keep.append(i)
            last = i
    return np.array(keep, dtype=np.int64)


ENTRIES = ["kapanışta", "ertesi açılış", "ilk yeşil kapanış", "VIX zirveden %10 geri çekilince", "5g ortalamayı geri alınca",
           "3 günde kademeli"]


def entry(mode: str, d: int, O, C, vix, ma5) -> Tuple[int, float]:
    n = len(C)
    if mode == "kapanışta":
        return d, C[d]
    if mode == "ertesi açılış":
        return (d + 1, O[d + 1]) if d + 1 < n else (-1, np.nan)
    if mode == "3 günde kademeli":
        return (d + 2, float(np.mean(C[d:d + 3]))) if d + 2 < n else (-1, np.nan)
    peak = vix[d]
    for k in range(d + 1, min(n, d + 16)):
        if mode == "ilk yeşil kapanış" and C[k] > C[k - 1]:
            return k, C[k]
        if mode == "VIX zirveden %10 geri çekilince":
            peak = max(peak, vix[k]) if np.isfinite(vix[k]) else peak
            if np.isfinite(vix[k]) and vix[k] <= 0.9 * peak:
                return k, C[k]
        if mode == "5g ortalamayı geri alınca" and C[k] > ma5[k]:
            return k, C[k]
    return -1, np.nan


def exit_specs() -> List[dict]:
    X = [dict(kind="hold", H=H) for H in (5, 10, 20, 40, 60, 90, 120)]
    for tp, sl in itertools.product((0.03, 0.05, 0.08, 0.12, 0.20), (0.03, 0.05, 0.08, 0.12, 0.0)):
        X.append(dict(kind="pct", tp=tp, sl=sl, H=MAX_HOLD))
    for tp, sl in itertools.product((2.0, 3.0, 5.0), (1.5, 2.0, 3.0)):
        X.append(dict(kind="atr", tp=tp, sl=sl, H=MAX_HOLD))
    for tr in (0.05, 0.08, 0.12):
        X.append(dict(kind="trail", tr=tr, H=MAX_HOLD))
    for tr in (2.0, 3.0):
        X.append(dict(kind="trail_atr", tr=tr, H=MAX_HOLD))
    X += [dict(kind="vix_norm", H=MAX_HOLD), dict(kind="vix_below20", H=MAX_HOLD),
          dict(kind="recover", H=MAX_HOLD), dict(kind="trend_break", H=MAX_HOLD)]
    for H in (20, 60):
        X += [dict(kind="pct", tp=tp, sl=0.0, H=H) for tp in (0.05, 0.10)]
    return X


def exit_label(x: dict) -> str:
    k = x["kind"]
    if k == "hold":
        return f"{x['H']} gün tut"
    if k == "pct":
        return f"TP %{x['tp'] * 100:.0f} / " + (f"SL %{x['sl'] * 100:.0f}" if x["sl"] else "stop yok") + f" (en çok {x['H']}g)"
    if k == "atr":
        return f"TP {x['tp']:g} ATR / SL {x['sl']:g} ATR"
    if k == "trail":
        return f"iz süren stop %{x['tr'] * 100:.0f}"
    if k == "trail_atr":
        return f"iz süren stop {x['tr']:g} ATR"
    return {"vix_norm": "VIX 50g ortalamasına inince çık", "vix_below20": "VIX 20 altına inince çık",
            "recover": "zirveye %2 yaklaşınca çık", "trend_break": "20g dibin altında kapanınca çık"}[k]


@njit(cache=True)
def _walk(e, px0, O, H, L, C, atr, vix, vix50, hi52, lo20, kind, a, b, Hmax, cost):
    """Return (net return, bars held) of one long trade entered at px0 on bar e (after its close)."""
    n = len(C)
    peak = px0
    a_atr = atr[e] * px0
    tp = px0 * (1 + a) if kind == 1 else px0 + a * a_atr
    sl = (px0 * (1 - b) if b > 0 else -1.0) if kind == 1 else px0 - b * a_atr
    last = min(n - 1, e + Hmax)
    for t in range(e + 1, last + 1):
        if kind == 1 or kind == 2:                          # % or ATR take-profit / stop (stop first)
            if sl > 0 and L[t] <= sl:
                return min(O[t], sl) / px0 - 1 - 2 * cost, t - e
            if H[t] >= tp:
                return max(O[t], tp) / px0 - 1 - 2 * cost, t - e
        elif kind == 3 or kind == 4:                        # trailing stops
            stop = peak * (1 - a) if kind == 3 else peak - a * atr[t - 1] * C[t - 1]
            if L[t] <= stop:
                return min(O[t], stop) / px0 - 1 - 2 * cost, t - e
            peak = max(peak, H[t])
        elif kind == 5:
            if vix[t] < vix50[t]:
                return C[t] / px0 - 1 - 2 * cost, t - e
        elif kind == 6:
            if vix[t] < 20:
                return C[t] / px0 - 1 - 2 * cost, t - e
        elif kind == 7:
            if C[t] >= 0.98 * hi52[e]:
                return C[t] / px0 - 1 - 2 * cost, t - e
        elif kind == 8:
            if t > e + 2 and C[t] < lo20[t - 1]:
                return C[t] / px0 - 1 - 2 * cost, t - e
    return C[last] / px0 - 1 - 2 * cost, last - e


KIND = {"hold": 0, "pct": 1, "atr": 2, "trail": 3, "trail_atr": 4, "vix_norm": 5, "vix_below20": 6, "recover": 7, "trend_break": 8}


def filters(F: pd.DataFrame) -> Dict[str, np.ndarray]:
    """Technical + fundamental state at the shock day. NaN (data not yet available) -> filter not met."""
    G = {
        "trend: 200g ortalama ÜSTÜNDE": F.ma200 > 0, "trend: 200g ortalama ALTINDA": F.ma200 <= 0,
        "düşüş derin (zirveden −%10'dan fazla)": F.dd52 <= -0.10, "düşüş sığ (−%10'dan az)": F.dd52 > -0.10,
        "VIX vade yapısı ters": F.vix_term > 1.0, "VIX vade yapısı normal": F.vix_term <= 1.0,
        "VIX > 30": F.vix > 30, "VIX < 25": F.vix < 25,
        "enflasyon beklentisi DÜŞÜK (z<0.5)": F.breakeven_z < 0.5, "enflasyon beklentisi YÜKSEK (z≥0.5)": F.breakeven_z >= 0.5,
        "enflasyon beklentisi 60g düşüyor": F.breakeven_chg60 < 0, "enflasyon beklentisi 60g yükseliyor": F.breakeven_chg60 >= 0,
        "reel faiz 20g düşüyor": F.realy_chg20 < 0, "reel faiz 20g yükseliyor": F.realy_chg20 >= 0,
        "kredi spreadi sakin (z<1)": F.hy_z < 1, "kredi spreadi stresli (z≥1)": F.hy_z >= 1,
        "kredi spreadi 20g genişliyor": F.hy_chg20 > 0, "kredi spreadi 20g daralıyor": F.hy_chg20 <= 0,
        "getiri eğrisi ters": F.curve < 0, "getiri eğrisi normal": F.curve >= 0,
        "Fed faiz ARTIRIYOR (6 ay)": F.fed_chg6m > 0.25, "Fed faiz İNDİRİYOR (6 ay)": F.fed_chg6m < -0.25,
        "Fed sabit": F.fed_chg6m.abs() <= 0.25,
        "finansal koşullar gevşek (NFCI<0)": F.nfci < 0, "finansal koşullar sıkı (NFCI≥0)": F.nfci >= 0,
        "işsizlik başvuruları sakin (resesyon sinyali yok)": F.claims_ratio < 0.2, "işsizlik başvuruları yükseliyor (resesyon riski)": F.claims_ratio >= 0.2,
        "dolar sakin": F.dxy_z20.abs() < 1.5, "petrol sakin": F.oil_chg20.abs() < 0.2,
        "enflasyon (TÜFE yıllık) < %3": F.cpi_yoy < 0.03, "enflasyon (TÜFE yıllık) ≥ %3": F.cpi_yoy >= 0.03,
    }
    return {k: v.fillna(False).values.astype(bool) for k, v in G.items()}


# ================================================================= research
def trades_for(F: pd.DataFrame, P: pd.DataFrame, shock_idx: np.ndarray, emode: str, xspecs: List[dict]):
    O, H, L, C = (P[c].values.astype(float) for c in ("Open", "High", "Low", "Close"))
    vix = F.vix.values.astype(float)
    vix50 = F.vix.rolling(50, min_periods=30).mean().values
    ma5 = P.Close.rolling(5).mean().values
    atr = F.atr_pct.values.astype(float)
    hi52 = P.Close.rolling(252, min_periods=60).max().values
    lo20 = P.Low.rolling(20).min().values
    ev, ent = [], []
    for d in shock_idx:
        e, p0 = entry(emode, int(d), O, C, vix, ma5)
        if e < 0 or not np.isfinite(p0) or e >= len(C) - 2 or not np.isfinite(atr[e]):
            continue
        ev.append(int(d)); ent.append((e, p0))
    R = np.full((len(xspecs), len(ev)), np.nan)
    HD = np.zeros((len(xspecs), len(ev)))
    for k, (e, p0) in enumerate(ent):
        for xi, x in enumerate(xspecs):
            kind = KIND[x["kind"]]
            a = x.get("tp", x.get("tr", 0.0))
            b = x.get("sl", 0.0)
            Hm = x["H"]
            r, hd = _walk(e, p0, O, H, L, C, atr, vix, vix50, hi52, lo20, kind, float(a), float(b), int(Hm), COST)
            R[xi, k] = r
            HD[xi, k] = hd
    return np.array(ev, dtype=np.int64), np.array([e for e, _ in ent], dtype=np.int64), R, HD


def _stats(R: np.ndarray, M: np.ndarray):
    """R: (n_exit, n_ev) returns; M: (n_filter, n_ev) bool. -> n, mean, t, win (n_filter, n_exit)."""
    Mf = M.astype(float)
    Rz = np.nan_to_num(R)
    ok = np.isfinite(R).astype(float)
    n = Mf @ ok.T
    s1 = Mf @ Rz.T
    s2 = Mf @ (Rz ** 2).T
    w = Mf @ ((Rz > 0) * ok).T
    mean = np.divide(s1, n, out=np.zeros_like(s1), where=n > 0)
    var = np.divide(s2 - n * mean ** 2, n - 1, out=np.zeros_like(s1), where=n > 1)
    # a 2% floor on the per-trade dispersion: a handful of identical take-profit hits must not look like certainty
    t = np.divide(mean * np.sqrt(n), np.maximum(np.sqrt(np.maximum(var, 0.0)), 0.02), out=np.zeros_like(s1), where=n > 2)
    win = np.divide(w, n, out=np.zeros_like(s1), where=n > 0)
    return n, mean, t, win


def research(px, fred, hourly=None, assets=("SPX", "NDX"), fast=False) -> dict:
    xspecs = exit_specs()
    if fast:
        xspecs = xspecs[:10] + xspecs[-6:]
    res = {"generated_at": pd.Timestamp.now("UTC").isoformat(), "exam_start": str(EXAM_START.date()), "assets": {}}
    for asset in assets:
        if ASSETS[asset] not in px:
            continue
        P = px[ASSETS[asset]]
        P = P[P.index >= TRAIN_START - pd.Timedelta(days=400)]
        F = features(px, fred, asset).reindex(P.index)
        cal = P.index
        S = shocks(F)
        G = filters(F)
        gnames = ["(filtresiz)"] + list(G)
        pairs = list(itertools.combinations(list(G), 2))
        start_i = int(np.searchsorted(cal.values, np.datetime64(TRAIN_START)))
        ex_i = int(np.searchsorted(cal.values, np.datetime64(EXAM_START)))
        parts, ev_count = [], {}
        xl = np.array([exit_label(x) for x in xspecs], dtype=object)
        xk = np.array([x["kind"] for x in xspecs], dtype=object)
        store = {}
        for sname, mask in S.items():
            mask = mask.copy()
            mask[:start_i] = False
            sidx = decluster(mask)
            ev_count[sname] = (int((sidx < ex_i).sum()), int((sidx >= ex_i).sum()))
            if len(sidx) < 8:
                continue
            for emode in (ENTRIES[:3] if fast else ENTRIES):
                ev, en, R, HD = trades_for(F, P, sidx, emode, xspecs)
                if len(ev) < 8:
                    continue
                store[(sname, emode)] = (ev, en, R, HD)
                tr = ev < ex_i
                # single filters + all pairs
                Ms = [np.ones(len(ev), bool)] + [G[g][ev] for g in G] + [G[a][ev] & G[b][ev] for a, b in pairs]
                names = gnames + [f"{a} + {b}" for a, b in pairs]
                M = np.vstack(Ms)
                n1, m1, t1, w1 = _stats(R[:, tr], M[:, tr])
                n2, m2, t2, w2 = _stats(R[:, ~tr], M[:, ~tr])
                hd = np.nanmean(HD, axis=1)
                single = np.arange(M.shape[0]) <= len(G)
                keep = (n1 >= 5) & (single[:, None] | ((n1 >= 15) & (t1 > 1.0)))   # pairs: enough events and a positive train signal
                fi, xi = np.nonzero(keep)
                nm = np.array(names, dtype=object)
                parts.append(pd.DataFrame({
                    "şok": sname, "giriş": emode, "çıkış": xl[xi], "çıkış_türü": xk[xi], "filtre": nm[fi], "tek_filtre": single[fi],
                    "n_eğitim": n1[fi, xi].astype(int), "ort_eğitim": m1[fi, xi], "t_eğitim": t1[fi, xi], "kazanma_eğitim": w1[fi, xi],
                    "n_sınav": n2[fi, xi].astype(int), "ort_sınav": m2[fi, xi], "t_sınav": t2[fi, xi], "kazanma_sınav": w2[fi, xi],
                    "ort_gün": hd[xi]}))
        T = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
        # excess over simply being long for the same number of days (the market's normal drift)
        rr = P.Close.pct_change().values
        dr_tr = float(np.nanmean(rr[start_i:ex_i])); dr_ex = float(np.nanmean(rr[ex_i:]))
        if len(T):
            T["fazla_eğitim"] = T.ort_eğitim - dr_tr * T.ort_gün
            T["fazla_sınav"] = T.ort_sınav - dr_ex * T.ort_gün
        res["assets"][asset] = analyse(asset, T, store, F, P, G, xspecs, ex_i, ev_count, hourly)
        res["assets"][asset]["_table"] = T
    return res


def _rowdict(row: pd.Series) -> dict:
    return {k: (round(float(v), 4) if isinstance(v, (float, np.floating)) else (int(v) if isinstance(v, (np.integer,)) else
                (bool(v) if isinstance(v, np.bool_) else v))) for k, v in row.items()}


def _fam(T: pd.DataFrame, col: str, single_only=True) -> list:
    D = T[T.tek_filtre] if single_only else T
    D = D[D.n_sınav >= 3]
    g = D.groupby(col).agg(kural=("ort_eğitim", "size"), eğitim=("ort_eğitim", "mean"), sınav=("ort_sınav", "mean"),
                           fazla_eğitim=("fazla_eğitim", "mean"), fazla_sınav=("fazla_sınav", "mean"),
                           eğitim_kazanma=("kazanma_eğitim", "mean"), sınav_kazanma=("kazanma_sınav", "mean"),
                           sınav_pozitif=("ort_sınav", lambda s: float((s > 0).mean())))
    return g.sort_values("fazla_sınav", ascending=False).reset_index().round(4).to_dict("records")


def analyse(asset, T, store, F, P, G, xspecs, ex_i, ev_count, hourly) -> dict:
    out = {"events": ev_count, "n_configs": int(len(T))}
    # baseline: buy on a random day and hold the same time -> "excess" is what a shock adds
    C = P.Close.values
    base = {}
    for H in (5, 10, 20, 40, 60, 90, 120):
        f = C[H:] / C[:-H] - 1
        idx = np.arange(len(f))
        base[H] = (float(np.nanmean(f[(idx < ex_i)])), float(np.nanmean(f[idx >= ex_i])))
    out["baseline"] = base
    out["fam_shock"] = _fam(T, "şok")
    out["fam_entry"] = _fam(T, "giriş")
    out["fam_exit"] = _fam(T, "çıkış_türü")
    out["fam_filter"] = _fam(T[T.tek_filtre], "filtre", single_only=False)
    # train-only selection: highest train t with enough events (n >= 20)
    C1 = T[(T.n_eğitim >= 20)].sort_values("t_eğitim", ascending=False)
    out["top"] = C1.head(30).round(4).to_dict("records")
    if len(C1):
        out["chosen"] = _rowdict(C1.iloc[0])
    # robust choice: best train t among configs WITHOUT filters (fewer degrees of freedom)
    C2 = T[(T.n_eğitim >= 20) & (T.filtre == "(filtresiz)")].sort_values("t_eğitim", ascending=False)
    if len(C2):
        out["chosen_nofilter"] = _rowdict(C2.iloc[0])
    out["n_tests"] = int(len(T))
    # pre-registered hypothesis: low vs high inflation expectations (found on 2016-26) on unseen 2003-2016 data
    hyp = []
    for (sname, emode), (ev, en, R, HD) in store.items():
        if emode != "kapanışta":
            continue
        xi = [i for i, x in enumerate(xspecs) if x["kind"] == "hold" and x["H"] == 60]
        if not xi:
            continue
        r = R[xi[0]]
        dts = P.index[ev]
        win = (dts >= pd.Timestamp("2003-01-01")) & (dts < pd.Timestamp("2016-01-01"))
        lo = G["enflasyon beklentisi DÜŞÜK (z<0.5)"][ev] & win
        hi = G["enflasyon beklentisi YÜKSEK (z≥0.5)"][ev] & win
        if lo.sum() >= 3 and hi.sum() >= 3:
            hyp.append({"şok": sname, "düşük_n": int(lo.sum()), "düşük_ort": float(np.nanmean(r[lo])),
                        "yüksek_n": int(hi.sum()), "yüksek_ort": float(np.nanmean(r[hi]))})
    out["hypothesis_2003_2016"] = hyp
    # portfolio simulation for the chosen config (+ plain buy & hold references)
    out["portfolio"] = portfolio(asset, out.get("chosen"), store, F, P, G, xspecs)
    out["portfolio_nofilter"] = portfolio(asset, out.get("chosen_nofilter"), store, F, P, G, xspecs)
    out["ml_gate"] = ml_gate(out.get("chosen_nofilter"), store, F, P, xspecs, ex_i)
    out["intraday"] = intraday(asset, hourly, F, P)
    return out


def _filter_mask(name: str, G, ev):
    if name == "(filtresiz)":
        return np.ones(len(ev), bool)
    if " + " in name and name not in G:
        a, b = name.split(" + ", 1)
        return G[a][ev] & G[b][ev]
    return G[name][ev]


def portfolio(asset, ch, store, F, P, G, xspecs) -> Optional[dict]:
    if not ch:
        return None
    ev, en, R, HD = store[(ch["şok"], ch["giriş"])]
    xi = [i for i, x in enumerate(xspecs) if exit_label(x) == ch["çıkış"]][0]
    m = _filter_mask(ch["filtre"], G, ev)
    r = P.Close.pct_change().fillna(0).values
    tb = np.nan_to_num(F.tbill.values, nan=0.03)
    on = np.zeros(len(r), bool)
    for k in np.where(m)[0]:
        e, hd = en[k], int(HD[xi, k])
        on[e + 1:e + 1 + hd] = True
    out = {}
    cal = P.index
    for name, base, boost in (("Al-tut 1x", 1, 1), ("Al-tut 2x", 2, 2), ("Sadece sinyalde 1x (diğer zaman nakit)", 0, 1),
                              ("Sadece sinyalde 3x", 0, 3), ("Normalde 1x, sinyalde 2x", 1, 2), ("Normalde 1x, sinyalde 3x", 1, 3),
                              ("Normalde 1.5x, sinyalde 3x", 1.5, 3)):
        lev = np.where(on, boost, base).astype(float)
        cash = (1 - np.minimum(lev, 1)) * tb / 252                # idle cash earns T-bills
        fin = np.maximum(lev - 1, 0) * tb / 252                    # leverage pays T-bills
        d = lev * r + cash - fin - np.abs(np.diff(np.r_[base, lev])) * COST
        s = pd.Series(d, index=cal)
        row = {}
        for lab, a, b in (("eğitim", TRAIN_START, EXAM_START), ("sınav", EXAM_START, cal[-1] + pd.Timedelta(days=1))):
            x = s[(s.index >= a) & (s.index < b)]
            eq = (1 + x).cumprod()
            yrs = len(x) / 252
            row[lab] = {"cagr": float(eq.iloc[-1] ** (1 / yrs) - 1), "maxdd": float(1 - (eq / eq.cummax()).min()),
                        "final": float(eq.iloc[-1])}
        row["yearly"] = {int(y): float((1 + g).prod() - 1) for y, g in s[s.index >= TRAIN_START].groupby(s.index[s.index >= TRAIN_START].year)}
        out[name] = row
    out["_exposure"] = float(on[cal >= TRAIN_START].mean())
    return out


def ml_gate(ch, store, F, P, xspecs, ex_i) -> Optional[dict]:
    """Gradient boosting on the event-day state decides which events of the chosen
    (unfiltered) rule to take. Yearly walk-forward in training, trained once for the exam."""
    if not ch:
        return None
    try:
        from sklearn.ensemble import HistGradientBoostingRegressor
    except Exception:
        return None
    ev, en, R, HD = store[(ch["şok"], ch["giriş"])]
    xi = [i for i, x in enumerate(xspecs) if exit_label(x) == ch["çıkış"]][0]
    y = R[xi]
    cols = [c for c in F.columns if c not in ("tbill",)]
    X = F[cols].values[ev]
    years = P.index[ev].year
    pred = np.full(len(ev), np.nan)
    tr = ev < ex_i
    for yr in sorted(set(years[tr])):
        past = (years < yr) & tr
        cur = (years == yr) & tr
        if past.sum() < 15 or not cur.any():
            continue
        m = HistGradientBoostingRegressor(max_depth=2, max_iter=150, learning_rate=0.05, min_samples_leaf=5).fit(X[past], y[past])
        pred[cur] = m.predict(X[cur])
    if tr.sum() >= 15 and (~tr).any():
        m = HistGradientBoostingRegressor(max_depth=2, max_iter=150, learning_rate=0.05, min_samples_leaf=5).fit(X[tr], y[tr])
        pred[~tr] = m.predict(X[~tr])
    take = pred > 0
    f = lambda s: {"n": int(s.sum()), "ort": float(np.nanmean(y[s])) if s.any() else None,
                   "kazanma": float(np.mean(y[s] > 0)) if s.any() else None}
    return {"rule": f"{ch['şok']} · {ch['giriş']} · {ch['çıkış']}",
            "eğitim_hepsi": f(tr & np.isfinite(pred)), "eğitim_model_al": f(tr & take), "eğitim_model_alma": f(tr & np.isfinite(pred) & ~take),
            "sınav_hepsi": f(~tr), "sınav_model_al": f(~tr & take), "sınav_model_alma": f(~tr & ~take)}


def intraday(asset, hourly, F, P) -> Optional[list]:
    """After a shock day (any-panic union), which hour of the NEXT day was the best entry? (last ~2 years)"""
    if hourly is None:
        return None
    h = hourly[hourly.symbol == ASSETS[asset]].set_index("time").sort_index()
    if h.empty:
        return None
    S = shocks(F)["HERHANGİ bir panik (birleşim)"]
    days = P.index[decluster(S)]
    days = days[days >= h.index.min().normalize()]
    out = []
    C = P.Close
    for d in days:
        nxt = h[(h.index.normalize() > d)]
        if nxt.empty:
            continue
        day1 = nxt[nxt.index.normalize() == nxt.index.normalize()[0]]
        exit_px = C[C.index > d]
        if len(exit_px) < 21:
            continue
        x20 = exit_px.iloc[20]
        row = {"tarih": str(d.date()), "şok kapanışında": float(x20 / C.loc[d] - 1)}
        for k in range(min(7, len(day1))):
            row[f"ertesi gün {day1.index[k].strftime('%H:%M')} UTC"] = float(x20 / day1.Close.iloc[k] - 1)
        out.append(row)
    return out


# ================================================================= report
def _p(x, d=1):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"%{x * 100:+.{d}f}"


def report_md(res: dict) -> str:
    L = ["# 🧯 Şok Laboratuvarı v12 — S&P 500 ve Nasdaq-100 panikleri (1990 → bugün)", "",
         f"_Üretim: {res['generated_at'][:16]} UTC · tüm seçimler 1990–2016 verisiyle yapıldı · **{res['exam_start']} sonrası mühürlü sınav**. "
         "İşlem getirileri 1x, komisyon+kayma dahil; günlük OHLC, mum içinde önce stop varsayılır._", ""]
    for asset, r in res["assets"].items():
        L += [f"## {asset}", "", f"Denenen kural sayısı: **{r['n_tests']:,}** (şok × giriş × çıkış × filtre/ikili filtre)", ""]
        b = r["baseline"]
        L += ["**Karşılaştırma tabanı — rastgele bir günde alıp aynı süre tutmak:** " +
              " · ".join(f"{H}g: eğitim {_p(v[0])} / sınav {_p(v[1])}" for H, v in b.items()), ""]
        L += ["_*Sınav fazlası: işlemin getirisi eksi, aynı gün sayısı boyunca sadece endeksi tutmanın normal getirisi. Pozitifse şok gerçekten bir şey katıyor._", "",
              "### 1) Şok türleri (tüm giriş/çıkış varyantlarının ortalaması, işlem başı)", "",
              "| Şok | Kural | Eğitim ort. | Sınav ort. | **Sınav fazlası*** | Eğitim kazanma | Sınav kazanma | Sınavda + |", "|---|---|---|---|---|---|---|---|"]
        for f in r["fam_shock"]:
            n = r["events"].get(f["şok"], (0, 0))
            L.append(f"| {f['şok']} ({n[0]} / {n[1]} olay) | {f['kural']} | {_p(f['eğitim'])} | {_p(f['sınav'])} | **{_p(f['fazla_sınav'])}** | %{f['eğitim_kazanma'] * 100:.0f} | "
                     f"%{f['sınav_kazanma'] * 100:.0f} | %{f['sınav_pozitif'] * 100:.0f} |")
        for title, key, col in (("2) Giriş zamanlaması", "fam_entry", "giriş"), ("3) Çıkış yöntemi", "fam_exit", "çıkış_türü"),
                                ("4) Teknik ve temel filtreler (tek başına)", "fam_filter", "filtre")):
            L += ["", f"### {title}", "", f"| {col} | Kural | Eğitim ort. | Sınav ort. | **Sınav fazlası*** | Eğitim kazanma | Sınav kazanma | Sınavda + |", "|---|---|---|---|---|---|---|---|"]
            for f in r[key]:
                L.append(f"| {f[col]} | {f['kural']} | {_p(f['eğitim'])} | {_p(f['sınav'])} | **{_p(f['fazla_sınav'])}** | %{f['eğitim_kazanma'] * 100:.0f} | "
                         f"%{f['sınav_kazanma'] * 100:.0f} | %{f['sınav_pozitif'] * 100:.0f} |")
        L += ["", "### 5) Eğitimin en iyi 30 kuralı (t-istatistiğine göre, ≥20 olay) ve sınavdaki sonuçları", "",
              "| # | Şok | Giriş | Çıkış | Filtre | Eğitim n / ort / t / kazanma | **Sınav n / ort / kazanma** | Ort. gün |", "|---|---|---|---|---|---|---|---|"]
        for k, t in enumerate(r["top"], 1):
            L.append(f"| {k} | {t['şok']} | {t['giriş']} | {t['çıkış']} | {t['filtre']} | {t['n_eğitim']} / {_p(t['ort_eğitim'])} / {t['t_eğitim']:.1f} / "
                     f"%{t['kazanma_eğitim'] * 100:.0f} | **{t['n_sınav']} / {_p(t['ort_sınav'])} / %{t['kazanma_sınav'] * 100:.0f}** | {t['ort_gün']:.0f} |")
        L += ["", f"_{r['n_tests']:,} kural denendiği için en iyi eğitim t-değerleri şansla da yüksek çıkar; asıl ölçü sınav sütunudur._", ""]
        L += ["### 6) Enflasyon hipotezi — hiç görülmemiş 2003–2015 verisinde (60 gün tut, şok kapanışında al)", "",
              "| Şok | Enflasyon beklentisi düşük: n / ort | Yüksek: n / ort | Hipotez tuttu mu? |", "|---|---|---|---|"]
        for hrow in r["hypothesis_2003_2016"]:
            ok = "✅" if hrow["düşük_ort"] > hrow["yüksek_ort"] else "❌"
            L.append(f"| {hrow['şok']} | {hrow['düşük_n']} / {_p(hrow['düşük_ort'])} | {hrow['yüksek_n']} / {_p(hrow['yüksek_ort'])} | {ok} |")
        hy = r["hypothesis_2003_2016"]
        if hy:
            L += ["", f"**Özet:** {sum(h['düşük_ort'] > h['yüksek_ort'] for h in hy)}/{len(hy)} şok türünde düşük enflasyon beklentisindeki panikler daha iyi sonuçlandı."]
        for key, title in (("portfolio", "7) Seçilen kural (eğitimin en iyisi) — portföy ve kaldıraç"),
                           ("portfolio_nofilter", "8) Seçilen FİLTRESİZ kural — portföy ve kaldıraç")):
            pf = r.get(key)
            ch = r.get("chosen" if key == "portfolio" else "chosen_nofilter")
            if not pf or not ch:
                continue
            L += ["", f"### {title}", "", f"**Kural:** {ch['şok']} · {ch['giriş']} · {ch['çıkış']} · filtre: {ch['filtre']} · piyasada zamanın %{pf['_exposure'] * 100:.0f}'i", "",
                  "| Strateji | Eğitim yıllık / DD | **Sınav yıllık / DD** | Sınav sonu (1→) |", "|---|---|---|---|"]
            for name, v in pf.items():
                if name.startswith("_"):
                    continue
                L.append(f"| {name} | {_p(v['eğitim']['cagr'])} / %{v['eğitim']['maxdd'] * 100:.0f} | **{_p(v['sınav']['cagr'])} / %{v['sınav']['maxdd'] * 100:.0f}** | "
                         f"{v['sınav']['final']:.2f} |")
            yrs = sorted(next(iter(v for k_, v in pf.items() if not k_.startswith("_")))["yearly"])
            L += ["", "| Yıl | " + " | ".join(k_ for k_ in pf if not k_.startswith("_")) + " |", "|---" * (1 + sum(1 for k_ in pf if not k_.startswith("_"))) + "|"]
            for y in yrs:
                L.append(f"| {y} | " + " | ".join(_p(v["yearly"].get(y), 0) for k_, v in pf.items() if not k_.startswith("_")) + " |")
        mg = r.get("ml_gate")
        if mg:
            L += ["", "### 9) Makine öğrenmesi kapısı (olay günündeki tüm teknik+temel durum, yıllık walk-forward)", "", f"Kural: {mg['rule']}", "",
                  "| | Tüm olaylar | Modelin AL dedikleri | Modelin ALMA dedikleri |", "|---|---|---|---|"]
            for lab in ("eğitim", "sınav"):
                a, b_, c = mg[f"{lab}_hepsi"], mg[f"{lab}_model_al"], mg[f"{lab}_model_alma"]
                def fmt(z):
                    kz = "—" if z["kazanma"] is None else f"%{z['kazanma'] * 100:.0f}"
                    return f"n={z['n']} · {_p(z['ort'])} · kazanma {kz}"
                L.append(f"| {lab} | {fmt(a)} | {fmt(b_)} | {fmt(c)} |")
        it = r.get("intraday")
        if it:
            L += ["", "### 10) Gün içi giriş saati (son ~2 yıl, 20 gün tutma getirisi)", ""]
            keys = sorted({k for row in it for k in row if k != "tarih"})
            L += ["| Tarih | " + " | ".join(keys) + " |", "|---" * (len(keys) + 1) + "|"]
            for row in it:
                L.append(f"| {row['tarih']} | " + " | ".join(_p(row.get(k)) for k in keys) + " |")
        L.append("")
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="shock_data")
    ap.add_argument("--out", default="shock_out")
    a = ap.parse_args()
    px, fred, hourly = load(a.data)
    res = research(px, fred, hourly)
    os.makedirs(a.out, exist_ok=True)
    for asset, r in res["assets"].items():
        T = r.pop("_table")
        T = pd.concat([T[T.tek_filtre], T[~T.tek_filtre].nlargest(30000, "t_eğitim")])
        T.to_csv(os.path.join(a.out, f"shock_all_rules_{asset}.csv.gz"), index=False, compression="gzip", float_format="%.5g")
    open(os.path.join(a.out, "shock_report.md"), "w", encoding="utf-8").write(report_md(res))
    json.dump(json.loads(json.dumps(res, default=str)), open(os.path.join(a.out, "shock_results.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("[shock] bitti", flush=True)


if __name__ == "__main__":
    main()
