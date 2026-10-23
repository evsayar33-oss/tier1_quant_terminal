import pandas as pd

import decision_log as DL
import shock_monitor as SM


def test_hourly_snapshot_with_logic_version(tmp_path):
    p = str(tmp_path / "d.csv")
    v = {"SPX": {"current_direction": "⚪ YATAY", "market_structure": {"levels": {"price": 7680.0}}}}
    t = pd.Timestamp("2026-10-23 12:10", tz="UTC")
    assert DL.record(v, ["SPX"], path=p, now=t) == 1
    assert DL.record(v, ["SPX"], path=p, now=t + pd.Timedelta(minutes=20)) == 0     # aynı saat
    d = pd.read_csv(p)
    assert d.loc[0, "logic"] and d.loc[0, "price"] == 7680.0
    assert any(c.startswith("basit · ") for c in d.columns) and any(c.startswith("detay · ") for c in d.columns)


def test_closed_session_is_not_a_failure():
    import numpy as np
    idx = pd.date_range("2026-10-20", periods=300, freq="5min", tz="UTC")
    df = pd.DataFrame({"Close": 100 * np.exp(np.cumsum(np.random.default_rng(1).normal(0, 0.001, 300)))}, index=idx)
    s = SM.detect({"EEM": df}, idx[-1] + pd.Timedelta(hours=10))
    assert s["closed"] == ["EEM"] and s["failed"] == []
