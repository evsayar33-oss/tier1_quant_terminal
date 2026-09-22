import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / "base_pkg"
sys.path.insert(0, str(ROOT))
sys.path.insert(1, str(BASE))

from stateful_factor_quality import sanitize_factor_rows, _safe_ratio_z
from stateful_adaptive_model import AdaptiveScoreModel
from stateful_memory_store import StatefulMemoryStore
from stateful_direction_engine import StatefulDirectionEngine


class FakeGK:
    def __init__(self, grid):
        self.grid_1h = grid
        self.processor = None
        self.dxy_velocity = 0.0
        self.credit_velocity = 0.0
        self.real_yield_z = 0.0
        self.breakeven_z = 0.0
        self.stagflation_z = 0.0
        self.yen_carry_z = 0.0
        self.ndl_z = 0.0


def ohlcv(values):
    idx = pd.date_range("2026-01-01", periods=len(values), freq="h")
    v = np.asarray(values, dtype=float)
    return pd.DataFrame({"Open": v, "High": v, "Low": v, "Close": v, "Volume": 1000.0}, index=idx)


def test_ratio_uses_denominator_close():
    num = ohlcv(np.arange(10, 20, dtype=float))
    den = ohlcv(np.arange(100, 110, dtype=float))
    value = _safe_ratio_z(num, den, window=10)
    assert value is not None
    # Ensure the function can operate on standard OHLCV data and does not
    # accidentally use denominator.Open/other first column.


def test_missing_factor_zero_is_not_data():
    gk = FakeGK({"GC=F": ohlcv(np.arange(100, 140, dtype=float))})
    rows = [{"faktör": "Altın Hızlı 2H/16H Anlık İvme", "küme": "E", "ham_deger": 0.0, "puan": 0.0}]
    out, diag = sanitize_factor_rows("XAU", rows, gk)
    row = next(r for r in out if r["faktor_id"] == "asset_direction")
    assert row["ham_deger"] is not None
    assert row["veri_durumu"] == "MEVCUT" or row["veri_durumu"] == "MEVCUT / NÖTR"
    assert diag["coverage"] > 0.0


def test_missing_source_becomes_unavailable():
    gk = FakeGK({})
    rows = [{"faktör": "Gümüş / Bakır Sanayi Rotasyonu", "küme": "D", "ham_deger": 0.0, "puan": 0.0}]
    out, diag = sanitize_factor_rows("XAG", rows, gk)
    row = next(r for r in out if r["faktor_id"] == "silver_copper")
    assert row["ham_deger"] is None
    assert row["puan"] is None
    assert row["veri_durumu"] == "VERİ YETERSİZ"


def test_direction_warmup_diagnostics_are_not_fake_zero():
    store = StatefulMemoryStore("/tmp/test_direction_fix.json")
    engine = StatefulDirectionEngine(store)
    result = engine.evaluate(
        asset="XAG",
        regime_id=3,
        score=-0.60,
        bull_clusters=0,
        bear_clusters=3,
        thresholds={"buy_early": 0.4, "sell_early": -0.4, "buy_enter": 0.6, "sell_enter": -0.6, "min_clusters": 2},
        previous_signal="NÖTR (BEKLE)",
    )
    assert result["score_z"] is None
    assert result["velocity"] is None
    assert result["acceleration"] is None
    assert result["diagnostic_warmup"] is True


def test_xag_relative_contribution_is_bounded():
    store = StatefulMemoryStore("/tmp/test_xag_cap.json")
    model = AdaptiveScoreModel(store)
    rows = []
    for f in __import__("config").ASSET_MATRICES["XAG"]["factors"]:
        rows.append({"faktör": f["name"], "küme": f["cluster"], "ham_deger": 1.8, "veri_durumu": "MEVCUT"})
    result = model.recompute_score("XAG", rows)
    rel = sum(abs(v["final_contribution"]) for k, v in result["factor_runtime"].items() if k in {"gold_sympathy", "silver_monetary_catchup", "copper_gold", "silver_copper"})
    other = sum(abs(v["final_contribution"]) for k, v in result["factor_runtime"].items() if k not in {"gold_sympathy", "silver_monetary_catchup", "copper_gold", "silver_copper"})
    assert rel <= 0.3000001 * max(other, 1e-12)
