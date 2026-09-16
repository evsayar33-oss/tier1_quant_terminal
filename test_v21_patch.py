import importlib.util
import numpy as np
import pandas as pd

PATCH = "v21_patch.py"

spec = importlib.util.spec_from_file_location("v21_patch_test", PATCH)
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

def make_df(duplicate_volume=False):
    now = pd.Timestamp.now(tz="UTC")
    idx = pd.date_range(end=now, periods=60, freq="h")
    close = np.linspace(100.0, 105.0, 60)
    data = {
        "Open": close,
        "High": close + 1.0,
        "Low": close - 1.0,
        "Close": close,
        "Volume": np.arange(60, dtype=float) + 1000.0,
    }
    if duplicate_volume:
        data["Volume_2"] = data["Volume"] + 1.0
        df = pd.DataFrame(data, index=idx)
        df = df.rename(columns={"Volume_2": "Volume"})
    else:
        df = pd.DataFrame(data, index=idx)
    return v._attach_quality(df, source="TEST", fetched_at=now)

def test_entry_gate_normal():
    df = make_df()
    allowed, reason, atr, rvol = v._v21_evaluate_trade_entry_gate(df, "SPX")
    assert isinstance(allowed, bool)
    assert np.isfinite(atr)
    assert np.isfinite(rvol)
    assert "LIVE/DIRECT" in reason or "Önerilmez" in reason

def test_duplicate_columns_do_not_crash():
    df = make_df(duplicate_volume=True)
    result = v._v21_evaluate_trade_entry_gate(df, "SPX")
    assert isinstance(result, tuple) and len(result) == 4

def test_missing_volume_blocks_execution():
    now = pd.Timestamp.now(tz="UTC")
    idx = pd.date_range(end=now, periods=60, freq="h")
    close = np.linspace(100.0, 105.0, 60)
    df = pd.DataFrame({
        "Open": close, "High": close + 1, "Low": close - 1,
        "Close": close, "Volume": np.nan
    }, index=idx)
    df = v._attach_quality(df, source="TEST", fetched_at=now)
    allowed, reason, atr, rvol = v._v21_evaluate_trade_entry_gate(df, "SPX")
    assert allowed is False
    assert rvol == 0.0

if __name__ == "__main__":
    test_entry_gate_normal()
    test_duplicate_columns_do_not_crash()
    test_missing_volume_blocks_execution()
    print("V2.1.2 regression tests: PASS")
