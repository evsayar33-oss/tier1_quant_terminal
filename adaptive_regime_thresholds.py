"""
Adaptive Regime Threshold Store
================================
Replaces MacroRegimeEngine's hardcoded trigger cutoffs (e.g. "oil_20d_z >
1.5", "hy_oas_z > 2.0") with thresholds DERIVED from each indicator's own
recency-weighted empirical distribution.

Why this matters: a fixed z-score cutoff assumes the indicator's own
distribution is stationary. It is not -- HY OAS, VIX, DXY velocity all go
through multi-year stretches of higher or lower typical variance. A shock
threshold calibrated once in a calm period keeps firing false positives once
the regime gets structurally noisier (or goes stale and stops firing at all
once it gets structurally calmer). Central-bank and cross-asset stress
dashboards handle this by expressing triggers as percentiles of trailing
history, not fixed magnitudes -- this module gives the existing rule-based
engine that same property without touching its rule STRUCTURE (still
deterministic, still explainable, still "Regime 1 needs oil shock AND
freight collapse") -- only the calibration of what counts as "shock-sized"
becomes self-updating.

Cold start / never-fabricate-data safety: every threshold is a SHRINKAGE
blend between the empirical quantile and the original literal default. With
zero history the store returns exactly the original literal (behavior is
byte-for-byte identical to before this module existed). As observations
accrue, the blend smoothly shifts toward the empirical estimate -- there is
no hard cutover, no "at N observations everything suddenly changes."

Each `evaluate()` call in MacroRegimeEngine feeds one more observation for
every indicator it computes, which is exactly what "senelerce dinamik ve
otomatik çalışsın" (working dynamically for years, unattended) requires:
the longer this runs in production, the better calibrated it gets, with no
manual re-tuning.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Deque, Dict, Optional

import numpy as np

_LOCK = threading.RLock()

DEFAULT_STATE_FILE = "adaptive_regime_thresholds_state.json"
STATE_VERSION = "1.0.0"
MAX_HISTORY = 500          # bounded reservoir per indicator
HALF_LIFE_OBSERVATIONS = 180.0   # ~ one trading-year at weekly cadence
TARGET_OBSERVATIONS_FOR_FULL_TRUST = 60.0  # below this, lean on the literal default


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: str, payload: Dict) -> None:
    d = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp_path = tempfile.mkstemp(prefix=".art_", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


class AdaptiveThresholdStore:
    def __init__(self, path: str = DEFAULT_STATE_FILE, max_history: int = MAX_HISTORY) -> None:
        self.path = path
        self.max_history = int(max_history)
        self._series: Dict[str, Deque[float]] = {}
        self._load()

    def _load(self) -> None:
        with _LOCK:
            if os.path.exists(self.path):
                try:
                    with open(self.path, "r", encoding="utf-8") as fh:
                        payload = json.load(fh)
                    for key, values in payload.get("series", {}).items():
                        self._series[key] = deque(values[-self.max_history:], maxlen=self.max_history)
                except (json.JSONDecodeError, OSError):
                    pass

    def _save(self) -> None:
        with _LOCK:
            payload = {
                "version": STATE_VERSION,
                "updated_at": _utc_now_iso(),
                "series": {k: list(v) for k, v in self._series.items()},
            }
            _atomic_write_json(self.path, payload)

    def update(self, indicator_key: str, value: Optional[float]) -> None:
        """Feed one fresh, real observation. Never called with fabricated
        or forward-filled data -- callers should only pass values that were
        actually computed for the current cycle."""
        if value is None:
            return
        try:
            v = float(value)
        except (TypeError, ValueError):
            return
        if not np.isfinite(v):
            return
        with _LOCK:
            self._series.setdefault(indicator_key, deque(maxlen=self.max_history)).append(v)

    def save(self) -> None:
        self._save()

    def _weighted_quantile(self, indicator_key: str, quantile: float) -> Optional[float]:
        obs = self._series.get(indicator_key)
        if not obs or len(obs) < 8:
            return None
        arr = np.asarray(obs, dtype=float)
        n = len(arr)
        age = np.arange(n - 1, -1, -1, dtype=float)  # 0 = most recent
        weights = np.exp(-np.log(2.0) * age / HALF_LIFE_OBSERVATIONS)
        order = np.argsort(arr)
        arr_sorted = arr[order]
        w_sorted = weights[order]
        cum_w = np.cumsum(w_sorted) - 0.5 * w_sorted
        cum_w /= w_sorted.sum()
        return float(np.interp(quantile, cum_w, arr_sorted))

    def get_threshold(
        self,
        indicator_key: str,
        quantile: float,
        fallback_value: float,
    ) -> float:
        """Shrinkage blend of the indicator's own recency-weighted empirical
        quantile and the original hardcoded literal. Returns `fallback_value`
        unchanged until enough real observations exist -- this is the
        cold-start / non-regression guarantee."""
        empirical = self._weighted_quantile(indicator_key, quantile)
        if empirical is None:
            return float(fallback_value)
        n_obs = len(self._series.get(indicator_key, []))
        trust = min(n_obs / TARGET_OBSERVATIONS_FOR_FULL_TRUST, 1.0)
        return float(trust * empirical + (1.0 - trust) * fallback_value)

    def diagnostics(self, indicator_key: str) -> Dict[str, object]:
        obs = self._series.get(indicator_key, [])
        return {
            "n_observations": len(obs),
            "trust": round(min(len(obs) / TARGET_OBSERVATIONS_FOR_FULL_TRUST, 1.0), 3),
        }


_DEFAULT_STORE: Optional[AdaptiveThresholdStore] = None


def default_store() -> AdaptiveThresholdStore:
    global _DEFAULT_STORE
    if _DEFAULT_STORE is None:
        _DEFAULT_STORE = AdaptiveThresholdStore()
    return _DEFAULT_STORE
