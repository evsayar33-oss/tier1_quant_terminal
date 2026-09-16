"""
V2.1 — Zero Synthetic Data + Live Multi-Horizon Direction + Strict Execution Gate

AMAÇ
----
1. Sentetik OHLCV kesinlikle üretme.
2. Kritik enstrümanları ETF/proxy ile sessizce değiştirme.
3. Sonsuz/stale cache kullanımını engelle.
4. Her gerçek market dataframe'ine veri kalitesi metadata ekle.
5. Yönü yalnızca 4 barlık ham ROC ile belirleme.
6. 1H / 2H / 4H ATR-normalized impulse + persistence + ADX/DI kullan.
7. Güçlü 1H hareketi, 4H yatay diye otomatik YATAY yapma.
8. Güçlü 4H trendi koru.
9. MODEL_DIRECTION ile EXECUTION_GATE birbirinden bağımsız olsun.
10. Gerçek RVOL hesapla ve mevcut barı baseline'dan çıkar.
11. Volume yoksa fiyat hareketinden sahte RVOL üretme.
12. Veri yetersizse işlem girişini KESİNLİKLE engelle.
13. STALE / DEGRADED / UNAVAILABLE veri ile execution yapma.

AKTİVASYON
----------
app.py içine:

    import v21_patch

ve mevcut import/reload bölümünden sonra:

    v21_patch.apply_v21_patch()

eklenmelidir.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd


# ============================================================
# V2.1 CONFIG
# ============================================================

V21_VERSION = "2.1"

# Bunlar gerçek işlem referanslarıdır.
# ETF/proxy ile değiştirilmeleri YASAK.
CRITICAL_DIRECT_SYMBOLS = {
    "ES=F",
    "NQ=F",
    "GC=F",
    "SI=F",
}

ALL_MARKET_SYMBOLS = [
    "ES=F",
    "NQ=F",
    "SPY",
    "QQQ",
    "SMH",
    "RSP",
    "HYG",
    "LQD",
    "^VIX",
    "^VIX3M",
    "XLU",
    "XLP",
    "XLY",
    "ARKK",
    "TLT",
    "SHY",
    "KRE",
    "XLF",
    "USO",
    "CL=F",
    "IYT",
    "BDRY",
    "DX-Y.NYB",
    "TIP",
    "IEF",
    "^TNX",
    "USDJPY=X",
    "GC=F",
    "SI=F",
    "HG=F",
    "BTC-USD",
    "ETH-USD",
]

# Cache sadece geçici network problemi için tutulur.
# Sonsuza kadar cache kullanılamaz.
CACHE_MAX_AGE_SECONDS = 2 * 60 * 60

# Son bar yaşına göre veri sınıfları.
LIVE_MAX_AGE_SECONDS = 150 * 60
DEGRADED_MAX_AGE_SECONDS = 6 * 60 * 60

# Execution yalnızca LIVE + DIRECT veriye izin verir.
EXECUTION_LIVE_STATUSES = {"LIVE"}

MIN_DIRECTION_BARS = 8
MIN_ENTRY_BARS = 30

ATR_PERIOD = 14
ATR_BASELINE_PERIOD = 20
RVOL_BASELINE_PERIOD = 20


# ============================================================
# TIME / DATA HELPERS
# ============================================================

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


def _clean_ohlcv(df: Optional[pd.DataFrame]) -> pd.DataFrame:
    """
    Gerçek OHLCV dataframe'ini standartlaştırır.

    Sentetik veri üretmez.
    Eksik fiyat satırlarını temizler.
    Volume yoksa Volume yaratmaz.
    """

    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    if isinstance(out.columns, pd.MultiIndex):
        flat_columns = []

        for col in out.columns:
            if isinstance(col, tuple):
                flat_columns.append(col[0])
            else:
                flat_columns.append(col)

        out.columns = flat_columns

    required = [
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
    ]

    if not all(col in out.columns for col in required):
        return pd.DataFrame()

    out = out[required].copy()

    try:
        idx = pd.DatetimeIndex(out.index)

        if idx.tz is None:
            idx = idx.tz_localize("UTC")
        else:
            idx = idx.tz_convert("UTC")

        out.index = idx

    except Exception:
        return pd.DataFrame()

    for col in required:
        out[col] = pd.to_numeric(
            out[col],
            errors="coerce",
        )

    out = out.replace(
        [np.inf, -np.inf],
        np.nan,
    )

    out = out.dropna(
        subset=[
            "Open",
            "High",
            "Low",
            "Close",
        ]
    )

    out = out[
        ~out.index.duplicated(
            keep="last"
        )
    ]

    out = out.sort_index()

    if out.empty:
        return pd.DataFrame()

    # Volume sütunu gerçekten kaynaktan gelmiştir.
    # NaN -> 0 yapılabilir; fakat volume olmayan kaynak
    # kesinlikle sonradan fiyat verisinden türetilmeyecektir.
    out["Volume"] = out["Volume"].fillna(0.0)

    return out


def _bar_age_seconds(
    df: pd.DataFrame,
) -> Optional[float]:

    if df is None or df.empty:
        return None

    last_bar = _to_utc_timestamp(
        df.index[-1]
    )

    if last_bar is None:
        return None

    age = (
        _utc_now() - last_bar
    ).total_seconds()

    return max(
        float(age),
        0.0,
    )


def _status_from_bar_age(
    age_seconds: Optional[float],
) -> str:

    if age_seconds is None:
        return "UNAVAILABLE"

    if age_seconds <= LIVE_MAX_AGE_SECONDS:
        return "LIVE"

    if age_seconds <= DEGRADED_MAX_AGE_SECONDS:
        return "DEGRADED"

    return "STALE"


def _attach_quality(
    df: pd.DataFrame,
    *,
    source: str,
    source_type: str = "DIRECT",
    status: Optional[str] = None,
    fetched_at: Optional[pd.Timestamp] = None,
    cache_age_seconds: Optional[float] = None,
) -> pd.DataFrame:

    out = df.copy()

    age_seconds = _bar_age_seconds(out)

    final_status = (
        status
        or _status_from_bar_age(
            age_seconds
        )
    )

    out.attrs["v21"] = V21_VERSION
    out.attrs["source"] = source
    out.attrs["source_type"] = source_type

    out.attrs["is_real"] = True
    out.attrs["is_synthetic"] = False

    out.attrs["fetched_at"] = (
        _to_utc_timestamp(
            fetched_at
        )
        if fetched_at is not None
        else _utc_now()
    )

    out.attrs["last_bar_time"] = (
        _to_utc_timestamp(
            out.index[-1]
        )
        if not out.empty
        else None
    )

    out.attrs["age_seconds"] = age_seconds
    out.attrs["cache_age_seconds"] = (
        cache_age_seconds
    )

    out.attrs["status"] = final_status
    out.attrs["quality"] = final_status

    return out


def _empty_market_frame() -> pd.DataFrame:

    return pd.DataFrame(
        columns=[
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
        ]
    )


# ============================================================
# TECHNICAL HELPERS
# ============================================================

def _atr_series(
    df: pd.DataFrame,
    period: int = ATR_PERIOD,
) -> pd.Series:

    high = pd.to_numeric(
        df["High"],
        errors="coerce",
    )

    low = pd.to_numeric(
        df["Low"],
        errors="coerce",
    )

    close = pd.to_numeric(
        df["Close"],
        errors="coerce",
    )

    prev_close = close.shift(1)

    tr = pd.concat(
        [
            high - low,
            (
                high - prev_close
            ).abs(),
            (
                low - prev_close
            ).abs(),
        ],
        axis=1,
    ).max(axis=1)

    return tr.rolling(
        period,
        min_periods=period,
    ).mean()


def _safe_pct_change(
    close: pd.Series,
    bars: int,
) -> float:

    if close is None:
        return 0.0

    if len(close) <= bars:
        return 0.0

    old_value = float(
        close.iloc[
            -bars - 1
        ]
    )

    new_value = float(
        close.iloc[-1]
    )

    if (
        not np.isfinite(old_value)
        or abs(old_value) < 1e-12
        or not np.isfinite(new_value)
    ):
        return 0.0

    return (
        (new_value - old_value)
        / old_value
    ) * 100.0


def _normalized_impulse(
    df: pd.DataFrame,
    horizon: int,
) -> float:

    if (
        df is None
        or df.empty
        or len(df)
        < max(
            ATR_PERIOD + 2,
            horizon + 2,
        )
    ):
        return 0.0

    close = pd.to_numeric(
        df["Close"],
        errors="coerce",
    )

    atr = _atr_series(
        df,
        ATR_PERIOD,
    )

    last_close = float(
        close.iloc[-1]
    )

    last_atr = float(
        atr.iloc[-1]
    ) if np.isfinite(
        atr.iloc[-1]
    ) else np.nan

    if (
        not np.isfinite(last_close)
        or last_close <= 0
        or not np.isfinite(last_atr)
        or last_atr <= 0
    ):
        return 0.0

    roc_pct = _safe_pct_change(
        close,
        horizon,
    )

    atr_pct_per_hour = (
        last_atr
        / last_close
    ) * 100.0

    if (
        not np.isfinite(
            atr_pct_per_hour
        )
        or atr_pct_per_hour <= 1e-9
    ):
        return 0.0

    normalized = (
        roc_pct
        / (
            atr_pct_per_hour
            * np.sqrt(
                float(horizon)
            )
        )
    )

    return float(
        np.clip(
            normalized,
            -4.0,
            4.0,
        )
    )


def _persistence_score(
    df: pd.DataFrame,
    window: int = 6,
) -> float:

    if (
        df is None
        or df.empty
        or len(df) < window + 2
    ):
        return 0.0

    close = pd.to_numeric(
        df["Close"],
        errors="coerce",
    )

    returns = (
        close
        .pct_change()
        .tail(window)
        .dropna()
    )

    if returns.empty:
        return 0.0

    # Mikro / anlamsız hareketleri
    # persistence hesabından çıkar.
    returns = returns[
        np.abs(returns) > 1e-9
    ]

    if returns.empty:
        return 0.0

    positive_share = float(
        (returns > 0).mean()
    )

    negative_share = float(
        (returns < 0).mean()
    )

    score = (
        positive_share
        - negative_share
    )

    return float(
        np.clip(
            score,
            -1.0,
            1.0,
        )
    )


def _adx_di(
    df: pd.DataFrame,
    period: int = 14,
) -> Tuple[float, float]:

    """
    Return:
        ADX
        directional_bias [-1, +1]

    ADX yön değildir.
    +DI/-DI yön doğrulaması için kullanılır.
    """

    if (
        df is None
        or df.empty
        or len(df)
        < period * 2
    ):
        return 0.0, 0.0

    high = pd.to_numeric(
        df["High"],
        errors="coerce",
    )

    low = pd.to_numeric(
        df["Low"],
        errors="coerce",
    )

    close = pd.to_numeric(
        df["Close"],
        errors="coerce",
    )

    prev_close = close.shift(1)

    tr = pd.concat(
        [
            high - low,
            (
                high - prev_close
            ).abs(),
            (
                low - prev_close
            ).abs(),
        ],
        axis=1,
    ).max(axis=1)

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(
        np.where(
            (up_move > down_move)
            & (up_move > 0),
            up_move,
            0.0,
        ),
        index=df.index,
        dtype="float64",
    )

    minus_dm = pd.Series(
        np.where(
            (down_move > up_move)
            & (down_move > 0),
            down_move,
            0.0,
        ),
        index=df.index,
        dtype="float64",
    )

    atr = tr.rolling(
        period,
        min_periods=period,
    ).mean()

    plus_di = (
        100.0
        * (
            plus_dm.rolling(
                period,
                min_periods=period,
            ).mean()
            / (
                atr + 1e-12
            )
        )
    )

    minus_di = (
        100.0
        * (
            minus_dm.rolling(
                period,
                min_periods=period,
            ).mean()
            / (
                atr + 1e-12
            )
        )
    )

    dx = (
        100.0
        * (
            (
                plus_di
                - minus_di
            ).abs()
            / (
                plus_di
                + minus_di
                + 1e-12
            )
        )
    )

    adx = dx.rolling(
        period,
        min_periods=period,
    ).mean()

    adx_value = float(
        adx.iloc[-1]
    ) if np.isfinite(
        adx.iloc[-1]
    ) else 0.0

    plus_value = float(
        plus_di.iloc[-1]
    ) if np.isfinite(
        plus_di.iloc[-1]
    ) else 0.0

    minus_value = float(
        minus_di.iloc[-1]
    ) if np.isfinite(
        minus_di.iloc[-1]
    ) else 0.0

    di_sum = (
        plus_value
        + minus_value
    )

    directional_bias = (
        plus_value
        - minus_value
    ) / (
        di_sum + 1e-12
    )

    return (
        round(
            max(
                adx_value,
                0.0,
            ),
            2,
        ),
        float(
            np.clip(
                directional_bias,
                -1.0,
                1.0,
            )
        ),
    )


# ============================================================
# DATA QUALITY
# ============================================================

def _has_real_live_data(
    df: Optional[pd.DataFrame],
) -> Tuple[bool, str]:

    if df is None or df.empty:
        return False, "VERİ YOK"

    attrs = (
        getattr(
            df,
            "attrs",
            {},
        )
        or {}
    )

    if attrs.get(
        "is_synthetic",
        False,
    ):
        return (
            False,
            "SENTETİK VERİ REDDEDİLDİ",
        )

    if not attrs.get(
        "is_real",
        False,
    ):
        return (
            False,
            "GERÇEKLİK DOĞRULAMASI YOK",
        )

    status = str(
        attrs.get(
            "status",
            "UNAVAILABLE",
        )
    ).upper()

    if (
        status
        not in EXECUTION_LIVE_STATUSES
    ):
        return (
            False,
            f"VERİ DURUMU: {status}",
        )

    source_type = str(
        attrs.get(
            "source_type",
            "",
        )
    ).upper()

    if source_type != "DIRECT":
        return (
            False,
            "KAYNAK TÜRÜ: "
            f"{source_type or 'BİLİNMİYOR'}",
        )

    return (
        True,
        "LIVE / DIRECT",
    )


# ============================================================
# DATA ENGINE — V2.1
# ============================================================

def _v21_fetch_single_ticker_1h(
    self,
    symbol: str,
    period: str = "5d",
):

    """
    Tek bir doğrudan market kaynağından 1H veri çeker.

    ÖNEMLİ:
    - Proxy yok.
    - ETF ikamesi yok.
    - Sentetik OHLCV yok.
    - Sonsuz stale cache yok.
    """

    # Her sembol kendi gerçek kaynağıdır.
    candidate_symbols = [symbol]

    # Özellikle kritik futures söz konusu olduğunda
    # alternatif proxy kullanmak YASAK.
    if symbol in CRITICAL_DIRECT_SYMBOLS:
        candidate_symbols = [symbol]

    fetched_at = _utc_now()

    for candidate in candidate_symbols:

        try:
            import yfinance as yf

            df = yf.download(
                candidate,
                period=period,
                interval="1h",
                prepost=True,
                progress=False,
                timeout=10,
                auto_adjust=False,
            )

            clean = _clean_ohlcv(df)

            if len(clean) < 2:
                continue

            clean = _attach_quality(
                clean,
                source=candidate,
                source_type="DIRECT",
                status=None,
                fetched_at=fetched_at,
                cache_age_seconds=0.0,
            )

            if not hasattr(
                self,
                "_v21_cache_fetched_at",
            ):
                self._v21_cache_fetched_at = {}

            self._cache[
                symbol
            ] = clean.copy()

            self._v21_cache_fetched_at[
                symbol
            ] = fetched_at

            return (
                symbol,
                clean,
            )

        except Exception:
            continue

    # --------------------------------------------------------
    # Bounded real-data cache
    # --------------------------------------------------------

    cache_df = getattr(
        self,
        "_cache",
        {},
    ).get(symbol)

    cache_times = getattr(
        self,
        "_v21_cache_fetched_at",
        {},
    )

    cached_at = _to_utc_timestamp(
        cache_times.get(symbol)
    )

    if (
        cache_df is not None
        and not cache_df.empty
        and cached_at is not None
    ):

        cache_age = max(
            float(
                (
                    _utc_now()
                    - cached_at
                ).total_seconds()
            ),
            0.0,
        )

        if (
            cache_age
            <= CACHE_MAX_AGE_SECONDS
        ):

            source = str(
                (
                    getattr(
                        cache_df,
                        "attrs",
                        {},
                    )
                    or {}
                ).get(
                    "source",
                    symbol,
                )
            )

            cached = _attach_quality(
                _clean_ohlcv(
                    cache_df
                ),
                source=source,
                source_type="DIRECT",
                status="DEGRADED",
                fetched_at=cached_at,
                cache_age_seconds=cache_age,
            )

            return (
                symbol,
                cached,
            )

    # --------------------------------------------------------
    # Gerçek veri yoksa satır yok.
    # --------------------------------------------------------

    return (
        symbol,
        _empty_market_frame(),
    )


def _v21_fetch_global_market_grid(
    self,
) -> Dict[str, pd.DataFrame]:

    """
    Yalnızca gerçek market verisinden grid üretir.

    Sentetik base_map tamamen kaldırılmıştır.
    """

    tickers = list(
        ALL_MARKET_SYMBOLS
    )

    results = {}

    if not hasattr(
        self,
        "data_quality",
    ):
        self.data_quality = {}

    if not hasattr(
        self,
        "data_sources",
    ):
        self.data_sources = {}

    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=10
    ) as executor:

        future_to_sym = {
            executor.submit(
                self.fetch_single_ticker_1h,
                sym,
            ): sym
            for sym in tickers
        }

        for future in concurrent.futures.as_completed(
            future_to_sym
        ):

            requested_symbol = (
                future_to_sym[future]
            )

            try:
                symbol, data = (
                    future.result()
                )
            except Exception:
                continue

            if (
                data is None
                or data.empty
            ):
                continue

            attrs = (
                getattr(
                    data,
                    "attrs",
                    {},
                )
                or {}
            )

            # Sentetik herhangi bir şey gelirse
            # grid'e dahil etmiyoruz.
            if attrs.get(
                "is_synthetic",
                False,
            ):
                continue

            clean_key = (
                symbol
                .replace("^", "")
                .replace("=X", "")
                .replace("=F", "")
                .replace(
                    "DX-Y.NYB",
                    "DXY",
                )
            )

            results[
                symbol
            ] = data

            results[
                clean_key
            ] = data

            self.data_quality[
                symbol
            ] = {
                "status": attrs.get(
                    "status"
                ),
                "quality": attrs.get(
                    "quality"
                ),
                "source": attrs.get(
                    "source"
                ),
                "source_type": attrs.get(
                    "source_type"
                ),
                "is_real": attrs.get(
                    "is_real",
                    False,
                ),
                "is_synthetic": attrs.get(
                    "is_synthetic",
                    False,
                ),
                "fetched_at": attrs.get(
                    "fetched_at"
                ),
                "last_bar_time": attrs.get(
                    "last_bar_time"
                ),
                "age_seconds": attrs.get(
                    "age_seconds"
                ),
                "cache_age_seconds": attrs.get(
                    "cache_age_seconds"
                ),
            }

            self.data_sources[
                symbol
            ] = attrs.get(
                "source"
            )

    # ========================================================
    # SADECE IDENTITY ALIAS
    #
    # Bunlar proxy değildir.
    # Aynı gerçek futures dataframe'ine isim alias'ıdır.
    # ========================================================

    if "ES=F" in results:
        results["ES"] = results[
            "ES=F"
        ]
        results["SPX"] = results[
            "ES=F"
        ]

    if "NQ=F" in results:
        results["NQ"] = results[
            "NQ=F"
        ]

    if "GC=F" in results:
        results["GC"] = results[
            "GC=F"
        ]
        results["XAU"] = results[
            "GC=F"
        ]

    if "SI=F" in results:
        results["SI"] = results[
            "SI=F"
        ]
        results["XAG"] = results[
            "SI=F"
        ]

    if "^VIX" in results:
        results["VIX"] = results[
            "^VIX"
        ]

    if "^VIX3M" in results:
        results["VIX3M"] = results[
            "^VIX3M"
        ]

    return results


# ============================================================
# QUANT PROCESSOR — MODEL DIRECTION
# ============================================================

def _v21_compute_realtime_price_action(
    df_1h: pd.DataFrame,
    fast_window: int = 4,
    vol_scale: float = 1.0,
    asset_key: Optional[str] = None,
):

    """
    MODEL_DIRECTION

    Kullanılan yapı:

        1H impulse
        2H impulse
        4H impulse
        persistence
        ADX
        +DI / -DI

    Kritik davranış:

    Güçlü 1H hareket
        +
    4H henüz yatay
        =>
    otomatik YATAY değildir.

    4H trend güçlüyse yön daha da doğrulanır.

    ADX tek başına yön değildir.
    """

    if (
        df_1h is None
        or df_1h.empty
        or len(df_1h)
        < MIN_DIRECTION_BARS
    ):

        return (
            "⚪ VERİ YETERSİZ",
            "⚪",
            "gray",
            0.0,
        )

    close = pd.to_numeric(
        df_1h["Close"],
        errors="coerce",
    ).dropna()

    if (
        len(close)
        < MIN_DIRECTION_BARS
    ):
        return (
            "⚪ VERİ YETERSİZ",
            "⚪",
            "gray",
            0.0,
        )

    # Kullanıcıya gösterilen anlık hareket:
    # son 1H.
    roc_1h = _safe_pct_change(
        close,
        1,
    )

    # Çoklu horizon impulse.
    z1 = _normalized_impulse(
        df_1h,
        1,
    )

    z2 = _normalized_impulse(
        df_1h,
        2,
    )

    z4 = _normalized_impulse(
        df_1h,
        4,
    )

    persistence = _persistence_score(
        df_1h,
        window=6,
    )

    adx_value, di_bias = _adx_di(
        df_1h,
        period=14,
    )

    # ========================================================
    # ANA YÖN SKORU
    # ========================================================
    #
    # 1H en yüksek ağırlıkta.
    # Çünkü "şu anda ne oluyor?" sorusunu cevaplıyor.
    #
    # 4H yalnızca bağlam.
    # Tek başına veto etmiyor.
    # ========================================================

    impulse_score = (
        0.50 * z1
        + 0.20 * z2
        + 0.20 * z4
        + 0.10 * (
            persistence * 2.0
        )
    )

    # ========================================================
    # ADX / DI CONFIRMATION
    # ========================================================

    if adx_value >= 25.0:

        impulse_score += (
            0.18 * di_bias
        )

    elif adx_value >= 20.0:

        impulse_score += (
            0.10 * di_bias
        )

    else:

        # Düşük ADX güveni düşürür,
        # ancak kuvvetli impulse'ı tamamen silmez.
        impulse_score *= 0.90

    impulse_score = float(
        np.clip(
            impulse_score,
            -4.0,
            4.0,
        )
    )

    # ========================================================
    # VOLATILITY SCALING
    # ========================================================

    scale = max(
        float(vol_scale),
        0.5,
    )

    base_threshold = (
        0.48
        * np.sqrt(scale)
    )

    strong_threshold = (
        1.00
        * np.sqrt(scale)
    )

    # ========================================================
    # CLASSIFICATION
    # ========================================================

    if (
        impulse_score
        <= -strong_threshold
    ):

        return (
            f"🔴 GÜÇLÜ AŞAĞI "
            f"(%{roc_1h:+.2f})",
            "🔴🔴",
            "darkred",
            round(
                float(roc_1h),
                2,
            ),
        )

    if (
        impulse_score
        <= -base_threshold
    ):

        return (
            f"🔴 AŞAĞI "
            f"(%{roc_1h:+.2f})",
            "🔴",
            "red",
            round(
                float(roc_1h),
                2,
            ),
        )

    if (
        impulse_score
        >= strong_threshold
    ):

        return (
            f"🟢 GÜÇLÜ YUKARI "
            f"(%{roc_1h:+.2f})",
            "🟢🟢",
            "green",
            round(
                float(roc_1h),
                2,
            ),
        )

    if (
        impulse_score
        >= base_threshold
    ):

        return (
            f"🟢 YUKARI "
            f"(%{roc_1h:+.2f})",
            "🟢",
            "lightgreen",
            round(
                float(roc_1h),
                2,
            ),
        )

    return (
        f"⚪ YATAY / DENGELİ "
        f"(%{roc_1h:+.2f})",
        "⚪",
        "gray",
        round(
            float(roc_1h),
            2,
        ),
    )


# ============================================================
# QUANT PROCESSOR — EXECUTION GATE
# ============================================================

def _v21_evaluate_trade_entry_gate(
    df_1h: pd.DataFrame,
    asset_key: str = "SPX",
) -> Tuple[
    bool,
    str,
    float,
    float,
]:

    """
    EXECUTION_GATE

    Ayrı mantık:

        MODEL_DIRECTION
                |
                v
          Piyasa yönü

        EXECUTION_GATE
                |
                v
        İşleme girmek uygun mu?

    Bu fonksiyon yön belirlemez.

    Kontroller:

        1. Gerçek veri
        2. LIVE veri
        3. Yeterli bar
        4. ATR regime
        5. Gerçek RVOL
        6. Current bar baseline dışında
        7. Volume yoksa FALSE
    """

    # ========================================================
    # 1. DATA EXISTENCE
    # ========================================================

    if (
        df_1h is None
        or df_1h.empty
    ):

        return (
            False,
            "İşleme Giriş Önerilmez: "
            "Gerçek piyasa verisi yok.",
            0.0,
            0.0,
        )

    # ========================================================
    # 2. DATA QUALITY
    # ========================================================

    live_ok, quality_reason = (
        _has_real_live_data(
            df_1h
        )
    )

    if not live_ok:

        return (
            False,
            "İşleme Giriş Önerilmez: "
            f"{quality_reason}.",
            0.0,
            0.0,
        )

    # ========================================================
    # 3. DATA DEPTH
    # ========================================================

    if (
        len(df_1h)
        < MIN_ENTRY_BARS
    ):

        return (
            False,
            "İşleme Giriş Önerilmez: "
            f"Yetersiz veri "
            f"({len(df_1h)}/"
            f"{MIN_ENTRY_BARS} bar).",
            0.0,
            0.0,
        )

    high = pd.to_numeric(
        df_1h["High"],
        errors="coerce",
    )

    low = pd.to_numeric(
        df_1h["Low"],
        errors="coerce",
    )

    close = pd.to_numeric(
        df_1h["Close"],
        errors="coerce",
    )

    volume = pd.to_numeric(
        df_1h["Volume"],
        errors="coerce",
    )

    if volume is None:

        return (
            False,
            "İşleme Giriş Önerilmez: "
            "Hacim verisi yok.",
            0.0,
            0.0,
        )

    # ========================================================
    # 4. TRUE RANGE / ATR
    # ========================================================

    prev_close = close.shift(1)

    tr = pd.concat(
        [
            high - low,
            (
                high - prev_close
            ).abs(),
            (
                low - prev_close
            ).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = tr.rolling(
        ATR_PERIOD,
        min_periods=ATR_PERIOD,
    ).mean()

    # Çok önemli:
    #
    # Current ATR baseline'a dahil edilmez.
    #
    atr_baseline = (
        atr
        .shift(1)
        .rolling(
            ATR_BASELINE_PERIOD,
            min_periods=ATR_BASELINE_PERIOD,
        )
        .mean()
    )

    last_atr = (
        float(
            atr.iloc[-1]
        )
        if np.isfinite(
            atr.iloc[-1]
        )
        else np.nan
    )

    baseline_atr = (
        float(
            atr_baseline.iloc[-1]
        )
        if np.isfinite(
            atr_baseline.iloc[-1]
        )
        else np.nan
    )

    if (
        not np.isfinite(
            last_atr
        )
        or last_atr <= 0
        or not np.isfinite(
            baseline_atr
        )
        or baseline_atr <= 0
    ):

        return (
            False,
            "İşleme Giriş Önerilmez: "
            "ATR referansı hesaplanamadı.",
            0.0,
            0.0,
        )

    atr_ratio = (
        last_atr
        / (
            baseline_atr
            + 1e-12
        )
    )

    atr_ratio = round(
        float(
            np.clip(
                atr_ratio,
                0.25,
                4.0,
            )
        ),
        2,
    )

    # ========================================================
    # 5. TRUE RVOL
    # ========================================================
    #
    # CURRENT BAR BASELINE'A DAHİL DEĞİL.
    #
    # Eski mantık:
    #
    # volume.rolling(20).mean()
    #
    # Yanlış çünkü current bar kendisini baseline
    # içine sokuyor.
    #
    # Yeni mantık:
    #
    # volume.shift(1).rolling(20).mean()
    # ========================================================

    clean_volume = volume.replace(
        [np.inf, -np.inf],
        np.nan,
    )

    if clean_volume.isna().all():

        return (
            False,
            "İşleme Giriş Önerilmez: "
            "Hacim verisi kullanılamıyor; "
            "RVOL üretilmedi.",
            atr_ratio,
            0.0,
        )

    historical_volume = (
        clean_volume.iloc[:-1]
        .dropna()
    )

    positive_history = (
        historical_volume[
            historical_volume > 0
        ]
    )

    if (
        len(positive_history)
        < RVOL_BASELINE_PERIOD
    ):

        return (
            False,
            "İşleme Giriş Önerilmez: "
            "Gerçek RVOL için "
            "yeterli hacim geçmişi yok.",
            atr_ratio,
            0.0,
        )

    baseline_volume = (
        clean_volume
        .shift(1)
        .rolling(
            RVOL_BASELINE_PERIOD,
            min_periods=RVOL_BASELINE_PERIOD,
        )
        .mean()
        .iloc[-1]
    )

    current_volume = (
        clean_volume.iloc[-1]
    )

    if (
        not np.isfinite(
            current_volume
        )
        or current_volume <= 0
        or not np.isfinite(
            baseline_volume
        )
        or baseline_volume <= 0
    ):

        return (
            False,
            "İşleme Giriş Önerilmez: "
            "Gerçek RVOL hesaplanamadı.",
            atr_ratio,
            0.0,
        )

    rvol = (
        current_volume
        / (
            baseline_volume
            + 1e-12
        )
    )

    rvol = round(
        float(
            np.clip(
                rvol,
                0.05,
                10.0,
            )
        ),
        2,
    )

    # ========================================================
    # 6. CONFIG
    # ========================================================

    try:

        from config import (
            ENTRY_FILTER_CONFIG
        )

    except ImportError:

        ENTRY_FILTER_CONFIG = {
            "vol_shock_high": 2.20,
            "vol_shock_low": 0.65,
            "rvol_strong_min": 1.25,
            "rvol_climax_shock": 3.20,
            "rvol_illiquid": 0.50,
        }

    cfg = ENTRY_FILTER_CONFIG

    # ========================================================
    # 7. ATR SHOCK
    # ========================================================

    if (
        atr_ratio
        > float(
            cfg.get(
                "vol_shock_high",
                2.20,
            )
        )
    ):

        return (
            False,
            "İşleme Giriş Önerilmez: "
            f"Volatilite Şoku "
            f"(ATR {atr_ratio:.2f}x).",
            atr_ratio,
            rvol,
        )

    # ========================================================
    # 8. LOW VOL
    # ========================================================

    if (
        atr_ratio
        < float(
            cfg.get(
                "vol_shock_low",
                0.65,
            )
        )
    ):

        return (
            False,
            "İşleme Giriş Önerilmez: "
            f"Volatilite çok düşük "
            f"(ATR {atr_ratio:.2f}x).",
            atr_ratio,
            rvol,
        )

    # ========================================================
    # 9. VOLUME CLIMAX
    # ========================================================

    if (
        rvol
        > float(
            cfg.get(
                "rvol_climax_shock",
                3.20,
            )
        )
    ):

        return (
            False,
            "İşleme Giriş Önerilmez: "
            f"Hacim climax "
            f"(RVOL {rvol:.2f}x).",
            atr_ratio,
            rvol,
        )

    # ========================================================
    # 10. ILLIQUID
    # ========================================================

    if (
        rvol
        < float(
            cfg.get(
                "rvol_illiquid",
                0.50,
            )
        )
    ):

        return (
            False,
            "İşleme Giriş Önerilmez: "
            f"Gerçek hacim zayıf "
            f"(RVOL {rvol:.2f}x).",
            atr_ratio,
            rvol,
        )

    # ========================================================
    # 11. APPROVED
    # ========================================================

    return (
        True,
        "İşleme Giriş Uygun: "
        "LIVE/DIRECT | "
        f"ATR {atr_ratio:.2f}x | "
        f"RVOL {rvol:.2f}x.",
        atr_ratio,
        rvol,
    )


# ============================================================
# DATA QUALITY ACCESSOR
# ============================================================

def v21_get_data_quality(
    df: Optional[pd.DataFrame],
) -> Dict[str, Any]:

    if (
        df is None
        or df.empty
    ):

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

    attrs = (
        getattr(
            df,
            "attrs",
            {},
        )
        or {}
    )

    return {
        "status": attrs.get(
            "status",
            "UNAVAILABLE",
        ),
        "quality": attrs.get(
            "quality",
            attrs.get(
                "status",
                "UNAVAILABLE",
            ),
        ),
        "source": attrs.get(
            "source"
        ),
        "source_type": attrs.get(
            "source_type"
        ),
        "is_real": bool(
            attrs.get(
                "is_real",
                False,
            )
        ),
        "is_synthetic": bool(
            attrs.get(
                "is_synthetic",
                False,
            )
        ),
        "fetched_at": attrs.get(
            "fetched_at"
        ),
        "last_bar_time": attrs.get(
            "last_bar_time"
        ),
        "age_seconds": attrs.get(
            "age_seconds"
        ),
        "cache_age_seconds": attrs.get(
            "cache_age_seconds"
        ),
    }


# ============================================================
# ACTIVATION
# ============================================================

def apply_v21_patch() -> None:
    """
    Mevcut mimariyi bozmadan V2.1'i aktive eder.

    Streamlit rerun sırasında birden fazla kez çağrılsa dahi
    patch güvenli şekilde tekrar uygulanabilir.
    """

    from data_engine import (
        ResilientDataEngine
    )

    from quant_processor import (
        RobustQuantProcessor
    )

    # --------------------------------------------------------
    # Constructor'a sadece metadata container ekle.
    # --------------------------------------------------------

    if not getattr(
        ResilientDataEngine,
        "_v21_init_patched",
        False,
    ):

        original_init = (
            ResilientDataEngine.__init__
        )

        def _init_v21(
            self,
            *args,
            **kwargs,
        ):

            original_init(
                self,
                *args,
                **kwargs,
            )

            self._v21_cache_fetched_at = (
                getattr(
                    self,
                    "_v21_cache_fetched_at",
                    {},
                )
            )

            self.data_quality = (
                getattr(
                    self,
                    "data_quality",
                    {},
                )
            )

            self.data_sources = (
                getattr(
                    self,
                    "data_sources",
                    {},
                )
            )

        ResilientDataEngine.__init__ = (
            _init_v21
        )

        ResilientDataEngine._v21_init_patched = (
            True
        )

    # --------------------------------------------------------
    # DATA ENGINE
    # --------------------------------------------------------

    ResilientDataEngine.fetch_single_ticker_1h = (
        _v21_fetch_single_ticker_1h
    )

    ResilientDataEngine.fetch_global_market_grid = (
        _v21_fetch_global_market_grid
    )

    # --------------------------------------------------------
    # QUANT PROCESSOR
    # --------------------------------------------------------

    RobustQuantProcessor.compute_realtime_price_action = (
        _v21_compute_realtime_price_action
    )

    RobustQuantProcessor.evaluate_trade_entry_gate = (
        _v21_evaluate_trade_entry_gate
    )


__all__ = [
    "V21_VERSION",
    "apply_v21_patch",
    "v21_get_data_quality",
]
