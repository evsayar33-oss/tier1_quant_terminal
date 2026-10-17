"""
Piyasa Yapısı (v15.1) — seans saati, opsiyon takvimi, likidite seviyeleri,
likidite avı, sistematik fon akışları
==========================================================================
Bu modül YÖN TAHMİNİ ÜRETMEZ. Fiyatın NEREDE durabileceğini (seviyeler),
NE ZAMAN hareketin karakter değiştirdiğini (seans, OPEX) ve KİMİN mekanik
olarak alıp sattığını (CTA, volatilite hedefli fonlar) ölçer.

Piyasa yapıcı mantığı:
* Stop emirleri belirgin seviyelerin hemen ötesinde birikir (önceki gün
  tepe/dip, gece aralığı, salınım noktaları, yuvarlak sayılar).
* Büyük katılımcı likidite ister. Fiyat bu seviyeyi kısa süre aşar, stopları
  tetikler, sonra geri döner ("likidite avı" / sweep). Mumda bu, seviyenin
  ötesine uzanan bir fitil ve seviyenin içinde bir kapanıştır.
* 0DTE gaması vade kapanışına doğru sıfıra iner (charm). OPEX'ten sonra
  dealer gaması "serbest kalır"; volatilite genelde artar.
* CTA'lar trendi takip eder. Tetik seviyesi geçilince mekanik alım/satım
  yaparlar. Volatilite hedefli fonlar gerçekleşen volatilite düşünce alır,
  yükselince satar.

Buradaki faktörler config'te "role": "state" olarak tanımlıdır: yön skoruna
oy vermez; replay paneline yazılır, 3 dönem kararlılık tanısı ve öğrenilmiş
model onların gerçekten işe yarayıp yaramadığını kanıtla belirler.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

try:
    from zoneinfo import ZoneInfo
    _NY = ZoneInfo("America/New_York")
except Exception:  # pragma: no cover
    _NY = None

from system_clock import now_utc

CRYPTO = {"BTC", "ETH"}
FIVE_MIN_SYMBOLS = {"SPX": "ES=F", "NQ": "NQ=F", "XAU": "GC=F", "XAG": "SI=F", "BTC": "BTC-USD", "ETH": "ETH-USD"}


def _ts(x: Any) -> pd.Timestamp:
    t = pd.Timestamp(x)
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def _ny(t: pd.Timestamp) -> pd.Timestamp:
    t = _ts(t)
    return t.tz_convert(_NY) if _NY is not None else t - pd.Timedelta(hours=4)


def _ohlc(df: Any) -> Optional[pd.DataFrame]:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return None
    d = df.copy()
    if isinstance(d.columns, pd.MultiIndex):
        d.columns = [c[0] if isinstance(c, tuple) else c for c in d.columns]
    if any(c not in d.columns for c in ("High", "Low", "Close")):
        return None
    for c in ("Open", "High", "Low", "Close", "Volume"):
        if c in d.columns:
            d[c] = pd.to_numeric(d[c], errors="coerce")
    d.index = pd.to_datetime(d.index, utc=True)
    d = d.dropna(subset=["High", "Low", "Close"]).sort_index()
    return d[~d.index.duplicated(keep="last")] if not d.empty else None


def atr(df: pd.DataFrame, n: int = 14) -> Optional[float]:
    d = _ohlc(df)
    if d is None or len(d) < n + 1:
        return None
    tr = pd.concat([d["High"] - d["Low"], (d["High"] - d["Close"].shift()).abs(),
                    (d["Low"] - d["Close"].shift()).abs()], axis=1).max(axis=1)
    v = float(tr.tail(n).mean())
    return v if np.isfinite(v) and v > 0 else None


# ---------------------------------------------------------------------------
# 1) Seans saati
# ---------------------------------------------------------------------------
def trading_day(t: Any, asset: str) -> date:
    """Vadeli: CME günü New York 18:00'de başlar. Kripto: UTC günü."""
    t = _ts(t)
    if asset in CRYPTO:
        return t.date()
    return (_ny(t) + pd.Timedelta(hours=6)).date()


def session_phase(now: Any = None, asset: str = "NQ") -> Dict[str, str]:
    now = _ts(now or now_utc())
    ny = _ny(now)
    h = ny.hour + ny.minute / 60.0
    wd = ny.weekday()
    if asset in CRYPTO:
        if 9.5 <= h < 16 and wd < 5:
            return {"phase": "ABD nakit seansı ile çakışma", "note": "Kripto hacminin en yoğun olduğu saatler; ABD endeksleriyle korelasyon yüksek."}
        if wd >= 5:
            return {"phase": "Hafta sonu", "note": "Kurumsal katılım düşük; ince likidite fitilleri (sweep) daha sık."}
        return {"phase": "ABD dışı saatler", "note": "Likidite daha ince."}
    closed = (wd == 5) or (wd == 6 and h < 18) or (wd == 4 and h >= 17) or (17 <= h < 18)
    if closed:
        return {"phase": "Kapalı", "note": "Vadeli piyasa kapalı (günlük bakım veya hafta sonu)."}
    if h >= 18 or h < 3:
        return {"phase": "Asya seansı", "note": "Düşük hacim; gece aralığı oluşur. Gece tepe/dibi ABD açılışında hedef seviyedir."}
    if h < 9.5:
        return {"phase": "Avrupa seansı", "note": "Avrupa likiditesi; 08:30 ET ABD verileri gece aralığını kırabilir."}
    if h < 10.5:
        return {"phase": "ABD açılış (ilk saat)", "note": "Günün en yüksek hacmi; gece tepe/dibi sık sık süpürülür (likidite avı)."}
    if h < 14.0:
        return {"phase": "ABD gün ortası", "note": "Hacim düşer; +Γ günlerinde fiyat duvarlar arasında sıkışır."}
    if h < 16.0:
        return {"phase": "ABD kapanış saatleri", "note": "0DTE gaması hızla sıfıra iner (charm). Pin seviyesi çeker, sonra serbest kalır; kapanış imbalance'ı."}
    return {"phase": "Kapanış sonrası", "note": "Nakit seans kapandı; vadeli ince likiditeyle devam eder."}


# ---------------------------------------------------------------------------
# 2) Opsiyon takvimi (OPEX, VIX vadesi, çeyrek sonu)
# ---------------------------------------------------------------------------
def third_friday(y: int, m: int) -> date:
    d = date(y, m, 15)
    return d + timedelta(days=(4 - d.weekday()) % 7)


def vix_expiry(y: int, m: int) -> date:
    """VIX vadesi: bir SONRAKİ ayın 3. Cuması'ndan 30 gün önceki Çarşamba."""
    ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
    return third_friday(ny, nm) - timedelta(days=30)


def _next_monthly(today: date, fn) -> date:
    for k in range(0, 3):
        y, m = today.year + (today.month - 1 + k) // 12, (today.month - 1 + k) % 12 + 1
        d = fn(y, m)
        if d >= today:
            return d
    return fn(today.year + 1, today.month)


def _last_business_day(y: int, m: int) -> date:
    d = (date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1))
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def options_calendar(now: Any = None) -> Dict[str, Any]:
    """Not: ABD resmi tatilleri hesaba katılmaz (OPEX tatile denk gelirse bir gün önce olur)."""
    now = _ts(now or now_utc())
    today = _ny(now).date()
    opex = _next_monthly(today, third_friday)
    prev_opex = third_friday(today.year, today.month)
    if prev_opex >= today:
        py, pm = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
        prev_opex = third_friday(py, pm)
    vx = _next_monthly(today, vix_expiry)
    me = _last_business_day(today.year, today.month)
    days_to_opex = (opex - today).days
    days_after_opex = (today - prev_opex).days
    quarterly = opex.month in (3, 6, 9, 12)
    notes = []
    if days_to_opex <= 4:
        notes.append(f"OPEX haftası ({opex:%d.%m}{', üçlü vade (triple witching)' if quarterly else ''}): "
                     "büyük strike'lar fiyatı çeker (pin), charm akışı güçlü.")
    if 0 < days_after_opex <= 2:
        notes.append("OPEX sonrası: dealer gaması serbest kaldı; volatilite artabilir, sıkışma çözülebilir.")
    if (vx - today).days <= 1:
        notes.append(f"VIX vadesi {vx:%d.%m}: VIX vadeli/opsiyon hedge akışı, sabah SPX açılış oynaklığı.")
    if 0 <= (me - today).days <= 2:
        q = me.month in (3, 6, 9, 12)
        notes.append(f"{'Çeyrek' if q else 'Ay'} sonu ({me:%d.%m}): portföy yeniden dengeleme akışı"
                     f"{' ve JPM collar (JHEQX) yenilemesi' if q else ''}.")
    return {"next_opex": opex.isoformat(), "days_to_opex": days_to_opex, "quarterly_opex": quarterly,
            "days_after_opex": days_after_opex, "next_vix_expiry": vx.isoformat(),
            "month_end": me.isoformat(), "opex_week": days_to_opex <= 4, "notes": notes}


# ---------------------------------------------------------------------------
# 3) Likidite seviyeleri + likidite avı
# ---------------------------------------------------------------------------
def nice_step(price: float) -> float:
    raw = abs(price) * 0.004
    if raw <= 0:
        return 1.0
    p = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if m * p >= raw:
            return m * p
    return 10 * p


def _swings(d: pd.DataFrame, k: int = 2, lookback: int = 48) -> Dict[str, List[float]]:
    x = d.tail(lookback)
    hi, lo = x["High"].to_numpy(), x["Low"].to_numpy()
    sh, sl = [], []
    for i in range(k, len(x) - k):
        if hi[i] == hi[i - k:i + k + 1].max():
            sh.append(float(hi[i]))
        if lo[i] == lo[i - k:i + k + 1].min():
            sl.append(float(lo[i]))
    return {"high": sh[-3:], "low": sl[-3:]}


def liquidity_levels(df_1h: Any, asset: str, df_daily: Any = None, now: Any = None) -> Optional[Dict[str, Any]]:
    d = _ohlc(df_1h)
    if d is None or len(d) < 10:
        return None
    now = _ts(now or d.index[-1])
    price = float(d["Close"].iloc[-1])
    days = pd.Series([trading_day(t, asset) for t in d.index], index=d.index)
    cur = trading_day(now, asset)
    out: Dict[str, Any] = {"price": price, "levels": []}

    def add(p, kind, label):
        if p is not None and np.isfinite(p):
            out["levels"].append({"price": round(float(p), 4), "kind": kind, "label": label})

    prev_days = sorted(x for x in days.unique() if x < cur)
    if prev_days:
        pdx = d[days == prev_days[-1]]
        if len(pdx) >= 4:
            add(float(pdx["High"].max()), "PDH", "Önceki gün tepesi")
            add(float(pdx["Low"].min()), "PDL", "Önceki gün dibi")
    today = d[days == cur]
    if asset not in CRYPTO and not today.empty:
        ny_h = pd.Series([_ny(t).hour + _ny(t).minute / 60.0 for t in today.index], index=today.index)
        on = today[(ny_h >= 18) | (ny_h < 9.5)]
        if len(on) >= 3:
            forming = _ny(now).hour + _ny(now).minute / 60.0 < 9.5 or _ny(now).hour >= 18
            sfx = " (oluşuyor)" if forming else ""
            add(float(on["High"].max()), "ONH", "Gece (Globex) tepesi" + sfx)
            add(float(on["Low"].min()), "ONL", "Gece (Globex) dibi" + sfx)
    if "Volume" in today.columns and not today.empty and float(today["Volume"].fillna(0).sum()) > 0:
        tp = (today["High"] + today["Low"] + today["Close"]) / 3.0
        add(float((tp * today["Volume"].fillna(0)).sum() / today["Volume"].fillna(0).sum()), "VWAP", "Seans VWAP")
    dd = _ohlc(df_daily)
    if dd is not None and len(dd) >= 10:
        wk = dd.index.tz_localize(None).to_period("W")
        cur_wk = now.tz_localize(None).to_period("W")
        prev = dd[wk < cur_wk]
        if not prev.empty:
            pw = prev.index.tz_localize(None).to_period("W")
            lw = prev[pw == pw[-1]]
            add(float(lw["High"].max()), "PWH", "Önceki hafta tepesi")
            add(float(lw["Low"].min()), "PWL", "Önceki hafta dibi")
    sw = _swings(d)
    for p in sw["high"]:
        add(p, "SWH", "Salınım tepesi")
    for p in sw["low"]:
        add(p, "SWL", "Salınım dibi")
    step = nice_step(price)
    base = math.floor(price / step) * step
    add(base, "RND", "Yuvarlak sayı")
    add(base + step, "RND", "Yuvarlak sayı")
    out["round_step"] = step
    out["levels"].sort(key=lambda x: x["price"])
    return out


def detect_sweep(df: Any, levels: Optional[Dict[str, Any]], lookback: int = 3,
                 kinds=("PDH", "PDL", "ONH", "ONL", "PWH", "PWL", "SWH", "SWL")) -> Optional[Dict[str, Any]]:
    """Son `lookback` barda bir seviyenin ötesine fitil atıp seviyenin içinde
    kapanış var mı? Aşağı fitil + geri kapanış = altındaki stoplar alındı
    (yukarı yönlü sweep, +1). Yukarı fitil + geri kapanış = üstteki stoplar
    alındı (aşağı yönlü sweep, −1). En yeni olay döner."""
    d = _ohlc(df)
    if d is None or not levels or len(d) < 1:
        return None
    lv = [x for x in levels.get("levels", []) if x["kind"] in kinds]
    lows = {"PDL", "ONL", "PWL", "SWL"}
    best = None
    tail = d.tail(lookback)
    for age, (t, bar) in enumerate(reversed(list(tail.iterrows()))):
        o = float(bar["Open"]) if "Open" in bar and np.isfinite(bar["Open"]) else float(bar["Close"])
        for x in lv:
            L = x["price"]
            # Destek (dip) seviyesi: üstten açılış, altına fitil, üstünde kapanış.
            if x["kind"] in lows and o > L and bar["Low"] < L < bar["Close"] \
                    and (bar["Close"] - L) > 0.1 * (bar["High"] - bar["Low"]):
                ev = {"direction": +1, "level": L, "kind": x["kind"], "label": x["label"], "bars_ago": age,
                      "time": t.isoformat()}
            # Direnç (tepe) seviyesi: alttan açılış, üstüne fitil, altında kapanış.
            elif x["kind"] not in lows and o < L and bar["High"] > L > bar["Close"] \
                    and (L - bar["Close"]) > 0.1 * (bar["High"] - bar["Low"]):
                ev = {"direction": -1, "level": L, "kind": x["kind"], "label": x["label"], "bars_ago": age,
                      "time": t.isoformat()}
            else:
                continue
            if best is None or age < best["bars_ago"]:
                best = ev
        if best is not None:
            break
    if best:
        best["note"] = (f"{best['label']} ({best['level']:.2f}) {'altı' if best['direction'] > 0 else 'üstü'} "
                        f"süpürüldü, fiyat geri döndü → {'alttaki' if best['direction'] > 0 else 'üstteki'} stoplar alındı.")
    return best


def sweep_factor(df_1h: Any, asset: str, df_daily: Any = None) -> Optional[float]:
    lv = liquidity_levels(df_1h, asset, df_daily)
    if lv is None:
        return None
    ev = detect_sweep(df_1h, lv)
    if ev is None:
        return 0.0
    return float(ev["direction"] * (1.0 - ev["bars_ago"] / 3.0) * 1.5)


# ---------------------------------------------------------------------------
# 4) Sistematik akışlar: CTA trend fonları + volatilite hedefli fonlar
# ---------------------------------------------------------------------------
CTA_LOOKBACKS = (20, 60, 120, 250)


def _daily_close(df_daily: Any) -> Optional[pd.Series]:
    d = _ohlc(df_daily)
    return None if d is None else d["Close"]


def cta_model(df_daily: Any) -> Optional[Dict[str, Any]]:
    """Genel bir trend takipçisi (CTA) taklidi. Her ufukta sinyal =
    clip(log getiri / (günlük vol·√k), ±1); pozisyon = ortalama.
    Tetik seviyesi: yarın o ufkun getirisini sıfırlayan fiyat (k−1 gün önceki kapanış)."""
    c = _daily_close(df_daily)
    if c is None or len(c) < 25:
        return None
    r = np.log(c).diff().dropna()
    vol = float(r.tail(60).std())
    if not np.isfinite(vol) or vol <= 0:
        return None
    P = float(c.iloc[-1])
    sig, trig = {}, []
    for k in CTA_LOOKBACKS:
        if len(c) <= k:
            continue
        sig[k] = float(np.clip(math.log(P / float(c.iloc[-1 - k])) / (vol * math.sqrt(k)), -1, 1))
        lvl = float(c.iloc[-k])               # tomorrow's reference price for lookback k
        trig.append({"lookback": k, "level": round(lvl, 4), "side": "üstünde" if P > lvl else "altında"})
    if not sig:
        return None
    pos = float(np.mean(list(sig.values())))
    # Fiyat yarın sabit kalırsa pozisyon nasıl değişir? (pencere kayması = mekanik akış)
    nxt = []
    for k in sig:
        ref = float(c.iloc[-k])
        nxt.append(float(np.clip(math.log(P / ref) / (vol * math.sqrt(k)), -1, 1)))
    roll = float(np.mean(nxt)) - pos
    below = [t for t in trig if t["level"] < P]
    above = [t for t in trig if t["level"] > P]
    return {"position": round(pos, 3), "signals": {str(k): round(v, 3) for k, v in sig.items()},
            "flow_if_flat": round(roll, 3),
            "nearest_trigger_below": max(below, key=lambda t: t["level"]) if below else None,
            "nearest_trigger_above": min(above, key=lambda t: t["level"]) if above else None}


def vol_control_model(df_daily: Any, target: float = 0.10, lam: float = 0.94, days_back: int = 5) -> Optional[Dict[str, Any]]:
    """Volatilite hedefli fonlar: kaldıraç = hedef vol / gerçekleşen vol (EWMA).
    Kaldıraç artıyorsa fonlar mekanik ALIM yapar."""
    c = _daily_close(df_daily)
    if c is None or len(c) < 40:
        return None
    r = np.log(c).diff().dropna()
    var = r.pow(2).ewm(alpha=1 - lam, adjust=False).mean()
    vol = np.sqrt(var * 252)
    lev = (target / vol).clip(upper=2.0)
    now, before = float(lev.iloc[-1]), float(lev.iloc[-1 - days_back])
    return {"realized_vol": round(float(vol.iloc[-1]), 4), "leverage": round(now, 3),
            "leverage_change_5d": round(now - before, 3),
            "flow": "mekanik ALIM" if now - before > 0.02 else "mekanik SATIŞ" if now - before < -0.02 else "nötr"}


def cta_factor(df_daily: Any) -> Optional[float]:
    m = cta_model(df_daily)
    return None if m is None else float(np.clip(m["position"] * 1.8, -1.8, 1.8))


def vol_control_factor(df_daily: Any) -> Optional[float]:
    m = vol_control_model(df_daily)
    return None if m is None else float(np.tanh(m["leverage_change_5d"] * 4.0) * 1.8)


# ---------------------------------------------------------------------------
# 5) 5 dakikalık veri (videodaki "dakikalar içinde kırılım" saatlik barda görünmez)
# ---------------------------------------------------------------------------
def fetch_5m(symbol: str, period: str = "2d") -> Optional[pd.DataFrame]:
    try:
        import yfinance as yf
        df = yf.download(symbol, period=period, interval="5m", progress=False, auto_adjust=False, threads=False)
        d = _ohlc(df)
        return d
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Toplu çıktı (arka plan döngüsü)
# ---------------------------------------------------------------------------
def build_context(asset: str, df_1h: Any, df_daily: Any, df_5m: Any = None, now: Any = None) -> Dict[str, Any]:
    now = _ts(now or now_utc())
    lv = liquidity_levels(df_1h, asset, df_daily, now=now)
    sweep = None
    if lv is not None:
        sweep = detect_sweep(df_5m, lv, lookback=12) if _ohlc(df_5m) is not None else None
        sweep = sweep or detect_sweep(df_1h, lv)
    ctx = {"session": session_phase(now, asset), "levels": lv, "sweep": sweep,
           "cta": cta_model(df_daily), "atr_1h": atr(df_1h), "atr_1d": atr(df_daily),
           "has_5m": _ohlc(df_5m) is not None}
    if asset in ("SPX", "NQ"):
        ctx["vol_control"] = vol_control_model(df_daily)
    return ctx
