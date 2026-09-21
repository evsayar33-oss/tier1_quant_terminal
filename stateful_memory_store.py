"""
Stateful Adaptive Memory Store
==============================
Persistent, compact online-learning memory for Tier-1 Quant Terminal.

Design goals
------------
* No synthetic market data.
* No look-ahead: observations are stored first; outcomes are settled only
  after their forecast horizon is available.
* Persistent across GitHub Actions / Streamlit process restarts.
* Compact enough to be safely versioned as JSON.
* Exponentially decayed statistics so old regimes matter less without being
  forgotten abruptly.
* Stores pending factor snapshots only until their outcomes can be measured.

The memory file is intentionally separate from terminal_state.json. The latter
is a UI/state snapshot; this file is the model's longitudinal learning memory.
"""

from __future__ import annotations

import json
import math
import os
import tempfile
import threading
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np


DEFAULT_MEMORY_FILE = "stateful_adaptive_memory.json"
MEMORY_VERSION = "1.0.0"

DEFAULT_HALF_LIFE_HOURS = 24.0 * 14.0  # 14 days
MAX_PENDING_OBSERVATIONS = 2500
MAX_SCORE_BINS = 28  # abs(score) range [0, 3.5], width 0.125
SCORE_MIN = 0.0
SCORE_MAX = 3.5

_LOCK = threading.RLock()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    try:
        text = str(value).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _finite_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        x = float(value)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, datetime):
        return _iso(value)
    raise TypeError(f"Unsupported JSON value: {type(value)!r}")


def _default_score_direction_bucket() -> Dict[str, Any]:
    return {
        "n": 0.0,
        "wins": 0.0,
        "return_sum": 0.0,
        "return_sq_sum": 0.0,
    }


def _default_memory() -> Dict[str, Any]:
    return {
        "version": MEMORY_VERSION,
        "created_at": _iso(_utc_now()),
        "last_updated": None,
        "last_decay_at": None,
        "regime_state": {},
        "score_memory": {},
        "factor_memory": {},
        "pending_observations": [],
        "meta": {
            "settled_observations": 0,
            "last_cycle_id": None,
        },
    }


class StatefulMemoryStore:
    """Compact persistent memory with atomic writes and exponential decay."""

    def __init__(
        self,
        path: str | os.PathLike[str] = DEFAULT_MEMORY_FILE,
        half_life_hours: float = DEFAULT_HALF_LIFE_HOURS,
    ) -> None:
        self.path = Path(path)
        self.half_life_hours = max(float(half_life_hours), 1.0)
        self.memory = self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return _default_memory()
        try:
            with self.path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict):
                return _default_memory()
            base = _default_memory()
            base.update(data)
            return base
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return _default_memory()

    def save(self) -> None:
        """Atomic JSON replacement to prevent partial/corrupted memory."""
        with _LOCK:
            self.memory["version"] = MEMORY_VERSION
            self.memory["last_updated"] = _iso(_utc_now())
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                dir=str(self.path.parent),
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    json.dump(
                        self.memory,
                        fh,
                        ensure_ascii=False,
                        indent=2,
                        allow_nan=False,
                        default=_json_default,
                    )
                    fh.flush()
                    os.fsync(fh.fileno())
                os.replace(tmp_name, self.path)
            finally:
                if os.path.exists(tmp_name):
                    try:
                        os.remove(tmp_name)
                    except OSError:
                        pass

    # ------------------------------------------------------------------
    # Generic decay
    # ------------------------------------------------------------------
    @staticmethod
    def decay_factor(elapsed_hours: float, half_life_hours: float) -> float:
        elapsed = max(float(elapsed_hours), 0.0)
        half_life = max(float(half_life_hours), 1.0)
        return float(math.exp(-math.log(2.0) * elapsed / half_life))

    def apply_decay(self, now: Optional[datetime] = None) -> None:
        """Decay model statistics once per cycle based on wall-clock elapsed time."""
        with _LOCK:
            current = now or _utc_now()
            last = _parse_dt(self.memory.get("last_decay_at"))
            if last is None:
                self.memory["last_decay_at"] = _iso(current)
                return

            elapsed_hours = max((current - last).total_seconds() / 3600.0, 0.0)
            if elapsed_hours <= 0.0:
                return

            decay = self.decay_factor(elapsed_hours, self.half_life_hours)

            for asset_state in self.memory.get("score_memory", {}).values():
                for regime_state in asset_state.values():
                    for direction_state in regime_state.values():
                        if not isinstance(direction_state, dict):
                            continue
                        for field in (
                            "n",
                            "wins",
                            "return_sum",
                            "return_sq_sum",
                        ):
                            direction_state[field] = float(direction_state.get(field, 0.0)) * decay

            for asset_state in self.memory.get("factor_memory", {}).values():
                for stats in asset_state.values():
                    if not isinstance(stats, dict):
                        continue
                    for field in (
                        "n",
                        "sum_x",
                        "sum_y",
                        "sum_x2",
                        "sum_y2",
                        "sum_xy",
                    ):
                        stats[field] = float(stats.get(field, 0.0)) * decay

            self.memory["last_decay_at"] = _iso(current)

    # ------------------------------------------------------------------
    # Regime state
    # ------------------------------------------------------------------
    def get_regime_state(self) -> Dict[str, Any]:
        return deepcopy(self.memory.get("regime_state", {}))

    def set_regime_state(self, state: Dict[str, Any]) -> None:
        with _LOCK:
            self.memory["regime_state"] = deepcopy(state or {})

    # ------------------------------------------------------------------
    # Pending observations
    # ------------------------------------------------------------------
    def add_pending_observation(self, observation: Dict[str, Any]) -> None:
        """Store a forecast snapshot until its forward returns become observable."""
        with _LOCK:
            pending = self.memory.setdefault("pending_observations", [])
            obs = deepcopy(observation)
            obs.setdefault("created_at", _iso(_utc_now()))
            obs["created_at"] = str(obs["created_at"])
            pending.append(obs)
            if len(pending) > MAX_PENDING_OBSERVATIONS:
                # Oldest pending observations are the least useful if a remote
                # runner was interrupted for a prolonged period.
                pending.sort(key=lambda x: str(x.get("created_at", "")))
                del pending[:-MAX_PENDING_OBSERVATIONS]

    def pending_count(self) -> int:
        return len(self.memory.get("pending_observations", []))

    # ------------------------------------------------------------------
    # Score calibration memory
    # ------------------------------------------------------------------
    @staticmethod
    def _regime_key(regime_id: Any) -> str:
        return str(regime_id) if regime_id is not None else "REJIMSIZ_GECIS"

    def _ensure_score_bucket(
        self,
        asset: str,
        regime_id: Any,
        direction: str,
    ) -> Dict[str, Any]:
        asset_key = str(asset)
        regime_key = self._regime_key(regime_id)
        direction_key = "long" if direction.lower().startswith("l") else "short"
        asset_state = self.memory.setdefault("score_memory", {}).setdefault(asset_key, {})
        regime_state = asset_state.setdefault(regime_key, {})
        return regime_state.setdefault(direction_key, _default_score_direction_bucket())

    @staticmethod
    def score_bin_index(abs_score: float) -> int:
        x = min(max(float(abs_score), SCORE_MIN), SCORE_MAX - 1e-12)
        return int(math.floor(x / (SCORE_MAX / MAX_SCORE_BINS)))

    def _ensure_score_bins(
        self,
        asset: str,
        regime_id: Any,
        direction: str,
    ) -> List[Dict[str, float]]:
        bucket = self._ensure_score_bucket(asset, regime_id, direction)
        bins = bucket.setdefault(
            "bins",
            [
                {
                    "n": 0.0,
                    "wins": 0.0,
                    "return_sum": 0.0,
                    "return_sq_sum": 0.0,
                }
                for _ in range(MAX_SCORE_BINS)
            ],
        )
        return bins

    def record_score_outcome(
        self,
        asset: str,
        regime_id: Any,
        score: float,
        forward_return: float,
    ) -> None:
        """Update long/short threshold evidence for one realized forecast."""
        score_f = _finite_float(score)
        ret = _finite_float(forward_return)
        if score_f is None or ret is None:
            return
        if abs(score_f) < 1e-12:
            return

        direction = "long" if score_f > 0 else "short"
        success = ret > 0.0 if direction == "long" else ret < 0.0
        bucket = self._ensure_score_bucket(asset, regime_id, direction)
        bins = self._ensure_score_bins(asset, regime_id, direction)
        idx = self.score_bin_index(abs(score_f))
        target = bins[idx]

        for node in (bucket, target):
            node["n"] = float(node.get("n", 0.0)) + 1.0
            if success:
                node["wins"] = float(node.get("wins", 0.0)) + 1.0
            node["return_sum"] = float(node.get("return_sum", 0.0)) + ret
            node["return_sq_sum"] = float(node.get("return_sq_sum", 0.0)) + ret * ret

    def score_calibration_snapshot(
        self,
        asset: str,
        regime_id: Any,
        direction: str,
        min_abs_score: float,
    ) -> Dict[str, float]:
        """
        Aggregate all score evidence at or above a candidate threshold.
        This is the sufficient-statistics equivalent of querying historical rows.
        """
        bins = self._ensure_score_bins(asset, regime_id, direction)
        width = SCORE_MAX / MAX_SCORE_BINS
        first_idx = min(MAX_SCORE_BINS - 1, self.score_bin_index(min_abs_score))

        n = wins = ret_sum = ret_sq_sum = 0.0
        for idx in range(first_idx, MAX_SCORE_BINS):
            node = bins[idx]
            n += float(node.get("n", 0.0))
            wins += float(node.get("wins", 0.0))
            ret_sum += float(node.get("return_sum", 0.0))
            ret_sq_sum += float(node.get("return_sq_sum", 0.0))

        if n <= 0.0:
            return {
                "n": 0.0,
                "wins": 0.0,
                "hit_rate": 0.0,
                "return_mean": 0.0,
                "return_std": 0.0,
                "threshold": float(min_abs_score),
                "effective_n": 0.0,
                "wilson_lower": 0.0,
                "bin_start": float(first_idx * width),
            }

        p = wins / n
        variance = max(ret_sq_sum / n - (ret_sum / n) ** 2, 0.0)
        # The bucket count itself is the weighted sample size after decay.
        effective_n = n
        wilson = _wilson_lower_bound(p, effective_n)
        return {
            "n": float(n),
            "wins": float(wins),
            "hit_rate": float(p),
            "return_mean": float(ret_sum / n),
            "return_std": float(math.sqrt(variance)),
            "threshold": float(min_abs_score),
            "effective_n": float(effective_n),
            "wilson_lower": float(wilson),
            "bin_start": float(first_idx * width),
        }

    # ------------------------------------------------------------------
    # Factor performance memory
    # ------------------------------------------------------------------
    def _ensure_factor(self, asset: str, factor_id: str) -> Dict[str, float]:
        return self.memory.setdefault("factor_memory", {}).setdefault(str(asset), {}).setdefault(
            str(factor_id),
            {
                "n": 0.0,
                "sum_x": 0.0,
                "sum_y": 0.0,
                "sum_x2": 0.0,
                "sum_y2": 0.0,
                "sum_xy": 0.0,
            },
        )

    def record_factor_outcome(
        self,
        asset: str,
        factor_id: str,
        factor_value: float,
        forward_return: float,
    ) -> None:
        x = _finite_float(factor_value)
        y = _finite_float(forward_return)
        if x is None or y is None:
            return
        x = float(np.clip(x, -1.8, 1.8))
        # Cap extreme returns so one gap cannot rewrite factor memory.
        y = float(np.clip(y, -0.20, 0.20))
        stats = self._ensure_factor(asset, factor_id)
        stats["n"] += 1.0
        stats["sum_x"] += x
        stats["sum_y"] += y
        stats["sum_x2"] += x * x
        stats["sum_y2"] += y * y
        stats["sum_xy"] += x * y

    def factor_ic(self, asset: str, factor_id: str, prior_n: float = 60.0) -> Tuple[float, float]:
        stats = self.memory.get("factor_memory", {}).get(str(asset), {}).get(str(factor_id))
        if not stats:
            return 0.0, 0.0
        n = float(stats.get("n", 0.0))
        if n < 3.0:
            return 0.0, n
        sx = float(stats.get("sum_x", 0.0))
        sy = float(stats.get("sum_y", 0.0))
        sxx = float(stats.get("sum_x2", 0.0))
        syy = float(stats.get("sum_y2", 0.0))
        sxy = float(stats.get("sum_xy", 0.0))

        cov = sxy - (sx * sy / n)
        vx = max(sxx - (sx * sx / n), 0.0)
        vy = max(syy - (sy * sy / n), 0.0)
        denom = math.sqrt(vx * vy)
        raw_ic = cov / denom if denom > 1e-12 else 0.0

        # Bayesian-style shrinkage toward zero with a fixed prior sample size.
        shrink = n / (n + max(float(prior_n), 1.0))
        return float(np.clip(raw_ic, -1.0, 1.0) * shrink), n

    def factor_weight_multiplier(
        self,
        asset: str,
        factor_id: str,
        min_mult: float = 0.65,
        max_mult: float = 1.35,
    ) -> Dict[str, float]:
        ic, n = self.factor_ic(asset, factor_id)
        multiplier = float(np.clip(1.0 + 1.75 * ic, min_mult, max_mult))
        return {
            "factor_id": str(factor_id),
            "ic": round(ic, 6),
            "n": round(n, 3),
            "multiplier": round(multiplier, 6),
        }

    # ------------------------------------------------------------------
    # Pending settlement
    # ------------------------------------------------------------------
    @staticmethod
    def _frame_series(frame: Any) -> Optional[Any]:
        try:
            import pandas as pd
            if frame is None or not isinstance(frame, pd.DataFrame) or frame.empty:
                return None
            if "Close" not in frame.columns:
                return None
            x = pd.to_numeric(frame["Close"], errors="coerce").dropna()
            if x.empty:
                return None
            idx = pd.to_datetime(x.index, errors="coerce", utc=True)
            x = x.copy()
            x.index = idx
            x = x[~x.index.isna()]
            return x.sort_index()
        except Exception:
            return None

    def _future_price(
        self,
        price_series: Any,
        observation_time: datetime,
        horizon_hours: float,
    ) -> Optional[float]:
        if price_series is None or len(price_series) == 0:
            return None
        target = observation_time + __import__("datetime").timedelta(hours=float(horizon_hours))
        try:
            import pandas as pd
            idx = price_series.index
            if not isinstance(idx, pd.DatetimeIndex):
                return None
            pos = int(idx.searchsorted(pd.Timestamp(target), side="left"))
            if pos >= len(price_series):
                return None
            value = _finite_float(price_series.iloc[pos])
            return value
        except Exception:
            return None

    def settle_pending(
        self,
        price_frames: Dict[str, Any],
        horizon_hours: Iterable[int] = (1, 4, 8),
        now: Optional[datetime] = None,
    ) -> Dict[str, int]:
        """
        Settle due observations and update factor/score memories.

        Returns counts of settled observations and remains safe when historical
        frames do not yet contain the requested future target.
        """
        current = now or _utc_now()
        series_map = {str(k): self._frame_series(v) for k, v in price_frames.items()}
        pending = self.memory.get("pending_observations", [])
        remaining: List[Dict[str, Any]] = []
        settled = 0
        ignored = 0
        requested_horizons = tuple(int(x) for x in horizon_hours)

        for obs in pending:
            observed_at = _parse_dt(obs.get("observed_at") or obs.get("created_at"))
            asset = str(obs.get("asset", ""))
            start_price = _finite_float(obs.get("price"))
            if observed_at is None or not asset or start_price is None or start_price <= 0:
                ignored += 1
                continue

            frame_series = series_map.get(asset)
            if frame_series is None:
                remaining.append(obs)
                continue

            horizons: Dict[str, float] = {}
            all_due = True
            for horizon in requested_horizons:
                target = observed_at.timestamp() + horizon * 3600.0
                if current.timestamp() + 60.0 < target:
                    all_due = False
                    continue
                px = self._future_price(frame_series, observed_at, horizon)
                if px is None:
                    all_due = False
                    continue
                horizons[str(horizon)] = float(px / start_price - 1.0)

            # Do not consume an observation until the calibration horizon (4h)
            # is actually measurable. Shorter/longer horizons may be partial.
            if "4" not in horizons:
                remaining.append(obs)
                continue

            for h_str, ret in horizons.items():
                obs[f"forward_return_{h_str}h"] = ret

            calibration_ret = horizons["4"]
            regime_id = obs.get("active_regime_id", "REJIMSIZ_GECIS")
            score = obs.get("model_score_adaptive", obs.get("model_score_raw"))
            self.record_score_outcome(asset, regime_id, score, calibration_ret)

            factors = obs.get("factors", {})
            if isinstance(factors, dict):
                for factor_id, factor_value in factors.items():
                    self.record_factor_outcome(asset, factor_id, factor_value, calibration_ret)

            settled += 1
            self.memory.setdefault("meta", {})["settled_observations"] = int(
                self.memory.get("meta", {}).get("settled_observations", 0)
            ) + 1

        self.memory["pending_observations"] = remaining
        return {
            "settled": settled,
            "remaining": len(remaining),
            "ignored": ignored,
        }

    # ------------------------------------------------------------------
    # Memory diagnostics
    # ------------------------------------------------------------------
    def diagnostics(self) -> Dict[str, Any]:
        score_assets = len(self.memory.get("score_memory", {}))
        factor_assets = len(self.memory.get("factor_memory", {}))
        factor_count = sum(
            len(v) for v in self.memory.get("factor_memory", {}).values() if isinstance(v, dict)
        )
        return {
            "memory_version": self.memory.get("version", MEMORY_VERSION),
            "memory_file": str(self.path),
            "score_assets": score_assets,
            "factor_assets": factor_assets,
            "factor_count": factor_count,
            "pending_observations": self.pending_count(),
            "settled_observations": int(self.memory.get("meta", {}).get("settled_observations", 0)),
            "half_life_hours": self.half_life_hours,
            "last_updated": self.memory.get("last_updated"),
            "last_decay_at": self.memory.get("last_decay_at"),
        }


def _wilson_lower_bound(p: float, n: float, z: float = 1.2815515655446004) -> float:
    """One-sided 90% Wilson lower confidence bound."""
    if n <= 0.0:
        return 0.0
    p = float(np.clip(p, 0.0, 1.0))
    denom = 1.0 + z * z / n
    center = p + z * z / (2.0 * n)
    margin = z * math.sqrt(max(p * (1.0 - p) / n + z * z / (4.0 * n * n), 0.0))
    return float(np.clip((center - margin) / denom, 0.0, 1.0))
