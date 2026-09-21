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

    def profile(self, df: pd.DataFrame) -> Tuple[Optional[Dict[str, float]], Optional[str]]:
        x = self._clean(df)
        if x is None:
            return None, "Gerçek OHLC verisi yok."

        if len(x) < 2:
            return None, "Yetersiz OHLC geçmişi."

        volume = x["Volume"]
        if volume.dropna().empty or (volume.dropna() > 0).sum() < self.min_history:
            return None, "RVOL için yeterli gerçek hacim gözlemi yok."

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

        rvol_base = volume.shift(1).rolling(
            self.rvol_baseline_period,
            min_periods=self.rvol_baseline_period,
        ).mean()
        rvol = volume / (rvol_base + 1e-12)

        last_atr = float(atr_ratio.iloc[-1])
        last_rvol = float(rvol.iloc[-1])
        if not np.isfinite(last_atr) or last_atr <= 0:
            return None, "ATR oranı hesaplanamadı."
        if not np.isfinite(last_rvol) or last_rvol <= 0:
            return None, "RVOL hesaplanamadı."

        # Current bar excluded from the threshold distribution.
        ah = atr_ratio.iloc[:-1].replace([np.inf, -np.inf], np.nan).dropna().tail(self.window)
        rh = rvol.iloc[:-1].replace([np.inf, -np.inf], np.nan).dropna()
        rh = rh[rh > 0].tail(self.window)
        if len(ah) < self.min_history or len(rh) < self.min_history:
            return None, (
                f"Dinamik eşik warm-up eksik: ATR {len(ah)}/{self.min_history}, "
                f"RVOL {len(rh)}/{self.min_history}."
            )

        atr_low = float(np.quantile(ah.to_numpy(float), 0.05))
        atr_high = float(np.quantile(ah.to_numpy(float), 0.95))
        rvol_low = float(np.quantile(rh.to_numpy(float), 0.05))
        rvol_strong = float(np.quantile(rh.to_numpy(float), 0.70))
        rvol_climax = float(np.quantile(rh.to_numpy(float), 0.99))
        atr_rank = float((ah <= last_atr).mean())
        rvol_rank = float((rh <= last_rvol).mean())

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
            "history_n": float(min(len(ah), len(rh))),
        }, None

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

        profile, error = self.profile(df)
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
            "profile": profile,
            "volume_supports": bool(rvol >= profile["rvol_strong"]),
            "volatility_supports": bool(profile["atr_low"] <= atr <= profile["atr_high"]),
        }
