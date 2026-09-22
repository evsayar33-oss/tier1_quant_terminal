"""
Stateful Direction Engine v3.1
==============================
Bounded live direction state machine. Execution permission is never an input.

Stages:
    NEUTRAL -> EARLY -> CONFIRMED
                 -> HELD (hysteresis)

The threshold surface comes from AdaptiveScoreModel. This engine adds only
short-horizon live adaptation from score velocity, acceleration, persistence,
and score dispersion.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import numpy as np

from stateful_memory_store import StatefulMemoryStore

EARLY_MIN = 0.30
EARLY_MAX = 1.25
CONFIRM_MIN = 0.52
CONFIRM_MAX = 1.90
EXIT_MIN = 0.18
EXIT_MAX = 1.10
MAX_RUNTIME_SAMPLES = 12
EARLY_PERSISTENCE_REQUIRED = 2
CONFIRM_PERSISTENCE_REQUIRED = 2


class StatefulDirectionEngine:
    """Direction state machine with bounded live threshold modulation."""

    def __init__(self, store: StatefulMemoryStore) -> None:
        self.store = store

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _finite(value: Any, default: float = 0.0) -> float:
        try:
            x = float(value)
            return x if np.isfinite(x) else default
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _side(score: float) -> str:
        if score > 0.0:
            return "LONG"
        if score < 0.0:
            return "SHORT"
        return "NEUTRAL"

    def _get_runtime(self, asset: str, regime_id: Any) -> Dict[str, Any]:
        return self.store.get_direction_runtime(asset, regime_id)

    def _score_z_before_update(self, score: float, runtime: Dict[str, Any]) -> float:
        n = self._finite(runtime.get("n"))
        mean = self._finite(runtime.get("mean_score"))
        variance = max(self._finite(runtime.get("variance_score")), 0.0)
        if n < 5.0:
            return 0.0
        sd = math.sqrt(variance)
        if sd <= 1e-9:
            return 0.0
        return float((score - mean) / sd)

    def _update_runtime(
        self,
        asset: str,
        regime_id: Any,
        score: float,
        candidate_side: str,
        now: datetime,
    ) -> Dict[str, Any]:
        state = self._get_runtime(asset, regime_id)
        samples = list(state.get("recent_scores", []))
        previous_score = self._finite(state.get("last_score"), 0.0) if samples else None
        previous_update = state.get("last_update_at")

        elapsed_h = 0.5
        if previous_update:
            try:
                dt = datetime.fromisoformat(str(previous_update).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                elapsed_h = max((now - dt).total_seconds() / 3600.0, 1.0 / 120.0)
            except (TypeError, ValueError):
                elapsed_h = 0.5

        velocity = 0.0 if previous_score is None else (score - previous_score) / elapsed_h
        previous_velocity = self._finite(state.get("last_velocity"), 0.0)
        acceleration = 0.0 if previous_score is None else (velocity - previous_velocity) / elapsed_h

        old_n = self._finite(state.get("n"), 0.0)
        old_mean = self._finite(state.get("mean_score"), 0.0)
        old_var = max(self._finite(state.get("variance_score"), 0.0), 0.0)
        alpha = float(np.clip(1.0 - math.exp(-math.log(2.0) * elapsed_h / self.store.half_life_hours), 0.005, 0.50))

        if old_n <= 0.0:
            new_mean, new_var, new_n = score, 0.0, 1.0
        else:
            delta = score - old_mean
            new_mean = old_mean + alpha * delta
            new_var = max((1.0 - alpha) * (old_var + alpha * delta * delta), 0.0)
            new_n = min(old_n + 1.0, 500.0)

        samples.append({
            "ts": now.astimezone(timezone.utc).isoformat(),
            "score": float(score),
            "side": candidate_side,
        })
        samples = samples[-MAX_RUNTIME_SAMPLES:]
        persistence = 0
        if candidate_side != "NEUTRAL":
            for item in reversed(samples):
                if str(item.get("side")) == candidate_side:
                    persistence += 1
                else:
                    break

        updated = {
            "n": float(new_n),
            "mean_score": float(new_mean),
            "variance_score": float(new_var),
            "last_score": float(score),
            "last_velocity": float(velocity),
            "last_acceleration": float(acceleration),
            "last_update_at": now.astimezone(timezone.utc).isoformat(),
            "same_side_persistence": int(persistence),
            "recent_scores": samples,
        }
        self.store.set_direction_runtime(asset, regime_id, updated)
        return updated

    @staticmethod
    def _effective_thresholds(
        thresholds: Dict[str, Any],
        score_z: float,
        velocity: float,
        acceleration: float,
        direction: str,
    ) -> Dict[str, Any]:
        out = dict(thresholds)
        if direction not in ("LONG", "SHORT"):
            direction = "LONG"

        favorable_v = velocity > 0.0 if direction == "LONG" else velocity < 0.0
        favorable_a = acceleration > 0.0 if direction == "LONG" else acceleration < 0.0
        v_strength = float(np.clip(abs(velocity) / 0.20, 0.0, 1.0))
        z_strength = float(np.clip(abs(score_z) / 2.0, 0.0, 1.0))

        early_key = "buy_early" if direction == "LONG" else "sell_early"
        confirm_key = "buy_enter" if direction == "LONG" else "sell_enter"
        early_sign = 1.0 if direction == "LONG" else -1.0

        early = abs(float(out.get(early_key, 0.50)))
        confirm = abs(float(out.get(confirm_key, 0.75)))

        # Favorable live momentum may lower the early barrier modestly; adverse
        # momentum raises it. Confirmation moves less, preserving false-positive
        # protection. Acceleration contributes only a small second-order effect.
        if favorable_v:
            early *= 1.0 - 0.10 * v_strength
            confirm *= 1.0 - 0.035 * v_strength
        else:
            early *= 1.0 + 0.10 * v_strength
            confirm *= 1.0 + 0.04 * v_strength
        if favorable_a:
            early *= 1.0 - 0.04 * z_strength
        elif abs(acceleration) > 0.02:
            early *= 1.0 + 0.04 * z_strength

        if (direction == "LONG" and score_z > 0.55) or (direction == "SHORT" and score_z < -0.55):
            early *= 1.0 - 0.04 * z_strength

        early = float(np.clip(early, EARLY_MIN, EARLY_MAX))
        confirm = float(np.clip(max(confirm, early + 0.12), CONFIRM_MIN, CONFIRM_MAX))
        if direction == "LONG":
            out[early_key] = round(early, 4)
            out[confirm_key] = round(confirm, 4)
            out["buy_exit"] = round(float(np.clip(confirm * 0.42, EXIT_MIN, EXIT_MAX)), 4)
        else:
            out[early_key] = round(-early, 4)
            out[confirm_key] = round(-confirm, 4)
            out["sell_exit"] = round(-float(np.clip(confirm * 0.42, EXIT_MIN, EXIT_MAX)), 4)
        out["live_velocity_adjustment"] = round((early / max(abs(float(thresholds.get(early_key, early_sign * early))), 1e-9)) - 1.0, 6)
        out["score_z"] = round(score_z, 4)
        out["velocity"] = round(velocity, 6)
        out["acceleration"] = round(acceleration, 6)
        return out

    def evaluate(
        self,
        asset: str,
        regime_id: Any,
        score: float,
        bull_clusters: int,
        bear_clusters: int,
        thresholds: Dict[str, Any],
        previous_signal: str = "NÖTR (BEKLE)",
        now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        current = now or self._now()
        score = float(np.clip(self._finite(score), -3.5, 3.5))
        previous_runtime = self._get_runtime(asset, regime_id)
        previous_n = self._finite(previous_runtime.get("n"), 0.0)
        previous_score_available = previous_n > 0.0 and bool(previous_runtime.get("recent_scores"))
        score_z = self._score_z_before_update(score, previous_runtime)
        side = self._side(score)
        runtime = self._update_runtime(asset, regime_id, score, side, current)
        velocity = self._finite(runtime.get("last_velocity"))
        acceleration = self._finite(runtime.get("last_acceleration"))
        persistence = int(runtime.get("same_side_persistence", 0))

        effective = self._effective_thresholds(thresholds, score_z, velocity, acceleration, side)
        if side == "LONG":
            early_thr = abs(float(effective.get("buy_early", 0.50)))
            confirm_thr = abs(float(effective.get("buy_enter", 0.75)))
            cluster_count = int(bull_clusters)
            favorable_velocity = velocity > 0.0
            unfavorable_accel = acceleration < -0.02
        elif side == "SHORT":
            early_thr = abs(float(effective.get("sell_early", -0.50)))
            confirm_thr = abs(float(effective.get("sell_enter", -0.75)))
            cluster_count = int(bear_clusters)
            favorable_velocity = velocity < 0.0
            unfavorable_accel = acceleration > 0.02
        else:
            early_thr = confirm_thr = 999.0
            cluster_count = 0
            favorable_velocity = False
            unfavorable_accel = False

        min_clusters = max(int(effective.get("min_clusters", 2)), 1)
        cluster_ok = cluster_count >= min_clusters
        velocity_support = favorable_velocity and abs(velocity) >= 0.08
        z_support = score_z >= 0.55 if side == "LONG" else score_z <= -0.55 if side == "SHORT" else False
        strong_impulse = abs(score) >= confirm_thr * 1.18 and cluster_ok and not unfavorable_accel
        moderate = abs(score) >= early_thr and cluster_ok

        early = bool(
            side != "NEUTRAL"
            and moderate
            and (persistence >= EARLY_PERSISTENCE_REQUIRED or velocity_support or z_support or strong_impulse)
            and not (unfavorable_accel and not strong_impulse)
        )
        confirmed = bool(
            side != "NEUTRAL"
            and abs(score) >= confirm_thr
            and cluster_ok
            and (persistence >= CONFIRM_PERSISTENCE_REQUIRED or strong_impulse)
            and not (unfavorable_accel and not strong_impulse)
        )

        prev = str(previous_signal or "NÖTR (BEKLE)")
        prev_long = "AL" in prev and "SAT" not in prev
        prev_short = "SAT" in prev and "AL" not in prev
        hold = (prev_long and score > float(effective.get("buy_exit", 0.30)) and side != "SHORT") or (
            prev_short and score < float(effective.get("sell_exit", -0.30)) and side != "LONG"
        )
        held_side = "LONG" if prev_long else "SHORT" if prev_short else "NEUTRAL"

        if confirmed:
            stage = "CONFIRMED"
            direction = side
            reason = "confirm_threshold + cluster_agreement + persistence_or_impulse"
        elif early:
            stage = "EARLY"
            direction = side
            reason = "early_threshold + live_velocity_or_dispersion_or_persistence"
        elif hold:
            stage = "HELD"
            direction = held_side
            reason = "hysteresis_hold"
        else:
            stage = "NEUTRAL"
            direction = "NEUTRAL"
            reason = "direction_conditions_not_met"

        if direction == "LONG":
            verdict, icon, color = "AL", "🟢", "green" if stage == "CONFIRMED" else "lightgreen"
        elif direction == "SHORT":
            verdict, icon, color = "SAT", "🔴", "red" if stage == "CONFIRMED" else "lightcoral"
        else:
            verdict, icon, color = "NÖTR (BEKLE)", "⚪", "gray"

        return {
            "direction": direction,
            "verdict": verdict,
            "icon": icon,
            "color": color,
            "stage": stage,
            "reason": reason,
            "thresholds": effective,
            "score": score,
            "score_z": round(score_z, 4) if previous_n >= 5.0 and self._finite(runtime.get("variance_score"), 0.0) > 1e-12 else None,
            "velocity": round(velocity, 6) if previous_score_available else None,
            "acceleration": round(acceleration, 6) if previous_score_available else None,
            "persistence": persistence,
            "diagnostic_warmup": previous_n < 5.0,
            "cluster_count": cluster_count,
            "min_clusters": min_clusters,
            "cluster_ok": cluster_ok,
            "early": early,
            "confirmed": confirmed,
            "strong_impulse": strong_impulse,
            "velocity_support": velocity_support,
            "z_support": z_support,
            "unfavorable_acceleration": unfavorable_accel,
            "runtime_n": round(self._finite(runtime.get("n")), 2),
            "runtime_mean": round(self._finite(runtime.get("mean_score")), 5),
            "runtime_sd": round(math.sqrt(max(self._finite(runtime.get("variance_score")), 0.0)), 5),
        }
