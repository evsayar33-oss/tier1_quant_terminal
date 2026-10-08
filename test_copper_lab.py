"""Copper lab tests: planted edge found in the sealed exam, pure noise not, no look-ahead, publication lags."""
import numpy as np
import pandas as pd

import copper_lab as C


def market(seed=0, planted=False, start="1998-01-01", end="2026-09-30"):
    rng = np.random.default_rng(seed)
    cal = pd.bdate_range(start, end)
    n = len(cal)
    dxy_r = rng.normal(0, 0.005, n)
    dxy = 90 * np.exp(np.cumsum(dxy_r))
    dmom = pd.Series(dxy).pct_change(63).shift(1).to_numpy()            # known before today's copper return
    cu_r = rng.normal(0.0002, 0.015, n)
    if planted:
        cu_r += 0.0012 * np.where(np.nan_to_num(dmom) < 0, 1.0, -1.0)    # copper rises when the dollar weakened
    px = {}

    def ohlc(r, p0):
        c = p0 * np.exp(np.cumsum(r))
        o = np.r_[c[0], c[:-1]]
        return pd.DataFrame({"Open": o, "High": np.maximum(o, c) * (1 + np.abs(rng.normal(0, 0.004, n))),
                             "Low": np.minimum(o, c) * (1 - np.abs(rng.normal(0, 0.004, n))), "Close": c}, index=cal)
    px["HG=F"] = ohlc(cu_r, 1.0)
    px["DX-Y.NYB"] = ohlc(dxy_r, 90)
    for s, v in (("GC=F", 0.01), ("SI=F", 0.018), ("CL=F", 0.02), ("^GSPC", 0.011), ("^NDX", 0.014), ("FCX", 0.025),
                 ("AUDUSD=X", 0.006), ("CNY=X", 0.002), ("FXI", 0.018), ("000001.SS", 0.015)):
        px[s] = ohlc(rng.normal(0.0002, v, n), 100)
    vix = 15 + 5 * np.abs(np.sin(np.arange(n) / 300)) + rng.normal(0, 1, n)
    px["^VIX"] = pd.DataFrame({"Open": vix, "High": vix, "Low": vix, "Close": vix}, index=cal)
    rows = []
    for sid, base in (("DFII10", 1.0), ("T10YIE", 2.0), ("T10Y2Y", 1.0), ("DGS3MO", 2.0), ("BAMLH0A0HYM2", 4.0)):
        v = base + np.cumsum(rng.normal(0, 0.02, n))
        rows += [(sid, d, x, d + pd.Timedelta(days=1)) for d, x in zip(cal, v)]
    fred = pd.DataFrame(rows, columns=["series", "date", "value", "avail"])
    wk = cal[cal.dayofweek == 1]
    cot = pd.DataFrame({"date": wk, "avail": wk + pd.Timedelta(days=6), "spec_long": rng.uniform(4e4, 8e4, len(wk)),
                        "spec_short": rng.uniform(4e4, 8e4, len(wk)), "oi": 2e5})
    return px, fred, cot


def test_planted_dollar_edge_found_and_noise_rejected():
    px, fred, cot = market(1, planted=True)
    R = C.research(px, fred, cot, fast=True)
    T = R["_table"]
    d = T[(T.strateji == "dolar (DXY) 3 ay düşüyor") & (T.yön == "çift yön")].iloc[0]
    assert d.eğitim_sharpe > 0.8 and d.sınav_sharpe > 0.8 and d.sınav_alfa_t > 2, d
    assert R["chosen"]["sınav_sharpe"] > 0.5                       # training choice survives the exam
    px0, fred0, cot0 = market(2, planted=False)
    R0 = C.research(px0, fred0, cot0, fast=True)
    T0 = R0["_table"]
    # in pure noise the training winner must NOT look like a discovery out of sample on average
    assert T0[T0.tür == "tek"].sınav_sharpe.mean() < 0.15
    assert R0["chosen"]["deflated_sharpe"] < 0.95
    md = C.report_md({k: v for k, v in R.items() if k != "_table"})
    assert "mühürlü sınav" in md


def test_views_do_not_look_ahead():
    px, fred, cot = market(3)
    F1 = C.frame(px, fred, cot)
    V1 = C.views(F1)
    cut = pd.Timestamp("2010-06-30")
    px2 = {k: v[v.index <= cut] for k, v in px.items()}
    F2 = C.frame(px2, fred[fred.avail <= cut], cot[cot.avail <= cut])
    V2 = C.views(F2)
    n = len(F2)
    for k in V2:
        if k.startswith(("ay mevsimselliği", "haftanın günü")):
            continue                                                # fixed per calendar year by design (only past years)
        a, b = np.nan_to_num(V1[k][1][:n]), np.nan_to_num(V2[k][1])
        assert np.allclose(a, b), k


def test_cot_used_only_after_publication():
    px, fred, cot = market(4)
    F = C.frame(px, fred, cot)
    d = cot.iloc[100]
    tue = d.date
    net = (d.spec_long - d.spec_short) / d.oi
    assert not np.isclose(F.spec_net.loc[tue + pd.Timedelta(days=3)], net)   # Friday: not yet usable
    assert np.isclose(F.spec_net.loc[tue + pd.Timedelta(days=6)], net)       # next Monday: usable


def test_returns_use_next_day_and_charge_costs():
    px, fred, cot = market(5)
    F = C.frame(px, fred, cot)
    pos = np.zeros(len(F)); pos[10] = 1
    ret = C.strat_returns(pos, F)
    assert np.isclose(ret[10], F.r.iloc[11] - C.COST - C.LONG_FUNDING / 252)
    assert np.isclose(ret[11], -C.COST)


if __name__ == "__main__":
    for k, f in list(globals().items()):
        if k.startswith("test_"):
            f()
            print("OK", k)
