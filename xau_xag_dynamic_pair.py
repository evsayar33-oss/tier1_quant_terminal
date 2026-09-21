"""
Dynamic XAU/XAG Relative-State Model
=====================================
Models silver as a time-varying response to gold and copper rather than using a
fixed "82% gold sympathy" coefficient.

Model (hourly returns):
    r_XAG = alpha + beta_G * r_XAU + beta_C * r_HG + epsilon

Weighted ridge regression with exponential recency weighting is used. The
residual z-score becomes the divergence evidence. Pair reconciliation is only a
small shrinkage of score disagreement when the residual does NOT support true
divergence; it never forces XAU and XAG to share a direction.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd


class DynamicXAU_XAGModel:
    def __init__(
        self,
        window: int = 120,
        half_life_hours: float = 36.0,
        ridge_strength: float = 1e-3,
    ) -> None:
        self.window = int(window)
        self.half_life_hours = max(float(half_life_hours), 1.0)
        self.ridge_strength = max(float(ridge_strength), 0.0)

    @staticmethod
    def _series(frame: Any) -> Optional[pd.Series]:
        if frame is None or not isinstance(frame, pd.DataFrame) or frame.empty:
            return None
        if "Close" not in frame.columns:
            return None
        s = pd.to_numeric(frame["Close"], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        if s.empty:
            return None
        idx = pd.to_datetime(s.index, errors="coerce", utc=True)
        s = s.copy()
        s.index = idx
        s = s[~s.index.isna()]
        return s.sort_index()

    @staticmethod
    def _get(grid: Dict[str, Any], *keys: str) -> Optional[pd.DataFrame]:
        for key in keys:
            df = grid.get(key)
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
        return None

    def _aligned_returns(self, grid: Dict[str, Any]) -> Optional[pd.DataFrame]:
        xau = self._series(self._get(grid, "GC", "GC=F", "XAU"))
        xag = self._series(self._get(grid, "SI", "SI=F", "XAG"))
        hg = self._series(self._get(grid, "HG", "HG=F"))
        if xau is None or xag is None or hg is None:
            return None
        x = pd.concat(
            [xau.rename("xau"), xag.rename("xag"), hg.rename("hg")],
            axis=1,
            join="inner",
        ).dropna()
        if len(x) < 40:
            return None
        returns = x.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
        if len(returns) < 40:
            return None
        return returns.tail(self.window)

    def fit(self, grid: Dict[str, Any]) -> Dict[str, Any]:
        returns = self._aligned_returns(grid)
        if returns is None:
            return {
                "available": False,
                "reason": "XAU/XAG/HG için yeterli eşleşmiş saatlik veri yok.",
            }

        y = returns["xag"].to_numpy(float)
        xau = returns["xau"].to_numpy(float)
        hg = returns["hg"].to_numpy(float)
        n = len(y)

        age = np.arange(n - 1, -1, -1, dtype=float)
        weights = np.exp(-np.log(2.0) * age / self.half_life_hours)
        weights = weights / max(weights.sum(), 1e-12)

        # Scale regressors by robust-ish RMS to keep the ridge penalty
        # dimensionally comparable while preserving beta interpretation.
        scale_xau = max(float(np.sqrt(np.average(xau * xau, weights=weights))), 1e-6)
        scale_hg = max(float(np.sqrt(np.average(hg * hg, weights=weights))), 1e-6)
        xs = np.column_stack([np.ones(n), xau / scale_xau, hg / scale_hg])
        w = weights[:, None]
        xtwx = xs.T @ (w * xs)
        xtwy = xs.T @ (weights * y)
        ridge = self.ridge_strength * max(float(np.trace(xtwx)), 1e-8)
        reg = np.eye(3) * ridge
        reg[0, 0] = ridge * 0.01  # almost no shrinkage on intercept

        try:
            coef_scaled = np.linalg.solve(xtwx + reg, xtwy)
        except np.linalg.LinAlgError:
            coef_scaled = np.linalg.lstsq(xtwx + reg, xtwy, rcond=None)[0]

        alpha = float(coef_scaled[0])
        beta_gold = float(coef_scaled[1] / scale_xau)
        beta_copper = float(coef_scaled[2] / scale_hg)
        predicted = alpha + beta_gold * xau + beta_copper * hg
        residual = y - predicted

        med = float(np.median(residual))
        mad = float(np.median(np.abs(residual - med)))
        robust_scale = max(1.4826 * mad, float(np.std(residual, ddof=1)) * 0.25, 1e-8)
        residual_z = float((residual[-1] - med) / robust_scale)

        corr = float(returns["xau"].corr(returns["xag"])) if n >= 5 else 0.0
        expected_xag = float(alpha + beta_gold * xau[-1] + beta_copper * hg[-1])
        observed_xag = float(y[-1])
        divergence_supported = bool(
            abs(residual_z) >= 1.75
            and abs(residual[-1]) >= 0.75 * robust_scale
        )

        if not divergence_supported and abs(residual_z) < 0.90 and corr >= 0.55:
            coherence_blend = 0.20
        elif not divergence_supported and abs(residual_z) < 1.50 and corr >= 0.45:
            coherence_blend = 0.08
        else:
            coherence_blend = 0.0

        return {
            "available": True,
            "n": int(n),
            "beta_gold": round(beta_gold, 6),
            "beta_copper": round(beta_copper, 6),
            "alpha": round(alpha, 8),
            "corr_xau_xag": round(corr, 5),
            "residual_z": round(residual_z, 4),
            "residual": round(float(residual[-1]), 8),
            "residual_scale": round(robust_scale, 8),
            "expected_xag_return": round(expected_xag, 8),
            "observed_xag_return": round(observed_xag, 8),
            "divergence_supported": divergence_supported,
            "coherence_blend": coherence_blend,
            "model": "EW_RIDGE_XAG~XAU+HG",
            "window": int(n),
            "half_life_hours": self.half_life_hours,
        }

    @staticmethod
    def reconcile_scores(
        xau_score: float,
        xag_score: float,
        pair_state: Dict[str, Any],
    ) -> Tuple[float, float]:
        """Small symmetric disagreement shrinkage; never hard-overrides direction."""
        if not pair_state.get("available"):
            return float(xau_score), float(xag_score)
        if bool(pair_state.get("divergence_supported")):
            return float(xau_score), float(xag_score)

        blend = float(np.clip(pair_state.get("coherence_blend", 0.0), 0.0, 0.25))
        if blend <= 0.0:
            return float(xau_score), float(xag_score)

        mean_score = 0.5 * (float(xau_score) + float(xag_score))
        xau_adj = (1.0 - blend) * float(xau_score) + blend * mean_score
        xag_adj = (1.0 - blend) * float(xag_score) + blend * mean_score
        return float(np.clip(xau_adj, -3.5, 3.5)), float(np.clip(xag_adj, -3.5, 3.5))
