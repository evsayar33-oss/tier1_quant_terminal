import numpy as np
import pandas as pd

import shadow_eval as SE
import shadow_ledger as SH


def _h1(n=24 * 40, seed=0):
    idx = pd.date_range("2026-09-01", periods=n, freq="h", tz="UTC")
    c = 100 * np.exp(np.cumsum(np.random.default_rng(seed).normal(0, 0.003, n)))
    return pd.DataFrame({"Open": c, "High": c * 1.002, "Low": c * 0.998, "Close": c}, index=idx)


def test_volume_profile_poc_inside_value_area():
    idx = pd.date_range("2026-10-21 13:30", periods=78, freq="5min", tz="UTC")
    c = np.r_[np.linspace(100, 101, 39), np.linspace(101, 100.5, 39)]
    vol = np.ones(78)
    vol[30:45] = 20
    df = pd.DataFrame({"High": c + 0.05, "Low": c - 0.05, "Close": c, "Volume": vol}, index=idx)
    vp = SH.volume_profile(df, pd.Timestamp("2026-10-22 15:00", tz="UTC"))
    assert vp and vp["val"] <= vp["poc"] <= vp["vah"] and abs(vp["poc"] - 101) < 0.3


def test_cycle_records_grades_and_eval_runs(tmp_path):
    f = _h1()
    p = str(tmp_path / "s.csv")
    snaps = {"SPX": {"charm_flow_1d_usd": 1e9, "call_wall": 0, "put_wall": 0, "pin_0dte": 0}}
    for t in f.index[24 * 2:24 * 38:1]:
        price = float(f["Close"][t])
        snaps["SPX"].update({"call_wall": price * 1.004, "put_wall": price * 0.996, "pin_0dte": price * 1.001})
        v = {"SPX": {"market_structure": {"levels": {"price": price}}}}
        SH.run_cycle(v, snaps, {"SPX": f}, {}, path=p, now=t)
    d = pd.read_csv(p)
    assert (d["graded"] == 1).sum() > 500 and d["shadow"].eq("shadow-v1").all()
    res = SE.evaluate(p)
    assert res["n_tests"] >= 3
    assert "H14 call_wall tutma" in res["tests"] and "H13a charm_1d → seans sonu" in res["tests"]
    assert SE.report(res)[0].startswith("# 🧪")
