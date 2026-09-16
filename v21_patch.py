"""
V2.1 — Zero Synthetic Data + Live Multi-Horizon Direction + Strict Execution Gate

Bu dosya mevcut data_engine.py / quant_processor.py / gatekeeper.py mimarisini
monkey-patch eder. Mobil kullanım için tek parça replacement olarak tasarlanmıştır.

Kurallar:
- Sentetik OHLCV yok.
- Kritik futures için ETF/proxy fallback yok.
- Sadece gerçek veri.
- Cache sınırlı; cache kullanılıyorsa execution kapalı.
- Model yönü ile execution gate ayrıdır.
- 1H / 2H / 4H ATR-normalized impulse + persistence + ADX/DI kullanılır.
- Güçlü 1H hareketi + yatay 4H => otomatik YATAY değildir.
- Gerçek RVOL: current bar baseline dışındadır.
- Volume yoksa sahte RVOL üretilmez.
- Veri yetersizse execution kapalıdır.
- Non-DataFrame input güvenli şekilde VERİ YETERSİZ'e düşürülür.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
import concurrent.futures

import numpy as np
import pandas as pd

V21_VERSION = "2.1"

CRITICAL_DIRECT_SYMBOLS = {
    "ES=F",
    "NQ=F",
    "GC=F",
    "SI=F",
}

ALL_MARKET_SYMBOLS = [
    "ES=F", "NQ=F", "SPY", "QQQ", "SMH", "RSP", "HYG", "LQD",
    "^VIX", "^VIX3M", "XLU", "XLP", "XLY", "ARKK", "TLT", "SHY",
    "KRE", "XLF", "USO", "CL=F", "IYT", "BDRY", "DX-Y.NYB", "TIP",
    "IEF", "^TNX", "USDJPY=X", "GC=F", "SI=F", "HG=F", "BTC-USD",
    "ETH-USD",
]

CACHE_MAX_AGE_SECONDS = 2 * 60 * 60
LIVE_MAX_AGE_SECONDS = 150 * 60
DEGRADED_MAX_AGE_SECONDS = 6 * 60 * 60
EXECUTION_LIVE_STATUSES = {"LIVE"}

MIN_DIRECTION_BARS = 8
MIN_ENTRY_BARS = 30
ATR_PERIOD = 14
ATR_BASELINE_PERIOD = 20
RVOL_BASELINE_PERIOD = 20


def _utc_now() -> pd.Timestamp:
    return pd.Timestamp.now(tz="UTC")


def _to_utc_timestamp(value: Any) -> Optional[pd.Timestamp]:
    if value is None:
        return None
    try:
        ts = pd.Timestamp(value)
    except Exception:
        return None
    if ts.tzinfo is None:
        return ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


def _empty_market_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])


def _as_dataframe(value: Any) -> Optional[pd.DataFrame]:
    """
    V2.1 crash guard.

    Normal input: DataFrame.
    Ayrıca eski/ara katmanların yanlışlıkla tuple/dict bırakması durumunda
    DataFrame'i güvenli biçimde ayıklar. Uygun dataframe bulunamazsa None döner.
    """
    if isinstance(value, pd.DataFrame):
        return value

    if isinstance(value, (tuple, list)):
        for item in reversed(value):
            if isinstance(item, pd.DataFrame):
                return item

    if isinstance(value, dict):
        for key in ("data", "df", "frame", "ohlcv", "market_data"):
            item = value.get(key)
            if isinstance(item, pd.DataFrame):
                return item

    return None


def _clean_ohlcv(value: Any) -> pd.DataFrame:
    df = _as_dataframe(value)
    if df is None or df.empty:
        return _empty_market_frame()

    out = df.copy()

    if isinstance(out.columns, pd.MultiIndex):
        out.columns = [col[0] if isinstance(col, tuple) else col for col in out.columns]

    required_price = ["Open", "High", "Low", "Close"]
    if not all(col in out.columns for col in required_price):
        return _empty_market_frame()

    cols = required_price + (["Volume"] if "Volume" in out.columns else [])
    out = out[cols].copy()

    try:
        idx = pd.DatetimeIndex(out.index)
        if idx.tz is None:
            idx = idx.tz_localize("UTC")
        else:
            idx = idx.tz_convert("UTC")
        out.index = idx
    except Exception:
        return _empty_market_frame()

    for col in cols:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    out = out.replace([np.inf, -np.inf], np.nan)
    out = out.dropna(subset=required_price)
    out = out[~out.index.duplicated(keep="last")]
    out = out.sort_index()

    if out.empty:
        return _empty_market_frame()

    if "Volume" not in out.columns:
        # DİKKAT: Volume üretilmiyor. Sadece absence korunuyor.
        out["Volume"] = np.nan

    return out[["Open", "High", "Low", "Close", "Volume"]]


def _bar_age_seconds(df: Any) -> Optional[float]:
    clean = _clean_ohlcv(df)
    if clean.empty:
        return None
    ts = _to_utc_timestamp(clean.index[-1])
    if ts is None:
        return None
    return max(float((_utc_now() - ts).total_seconds()), 0.0)


def _status_from_age(age_seconds: Optional[float]) -> str:
    if age_seconds is None:
        return "UNAVAILABLE"
    if age_seconds <= LIVE_MAX_AGE_SECONDS:
        return "LIVE"
    if age_seconds <= DEGRADED_MAX_AGE_SECONDS:
        return "DEGRADED"
    return "STALE"


def _attach_quality(
    df: Any,
    *,
    source: str,
    source_type: str = "DIRECT",
    status: Optional[str] = None,
    fetched_at: Optional[pd.Timestamp] = None,
    cache_age_seconds: Optional[float] = None,
) -> pd.DataFrame:
    out = _clean_ohlcv(df)
    if out.empty:
        return _empty_market_frame()

    age = _bar_age_seconds(out)
    final_status = status or _status_from_age(age)

    out.attrs["v21"] = V21_VERSION
    out.attrs["source"] = source
    out.attrs["source_type"] = source_type
    out.attrs["is_real"] = True
    out.attrs["is_synthetic"] = False
    out.attrs["fetched_at"] = _to_utc_timestamp(fetched_at) if fetched_at is not None else _utc_now()
    out.attrs["last_bar_time"] = _to_utc_timestamp(out.index[-1])
    out.attrs["age_seconds"] = age
    out.attrs["cache_age_seconds"] = cache_age_seconds
    out.attrs["status"] = final_status
    out.attrs["quality"] = final_status
    return out


def _has_real_live_data(df: Any) -> Tuple[bool, str]:
    frame = _as_dataframe(df)
    if frame is None or frame.empty:
        return False, "GERÇEK VERİ YOK"

    attrs = getattr(frame, "attrs", {}) or {}
    if attrs.get("is_synthetic", False):
        return False, "SENTETİK VERİ REDDEDİLDİ"
    if not attrs.get("is_real", False):
        return False, "GERÇEKLİK DOĞRULAMASI YOK"

    status = str(attrs.get("status", "UNAVAILABLE")).upper()
    if status != "LIVE":
        return False, f"VERİ DURUMU: {status}"

    source_type = str(attrs.get("source_type", "")).upper()
    if source_type != "DIRECT":
        return False, f"KAYNAK TÜRÜ: {source_type or 'BİLİNMİYOR'}"

    return True, "LIVE / DIRECT"


def _atr_series(df: pd.DataFrame, period: int = ATR_PERIOD) -> pd.Series:
    high = pd.to_numeric(df["High"], errors="coerce")
    low = pd.to_numeric(df["Low"], errors="coerce")
    close = pd.to_numeric(df["Close"], errors="coerce")
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()


def _safe_pct_change(close: pd.Series, bars: int) -> float:
    if close is None or len(close) <= bars:
        return 0.0
    old_value = float(close.iloc[-bars - 1])
    new_value = float(close.iloc[-1])
    if not np.isfinite(old_value) or abs(old_value) < 1e-12 or not np.isfinite(new_value):
        return 0.0
    return ((new_value - old_value) / old_value) * 100.0


def _normalized_impulse(df: pd.DataFrame, horizon: int) -> float:
    if df is None or df.empty or len(df) < max(ATR_PERIOD + 2, horizon + 2):
        return 0.0

    close = pd.to_numeric(df["Close"], errors="coerce")
    atr = _atr_series(df, ATR_PERIOD)
    last_close = float(close.iloc[-1])
    last_atr = float(atr.iloc[-1]) if np.isfinite(atr.iloc[-1]) else np.nan

    if not np.isfinite(last_close) or last_close <= 0 or not np.isfinite(last_atr) or last_atr <= 0:
        return 0.0

    roc_pct = _safe_pct_change(close, horizon)
    atr_pct = (last_atr / last_close) * 100.0
    if not np.isfinite(atr_pct) or atr_pct <= 1e-9:
        return 0.0

    value = roc_pct / (atr_pct * np.sqrt(float(horizon)))
    return float(np.clip(value, -4.0, 4.0))


def _persistence_score(df: pd.DataFrame, window: int = 6) -> float:
    if df is None or df.empty or len(df) < window + 2:
        return 0.0

    close = pd.to_numeric(df["Close"], errors="coerce")
    returns = close.pct_change().tail(window).dropna()
    if returns.empty:
        return 0.0

    returns = returns[np.abs(returns) > 1e-9]
    if returns.empty:
        return 0.0

    return float(np.clip(float((returns > 0).mean()) - float((returns < 0).mean()), -1.0, 1.0))


def _adx_di(df: pd.DataFrame, period: int = 14) -> Tuple[float, float]:
    if df is None or df.empty or len(df) < period * 2:
        return 0.0, 0.0

    high = pd.to_numeric(df["High"], errors="coerce")
    low = pd.to_numeric(df["Low"], errors="coerce")
    close = pd.to_numeric(df["Close"], errors="coerce")
    prev_close = close.shift(1)

    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index)

    atr = tr.rolling(period, min_periods=period).mean()
    plus_di = 100.0 * plus_dm.rolling(period, min_periods=period).mean() / (atr + 1e-12)
    minus_di = 100.0 * minus_dm.rolling(period, min_periods=period).mean() / (atr + 1e-12)

    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-12)
    adx = dx.rolling(period, min_periods=period).mean()

    last_adx = float(adx.iloc[-1]) if np.isfinite(adx.iloc[-1]) else 0.0
    pdi = float(plus_di.iloc[-1]) if np.isfinite(plus_di.iloc[-1]) else 0.0
    mdi = float(minus_di.iloc[-1]) if np.isfinite(minus_di.iloc[-1]) else 0.0
    denom = pdi + mdi + 1e-12
    bias = float(np.clip((pdi - mdi) / denom, -1.0, 1.0))
    return last_adx, bias


def _resample_ohlc(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    if df is None or df.empty:
        return _empty_market_frame()
    x = df.copy()
    agg = {
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum",
    }
    out = x.resample(rule, label="right", closed="right").agg(agg).dropna(subset=["Open", "High", "Low", "Close"])
    out.attrs = dict(getattr(df, "attrs", {}) or {})
    out.attrs["last_bar_time"] = _to_utc_timestamp(out.index[-1]) if not out.empty else None
    out.attrs["age_seconds"] = _bar_age_seconds(out)
    return out


def _v21_compute_realtime_price_action(
    df_1h: Any,
    fast_window: int = 4,
    vol_scale: float = 1.0,
    asset_key: Optional[str] = None,
):
    """MODEL_DIRECTION: 1H + 2H + 4H normalized impulse + persistence + ADX/DI."""

    df = _clean_ohlcv(df_1h)
    if df.empty or len(df) < MIN_DIRECTION_BARS:
        return "⚪ VERİ YETERSİZ", "⚪", "gray", 0.0

    close = pd.to_numeric(df["Close"], errors="coerce").dropna()
    if len(close) < MIN_DIRECTION_BARS:
        return "⚪ VERİ YETERSİZ", "⚪", "gray", 0.0

    # 1H görünümü: son gerçekleşmiş saatlik hareket.
    roc_1h = _safe_pct_change(close, 1)

    # 2H / 4H barları gerçek 1H barlardan yeniden örneklenir.
    df_2h = _resample_ohlc(df, "2h")
    df_4h = _resample_ohlc(df, "4h")

    impulse_1h = _normalized_impulse(df, 1)
    impulse_2h = _normalized_impulse(df, 2)
    impulse_4h = _normalized_impulse(df_4h, 1) if len(df_4h) >= ATR_PERIOD + 2 else _normalized_impulse(df, 4)

    persist_1h = _persistence_score(df, 6)
    persist_4h = _persistence_score(df_4h, 5) if len(df_4h) >= 7 else 0.0

    adx_1h, di_bias_1h = _adx_di(df, 14)
    adx_4h, di_bias_4h = _adx_di(df_4h, 14) if len(df_4h) >= 28 else (0.0, 0.0)

    # 1H daha hızlı, 4H daha yapısal.
    base_score = (
        0.45 * impulse_1h
        + 0.30 * impulse_2h
        + 0.45 * impulse_4h
        + 0.20 * persist_1h
        + 0.20 * persist_4h
        + 0.15 * di_bias_1h
        + 0.25 * di_bias_4h
    )

    # ADX yalnızca teyit gücü verir; tek başına yön üretmez.
    adx_strength = np.clip(max(adx_1h, adx_4h) / 35.0, 0.0, 1.0)
    score = base_score * (0.85 + 0.30 * adx_strength)
    score = float(np.clip(score, -4.0, 4.0))

    # Güçlü 1H hareket + flat 4H => otomatik YATAY DEĞİL.
    strong_1h = abs(impulse_1h) >= 1.15
    flat_4h = abs(impulse_4h) < 0.35 and abs(persist_4h) < 0.35

    if strong_1h and flat_4h:
        directional_score = impulse_1h * (0.85 + 0.15 * np.sign(impulse_1h) * np.sign(impulse_2h))
    else:
        directional_score = score

    threshold = 0.65
    strong_threshold = 1.35

    if directional_score >= strong_threshold:
        return f"🟢 GÜÇLÜ YUKARI (%{roc_1h:+.2f})", "🟢🟢", "darkgreen", round(float(roc_1h), 2)
    if directional_score >= threshold:
        return f"🟢 YUKARI (%{roc_1h:+.2f})", "🟢", "lightgreen", round(float(roc_1h), 2)
    if directional_score <= -strong_threshold:
        return f"🔴 GÜÇLÜ AŞAĞI (%{roc_1h:+.2f})", "🔴🔴", "darkred", round(float(roc_1h), 2)
    if directional_score <= -threshold:
        return f"🔴 AŞAĞI (%{roc_1h:+.2f})", "🔴", "red", round(float(roc_1h), 2)

    return f"⚪ YATAY / DENGELİ (%{roc_1h:+.2f})", "⚪", "gray", round(float(roc_1h), 2)


def _v21_evaluate_trade_entry_gate(
    df_1h: Any,
    asset_key: str = "SPX",
) -> Tuple[bool, str, float, float]:
    """EXECUTION_GATE: strict real-data + freshness + ATR + true RVOL."""

    df = _clean_ohlcv(df_1h)
    if df.empty:
        return False, "İşleme Giriş Önerilmez: Gerçek piyasa verisi yok.", 0.0, 0.0

    live_ok, quality_reason = _has_real_live_data(df)
    if not live_ok:
        return False, f"İşleme Giriş Önerilmez: {quality_reason}.", 0.0, 0.0

    if len(df) < MIN_ENTRY_BARS:
        return False, f"İşleme Giriş Önerilmez: Yetersiz veri ({len(df)}/{MIN_ENTRY_BARS} bar).", 0.0, 0.0

    high = pd.to_numeric(df["High"], errors="coerce")
    low = pd.to_numeric(df["Low"], errors="coerce")
    close = pd.to_numeric(df["Close"], errors="coerce")
    volume = pd.to_numeric(df["Volume"], errors="coerce")

    if volume is None or volume.dropna().empty:
        return False, "İşleme Giriş Önerilmez: Hacim verisi yok; RVOL üretilmedi.", 0.0, 0.0

    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    atr = tr.rolling(ATR_PERIOD, min_periods=ATR_PERIOD).mean()
    atr_baseline = atr.shift(1).rolling(ATR_BASELINE_PERIOD, min_periods=ATR_BASELINE_PERIOD).mean()

    last_atr = float(atr.iloc[-1]) if np.isfinite(atr.iloc[-1]) else np.nan
    baseline_atr = float(atr_baseline.iloc[-1]) if np.isfinite(atr_baseline.iloc[-1]) else np.nan

    if not np.isfinite(last_atr) or last_atr <= 0 or not np.isfinite(baseline_atr) or baseline_atr <= 0:
        return False, "İşleme Giriş Önerilmez: ATR referansı hesaplanamadı.", 0.0, 0.0

    atr_ratio = round(float(np.clip(last_atr / (baseline_atr + 1e-12), 0.25, 4.0)), 2)

    clean_volume = volume.replace([np.inf, -np.inf], np.nan)
    historical = clean_volume.iloc[:-1].dropna()
    positive_history = historical[historical > 0]

    if len(positive_history) < RVOL_BASELINE_PERIOD:
        return False, "İşleme Giriş Önerilmez: Gerçek RVOL için yeterli hacim geçmişi yok.", atr_ratio, 0.0

    baseline_volume = clean_volume.shift(1).rolling(RVOL_BASELINE_PERIOD, min_periods=RVOL_BASELINE_PERIOD).mean().iloc[-1]
    current_volume = clean_volume.iloc[-1]

    if (
        not np.isfinite(current_volume)
        or current_volume <= 0
        or not np.isfinite(baseline_volume)
        or baseline_volume <= 0
    ):
        return False, "İşleme Giriş Önerilmez: Gerçek RVOL hesaplanamadı.", atr_ratio, 0.0

    rvol = round(float(np.clip(current_volume / (baseline_volume + 1e-12), 0.05, 10.0)), 2)

    try:
        from config import ENTRY_FILTER_CONFIG
    except Exception:
        ENTRY_FILTER_CONFIG = {
            "vol_shock_high": 2.20,
            "vol_shock_low": 0.65,
            "rvol_climax_shock": 3.20,
            "rvol_illiquid": 0.50,
        }

    cfg = ENTRY_FILTER_CONFIG
    high_limit = float(cfg.get("vol_shock_high", 2.20))
    low_limit = float(cfg.get("vol_shock_low", 0.65))
    climax_limit = float(cfg.get("rvol_climax_shock", 3.20))
    illiquid_limit = float(cfg.get("rvol_illiquid", 0.50))

    if atr_ratio > high_limit:
        return False, f"İşleme Giriş Önerilmez: Volatilite Şoku (ATR {atr_ratio:.2f}x).", atr_ratio, rvol
    if atr_ratio < low_limit:
        return False, f"İşleme Giriş Önerilmez: Volatilite çok düşük (ATR {atr_ratio:.2f}x).", atr_ratio, rvol
    if rvol > climax_limit:
        return False, f"İşleme Giriş Önerilmez: Hacim climax (RVOL {rvol:.2f}x).", atr_ratio, rvol
    if rvol < illiquid_limit:
        return False, f"İşleme Giriş Önerilmez: Gerçek hacim zayıf (RVOL {rvol:.2f}x).", atr_ratio, rvol

    return True, f"İşleme Giriş Uygun: LIVE/DIRECT | ATR {atr_ratio:.2f}x | RVOL {rvol:.2f}x.", atr_ratio, rvol


def _v21_get_data_quality(df: Any) -> Dict[str, Any]:
    frame = _as_dataframe(df)
    if frame is None or frame.empty:
        return {
            "status": "UNAVAILABLE",
            "quality": "UNAVAILABLE",
            "source": None,
            "source_type": None,
            "is_real": False,
            "is_synthetic": False,
            "fetched_at": None,
            "last_bar_time": None,
            "age_seconds": None,
            "cache_age_seconds": None,
        }

    attrs = getattr(frame, "attrs", {}) or {}
    return {
        "status": attrs.get("status", "UNAVAILABLE"),
        "quality": attrs.get("quality", attrs.get("status", "UNAVAILABLE")),
        "source": attrs.get("source"),
        "source_type": attrs.get("source_type"),
        "is_real": bool(attrs.get("is_real", False)),
        "is_synthetic": bool(attrs.get("is_synthetic", False)),
        "fetched_at": attrs.get("fetched_at"),
        "last_bar_time": attrs.get("last_bar_time"),
        "age_seconds": attrs.get("age_seconds"),
        "cache_age_seconds": attrs.get("cache_age_seconds"),
    }


def _v21_fetch_single_ticker_1h(self, symbol: str, period: str = "5d"):
    """Tek gerçek kaynaktan 1H veri. Proxy ve sentetik veri yok."""
    candidate = str(symbol)
    fetched_at = _utc_now()

    try:
        import yfinance as yf
        raw = yf.download(
            candidate,
            period=period,
            interval="1h",
            prepost=True,
            progress=False,
            timeout=10,
            auto_adjust=False,
        )
        clean = _clean_ohlcv(raw)
        if len(clean) >= 2:
            clean = _attach_quality(
                clean,
                source=candidate,
                source_type="DIRECT",
                status=None,
                fetched_at=fetched_at,
                cache_age_seconds=0.0,
            )

            if not hasattr(self, "_v21_cache_fetched_at"):
                self._v21_cache_fetched_at = {}
            if not hasattr(self, "_cache"):
                self._cache = {}

            self._cache[symbol] = clean.copy()
            self._v21_cache_fetched_at[symbol] = fetched_at
            return symbol, clean
    except Exception:
        pass

    cache = getattr(self, "_cache", {}) or {}
    cache_df = cache.get(symbol)
    cache_times = getattr(self, "_v21_cache_fetched_at", {}) or {}
    cached_at = _to_utc_timestamp(cache_times.get(symbol))

    cache_frame = _as_dataframe(cache_df)
    if cache_frame is not None and not cache_frame.empty and cached_at is not None:
        cache_age = max(float((_utc_now() - cached_at).total_seconds()), 0.0)
        if cache_age <= CACHE_MAX_AGE_SECONDS:
            attrs = getattr(cache_frame, "attrs", {}) or {}
            source = str(attrs.get("source", symbol))
            cached = _attach_quality(
                cache_frame,
                source=source,
                source_type="DIRECT",
                status="DEGRADED",
                fetched_at=cached_at,
                cache_age_seconds=cache_age,
            )
            return symbol, cached

    return symbol, _empty_market_frame()


def _v21_fetch_global_market_grid(self) -> Dict[str, pd.DataFrame]:
    """Sadece gerçek kaynaklardan grid oluşturur."""
    if not hasattr(self, "data_quality"):
        self.data_quality = {}
    else:
        self.data_quality.clear()

    if not hasattr(self, "data_sources"):
        self.data_sources = {}
    else:
        self.data_sources.clear()

    results: Dict[str, pd.DataFrame] = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(self.fetch_single_ticker_1h, sym): sym
            for sym in ALL_MARKET_SYMBOLS
        }

        for future in concurrent.futures.as_completed(futures):
            requested = futures[future]
            try:
                returned_symbol, data = future.result()
            except Exception:
                continue

            frame = _as_dataframe(data)
            if frame is None or frame.empty:
                self.data_quality[requested] = _v21_get_data_quality(None)
                self.data_sources[requested] = None
                continue

            attrs = getattr(frame, "attrs", {}) or {}
            if attrs.get("is_synthetic", False):
                self.data_quality[requested] = _v21_get_data_quality(None)
                self.data_sources[requested] = None
                continue

            # Aynı gerçek dataframe'e isim alias'ı veriyoruz.
            # Bu proxy değildir; veri değiştirilmiyor.
            clean_key = (
                returned_symbol
                .replace("^", "")
                .replace("=X", "")
                .replace("=F", "")
                .replace("DX-Y.NYB", "DXY")
            )

            results[returned_symbol] = frame
            results[clean_key] = frame

            q = _v21_get_data_quality(frame)
            self.data_quality[requested] = q
            self.data_sources[requested] = q.get("source")

    if "ES=F" in results:
        results["ES"] = results["ES=F"]
        results["SPX"] = results["ES=F"]
    if "NQ=F" in results:
        results["NQ"] = results["NQ=F"]
    if "GC=F" in results:
        results["GC"] = results["GC=F"]
        results["XAU"] = results["GC=F"]
    if "SI=F" in results:
        results["SI"] = results["SI=F"]
        results["XAG"] = results["SI=F"]
    if "^VIX" in results:
        results["VIX"] = results["^VIX"]
    if "^VIX3M" in results:
        results["VIX3M"] = results["^VIX3M"]

    return results


def v21_get_data_quality(df: Any) -> Dict[str, Any]:
    return _v21_get_data_quality(df)


def apply_v21_patch() -> None:
    """V2.1 monkey-patch aktivasyonu."""
    from data_engine import ResilientDataEngine
    from quant_processor import RobustQuantProcessor

    # Constructor metadata container.
    if not getattr(ResilientDataEngine, "_v21_init_patched", False):
        original_init = ResilientDataEngine.__init__

        def _init_v21(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            self._v21_cache_fetched_at = getattr(self, "_v21_cache_fetched_at", {})
            self.data_quality = getattr(self, "data_quality", {})
            self.data_sources = getattr(self, "data_sources", {})

        ResilientDataEngine.__init__ = _init_v21
        ResilientDataEngine._v21_init_patched = True

    ResilientDataEngine.fetch_single_ticker_1h = _v21_fetch_single_ticker_1h
    ResilientDataEngine.fetch_global_market_grid = _v21_fetch_global_market_grid

    RobustQuantProcessor.compute_realtime_price_action = _v21_compute_realtime_price_action
    RobustQuantProcessor.evaluate_trade_entry_gate = _v21_evaluate_trade_entry_gate


__all__ = [
    "V21_VERSION",
    "apply_v21_patch",
    "v21_get_data_quality",
]
