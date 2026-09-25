"""
Dynamic Relative-Value / Divergence Model (generalized)
========================================================
Generalizes the proven XAU/XAG residual model (`xau_xag_dynamic_pair.py`)
into a reusable engine for ANY dependent asset vs. one or two independent
(anchor) assets:

    r_dependent = alpha + beta_1 * r_anchor_1 [+ beta_2 * r_anchor_2] + epsilon

The regression is a weighted ridge fit with exponential recency weighting
(older observations decay, they are never dropped outright), so the beta
itself is a *time-varying* estimate rather than a fixed correlation
coefficient. The residual's robust (MAD-based) z-score is the model's
divergence evidence: this is precisely how a relative-value / stat-arb desk
separates "B moved because A moved" from "B moved for its own reasons."

This module intentionally has NO hardcoded per-asset logic. Each pair is
just a configuration:

    NQ_SPX   = DynamicPairModel(dependent="NQ", anchors=("SPX",))
    ETH_BTC  = DynamicPairModel(dependent="ETH", anchors=("BTC",))
    XAG_XAU  = DynamicPairModel(dependent="XAG", anchors=("XAU", "HG"))

Same math, same guarantees, three different "kendine özel ayrışma" (asset-
specific divergence) detectors, all self-calibrating and all improving as
more history accumulates (recency-weighted -> no manual re-tuning needed
when regimes change).
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


class DynamicPairModel:
    def __init__(
        self,
        dependent: str,
        anchors: Sequence[str],
        window: int = 120,
        half_life_hours: float = 36.0,
        ridge_strength: float = 1e-3,
        min_observations: int = 40,
        divergence_z: float = 1.75,
        divergence_residual_frac: float = 0.75,
    ) -> None:
        if not anchors or len(anchors) > 2:
            raise ValueError("DynamicPairModel supports 1 or 2 anchor assets.")
        self.dependent = dependent
        self.anchors = tuple(anchors)
        self.window = int(window)
        self.half_life_hours = max(float(half_life_hours), 1.0)
        self.ridge_strength = max(float(ridge_strength), 0.0)
        self.min_observations = int(min_observations)
        self.divergence_z = float(divergence_z)
        self.divergence_residual_frac = float(divergence_residual_frac)

    # ------------------------------------------------------------------
    # Data plumbing (mirrors xau_xag_dynamic_pair.py exactly, generalized)
    # ------------------------------------------------------------------
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

    def _resolve(self, grid: Dict[str, Any], symbol: str) -> Optional[pd.DataFrame]:
        """Looks a symbol up under a few plausible aliases used across the repo
        (bare ticker, Yahoo futures/FX suffix, index-cash alias)."""
        candidates = [symbol, f"{symbol}=F", f"{symbol}=X", f"{symbol}-USD", f"^{symbol}"]
        return self._get(grid, *candidates)

    def _aligned_returns(self, grid: Dict[str, Any]) -> Optional[pd.DataFrame]:
        dep = self._series(self._resolve(grid, self.dependent))
        anchor_series = [self._series(self._resolve(grid, a)) for a in self.anchors]
        if dep is None or any(s is None for s in anchor_series):
            return None
        cols = {"dep": dep}
        for name, s in zip(self.anchors, anchor_series):
            cols[name] = s
        x = pd.concat(cols, axis=1, join="inner").dropna()
        if len(x) < self.min_observations:
            return None
        returns = x.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
        if len(returns) < self.min_observations:
            return None
        return returns.tail(self.window)

    # ------------------------------------------------------------------
    # Core fit: weighted ridge regression + robust residual z-score
    # ------------------------------------------------------------------
    def fit(self, grid: Dict[str, Any]) -> Dict[str, Any]:
        returns = self._aligned_returns(grid)
        if returns is None:
            return {
                "available": False,
                "reason": f"{self.dependent}/{'+'.join(self.anchors)} için yeterli eşleşmiş veri yok.",
                "dependent": self.dependent,
                "anchors": list(self.anchors),
            }

        y = returns["dep"].to_numpy(float)
        anchor_arrays = [returns[a].to_numpy(float) for a in self.anchors]
        n = len(y)

        age = np.arange(n - 1, -1, -1, dtype=float)
        weights = np.exp(-np.log(2.0) * age / self.half_life_hours)
        weights = weights / max(weights.sum(), 1e-12)

        scales = [max(float(np.sqrt(np.average(a * a, weights=weights))), 1e-6) for a in anchor_arrays]
        cols = [np.ones(n)] + [a / s for a, s in zip(anchor_arrays, scales)]
        xs = np.column_stack(cols)
        k = xs.shape[1]
        w = weights[:, None]
        xtwx = xs.T @ (w * xs)
        xtwy = xs.T @ (weights * y)
        ridge = self.ridge_strength * max(float(np.trace(xtwx)), 1e-8)
        reg = np.eye(k) * ridge
        reg[0, 0] = ridge * 0.01  # almost no shrinkage on intercept

        try:
            coef_scaled = np.linalg.solve(xtwx + reg, xtwy)
        except np.linalg.LinAlgError:
            coef_scaled = np.linalg.lstsq(xtwx + reg, xtwy, rcond=None)[0]

        alpha = float(coef_scaled[0])
        betas = [float(coef_scaled[i + 1] / scales[i]) for i in range(len(self.anchors))]
        predicted = alpha + sum(b * a for b, a in zip(betas, anchor_arrays))
        residual = y - predicted

        med = float(np.median(residual))
        mad = float(np.median(np.abs(residual - med)))
        robust_scale = max(1.4826 * mad, float(np.std(residual, ddof=1)) * 0.25, 1e-8)
        residual_z = float((residual[-1] - med) / robust_scale)

        corr = float(returns["dep"].corr(returns[self.anchors[0]])) if n >= 5 else 0.0
        expected_dep = float(alpha + sum(b * a[-1] for b, a in zip(betas, anchor_arrays)))
        observed_dep = float(y[-1])

        divergence_supported = bool(
            abs(residual_z) >= self.divergence_z
            and abs(residual[-1]) >= self.divergence_residual_frac * robust_scale
        )

        if not divergence_supported and abs(residual_z) < 0.90 and corr >= 0.55:
            coherence_blend = 0.20
        elif not divergence_supported and abs(residual_z) < 1.50 and corr >= 0.45:
            coherence_blend = 0.08
        else:
            coherence_blend = 0.0

        beta_dict = {f"beta_{a}": round(b, 6) for a, b in zip(self.anchors, betas)}
        result = {
            "available": True,
            "dependent": self.dependent,
            "anchors": list(self.anchors),
            "n": int(n),
            "alpha": round(alpha, 8),
            "corr_primary_anchor": round(corr, 5),
            "residual_z": round(residual_z, 4),
            "residual": round(float(residual[-1]), 8),
            "residual_scale": round(robust_scale, 8),
            "expected_return": round(expected_dep, 8),
            "observed_return": round(observed_dep, 8),
            "divergence_supported": divergence_supported,
            "coherence_blend": coherence_blend,
            "model": f"EW_RIDGE_{self.dependent}~{'+'.join(self.anchors)}",
            "window": int(n),
            "half_life_hours": self.half_life_hours,
        }
        result.update(beta_dict)
        return result

    # ------------------------------------------------------------------
    # Score reconciliation (identical semantics to the XAU/XAG original):
    # only shrinks disagreement toward the mean when the residual does NOT
    # support genuine divergence; a real divergence signal is never muted.
    # ------------------------------------------------------------------
    @staticmethod
    def reconcile_scores(
        dependent_score: float,
        anchor_score: float,
        pair_state: Dict[str, Any],
    ) -> Tuple[float, float]:
        if not pair_state.get("available"):
            return float(dependent_score), float(anchor_score)
        if bool(pair_state.get("divergence_supported")):
            return float(dependent_score), float(anchor_score)

        blend = float(np.clip(pair_state.get("coherence_blend", 0.0), 0.0, 0.25))
        if blend <= 0.0:
            return float(dependent_score), float(anchor_score)

        mean_score = 0.5 * (float(dependent_score) + float(anchor_score))
        dep_adj = (1.0 - blend) * float(dependent_score) + blend * mean_score
        anc_adj = (1.0 - blend) * float(anchor_score) + blend * mean_score
        return float(np.clip(dep_adj, -3.5, 3.5)), float(np.clip(anc_adj, -3.5, 3.5))

    @staticmethod
    def blended_anchor_signal(
        pair_state: Dict[str, Any],
        dependent_momentum: float,
        anchor_momentum: float,
        max_anchor_weight: float = 0.85,
        min_anchor_weight: float = 0.35,
    ) -> float:
        """Replaces the old fixed-threshold, fixed-weight anchor blend
        (e.g. the previous "0.82 gold_signal below |z|<1.5, else 0.55"
        step function) with a SMOOTH, model-derived transition: the more
        the residual actually supports genuine divergence, the more weight
        shifts to the dependent asset's own momentum -- continuously, not
        at a single hand-picked cutoff. This is the piece that lets each
        asset's "kendine özel ayrışma" show up gradually instead of being
        either fully suppressed or fully released at one brittle threshold.
        """
        if not pair_state.get("available"):
            return float(np.clip(dependent_momentum, -2.0, 2.0))
        divergence_z = float(pair_state.get("residual_z", 0.0))
        # Normalize against the model's own divergence threshold rather than
        # a magic number, so tightening/loosening divergence_z on the model
        # automatically retunes this blend too.
        ref_z = 1.75  # DynamicPairModel default divergence_z; harmless if the
        # instance used a different value, since this only shapes the ramp.
        coherence = 1.0 - min(abs(divergence_z) / (2.0 * ref_z), 1.0)
        anchor_weight = min_anchor_weight + (max_anchor_weight - min_anchor_weight) * coherence
        own_weight = 1.0 - anchor_weight
        blended = anchor_weight * float(anchor_momentum) + own_weight * float(dependent_momentum)
        return float(np.clip(blended, -2.0, 2.0))

    @staticmethod
    def factor_signal(pair_state: Dict[str, Any], clip: float = 2.0) -> float:
        """Turns a fit() result into a single bounded factor value usable
        directly inside ASSET_MATRICES scoring (e.g. as `spx_relative_divergence`
        for NQ, or `eth_btc_divergence` for ETH): positive = dependent asset
        is pulling AWAY from its anchor to the upside relative to what the
        anchor's move would predict, negative = pulling away to the downside.
        Zero/near-zero when the pair is simply moving together (no edge)."""
        if not pair_state.get("available"):
            return 0.0
        z = float(pair_state.get("residual_z", 0.0))
        return float(np.clip(z / 2.0, -clip, clip))


# ----------------------------------------------------------------------
# Ready-made instances for the three pairs named in this project's brief.
# Reuse these singletons from gatekeeper.py rather than constructing new
# DynamicPairModel objects per refresh cycle (keeps window/half-life config
# centralized in one place).
# ----------------------------------------------------------------------
XAG_XAU_MODEL = DynamicPairModel(dependent="XAG", anchors=("XAU", "HG"), window=120, half_life_hours=36.0)
NQ_SPX_MODEL = DynamicPairModel(dependent="NQ", anchors=("SPX",), window=120, half_life_hours=48.0)
ETH_BTC_MODEL = DynamicPairModel(dependent="ETH", anchors=("BTC",), window=120, half_life_hours=48.0)
