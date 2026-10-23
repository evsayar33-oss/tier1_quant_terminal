import os

import numpy as np
import pandas as pd

import clone_system as CS
import decision_log as DL
import forecast_ledger as FL


def _frames():
    idx = pd.date_range("2026-10-01", periods=24 * 22, freq="h", tz="UTC")
    c = 7000 * np.exp(np.cumsum(np.random.default_rng(0).normal(0, 0.002, len(idx))))
    return pd.DataFrame({"Open": c, "High": c * 1.001, "Low": c * 0.999, "Close": c}, index=idx)


def test_clone_runs_full_pipeline_separately(tmp_path):
    f = _frames()
    now = pd.Timestamp("2026-10-22 16:00", tz="UTC")          # 12:00 ET
    price = float(f["Close"][f.index <= now].iloc[-1])
    v = {"SPX": {"learned_model_status": "NOT_PROVEN", "verdict": "NÖTR"}}
    ctx = {"SPX": {"atr_1h": 10.0, "atr_1d": 60.0, "vol": {"s20": 0.008, "s252": 0.009},
                   "levels": {"price": price, "levels": [], "round_step": None}}}
    snaps = {"SPX": {"charm_flow_1d_usd": 4e9, "expected_move_1d": 70.0}}
    root = str(tmp_path / "clone")
    out = CS.run(v, ctx, snaps, {"SPX": f[f.index <= now]}, {}, ["SPX"], root=root, now=now)
    assert out["logic"].endswith("+klon1") and out["charm_override"] == ["SPX"] and out["rows"]["SPX"]["short"] == 1
    assert "clone_short_side" not in v["SPX"]                       # şampiyon değişmedi
    for fn in ("stop_ledger.csv", "forecast_ledger.csv", "decision_log.csv"):
        assert os.path.exists(os.path.join(root, fn))
    assert pd.read_csv(os.path.join(root, "decision_log.csv"))["logic"].iloc[0].endswith("+klon1")
    assert pd.read_csv(os.path.join(root, "forecast_ledger.csv"))["logic"].iloc[0].endswith("+klon1")
