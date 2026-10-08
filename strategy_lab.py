"""
Strategy Lab v5 — leveraged perpetual-futures research over EVERY system signal
================================================================================
What is tested (per asset: SPX, NQ, XAU, XAG, BTC, ETH)
  * EVERY output of the terminal, point-in-time (validation_reports/
    signal_panel.csv.gz from the historical replay): model verdict, forecast,
    short-term direction, live tier, direction stage, all scores / z's /
    velocities, pair & cluster scores, timeframe confluence, entry gate &
    grade, RVOL, ATR, ADX, every macro factor, regime, USD risk, VIX ...
      - as a direction (sign, and strong-only |z| > 1 against its own past
        30 days), in the system's orientation AND contrarian
      - as a filter (entry allowed, grade, volume/volatility support, ADX trend,
        regime, crisis off, live-vs-model agreement, RVOL/ATR high/low)
  * 54 technical rules on 1h / 4h / 1d (momentum, EMA trend & cross, Donchian,
    MACD, DMI/ADX, RSI trend & mean-reversion, Bollinger, Keltner)
  * combinations: system direction x filter, technical x system filter,
    technical x system-direction agreement, factor x regime, majority votes
  * long-short, long-only, short-only
  * exits: signal, ATR stop/target (1.5/3, 2/4, 3/6), ATR trailing (2, 3),
    time stop (4h, 24h)
  -> tens of thousands of configurations per asset, all on the same hourly
     execution grid (position decided at a bar's close earns the next bar;
     stops/targets/trailing checked on later bars' High/Low, stop first).

Perpetual-futures economics
  * fee + slippage per side, funding: longs pay 0.01%/8h (shorts credited
    nothing - conservative), every hour a position is open
  * leverage table for the selected rules: 1x..10x with isolated-margin
    liquidation (maintenance 0.5%), and a volatility-targeted sizing

Honesty machinery (unchanged in spirit)
  * walk-forward of the WHOLE selection procedure (6 folds), Deflated Sharpe
    with the effective number of independent configurations, ≥ 30 trades
  * alpha vs simply holding the perp (beta-adjusted). Beating cash with a
    mostly-long rule in a bull market is not an edge -> "β ağırlıklı".
  * a second, independent 10-year daily test for daily technical rules.

Outputs: lab_report.md, lab_results.json, lab_playbook.json,
         lab_all_configs.csv.gz (EVERY configuration with its numbers).
CLI:  python strategy_lab.py --source yahoo --panel validation_reports/signal_panel.csv.gz
      python strategy_lab.py --source panel --panel validation_reports/factor_panel.csv.gz   (offline preview)
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

ASSETS = {"SPX": "ES=F", "NQ": "NQ=F", "XAU": "GC=F", "XAG": "SI=F", "BTC": "BTC-USD", "ETH": "ETH-USD"}
NAMES = {"SPX": "S&P 500", "NQ": "Nasdaq 100", "XAU": "Altın", "XAG": "Gümüş", "BTC": "Bitcoin", "ETH": "Ethereum"}
# one-way cost (perp taker fee + slippage) as a fraction of notional
COST = {"BTC": 0.0008, "ETH": 0.0008, "SPX": 0.0008, "NQ": 0.0008, "XAU": 0.0008, "XAG": 0.0010}
FUND_LONG_H = 0.0001 / 8.0          # longs pay 0.01% per 8h
FUND_SHORT_H = 0.0                  # shorts: assume no credit (conservative)
LEVERAGES = (1, 2, 3, 5, 10)
MMR = 0.005                         # maintenance margin (isolated)
VOL_TARGET, VOL_MAX_LEV = 0.40, 5.0
WINDOW_DAYS = 730
FOLDS, LONG_FOLDS = 6, 8
MIN_SELECT_TRADES = 15
Z_WINDOW, Z_MIN = "30D", 60
ALT_Z_N, ALT_Z_MIN = 90, 20                      # alt z-score: 90 observations of its own frequency (days / weeks)
ALT_STALE = pd.Timedelta(days=15)              # COT is weekly + holidays -> stale after 15 days
BATCH = 3000
CRIT = {"wf_t": 2.0, "pos_folds": 3, "dsr": 0.90, "trades": 30,
        "long_t": 2.0, "long_pos_folds": 5, "long_years": 6.0, "alpha_t": 2.0}
EXITS = [{"type": "sig"},
         {"type": "sltp", "k1": 1.5, "k2": 3.0}, {"type": "sltp", "k1": 2.0, "k2": 4.0}, {"type": "sltp", "k1": 3.0, "k2": 6.0},
         {"type": "trail", "k1": 2.0}, {"type": "trail", "k1": 3.0},
         {"type": "time", "h": 4}, {"type": "time", "h": 24},
         # v6.1: breakeven stop, partial take-profit (half at TP1, rest trails), volatility-adaptive target
         {"type": "be", "k1": 2.0, "k2": 4.0, "b": 1.0}, {"type": "be", "k1": 3.0, "k2": 6.0, "b": 1.5},
         {"type": "part", "k1": 2.0, "k2": 2.0, "k3": 3.0}, {"type": "part", "k1": 3.0, "k2": 3.0, "k3": 3.0},
         {"type": "vol", "k1": 2.0, "k2": 4.0}, {"type": "vol", "k1": 3.0, "k2": 6.0}]
MODES = ("LS", "LO", "SO")
TRIG_EXITS = [{"type": "sig"}, {"type": "sltp", "k1": 2.0, "k2": 4.0}, {"type": "be", "k1": 2.0, "k2": 4.0, "b": 1.0},
              {"type": "part", "k1": 2.0, "k2": 2.0, "k3": 3.0}, {"type": "trail", "k1": 2.0}, {"type": "vol", "k1": 2.0, "k2": 4.0}]
# v6: holding horizons (rebalance cadence in hours) and their Turkish labels
CADENCES = (1, 4, 24, 168, 720)
CAD_TR = {1: "1 saat", 4: "4 saat", 24: "1 gün", 168: "1 hafta", 720: "1 ay"}
CAD_ADJ = {1: "1 saatlik", 4: "4 saatlik", 24: "1 günlük", 168: "1 haftalık", 720: "1 aylık"}
SLOW_EXITS = [{"type": "sig"}, {"type": "sltp", "k1": 3.0, "k2": 6.0}, {"type": "trail", "k1": 3.0},
              {"type": "be", "k1": 3.0, "k2": 6.0, "b": 1.5}, {"type": "part", "k1": 3.0, "k2": 3.0, "k3": 3.0},
              {"type": "vol", "k1": 3.0, "k2": 6.0}]
EX_CODE = {"sig": 0, "sltp": 1, "trail": 2, "time": 3, "be": 4, "part": 5, "vol": 6}
TF_H = {"1h": 1, "4h": 4, "1d": 24}

# ---------------------------------------------------------------- technical rules
TECH = {
    "1h": {"tsmom": [24, 72, 168, 336], "ema_trend": [50, 200], "ema_cross": [(24, 96), (50, 200)],
           "donchian": [48, 168], "macd": [(12, 26, 9)], "dmi": [14], "boll_mr": [(20, 2.0)],
           "rsi_mr": [(2, 10, 90)], "rsi_trend": [14], "keltner": [(20, 2.0)]},
    "4h": {"tsmom": [12, 42, 90, 180], "ema_trend": [50, 200], "ema_cross": [(10, 30), (20, 50), (50, 200)],
           "donchian": [20, 55, 120], "macd": [(12, 26, 9)], "dmi": [14], "boll_mr": [(20, 2.0)],
           "rsi_mr": [(2, 10, 90)], "rsi_trend": [14], "keltner": [(20, 2.0)]},
    "1d": {"tsmom": [10, 20, 60, 120, 250], "ema_trend": [20, 50, 100, 200],
           "ema_cross": [(10, 30), (20, 50), (50, 200)], "donchian": [20, 55], "macd": [(12, 26, 9)],
           "dmi": [14], "boll_mr": [(20, 2.0)], "rsi_mr": [(2, 10, 90)], "rsi_trend": [14], "keltner": [(20, 2.0)]},
}
TECH_TR = {"tsmom": "Momentum", "ema_trend": "EMA trend", "ema_cross": "EMA kesişimi", "donchian": "Donchian kırılımı",
           "macd": "MACD", "dmi": "DMI/ADX yönü", "boll_mr": "Bollinger dönüş", "rsi_mr": "RSI(2) dönüş",
           "rsi_trend": "RSI trend", "keltner": "Keltner kırılımı"}
TREND_FAMS = ("tsmom", "ema_trend", "ema_cross", "donchian", "macd", "dmi", "rsi_trend", "keltner")

# system columns that are the system's main DIRECTION outputs (used in combos)
CORE_SYS = ["cat::verdict", "cat::forecast", "cat::short_term", "cat::stage", "cat::live_tier", "cat::direction",
            "sys::score", "sys::adaptive_score", "sys::legacy_score", "sys::live_score", "sys::live_price_score",
            "sys::direction_score_z", "sys::pair_direction_score", "sys::timeframe_confluence.confluence_score",
            "sys::short_term_parts.model_z"]
# columns that must never be used (future returns in the factor panel, bookkeeping)
FORBIDDEN_PREFIX = ("r1", "r4", "r24", "r72", "vol_1h", "past_24h")

TR = {  # Turkish names of the most important system signals
    "cat::verdict": "Model sinyali (24s-1h)", "cat::forecast": "Model tahmini", "cat::short_term": "Kısa Vade Yön",
    "cat::stage": "Yön aşaması", "cat::live_tier": "Kısa vade kademesi", "cat::direction": "Yön motoru",
    "sys::score": "Model skoru", "sys::adaptive_score": "Adaptif skor", "sys::legacy_score": "Makro model skoru",
    "sys::live_score": "Kısa vade skoru", "sys::live_price_score": "Fiyat itkisi skoru",
    "sys::direction_score_z": "Yön z-skoru", "sys::pair_direction_score": "Çift-uyumlu yön skoru",
    "sys::timeframe_confluence.confluence_score": "Zaman dilimi uyumu", "sys::short_term_parts.model_z": "Model z (kısa vade)",
    "sys::entry_allowed": "Giriş izni", "cat::entry_grade": "Giriş notu", "sys::volume_supports": "Hacim desteği",
    "sys::volatility_supports": "Volatilite desteği", "cat::adx_trend": "ADX trend rejimi", "cat::live_vs_model": "Kısa vade=model",
    "mac::crisis_active": "Kriz kilidi", "mac::regime_id": "Makro rejim", "sys::rvol": "RVOL", "sys::atr_ratio": "ATR oranı",
}


ALT_TR = {"oi_chg_24h": "Açık pozisyon değişimi 24s", "oi_chg_7d": "Açık pozisyon değişimi 7g",
          "top_trader_ls": "Büyük trader long/short", "account_ls": "Hesap long/short oranı",
          "taker_buy_sell": "Agresif alış/satış oranı", "premium": "Perp primi (baz)", "premium_8h": "Perp primi 8s ort.",
          "cot_lev_net": "COT kaldıraçlı fon net", "cot_am_net": "COT varlık yöneticisi net", "cot_dealer_net": "COT dealer net",
          "cot_mm_net": "COT spekülatif fon net", "cot_prod_net": "COT üretici net", "cot_swap_net": "COT swap dealer net",
          "cot_oi_chg": "COT açık pozisyon değişimi"}


def tr_name(col: str) -> str:
    if col.startswith("alt::"):
        k = col[5:]
        base = k[:-4] + "_net" if k.endswith("_chg") and k.startswith("cot_") and k != "cot_oi_chg" else k
        nm = ALT_TR.get(base, k)
        return "Alt: " + (nm + " (haftalık değişim)" if base != k else nm)
    if col in TR:
        return TR[col]
    if col.startswith("z::"):
        return tr_name(col[3:]) + " (z)"
    if col.startswith("tech:"):
        _, tf, fam, p = col.split(":", 3)
        return f"{TECH_TR.get(fam, fam)} ({p.replace('-', '/')}) · {tf}"
    for pre, lab in (("f::", "Faktör: "), ("sys::", ""), ("mac::", "Makro: "), ("cat::", "")):
        if col.startswith(pre):
            return lab + col[len(pre):]
    return col


# ================================================================= data
def _closed(df: pd.DataFrame, hours: int, now: datetime) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    return df[df.index + pd.Timedelta(hours=hours) <= pd.Timestamp(now)]


def _resample(h: pd.DataFrame, rule: str) -> pd.DataFrame:
    return h.resample(rule, label="left", closed="left").agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()


def load_yahoo(now: Optional[datetime] = None, hourly_period: str = "730d", daily_period: str = "10y") -> Dict[str, dict]:
    import yfinance as yf
    now = now or datetime.now(timezone.utc)
    out = {}
    for a, sym in ASSETS.items():
        try:
            t = yf.Ticker(sym)
            h = t.history(period=hourly_period, interval="1h", auto_adjust=False)[["Open", "High", "Low", "Close"]]
            h.index = pd.to_datetime(h.index, utc=True)
            h = _closed(h[~h.index.duplicated()].dropna().sort_index(), 1, now)
            d = t.history(period=daily_period, interval="1d", auto_adjust=False)[["Open", "High", "Low", "Close"]]
            d.index = pd.to_datetime(d.index.date).tz_localize("UTC")
            d = _closed(d[~d.index.duplicated()].dropna().sort_index(), 24, now)
            out[a] = {"1h": h, "1d": d}
            print(f"[lab] {a}: 1h={len(h)} 1d={len(d)}", flush=True)
        except Exception as exc:
            print(f"[lab] {a}: veri alınamadı ({exc})", flush=True)
    return out


def load_signal_panel(path: Optional[str]) -> Optional[pd.DataFrame]:
    """System signals, point-in-time. Prefers signal_panel.csv.gz (every system
    output); falls back to factor_panel.csv.gz (model score, price score,
    factors, regime). Future-return columns are dropped."""
    cands = [p for p in ([path] if path else []) +
             ["validation_reports/signal_panel.csv.gz", "validation_reports/factor_panel.csv.gz"] if p]
    for p in cands:
        if p and os.path.exists(p):
            P = pd.read_csv(p, low_memory=False)
            P["t"] = pd.to_datetime(P["t"], utc=True)
            if "sys::score" not in P.columns:           # factor_panel -> same naming as signal_panel
                ren = {"legacy_score": "sys::legacy_score", "price_score": "sys::live_price_score"}
                P = P.rename(columns=ren)
                if "regime" in P.columns:
                    P["mac::regime_id"] = pd.to_numeric(P["regime"], errors="coerce").fillna(0.0)
            keep = ["asset", "t"] + [c for c in P.columns if c.startswith(("sys::", "cat::", "f::", "mac::"))]
            P = P[keep]
            print(f"[lab] sistem sinyal paneli: {p} · {len(P)} satır · {len(keep) - 2} sinyal", flush=True)
            P.attrs["source"] = os.path.basename(p)
            return P
    return None


def panel_price_path(path: str) -> Dict[str, dict]:
    """OFFLINE PREVIEW ONLY: an hourly close path rebuilt from the factor panel
    (r4 = exact 4h log return chains every 2h, r1 = next hour; one constant
    offset between the two interleaved chains is estimated). No High/Low."""
    P = pd.read_csv(path, usecols=["asset", "t", "r1", "r4"])
    P["t"] = pd.to_datetime(P["t"], utc=True)
    out = {}
    for a, g in P.groupby("asset"):
        g = g.sort_values("t").reset_index(drop=True)
        r4 = g["r4"].fillna(0.0).values
        x = np.zeros(len(g))
        for i in range(2, len(g)):
            x[i] = x[i - 2] + r4[i - 2]
        alt = np.where(np.arange(len(g)) % 2 == 1, 1.0, 0.0)
        d1 = np.diff(x)
        c = -np.mean(d1 * np.where(alt[1:] == 1, 1, -1))        # offset that minimises alternating jumps
        x = x + alt * c
        r1 = g["r1"].fillna(0.0).values
        ts = list(g["t"]) + list(g["t"] + pd.Timedelta(hours=1))
        lp = list(x) + list(x + r1)
        s = pd.Series(lp, index=pd.DatetimeIndex(ts)).sort_index()
        s = s[~s.index.duplicated()]
        close = 100 * np.exp(s - s.iloc[0])
        bars = pd.DataFrame({"Close": close.values}, index=s.index - pd.Timedelta(hours=1))   # bar start = close time - 1h
        bars["Open"] = bars["Close"].shift(1).fillna(bars["Close"])
        bars["High"] = bars[["Open", "Close"]].max(axis=1)
        bars["Low"] = bars[["Open", "Close"]].min(axis=1)
        out[a] = {"1h": bars[["Open", "High", "Low", "Close"]]}
    return out


# ================================================================= indicators
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


def _hold(ev: pd.Series) -> pd.Series:
    return ev.ffill().fillna(0.0)


def tech_signal(fam: str, p, df: pd.DataFrame) -> pd.Series:
    """Direction in {-1,0,1} known at each bar's close (no look-ahead)."""
    C = df["Close"]
    nan = pd.Series(np.nan, index=df.index)
    if fam == "tsmom":
        return np.sign(C / C.shift(p) - 1.0).fillna(0.0)
    if fam == "ema_trend":
        return np.sign(C - _ema(C, p)).fillna(0.0)
    if fam == "ema_cross":
        return np.sign(_ema(C, p[0]) - _ema(C, p[1])).fillna(0.0)
    if fam == "donchian":
        ev = nan.copy()
        ev[C > df["High"].rolling(p).max().shift(1)] = 1.0
        ev[C < df["Low"].rolling(p).min().shift(1)] = -1.0
        return _hold(ev)
    if fam == "macd":
        f, s, g = p
        m = _ema(C, f) - _ema(C, s)
        return np.sign(m - _ema(m, g)).fillna(0.0)
    if fam == "dmi":
        h, l = df["High"], df["Low"]
        up, dn = h.diff(), -l.diff()
        pdm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
        mdm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
        atr = _atr(df, p)
        pdi = 100 * pdm.ewm(alpha=1 / p, adjust=False).mean() / atr
        mdi = 100 * mdm.ewm(alpha=1 / p, adjust=False).mean() / atr
        adx = (100 * (pdi - mdi).abs() / (pdi + mdi)).ewm(alpha=1 / p, adjust=False).mean()
        return (np.sign(pdi - mdi) * (adx > 20)).fillna(0.0)
    if fam == "boll_mr":
        n, k = p
        z = (C - C.rolling(n).mean()) / C.rolling(n).std()
        ev = nan.copy()
        ev[np.sign(z) != np.sign(z.shift())] = 0.0
        ev[z < -k] = 1.0
        ev[z > k] = -1.0
        return _hold(ev)
    if fam == "rsi_mr":
        n, lo, hi = p
        r = _rsi(C, n)
        ev = nan.copy()
        ev[np.sign(r - 50) != np.sign(r.shift() - 50)] = 0.0
        ev[r < lo] = 1.0
        ev[r > hi] = -1.0
        return _hold(ev)
    if fam == "rsi_trend":
        return np.sign(_rsi(C, p) - 50).fillna(0.0)
    if fam == "keltner":
        n, k = p
        e, a = _ema(C, n), _atr(df, n)
        ev = nan.copy()
        ev[np.sign(C - e) != np.sign(C.shift() - e.shift())] = 0.0
        ev[C > e + k * a] = 1.0
        ev[C < e - k * a] = -1.0
        return _hold(ev)
    raise ValueError(fam)


TRIG_TR = {"rsi2": "RSI(2) geri çekilme", "boll": "Bollinger bandı dışı", "donch": "20 mum kırılımı",
           "ema20x": "EMA20 kesişimi", "macdx": "MACD kesişimi", "kelt": "Keltner kırılımı"}
TRIG_HOLD = {"1h": 12, "4h": 48, "1d": 120}       # an entry trigger stays valid this many hours


def trigger_events(kind: str, df: pd.DataFrame) -> pd.Series:
    """ENTRY EVENTS (+1 long / -1 short) at the bar where the condition starts; 0 otherwise."""
    C = df["Close"]

    def onset(up: pd.Series, dn: pd.Series) -> pd.Series:
        up, dn = up.fillna(False), dn.fillna(False)
        e = pd.Series(0.0, index=df.index)
        e[up & ~up.shift(1, fill_value=False)] = 1.0
        e[dn & ~dn.shift(1, fill_value=False)] = -1.0
        return e
    if kind == "rsi2":
        r = _rsi(C, 2)
        return onset(r < 10, r > 90)
    if kind == "boll":
        m, sd = C.rolling(20).mean(), C.rolling(20).std()
        return onset(C < m - 2 * sd, C > m + 2 * sd)
    if kind == "donch":
        return onset(C > df["High"].rolling(20).max().shift(1), C < df["Low"].rolling(20).min().shift(1))
    if kind == "ema20x":
        e = _ema(C, 20)
        return onset(C > e, C < e)
    if kind == "macdx":
        m = _ema(C, 12) - _ema(C, 26)
        sg = _ema(m, 9)
        return onset(m > sg, m < sg)
    if kind == "kelt":
        e, a = _ema(C, 20), _atr(df, 20)
        return onset(C > e + 2 * a, C < e - 2 * a)
    raise ValueError(kind)


def _pstr(p) -> str:
    return "-".join(str(x) for x in p) if isinstance(p, (list, tuple)) else str(p)


# ================================================================= context
class Ctx:
    """Everything a rule can look at, aligned to the hourly execution grid."""

    def __init__(self, h1: pd.DataFrame, d1: Optional[pd.DataFrame] = None, sys: Optional[pd.DataFrame] = None,
                 alt: Optional[pd.DataFrame] = None):
        self.idx = h1.index
        self.O, self.H, self.L, self.C = (h1[c].values.astype(float) for c in ("Open", "High", "Low", "Close"))
        self.T = len(h1)
        # bars whose High/Low are just max/min(Open, Close) carry no intrabar information
        self.no_wicks = bool(np.allclose(self.H, np.maximum(self.O, self.C)) and np.allclose(self.L, np.minimum(self.O, self.C)))
        close_t = h1.index + pd.Timedelta(hours=1)
        # v6: hour counter of each bar's close (for rebalance cadences; weeks start Monday 00:00 UTC)
        self.close_h = ((close_t - pd.Timestamp("1970-01-05", tz="UTC")) // pd.Timedelta(hours=1)).astype(np.int64).values
        self._dmemo: Dict[str, np.ndarray] = {}
        self.feat: Dict[str, np.ndarray] = {}
        frames = {"1h": h1, "4h": _resample(h1, "4h")}
        frames["1d"] = d1 if d1 is not None and len(d1) > 30 else _resample(h1, "1D")
        self.atr: Dict[str, np.ndarray] = {}
        for tf, df in frames.items():
            avail = df.index + pd.Timedelta(hours=TF_H[tf])            # known once the bar has closed
            pos = np.searchsorted(avail.values, close_t.values, side="right") - 1

            def _map(s: pd.Series) -> np.ndarray:
                v = s.values.astype(float)
                return np.where(pos >= 0, v[np.clip(pos, 0, len(v) - 1)], np.nan)

            self.atr[tf] = _map(_atr(df))
            first_seen = np.r_[True, pos[1:] != pos[:-1]] & (pos >= 0)
            for kind in TRIG_TR:
                ev = trigger_events(kind, df).values
                self.feat[f"trig:{tf}:{kind}"] = np.where(first_seen, ev[np.clip(pos, 0, len(ev) - 1)], 0.0)
            for fam, plist in TECH[tf].items():
                for p in plist:
                    self.feat[f"tech:{tf}:{fam}:{_pstr(p)}"] = np.nan_to_num(_map(tech_signal(fam, p, df)))
        self.sys_cols: List[str] = []
        if sys is not None and len(sys):
            S = sys.sort_values("t").drop_duplicates("t", keep="last").set_index("t")
            S = S[[c for c in S.columns if c not in ("asset",) and not c.startswith(FORBIDDEN_PREFIX)]]
            S = S.apply(pd.to_numeric, errors="coerce")
            Z = (S - S.rolling(Z_WINDOW, min_periods=Z_MIN).mean()) / S.rolling(Z_WINDOW, min_periods=Z_MIN).std()
            Z.columns = ["z::" + c for c in S.columns]
            A = pd.concat([S, Z], axis=1)
            tv = A.index.values
            pos = np.searchsorted(tv, close_t.values, side="right") - 1
            fresh = (pos >= 0) & ((close_t.values - tv[np.clip(pos, 0, len(tv) - 1)]) <= np.timedelta64(3, "h"))
            for c in A.columns:
                v = A[c].values.astype(float)
                self.feat[c] = np.where(fresh, v[np.clip(pos, 0, len(v) - 1)], np.nan)
            self.sys_cols = list(S.columns)
            self.sys_cover = (int(np.argmax(fresh)) if fresh.any() else self.T,
                              int(len(fresh) - np.argmax(fresh[::-1])) if fresh.any() else 0)
        else:
            self.sys_cover = (0, 0)
        # v7: alternative data (Binance derivatives positioning, CFTC COT) - its own as-of alignment:
        # values arrive daily/weekly, so they stay valid up to ALT_STALE after they became known
        self.alt_cols: List[str] = []
        if alt is not None and len(alt):
            A = alt[["t"] + [c for c in alt.columns if c.startswith("alt::")]].groupby("t").last().sort_index()
            A = A.apply(pd.to_numeric, errors="coerce").dropna(axis=1, how="all")
            stale = ALT_STALE.to_timedelta64()
            for c in A.columns:                         # each source has its own calendar -> align column by column
                x = A[c].dropna()
                if len(x) < ALT_Z_MIN:
                    continue
                z = (x - x.rolling(ALT_Z_N, min_periods=ALT_Z_MIN).mean()) / x.rolling(ALT_Z_N, min_periods=ALT_Z_MIN).std()
                tv = x.index.values
                pos = np.searchsorted(tv, close_t.values, side="right") - 1
                ok = (pos >= 0) & ((close_t.values - tv[np.clip(pos, 0, len(tv) - 1)]) <= stale)
                for name, ser in ((c, x), ("z::" + c, z)):
                    v = ser.values.astype(float)
                    self.feat[name] = np.where(ok, v[np.clip(pos, 0, len(v) - 1)], np.nan)
                    self.alt_cols.append(name)
            self.sys_cols += self.alt_cols

    # ---------------- rule evaluation
    def direction(self, d: dict) -> np.ndarray:
        if "bench" in d:
            return np.full(self.T, 1.0 if d["bench"] == "long" else -1.0)
        if "ens" in d:
            parts = [self.direction(x) for x in d["ens"]]
            M = np.vstack(parts)
            vote = M.sum(0)
            if d.get("need") == "all":
                return np.where(np.all(M == M[0], axis=0), M[0], 0.0)
            need = math.ceil(len(parts) / 2.0)
            return np.where(np.abs(vote) >= need, np.sign(vote), 0.0) if len(parts) > 2 else np.sign(vote) * (np.abs(vote) == len(parts))
        if "trig" in d:
            key = json.dumps(d, sort_keys=True)
            out = self._dmemo.get(key)
            if out is None:
                ev = self.feat.get(d["trig"])
                if ev is None:
                    return np.zeros(self.T)
                last = np.maximum.accumulate(np.where(ev != 0, np.arange(self.T), -1))
                age = np.arange(self.T) - last
                hold = int(d.get("hold", 12))
                sig = np.where((last >= 0) & (age < hold), ev[np.clip(last, 0, None)], 0.0)
                if d.get("bias"):
                    b = np.sign(self.direction(d["bias"]))
                    sig = np.where(b == np.sign(sig), sig, 0.0)       # trade a trigger ONLY in the system's direction
                out = sig
                if len(self._dmemo) < 20000:
                    self._dmemo[key] = out
            return out
        if "cad" in d:
            key = json.dumps(d, sort_keys=True)
            out = self._dmemo.get(key)
            if out is None:
                out = self._transform(d)
                if len(self._dmemo) < 20000:
                    self._dmemo[key] = out
            return out
        x = self.feat.get(d["src"])
        if x is None:
            return np.zeros(self.T)
        x = np.nan_to_num(x)
        if d.get("op") == "z":
            thr = float(d.get("thr", 1.0))
            out = np.where(x > thr, 1.0, np.where(x < -thr, -1.0, 0.0))
        else:
            out = np.sign(x)
        return -out if d.get("inv") else out

    def _transform(self, d: dict) -> np.ndarray:
        """v6 multi-horizon transform of ONE signal:
        cad    = rebalance every `cad` hours (1, 4, 24, 168 = weekly, 720 = ~monthly);
                 the position is decided at the first bar of each period and held
        smooth = use the mean of the signal over the last `cad` hours instead of its last value
        op     = 'sign' or 'z' (|z| > thr against the signal's own trailing history)
        inv    = contrarian"""
        x = self.feat.get(d["src"])
        if x is None:
            return np.zeros(self.T)
        cad = int(d.get("cad", 1))
        s = pd.Series(x, dtype=float)
        if d.get("smooth") and cad > 1:
            s = s.rolling(cad, min_periods=1).mean()
        if d.get("op") == "z":
            w = max(720, 6 * cad)
            z = (s - s.rolling(w, min_periods=w // 4).mean()) / s.rolling(w, min_periods=w // 4).std()
            thr = float(d.get("thr", 1.0))
            v = z.values
            out = np.where(v > thr, 1.0, np.where(v < -thr, -1.0, 0.0))
        else:
            out = np.sign(np.nan_to_num(s.values))
        if d.get("inv"):
            out = -out
        if cad > 1:
            b = self.close_h // cad
            first = np.r_[True, b[1:] != b[:-1]]
            src = np.maximum.accumulate(np.where(first, np.arange(self.T), 0))
            out = out[src]
        return out

    def mask(self, f: Optional[dict], d_arr: np.ndarray) -> np.ndarray:
        if not f:
            return np.ones(self.T, dtype=bool)
        if f.get("op") == "agree":
            return np.sign(self.direction(f["d"])) == np.sign(d_arr)
        x = self.feat.get(f["src"])
        if x is None:
            return np.zeros(self.T, dtype=bool)
        v = float(f.get("val", 0.0))
        with np.errstate(invalid="ignore"):
            if f["op"] == "gt":
                return np.nan_to_num(x, nan=-np.inf) > v
            if f["op"] == "lt":
                return np.nan_to_num(x, nan=np.inf) < v
            if f["op"] == "eq":
                return np.nan_to_num(x, nan=-999) == v
            if f["op"] == "ge":
                return np.nan_to_num(x, nan=-np.inf) >= v
        return np.ones(self.T, dtype=bool)

    def position(self, rule: dict) -> np.ndarray:
        d = self.direction(rule["d"])
        p = d * self.mask(rule.get("f"), d)
        if rule["mode"] == "LO":
            p = np.clip(p, 0, 1)
        elif rule["mode"] == "SO":
            p = np.clip(p, -1, 0)
        return p.astype(np.int8)


# ================================================================= rule universe
def _two_sided(x: np.ndarray) -> bool:
    v = x[np.isfinite(x)]
    if len(v) < 200 or np.nanstd(v) == 0:
        return False
    return (v > 0).mean() > 0.1 and (v < 0).mean() > 0.1


def _usable(x: np.ndarray) -> bool:
    v = x[np.isfinite(x)]
    return len(v) >= 200 and np.nanstd(v) > 0


def direction_rules(ctx: Ctx) -> List[Tuple[str, dict, Optional[dict]]]:
    """(category, direction spec, filter spec) - every single signal and every
    a-priori combination. Built from what the panel actually contains."""
    out: List[Tuple[str, dict, Optional[dict]]] = []
    sys_dir = [c for c in ctx.sys_cols if _two_sided(ctx.feat[c]) and not c.startswith("mac::regime")]
    core = [c for c in CORE_SYS if c in ctx.sys_cols and _usable(ctx.feat[c])]
    tech = [k for k in ctx.feat if k.startswith("tech:")]
    # --- filters
    filters: List[dict] = []
    for c, op, v in (("sys::entry_allowed", "eq", 1.0), ("cat::entry_grade", "ge", 2.0), ("sys::volume_supports", "eq", 1.0),
                     ("sys::volatility_supports", "eq", 1.0), ("cat::adx_trend", "eq", 1.0), ("cat::adx_trend", "eq", 0.0),
                     ("cat::live_vs_model", "eq", 1.0), ("mac::crisis_active", "eq", 0.0),
                     ("z::sys::rvol", "gt", 0.0), ("z::sys::atr_ratio", "gt", 0.0), ("z::sys::atr_ratio", "lt", 0.0)):
        if c in ctx.feat and _usable(np.nan_to_num(ctx.feat[c], nan=0.0) + 0.0) and np.nanstd(ctx.feat[c]) > 0:
            filters.append({"src": c, "op": op, "val": v})
    regimes = []
    if "mac::regime_id" in ctx.feat:
        r = ctx.feat["mac::regime_id"]
        vals, cnt = np.unique(r[np.isfinite(r)], return_counts=True)
        regimes = [float(v) for v, n in sorted(zip(vals, cnt), key=lambda z: -z[1]) if n >= 0.1 * np.isfinite(r).sum()][:4]
        filters += [{"src": "mac::regime_id", "op": "eq", "val": v} for v in regimes]
    agree_tech = [k for k in ("tech:1d:ema_trend:200", "tech:1d:tsmom:60", "tech:4h:ema_trend:50", "tech:1h:ema_trend:200") if k in ctx.feat]
    agree_sys = [c for c in ("cat::verdict", "cat::short_term", "sys::timeframe_confluence.confluence_score", "sys::legacy_score") if c in core]
    # 1) every system output alone: sign and strong-only (|z|>1), system orientation and contrarian
    for c in sys_dir:
        for inv in (False, True):
            out.append(("sys", {"src": c, "op": "sign", "inv": inv}, None))
            if "z::" + c in ctx.feat and _usable(ctx.feat["z::" + c]):
                out.append(("sys", {"src": "z::" + c, "op": "z", "thr": 1.0, "inv": inv}, None))
    # 2) core system directions x every filter (incl. agreement with trend and other system outputs)
    for c in core:
        for inv in (False, True):
            d = {"src": c, "op": "sign", "inv": inv}
            for f in filters:
                out.append(("sys×filtre", d, f))
            for k in agree_tech:
                out.append(("sys×trend", d, {"op": "agree", "d": {"src": k, "op": "sign"}}))
            for k in agree_sys:
                if k != c:
                    out.append(("sys×sys", d, {"op": "agree", "d": {"src": k, "op": "sign"}}))
    # 3) every technical rule alone (trend and its contrarian)
    for k in tech:
        for inv in (False, True):
            out.append(("teknik", {"src": k, "op": "sign", "inv": inv}, None))
    # 4) technical x system filters, technical x system-direction agreement
    for k in tech:
        d = {"src": k, "op": "sign"}
        for f in filters:
            out.append(("teknik×filtre", d, f))
        for c in core:
            out.append(("teknik×sys", d, {"op": "agree", "d": {"src": c, "op": "sign"}}))
    # 5) factor x regime (does a macro factor only work in one regime?)
    for c in [c for c in sys_dir if c.startswith("f::")]:
        for inv in (False, True):
            for v in regimes:
                out.append(("faktör×rejim", {"src": c, "op": "sign", "inv": inv}, {"src": "mac::regime_id", "op": "eq", "val": v}))
    # 6) votes / ensembles
    if len(core) >= 3:
        out.append(("oylama", {"ens": [{"src": c, "op": "sign"} for c in core], "need": "maj"}, None))
    for tf in ("1h", "4h", "1d"):
        ks = [k for k in tech if k.startswith(f"tech:{tf}:") and k.split(":")[2] in TREND_FAMS]
        if len(ks) >= 3:
            out.append(("oylama", {"ens": [{"src": k, "op": "sign"} for k in ks], "need": "maj"}, None))
    allt = [k for k in tech if k.split(":")[2] in TREND_FAMS]
    if allt:
        out.append(("oylama", {"ens": [{"src": k, "op": "sign"} for k in allt], "need": "maj"}, None))
    if core and agree_tech:
        out.append(("oylama", {"ens": [{"src": core[0], "op": "sign"}] + [{"src": k, "op": "sign"} for k in agree_tech[:2]],
                               "need": "all"}, None))
    # 8) v6: EVERY signal alone at every holding horizon (raw / smoothed, sign / |z|>0.5 / |z|>1, normal / TERS)
    for c in sys_dir + [k for k in core if k not in sys_dir]:
        for cad in CADENCES:
            for sm in ((False,) if cad == 1 else (False, True)):
                for op, thr in (("sign", None), ("z", 0.5), ("z", 1.0)):
                    for inv in (False, True):
                        d = {"src": c, "op": op, "inv": inv, "cad": cad, "smooth": sm}
                        if thr is not None:
                            d["thr"] = thr
                        out.append((f"tek·{CAD_TR[cad]}", d, None))
    for k in tech:
        for cad in CADENCES[1:]:
            for sm in (False, True):
                for inv in (False, True):
                    out.append((f"tek·{CAD_TR[cad]}", {"src": k, "op": "sign", "inv": inv, "cad": cad, "smooth": sm}, None))
    # 9) v7: SYSTEM DIRECTION AS FILTER + TECHNICAL ENTRY TRIGGER + ATR EXIT
    #    every trigger alone (baseline) and taken only in the direction of each system bias
    biases = [None]
    bias_src = [c for c in core] + [c for c in sys_dir if c.startswith(("f::", "alt::", "z::alt::")) and c not in core]
    for c in bias_src:
        for cad in (1, 24, 168):
            biases.append({"src": c, "op": "sign", "cad": cad, "smooth": cad > 1})
    for tf in ("1h", "4h", "1d"):
        for kind in TRIG_TR:
            key = f"trig:{tf}:{kind}"
            if key not in ctx.feat:
                continue
            for bspec in biases:
                d = {"trig": key, "hold": TRIG_HOLD[tf], "bias": bspec}
                out.append(("filtre+tetik" if bspec else "tetik (filtresiz)", d, None))
    # 7) benchmarks FIRST, so de-duplication never drops them (an always-positive signal equals "hold long")
    return [("referans", {"bench": "long"}, None), ("referans", {"bench": "short"}, None)] + out


def _dir_tf(d: dict) -> str:
    """Which ATR scale the stops of this rule use."""
    if "trig" in d:
        return d["trig"].split(":")[1]
    src = d.get("src") or ""
    if int(d.get("cad", 1)) >= 24:
        return "1d"
    if src.startswith("tech:"):
        return src.split(":")[1]
    if "ens" in d:
        tfs = {x.get("src", "").split(":")[1] for x in d["ens"] if str(x.get("src", "")).startswith("tech:")}
        return "1d" if tfs == {"1d"} else "4h"
    return "4h"


def rule_id(cat: str, d: dict, f: Optional[dict], mode: str, ex: dict) -> str:
    def ds(x):
        if "bench" in x:
            return "HOLD_" + x["bench"].upper()
        if "trig" in x:
            return x["trig"] + ("|" + ds(x["bias"]) if x.get("bias") else "")
        if "ens" in x:
            return ("ALL(" if x.get("need") == "all" else "MAJ(") + ",".join(ds(e) for e in x["ens"]) + ")"
        s = x["src"] + (f">{x.get('thr', 1.0)}σ" if x.get("op") == "z" else "")
        if "cad" in x:
            s += f"@{x['cad']}h" + ("~" if x.get("smooth") else "")
        return ("-" if x.get("inv") else "") + s
    fs = ""
    if f:
        fs = " & agree(" + ds(f["d"]) + ")" if f.get("op") == "agree" else f" & {f['src']} {f['op']} {f.get('val')}"
    es = ex["type"] + "".join(f"{k}{ex[k]:g}" for k in ("k1", "k2", "k3", "b", "h") if k in ex)
    return f"{ds(d)}{fs} | {mode} | {es}"


def rule_label(r: dict) -> str:
    d, f = r["d"], r.get("f")

    def ds(x):
        if "bench" in x:
            return "Sürekli " + ("LONG" if x["bench"] == "long" else "SHORT") + " (referans)"
        if "trig" in x:
            _, tf, kind = x["trig"].split(":")
            t = f"Tetik: {TRIG_TR[kind]} · {tf}"
            return t + (f" | filtre: {ds(x['bias'])} yönünde" if x.get("bias") else " (filtresiz)")
        if "ens" in x:
            return ("Hepsi aynı yönde: " if x.get("need") == "all" else "Çoğunluk oyu: ") + \
                   (" & ".join(f"[{ds(e)}]" for e in x["ens"]) if len(x["ens"]) <= 7 else f"{len(x['ens'])} sinyal")
        s = tr_name(x["src"])
        if x.get("op") == "z":
            s += f" (güçlü, ∣z∣>{x.get('thr', 1.0):g})"
        if "cad" in x and int(x["cad"]) > 1:
            s += f" · {CAD_ADJ.get(int(x['cad']), str(x['cad']) + ' saatlik')}" + (" ortalama" if x.get("smooth") else "")
        return ("TERS " if x.get("inv") else "") + s
    txt = ds(d)
    if f:
        if f.get("op") == "agree":
            txt += f" + teyit: {ds(f['d'])}"
        else:
            sym = {"eq": "=", "ge": "≥", "gt": ">", "lt": "<"}[f["op"]]
            txt += f" + filtre: {tr_name(f['src'])} {sym} {f.get('val'):g}"
    ex = r["exit"]
    exs = {"sig": "sinyalle çıkış", "sltp": f"SL {ex.get('k1')}×ATR / TP {ex.get('k2')}×ATR",
           "trail": f"iz süren stop {ex.get('k1')}×ATR", "time": f"{ex.get('h')} saat tut",
           "be": f"SL {ex.get('k1')} / TP {ex.get('k2')}×ATR, {ex.get('b')}×ATR kârda stop girişe (başa baş)",
           "part": f"SL {ex.get('k1')}×ATR, yarısı {ex.get('k2')}×ATR'de kâr al, kalanı başa baş + iz süren {ex.get('k3')}×ATR",
           "vol": f"SL {ex.get('k1')} / TP {ex.get('k2')}×ATR × volatilite oranı"}[ex["type"]]
    mode = {"LS": "long+short", "LO": "sadece long", "SO": "sadece short"}[r["mode"]]
    return f"{txt} · {mode} · {exs}"


# ================================================================= vectorised simulator
def simulate_batch(P: np.ndarray, ex: List[dict], atr_sel: np.ndarray, ctx_arrays: dict, cost: float,
                   day_idx: np.ndarray, n_days: int, fund_long: float = FUND_LONG_H, fund_short: float = FUND_SHORT_H,
                   keep_hourly: bool = False) -> dict:
    """Simulate n configurations at once along time. P: int8 [n, T] target
    positions decided at each bar's close (earned from the next bar).

    Exit types (ATR fixed at entry):
      sig    signal only
      sltp   stop k1*ATR, target k2*ATR
      trail  trailing stop k1*ATR behind the best price
      time   close after h bars
      be     stop k1, target k2; once price moved b*ATR in favour the stop goes to entry (breakeven)
      part   stop k1; HALF closed at k2*ATR, then the stop goes to entry and the rest trails at k3*ATR
      vol    stop k1; target k2*ATR*(ATR / its 30-day median, clipped 0.5..2) -> wider targets when volatility expands
    Same bar touches stop and target -> stop. Gaps through a level fill at the open."""
    O, H, L, C, ATR = (ctx_arrays[k] for k in ("O", "H", "L", "C", "ATR"))
    ATRM = ctx_arrays.get("ATRM", ATR)
    close_fill = bool(ctx_arrays.get("close_fill", False))
    n, T = P.shape
    et = np.array([EX_CODE[e["type"]] for e in ex])
    k1 = np.array([float(e.get("k1", 0.0)) for e in ex])
    k2 = np.array([float(e.get("k2", 0.0)) for e in ex])
    k3 = np.array([float(e.get("k3", 0.0)) for e in ex])
    bk = np.array([float(e.get("b", 0.0)) for e in ex])
    hmax = np.array([float(e.get("h", 1e9)) for e in ex])
    has_sl = np.isin(et, (1, 2, 4, 5, 6))
    has_tp = np.isin(et, (1, 4, 5, 6))
    is_trail = et == 2
    is_time = et == 3
    is_be = et == 4
    is_part = et == 5
    is_vol = et == 6
    cur = np.zeros(n)
    blocked = np.zeros(n)
    entry = np.zeros(n); sl = np.full(n, np.nan); tp = np.full(n, np.nan); ext = np.zeros(n); atr_e = np.zeros(n)
    held = np.zeros(n); tpnl = np.zeros(n); part_done = np.zeros(n, dtype=bool); be_done = np.zeros(n, dtype=bool)
    ntr = np.zeros(n); nwin = np.zeros(n); inpos = np.zeros(n)
    R = np.zeros((n, n_days), dtype=np.float32)
    E = np.zeros((n, n_days), dtype=np.int16)
    hourly = np.zeros((n, T)) if keep_hourly else None
    pos_h = np.zeros((n, T)) if keep_hourly else None
    ent_h = np.zeros((n, T)) if keep_hourly else None
    any_stop = bool((has_sl | is_time).any())
    for t in range(1, T):
        pc = C[t - 1]
        lr = math.log(C[t] / pc) if pc > 0 and C[t] > 0 else 0.0
        ps = cur
        side = np.sign(ps)
        size = np.abs(ps)
        fund = np.where(ps > 0, fund_long * ps, np.where(ps < 0, -fund_short * ps, 0.0))
        ret = ps * lr - fund
        if any_stop:
            live = ps != 0
            if live.any():
                lng = ps > 0
                sht = ps < 0
                with np.errstate(invalid="ignore"):
                    hit_sl = has_sl & live & ((lng & (L[t] <= sl)) | (sht & (H[t] >= sl)))
                    hit_tp = has_tp & live & ~hit_sl & ((lng & (H[t] >= tp)) | (sht & (L[t] <= tp)))
                full_tp = hit_tp & ~(is_part & ~part_done)
                half_tp = hit_tp & is_part & ~part_done
                stop_exit = hit_sl | full_tp
                if stop_exit.any():
                    if close_fill:      # no real High/Low: a level seen only at the close is filled AT the close
                        px = np.full(n, C[t])
                    else:
                        px = np.where(hit_sl, np.where(lng, np.minimum(O[t], sl), np.maximum(O[t], sl)), tp)
                    px = np.where(px > 0, px, C[t])
                    ret = np.where(stop_exit, ps * np.log(px / pc) - cost * size - fund, ret)
                if half_tp.any():
                    # half closed at the target, the rest marked to the close; stop -> entry, rest trails
                    tpx = np.full(n, C[t]) if close_fill else np.where(lng, np.maximum(O[t], tp), np.minimum(O[t], tp))
                    tpx = np.where(tpx > 0, tpx, C[t])
                    r_half = 0.5 * side * np.log(tpx / pc) + 0.5 * side * lr - cost * 0.5 - fund
                    # the remaining half is stopped at entry in the same bar if the bar also came back there
                    with np.errstate(invalid="ignore"):
                        back = half_tp & ((lng & (L[t] <= entry)) | (sht & (H[t] >= entry)))
                    r_back = 0.5 * side * np.log(tpx / pc) + 0.5 * side * np.log(np.where(entry > 0, entry, pc) / pc) \
                        - cost * 1.0 - fund
                    ret = np.where(half_tp & ~back, r_half, np.where(back, r_back, ret))
                    stop_exit = stop_exit | back
                    keep = half_tp & ~back
                    part_done = part_done | keep
                    cur = np.where(keep, side * 0.5, ps)
                    sl = np.where(keep, entry, sl)
                    ext = np.where(keep, np.where(lng, H[t], L[t]), ext)
                    tp = np.where(keep, np.nan, tp)
                    ps_after = cur
                else:
                    ps_after = ps
                # breakeven trigger (applies from the next bar)
                trig = is_be & live & ~stop_exit & ~be_done & (
                    (lng & (H[t] >= entry + bk * atr_e)) | (sht & (L[t] <= entry - bk * atr_e)))
                if trig.any():
                    be_done = be_done | trig
                    sl = np.where(trig & lng, np.maximum(sl, entry), np.where(trig & sht, np.minimum(sl, entry), sl))
                # trailing (plain trail, and the remainder after a partial target)
                tr_upd = (is_trail | (is_part & part_done)) & live & ~stop_exit & ~half_tp
                if tr_upd.any():
                    kt = np.where(is_trail, k1, k3)
                    ext = np.where(tr_upd & lng, np.maximum(ext, H[t]), np.where(tr_upd & sht, np.minimum(ext, L[t]), ext))
                    sl = np.where(tr_upd & lng, np.maximum(sl, ext - kt * atr_e),
                                  np.where(tr_upd & sht, np.minimum(sl, ext + kt * atr_e), sl))
                held = held + live
                time_exit = is_time & live & ~stop_exit & (held >= hmax)
                if time_exit.any():
                    ret = np.where(time_exit, ret - cost * size, ret)
                closed = stop_exit | time_exit
                tpnl = tpnl + np.where(live, ret, 0.0)
                if closed.any():
                    ntr += closed
                    nwin += closed & (tpnl > 0)
                    tpnl = np.where(closed, 0.0, tpnl)
                    blocked = np.where(closed, side, blocked)
                    cur = np.where(closed, 0.0, ps_after)
                else:
                    cur = ps_after
            else:
                cur = ps
        else:
            tpnl = tpnl + np.where(ps != 0, ret, 0.0)
        # ---- decision at the close of bar t (compares SIDES: a half position after a partial target is kept)
        raw = P[:, t].astype(float)
        blk = blocked != 0
        still = blk & (raw == blocked)
        blocked = np.where(blk & ~still, 0.0, blocked)
        want = np.where(still, 0.0, raw)
        cside = np.sign(cur)
        change = want != cside
        if change.any():
            closing = change & (cur != 0)
            csize = np.abs(cur)
            ret = ret - cost * csize * closing
            tpnl = tpnl - cost * csize * closing
            ntr += closing
            nwin += closing & (tpnl > 0)
            tpnl = np.where(closing, 0.0, tpnl)
            opening = change & (want != 0)
            ret = ret - cost * np.abs(want) * opening
            tpnl = np.where(opening, -cost * np.abs(want), tpnl)
            a = ATR[atr_sel, t]
            am = ATRM[atr_sel, t]
            vmul = np.clip(np.where(am > 0, a / np.where(am > 0, am, 1.0), 1.0), 0.5, 2.0)
            k2e = np.where(is_vol, k2 * vmul, k2)
            entry = np.where(opening, C[t], entry)
            sl = np.where(opening & has_sl, C[t] - want * k1 * a, np.where(opening, np.nan, sl))
            tp = np.where(opening & has_tp, C[t] + want * k2e * a, np.where(opening, np.nan, tp))
            ext = np.where(opening, C[t], ext)
            atr_e = np.where(opening, a, atr_e)
            held = np.where(opening, 0.0, held)
            part_done = np.where(change, False, part_done)
            be_done = np.where(change, False, be_done)
            E[opening, day_idx[t]] += 1
            cur = np.where(change, want, cur)
        inpos += cur != 0
        R[:, day_idx[t]] += ret.astype(np.float32)
        if keep_hourly:
            hourly[:, t] = ret
            pos_h[:, t] = cur
            ent_h[:, t] = entry
    open_ = cur != 0
    ntr += open_
    nwin += open_ & (tpnl > 0)
    return {"R": R, "E": E, "ntr": ntr, "nwin": nwin, "exposure": inpos / max(T - 1, 1), "hourly": hourly,
            "pos": pos_h, "ent": ent_h,
            "state": {"side": cur, "entry": entry, "sl": sl, "tp": tp}}


# ================================================================= statistics
def sharpe(x: np.ndarray, per_year: float = 365.0) -> float:
    x = np.asarray(x, dtype=float)
    if len(x) < 5:
        return 0.0
    sd = x.std(ddof=1)
    return float(x.mean() / sd * math.sqrt(per_year)) if sd > 0 else 0.0


def _rows_sharpe(R: np.ndarray) -> np.ndarray:
    mu = R.mean(1, dtype=np.float64)
    sd = R.std(1, ddof=1, dtype=np.float64)
    return np.where(sd > 0, mu / np.where(sd > 0, sd, 1) * math.sqrt(365.0), 0.0)


def _norm_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _norm_ppf(p: float) -> float:
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02,
         -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01,
         -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00,
         4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00]
    if p < 0.02425:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > 1 - 0.02425:
        return -_norm_ppf(1 - p)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def deflated_sharpe(x: np.ndarray, n_trials: float) -> float:
    """P(true Sharpe > 0) after best-of-N selection (Bailey & López de Prado);
    null dispersion 1/T, N = effective number of independent trials."""
    x = np.asarray(x, dtype=float)
    T = len(x)
    sd = x.std(ddof=1) if T > 2 else 0.0
    if T < 30 or sd <= 0:
        return 0.0
    sr = x.mean() / sd
    g = 0.5772156649
    N = max(float(n_trials), 2.0)
    sr0 = math.sqrt(1.0 / (T - 1)) * ((1 - g) * _norm_ppf(1 - 1.0 / N) + g * _norm_ppf(1 - 1.0 / (N * math.e)))
    z = (x - x.mean()) / sd
    skew, kurt = float((z ** 3).mean()), float((z ** 4).mean())
    den = 1 - skew * sr + (kurt - 1) / 4.0 * sr * sr
    return float(_norm_cdf((sr - sr0) * math.sqrt(T - 1) / math.sqrt(den))) if den > 0 else 0.0


def n_effective(R: np.ndarray) -> float:
    """Effective number of independent configurations: participation ratio of
    the correlation eigenvalues, computed in the (days x days) dual space so
    100k configurations cost the same as 700."""
    T = R.shape[1]
    G = np.zeros((T, T))
    used = 0
    for i in range(0, R.shape[0], 5000):                 # chunked: memory stays flat for 100k configurations
        X = np.asarray(R[i:i + 5000], dtype=np.float64)
        sd = X.std(1)
        X = X[sd > 0]
        if not len(X):
            continue
        Z = (X - X.mean(1, keepdims=True)) / X.std(1, keepdims=True)
        G += Z.T @ Z
        used += len(X)
    if used < 2:
        return 1.0
    ev = np.clip(np.linalg.eigvalsh(G / T), 0, None)    # same non-zero eigenvalues as the N x N correlation
    return float(max(1.0, ev.sum() ** 2 / (ev ** 2).sum()))


def t_stat(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    sd = x.std(ddof=1) if len(x) > 2 else 0.0
    return float(x.mean() / sd * math.sqrt(len(x))) if sd > 0 else 0.0


def alpha_t(x: np.ndarray, b: np.ndarray) -> Tuple[float, float, float]:
    """OLS x = alpha + beta*b -> (annual alpha, beta, t of alpha)."""
    x, b = np.asarray(x, float), np.asarray(b, float)
    n = len(x)
    if n < 30 or b.std() == 0:
        return 0.0, 0.0, 0.0
    beta = float(np.cov(x, b, ddof=1)[0, 1] / b.var(ddof=1))
    e = x - beta * b
    a = e.mean()
    se = math.sqrt(((e - a) ** 2).sum() / (n - 2)) * math.sqrt(1.0 / n + b.mean() ** 2 / ((b - b.mean()) ** 2).sum())
    return float(a * 365), beta, float(a / se) if se > 0 else 0.0


def max_dd(daily: np.ndarray) -> float:
    eq = np.cumsum(np.asarray(daily, float))
    if not len(eq):
        return 0.0
    peak = np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]
    return float(1 - math.exp((eq - peak).min()))


def _wf(R: np.ndarray, E: np.ndarray, folds: int, min_tr: int = 5) -> dict:
    """Walk-forward of the selection procedure on the daily matrix R (cfg x day)."""
    T = R.shape[1]
    edges = np.linspace(0, T, folds + 1).astype(int)
    oos, picks, fold_ret = [], [], []
    Ecum = np.zeros(R.shape[0])
    for k in range(1, folds):
        tr = slice(0, edges[k])
        te = slice(edges[k], edges[k + 1])
        Ecum = E[:, tr].sum(1)
        sr = _rows_sharpe(R[:, tr])
        sr[Ecum < min_tr] = -np.inf
        j = int(np.argmax(sr))
        if not np.isfinite(sr[j]):
            oos.append(np.zeros(edges[k + 1] - edges[k])); picks.append(None); fold_ret.append(0.0)
            continue
        x = R[j, te].astype(np.float64)
        oos.append(x); picks.append(j); fold_ret.append(float(x.sum()))
    x = np.concatenate(oos) if oos else np.zeros(0)
    return {"sharpe": sharpe(x), "t": t_stat(x), "ret": float(math.exp(x.sum()) - 1) if len(x) else 0.0,
            "pos_folds": int(sum(1 for f in fold_ret if f > 0)), "n_folds": folds - 1,
            "fold_ret": [round(math.exp(f) - 1, 4) for f in fold_ret], "picks": picks, "oos": x,
            "oos_start": int(edges[1])}


# ================================================================= leverage / liquidation
def leverage_daily(x: np.ndarray, years: float) -> List[dict]:
    """Leverage applied to a DAILY net return path (used for the walk-forward
    out-of-sample path). A day whose levered loss exceeds the margin
    (1/L - maintenance) is counted as a liquidation."""
    out = []
    simple = np.expm1(np.asarray(x, float))
    for lev in LEVERAGES:
        eq, peak, mdd, liq = 1.0, 1.0, 0.0, 0
        for r in simple:
            if r <= -(1.0 / lev - MMR):
                eq *= MMR * lev
                liq += 1
            else:
                eq *= max(1.0 + lev * r, 0.0)
            peak = max(peak, eq)
            mdd = max(mdd, 1 - eq / peak if peak > 0 else 1.0)
            if eq <= 1e-6:
                eq, mdd = 0.0, 1.0
                break
        out.append({"lev": lev, "cagr": round(eq ** (1 / years) - 1 if eq > 0 else -1.0, 4), "final": round(eq, 4),
                    "maxdd": round(mdd, 4), "liquidations": liq})
    return out


def leverage_table(hr: np.ndarray, pos: np.ndarray, ent: np.ndarray, H: np.ndarray, L: np.ndarray, C: np.ndarray,
                   bars_per_year: float, years: float) -> List[dict]:
    """Unit-exposure hourly net returns -> leveraged equity. Each trade uses
    isolated margin = whole equity; it is LIQUIDATED (equity keeps only
    L*maintenance) when the adverse move from entry reaches 1/L - maintenance
    on any bar's High/Low. After a liquidation the rule waits for its next
    signal. 'vol' = leverage set at each entry to hit 40% annual volatility
    (capped at 5x)."""
    T = len(hr)
    simple = np.expm1(hr)
    win = max(24, int(bars_per_year / 365 * 20))
    px_r = np.concatenate([[0.0], np.diff(np.log(C))])
    vol = pd.Series(px_r).rolling(win, min_periods=win // 2).std().values * math.sqrt(bars_per_year)
    out = []
    for lev in list(LEVERAGES) + ["vol"]:
        eq, peak, mdd, liq, dead, cur_lev = 1.0, 1.0, 0.0, 0, False, 1.0
        for t in range(1, T):
            p_prev, p_now = pos[t - 1], pos[t]
            if p_prev == 0 and p_now != 0:          # trade opened at this close: choose its leverage
                if lev == "vol":
                    v = vol[t] if np.isfinite(vol[t]) and vol[t] > 0 else VOL_TARGET
                    cur_lev = float(np.clip(VOL_TARGET / v, 0.25, VOL_MAX_LEV))
                else:
                    cur_lev = float(lev)
                dead = False
            if p_prev != 0 and not dead:
                e = ent[t - 1]
                adverse = (L[t] / e - 1.0) if p_prev > 0 else (1.0 - H[t] / e)
                if e > 0 and adverse <= -(1.0 / cur_lev - MMR):
                    eq *= MMR * cur_lev
                    liq += 1
                    dead = True
                else:
                    eq *= max(1.0 + cur_lev * simple[t], 0.0)
            elif not dead:
                eq *= max(1.0 + cur_lev * simple[t], 0.0)        # entry cost of a trade opened at this close
            if p_now != p_prev and p_prev != 0 and p_now != 0:    # direct flip: new trade, new leverage
                dead = False
                if lev == "vol":
                    v = vol[t] if np.isfinite(vol[t]) and vol[t] > 0 else VOL_TARGET
                    cur_lev = float(np.clip(VOL_TARGET / v, 0.25, VOL_MAX_LEV))
            if p_now == 0:
                dead = False
            peak = max(peak, eq)
            mdd = max(mdd, 1 - eq / peak if peak > 0 else 1.0)
            if eq <= 1e-6:
                eq = 0.0
                mdd = 1.0
                break
        cagr = eq ** (1 / years) - 1 if eq > 0 and years > 0 else -1.0
        out.append({"lev": "vol" if lev == "vol" else int(lev), "cagr": round(cagr, 4), "final": round(eq, 4),
                    "maxdd": round(mdd, 4), "liquidations": liq})
    return out


# ================================================================= research
def _slice_ctx(ctx: Ctx, w0: int, w1: int) -> Tuple[dict, Dict[str, np.ndarray]]:
    arr = {"O": ctx.O[w0:w1], "H": ctx.H[w0:w1], "L": ctx.L[w0:w1], "C": ctx.C[w0:w1], "close_fill": ctx.no_wicks,
           "ATRM": np.vstack([pd.Series(ctx.atr[tf]).rolling(720, min_periods=48).median().values[w0:w1]
                              for tf in ("1h", "4h", "1d")]),
           "ATR": np.vstack([np.nan_to_num(ctx.atr[tf][w0:w1], nan=np.nan) for tf in ("1h", "4h", "1d")])}
    return arr, {}


ATR_ROW = {"1h": 0, "4h": 1, "1d": 2}


def _enumerate(ctx: Ctx, w0: int, w1: int, with_modes=MODES, exits=EXITS):
    """Yield (meta, position array) for every distinct configuration."""
    seen = set()
    for cat, d, f in direction_rules(ctx):
        dirv = ctx.direction(d)
        base = (dirv * ctx.mask(f, dirv))[w0:w1]
        modes = ("LS",) if "bench" in d else with_modes
        for mode in modes:
            p = base if mode == "LS" else (np.clip(base, 0, 1) if mode == "LO" else np.clip(base, -1, 0))
            if not np.any(p):
                continue
            key = hash(p.astype(np.int8).tobytes())
            if key in seen:
                continue
            seen.add(key)
            p8 = p.astype(np.int8)
            ex_list = exits
            if exits is EXITS:
                if "trig" in d:
                    ex_list = TRIG_EXITS
                elif int(d.get("cad", 1)) >= 24:
                    ex_list = SLOW_EXITS
            for ex in ex_list:
                if "bench" in d and ex["type"] != "sig":
                    continue
                yield {"cat": cat, "d": d, "f": f, "mode": mode, "exit": ex, "atr": _dir_tf(d)}, p8


def _run_universe(ctx: Ctx, w0: int, w1: int, cost: float, days: pd.DatetimeIndex, day_idx: np.ndarray,
                  fund_long: float = FUND_LONG_H, exits=EXITS, modes=MODES):
    arr, _ = _slice_ctx(ctx, w0, w1)
    metas, Rs, Es, ntr, nwin, expo, states = [], [], [], [], [], [], []
    buf_m, buf_p = [], []

    def flush():
        if not buf_m:
            return
        P = np.vstack(buf_p)
        ex = [m["exit"] for m in buf_m]
        sel = np.array([ATR_ROW[m["atr"]] for m in buf_m])
        out = simulate_batch(P, ex, sel, arr, cost, day_idx, len(days), fund_long=fund_long)
        metas.extend(buf_m); Rs.append(out["R"]); Es.append(out["E"])
        ntr.append(out["ntr"]); nwin.append(out["nwin"]); expo.append(out["exposure"])
        st = out["state"]
        states.extend({"side": float(st["side"][i]), "entry": float(st["entry"][i]), "sl": float(st["sl"][i]),
                       "tp": float(st["tp"][i])} for i in range(len(buf_m)))
        buf_m.clear(); buf_p.clear()

    for meta, p in _enumerate(ctx, w0, w1, modes, exits):
        buf_m.append(meta); buf_p.append(p)
        if len(buf_m) >= BATCH:
            flush()
    flush()
    return (metas, np.vstack(Rs), np.vstack(Es), np.concatenate(ntr), np.concatenate(nwin),
            np.concatenate(expo), states, arr)


def _bars_per_year(idx: pd.DatetimeIndex) -> float:
    yrs = max((idx[-1] - idx[0]).total_seconds() / (365.25 * 86400), 1e-6)
    return len(idx) / yrs


def long_daily(d1: pd.DataFrame, cost: float, crypto: bool) -> Optional[dict]:
    """Path B: 1d technical rules (alone, inverted, majority vote) on up to 10
    years of daily bars, as perps (funding included)."""
    if d1 is None or (d1.index[-1] - d1.index[0]).days < WINDOW_DAYS * 1.5:
        return None
    feats = {}
    for fam, plist in TECH["1d"].items():
        for p in plist:
            feats[f"tech:1d:{fam}:{_pstr(p)}"] = np.nan_to_num(tech_signal(fam, p, d1).values.astype(float))
    T = len(d1)
    arr = {"O": d1["Open"].values.astype(float), "H": d1["High"].values.astype(float),
           "L": d1["Low"].values.astype(float), "C": d1["Close"].values.astype(float)}
    a1 = _atr(d1).values
    arr["ATR"] = np.vstack([a1, a1, a1])
    dirs = []
    for k, v in feats.items():
        dirs.append(({"src": k, "op": "sign", "inv": False}, v))
        dirs.append(({"src": k, "op": "sign", "inv": True}, -v))
    trend = [v for k, v in feats.items() if k.split(":")[2] in TREND_FAMS]
    vote = np.sum(trend, axis=0)
    dirs.append(({"ens": [{"src": k, "op": "sign"} for k in feats if k.split(":")[2] in TREND_FAMS], "need": "maj"},
                 np.where(np.abs(vote) >= math.ceil(len(trend) / 2), np.sign(vote), 0.0)))
    bench = ({"bench": "long"}, np.ones(T))
    exits = [e for e in EXITS if e["type"] != "time"]
    metas, P = [], []
    seen = set()
    for d, v in dirs + [bench]:
        for mode in (("LS",) if "bench" in d else MODES):
            p = v if mode == "LS" else (np.clip(v, 0, 1) if mode == "LO" else np.clip(v, -1, 0))
            key = hash(p.astype(np.int8).tobytes())
            if key in seen or not np.any(p):
                continue
            seen.add(key)
            for ex in (exits if "bench" not in d else [EXITS[0]]):
                metas.append({"cat": "uzun-dönem 1g", "d": d, "f": None, "mode": mode, "exit": ex, "atr": "1d"})
                P.append(p.astype(np.int8))
    days = pd.date_range(d1.index[0].normalize(), d1.index[-1].normalize(), freq="D", tz="UTC")
    day_idx = days.get_indexer(d1.index.normalize())
    fund = FUND_LONG_H * 24 * (1.0 if crypto else 7.0 / 5.0)
    P = np.vstack(P)
    out = simulate_batch(P, [m["exit"] for m in metas], np.full(len(metas), 2), arr, cost, day_idx, len(days), fund_long=fund)
    R, E = out["R"], out["E"]
    srs = _rows_sharpe(R)
    ntr = out["ntr"]
    rank = np.where(ntr >= CRIT["trades"], srs, -np.inf)
    rank[[i for i, m in enumerate(metas) if "bench" in m["d"]]] = -np.inf
    k = int(np.argmax(rank)) if np.isfinite(rank).any() else int(np.argmax(srs))
    wf = _wf(R, E, LONG_FOLDS, min_tr=10)
    bi = [i for i, m in enumerate(metas) if "bench" in m["d"]][0]
    bh = R[bi].astype(float)
    al, be, at = alpha_t(wf["oos"], bh[wf["oos_start"]:])
    dsr = deflated_sharpe(R[k], n_effective(R))
    years = len(days) / 365.25
    m = metas[k]
    rule = {"cat": m["cat"], "d": m["d"], "f": None, "mode": m["mode"], "exit": m["exit"], "atr": "1d"}
    base = {"long_years": years >= CRIT["long_years"], "long_t": wf["t"] >= CRIT["long_t"],
            "long_pos_folds": wf["pos_folds"] >= CRIT["long_pos_folds"], "dsr": dsr >= CRIT["dsr"],
            "trades": ntr[k] >= CRIT["trades"]}
    return {"years": round(years, 1), "rule": rule, "label": rule_label(rule), "id": rule_id(m["cat"], m["d"], None, m["mode"], m["exit"]),
            "sharpe": round(float(srs[k]), 2), "ret": round(float(math.expm1(R[k].sum())), 4), "maxdd": round(max_dd(R[k]), 4),
            "trades": int(ntr[k]), "win": round(float(out["nwin"][k] / max(ntr[k], 1)), 3), "dsr": round(dsr, 3),
            "wf_sharpe": round(wf["sharpe"], 2), "wf_t": round(wf["t"], 2), "wf_pos_folds": wf["pos_folds"], "wf_folds": wf["n_folds"],
            "wf_fold_ret": wf["fold_ret"], "alpha": round(al, 4), "beta": round(be, 2), "alpha_t": round(at, 2),
            "bh_sharpe": round(sharpe(bh), 2), "bh_ret": round(float(math.expm1(bh.sum())), 4), "bh_maxdd": round(max_dd(bh), 4),
            "base": base, "base_ok": all(base.values()), "n_configs": len(metas),
            "state": {"side": float(out["state"]["side"][k]), "entry": float(out["state"]["entry"][k]),
                      "sl": float(out["state"]["sl"][k]), "tp": float(out["state"]["tp"][k])}}


DISC_K = 40            # best singles (by discovery period) that enter the combination search
GREEDY_MAX = 7         # largest majority-vote ensemble built greedily


def discover_combos(ctx: Ctx, metas: list, R: np.ndarray, E: np.ndarray, w0: int, w1: int, arr: dict, cost: float,
                    days: pd.DatetimeIndex, day_idx: np.ndarray, bh: np.ndarray) -> dict:
    """Data-driven combinations with an UNTOUCHED holdout.
    Discovery = first 50% of the window: rank every single, build all pairs
    (both must agree) of the best 40 and greedy majority-vote ensembles of
    2..7 signals. Validation = next 25%: pick the winner. Holdout = last 25%:
    never seen by any choice above -> the honest verdict."""
    D = R.shape[1]
    e1, e2 = int(D * 0.50), int(D * 0.75)
    elig = [i for i, m in enumerate(metas) if m.get("f") is None and "bench" not in m["d"] and "ens" not in m["d"]
            and (m["cat"].startswith("tek") or m["cat"] in ("sys", "teknik"))]
    if not elig:
        return {}
    el = np.array(elig)
    s1 = _rows_sharpe(R[el, :e1])
    s1[E[el, :e1].sum(1) < 8] = -np.inf
    order = el[np.argsort(-s1)]
    seen, top = set(), []
    for i in order:
        if not np.isfinite(_rows_sharpe(R[[i], :e1])[0]):
            break
        key = json.dumps(metas[i]["d"], sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        top.append(i)
        if len(top) >= DISC_K:
            break
    if len(top) < 2:
        return {}
    rules = []
    for a in range(len(top)):
        for b in range(a + 1, len(top)):
            ma, mb = metas[top[a]], metas[top[b]]
            for ex in ([ma["exit"]] if ma["exit"]["type"] == "sig" else [ma["exit"], {"type": "sig"}]):
                rules.append({"cat": "kombi·ikili", "d": {"ens": [ma["d"], mb["d"]], "need": "all"}, "f": None,
                              "mode": ma["mode"], "exit": ex, "atr": ma["atr"]})

    def _sim(rule_list):
        if not rule_list:
            return np.zeros((0, D), dtype=np.float32), np.zeros((0, D), dtype=np.int16)
        outR, outE = [], []
        for k in range(0, len(rule_list), BATCH):
            chunk = rule_list[k:k + BATCH]
            P = np.vstack([ctx.position(r)[w0:w1] for r in chunk])
            o = simulate_batch(P, [r["exit"] for r in chunk], np.array([ATR_ROW[r["atr"]] for r in chunk]), arr, cost,
                               day_idx, len(days))
            outR.append(o["R"]); outE.append(o["E"])
        return np.vstack(outR), np.vstack(outE)

    Rp, Ep = _sim(rules)
    # greedy majority-vote ensembles (each step chooses on the DISCOVERY period only)
    members = [top[0]]
    greedy_rules = []
    for step in range(2, GREEDY_MAX + 1):
        cand = [i for i in top if i not in members]
        if not cand:
            break
        trial = [{"cat": "kombi·oylama", "d": {"ens": [metas[j]["d"] for j in members + [c]], "need": "maj"}, "f": None,
                  "mode": metas[top[0]]["mode"], "exit": {"type": "sig"}, "atr": metas[top[0]]["atr"]} for c in cand]
        Rt, _ = _sim(trial)
        sc = _rows_sharpe(Rt[:, :e1])
        k = int(np.argmax(sc))
        members.append(cand[k])
        greedy_rules.append(trial[k])
    Rg, Eg = _sim(greedy_rules)
    cand_rules = [metas[i] for i in top] + rules + greedy_rules
    CR = np.vstack([R[top], Rp, Rg]).astype(np.float64)
    CE = np.vstack([E[top], Ep, Eg])
    sd1, sd2, sd3 = _rows_sharpe(CR[:, :e1]), _rows_sharpe(CR[:, e1:e2]), _rows_sharpe(CR[:, e2:])
    n2 = CE[:, e1:e2].sum(1)
    ok = (sd1 > 0) & (n2 >= 5)
    rank = np.where(ok, sd2, -np.inf)
    rows = []
    for i in [j for j in np.argsort(-rank)[:15] if np.isfinite(rank[j])]:
        x3 = CR[i, e2:]
        al, be, at = alpha_t(x3, bh[e2:])
        rows.append({"label": rule_label(cand_rules[i]), "cat": cand_rules[i]["cat"], "rule": cand_rules[i],
                     "d1": round(float(sd1[i]), 2), "d2": round(float(sd2[i]), 2), "d3": round(float(sd3[i]), 2),
                     "ret3": round(float(math.expm1(x3.sum())), 4), "t3": round(t_stat(x3), 2), "alpha_t3": round(at, 2),
                     "beta3": round(be, 2), "trades": int(CE[i].sum())})
    chosen = rows[0] if rows else None
    passed = bool(chosen and chosen["t3"] >= CRIT["wf_t"] and chosen["alpha_t3"] >= CRIT["alpha_t"] and chosen["d2"] > 0)
    split = [str(days[0].date()), str(days[e1].date()), str(days[e2].date()), str(days[-1].date())]
    return {"split": split, "n_candidates": int(len(cand_rules)), "n_pairs": len(rules), "n_greedy": len(greedy_rules),
            "top": rows, "chosen": chosen, "passed": passed,
            "greedy_path": [rule_label(r) for r in greedy_rules],
            "_extra": (cand_rules[len(top):], CR[len(top):], sd1[len(top):], sd2[len(top):], sd3[len(top):])}


def research(data: Dict[str, dict], panel: Optional[pd.DataFrame] = None, now: Optional[datetime] = None,
             source: str = "yahoo", all_rows: Optional[list] = None, alt: Optional[pd.DataFrame] = None) -> dict:
    now = now or datetime.now(timezone.utc)
    res = {"generated_at": now.isoformat(), "source": source, "panel": (panel.attrs.get("source") if panel is not None else None),
           "criteria": CRIT, "costs": {"fee_slippage_per_side": COST, "funding_long_per_8h": FUND_LONG_H * 8,
                                       "funding_short_per_8h": FUND_SHORT_H * 8},
           "assets": {}, "categories": [], "system_signals": {}, "robust": [], "n_configs": 0}
    cat_rows, sys_rows, hz_rows, trig_rows, alt_rows = [], [], [], [], []
    robust: Dict[str, list] = {}
    robust_meta: Dict[str, dict] = {}
    for a, frames in data.items():
        h1 = frames.get("1h")
        if h1 is None or len(h1) < 500:
            continue
        sysp = panel[panel["asset"] == a] if panel is not None else None
        altp = alt[alt["asset"] == a] if alt is not None else None
        ctx = Ctx(h1, frames.get("1d"), sysp, altp)
        if ctx.alt_cols:
            print(f"[lab] {a}: {len(ctx.alt_cols) // 2} alternatif veri sinyali eklendi", flush=True)
        idx = ctx.idx
        w0 = int(np.searchsorted(idx.values, (idx[-1] - pd.Timedelta(days=WINDOW_DAYS)).to_datetime64()))
        w1 = ctx.T
        if sysp is not None and ctx.sys_cover[1] > ctx.sys_cover[0]:
            w0, w1 = max(w0, ctx.sys_cover[0]), min(w1, ctx.sys_cover[1])
        widx = idx[w0:w1]
        days = pd.date_range(widx[0].normalize(), widx[-1].normalize(), freq="D", tz="UTC")
        day_idx = days.get_indexer(widx.normalize())
        cost = COST[a]
        metas, R, E, ntr, nwin, expo, states, arr = _run_universe(ctx, w0, w1, cost, days, day_idx)
        N = len(metas)
        res["n_configs"] += N
        print(f"[lab] {a}: {N} konfigürasyon · pencere {days[0].date()} → {days[-1].date()}", flush=True)
        srs = _rows_sharpe(R)
        half = R.shape[1] // 2
        s1, s2 = _rows_sharpe(R[:, :half]), _rows_sharpe(R[:, half:])
        rank = np.where((ntr >= MIN_SELECT_TRADES), srs, -np.inf)
        bench_i = [i for i, m in enumerate(metas) if "bench" in m["d"]]
        long_i = [i for i in bench_i if metas[i]["d"]["bench"] == "long"][0]
        rank[bench_i] = -np.inf
        best = int(np.argmax(rank))
        wf = _wf(R, E, FOLDS, min_tr=max(3, MIN_SELECT_TRADES // 3))
        neff = n_effective(R)
        dsr = deflated_sharpe(R[best], neff)
        bh = R[long_i].astype(float)
        al, be, at = alpha_t(wf["oos"], bh[wf["oos_start"]:])
        base_a = {"wf_t": wf["t"] >= CRIT["wf_t"], "pos_folds": wf["pos_folds"] >= CRIT["pos_folds"],
                  "dsr": bool(dsr >= CRIT["dsr"]), "trades": bool(ntr[best] >= CRIT["trades"])}
        lg = long_daily(frames.get("1d"), cost, a in ("BTC", "ETH"))
        combo = {}
        try:
            combo = discover_combos(ctx, metas, R, E, w0, w1, arr, cost, days, day_idx, bh)
        except Exception as exc:                       # never lose the whole run for the combo stage
            print(f"[lab] {a}: kombinasyon aşaması atlandı ({exc})", flush=True)
        if all(base_a.values()):
            path, kind = "A", ("alpha" if at >= CRIT["alpha_t"] else "beta")
            rule = metas[best]; st = states[best]
        elif lg and lg["base_ok"]:
            path, kind = "B", ("alpha" if lg["alpha_t"] >= CRIT["alpha_t"] else "beta")
            rule = lg["rule"]; st = lg["state"]
        elif combo.get("passed"):
            path, kind = "C", "alpha"
            rule = combo["chosen"]["rule"]
            o1 = simulate_batch(ctx.position(rule)[w0:w1][None, :], [rule["exit"]], np.array([ATR_ROW[rule["atr"]]]),
                                arr, cost, day_idx, len(days))
            st = {k: float(v[0]) for k, v in o1["state"].items()}
        else:
            path, kind = None, None
            rule = metas[best]; st = states[best]
        # leverage table for the candidate (window A, hourly)
        lev_rows = None
        if path != "B":
            one = simulate_batch(ctx.position(rule)[w0:w1][None, :], [rule["exit"]],
                                 np.array([ATR_ROW[rule["atr"]]]), arr, cost, day_idx, len(days), keep_hourly=True)
            lev_rows = leverage_table(one["hourly"][0], one["pos"][0], one["ent"][0], arr["H"], arr["L"], arr["C"],
                                      _bars_per_year(widx), len(days) / 365.25)
        top = []
        for i in [j for j in np.argsort(-rank)[:15] if np.isfinite(rank[j])]:
            top.append({"label": rule_label(metas[i]), "id": rule_id(**_idargs(metas[i])), "cat": metas[i]["cat"],
                        "sharpe": round(float(srs[i]), 2), "h1": round(float(s1[i]), 2), "h2": round(float(s2[i]), 2),
                        "ret": round(float(math.expm1(R[i].sum())), 4), "maxdd": round(max_dd(R[i]), 4),
                        "trades": int(ntr[i]), "win": round(float(nwin[i] / max(ntr[i], 1)), 3),
                        "expo": round(float(expo[i]), 2)})
        res["assets"][a] = {
            "window": [str(days[0].date()), str(days[-1].date())], "n_configs": N, "n_effective": round(neff, 1),
            "best": {"label": rule_label(metas[best]), "id": rule_id(**_idargs(metas[best])), "rule": metas[best],
                     "sharpe": round(float(srs[best]), 2), "h1": round(float(s1[best]), 2), "h2": round(float(s2[best]), 2),
                     "ret": round(float(math.expm1(R[best].sum())), 4), "maxdd": round(max_dd(R[best]), 4),
                     "trades": int(ntr[best]), "win": round(float(nwin[best] / max(ntr[best], 1)), 3), "dsr": round(dsr, 3)},
            "wf": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in wf.items() if k not in ("oos", "picks", "oos_start")},
            "wf_alpha": round(al, 4), "wf_beta": round(be, 2), "wf_alpha_t": round(at, 2),
            "wf_picks": [rule_label(metas[j]) if j is not None else None for j in wf["picks"]],
            "bh": {"sharpe": round(sharpe(bh), 2), "ret": round(float(math.expm1(bh.sum())), 4), "maxdd": round(max_dd(bh), 4)},
            "long": lg, "base_a": base_a, "path": path, "kind": kind, "proven": kind == "alpha",
            "candidate": {"rule": rule, "label": rule_label(rule)},
            "signal": {"side": {1: "LONG", -1: "SHORT", 0: "FLAT"}[int(np.sign(st["side"]))],
                       "entry": st["entry"] if st["side"] else None, "sl": st["sl"] if st["side"] and np.isfinite(st["sl"]) else None,
                       "tp": st["tp"] if st["side"] and np.isfinite(st["tp"]) else None, "as_of": str(widx[-1])},
            "leverage": lev_rows, "top": top,
            "combo": {k: v for k, v in combo.items() if k != "_extra"} if combo else None,
            "leverage_wf": leverage_daily(wf["oos"], len(wf["oos"]) / 365.25),
        }
        # category table input
        cats = sorted({m["cat"] for m in metas})
        for c in cats:
            ii = np.array([i for i, m in enumerate(metas) if m["cat"] == c])
            fwf = _wf(R[ii], E[ii], FOLDS, min_tr=5)
            ok = np.isfinite(rank[ii])
            cat_rows.append({"asset": a, "cat": c, "n": len(ii), "best": float(np.max(srs[ii][ok])) if ok.any() else float(np.max(srs[ii])),
                             "median": float(np.median(srs[ii])), "wf": fwf["sharpe"]})
        # v6 horizon matrix: each signal, system orientation, sign, smoothed, signal exit, long+short, per horizon
        for i, m in enumerate(metas):
            d = m["d"]
            if (m["cat"].startswith("tek") or (m["cat"] == "sys" and "cad" not in d)) and m["f"] is None \
                    and m["mode"] == "LS" and m["exit"]["type"] == "sig" and d.get("op") == "sign" \
                    and not d.get("inv") and bool(d.get("smooth")) == (int(d.get("cad", 1)) > 1) \
                    and not str(d.get("src", "")).startswith("z::"):
                hz_rows.append({"asset": a, "src": d["src"], "cad": int(d.get("cad", 1)), "sharpe": float(srs[i]),
                                "h1": float(s1[i]), "h2": float(s2[i])})
        # v7: system direction as FILTER for technical triggers - same trigger/exit/mode with vs without the filter
        base_tr = {}
        for i, m in enumerate(metas):
            d = m["d"]
            if "trig" in d and not d.get("bias"):
                base_tr[(d["trig"], m["mode"], json.dumps(m["exit"], sort_keys=True))] = i
        for i, m in enumerate(metas):
            d = m["d"]
            if "trig" in d and d.get("bias"):
                j = base_tr.get((d["trig"], m["mode"], json.dumps(m["exit"], sort_keys=True)))
                if j is None:
                    continue
                b = d["bias"]
                trig_rows.append({"asset": a, "trig": d["trig"], "bias": b["src"], "bcad": int(b.get("cad", 1)), "mode": m["mode"],
                                  "exit": m["exit"]["type"], "i_label": rule_label(m), "sharpe": float(srs[i]), "h1": float(s1[i]),
                                  "h2": float(s2[i]), "trades": int(ntr[i]), "b_sharpe": float(srs[j]), "b_h1": float(s1[j]),
                                  "b_h2": float(s2[j]), "b_trades": int(ntr[j])})
            src = str(d.get("src", ""))
            if "alt::" in src and m["f"] is None and m["mode"] == "LS" and m["exit"]["type"] == "sig" and not d.get("inv"):
                alt_rows.append({"asset": a, "src": src, "cad": int(d.get("cad", 1)), "op": d.get("op"), "thr": d.get("thr"),
                                 "smooth": bool(d.get("smooth")), "sharpe": float(srs[i]), "h1": float(s1[i]), "h2": float(s2[i]),
                                 "trades": int(ntr[i])})
        # every system signal alone (LS, sign, signal exit): which outputs of the system carry information?
        for i, m in enumerate(metas):
            d = m["d"]
            if m["cat"] == "sys" and m["mode"] == "LS" and m["exit"]["type"] == "sig" and d.get("op") == "sign" and not d.get("inv"):
                sys_rows.append({"asset": a, "src": d["src"], "sharpe": float(srs[i]), "h1": float(s1[i]), "h2": float(s2[i]),
                                 "trades": int(ntr[i])})
            if m["cat"] in ("teknik", "sys", "oylama") and m["f"] is None and not d.get("inv"):
                key = rule_id(**_idargs(m))
                robust.setdefault(key, []).append(float(srs[i]))
                robust_meta[key] = m
        if all_rows is not None and combo.get("_extra"):
            cr, CRx, c1, c2, c3 = combo["_extra"]
            for k, m in enumerate(cr):
                all_rows.append((a, m["cat"], rule_label(m), m["mode"], m["exit"]["type"], round(float(_rows_sharpe(CRx[[k]])[0]), 3),
                                 round(float(c1[k]), 3), round(float(c3[k]), 3), round(float(math.expm1(CRx[k].sum())), 4),
                                 round(max_dd(CRx[k]), 4), -1, None, None))
        if all_rows is not None:
            for i, m in enumerate(metas):
                all_rows.append((a, m["cat"], rule_label(m), m["mode"], m["exit"]["type"], round(float(srs[i]), 3),
                                 round(float(s1[i]), 3), round(float(s2[i]), 3), round(float(math.expm1(R[i].sum())), 4),
                                 round(max_dd(R[i]), 4), int(ntr[i]), round(float(nwin[i] / max(ntr[i], 1)), 3),
                                 round(float(expo[i]), 3)))
        del R, E
    if cat_rows:
        g = pd.DataFrame(cat_rows).groupby("cat").agg(n=("n", "sum"), best=("best", "mean"), median=("median", "mean"),
                                                       wf=("wf", "mean"), wf_pos=("wf", lambda s: int((s > 0).sum())),
                                                       assets=("wf", "size")).reset_index()
        res["categories"] = g.sort_values("wf", ascending=False).round(3).to_dict("records")
    if sys_rows:
        S = pd.DataFrame(sys_rows)
        piv = S.pivot_table(index="src", columns="asset", values="sharpe")
        st_ = S.groupby("src").agg(mean=("sharpe", "mean"), h1=("h1", "mean"), h2=("h2", "mean"),
                                   pos=("sharpe", lambda s: int((s > 0).sum())), n=("sharpe", "size"))
        st_["pos"] = st_["pos"].astype(int)
        st_["n"] = st_["n"].astype(int)
        st_ = st_.join(piv).sort_values("mean", key=lambda s: -s.abs())
        res["system_signals"] = {"columns": list(piv.columns), "rows": [
            dict(src=k, name=tr_name(k), **{c: (None if pd.isna(v) else round(float(v), 2)) for c, v in r.items()})
            for k, r in st_.head(40).iterrows()]}
    if hz_rows:
        H = pd.DataFrame(hz_rows)
        piv = H.pivot_table(index="src", columns="cad", values="sharpe", aggfunc="mean")
        pos = H.assign(p=H["sharpe"] > 0).pivot_table(index="src", columns="cad", values="p", aggfunc="sum")
        piv = piv.reindex(columns=[c for c in CADENCES if c in piv.columns])
        best_abs = piv.abs().max(axis=1).sort_values(ascending=False)
        res["horizon"] = {"cads": [int(c) for c in piv.columns], "rows": [
            {"src": k, "name": tr_name(k), **{str(int(c)): (None if pd.isna(piv.loc[k, c]) else round(float(piv.loc[k, c]), 2))
                                             for c in piv.columns},
             **{f"pos{int(c)}": (None if pd.isna(pos.loc[k, c]) else int(pos.loc[k, c])) for c in piv.columns},
             "n": int((H["src"] == k).sum() / max(len(piv.columns), 1))}
            for k in best_abs.index[:45]]}
        cad_avg = H.groupby("cad")["sharpe"].agg(["mean", "median", lambda s: float((s > 0).mean())])
        res["horizon_summary"] = [{"cad": int(c), "mean": round(float(r["mean"]), 2), "median": round(float(r["median"]), 2),
                                   "pos_share": round(float(r.iloc[2]), 2)} for c, r in cad_avg.iterrows()]
    if trig_rows:
        res["trigger"] = trigger_summary(pd.DataFrame(trig_rows))
    if alt_rows:
        A = pd.DataFrame(alt_rows)
        A["key"] = A["src"] + "|" + A["cad"].astype(str) + "|" + A["op"].astype(str) + "|" + A["thr"].astype(str) + "|" + A["smooth"].astype(str)
        g = A.groupby("key").agg(src=("src", "first"), cad=("cad", "first"), op=("op", "first"), thr=("thr", "first"),
                                 smooth=("smooth", "first"),
                                 mean=("sharpe", "mean"), h1=("h1", "mean"), h2=("h2", "mean"),
                                 pos=("sharpe", lambda x: int((x > 0).sum())), n=("sharpe", "size"),
                                 both=("h1", lambda x: 0))
        both = A.assign(b=(A["h1"] > 0) & (A["h2"] > 0)).groupby("key")["b"].sum()
        g["both"] = both.reindex(g.index).astype(int)
        g = g.sort_values("mean", key=lambda x: -x.abs())
        res["alt_signals"] = [{"name": tr_name(r["src"]), "src": r["src"], "cad": int(r["cad"]),
                               "op": ("işaret" if r["op"] == "sign" else f"∣z∣>{r['thr']}") + (" · ufuk ort." if r["smooth"] else " · son değer"), "mean": round(float(r["mean"]), 2),
                               "h1": round(float(r["h1"]), 2), "h2": round(float(r["h2"]), 2), "pos": int(r["pos"]),
                               "both": int(r["both"]), "n": int(r["n"])} for _, r in g.head(30).iterrows()]
        res["alt_assets"] = sorted(A["asset"].unique().tolist())
    nA = len(res["assets"])
    rob = [{"id": k, "label": rule_label(robust_meta[k]), "rule": robust_meta[k], "mean_sharpe": round(float(np.mean(v)), 2),
            "pos_assets": int(sum(x > 0 for x in v)), "n_assets": len(v)}
           for k, v in robust.items() if len(v) >= max(2, nA - 1) and "bench" not in robust_meta[k]["d"]]
    res["robust"] = sorted(rob, key=lambda r: (-r["pos_assets"], -r["mean_sharpe"]))[:15]
    if res["robust"]:
        res["consensus"] = res["robust"][0]
    return res


def trigger_summary(T: pd.DataFrame) -> dict:
    """Does the system's direction, used ONLY as a filter, improve technical entry triggers?
    lift = Sharpe(trigger taken only in the bias direction) - Sharpe(same trigger, same exit, no filter).
    A filter is credible only if the lift is positive in BOTH halves of the window."""
    T = T.copy()
    T["lift"] = T["sharpe"] - T["b_sharpe"]
    T["lift1"] = T["h1"] - T["b_h1"]
    T["lift2"] = T["h2"] - T["b_h2"]
    T["both"] = (T["lift1"] > 0) & (T["lift2"] > 0)
    base = T.drop_duplicates(["asset", "trig", "mode", "exit"])
    out = {"n_pairs": int(len(T)), "base_mean": round(float(base["b_sharpe"].mean()), 2),
           "base_pos": round(float((base["b_sharpe"] > 0).mean()), 2), "filt_mean": round(float(T["sharpe"].mean()), 2),
           "filt_pos": round(float((T["sharpe"] > 0).mean()), 2), "lift_mean": round(float(T["lift"].mean()), 2),
           "lift_pos": round(float((T["lift"] > 0).mean()), 2), "lift_both": round(float(T["both"].mean()), 2)}
    g = T.groupby(["bias", "bcad"]).agg(lift=("lift", "mean"), lift1=("lift1", "mean"), lift2=("lift2", "mean"),
                                        both=("both", "mean"), filt=("sharpe", "mean"), n=("lift", "size"),
                                        assets=("asset", "nunique")).reset_index()
    g = g[g["n"] >= 6].sort_values("lift", ascending=False)
    lab = {1: "anlık", 24: "günlük ort.", 168: "haftalık ort."}
    out["biases"] = [{"name": tr_name(r["bias"]), "src": r["bias"], "cad": lab.get(int(r["bcad"]), str(r["bcad"])),
                      "lift": round(float(r["lift"]), 2), "lift1": round(float(r["lift1"]), 2), "lift2": round(float(r["lift2"]), 2),
                      "both": round(float(r["both"]), 2), "filt": round(float(r["filt"]), 2), "n": int(r["n"]), "assets": int(r["assets"])}
                     for _, r in g.iterrows()]
    t = T.groupby("trig").agg(base=("b_sharpe", "mean"), filt=("sharpe", "mean"), lift=("lift", "mean"),
                              both=("both", "mean")).reset_index().sort_values("lift", ascending=False)
    out["triggers"] = [{"trig": r["trig"], "name": f"{TRIG_TR.get(r['trig'].split(':')[2], r['trig'])} · {r['trig'].split(':')[1]}",
                        "base": round(float(r["base"]), 2), "filt": round(float(r["filt"]), 2), "lift": round(float(r["lift"]), 2),
                        "both": round(float(r["both"]), 2)} for _, r in t.iterrows()]
    T["robust"] = T[["h1", "h2"]].min(axis=1)
    top = T[(T["trades"] >= 20)].sort_values("robust", ascending=False).head(20)
    out["top"] = [{"asset": r["asset"], "label": r["i_label"], "sharpe": round(float(r["sharpe"]), 2), "h1": round(float(r["h1"]), 2),
                   "h2": round(float(r["h2"]), 2), "base": round(float(r["b_sharpe"]), 2), "lift": round(float(r["lift"]), 2),
                   "trades": int(r["trades"])} for _, r in top.iterrows()]
    return out


def _idargs(m: dict) -> dict:
    return {"cat": m["cat"], "d": m["d"], "f": m.get("f"), "mode": m["mode"], "ex": m["exit"]}


def _enumerate_one(ctx: Ctx, rule: dict, w0: int, w1: int) -> np.ndarray:
    return ctx.position(rule)[w0:w1]


# ================================================================= live use
def _jsonable(o):
    return json.loads(json.dumps(o, default=lambda x: float(x) if isinstance(x, (np.floating, np.integer)) else str(x)))


def playbook(res: dict) -> dict:
    out = {"generated_at": res["generated_at"], "source": res["source"], "assets": {}}
    for a, r in res["assets"].items():
        out["assets"][a] = {"rule": r["candidate"]["rule"], "label": r["candidate"]["label"], "kind": r.get("kind"),
                            "path": r.get("path"), "proven": bool(r.get("proven")), "beta_only": r.get("kind") == "beta",
                            "wf_sharpe": r["wf"]["sharpe"], "wf_t": r["wf"]["t"], "dsr": r["best"]["dsr"],
                            "signal": r["signal"]}
    if res.get("consensus"):
        out["consensus"] = {"rule": res["consensus"]["rule"], "label": res["consensus"]["label"],
                            "mean_sharpe": res["consensus"]["mean_sharpe"], "pos_assets": res["consensus"]["pos_assets"]}
    return _jsonable(out)


def _norm_rule(r: dict) -> dict:
    r = json.loads(json.dumps(r))

    def fix(d):
        if not d:
            return d
        if "ens" in d:
            d["ens"] = [fix(x) for x in d["ens"]]
        if d.get("op") == "agree":
            d["d"] = fix(d["d"])
        return d
    r["d"] = fix(r["d"])
    r["f"] = fix(r.get("f"))
    return r


def _rule_state(ctx: Ctx, rule: dict, cost: float) -> dict:
    rule = _norm_rule(rule)
    p = ctx.position(rule)
    arr, _ = _slice_ctx(ctx, 0, ctx.T)
    day_idx = np.zeros(ctx.T, dtype=int)
    out = simulate_batch(p[None, :], [rule["exit"]], np.array([ATR_ROW.get(rule.get("atr", "4h"), 1)]), arr, cost, day_idx, 1)
    st = out["state"]
    side = int(np.sign(st["side"][0]))   # a half position (after a partial target) keeps its side
    f = lambda v: float(v) if side and np.isfinite(v) else None
    return {"side": {1: "LONG", -1: "SHORT", 0: "FLAT"}[side], "entry": f(st["entry"][0]), "sl": f(st["sl"][0]),
            "tp": f(st["tp"][0]), "as_of": str(ctx.idx[-1])}


def load_live_system_history(root: str = ".") -> Optional[pd.DataFrame]:
    """Live system outputs (signal_history.csv, written every engine cycle),
    seeded with the replay's signal panel so z-scores have a past."""
    parts = []
    for p in (os.path.join(root, "validation_reports", "signal_panel.csv.gz"), os.path.join(root, "signal_history.csv")):
        if os.path.exists(p):
            try:
                d = pd.read_csv(p, low_memory=False)
                d["t"] = pd.to_datetime(d["t"], utc=True)
                parts.append(d)
            except Exception:
                pass
    if not parts:
        return None
    S = pd.concat(parts, ignore_index=True).sort_values("t").drop_duplicates(["asset", "t"], keep="last")
    cut = S["t"].max() - pd.Timedelta(days=60)
    return S[S["t"] >= cut]


def live_signals(pb: dict, data: Optional[Dict[str, dict]] = None, sys_hist: Optional[pd.DataFrame] = None,
                 now: Optional[datetime] = None, alt: Optional[pd.DataFrame] = None) -> dict:
    """Current position of every asset's candidate rule (and of the consensus
    rule), recomputed on fresh closed bars + the live system outputs."""
    now = now or datetime.now(timezone.utc)
    if data is None:
        try:
            data = load_yahoo(now, hourly_period="180d", daily_period="3y")
        except Exception as exc:
            print(f"[lab] canlı veri yok ({exc}); haftalık sinyal kullanılıyor", flush=True)
            data = {}
    if sys_hist is None:
        sys_hist = load_live_system_history()
    if alt is None:
        try:
            import alt_data
            alt = alt_data.load()
        except Exception:
            alt = None
    cons = (pb.get("consensus") or {}).get("rule")
    out = {}
    for a, p in (pb.get("assets") or {}).items():
        sig, fresh, c_side = dict(p.get("signal") or {}), False, None
        fr = data.get(a) or {}
        if fr.get("1h") is not None and len(fr["1h"]) > 200:
            try:
                sysp = sys_hist[sys_hist["asset"] == a] if sys_hist is not None else None
                altp = alt[alt["asset"] == a] if alt is not None else None
                ctx = Ctx(fr["1h"], fr.get("1d"), sysp, altp)
                sig = _rule_state(ctx, p["rule"], COST[a])
                fresh = True
                if cons:
                    c_side = _rule_state(ctx, cons, COST[a])["side"]
            except Exception as exc:
                print(f"[lab] {a}: canlı kural hesaplanamadı ({exc})", flush=True)
        out[a] = {"side": sig.get("side", "FLAT"), "sl": sig.get("sl"), "tp": sig.get("tp"), "entry": sig.get("entry"),
                  "as_of": sig.get("as_of"), "fresh": fresh, "strategy": p.get("label"), "kind": p.get("kind"),
                  "proven": bool(p.get("proven")), "beta_only": bool(p.get("beta_only")), "path": p.get("path"),
                  "wf_sharpe": p.get("wf_sharpe"), "dsr": p.get("dsr"),
                  "consensus_side": c_side, "consensus": (pb.get("consensus") or {}).get("label"),
                  "exit": (p.get("rule") or {}).get("exit")}
    return out


# ================================================================= report
def _pct(x, d=1):
    return "—" if x is None else f"%{x * 100:+.{d}f}"


def report_md(res: dict) -> str:
    c = res["costs"]
    L = ["# 🧪 Strateji Laboratuvarı v7 — Kaldıraçlı Vadeli (Perp) Sonuç Raporu", "",
         f"_Üretim: {res['generated_at'][:16]} UTC · fiyat: {res['source']} · sistem sinyalleri: {res.get('panel') or 'yok'} · "
         f"denenen konfigürasyon: **{res['n_configs']:,}**_", "",
         f"**Maliyetler:** işlem başına (giriş ve çıkışta ayrı ayrı) komisyon+kayma %{c['fee_slippage_per_side']['BTC'] * 100:.2f}; "
         f"fonlama: long pozisyon 8 saatte %{c['funding_long_per_8h'] * 100:.3f} öder, short pozisyona fonlama geliri yazılmaz (tutucu). "
         "Tüm getiriler 1x pozisyon büyüklüğünde ve maliyetler düşülmüş (net); kaldıraç tablosu ayrı.", ""]
    if res["source"] == "panel":
        L += ["> ⚠️ ÇEVRİMDIŞI ÖN İZLEME: fiyat yolu panelden yeniden kuruldu (High/Low yok, stoplar kapanışla kontrol edildi). "
              "Kesin sonuç GitHub Actions'taki çalışmadır.", ""]
    L += ["**v6:** her sinyal 5 tutma ufkunda (1 saat · 4 saat · 1 gün · 1 hafta · 1 ay), son değer ya da ufuk ortalaması, "
          "işaret / güçlü (∣z∣>0.5, ∣z∣>1), sistem yönünde ve TERS, long+short / sadece long / sadece short, 3-8 çıkış kuralıyla "
          "TEK TEK; sonra hazır kombinasyonlar ve veriden keşfedilen kombinasyonlar test edildi.", "",
          "**Kanıt** (biri yeterli; **C:** kombinasyon keşfinde hiç görülmemiş son dönemde t ≥ 2) — **A:** sistem sinyalli pencerede seçim prosedürünün walk-forward OOS t ≥ 2, 5 dilimin ≥ 3'ü "
          "pozitif, Deflated Sharpe ≥ 0.90, ≥ 30 işlem · **B:** 10 yıllık günlük veride aynı testler (7 dilimin ≥ 5'i). "
          "Kanıtlı kural ayrıca 'sürekli long perp'e karşı **alfa t ≥ 2** veriyorsa **✅ KANITLI ALFA** (bot işlem yapabilir); "
          "vermiyorsa **⚠️ β AĞIRLIKLI** (kazancı çoğunlukla piyasa yönünden; işlem sinyali sayılmaz).", "",
          "## 1) Varlık bazında sonuç", "",
          "| Varlık | Seçilen kural (pencerenin en iyisi) | Sharpe | 1. yarı / 2. yarı | Getiri | Maks. DD | İşlem | Kazanma | DSR | "
          "WF-OOS Sharpe (t) · + dilim | Alfa t | Uzun dönem 1g: en iyi kural · WF Sharpe (t) · + dilim · alfa t | Sürekli long Sharpe / getiri | Durum | Sinyal |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for a, r in res["assets"].items():
        b, w, bh, lg = r["best"], r["wf"], r["bh"], r.get("long")
        state = {"alpha": f"✅ KANITLI ALFA ({r['path']})", "beta": f"⚠️ β AĞIRLIKLI ({r['path']})"}.get(r.get("kind"), "❌ kanıt yok")
        if r.get("path") == "C":
            b = dict(b, label=r["candidate"]["label"])
        sig = {"LONG": "🟢 LONG", "SHORT": "🔴 SHORT", "FLAT": "⚪ YOK"}[r["signal"]["side"]]
        lgs = "—" if not lg else (f"{lg['label']} · {lg['wf_sharpe']:.2f} ({lg['wf_t']:+.1f}) · {lg['wf_pos_folds']}/{lg['wf_folds']} · "
                                  f"{lg['alpha_t']:+.1f} · {lg['years']} yıl")
        L.append(f"| {a} | {b['label']} | {b['sharpe']:.2f} | {b['h1']:.2f} / {b['h2']:.2f} | {_pct(b['ret'])} | {_pct(-b['maxdd'])} | "
                 f"{b['trades']} | %{b['win'] * 100:.0f} | {b['dsr']:.2f} | {w['sharpe']:.2f} ({w['t']:+.1f}) · {w['pos_folds']}/{w['n_folds']} | "
                 f"{r['wf_alpha_t']:+.1f} | {lgs} | {bh['sharpe']:.2f} / {_pct(bh['ret'])} | {state} | {sig} |")
    L += ["", "_'1. yarı / 2. yarı': aynı kuralın pencerenin iki yarısındaki Sharpe'ı — biri pozitif biri negatifse kural kararsızdır. "
          "WF-OOS: her dilimde YALNIZCA geçmişte en iyi olanı seçip bir sonraki dilimde ölçen prosedürün gerçek dışı-örneklem sonucu "
          "(on binlerce aday arasından seçimin bedeli dahil)._", ""]
    # v6: horizon effect
    if res.get("horizon_summary"):
        L += ["## 2) Tutma ufku etkisi — sistem sinyalleri tek tek (sistem yönünde, işaret, ufuk boyunca ortalama, long+short)", "",
              "| Ufuk | Ortalama Sharpe | Medyan Sharpe | Pozitif oran |", "|---|---|---|---|"]
        for h in res["horizon_summary"]:
            L.append(f"| {CAD_TR.get(h['cad'], h['cad'])} | {h['mean']:.2f} | {h['median']:.2f} | %{h['pos_share'] * 100:.0f} |")
        hz = res.get("horizon") or {}
        cads = hz.get("cads", [])
        L += ["", "**Sinyal × ufuk matrisi** (6 varlık ortalaması Sharpe · parantezde pozitif varlık sayısı)", "",
              "| Sinyal | " + " | ".join(CAD_TR.get(c, str(c)) for c in cads) + " |", "|---" * (len(cads) + 1) + "|"]
        for r in hz.get("rows", []):
            cells = []
            for c in cads:
                v, p = r.get(str(c)), r.get(f"pos{c}")
                cells.append("—" if v is None else f"{v:.2f} ({p})")
            L.append(f"| {r['name']} | " + " | ".join(cells) + " |")
        L += ["", "_Makro sinyallerin değeri uzun ufukta (hafta/ay) görünmeli; kısa ufukta sık yön değişimi maliyetle eriyor. "
              "Ay ufku 700 günde ~23 karar demek: istatistiksel gücü düşüktür._", ""]
    # v6: combination discovery
    if any(r.get("combo") for r in res["assets"].values()):
        L += ["## 3) Kombinasyon keşfi (keşif → doğrulama → hiç görülmemiş dönem)", "",
              "_Keşif döneminde her sinyal tek tek sıralandı; en iyi 40'ın tüm ikili kombinasyonları (ikisi aynı yönü "
              "gösterdiğinde işlem) ve 2-7 sinyallik açgözlü çoğunluk oyları kuruldu. Seçim doğrulama döneminde yapıldı; "
              "son dönem hiçbir seçimde kullanılmadı. Kanıt: son dönemde t ≥ 2 ve sürekli long'a karşı alfa t ≥ 2._", ""]
        for a, r in res["assets"].items():
            c = r.get("combo")
            if not c:
                continue
            sp = c["split"]
            L += [f"**{a}** · keşif {sp[0]}→{sp[1]} · doğrulama →{sp[2]} · son dönem →{sp[3]} · {c['n_candidates']:,} aday "
                  f"({c['n_pairs']:,} ikili, {c['n_greedy']} oylama) · {'✅ SON DÖNEMDE GEÇTİ' if c['passed'] else '❌ son dönemde geçmedi'}", "",
                  "| # | Kombinasyon | Tür | Keşif Sharpe | Doğrulama | **Son dönem** | Son dönem getiri | t | Alfa t | İşlem |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
            for k, t in enumerate(c["top"][:10], 1):
                L.append(f"| {k} | {t['label']} | {t['cat']} | {t['d1']:.2f} | {t['d2']:.2f} | **{t['d3']:.2f}** | {_pct(t['ret3'])} | "
                         f"{t['t3']:+.1f} | {t['alpha_t3']:+.1f} | {t['trades']} |")
            L.append("")
    # v7: system direction as filter + technical trigger
    tg = res.get("trigger")
    if tg:
        L += ["## 3b) Sistem yönü FİLTRE + teknik TETİK + ATR çıkışı", "",
              "_Kural: teknik tetik (RSI(2) aşırılığı, Bollinger dönüşü, Donchian kırılımı, EMA20 kesişimi, MACD kesişimi, "
              "Keltner kırılımı) oluşunca, YALNIZCA sistemin gösterdiği yönde işleme girilir; çıkış ATR stop/hedef, başa-baş, "
              "kısmi kâr, iz süren stop veya sinyal. 'Kazanç' = aynı tetik, aynı çıkış, aynı yön modu ile filtresiz hâline göre "
              "Sharpe farkı. Bir filtreye ancak pencerenin İKİ yarısında da kazanç veriyorsa güvenilir._", "",
              f"**Genel:** {tg['n_pairs']:,} (tetik × filtre × çıkış × yön) eşleşmesi · filtresiz tetik ort. Sharpe **{tg['base_mean']:.2f}** "
              f"(pozitif %{tg['base_pos'] * 100:.0f}) → sistem filtreli ort. **{tg['filt_mean']:.2f}** (pozitif %{tg['filt_pos'] * 100:.0f}) · "
              f"ortalama kazanç **{tg['lift_mean']:+.2f}** · kazanç pozitif %{tg['lift_pos'] * 100:.0f} · iki yarıda da pozitif "
              f"**%{tg['lift_both'] * 100:.0f}**", "",
              "**Filtre olarak en faydalı sistem yönleri** (tüm tetikler ve varlıklar ortalaması)", "",
              "| Filtre (sistem yönü) | Ufuk | Ort. kazanç | 1. yarı / 2. yarı kazanç | İki yarıda da + | Filtreli ort. Sharpe | Eşleşme | Varlık |",
              "|---|---|---|---|---|---|---|---|"]
        for r in tg["biases"][:20]:
            L.append(f"| {r['name']} | {r['cad']} | {r['lift']:+.2f} | {r['lift1']:+.2f} / {r['lift2']:+.2f} | %{r['both'] * 100:.0f} | "
                     f"{r['filt']:.2f} | {r['n']} | {r['assets']} |")
        if len(tg["biases"]) > 20:
            L += ["", "_En zayıf 5 filtre:_ " + " · ".join(f"{r['name']} ({r['cad']}) {r['lift']:+.2f}" for r in tg["biases"][-5:])]
        L += ["", "**Tetik bazında** (filtresiz → filtreli)", "", "| Tetik | Filtresiz Sharpe | Filtreli ort. | Kazanç | İki yarıda + |",
              "|---|---|---|---|---|"]
        for r in tg["triggers"]:
            L.append(f"| {r['name']} | {r['base']:.2f} | {r['filt']:.2f} | {r['lift']:+.2f} | %{r['both'] * 100:.0f} |")
        L += ["", "**İki yarıda da en sağlam 20 filtreli tetik kuralı** (sıralama: min(1. yarı, 2. yarı) — yine de seçim yanlılığı içerir)", "",
              "| Varlık | Kural | Sharpe | 1. yarı / 2. yarı | Filtresiz | Kazanç | İşlem |", "|---|---|---|---|---|---|---|"]
        for r in tg["top"]:
            L.append(f"| {r['asset']} | {r['label']} | {r['sharpe']:.2f} | {r['h1']:.2f} / {r['h2']:.2f} | {r['base']:.2f} | "
                     f"{r['lift']:+.2f} | {r['trades']} |")
        L.append("")
    if res.get("alt_signals"):
        L += ["## 3c) Yeni bilgi kaynağı — türev piyasası konumlanması (Binance) ve CFTC COT", "",
              f"_Varlıklar: {', '.join(res.get('alt_assets', []))}. Veri, canlı botun da bilebileceği an itibarıyla kullanıldı "
              "(Binance günlük dosyası gün başlangıcından 30 saat sonra, COT salı pozisyonu cumartesi 00:00 UTC). "
              "'(z)' = sinyalin kendi 90 gözlemlik ortalamasına göre konumu. Sinyal yönünde long+short, sinyalle çıkış._", "",
              "| Sinyal | Ufuk | Kural | Ort. Sharpe | 1. yarı / 2. yarı | Pozitif varlık | İki yarıda + varlık |", "|---|---|---|---|---|---|---|"]
        for r in res["alt_signals"]:
            L.append(f"| {r['name']} | {CAD_TR.get(r['cad'], r['cad'])} | {r['op']} | {r['mean']:.2f} | {r['h1']:.2f} / {r['h2']:.2f} | "
                     f"{r['pos']}/{r['n']} | {r['both']}/{r['n']} |")
        L += ["", "_Negatif ortalama + iki yarıda tutarlı = sinyal TERS yönde çalışıyor olabilir (kalabalık pozisyonun tersine "
              "işlem); bu TERS versiyonlar ayrıca test edilip tüm konfigürasyon dosyasında yer alır._", ""]
    # leverage
    L += ["## 4) Kaldıraç ve likidasyon (seçilen kural, 730 gün, saatlik High/Low ile)", "",
          "| Varlık | 1x yıllık / DD | 2x | 3x | 5x | 10x | Vol hedefli (%40, maks 5x) | Likidasyon (1/2/3/5/10x) |",
          "|---|---|---|---|---|---|---|---|"]
    for a, r in res["assets"].items():
        lv = r.get("leverage")
        if not lv:
            L.append(f"| {a} | — | — | — | — | — | — | — |")
            continue
        cell = lambda x: f"{_pct(x['cagr'], 0)} / {_pct(-x['maxdd'], 0)}"
        m = {str(x["lev"]): x for x in lv}
        L.append(f"| {a} · seçilen kural (iyimser) | {cell(m['1'])} | {cell(m['2'])} | {cell(m['3'])} | {cell(m['5'])} | {cell(m['10'])} | "
                 f"{cell(m['vol'])} | {'/'.join(str(m[k]['liquidations']) for k in ('1', '2', '3', '5', '10'))} |")
        wl = {str(x["lev"]): x for x in (r.get("leverage_wf") or [])}
        if wl:
            L.append(f"| {a} · walk-forward OOS (gerçekçi) | {cell(wl['1'])} | {cell(wl['2'])} | {cell(wl['3'])} | {cell(wl['5'])} | "
                     f"{cell(wl['10'])} | — | {'/'.join(str(wl[k]['liquidations']) for k in ('1', '2', '3', '5', '10'))} |")
    L += ["", "_'Seçilen kural' satırı o kuralın geçmişteki en iyi hâlidir (seçim yanlılığı yüzünden iyimser). "
          "'Walk-forward OOS' satırı, her dönemde o güne kadar en iyi olanı seçip uygulasaydınız ne olacağını gösterir "
          "(günlük kapanışla; gün içi likidasyonları kaçırabilir). Kaldıraç Sharpe'ı değiştirmez; getiriyi de düşüşü de büyütür ve likidasyonla sermayeyi sıfırlayabilir. "
          "Kanıtsız bir kurala kaldıraç eklemek beklenen kaybı büyütür._", ""]
    # categories
    L += ["## 5) Kombinasyon türlerine göre (6 varlık ortalaması)", "",
          "| Tür | Konfigürasyon | En iyi Sharpe | Medyan Sharpe | WF-OOS Sharpe | WF pozitif varlık |", "|---|---|---|---|---|---|"]
    for g in res["categories"]:
        L.append(f"| {g['cat']} | {int(g['n']):,} | {g['best']:.2f} | {g['median']:.2f} | {g['wf']:.2f} | {g['wf_pos']}/{g['assets']} |")
    # system signals
    ss = res.get("system_signals") or {}
    if ss.get("rows"):
        cols = ss["columns"]
        L += ["", "## 6) Sistemin kendi sinyalleri tek başına (long+short, sinyalle çıkış, sistemin yönünde)", "",
              "| Sinyal | " + " | ".join(cols) + " | Ort. | 1. yarı / 2. yarı | Pozitif |", "|---" * (len(cols) + 4) + "|"]
        for r in ss["rows"]:
            L.append(f"| {r['name']} | " + " | ".join("—" if r.get(c) is None else f"{r[c]:.2f}" for c in cols) +
                     f" | {r['mean']:.2f} | {r['h1']:.2f} / {r['h2']:.2f} | {int(r['pos'])}/{int(r['n'])} |")
        L += ["", "_Negatif ortalama = sinyal TERS yönde kullanılırsa çalışıyor olabilir (TERS kurallar da ayrıca test edildi)._"]
    # robust
    if res.get("robust"):
        L += ["", "## 7) Tüm varlıklarda aynı ayarla en tutarlı kurallar", "", "| Kural | Ort. Sharpe | Pozitif varlık |", "|---|---|---|"]
        for r in res["robust"]:
            L.append(f"| {r['label']} | {r['mean_sharpe']:.2f} | {r['pos_assets']}/{r['n_assets']} |")
    # per asset top
    L += ["", "## 8) Varlık bazında ilk 15 (tam pencere — seçim yanlılığı İÇERİR, tek başına kanıt değildir)", ""]
    for a, r in res["assets"].items():
        L += [f"**{a} — {NAMES[a]}** · {r['window'][0]} → {r['window'][1]} · {r['n_configs']:,} konfigürasyon "
              f"(etkin bağımsız: {r['n_effective']:.0f})", "",
              "| # | Kural | Tür | Sharpe | 1./2. yarı | Getiri | Maks. DD | İşlem | Kazanma | Pozisyonda |", "|---|---|---|---|---|---|---|---|---|---|"]
        for k, t in enumerate(r["top"], 1):
            L.append(f"| {k} | {t['label']} | {t['cat']} | {t['sharpe']:.2f} | {t['h1']:.2f} / {t['h2']:.2f} | {_pct(t['ret'])} | "
                     f"{_pct(-t['maxdd'])} | {t['trades']} | %{t['win'] * 100:.0f} | %{t['expo'] * 100:.0f} |")
        L.append(f"\n_Walk-forward dilim getirileri: {', '.join(_pct(x) for x in r['wf']['fold_ret'])} · "
                 f"seçilenler: {'; '.join(str(x) for x in r['wf_picks'] if x)[:600]}_\n")
    L += ["_Tüm konfigürasyonların tek tek sonuçları: **lab_all_configs.csv.gz**._"]
    return "\n".join(L) + "\n"


ALL_COLS = ["asset", "tur", "kural", "yon_modu", "cikis", "sharpe", "sharpe_1yari", "sharpe_2yari", "getiri", "maks_dd",
            "islem", "kazanma", "pozisyonda"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["yahoo", "panel"], default="yahoo")
    ap.add_argument("--panel", default=None, help="signal_panel.csv.gz (veya factor_panel.csv.gz)")
    ap.add_argument("--out", default=".")
    ap.add_argument("--assets", default=None, help="virgülle (test için)")
    ap.add_argument("--alt", default="auto", help="alt_panel.csv.gz yolu ('auto' = varsa yükle, 'none' = kullanma)")
    args = ap.parse_args()
    panel = load_signal_panel(args.panel)
    alt = None
    if args.alt != "none":
        import alt_data
        alt = alt_data.load((args.alt,) if args.alt != "auto" else alt_data.DEFAULT_PATHS)
        print(f"[lab] alternatif veri: {'yok' if alt is None else f'{len(alt)} satır, ' + str(sorted(alt['asset'].unique()))}", flush=True)
    if args.source == "yahoo":
        data = load_yahoo()
    else:
        data = panel_price_path(args.panel or "validation_reports/factor_panel.csv.gz")
    if args.assets:
        data = {k: v for k, v in data.items() if k in args.assets.split(",")}
    rows: list = []
    res = research(data, panel, source=args.source, all_rows=rows, alt=alt)
    os.makedirs(args.out, exist_ok=True)
    json.dump(_jsonable(res), open(os.path.join(args.out, "lab_results.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(playbook(res), open(os.path.join(args.out, "lab_playbook.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(os.path.join(args.out, "lab_report.md"), "w", encoding="utf-8").write(report_md(res))
    pd.DataFrame(rows, columns=ALL_COLS).sort_values(["asset", "sharpe"], ascending=[True, False]).to_csv(
        os.path.join(args.out, "lab_all_configs.csv.gz"), index=False, compression="gzip")
    print(f"[lab] {res['n_configs']:,} konfigürasyon · kanıtlı alfa: "
          f"{[a for a, r in res['assets'].items() if r['kind'] == 'alpha'] or 'yok'} · β ağırlıklı: "
          f"{[a for a, r in res['assets'].items() if r['kind'] == 'beta'] or 'yok'}", flush=True)


if __name__ == "__main__":
    main()
