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

        long_cal = self.store.direction_calibration_snapshot(asset_key, regime_id, "long", horizon="1")
        short_cal = self.store.direction_calibration_snapshot(asset_key, regime_id, "short", horizon="1")
        long_confirm = self.store.score_calibration_snapshot(asset_key, regime_id, "long", min_abs_score=0.45)
        short_confirm = self.store.score_calibration_snapshot(asset_key, regime_id, "short", min_abs_score=0.45)

        def early_outcome_adjustment(cal: Dict[str, float]) -> float:
            n = float(cal.get("effective_n", 0.0))
            if n < 12.0:
                return 1.0
            lcb = float(cal.get("wilson_lower", 0.0))
            if lcb < 0.45:
                return float(1.0 + min((0.45 - lcb) * 0.70, 0.15))
            if lcb > 0.60:
                return float(1.0 - min((lcb - 0.60) * 0.50, 0.10))
            return 1.0

        early_adj_long = early_outcome_adjustment(long_cal)
        early_adj_short = early_outcome_adjustment(short_cal)
        long_enter, long_meta = self._adaptive_candidate_threshold(asset_key, regime_id, "long", long_base)
        short_enter, short_meta = self._adaptive_candidate_threshold(asset_key, regime_id, "short", short_base)

        early_long = float(np.clip(long_enter * 0.72 * early_adj_long, 0.30, min(long_enter - 0.10, 1.20)))
        early_short = float(np.clip(short_enter * 0.72 * early_adj_short, 0.30, min(short_enter - 0.10, 1.20)))

        # Outcome-calibrated confirmation cannot become easier than the early
        # layer. The two barriers remain separated to reduce churn.
        long_enter = float(np.clip(max(long_enter, early_long + 0.12), 0.52, 1.85))
        short_enter = float(np.clip(max(short_enter, early_short + 0.12), 0.52, 1.85))

        long_exit = float(np.clip(long_enter * 0.42, 0.18, 1.10))
        short_exit = -float(np.clip(short_enter * 0.42, 0.18, 1.10))

        base_strong_long = float(base.get("strong_buy_enter", 1.70))
        base_strong_short = abs(float(base.get("strong_sell_enter", -1.70)))
        strong_long = float(np.clip(max(base_strong_long, long_enter * 1.55), 1.15, 3.20))
        strong_short = float(np.clip(max(base_strong_short, short_enter * 1.55), 1.15, 3.20))

        return {
            **base,
            "buy_enter": round(long_enter, 4),
            "buy_exit": round(long_exit, 4),
            "sell_enter": round(-short_enter, 4),
            "sell_exit": round(short_exit, 4),
            "buy_early": round(early_long, 4),
            "sell_early": round(-early_short, 4),
            "early_exit": round(float(np.clip(min(early_long, early_short) * 0.30, 0.18, 0.70)), 4),
            "strong_buy_enter": round(strong_long, 4),
            "strong_sell_enter": round(-strong_short, 4),
            "min_clusters": int(base.get("min_clusters", 2)),
            "adaptive": True,
            "adaptive_model": "BOUNDED_DIRECTION + SCORE_BIN_WILSON + 1H_OUTCOME",
            "long_calibration": long_meta,
            "short_calibration": short_meta,
            "early_outcome_adjustment": {
                "long": round(early_adj_long, 6),
                "short": round(early_adj_short, 6),
                "long_1h": long_cal,
                "short_1h": short_cal,
                "confirm_4h": {"long": long_confirm, "short": short_confirm},
            },
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

        configured_weight = float(sum(float(f.get("base_weight", 0.0)) for f in matrix.get("factors", [])))
        weighted_sum = 0.0
        total_weight = 0.0
        cluster_scores: Dict[str, float] = {}
        factor_runtime: Dict[str, Dict[str, Any]] = {}
        contributions: Dict[str, float] = {}
        valid_base_weight = 0.0

        for factor in matrix.get("factors", []):
            fid = str(factor["id"])
            fname = str(factor["name"])
            row = by_name.get(fname)
            if row is None:
                continue

            data_status = str(row.get("veri_durumu", "MEVCUT"))
            if data_status.upper().startswith("VERİ YETERSİZ"):
                factor_runtime[fid] = {
                    "name": fname,
                    "status": "MISSING",
                    "raw_value": None,
                    "base_weight": float(factor.get("base_weight", 0.0)),
                    "weight_multiplier": 0.0,
                    "effective_weight": 0.0,
                    "ic": 0.0,
                    "factor_n": 0.0,
                }
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
            multiplier_node = weight_map.get(fid, {})
            multiplier = float(multiplier_node.get("multiplier", 1.0)) if isinstance(multiplier_node, dict) else 1.0
            effective_weight = base_weight * max(multiplier, 0.0)
            signed = raw_f * sign
            contribution = signed * effective_weight

            contributions[fid] = contribution
            valid_base_weight += base_weight
            total_weight += effective_weight
            cluster = str(factor.get("cluster", "UNKNOWN"))
            cluster_scores[cluster] = cluster_scores.get(cluster, 0.0) + contribution
            factor_runtime[fid] = {
                "name": fname,
                "status": data_status,
                "raw_value": round(raw_f, 6),
                "base_weight": base_weight,
                "base_sign": sign,
                "weight_multiplier": multiplier,
                "effective_weight": effective_weight,
                "ic": multiplier_node.get("ic", 0.0) if isinstance(multiplier_node, dict) else 0.0,
                "factor_n": multiplier_node.get("n", 0.0) if isinstance(multiplier_node, dict) else 0.0,
            }

        # XAG: prevent multiple correlated relative-value factors from acting as
        # independent votes for the same move. Their combined contribution is
        # capped to a bounded share of total factor magnitude.
        if asset_key == "XAG" and contributions:
            relative_ids = {
                "gold_sympathy",
                "silver_monetary_catchup",
                "copper_gold",
                "silver_copper",
            }
            rel_ids = [fid for fid in relative_ids if fid in contributions]
            rel_abs = float(sum(abs(contributions[fid]) for fid in rel_ids))
            other_abs = float(sum(abs(v) for fid, v in contributions.items() if fid not in relative_ids))
            cap_fraction = 0.30
            cap_abs = cap_fraction * max(other_abs, 1e-12)
            if rel_abs > cap_abs and cap_abs > 0.0:
                scale = cap_abs / rel_abs
                for fid in rel_ids:
                    old = contributions[fid]
                    contributions[fid] = old * scale
                    factor_runtime.setdefault(fid, {})["relative_group_scale"] = round(scale, 6)

        # Rebuild total contribution after any XAG relative-value cap.
        weighted_sum = 0.0
        cluster_scores = {}
        for factor in matrix.get("factors", []):
            fid = str(factor["id"])
            if fid not in contributions:
                continue
            contrib = contributions[fid]
            weighted_sum += contrib
            cluster = str(factor.get("cluster", "UNKNOWN"))
            cluster_scores[cluster] = cluster_scores.get(cluster, 0.0) + contrib
            if fid in factor_runtime:
                factor_runtime[fid]["final_contribution"] = round(contrib, 6)

        coverage = valid_base_weight / max(configured_weight, 1e-12)
        if total_weight <= 0.0 or coverage < 0.45:
            score = 0.0
            score_confidence = "INSUFFICIENT_DATA"
        else:
            score = float(np.clip((weighted_sum / total_weight) * 1.5, -3.5, 3.5))
            score_confidence = "HIGH" if coverage >= 0.75 else "MEDIUM"
            if coverage < 0.60:
                score *= float(np.clip(coverage / 0.60, 0.70, 1.0))
                score_confidence = "LOW"

        active_clusters = [c for c, sc in cluster_scores.items() if abs(sc) > 0.15]
        bull_clusters = sum(1 for sc in cluster_scores.values() if sc > 0.20)
        bear_clusters = sum(1 for sc in cluster_scores.values() if sc < -0.20)

        return {
            "score": round(float(score), 4),
            "weighted_sum": round(weighted_sum, 6),
            "total_weight": round(total_weight, 6),
            "configured_weight": round(configured_weight, 6),
            "valid_base_weight": round(valid_base_weight, 6),
            "data_coverage": round(float(coverage), 4),
            "data_confidence": score_confidence,
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
        previous_signal: str = "NÖTR (BEKLE)",
        bull_clusters: int = 0,
        bear_clusters: int = 0,
        entry_allowed: bool = True,
        volume_supports: bool = False,
        volatility_supports: bool = False,
        market_regime: str = "",
    ) -> Tuple[str, str, str]:
        """Backward-compatible wrapper. Direction no longer depends on entry_allowed."""
        s = float(score)
        prev = str(previous_signal or "NÖTR (BEKLE)")
        buy = float(thresholds.get("buy_enter", 0.75))
        sell = float(thresholds.get("sell_enter", -0.75))
        buy_exit = float(thresholds.get("buy_exit", 0.30))
        sell_exit = float(thresholds.get("sell_exit", -0.30))
        req = int(thresholds.get("min_clusters", 2))
        if s >= buy and bull_clusters >= req:
            return ("GÜÇLÜ AL" if s >= float(thresholds.get("strong_buy_enter", 1.70)) else "AL", "green", "🟢🟢" if s >= float(thresholds.get("strong_buy_enter", 1.70)) else "🟢")
        if s <= sell and bear_clusters >= req:
            return ("GÜÇLÜ SAT" if s <= float(thresholds.get("strong_sell_enter", -1.70)) else "SAT", "darkred" if s <= float(thresholds.get("strong_sell_enter", -1.70)) else "red", "🔴🔴" if s <= float(thresholds.get("strong_sell_enter", -1.70)) else "🔴")
        if "AL" in prev and "SAT" not in prev and s > buy_exit:
            return "AL", "lightgreen", "🟢"
        if "SAT" in prev and "AL" not in prev and s < sell_exit:
            return "SAT", "red", "🔴"
        return "NÖTR (BEKLE)", "gray", "⚪"
