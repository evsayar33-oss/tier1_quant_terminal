"""Tests for shock_lab (v12.0): trade walker, point-in-time macro data, planted vs noise, full run."""
import math

import numpy as np
import pandas as pd

import shock_lab as S


def _market(seed=0, planted=False, start="1990-01-01", end="2026-09-30"):
    rng = np.random.default_rng(seed)
    cal = pd.bdate_range(start, end)
    n = len(cal)
    r = rng.normal(0.0003, 0.009, n)
    infl = np.repeat(rng.choice([-1.0, 1.0], n // 150 + 1), 150)[:n]          # inflation regime (~7 months)
    crash = rng.random(n) < 0.004
    for i in np.where(crash)[0]:
        r[i:i + 5] -= 0.02                                                     # 5-day sell-off
        if planted and infl[i] < 0:                                            # rebound ONLY in low-inflation regimes
            r[i + 5:i + 45] += 0.004
    c = 1000 * np.exp(np.cumsum(r))
    o = np.r_[c[0], c[:-1]] * (1 + rng.normal(0, 0.001, n))
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, 0.004, n)))
    l = np.minimum(o, c) * (1 - np.abs(rng.normal(0, 0.004, n)))
    vol = pd.Series(r).rolling(10, min_periods=1).std().values * math.sqrt(252) * 100
    vix = 12 + 1.6 * vol + rng.normal(0, 1, n)
    px = {}
    for sym, mult in (("^GSPC", 1.0), ("^NDX", 1.3)):
        cc = 1000 * np.exp(np.cumsum(r * mult))
        oo = np.r_[cc[0], cc[:-1]]
        px[sym] = pd.DataFrame({"Open": oo, "High": np.maximum(oo, cc) * 1.004, "Low": np.minimum(oo, cc) * 0.996, "Close": cc}, index=cal)
    px["^VIX"] = pd.DataFrame({"Open": vix, "High": vix, "Low": vix, "Close": vix}, index=cal)
    px["^VIX3M"] = pd.DataFrame({"Open": vix * 0.9 + 3, "High": vix, "Low": vix, "Close": vix * 0.9 + 3}, index=cal)
    rows = []
    for d, v in zip(cal, 2.0 + 0.6 * infl + rng.normal(0, 0.05, n)):
        rows.append(("T10YIE", d, v, d + pd.Timedelta(days=1)))
    for d in cal[::5]:
        rows.append(("DGS3MO", d, 2.0, d + pd.Timedelta(days=1)))
    fred = pd.DataFrame(rows, columns=["series", "date", "value", "avail"])
    return px, fred


def test_walk_stop_first_and_trailing():
    O = np.array([100, 100, 100, 100.0]); H = np.array([100, 106, 100, 100.0]); L = np.array([100, 94, 100, 100.0])
    C = np.array([100, 100, 100, 100.0]); z = np.zeros(4); atr = np.full(4, 0.01)
    r, hd = S._walk(0, 100.0, O, H, L, C, atr, z, z, z, z, 1, 0.05, 0.05, 10, 0.0)    # TP 5% and SL 5% both touched
    assert math.isclose(r, -0.05) and hd == 1                                         # the stop counts first
    H2 = np.array([100, 110, 100, 100.0]); L2 = np.array([100, 99, 99, 96.0]); C2 = np.array([100, 109, 100, 97.0]); O2 = np.array([100, 101, 108, 99.0])
    r, hd = S._walk(0, 100.0, O2, H2, L2, C2, atr, z, z, z, z, 3, 0.08, 0.0, 10, 0.0)  # 8% trailing from the 110 peak = 101.2
    assert hd == 2 and math.isclose(r, 101.2 / 100 - 1)
    r, hd = S._walk(0, 100.0, O2, H2, L2, C2, atr, z, z, z, z, 0, 0.0, 0.0, 2, 0.0)   # fixed hold: close of bar e+2
    assert hd == 2 and math.isclose(r, 0.0)


def test_macro_values_only_after_publication():
    cal = pd.bdate_range("2020-01-01", periods=30)
    fred = pd.DataFrame({"series": "T10YIE", "date": cal, "value": np.arange(30.0), "avail": cal + pd.Timedelta(days=3)})
    s = S._asof(fred, "T10YIE", cal)
    for i, d in enumerate(cal):
        known = fred[fred.avail <= d]
        exp = known.value.iloc[-1] if len(known) else np.nan
        assert (np.isnan(exp) and np.isnan(s.iloc[i])) or s.iloc[i] == exp


def test_features_do_not_look_ahead():
    px, fred = _market(seed=1, end="2000-12-31")
    F1 = S.features(px, fred, "SPX")
    cut = pd.Timestamp("1998-06-30")
    px2 = {k: v[v.index <= cut] for k, v in px.items()}
    F2 = S.features(px2, fred[fred.avail <= cut], "SPX")
    A, B = F1.loc[:cut], F2
    for c in B.columns:
        a, b = A[c].values, B[c].values
        assert np.allclose(np.nan_to_num(a, nan=-9e9), np.nan_to_num(b, nan=-9e9)), c


def test_planted_regime_is_found_and_noise_is_not():
    px, fred = _market(seed=2, planted=True)
    res = S.research(px, fred, None, assets=("SPX",), fast=True)
    r = res["assets"]["SPX"]
    hy = r["hypothesis_2003_2016"]
    assert hy and np.mean([h["düşük_ort"] > h["yüksek_ort"] for h in hy]) > 0.7, hy
    flt = {f["filtre"]: f for f in r["fam_filter"]}
    assert flt["enflasyon beklentisi DÜŞÜK (z<0.5)"]["sınav"] > flt["enflasyon beklentisi YÜKSEK (z≥0.5)"]["sınav"]
    md = S.report_md({k: v for k, v in res.items()})
    assert "mühürlü" in md and "SPX" in md
    # noise market: shocks add nothing over a random entry in the exam
    px0, fred0 = _market(seed=3, planted=False)
    r0 = S.research(px0, fred0, None, assets=("SPX",), fast=True)["assets"]["SPX"]
    shock_avg = np.mean([f["sınav"] for f in r0["fam_shock"]])
    assert shock_avg < 0.03, shock_avg
