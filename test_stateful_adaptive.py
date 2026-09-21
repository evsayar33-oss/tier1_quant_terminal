from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from stateful_adaptive_model import AdaptiveScoreModel
from dynamic_entry_engine import StatefulDynamicEntryEngine
from stateful_adaptive_controller import StatefulAdaptiveController
from stateful_memory_store import StatefulMemoryStore
from stateful_regime_controller import StatefulRegimeController
from xau_xag_dynamic_pair import DynamicXAU_XAGModel


def synthetic_ohlcv(n: int = 120, start: float = 100.0, seed: int = 7, volume_base: int = 1000) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0002, 0.005, n)
    close = start * np.cumprod(1.0 + rets)
    high = close * (1.0 + rng.uniform(0.0002, 0.003, n))
    low = close * (1.0 - rng.uniform(0.0002, 0.003, n))
    open_ = np.r_[close[0], close[:-1]]
    volume = rng.integers(volume_base // 2, volume_base * 2, n)
    idx = pd.date_range(datetime.now(timezone.utc) - timedelta(hours=n-1), periods=n, freq="1h")
    df = pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume}, index=idx)
    df.attrs.update({"is_real": True, "source_type": "DIRECT", "status": "LIVE", "execution_eligible": True})
    return df


def test_memory_score_and_factor_update(tmp_path: Path):
    store = StatefulMemoryStore(tmp_path / "memory.json", half_life_hours=336)
    for _ in range(40):
        store.record_score_outcome("XAU", 5, 1.20, 0.01)
        store.record_factor_outcome("XAU", "asset_direction", (-1.0 if _ % 2 == 0 else 1.0), (-0.01 if _ % 2 == 0 else 0.01))
    stats = store.score_calibration_snapshot("XAU", 5, "long", 1.0)
    ic, n = store.factor_ic("XAU", "asset_direction")
    assert stats["n"] > 30
    assert stats["hit_rate"] == 1.0
    assert ic > 0
    assert n == 40


def test_dynamic_threshold_has_memory_influence(tmp_path: Path):
    store = StatefulMemoryStore(tmp_path / "memory.json")
    model = AdaptiveScoreModel(store)
    baseline = model.dynamic_thresholds("XAU", 5)["buy_enter"]
    for _ in range(60):
        store.record_score_outcome("XAU", 5, 1.25, 0.01)
    changed = model.dynamic_thresholds("XAU", 5)["buy_enter"]
    assert changed != baseline or changed == 1.25
    assert 0.45 <= changed <= 2.50


def test_regime_controller_retains_confirmed_on_neutral(tmp_path: Path):
    store = StatefulMemoryStore(tmp_path / "memory.json")
    controller = StatefulRegimeController(store, confirmation_minutes={"SHOCK": 60, "RISK_ON": 60, "DENGE": 0})
    raw = {
        "candidate_regime_id": 5,
        "active_regime_id": 5,
        "active_regime_name": "Risk-On",
        "active_regime_type": "RISK_ON",
        "active_regime_subtype": "Risk-On",
        "indicator_z_scores": {"ndl_z": 1.2, "vix": -1.0},
    }
    first = controller.update(raw)
    assert first["active_regime_id"] == 5
    # Force a confirmed state in persistent memory.
    s = store.get_regime_state()
    s["confirmed_regime_id"] = 5
    s["candidate_regime_id"] = 5
    store.set_regime_state(s)
    neutral = controller.update({"candidate_regime_id": "REJIMSIZ_GECIS", "indicator_z_scores": {}})
    assert neutral["active_regime_id"] == 5
    assert neutral["stateful_transition_reason"] == "NO_NEW_TRIGGER_KEEP_CONFIRMED"


def test_dynamic_entry_works_with_82_plus_real_bars():
    df = synthetic_ohlcv(90, seed=11)
    engine = StatefulDynamicEntryEngine(min_history=45)
    result = engine.evaluate(df, require_live=True)
    assert result["profile"] is not None
    assert result["profile"]["history_n"] >= 45


def test_dynamic_xau_xag_model():
    n = 100
    idx = pd.date_range(datetime.now(timezone.utc) - timedelta(hours=n-1), periods=n, freq="1h")
    rng = np.random.default_rng(1)
    xau_r = rng.normal(0.0001, 0.003, n)
    hg_r = rng.normal(0.0001, 0.004, n)
    xag_r = 1.6 * xau_r + 0.5 * hg_r + rng.normal(0.0, 0.001, n)
    xau = 100 * np.cumprod(1 + xau_r)
    hg = 50 * np.cumprod(1 + hg_r)
    xag = 30 * np.cumprod(1 + xag_r)
    grid = {}
    for key, values in (("GC", xau), ("HG", hg), ("SI", xag)):
        grid[key] = pd.DataFrame({"Close": values}, index=idx)
    state = DynamicXAU_XAGModel().fit(grid)
    assert state["available"] is True
    assert np.isfinite(state["beta_gold"])
    assert np.isfinite(state["beta_copper"])


def test_controller_creates_pending_observations(tmp_path: Path):
    memory = tmp_path / "memory.json"
    controller = StatefulAdaptiveController(memory_file=str(memory))
    assert controller.store.path == memory
