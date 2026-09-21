"""
Adaptive Score Model
====================
Turns the deterministic factor matrix into a stateful adaptive model without
changing the original factor definitions.

Two distinct adaptation channels are maintained:
1) factor reliability -> dynamic multiplicative weight adjustments
2) score outcome distribution -> empirical entry/exit thresholds

Both are exponentially decayed and heavily shrunk toward the configured base
model, preventing small samples from rewriting the model.
"""

from __future__ import annotations

import math
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from config import ASSET_MATRICES, REGIME_DYNAMIC_THRESHOLDS
from stateful_memory_store import MAX_SCORE_BINS, SCORE_MAX, StatefulMemoryStore


ENTRY_MIN = 0.45
ENTRY_MAX = 2.50
STRONG_MIN = 1.10
STRONG_MAX = 3.20
MIN_EFFECTIVE_SAMPLES = 30.0
TARGET_LCB = 0.50


class AdaptiveScoreModel:
    def __init__(self, store: StatefulMemoryStore) -> None:
        self.store = store

    @staticmethod
    def _as_regime_key(regime_id: Any) -> Any:
        try:
            if isinstance(regime_id, str) and regime_id.strip().isdigit():
                return int(regime_id.strip())
            return int(regime_id)
        except (TypeError, ValueError):
            return "REJIMSIZ_GECIS"

    @staticmethod
    def _base_thresholds(regime_id: Any) -> Dict[str, Any]:
        key = AdaptiveScoreModel._as_regime_key(regime_id)
        return deepcopy(REGIME_DYNAMIC_THRESHOLDS.get(key, REGIME_DYNAMIC_THRESHOLDS["REJIMSIZ_GECIS"]))

    def factor_weight_map(self, asset_key: str) -> Dict[str, Dict[str, float]]:
        matrix = ASSET_MATRICES.get(asset_key, {})
        result: Dict[str, Dict[str, float]] = {}
        for factor in matrix.get("factors", []):
            fid = str(factor["id"])
            result[fid] = self.store.factor_weight_multiplier(asset_key, fid)
        return result

    def _adaptive_candidate_threshold(
        self,
        asset: str,
        regime_id: Any,
        direction: str,
        baseline: float,
    ) -> Tuple[float, Dict[str, float]]:
        # Candidate thresholds are aligned to the score grid, avoiding fragile
        # optimisation over hundreds of arbitrary parameter values.
        width = SCORE_MAX / MAX_SCORE_BINS
        candidates = [max(ENTRY_MIN, round(i * width, 6)) for i in range(4, MAX_SCORE_BINS)]

        best: Optional[Dict[str, float]] = None
        best_rank = (-1.0, -1.0, -1.0)

        for threshold in candidates:
            stats = self.store.score_calibration_snapshot(
                asset=asset,
                regime_id=regime_id,
                direction=direction,
                min_abs_score=threshold,
            )
            n = stats["effective_n"]
            if n <= 0:
                continue

            # Prefer statistically supported thresholds. Return quality is a
            # secondary criterion; we deliberately do not maximise raw return.
            lcb = stats["wilson_lower"]
            mean_ret = stats["return_mean"]
            sample_quality = min(n / 120.0, 1.0)
            risk_adjusted_quality = lcb + 0.20 * math.tanh(mean_ret * 100.0)
            rank = (
                1.0 if (n >= MIN_EFFECTIVE_SAMPLES and lcb >= TARGET_LCB and mean_ret > 0.0) else 0.0,
                risk_adjusted_quality,
                float(threshold),
                sample_quality,
            )
            if rank > best_rank:
                best_rank = rank
                best = stats

        if best is None:
            return float(baseline), {
                "adaptive": 0.0,
                "effective_n": 0.0,
                "wilson_lower": 0.0,
                "return_mean": 0.0,
            }

        selected = float(np.clip(best["threshold"], ENTRY_MIN, ENTRY_MAX))
        n_eff = float(best["effective_n"])
        # Empirical influence rises gradually; it never fully replaces the
        # regime prior. With 120+ effective observations the blend is 65%.
        data_blend = float(np.clip((n_eff - 15.0) / 160.0, 0.0, 0.65))
        adaptive = (1.0 - data_blend) * float(baseline) + data_blend * selected
        adaptive = float(np.clip(adaptive, ENTRY_MIN, ENTRY_MAX))
        return adaptive, {
            "adaptive": data_blend,
            "effective_n": n_eff,
            "wilson_lower": float(best["wilson_lower"]),
            "return_mean": float(best["return_mean"]),
            "hit_rate": float(best["hit_rate"]),
            "selected_threshold": selected,
        }

    def dynamic_thresholds(self, asset_key: str, regime_id: Any) -> Dict[str, Any]:
        base = self._base_thresholds(regime_id)
        long_base = float(base.get("buy_enter", 0.75))
        short_base = abs(float(base.get("sell_enter", -0.75)))

        long_enter, long_meta = self._adaptive_candidate_threshold(
            asset_key, regime_id, "long", long_base
        )
        short_enter, short_meta = self._adaptive_candidate_threshold(
            asset_key, regime_id, "short", short_base
        )

        long_exit = float(np.clip(long_enter * 0.42, 0.20, max(long_enter - 0.05, 0.20)))
        short_exit = -float(np.clip(short_enter * 0.42, 0.20, max(short_enter - 0.05, 0.20)))

        base_strong_long = float(base.get("strong_buy_enter", 1.70))
        base_strong_short = abs(float(base.get("strong_sell_enter", -1.70)))
        strong_long = float(np.clip(max(base_strong_long, long_enter * 1.60), STRONG_MIN, STRONG_MAX))
        strong_short = float(np.clip(max(base_strong_short, short_enter * 1.60), STRONG_MIN, STRONG_MAX))

        return {
            **base,
            "buy_enter": round(long_enter, 4),
            "buy_exit": round(long_exit, 4),
            "sell_enter": round(-short_enter, 4),
            "sell_exit": round(short_exit, 4),
            "strong_buy_enter": round(strong_long, 4),
            "strong_sell_enter": round(-strong_short, 4),
            "adaptive": True,
            "adaptive_model": "EWMA_FACTOR_IC + SCORE_BIN_WILSON",
            "long_calibration": long_meta,
            "short_calibration": short_meta,
        }

    def recompute_score(
        self,
        asset_key: str,
        detail_rows: List[Dict[str, Any]],
        cluster_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        matrix = ASSET_MATRICES.get(asset_key, {})
        weight_map = self.factor_weight_map(asset_key)
        by_name = {
            str(row.get("faktör")): row
            for row in detail_rows
            if isinstance(row, dict)
        }

        weighted_sum = 0.0
        total_weight = 0.0
        cluster_scores: Dict[str, float] = {}
        factor_runtime: Dict[str, Dict[str, Any]] = {}

        for factor in matrix.get("factors", []):
            fid = str(factor["id"])
            fname = str(factor["name"])
            row = by_name.get(fname)
            if row is None:
                continue
            raw = row.get("ham_deger")
            try:
                raw_f = float(raw)
            except (TypeError, ValueError):
                continue
            if not np.isfinite(raw_f):
                continue

            raw_f = float(np.clip(raw_f, -1.8, 1.8))
            sign = float(factor.get("base_sign", 1.0))
            base_weight = float(factor.get("base_weight", 0.0))
            multiplier = float(weight_map.get(fid, {}).get("multiplier", 1.0))
            effective_weight = base_weight * multiplier
            signed = raw_f * sign
            contribution = signed * effective_weight

            weighted_sum += contribution
            total_weight += effective_weight
            cluster = str(factor.get("cluster", "UNKNOWN"))
            cluster_scores[cluster] = cluster_scores.get(cluster, 0.0) + contribution
            factor_runtime[fid] = {
                "name": fname,
                "raw_value": round(raw_f, 6),
                "base_weight": base_weight,
                "base_sign": sign,
                "weight_multiplier": multiplier,
                "effective_weight": effective_weight,
                "ic": weight_map.get(fid, {}).get("ic", 0.0),
                "factor_n": weight_map.get(fid, {}).get("n", 0.0),
            }

        if total_weight <= 0.0:
            score = 0.0
        else:
            score = float(np.clip((weighted_sum / total_weight) * 1.5, -3.5, 3.5))

        active_clusters = [c for c, sc in cluster_scores.items() if abs(sc) > 0.15]
        bull_clusters = sum(1 for sc in cluster_scores.values() if sc > 0.20)
        bear_clusters = sum(1 for sc in cluster_scores.values() if sc < -0.20)

        return {
            "score": round(score, 4),
            "weighted_sum": round(weighted_sum, 6),
            "total_weight": round(total_weight, 6),
            "cluster_scores": {k: round(v, 6) for k, v in cluster_scores.items()},
            "active_clusters": active_clusters,
            "bull_clusters": bull_clusters,
            "bear_clusters": bear_clusters,
            "factor_runtime": factor_runtime,
            "weight_map": weight_map,
        }

    @staticmethod
    def resolve_signal(
        score: float,
        thresholds: Dict[str, Any],
        previous_signal: str,
        bull_clusters: int,
        bear_clusters: int,
        entry_allowed: bool,
        volume_supports: bool,
        volatility_supports: bool,
        market_regime: str = "",
    ) -> Tuple[str, str, str]:
        prev = str(previous_signal or "NÖTR (BEKLE)")
        buy_enter = float(thresholds.get("buy_enter", 0.75))
        sell_enter = float(thresholds.get("sell_enter", -0.75))
        buy_exit = float(thresholds.get("buy_exit", 0.30))
        sell_exit = float(thresholds.get("sell_exit", -0.30))
        strong_buy = float(thresholds.get("strong_buy_enter", 1.70))
        strong_sell = float(thresholds.get("strong_sell_enter", -1.70))
        req_clusters = int(thresholds.get("min_clusters", 2))

        base_dir = "NÖTR (BEKLE)"
        if prev in ("AL", "GÜÇLÜ AL", "AL (Hacim/Volatilite Teyitsiz)") and score > buy_exit:
            base_dir = "AL"
        elif score >= buy_enter and bull_clusters >= req_clusters and entry_allowed:
            base_dir = "AL"

        if prev in ("SAT", "GÜÇLÜ SAT", "SAT (Hacim/Volatilite Teyitsiz)") and score < sell_exit:
            base_dir = "SAT"
        elif score <= sell_enter and bear_clusters >= req_clusters and entry_allowed:
            base_dir = "SAT"

        choppy = (
            "DENGE" in market_regime
            or "SIKIŞMA" in market_regime
            or "REJİMSİZ" in market_regime
        )

        if base_dir == "AL":
            strong = score >= strong_buy and entry_allowed and volume_supports and volatility_supports
            if strong:
                return "GÜÇLÜ AL", "green", "🟢🟢"
            if score >= strong_buy and not (volume_supports and volatility_supports):
                return "AL (Hacim/Volatilite Teyitsiz)", "lightgreen", "🟢"
            return "AL", "lightgreen", "🟢"

        if base_dir == "SAT":
            strong = score <= strong_sell and entry_allowed and volume_supports and volatility_supports
            if strong:
                return "GÜÇLÜ SAT", "darkred", "🔴🔴"
            if score <= strong_sell and not (volume_supports and volatility_supports):
                return "SAT (Hacim/Volatilite Teyitsiz)", "red", "🔴"
            return "SAT", "red", "🔴"

        if not entry_allowed and abs(score) >= buy_enter:
            return "NÖTR (GİRİŞ GATE BLOKLU)", "gray", "⚪"
        return ("NÖTR (TESTERE BANDI)" if choppy and abs(score) > 0.40 else "NÖTR (BEKLE)"), "gray", "⚪"
