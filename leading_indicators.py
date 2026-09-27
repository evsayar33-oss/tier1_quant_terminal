"""
Leading (Öncü) Indicators — Options-Market-Derived
====================================================
Every other Cluster E ("Varlığa Özel İtici Güç") factor in this repo is
either raw price momentum or a price-return regression. These are not: they
are built from CBOE implied-volatility indices (VIX, VXN, GVZ, VXSLV) --
the options market's OWN forward-looking price of future risk. This is data
about what the future is expected to look like, not a summary of what
price has already done.

Two distinct signal types are implemented, matching how vol desks actually
use this data:

1. Term-structure slope (compute_vol_term_structure_lead): the spread
   between near-term and 3-month implied vol. Backwardation (near-term
   priced ABOVE the 3-month) is a well-documented leading stress signal --
   the market is pricing elevated risk RIGHT NOW, ahead of whatever event is
   driving it showing up fully in price. Contango (the normal state) gets a
   deliberately muted read: it signals absence-of-stress, not a strong
   bullish predictor, so the two sides of this function are NOT symmetric.

2. Relative/implied-vol-momentum lead (compute_relative_vol_premium_lead):
   for an asset-specific vol index (VXN for Nasdaq, GVZ for gold, VXSLV for
   silver) with no matching short/long-dated pair, the signal is how far
   that index's LEVEL has moved from its own recent norm (self-calibrating
   z-score, not a fixed magic threshold) and, where a benchmark vol index is
   available (VXN vs VIX), how far the SPREAD between them has moved from
   its own norm. A tech-specific or metal-specific options market pricing in
   materially more future risk than usual is a leading signal for that
   asset specifically -- again, before price necessarily reflects it.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd


def _last_close(df: Any) -> Optional[float]:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty or "Close" not in df.columns:
        return None
    s = pd.to_numeric(df["Close"], errors="coerce").dropna()
    if s.empty:
        return None
    v = float(s.iloc[-1])
    return v if np.isfinite(v) and v > 0 else None


def _close_series(df: Any, window: int = 250) -> Optional[pd.Series]:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty or "Close" not in df.columns:
        return None
    s = pd.to_numeric(df["Close"], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    return s.tail(window) if not s.empty else None


def compute_vol_term_structure_lead(near_vol_df: Any, far_vol_df: Any) -> Optional[float]:
    """near_vol_df=VIX (or VXN), far_vol_df=VIX3M. Positive = calm/contango
    (muted bullish lean), negative = backwardation (genuine near-term stress
    being priced in ahead of price) -- asymmetric by design, see module
    docstring."""
    near = _last_close(near_vol_df)
    far = _last_close(far_vol_df)
    if near is None or far is None:
        # Missing data is NOT "neutral". Returning 0.0 here used to make the
        # factor count as present-with-full-weight in the gatekeeper's
        # weighted average, silently dragging every SPX/NQ score toward
        # NÖTR whenever the feed was down. None = excluded from the average.
        return None
    slope_pct = (far - near) / near * 100.0
    if slope_pct < 0:
        val = np.tanh(slope_pct / 8.0)      # backwardation: steep, high-conviction stress read
    else:
        val = np.tanh(slope_pct / 25.0) * 0.5  # contango: muted, "no stress" rather than "bullish"
    return float(np.clip(val * 2.0, -2.0, 2.0))


def compute_relative_vol_premium_lead(
    asset_vol_df: Any,
    benchmark_vol_df: Any = None,
    lookback: int = 120,
    min_history: int = 20,
) -> Optional[float]:
    """Self-calibrating (no fixed magic threshold) read of whether THIS
    asset's own implied-vol pricing (and, if a benchmark is given, its
    premium/spread over that benchmark) is running hot or cold relative to
    its own recent history. Rising, historically-unusual implied vol is a
    forward-looking signal: the options market pricing a larger future move
    before it has happened."""
    level = _last_close(asset_vol_df)
    if level is None:
        return None

    series = _close_series(asset_vol_df, lookback)
    spread_now = None
    spread_series = None
    if benchmark_vol_df is not None:
        bench_series = _close_series(benchmark_vol_df, lookback)
        bench_now = _last_close(benchmark_vol_df)
        if bench_series is not None and bench_now is not None and series is not None:
            aligned = pd.concat([series.rename("a"), bench_series.rename("b")], axis=1, join="inner").dropna()
            if len(aligned) >= min_history:
                spread_series = (aligned["a"] - aligned["b"])
                spread_now = float(level - bench_now)

    def _zscore_last(hist: pd.Series, current: float) -> Optional[float]:
        if hist is None or len(hist) < min_history:
            return None
        mu = float(hist.mean())
        sd = float(hist.std(ddof=1))
        if sd <= 1e-9:
            return None
        return float((current - mu) / sd)

    level_z = _zscore_last(series, level) if series is not None else None
    spread_z = _zscore_last(spread_series, spread_now) if spread_series is not None and spread_now is not None else None

    # Combine: spread-vs-benchmark is the more specific ("this asset,
    # relative to the market") signal when available; level-only is the
    # fallback (still meaningful, just less discriminating).
    z = spread_z if spread_z is not None else level_z
    if z is None:
        # Not enough history to know what "unusual" means for this index
        # yet (e.g. CBOE SKEW prints ~1 bar per day, so a 1H feed needs
        # weeks before 20 points exist). Excluded rather than faked as 0.
        return None
    # Rising implied vol -> priced-in future risk -> treated as a bearish
    # lead (negative), consistent with compute_vol_term_structure_lead's
    # sign convention; falling implied vol (complacency) is muted, not a
    # confident bullish call.
    if z > 0:
        val = -np.tanh(z / 1.75)
    else:
        val = -np.tanh(z / 3.5) * 0.4
    return float(np.clip(val * 2.0, -2.0, 2.0))


def build_vol_history_frame(intraday_df: Any, daily_df: Any) -> Any:
    """Combines a volatility index's DAILY history (for a months-long,
    statistically meaningful norm) with its latest INTRADAY print (for a
    current reading).

    Why: z-scoring VXN/GVZ/VXSLV/SKEW against only the ~40 hourly bars the
    1H feed keeps compares today with the last few days -- that is a
    short-term momentum read of the index (reactive), not "is the options
    market pricing unusual risk versus its normal". Daily history gives the
    proper ~6-month baseline the leading-signal logic assumes.

    Point-in-time safe: only daily bars from dates strictly BEFORE the
    latest intraday bar's date are used, so today's (possibly still
    forming) daily bar never leaks into the baseline.
    """
    intraday = _close_series(intraday_df, 10_000)
    daily = _close_series(daily_df, 10_000)
    if daily is None or len(daily) < 5:
        return intraday_df if intraday is not None else pd.DataFrame()
    daily = daily.copy()
    daily.index = pd.to_datetime(daily.index, utc=True, errors="coerce")
    daily = daily[~daily.index.isna()]
    if intraday is None or intraday.empty:
        return pd.DataFrame({"Close": daily})
    intraday = intraday.copy()
    intraday.index = pd.to_datetime(intraday.index, utc=True, errors="coerce")
    intraday = intraday[~intraday.index.isna()]
    if intraday.empty:
        return pd.DataFrame({"Close": daily})
    last_ts = intraday.index[-1]
    hist = daily[daily.index.normalize() < last_ts.normalize()]
    combined = pd.concat([hist, pd.Series([float(intraday.iloc[-1])], index=[last_ts])])
    combined = combined[~combined.index.duplicated(keep="last")].sort_index()
    return pd.DataFrame({"Close": combined})
