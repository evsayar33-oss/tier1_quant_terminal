"""
Multi-Timeframe Confluence Engine (HTF / MTF / LTF)
====================================================
Builds the "tum zaman dilimleri onayli" (all-timeframes-confirmed) entry
logic that did not previously exist in this repository at all.

Design choices, and why:

1. HTF/MTF bars are DERIVED by resampling the same 1H series the terminal
   already fetches (Open=first, High=max, Low=min, Close=last, Volume=sum),
   instead of issuing separate network calls for "1d"/"4h" intervals. Two
   independently-fetched series can close at slightly different times and
   silently desynchronize; a resampled series is *always* perfectly
   consistent with the LTF series it came from. This is standard practice
   on systematic desks: fetch the finest grain you trust, derive everything
   coarser from it.

2. Confirmation is NOT a boolean AND across timeframes (that starves entries
   the moment any one timeframe is noisy). It is a weighted confluence
   score in [-1, +1], where each timeframe's vote is scaled by (a) its
   own directional conviction and (b) an adaptive reliability weight for
   THIS asset in THIS macro regime. "All timeframes confirmed" becomes a
   graded statement ("0.86 confluence, HTF+MTF+LTF aligned long") rather
   than a fragile pass/fail gate, which is how top-down trend confirmation
   is actually used by CTAs and macro desks.

3. The reliability weights are self-improving: `record_outcome()` updates a
   small persisted, exponentially-decayed scorecard per (asset, regime,
   timeframe) cell. A timeframe that has been a poor predictor of the
   subsequent move, for THIS asset, in THIS regime, quietly loses influence
   over time -- without ever being hand-tuned. Cold start is handled by
   Bayesian shrinkage toward an equal-weight prior (same philosophy as
   `stateful_adaptive_model.py`'s factor-reliability channel), so a handful
   of early observations cannot swing the system.
"""

from __future__ import annotations

import json
import math
import os
import tempfile
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

_LOCK = threading.RLock()

DEFAULT_STATE_FILE = "timeframe_confluence_state.json"
STATE_VERSION = "1.0.0"

# Timeframe ladder: (label, resample_rule, fast_bars, slow_bars, prior_weight)
# Prior weight reflects an institutional starting point -- HTF sets context,
# LTF times the entry -- but these are only the PRIOR; live weights adapt.
TIMEFRAME_LADDER: List[Tuple[str, Optional[str], int, int, float]] = [
    ("HTF_1D", "1D", 3, 10, 0.45),
    ("MTF_4H", "4h", 3, 12, 0.30),
    ("LTF_1H", None, 4, 24, 0.25),
]

MIN_EFFECTIVE_SAMPLES = 20.0
HALF_LIFE_OBSERVATIONS = 60.0


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: str, payload: Dict[str, Any]) -> None:
    d = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp_path = tempfile.mkstemp(prefix=".tfc_", dir=d)
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


def _clean_ohlc(df: Any) -> Optional[pd.DataFrame]:
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


def resample_ohlc(df_1h: pd.DataFrame, rule: Optional[str]) -> Optional[pd.DataFrame]:
    """Derives a higher timeframe from 1H bars. rule=None returns the 1H
    series itself (the LTF leg needs no resampling)."""
    x = _clean_ohlc(df_1h)
    if x is None:
        return None
    if rule is None:
        return x
    agg = {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
    out = x.resample(rule, label="right", closed="right").agg(agg).dropna(subset=["Open", "High", "Low", "Close"])
    return out if not out.empty else None


def _directional_score(close: pd.Series, fast: int, slow: int) -> float:
    """Same fast/slow ROC-blend shape used elsewhere in this repo
    (quant_processor.compute_intraday_direction_momentum), applied here to
    a timeframe-agnostic bar series so every rung of the ladder is scored
    with one consistent, well-understood formula."""
    n = len(close)
    if n < 2:
        return 0.0
    w_fast = min(fast, n - 1)
    roc_fast = ((close.iloc[-1] - close.iloc[-w_fast - 1]) / (close.iloc[-w_fast - 1] + 1e-9)) * 100.0
    w_slow = min(slow, n - 1)
    roc_slow = ((close.iloc[-1] - close.iloc[-w_slow - 1]) / (close.iloc[-w_slow - 1] + 1e-9)) * 100.0
    blended = (roc_fast * 1.3) + (roc_slow * 0.4)
    return float(np.clip(np.tanh(blended / 2.5), -1.0, 1.0))


class TimeframeReliabilityStore:
    """Small, self-contained, exponentially-decayed scorecard of
    (asset, regime, timeframe) -> hit-rate. Deliberately separate from
    stateful_memory_store.json so this module can be dropped in without
    touching the existing adaptive-model persistence format."""

    def __init__(self, path: str = DEFAULT_STATE_FILE) -> None:
        self.path = path
        self._data: Dict[str, Any] = {"version": STATE_VERSION, "cells": {}}
        self._load()

    def _load(self) -> None:
        with _LOCK:
            if os.path.exists(self.path):
                try:
                    with open(self.path, "r", encoding="utf-8") as fh:
                        loaded = json.load(fh)
                    if isinstance(loaded, dict) and "cells" in loaded:
                        self._data = loaded
                except (json.JSONDecodeError, OSError):
                    pass

    def _save(self) -> None:
        with _LOCK:
            _atomic_write_json(self.path, self._data)

    @staticmethod
    def _key(asset_key: str, regime_id: Any, timeframe: str) -> str:
        return f"{asset_key}|{regime_id}|{timeframe}"

    def get_weight(self, asset_key: str, regime_id: Any, timeframe: str, prior_weight: float) -> float:
        cell = self._data["cells"].get(self._key(asset_key, regime_id, timeframe))
        if not cell:
            return prior_weight
        n_eff = float(cell.get("n_eff", 0.0))
        hit_ewma = float(cell.get("hit_ewma", 0.5))
        # Bayesian shrinkage toward the prior until enough evidence accrues.
        shrink = n_eff / (n_eff + MIN_EFFECTIVE_SAMPLES)
        # hit_ewma in [0,1] around 0.5 baseline; map to a multiplicative
        # adjustment on the prior weight, bounded so no cell can dominate
        # or be zeroed out purely from adaptation.
        adj_multiplier = 1.0 + shrink * (2.0 * (hit_ewma - 0.5))
        return float(np.clip(prior_weight * adj_multiplier, prior_weight * 0.35, prior_weight * 1.8))

    def record_outcome(self, asset_key: str, regime_id: Any, timeframe: str, was_correct: bool) -> None:
        """Call once the forward-looking horizon for a prior confluence
        read has settled (e.g. from the same periodic job that already
        drives stateful_background_tracker.py)."""
        with _LOCK:
            key = self._key(asset_key, regime_id, timeframe)
            cell = self._data["cells"].get(key, {"n_eff": 0.0, "hit_ewma": 0.5})
            decay = math.exp(-math.log(2.0) / HALF_LIFE_OBSERVATIONS)
            cell["n_eff"] = float(cell["n_eff"]) * decay + 1.0
            cell["hit_ewma"] = float(cell["hit_ewma"]) * decay + (1.0 if was_correct else 0.0) * (1.0 - decay)
            cell["updated_at"] = _utc_now_iso()
            self._data["cells"][key] = cell
            self._save()


_DEFAULT_STORE: Optional[TimeframeReliabilityStore] = None


def _default_store() -> TimeframeReliabilityStore:
    global _DEFAULT_STORE
    if _DEFAULT_STORE is None:
        _DEFAULT_STORE = TimeframeReliabilityStore()
    return _DEFAULT_STORE


def evaluate_confluence(
    df_1h: pd.DataFrame,
    asset_key: str,
    regime_id: Any = "REJIMSIZ_GECIS",
    store: Optional[TimeframeReliabilityStore] = None,
    min_htf_bars: int = 20,
    df_daily: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """Returns a graded multi-timeframe confluence read for one asset.

    Keys:
      confluence_score   float in [-1, 1]; sign = direction, magnitude = agreement strength
      all_aligned        True only when every timeframe with enough history agrees on sign
      timeframes         per-rung diagnostics (score, weight, bar count)
      entry_confirmed    confluence_score magnitude clears an adaptive bar AND direction agrees
                          with the fastest (LTF) timeframe -- i.e. HTF/MTF context supports the
                          LTF trigger, which is the actual "girin mantıklı" test being asked for.
    """
    store = store or _default_store()
    rungs: Dict[str, Dict[str, Any]] = {}
    weighted_sum = 0.0
    weight_total = 0.0
    signs: List[int] = []

    for label, rule, fast, slow, prior_w in TIMEFRAME_LADDER:
        if label == "HTF_1D" and df_daily is not None and not df_daily.empty:
            # A genuinely-fetched daily series is preferred over resampling
            # only a few days of 1H bars, which cannot produce a meaningful
            # HTF read (see module docstring point 1: resampling is the
            # fallback, not a substitute for real HTF history when it's
            # available).
            bars = _clean_ohlc(df_daily)
        else:
            bars = resample_ohlc(df_1h, rule)
        if bars is None or len(bars) < min_htf_bars:
            rungs[label] = {"available": False, "bars": 0 if bars is None else len(bars)}
            continue
        score = _directional_score(bars["Close"], fast, slow)
        weight = store.get_weight(asset_key, regime_id, label, prior_w)
        rungs[label] = {
            "available": True,
            "bars": int(len(bars)),
            "score": round(score, 4),
            "weight": round(weight, 4),
        }
        weighted_sum += score * weight
        weight_total += weight
        if abs(score) > 0.05:
            signs.append(1 if score > 0 else -1)

    if weight_total <= 0.0:
        return {
            "available": False,
            "reason": "Hiçbir zaman dilimi için yeterli çubuk yok.",
            "confluence_score": 0.0,
            "all_aligned": False,
            "entry_confirmed": False,
            "timeframes": rungs,
        }

    confluence_score = float(np.clip(weighted_sum / weight_total, -1.0, 1.0))
    all_aligned = len(signs) >= 2 and len(set(signs)) == 1

    ltf = rungs.get("LTF_1H", {})
    ltf_score = float(ltf.get("score", 0.0)) if ltf.get("available") else 0.0
    ltf_sign = 1 if ltf_score > 0 else (-1 if ltf_score < 0 else 0)
    conf_sign = 1 if confluence_score > 0 else (-1 if confluence_score < 0 else 0)

    # Adaptive confirmation bar: requires more agreement, not a fixed magic
    # number, when the pair has recently been noisy (weight_total shrinks
    # toward the low end of its clip range when reliability has been poor).
    min_weight_for_full_confirmation = 0.55 * sum(w for *_, w in TIMEFRAME_LADDER)
    strength_ok = abs(confluence_score) >= 0.35
    weight_ok = weight_total >= min_weight_for_full_confirmation
    entry_confirmed = bool(strength_ok and weight_ok and ltf_sign != 0 and ltf_sign == conf_sign)

    return {
        "available": True,
        "confluence_score": round(confluence_score, 4),
        "all_aligned": bool(all_aligned),
        "entry_confirmed": entry_confirmed,
        "weight_total": round(weight_total, 4),
        "timeframes": rungs,
        "asset_key": asset_key,
        "regime_id": regime_id,
    }
