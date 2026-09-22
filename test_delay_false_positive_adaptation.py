from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np

from stateful_adaptive_model import AdaptiveScoreModel
from stateful_direction_engine import StatefulDirectionEngine
from stateful_memory_store import StatefulMemoryStore


def test_direction_ignores_execution_gate(tmp_path: Path):
    store = StatefulMemoryStore(tmp_path / "memory.json")
    engine = StatefulDirectionEngine(store)
    thresholds = {
        "buy_enter": 0.75,
        "buy_early": 0.50,
        "buy_exit": 0.30,
        "sell_enter": -0.75,
        "sell_early": -0.50,
        "sell_exit": -0.30,
        "strong_buy_enter": 1.70,
        "strong_sell_enter": -1.70,
        "min_clusters": 2,
    }
    first = engine.evaluate("XAU", 5, 0.82, 3, 0, thresholds, "NÖTR (BEKLE)")
    second = engine.evaluate("XAU", 5, 0.84, 3, 0, thresholds, first["verdict"])
    assert second["direction"] == "LONG"
    assert second["stage"] in {"EARLY", "CONFIRMED"}


def test_persistence_is_required_for_moderate_early_signal(tmp_path: Path):
    store = StatefulMemoryStore(tmp_path / "memory.json")
    engine = StatefulDirectionEngine(store)
    thresholds = {
        "buy_enter": 0.90,
        "buy_early": 0.55,
        "buy_exit": 0.30,
        "sell_enter": -0.90,
        "sell_early": -0.55,
        "sell_exit": -0.30,
        "strong_buy_enter": 1.70,
        "strong_sell_enter": -1.70,
        "min_clusters": 2,
    }
    a = engine.evaluate("NQ", 5, 0.60, 2, 0, thresholds)
    b = engine.evaluate("NQ", 5, 0.61, 2, 0, thresholds, a["verdict"])
    assert a["stage"] == "NEUTRAL"
    assert b["stage"] in {"EARLY", "CONFIRMED"}


def test_dynamic_thresholds_use_1h_outcome_quality(tmp_path: Path):
    store = StatefulMemoryStore(tmp_path / "memory.json")
    model = AdaptiveScoreModel(store)
    for _ in range(50):
        store.record_direction_outcome("XAG", 5, "LONG", -0.004, "1")
    thresholds = model.dynamic_thresholds("XAG", 5)
    assert thresholds["buy_early"] >= 0.30
    assert thresholds["early_outcome_adjustment"]["long"] > 1.0


def test_favorable_velocity_modulates_early_threshold_downward():
    base = {
        "buy_enter": 0.80,
        "buy_early": 0.56,
        "buy_exit": 0.30,
        "sell_enter": -0.80,
        "sell_early": -0.56,
        "sell_exit": -0.30,
        "min_clusters": 2,
    }
    neutral = StatefulDirectionEngine._effective_thresholds(base, 0.0, 0.0, 0.0, "LONG")
    fast = StatefulDirectionEngine._effective_thresholds(base, 0.9, 0.20, 0.10, "LONG")
    assert fast["buy_early"] < neutral["buy_early"]
    assert fast["buy_enter"] <= neutral["buy_enter"]


def test_direction_runtime_persists(tmp_path: Path):
    path = tmp_path / "memory.json"
    store = StatefulMemoryStore(path)
    engine = StatefulDirectionEngine(store)
    thresholds = {
        "buy_enter": 0.80,
        "buy_early": 0.55,
        "buy_exit": 0.30,
        "sell_enter": -0.80,
        "sell_early": -0.55,
        "sell_exit": -0.30,
        "min_clusters": 2,
    }
    engine.evaluate("GC", 5, 0.70, 2, 0, thresholds)
    store.save()
    store2 = StatefulMemoryStore(path)
    runtime = store2.get_direction_runtime("GC", 5)
    assert runtime["n"] >= 1
    assert len(runtime["recent_scores"]) >= 1
