"""
Copper Lab (v14) — every strategy family on COMEX copper (2000 -> today), sealed exam from 2017
==============================================================================================
Instrument: Bitget COPPERUSDT perpetual. Its own history is short, so the test runs on COMEX copper futures (HG=F,
the contract the perp tracks) and the Bitget contract is checked separately (price ratio, funding cost).

Families (every view in three modes: long/short, long-only, short-only):
  TREND     moving-average crosses, price vs MA, time-series momentum (5d-12m), TSMOM ensemble, Donchian/turtle
            breakouts, MACD (fast, slow/ATVS direction, zero line), EMA slope, ADX-filtered momentum
  MEANREV   RSI(2), RSI(14), Bollinger reversion, 5-day z-score, IBS, down/up streaks
  BREAKOUT  volatility squeeze breakout, ATR range expansion
  SEASONAL  month-of-year and weekday learnt WALK-FORWARD (only past years), turn-of-month
  MACRO     copper/gold ratio trend, dollar (DXY, broad), yuan, AUD, real yield, breakevens, oil, S&P trend, China
            equities, miners leading copper, curve steepening, credit spreads, VIX regime, OECD leading indicators,
            industrial production
  COT       CFTC speculators / managed money: contrarian extremes and positioning trend (published-date lagged)
  ML        gradient boosting on all features, retrained every year on past data only
  ATVS      the crypto EMA/X rules applied to copper (the source document says they fail on metals; checked here)
Then: pairs (every top trend/mean-reversion view x every macro/COT filter), exit overlays (ATR trailing stops,
volatility targeting) on the best training candidates, portfolio integration (risk parity with copper as a 5th
asset, with and without timing), Bitget contract check and an hourly exploration (last ~730 days, not used to choose).

Honesty protocol: positions decided at the close, earn the NEXT day; costs on turnover; longs pay extra perp
funding; everything is CHOSEN on 2000-2016 only; 2017+ is a sealed exam; family averages; Deflated Sharpe for the
number of trials; every strategy is compared with simply holding copper (alpha t-stat).
CLI: python copper_lab.py --data copper_data --out copper_out
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import os
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

TRAIN0, EXAM0 = pd.Timestamp("2000-01-01"), pd.Timestamp("2017-01-01")
COST = 0.0008                 # per unit of turnover (taker fee + slippage)
LONG_FUNDING = 0.03           # extra yearly cost of holding a long perp over futures (funding premium)
FUNDING_SCENARIOS = (0.0, 0.03, 0.08, 0.158)   # yearly funding paid by longs and received by shorts (Bitget 2026: 15.8%)
MIN_TRAIN_YEARS = 6


# ================================================================== data
def load(data: str):
    D = pd.read_csv(os.path.join(data, "daily.csv.gz"), parse_dates=["date"])
    px = {s: g.set_index("date").sort_index()[["Open", "High", "Low", "Close"]] for s, g in D.groupby("symbol")}
    rd = lambda f, **k: pd.read_csv(os.path.join(data, f), **k) if os.path.exists(os.path.join(data, f)) else None  # noqa: E731
    fred = rd("fred.csv.gz", parse_dates=["date", "avail"])
    cot = rd("cot.csv.gz", parse_dates=["date", "avail"])
    hourly = rd("hourly.csv.gz", parse_dates=["time"])
    bg = json.load(open(os.path.join(data, "bitget_copper.json"))) if os.path.exists(os.path.join(data, "bitget_copper.json")) else {}
    bgc = rd("bitget_candles.csv", parse_dates=["date"])
    return px, fred, cot, hourly, bg, bgc


def asof(tbl: Optional[pd.DataFrame], cal: pd.DatetimeIndex, sid: Optional[str] = None, col: str = "value") -> pd.Series:
    if tbl is None or len(tbl) == 0:
        return pd.Series(np.nan, index=cal)
    s = tbl[tbl.series == sid] if sid else tbl
    s = s.dropna(subset=[col]).sort_values("avail")
    if s.empty:
        return pd.Series(np.nan, index=cal)
    k = pd.Series(s[col].values, index=pd.DatetimeIndex(s.avail.values))
    k = k[~k.index.duplicated(keep="last")]
    return k.reindex(k.index.union(cal)).ffill().reindex(cal)


# ================================================================== indicators
def ema(x, n): return x.ewm(span=n, adjust=False, min_periods=n).mean()
def sma(x, n): return x.rolling(n, min_periods=n).mean()


def rsi(c, n):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def atr(h, l, c, n=14):
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def adx(h, l, c, n=14):
    up, dn = h.diff(), -l.diff()
    pdm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=c.index)
    ndm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=c.index)
    a = atr(h, l, c, n)
    pdi = 100 * pdm.ewm(alpha=1 / n, adjust=False).mean() / a
    ndi = 100 * ndm.ewm(alpha=1 / n, adjust=False).mean() / a
    dx = 100 * (pdi - ndi).abs() / (pdi + ndi).replace(0, np.nan)
    return dx.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def hold_state(enter_long, exit_long, enter_short=None, exit_short=None) -> np.ndarray:
    """Stateful position from entry/exit events (evaluated at each close)."""
    n = len(enter_long)
    el, xl = np.asarray(enter_long, bool), np.asarray(exit_long, bool)
    es = np.zeros(n, bool) if enter_short is None else np.asarray(enter_short, bool)
    xs = np.zeros(n, bool) if exit_short is None else np.asarray(exit_short, bool)
    out, p = np.zeros(n), 0
    for i in range(n):
        if p == 1 and xl[i]:
            p = 0
        elif p == -1 and xs[i]:
            p = 0
        if p == 0:
            if el[i]:
                p = 1
            elif es[i]:
                p = -1
        out[i] = p
    return out


def hold_n(event_long, n, event_short=None) -> np.ndarray:
    """Event -> position for the next n days (new events extend)."""
    L = pd.Series(np.asarray(event_long, float)).rolling(n, min_periods=1).max().to_numpy()
    if event_short is None:
        return L
    S = pd.Series(np.asarray(event_short, float)).rolling(n, min_periods=1).max().to_numpy()
    return np.where(L > 0, 1.0, np.where(S > 0, -1.0, 0.0))


# ================================================================== features (all known at the close of each day)
def frame(px, fred, cot) -> pd.DataFrame:
    P = px["HG=F"]
    P = P[(P.index >= pd.Timestamp("1995-01-01")) & (P.Close > 0)].dropna(subset=["Close"])
    bad = P.Close.pct_change().abs() > 0.25                     # data errors (copper never moved 25% in a day)
    P = P[~bad]
    cal = P.index
    F = pd.DataFrame(index=cal)
    F["o"], F["h"], F["l"], F["c"] = P.Open, P.High, P.Low, P.Close
    F["r"] = F.c.pct_change()
    y = lambda s: px[s].Close.reindex(cal).ffill(limit=5) if s in px else pd.Series(np.nan, index=cal)  # noqa: E731
    for k, s in (("gold", "GC=F"), ("oil", "CL=F"), ("dxy", "DX-Y.NYB"), ("aud", "AUDUSD=X"), ("cny", "CNY=X"),
                 ("spx", "^GSPC"), ("vix", "^VIX"), ("fxi", "FXI"), ("shc", "000001.SS"), ("fcx", "FCX"), ("copx", "COPX"),
                 ("silver", "SI=F")):
        F[k] = y(s)
    for k, sid in (("realy", "DFII10"), ("bei", "T10YIE"), ("curve", "T10Y2Y"), ("bdollar", "DTWEXBGS"),
                   ("usdcny_f", "DEXCHUS"), ("usdaud_f", "DEXUSAL"), ("tbill", "DGS3MO"), ("hy", "BAMLH0A0HYM2"),
                   ("nfci", "NFCI"), ("indpro", "INDPRO"), ("cli_cn", "CHNLOLITONOSTSAM"), ("cli_us", "USALOLITONOSTSAM")):
        F[k] = asof(fred, cal, sid)
    if cot is not None and len(cot):
        for col in ("spec_long", "spec_short", "oi", "mm_long", "mm_short"):
            F[col] = asof(cot, cal, None, col) if col in cot else np.nan
        F["spec_net"] = (F.spec_long - F.spec_short) / F.oi
        F["mm_net"] = (F.mm_long - F.mm_short) / F.oi
    else:
        F["spec_net"] = F["mm_net"] = np.nan
    F["atr"] = atr(F.h, F.l, F.c)
    F["rvol20"] = F.r.rolling(20).std() * math.sqrt(252)
    return F


# ================================================================== strategy views
def views(F: pd.DataFrame) -> Dict[str, Tuple[str, np.ndarray]]:
    """name -> (family, direction array in {-1, 0, +1} decided at the close)."""
    c, h, l = F.c, F.h, F.l
    V: Dict[str, Tuple[str, np.ndarray]] = {}
    sgn = lambda x: np.sign(np.nan_to_num(np.asarray(x, float)))  # noqa: E731
    # ---- trend
    for f, s in ((5, 20), (10, 30), (10, 50), (20, 50), (20, 100), (50, 100), (50, 200), (100, 200)):
        V[f"SMA {f}/{s} kesişimi"] = ("TREND", sgn(sma(c, f) - sma(c, s)))
    for n in (20, 50, 100, 150, 200, 250):
        V[f"fiyat > SMA{n}"] = ("TREND", sgn(c - sma(c, n)))
    for L in (5, 10, 21, 42, 63, 126, 189, 252):
        V[f"momentum {L}g"] = ("TREND", sgn(c / c.shift(L) - 1))
    ens = sum(sgn(c / c.shift(L) - 1) for L in (21, 63, 126, 252)) / 4
    V["momentum topluluğu 1-3-6-12 ay"] = ("TREND", sgn(ens))
    for n in (10, 20, 55, 100, 200):
        hi, lo = h.rolling(n).max().shift(1), l.rolling(n).min().shift(1)
        hx, lx = h.rolling(max(2, n // 2)).max().shift(1), l.rolling(max(2, n // 2)).min().shift(1)
        V[f"Donchian {n} kırılımı"] = ("TREND", hold_state(c > hi, c < lx, c < lo, c > hx))
    m = ema(c, 12) - ema(c, 26)
    V["MACD 12/26/9"] = ("TREND", sgn(m - ema(m, 9)))
    V["MACD sıfır çizgisi"] = ("TREND", sgn(m))
    m2 = ema(c, 28) - ema(c, 36)
    V["yavaş MACD 28/36/20 (ATVS yönü)"] = ("TREND", sgn(m2 - ema(m2, 20)))
    for n in (20, 50, 100):
        e = ema(c, n)
        V[f"EMA{n} eğimi"] = ("TREND", sgn(e - e.shift(5)))
    ax = adx(h, l, c)
    V["momentum 63g (ADX>20 iken)"] = ("TREND", np.where(ax.to_numpy() > 20, sgn(c / c.shift(63) - 1), 0.0))
    # ---- mean reversion
    r2, r14 = rsi(c, 2), rsi(c, 14)
    for lo_, hi_ in ((5, 95), (10, 90), (20, 80)):
        V[f"RSI(2) {lo_}/{hi_} dönüş"] = ("MEANREV", hold_state(r2 < lo_, r2 > 50, r2 > hi_, r2 < 50))
    V["RSI(14) 30/70 dönüş"] = ("MEANREV", hold_state(r14 < 30, r14 > 50, r14 > 70, r14 < 50))
    mid, sd = sma(c, 20), c.rolling(20).std()
    for k in (2.0, 2.5):
        V[f"Bollinger {k}σ dönüş"] = ("MEANREV", hold_state(c < mid - k * sd, c > mid, c > mid + k * sd, c < mid))
    z5 = (c / c.shift(5) - 1) / (F.r.rolling(60).std() * math.sqrt(5))
    for k in (1.5, 2.0):
        V[f"5g z-skoru ±{k} dönüş (5g tut)"] = ("MEANREV", hold_n(z5 < -k, 5, z5 > k))
    ibs = (c - l) / (h - l).replace(0, np.nan)
    V["IBS 0.2/0.8 (1g)"] = ("MEANREV", np.where(ibs < 0.2, 1.0, np.where(ibs > 0.8, -1.0, 0.0)))
    dn = (c < c.shift()).astype(int)
    up = (c > c.shift()).astype(int)
    ds = dn.groupby((dn == 0).cumsum()).cumsum()
    us = up.groupby((up == 0).cumsum()).cumsum()
    for k in (3, 4, 5):
        V[f"{k} gün seri sonrası ters (5g)"] = ("MEANREV", hold_n(ds >= k, 5, us >= k))
    # ---- breakout / volatility
    bw = (4 * sd / mid)
    sq = bw < bw.rolling(252, min_periods=126).quantile(0.2)
    hi20, lo20 = h.rolling(20).max().shift(1), l.rolling(20).min().shift(1)
    V["sıkışma kırılımı (20g tut)"] = ("BREAKOUT", hold_n(sq.shift(1).fillna(False) & (c > hi20), 20,
                                                          sq.shift(1).fillna(False) & (c < lo20)))
    a = F.atr.shift(1)
    for k in (1.0, 1.5, 2.0):
        V[f"ATR genişleme {k}x (10g tut)"] = ("BREAKOUT", hold_n(c - c.shift() > k * a, 10, c.shift() - c > k * a))
    # ---- seasonal (walk-forward: each year uses only earlier years)
    V["ay mevsimselliği (ileri yürüyen)"] = ("SEASONAL", seasonal(F, "month"))
    V["haftanın günü (ileri yürüyen)"] = ("SEASONAL", seasonal(F, "dow"))
    dom = pd.Series(F.index.day, index=F.index)
    nxt_month = pd.Series(F.index.month, index=F.index).shift(-1)
    last_days = (pd.Series(F.index.month, index=F.index) != nxt_month)   # calendar only, known in advance
    tom = last_days | last_days.shift(1).fillna(False) | (dom <= 3)
    V["ay dönümü (son 2 + ilk 3 gün)"] = ("SEASONAL", tom.astype(float).to_numpy())
    # ---- macro / fundamental
    ch = lambda x, n=63: x - x.shift(n)  # noqa: E731
    mom = lambda x, n=63: x / x.shift(n) - 1  # noqa: E731
    ratio = c / F.gold
    for n in (50, 100, 200):
        V[f"bakır/altın oranı > SMA{n}"] = ("MACRO", sgn(ratio - sma(ratio, n)))
    V["dolar (DXY) 3 ay düşüyor"] = ("MACRO", sgn(-mom(F.dxy)))
    V["geniş dolar endeksi 3 ay düşüyor"] = ("MACRO", sgn(-mom(F.bdollar)))
    V["yuan güçleniyor (USD/CNY 3 ay düşüş)"] = ("MACRO", sgn(-mom(F.usdcny_f.fillna(F.cny))))
    V["AUD 3 ay yükseliyor"] = ("MACRO", sgn(mom(F.aud)))
    V["reel faiz 3 ay düşüyor"] = ("MACRO", sgn(-ch(F.realy)))
    V["enflasyon beklentisi 3 ay yükseliyor"] = ("MACRO", sgn(ch(F.bei)))
    V["petrol 3 ay yükseliyor"] = ("MACRO", sgn(mom(F.oil)))
    V["S&P 500 > SMA200"] = ("MACRO", sgn(F.spx - sma(F.spx, 200)))
    V["Çin hisseleri (FXI) 3 ay yükseliyor"] = ("MACRO", sgn(mom(F.fxi)))
    V["Şanghay endeksi 3 ay yükseliyor"] = ("MACRO", sgn(mom(F.shc)))
    V["madenciler bakırı öncülüyor (FCX−bakır 1 ay)"] = ("MACRO", sgn(mom(F.fcx, 21) - mom(c, 21)))
    V["getiri eğrisi 3 ay dikleşiyor"] = ("MACRO", sgn(ch(F.curve)))
    V["kredi spreadi 3 ay daralıyor"] = ("MACRO", sgn(-ch(F.hy)))
    V["VIX < 20"] = ("MACRO", np.where(F.vix.to_numpy() < 20, 1.0, np.where(F.vix.to_numpy() >= 20, -1.0, 0.0)))
    V["finansal koşullar gevşiyor (NFCI 3 ay)"] = ("MACRO", sgn(-ch(F.nfci)))
    V["Çin öncü göstergesi yükseliyor"] = ("MACRO", sgn(ch(F.cli_cn, 63)))
    V["ABD öncü göstergesi yükseliyor"] = ("MACRO", sgn(ch(F.cli_us, 63)))
    ip = F.indpro / F.indpro.shift(252) - 1
    V["sanayi üretimi ivmeleniyor"] = ("MACRO", sgn(ch(ip)))
    V["altın/gümüş oranı düşüyor (risk iştahı)"] = ("MACRO", sgn(-mom(F.gold / F.silver)))
    # ---- positioning (CFTC)
    for k, col in (("spekülatör", "spec_net"), ("fon (managed money)", "mm_net")):
        x = F[col]
        pct = x.rolling(756, min_periods=260).rank(pct=True)          # 3-year percentile of positioning
        V[f"COT {k} aşırı uç → ters"] = ("COT", np.where(pct.to_numpy() > 0.9, -1.0, np.where(pct.to_numpy() < 0.1, 1.0, 0.0)))
        V[f"COT {k} 4 hafta artıyor → aynı yön"] = ("COT", sgn(ch(x, 20)))
    return V


def seasonal(F: pd.DataFrame, kind: str) -> np.ndarray:
    key = F.index.month if kind == "month" else F.index.dayofweek
    fwd = F.r.shift(-1)                       # return earned by a position held after this close
    years = F.index.year
    out = np.zeros(len(F))
    for yr in sorted(set(years)):
        past = (years < yr) & np.isfinite(fwd.to_numpy())
        past[np.flatnonzero(years < yr)[-1:]] = False                     # its label lies in the current year
        if len(set(years[past])) < 5:
            continue
        m = pd.Series(fwd[past].values, index=key[past]).groupby(level=0).mean()
        cur = years == yr
        k = key[cur]
        if kind == "month":
            good, bad = set(m.nlargest(4).index), set(m.nsmallest(4).index)
        else:
            good, bad = {m.idxmax()}, {m.idxmin()}
        out[cur] = [1.0 if x in good else (-1.0 if x in bad else 0.0) for x in k]
    return out


def ml_view(F: pd.DataFrame, V: Dict[str, Tuple[str, np.ndarray]]) -> Optional[np.ndarray]:
    """Gradient boosting on every view + raw features; yearly walk-forward (trains only on finished past years)."""
    try:
        from sklearn.ensemble import HistGradientBoostingRegressor
    except Exception:
        return None
    X = np.column_stack([v for _, v in V.values()] + [F[c].pct_change(21).to_numpy() for c in ("c", "gold", "oil", "dxy", "spx")]
                        + [F.rvol20.to_numpy(), F.vix.to_numpy()])
    X = np.where(np.isfinite(X), X, np.nan)
    y = (F.c.shift(-20) / F.c - 1).to_numpy()
    years = F.index.year
    out = np.zeros(len(F))
    for yr in range(2004, years.max() + 1):
        tr = (years < yr) & np.isfinite(y)
        tr &= np.arange(len(F)) < np.searchsorted(F.index.values, np.datetime64(f"{yr}-01-01")) - 20   # no label overlap
        cur = years == yr
        if tr.sum() < 750 or not cur.any():
            continue
        m = HistGradientBoostingRegressor(max_depth=3, max_iter=200, learning_rate=0.05, min_samples_leaf=50)
        m.fit(X[tr], y[tr])
        out[cur] = np.sign(m.predict(X[cur]))
    return out


def atvs_view(F: pd.DataFrame) -> Dict[str, np.ndarray]:
    """Crypto ATVS rules on copper: trades -> daily positions (entry at next open ~ next close here)."""
    try:
        import atvs_rules as A
    except Exception:
        return {}
    df = F[["o", "h", "l", "c"]].rename(columns={"o": "open", "h": "high", "l": "low", "c": "close"})
    out = {}
    for rule in ("EMA", "X"):
        pos = np.zeros(len(df))
        t = A.backtest(df, rule)
        for _, row in t.iterrows():
            i, k = int(row.bar), int(row.k)
            pos[i:i + k] = row.side
        out[f"ATVS {rule} kuralı"] = pos
    return out


# ================================================================== evaluation
def strat_returns(pos: np.ndarray, F: pd.DataFrame, cost=None, long_fund=None, symmetric=False) -> np.ndarray:
    """symmetric=False: longs pay long_fund, shorts receive nothing (conservative default used for SELECTION).
    symmetric=True : longs pay and shorts receive the same funding (how a perp actually settles; scenarios)."""
    cost = COST if cost is None else cost
    long_fund = LONG_FUNDING if long_fund is None else long_fund     # read at call time (can be set from Bitget data)
    p = np.nan_to_num(np.asarray(pos, float))
    r_next = np.r_[F.r.to_numpy()[1:], np.nan]
    turn = np.abs(np.diff(np.r_[0.0, p]))
    fund = p if symmetric else np.clip(p, 0, None)
    ret = p * np.nan_to_num(r_next) - cost * turn - fund * long_fund / 252
    return ret                                                    # ret[i] = P&L of the position chosen at close i


def stats(ret: np.ndarray, F: pd.DataFrame, a, b, bh: Optional[np.ndarray] = None, pos=None) -> dict:
    m = (F.index >= a) & (F.index < b)
    x = ret[m]
    x = x[np.isfinite(x)]
    if len(x) < 250:
        return {}
    eq = np.cumprod(1 + x)
    yrs = len(x) / 252
    sh = x.mean() / x.std() * math.sqrt(252) if x.std() > 0 else 0.0
    d = {"cagr": float(eq[-1] ** (1 / yrs) - 1), "sharpe": float(sh), "maxdd": float(1 - (eq / np.maximum.accumulate(eq)).min()),
         "n": int(len(x))}
    if pos is not None:
        p = np.nan_to_num(np.asarray(pos, float))[m]
        d["exposure"] = float((p != 0).mean())
        d["trades"] = int((np.abs(np.diff(p)) > 0).sum())
    if bh is not None:
        y = bh[m][: len(x)]
        ok = np.isfinite(y)
        if ok.sum() > 250:
            X = np.column_stack([np.ones(ok.sum()), y[ok]])
            beta, *_ = np.linalg.lstsq(X, x[ok], rcond=None)
            res = x[ok] - X @ beta
            se = math.sqrt(res.var(ddof=2) * np.linalg.inv(X.T @ X)[0, 0])
            d["alpha_ann"] = float(beta[0] * 252)
            d["alpha_t"] = float(beta[0] / se) if se > 0 else 0.0
            d["beta"] = float(beta[1])
    return d


def deflated_sharpe(sr_annual: float, n_obs: int, n_trials: int, sr_var: float, skew=0.0, kurt=3.0) -> float:
    """Bailey & Lopez de Prado: probability that the true Sharpe > 0 after picking the best of n_trials."""
    from math import erf, sqrt, log, e
    sr = sr_annual / math.sqrt(252)
    v = max(sr_var / 252, 1e-12)
    em = 0.5772156649
    z = lambda p: math.sqrt(2) * _erfinv(2 * p - 1)  # noqa: E731
    sr0 = math.sqrt(v) * ((1 - em) * z(1 - 1 / max(n_trials, 2)) + em * z(1 - 1 / (max(n_trials, 2) * e)))
    den = sqrt(max(1e-12, 1 - skew * sr + (kurt - 1) / 4 * sr ** 2))
    zz = (sr - sr0) * sqrt(max(n_obs - 1, 1)) / den
    return 0.5 * (1 + erf(zz / sqrt(2)))


def _erfinv(y: float) -> float:
    a = 0.147
    ln = math.log(max(1e-300, 1 - y * y))
    t = 2 / (math.pi * a) + ln / 2
    return math.copysign(math.sqrt(math.sqrt(t * t - ln / a) - t), y)


MODES = {"çift yön": lambda v: v, "yalnız long": lambda v: np.clip(v, 0, None), "yalnız short": lambda v: np.clip(v, None, 0)}


def research(px, fred, cot, hourly=None, bg=None, bgc=None, fast=False) -> dict:
    F = frame(px, fred, cot)
    F = F[F.index >= pd.Timestamp("1998-01-01")]
    V = views(F)
    V.update({k: ("ATVS", v) for k, v in atvs_view(F).items()})
    mlv = None if fast else ml_view(F, V)
    if mlv is not None:
        V["makine öğrenmesi (yıllık ileri yürüyen)"] = ("ML", mlv)
    end = F.index[-1] + pd.Timedelta(days=1)
    bh = strat_returns(np.ones(len(F)), F)
    res = {"generated_at": pd.Timestamp.now("UTC").isoformat(), "first": str(F.index[0].date()), "last": str(F.index[-1].date()),
           "bh": {"eğitim": stats(bh, F, TRAIN0, EXAM0), "sınav": stats(bh, F, EXAM0, end)}}
    rows, store = [], {}

    def add(name, fam, mode, pos, kind="tek"):
        ret = strat_returns(pos, F)
        tr, ex = stats(ret, F, TRAIN0, EXAM0, bh, pos), stats(ret, F, EXAM0, end, bh, pos)
        if not tr or not ex:
            return
        valid_years = ((np.abs(np.nan_to_num(pos)) > 0) | np.isfinite(pos))[(F.index >= TRAIN0) & (F.index < EXAM0)]
        rows.append({"strateji": name, "aile": fam, "yön": mode, "tür": kind,
                     "eğitim_sharpe": tr["sharpe"], "eğitim_yıllık": tr["cagr"], "eğitim_dd": tr["maxdd"],
                     "eğitim_alfa_t": tr.get("alpha_t", 0), "eğitim_işlem": tr.get("trades", 0), "eğitim_piyasada": tr.get("exposure", 0),
                     "sınav_sharpe": ex["sharpe"], "sınav_yıllık": ex["cagr"], "sınav_dd": ex["maxdd"],
                     "sınav_alfa_t": ex.get("alpha_t", 0), "sınav_alfa": ex.get("alpha_ann", 0), "sınav_işlem": ex.get("trades", 0),
                     "sınav_piyasada": ex.get("exposure", 0), "beta": ex.get("beta", 0)})
        store[(name, mode)] = pos

    # data coverage: a view counts in training only if its inputs existed for >= MIN_TRAIN_YEARS before 2017
    cover = {}
    for name, (fam, v) in V.items():
        live = pd.Series(np.abs(np.nan_to_num(v)) > 0, index=F.index)
        first = live[live].index.min() if live.any() else EXAM0
        cover[name] = (EXAM0 - first).days / 365.25 if pd.notna(first) else 0
    singles = [n for n in V if cover[n] >= MIN_TRAIN_YEARS]
    res["skipped_short_history"] = sorted(n for n in V if cover[n] < MIN_TRAIN_YEARS)
    for name in singles:
        fam, v = V[name]
        for mode, f in MODES.items():
            add(name, fam, mode, f(v))
    T = pd.DataFrame(rows)
    # ---- pairs: trend/mean-rev/breakout/seasonal base x macro/COT filter (filter must agree with the base direction)
    base = T[T.aile.isin(["TREND", "MEANREV", "BREAKOUT", "SEASONAL"])].sort_values("eğitim_sharpe", ascending=False)
    base = base.drop_duplicates(["strateji", "yön"]).head(12 if fast else 40)
    filt = [n for n in singles if V[n][0] in ("MACRO", "COT")]
    for _, b in base.iterrows():
        bp = store[(b.strateji, b.yön)]
        for fn in filt:
            fv = V[fn][1]
            pos = np.where(np.sign(bp) == np.sign(fv), bp, 0.0)
            add(f"{b.strateji} + {fn}", "İKİLİ", b.yön, pos, "ikili")
    T = pd.DataFrame(rows)
    # ---- exit overlays on the best training candidates
    top = T.sort_values("eğitim_sharpe", ascending=False).drop_duplicates(["strateji", "yön"]).head(10 if fast else 25)
    for _, t in top.iterrows():
        pos = store[(t.strateji, t.yön)]
        for k in (2.0, 3.0):
            add(f"{t.strateji} · iz süren stop {k:g} ATR", "ÇIKIŞ", t.yön, trail_overlay(pos, F, k), "çıkış")
        scale = np.clip(0.15 / F.rvol20.to_numpy(), 0, 2)
        add(f"{t.strateji} · oynaklık hedefi %15", "ÇIKIŞ", t.yön, np.nan_to_num(pos * scale), "çıkış")
    T = pd.DataFrame(rows)
    n_trials = len(T)
    sr_var = float(T.eğitim_sharpe.var())
    ntr = int(((F.index >= TRAIN0) & (F.index < EXAM0)).sum())
    T["deflated_sharpe"] = [deflated_sharpe(s, ntr, n_trials, sr_var) for s in T.eğitim_sharpe]
    res["n_trials"] = n_trials
    # ---- funding scenarios: the same strategies under 0 / 3 / 8 / 15.8 % yearly funding (longs pay, shorts receive)
    sc_rows = []
    keys = list(dict.fromkeys([(r.strateji, r.yön) for r in T.itertuples()]))
    for (nm, md) in keys:
        pos = store[(nm, md)]
        row = {"strateji": nm, "yön": md}
        for f in FUNDING_SCENARIOS:
            ret = strat_returns(pos, F, long_fund=f, symmetric=True)
            tr, ex = stats(ret, F, TRAIN0, EXAM0), stats(ret, F, EXAM0, end)
            row[f"eğ_{f}"] = tr.get("sharpe", np.nan)
            row[f"sı_{f}"] = ex.get("sharpe", np.nan)
            row[f"sı_yıllık_{f}"] = ex.get("cagr", np.nan)
        row["eğ_en_kötü"] = min(row[f"eğ_{f}"] for f in FUNDING_SCENARIOS)
        sc_rows.append(row)
    SC = pd.DataFrame(sc_rows)
    tc = T.drop_duplicates(["strateji", "yön"]).set_index(["strateji", "yön"])
    SC["eğitim_işlem"] = [tc.loc[(a, b), "eğitim_işlem"] for a, b in zip(SC.strateji, SC.yön)]
    robust = SC[SC.eğitim_işlem >= 20].sort_values("eğ_en_kötü", ascending=False)
    res["funding_robust_pick"] = _row(robust.iloc[0]) if len(robust) else None
    res["funding_table"] = robust.head(15).round(3).to_dict("records")
    bhr = {f"{f}": stats(strat_returns(np.ones(len(F)), F, long_fund=f, symmetric=True), F, EXAM0, end).get("cagr") for f in FUNDING_SCENARIOS}
    res["bh_by_funding"] = bhr
    for key in ("chosen", "chosen_single"):
        c = res.get(key) or (None)
    res["_scenarios"] = SC
    # ---- families
    res["families"] = (T[T.tür == "tek"].groupby(["aile", "yön"]).agg(
        strateji=("strateji", "size"), eğitim_sharpe=("eğitim_sharpe", "mean"), sınav_sharpe=("sınav_sharpe", "mean"),
        sınav_alfa_t=("sınav_alfa_t", "mean"), sınav_pozitif=("sınav_sharpe", lambda s: float((s > 0).mean())))
        .reset_index().sort_values("sınav_sharpe", ascending=False).round(3).to_dict("records"))
    res["top_train"] = T.sort_values("eğitim_sharpe", ascending=False).head(30).round(3).to_dict("records")
    res["singles_all"] = T[T.tür == "tek"].sort_values("eğitim_sharpe", ascending=False).round(3).to_dict("records")
    # ---- the choice (training only): best single with enough trades, and best overall
    cand = T[(T.eğitim_işlem >= 20)].sort_values("eğitim_sharpe", ascending=False)
    res["chosen"] = _row(cand.iloc[0]) if len(cand) else None
    cs = cand[cand.tür == "tek"]
    res["chosen_single"] = _row(cs.iloc[0]) if len(cs) else None
    for key in ("chosen", "chosen_single"):
        c = res.get(key)
        if c:
            r_ = res["_scenarios"].set_index(["strateji", "yön"]).loc[(c["strateji"], c["yön"])]
            c["senaryolar"] = {f"{f}": {"sınav_sharpe": float(r_[f"sı_{f}"]), "sınav_yıllık": float(r_[f"sı_yıllık_{f}"])} for f in FUNDING_SCENARIOS}
    # ---- robustness of the chosen single: neighbours in the same family/mode
    if res["chosen_single"]:
        ch = res["chosen_single"]
        nb = T[(T.tür == "tek") & (T.aile == ch["aile"]) & (T.yön == ch["yön"])]
        res["chosen_neighbours"] = {"n": int(len(nb)), "train_pos": float((nb.eğitim_sharpe > 0).mean()),
                                    "exam_pos": float((nb.sınav_sharpe > 0).mean()), "exam_mean": float(nb.sınav_sharpe.mean())}
    # ---- portfolio integration
    res["portfolio"] = portfolio(px, fred, F, store, res)
    res["bitget"] = bitget_check(F, bg or {}, bgc)
    res["hourly"] = hourly_explore(hourly) if hourly is not None else None
    res["_table"] = T
    res.pop("_scenarios", None)
    res["yearly_chosen"] = yearly(res, store, F)
    return res


def _row(r: pd.Series) -> dict:
    return {k: (round(float(v), 4) if isinstance(v, (float, np.floating)) else (int(v) if isinstance(v, np.integer) else v))
            for k, v in r.items()}


def trail_overlay(pos, F, k):
    p = np.nan_to_num(np.asarray(pos, float))
    c, a = F.c.to_numpy(), F.atr.to_numpy()
    out = np.zeros(len(p))
    side, ext, stopped = 0, 0.0, False
    for i in range(len(p)):
        want = np.sign(p[i])
        if want != side:
            side, ext, stopped = want, c[i], False
        if side != 0 and not stopped:
            ext = max(ext, c[i]) if side > 0 else min(ext, c[i])
            if np.isfinite(a[i]) and ((side > 0 and c[i] < ext - k * a[i]) or (side < 0 and c[i] > ext + k * a[i])):
                stopped = True
        out[i] = 0.0 if stopped else p[i]
    return out


def yearly(res, store, F):
    out = {}
    bh = strat_returns(np.ones(len(F)), F)
    series = {"Bakır al-tut": bh}
    for key in ("chosen", "chosen_single"):
        ch = res.get(key)
        if ch and (ch["strateji"], ch["yön"]) in store:
            series[f"{'Seçilen' if key == 'chosen' else 'Seçilen tek'}: {ch['strateji']} ({ch['yön']})"] = strat_returns(store[(ch["strateji"], ch["yön"])], F)
    for k, r in series.items():
        s = pd.Series(r, index=F.index)
        s = s[s.index >= TRAIN0]
        out[k] = {int(y): float((1 + g.fillna(0)).prod() - 1) for y, g in s.groupby(s.index.year)}
    return out


def portfolio(px, fred, F, store, res) -> Optional[dict]:
    """Risk parity (karma style: 10% vol target x2) with and without copper; copper timed by the chosen strategy."""
    assets = {"SPX": "^GSPC", "NQ": "^NDX", "XAU": "GC=F", "XAG": "SI=F", "HG": "HG=F"}
    if not all(v in px for v in assets.values()):
        return None
    C = pd.DataFrame({k: px[v].Close for k, v in assets.items()}).sort_index().ffill(limit=3)
    C = C[C.index >= pd.Timestamp("1999-01-01")]
    r = np.log(C / C.shift(1))
    tb = asof(fred, C.index, "DGS3MO").fillna(3.0) / 100

    def rp(cols, timing: Optional[pd.Series] = None, lev=2.0, fin=0.04):
        rr = r[cols]
        vol = rr.rolling(60, min_periods=40).std() * math.sqrt(252)
        w = (1 / vol).div(len(cols)) * 0.10
        pv = (w.shift(1) * rr).sum(1).rolling(60, min_periods=40).std() * math.sqrt(252)
        w = w.mul((0.10 / pv).clip(upper=3), axis=0) * lev
        if timing is not None and "HG" in cols:
            w["HG"] = w["HG"] * timing.reindex(w.index).fillna(0)
        w = w.mul((3 / w.abs().sum(1)).clip(upper=1), axis=0).shift(1).fillna(0)
        g = (w * np.expm1(rr).fillna(0)).sum(1) - 0.0005 * w.diff().abs().sum(1) - (w.sum(1) - 1).clip(lower=0) * fin / 252
        return g

    out = {}
    end = C.index[-1] + pd.Timedelta(days=1)
    base = ["SPX", "NQ", "XAU", "XAG"]
    variants = {"Mevcut risk paritesi (S&P, Nasdaq, altın, gümüş)": rp(base),
                "Risk paritesi + bakır (5. varlık, zamanlamasız)": rp(base + ["HG"])}
    for key in ("chosen_single", "chosen"):
        ch = res.get(key)
        if ch and (ch["strateji"], ch["yön"]) in store:
            t = pd.Series(store[(ch["strateji"], ch["yön"])], index=F.index)
            variants[f"Risk paritesi + bakır, seçilen kuralla zamanlanmış ({ch['strateji']}, {ch['yön']})"] = rp(base + ["HG"], t)
    for k, g in variants.items():
        row = {}
        for lab, a, b in (("eğitim", TRAIN0, EXAM0), ("sınav", EXAM0, end)):
            x = g[(g.index >= a) & (g.index < b)]
            eq = (1 + x).cumprod()
            yrs = len(x) / 252
            row[lab] = {"cagr": float(eq.iloc[-1] ** (1 / yrs) - 1), "maxdd": float(1 - (eq / eq.cummax()).min()),
                        "sharpe": float(x.mean() / x.std() * math.sqrt(252))}
        out[k] = row
    out["_note"] = "Botun bugünkü risk paritesiyle aynı yapı (VIX katmanı hariç); bakırın katkısını göreli olarak ölçer."
    return out


def bitget_check(F, bg, bgc) -> dict:
    out = {"contract": None}
    c = bg.get("contract") or {}
    if c:
        out["contract"] = {k: c.get(k) for k in ("symbol", "baseCoin", "minTradeNum", "sizeMultiplier", "minTradeUSDT",
                                                 "maxLever", "fundInterval", "isRwa", "symbolStatus")}
    t = bg.get("ticker") or {}
    if t:
        out["last"] = float(t.get("lastPr") or 0)
        out["hg_last"] = float(F.c.iloc[-1])
        out["ratio"] = out["last"] / out["hg_last"] if out["hg_last"] else None
    if bgc is not None and len(bgc):
        b = bgc.set_index("date").close.astype(float)
        j = pd.concat([b, F.c], axis=1, keys=["bitget", "hg"]).dropna()
        if len(j) > 20:
            ratio = (j.bitget / j.hg)
            rb, rh = j.bitget.pct_change(), j.hg.pct_change()
            out["candles"] = int(len(b))
            out["since"] = str(b.index.min().date())
            out["ratio_median"] = float(ratio.median())
            out["ratio_std_pct"] = float(ratio.std() / ratio.median())
            out["daily_corr"] = float(rb.corr(rh))
            out["tracking_err_ann"] = float((rb / 1 - rh).std() * math.sqrt(252))
    f = bg.get("funding") or []
    if f:
        fr = pd.DataFrame(f)
        fr["r"] = fr.fundingRate.astype(float)
        hours = float((c or {}).get("fundInterval") or 8)
        out["funding_apr_mean"] = float(fr.r.mean() * (24 / hours) * 365)
        out["funding_obs"] = int(len(fr))
        out["funding_apr_p90"] = float(fr.r.quantile(0.9) * (24 / hours) * 365)
    return out


def hourly_explore(H: pd.DataFrame) -> Optional[dict]:
    if H is None or len(H) < 2000:
        return None
    h = H.set_index("time").sort_index()
    r = h.Close.pct_change()
    cut = h.index[int(len(h) * 2 / 3)]
    hr = pd.Series(h.index.hour, index=h.index)
    a = r[h.index < cut].groupby(hr[h.index < cut]).mean()
    b = r[h.index >= cut].groupby(hr[h.index >= cut]).mean()
    best = a.idxmax()
    out = {"split": str(cut.date()), "hours": {int(k): [float(a.get(k, np.nan)), float(b.get(k, np.nan))] for k in sorted(set(a.index) | set(b.index))},
           "best_hour_train": int(best), "best_hour_exam_mean": float(b.get(best, np.nan)), "hour_corr": float(a.corr(b))}
    h4 = h.Close.resample("4h").last().dropna()
    p = np.sign(ema(h4, 20) - ema(h4, 50)).shift(1)
    rr = (p * h4.pct_change()).dropna()
    c2 = rr.index[int(len(rr) * 2 / 3)]
    s = lambda x: float(x.mean() / x.std() * math.sqrt(6 * 252)) if x.std() > 0 else 0.0  # noqa: E731
    out["4h_ema20_50"] = {"ilk_2/3": s(rr[rr.index < c2]), "son_1/3": s(rr[rr.index >= c2])}
    return out


# ================================================================== report
def _p(x, d=1):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"%{x * 100:+.{d}f}"


def report_md(R: dict) -> str:
    L = ["# 🟠 Bakır Laboratuvarı v14 — COMEX bakır (HG=F) üzerinde tüm strateji aileleri", "",
         f"_Üretim {R['generated_at'][:16]} UTC · veri {R['first']} → {R['last']} · seçim yalnızca 2000–2016 · **2017+ mühürlü sınav** · "
         f"{R['n_trials']:,} deneme · maliyet %{COST * 100:.2f}/işlem birimi + long'a yıllık %{LONG_FUNDING * 100:.0f} fonlama farkı._", ""]
    b = R["bh"]
    L += [f"**Karşılaştırma — bakırı sadece tutmak:** eğitim yıllık {_p(b['eğitim'].get('cagr'))} · Sharpe {b['eğitim'].get('sharpe', 0):.2f} · "
          f"DD %{b['eğitim'].get('maxdd', 0) * 100:.0f}  |  sınav yıllık {_p(b['sınav'].get('cagr'))} · Sharpe {b['sınav'].get('sharpe', 0):.2f} · "
          f"DD %{b['sınav'].get('maxdd', 0) * 100:.0f}", ""]
    L += ["## 1) Seçim (yalnızca eğitim verisiyle) ve mühürlü sınav sonucu", ""]
    for key, title in (("chosen", "Eğitimin en iyisi (tüm denemeler)"), ("chosen_single", "Eğitimin en iyi TEK kuralı")):
        c = R.get(key)
        if c:
            L += [f"**{title}:** {c['strateji']} · {c['yön']}", "",
                  "| | Sharpe | Yıllık | DD | Alfa t (bakıra göre) | İşlem | Piyasada |", "|---|---|---|---|---|---|---|",
                  f"| eğitim | {c['eğitim_sharpe']:.2f} | {_p(c['eğitim_yıllık'])} | %{c['eğitim_dd'] * 100:.0f} | {c['eğitim_alfa_t']:.1f} | {c['eğitim_işlem']} | %{c['eğitim_piyasada'] * 100:.0f} |",
                  f"| **sınav** | **{c['sınav_sharpe']:.2f}** | **{_p(c['sınav_yıllık'])}** | %{c['sınav_dd'] * 100:.0f} | **{c['sınav_alfa_t']:.1f}** | {c['sınav_işlem']} | %{c['sınav_piyasada'] * 100:.0f} |",
                  f"| Deflated Sharpe (eğitim, {R['n_trials']} deneme için) | {c['deflated_sharpe']:.2f} | | | | | |", ""]
    fs = list(FUNDING_SCENARIOS)
    L += ["### Fonlama senaryoları (long öder, short alır)", "",
          "| | " + " | ".join(f"fonlama %{f * 100:.1f}" for f in fs) + " |", "|---" * (len(fs) + 1) + "|",
          "| Bakırı tutmak (sınav yıllık) | " + " | ".join(_p(R["bh_by_funding"].get(f"{f}")) for f in fs) + " |"]
    for key, lab in (("chosen", "Eğitimin en iyisi"), ("chosen_single", "En iyi tek kural")):
        c = R.get(key)
        if c and c.get("senaryolar"):
            L.append(f"| {lab}: sınav Sharpe / yıllık | " + " | ".join(
                f"{c['senaryolar'][f'{f}']['sınav_sharpe']:.2f} / {_p(c['senaryolar'][f'{f}']['sınav_yıllık'])}" for f in fs) + " |")
    rp = R.get("funding_robust_pick")
    if rp:
        L.append(f"| **Fonlamaya dayanıklı seçim** ({rp['strateji']}, {rp['yön']}; eğitimde 4 senaryonun en kötüsüne göre) | " + " | ".join(
            f"{rp[f'sı_{f}']:.2f} / {_p(rp[f'sı_yıllık_{f}'])}" for f in fs) + " |")
    L += ["", "_Seçim yine yalnız eğitim verisiyle; sınav sütunları seçimi etkilemez._", ""]
    ft = R.get("funding_table") or []
    if ft:
        L += ["**Eğitimde en kötü senaryoda en iyi 15 (sınav Sharpe'ları senaryo sırasıyla):**", "",
              "| Strateji | Yön | Eğitim (en kötü) | Sınav: " + " / ".join(f"%{f * 100:.1f}" for f in fs) + " |", "|---|---|---|---|"]
        for t in ft:
            L.append(f"| {t['strateji']} | {t['yön']} | {t['eğ_en_kötü']:.2f} | " + " / ".join(f"{t[f'sı_{f}']:.2f}" for f in fs) + " |")
        L.append("")
    nb = R.get("chosen_neighbours")
    if nb:
        L += [f"_Seçilen tek kuralın ailesindeki {nb['n']} komşu: eğitimde pozitif %{nb['train_pos'] * 100:.0f}, sınavda pozitif %{nb['exam_pos'] * 100:.0f}, "
              f"sınav Sharpe ortalaması {nb['exam_mean']:.2f}._", ""]
    L += ["## 2) Aileler (tek kurallar, ortalama)", "", "| Aile | Yön | Kural | Eğitim Sharpe | **Sınav Sharpe** | Sınav alfa t | Sınavda + |", "|---|---|---|---|---|---|---|"]
    for f in R["families"]:
        L.append(f"| {f['aile']} | {f['yön']} | {f['strateji']} | {f['eğitim_sharpe']:.2f} | **{f['sınav_sharpe']:.2f}** | {f['sınav_alfa_t']:.2f} | %{f['sınav_pozitif'] * 100:.0f} |")
    L += ["", "## 3) Eğitimin en iyi 30 denemesi ve sınavdaki sonuçları", "",
          "| # | Strateji | Yön | Eğitim Sharpe / yıllık / DD | DSR | **Sınav Sharpe / yıllık / DD** | Sınav alfa t | İşlem (sınav) |", "|---|---|---|---|---|---|---|---|"]
    for i, t in enumerate(R["top_train"], 1):
        L.append(f"| {i} | {t['strateji']} | {t['yön']} | {t['eğitim_sharpe']:.2f} / {_p(t['eğitim_yıllık'])} / %{t['eğitim_dd'] * 100:.0f} | {t['deflated_sharpe']:.2f} | "
                 f"**{t['sınav_sharpe']:.2f} / {_p(t['sınav_yıllık'])} / %{t['sınav_dd'] * 100:.0f}** | {t['sınav_alfa_t']:.1f} | {t['sınav_işlem']} |")
    L += ["", "## 4) Bütün tek kurallar (eğitim sırasıyla)", "", "| Aile | Strateji | Yön | Eğitim Sharpe | Sınav Sharpe | Sınav alfa t |", "|---|---|---|---|---|---|"]
    for t in R["singles_all"]:
        L.append(f"| {t['aile']} | {t['strateji']} | {t['yön']} | {t['eğitim_sharpe']:.2f} | {t['sınav_sharpe']:.2f} | {t['sınav_alfa_t']:.1f} |")
    if R.get("skipped_short_history"):
        L += ["", f"_Eğitimde {MIN_TRAIN_YEARS} yıldan kısa verisi olduğu için seçime girmeyenler: {', '.join(R['skipped_short_history'])}_"]
    pf = R.get("portfolio")
    if pf:
        L += ["", "## 5) Portföye katkı (risk paritesi, %10 oynaklık hedefi ×2)", "", "| Portföy | Eğitim yıllık / DD / Sharpe | **Sınav yıllık / DD / Sharpe** |", "|---|---|---|"]
        for k, v in pf.items():
            if k.startswith("_"):
                continue
            e, s = v["eğitim"], v["sınav"]
            L.append(f"| {k} | {_p(e['cagr'])} / %{e['maxdd'] * 100:.0f} / {e['sharpe']:.2f} | **{_p(s['cagr'])} / %{s['maxdd'] * 100:.0f} / {s['sharpe']:.2f}** |")
        L += ["", f"_{pf.get('_note', '')}_"]
    y = R.get("yearly_chosen")
    if y:
        ks = list(y)
        yrs = sorted({yy for v in y.values() for yy in v})
        L += ["", "## 6) Yıllar", "", "| Yıl | " + " | ".join(ks) + " |", "|---" * (len(ks) + 1) + "|"]
        for yy in yrs:
            L.append(f"| {yy} | " + " | ".join(_p(y[k].get(yy), 0) for k in ks) + " |")
    bgc = R.get("bitget") or {}
    L += ["", "## 7) Bitget COPPERUSDT kontrolü", ""]
    if bgc.get("contract"):
        L.append("Kontrat: " + ", ".join(f"{k}={v}" for k, v in bgc["contract"].items()))
    if bgc.get("ratio"):
        L.append(f"Son fiyat Bitget {bgc['last']:.4g} / HG=F {bgc['hg_last']:.4g} → oran {bgc['ratio']:.4g}")
    if bgc.get("candles"):
        L.append(f"Bitget günlük mum: {bgc['candles']} ({bgc['since']}'ten beri) · oran medyanı {bgc['ratio_median']:.4g} (sapma %{bgc['ratio_std_pct'] * 100:.1f}) · "
                 f"günlük getiri korelasyonu {bgc['daily_corr']:.2f}")
    if bgc.get("funding_obs"):
        L.append(f"Fonlama: {bgc['funding_obs']} gözlem · yıllık ortalama {_p(bgc['funding_apr_mean'])} · 90. yüzdelik {_p(bgc['funding_apr_p90'])}")
    hh = R.get("hourly")
    if hh:
        L += ["", "## 8) Saatlik keşif (son ~2 yıl; seçimde KULLANILMADI)", "",
              f"İlk 2/3'te en iyi saat (UTC) {hh['best_hour_train']} → son 1/3'te o saatin ortalaması {_p(hh['best_hour_exam_mean'], 3)} · "
              f"saat profillerinin iki dönem arası korelasyonu {hh['hour_corr']:.2f}",
              f"4 saatlik EMA20/50 trendi Sharpe: ilk 2/3 {hh['4h_ema20_50']['ilk_2/3']:.2f}, son 1/3 {hh['4h_ema20_50']['son_1/3']:.2f}"]
    L.append("")
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="copper_data")
    ap.add_argument("--out", default="copper_out")
    a = ap.parse_args()
    px, fred, cot, hourly, bg, bgc = load(a.data)
    global LONG_FUNDING
    f = [float(x["fundingRate"]) for x in (bg or {}).get("funding", []) if x.get("fundingRate") not in (None, "")]
    hours = float(((bg or {}).get("contract") or {}).get("fundInterval") or 8)
    if len(f) >= 90:                       # the measured Bitget funding becomes the last scenario column
        global FUNDING_SCENARIOS
        real = round(float(np.mean(f)) * (24 / hours) * 365, 3)
        FUNDING_SCENARIOS = tuple(sorted(set((0.0, 0.03, 0.08, real))))
        print(f"[bakır] ölçülen Bitget fonlaması: %{real * 100:.1f}/yıl (senaryolara eklendi)", flush=True)
    R = research(px, fred, cot, hourly, bg, bgc)
    os.makedirs(a.out, exist_ok=True)
    T = R.pop("_table")
    T.to_csv(os.path.join(a.out, "copper_all_strategies.csv.gz"), index=False, compression="gzip", float_format="%.5g")
    open(os.path.join(a.out, "copper_report.md"), "w", encoding="utf-8").write(report_md(R))
    json.dump(json.loads(json.dumps(R, default=str)), open(os.path.join(a.out, "copper_results.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("[bakır] bitti", flush=True)


if __name__ == "__main__":
    main()
