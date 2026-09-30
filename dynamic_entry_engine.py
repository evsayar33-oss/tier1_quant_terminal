"""
Stateful Dynamic Entry Gate
===========================
Distribution-based live ATR/RVOL gate using the repository's persistent OHLCV
history. This deliberately uses a lower warm-up requirement than the existing
84-bar guard because the current repo contains ~82 real bars and the underlying
statistics need only 60 valid observations to become estimable.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd


MAX_MISSING_VOLUME_SHARE = 0.35   # v3.3.6


class StatefulDynamicEntryEngine:
    def __init__(
        self,
        window: int = 150,
        min_history: int = 45,
        atr_period: int = 14,
        atr_baseline_period: int = 20,
        rvol_baseline_period: int = 20,
    ) -> None:
        self.window = int(window)
        self.min_history = int(min_history)
        self.atr_period = int(atr_period)
        self.atr_baseline_period = int(atr_baseline_period)
        self.rvol_baseline_period = int(rvol_baseline_period)

    @staticmethod
    def _clean(df: pd.DataFrame) -> Optional[pd.DataFrame]:
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            return None
        x = df.copy()
        if isinstance(x.columns, pd.MultiIndex):
            x.columns = [c[0] if isinstance(c, tuple) else c for c in x.columns]
        x = x.loc[:, ~x.columns.duplicated(keep="last")].copy()
        for c in ("Open", "High", "Low", "Close"):
            if c not in x.columns:
                return None
            x[c] = pd.to_numeric(x[c], errors="coerce")
        if "Volume" not in x.columns:
            x["Volume"] = np.nan
        x["Volume"] = pd.to_numeric(x["Volume"], errors="coerce")
        x = x.replace([np.inf, -np.inf], np.nan).dropna(subset=["Open", "High", "Low", "Close"])
        if x.empty:
            return None
        idx = pd.to_datetime(x.index, errors="coerce", utc=True)
        x.index = idx
        x = x[~x.index.isna()]
        return x.sort_index()

    def profile(self, df: pd.DataFrame, now=None) -> Tuple[Optional[Dict[str, float]], Optional[str]]:
        x = self._clean(df)
        if x is None:
            return None, "Gerçek OHLC verisi yok."

        if len(x) < 2:
            return None, "Yetersiz OHLC geçmişi."

        # v3.3: Yahoo reports Volume=0 for many crypto/ETF hourly bars. A zero is
        # "not reported", not "no trading": treat it as missing. Otherwise a
        # 20-bar baseline of zeros made RVOL = vol / 1e-12 ~ 1e18 (live ETH/BTC
        # rvol_climax 1.6e19 -> the climax filter was silently disabled).
        volume = x["Volume"].astype(float).where(x["Volume"] > 0)
        # (v3.3.5) few reported volumes -> volume "unknown" below, ATR still valid

        h = x["High"]
        l = x["Low"]
        c = x["Close"]
        prev_close = c.shift(1)
        tr = pd.concat(
            [h - l, (h - prev_close).abs(), (l - prev_close).abs()],
            axis=1,
        ).max(axis=1)
        atr = tr.rolling(self.atr_period, min_periods=self.atr_period).mean()
        atr_baseline = atr.shift(1).rolling(
            self.atr_baseline_period,
            min_periods=self.atr_baseline_period,
        ).mean()
        atr_ratio = atr / (atr_baseline + 1e-12)

        # Partial (still-forming) last bar: project its volume to a full bar,
        # otherwise every run early in the hour looks like "no liquidity".
        rvol_base = self._seasonal_baseline(volume)   # uses shift(1): last bar never in its own base
        volume, partial_frac = self._project_partial_bar(volume, now, rvol_base)
        rvol = (volume / rvol_base.where(rvol_base > 0)).astype(float)

        volume_known = bool(np.isfinite(rvol.iloc[-1]) and rvol.iloc[-1] > 0)
        # v3.3.6: if the feed leaves most bars without volume (Yahoo crypto
        # hourly: BTC ~60% zeros, values jumping 10M <-> 5B) RVOL is not a
        # measurement -- live BTC showed a fake 10.85x. Treat as unknown.
        _recent = x["Volume"].tail(self.window)
        self_missing_share = float((~(_recent > 0)).mean()) if len(_recent) else 1.0
        if self_missing_share > MAX_MISSING_VOLUME_SHARE:
            volume_known = False
            rvol.iloc[-1] = np.nan
        if not volume_known:
            # Current bar volume not reported (crypto hourly gaps): fall back to
            # the latest reported bar within 2 bars, else volume is "unknown".
            recent = rvol.iloc[-3:-1].dropna()
            recent = recent[recent > 0]
            if not recent.empty and self_missing_share <= MAX_MISSING_VOLUME_SHARE:
                rvol.iloc[-1] = float(recent.iloc[-1])
                volume_known = True

        last_atr = float(atr_ratio.iloc[-1])
        last_rvol = float(rvol.iloc[-1]) if volume_known else float("nan")
        if not np.isfinite(last_atr) or last_atr <= 0:
            return None, "ATR oranı hesaplanamadı."

        # Current bar excluded from the threshold distribution.
        ah = atr_ratio.iloc[:-1].replace([np.inf, -np.inf], np.nan).dropna().tail(self.window)
        rh = rvol.iloc[:-1].replace([np.inf, -np.inf], np.nan).dropna()
        rh = rh[rh > 0].tail(self.window)
        if len(ah) < self.min_history:
            return None, f"Dinamik eşik warm-up eksik: ATR {len(ah)}/{self.min_history}."
        # v3.3.5: Yahoo reports volume on only ~40% of BTC hourly bars. Too few
        # RVOL observations must NOT discard the (fully valid) ATR profile --
        # that made BTC's volatility "0.00x / BİLİNMİYOR". Volume becomes
        # "unknown" instead and the gate runs on ATR alone.
        if len(rh) < self.min_history:
            volume_known = False
            rh = pd.Series([1.0] * self.min_history, dtype=float)   # neutral placeholder, never compared

        atr_low = float(np.quantile(ah.to_numpy(float), 0.05))
        atr_high = float(np.quantile(ah.to_numpy(float), 0.95))
        nanv = float("nan")
        rvol_low = float(np.quantile(rh.to_numpy(float), 0.05)) if volume_known else nanv
        rvol_strong = float(np.quantile(rh.to_numpy(float), 0.70)) if volume_known else nanv
        rvol_climax = float(np.quantile(rh.to_numpy(float), 0.99)) if volume_known else nanv
        atr_rank = float((ah <= last_atr).mean())
        rvol_rank = float((rh <= last_rvol).mean()) if volume_known else float("nan")

        return {
            "atr_ratio": last_atr,
            "rvol": last_rvol,
            "atr_low": atr_low,
            "atr_high": atr_high,
            "rvol_low": rvol_low,
            "rvol_strong": rvol_strong,
            "rvol_climax": rvol_climax,
            "atr_rank": atr_rank,
            "rvol_rank": rvol_rank,
            "history_n": float(len(ah)) if not volume_known else float(min(len(ah), len(rh))),
            "volume_known": volume_known,
            "partial_bar_fraction": partial_frac,
            "volume_missing_share": round(self_missing_share, 3),
            "rvol_method": "same-hour median (time-of-day seasonal), zero volume = missing",
        }, None

    @staticmethod
    def _bar_seconds(idx: pd.DatetimeIndex) -> float:
        if len(idx) < 3:
            return 3600.0
        d = pd.Series(idx).diff().dropna().dt.total_seconds()
        d = d[d > 0]
        return float(d.median()) if not d.empty else 3600.0

    def _project_partial_bar(self, volume: pd.Series, now, base: pd.Series) -> Tuple[pd.Series, Optional[float]]:
        """Expected full-bar volume = observed so far + remaining fraction at the
        baseline rate (shrinkage estimator; no naive x(1/frac) blow-up)."""
        v = volume.copy()
        bar = self._bar_seconds(v.index)
        if bar > 4 * 3600 or now is None:
            return v, None
        now_ts = pd.Timestamp(now)
        now_ts = now_ts.tz_localize("UTC") if now_ts.tzinfo is None else now_ts.tz_convert("UTC")
        elapsed = (now_ts - v.index[-1]).total_seconds()
        if not (0 < elapsed < bar):
            return v, None
        frac = float(elapsed / bar)
        b = float(base.iloc[-1]) if np.isfinite(base.iloc[-1]) else float("nan")
        if np.isfinite(v.iloc[-1]) and np.isfinite(b):
            v.iloc[-1] = float(v.iloc[-1]) + (1.0 - frac) * b
        return v, round(frac, 3)

    def _seasonal_baseline(self, volume: pd.Series) -> pd.Series:
        """Median volume of the SAME hour-of-day over the previous ~10 sessions
        (futures volume is 5-20x higher in the US session than in Asia; a plain
        20-bar mean flags every Asian bar as 'illiquid' and every US open as a
        'climax'). Falls back to a robust positive-only rolling median."""
        prev = volume.shift(1)
        fallback = prev.rolling(self.rvol_baseline_period, min_periods=max(5, self.rvol_baseline_period // 2)).median()
        bar = self._bar_seconds(volume.index)
        if bar > 2 * 3600:
            return fallback
        hours = volume.index.hour
        seasonal = volume.groupby(hours).transform(
            lambda s: s.shift(1).rolling(10, min_periods=5).median()
        )
        return seasonal.where(seasonal.notna(), fallback)

    def evaluate(self, df: pd.DataFrame, require_live: bool = True) -> Dict[str, Any]:
        attrs = getattr(df, "attrs", {}) or {}
        if require_live:
            if attrs.get("is_real") is not True or attrs.get("source_type") != "DIRECT":
                return {
                    "allowed": False,
                    "reason": "DIRECT/gerçek veri koşulu sağlanmadı.",
                    "profile": None,
                    "volume_supports": False,
                    "volatility_supports": False,
                }
            if attrs.get("status") != "LIVE" or attrs.get("execution_eligible") is not True:
                return {
                    "allowed": False,
                    "reason": "Veri LIVE/execution-eligible değil.",
                    "profile": None,
                    "volume_supports": False,
                    "volatility_supports": False,
                }

        now = attrs.get("as_of_utc") or attrs.get("fetched_at_utc")
        if now is None:
            try:
                from system_clock import now_utc
                now = now_utc()
            except Exception:
                now = None
        profile, error = self.profile(df, now=now)
        if profile is None:
            return {
                "allowed": False,
                "reason": error or "Dinamik giriş profili hesaplanamadı.",
                "profile": None,
                "volume_supports": False,
                "volatility_supports": False,
            }

        atr = profile["atr_ratio"]
        rvol = profile["rvol"]
        if atr > profile["atr_high"]:
            reason = (
                f"Dinamik yüksek volatilite: ATR {atr:.2f}x, "
                f"P{profile['atr_rank']*100:.0f}; üst sınır {profile['atr_high']:.2f}x."
            )
            allowed = False
        elif atr < profile["atr_low"]:
            reason = (
                f"Dinamik düşük volatilite: ATR {atr:.2f}x, "
                f"P{profile['atr_rank']*100:.0f}; alt sınır {profile['atr_low']:.2f}x."
            )
            allowed = False
        elif not profile.get("volume_known", True):
            reason = (
                f"Dinamik giriş uygun (hacim raporlanmadı; yalnız ATR): ATR {atr:.2f}x "
                f"(P{profile['atr_rank']*100:.0f}), n={int(profile['history_n'])}."
            )
            allowed = True
        elif rvol < profile["rvol_low"]:
            reason = (
                f"Dinamik düşük likidite: RVOL {rvol:.2f}x, "
                f"P{profile['rvol_rank']*100:.0f}; alt sınır {profile['rvol_low']:.2f}x."
            )
            allowed = False
        elif rvol > profile["rvol_climax"]:
            reason = (
                f"Dinamik hacim climax: RVOL {rvol:.2f}x, "
                f"P{profile['rvol_rank']*100:.0f}; üst sınır {profile['rvol_climax']:.2f}x."
            )
            allowed = False
        else:
            reason = (
                f"Dinamik giriş uygun: ATR {atr:.2f}x (P{profile['atr_rank']*100:.0f}), "
                f"RVOL {rvol:.2f}x (P{profile['rvol_rank']*100:.0f}), "
                f"n={int(profile['history_n'])}."
            )
            allowed = True

        return {
            "allowed": bool(allowed),
            "reason": reason,
            "profile": {k: (None if isinstance(v, float) and not np.isfinite(v) else v) for k, v in profile.items()},
            "volume_supports": bool(np.isfinite(rvol) and rvol >= profile["rvol_strong"]),
            "volatility_supports": bool(profile["atr_low"] <= atr <= profile["atr_high"]),
        }
