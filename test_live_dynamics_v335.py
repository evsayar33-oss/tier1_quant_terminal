"""v3.3.5: live-direction dynamics — regime hysteresis, event ageing,
threshold shrinkage, ATR without volume."""
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from quant_processor import RobustQuantProcessor as Q


def test_regime_label_has_hysteresis():
    first = Q.classify_intraday_regime(25.5, 1.0)["label"]
    assert first.startswith("GÜÇLÜ TREND")
    # small dip below 25 must not flip the label
    assert Q.classify_intraday_regime(23.5, 1.0, prev_label=first)["label"].startswith("GÜÇLÜ TREND")
    assert Q.classify_intraday_regime(21.0, 1.0, prev_label=first)["label"].startswith("GELİŞEN TREND")
    hv = Q.classify_intraday_regime(30, 1.40)["label"]
    assert "YÜKSEK" in Q.classify_intraday_regime(30, 1.30, prev_label=hv)["label"]


def _engine(tmp_path):
    from stateful_memory_store import StatefulMemoryStore
    from stateful_live_direction_engine import StatefulLiveDirectionEngine
    return StatefulLiveDirectionEngine(StatefulMemoryStore(path=tmp_path / "m.json"))


def test_regime_event_ages_out(tmp_path):
    eng = _engine(tmp_path)
    t0 = datetime(2026, 9, 30, 10, tzinfo=timezone.utc)
    eng.evaluate("SPX", "A · N", 0.5, 0.1, 0.1, now=t0)
    r1 = eng.evaluate("SPX", "B · N", 0.5, 0.1, 0.1, now=t0 + timedelta(minutes=5))
    r2 = eng.evaluate("SPX", "B · N", 0.5, 0.1, 0.1, now=t0 + timedelta(hours=3))
    assert r1["live_regime_event"] is True
    assert r2["live_regime_event"] is False          # old code: 'since' reset every write


def test_thresholds_shrink_to_asset_pool_and_stay_ordered(tmp_path):
    eng = _engine(tmp_path)
    t = datetime(2026, 9, 30, tzinfo=timezone.utc)
    rng = np.random.default_rng(0)
    for i in range(40):
        eng.evaluate("NQ", "POOL · N", float(rng.normal(0, 1)), 0, 0, now=t + timedelta(hours=4 * i))
    r = eng.evaluate("NQ", "RARE · N", 0.3, 0, 0, now=t + timedelta(days=30))
    th = r["live_thresholds"]
    assert th["p70"] >= 1.15 * th["p50"] - 1e-9 and th["p85"] >= 1.15 * th["p70"] - 1e-9
    assert abs(th["p50"] - 0.45) > 0.05                 # uses the asset pool, not the fixed bootstrap


def test_atr_survives_sparse_volume():
    from dynamic_entry_engine import StatefulDynamicEntryEngine
    idx = pd.date_range("2026-09-01", periods=200, freq="h", tz="UTC")
    c = 100 * np.exp(np.cumsum(np.random.default_rng(1).normal(0, 0.004, 200)))
    vol = np.zeros(200); vol[::6] = 1000.0            # ~17% bars with volume (BTC-like)
    df = pd.DataFrame({"Open": c, "High": c * 1.003, "Low": c * 0.997, "Close": c, "Volume": vol}, index=idx)
    p, err = StatefulDynamicEntryEngine().profile(df, now=idx[-1] + pd.Timedelta(hours=1))
    assert err is None and p["atr_ratio"] > 0 and p["volume_known"] is False


def test_data_quality_label_change_is_not_a_regime_event(tmp_path):
    eng = _engine(tmp_path)
    t0 = datetime(2026, 9, 30, 10, tzinfo=timezone.utc)
    eng.evaluate("BTC", "GELİŞEN TREND · VOLATİLİTE BİLİNMİYOR (VERİ YETERSİZ)", 0.3, 0, 0, now=t0)
    r = eng.evaluate("BTC", "GELİŞEN TREND · NORMAL VOLATİLİTE", 0.3, 0, 0, now=t0 + timedelta(minutes=10))
    assert r["live_regime_event"] is False
