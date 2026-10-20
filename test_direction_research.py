"""v16.0 — the direction research harness must find a planted edge and must NOT find one in noise."""
import numpy as np
import pandas as pd

import direction_research as DR


def _series(r):
    idx = pd.bdate_range("2010-01-01", periods=len(r))
    return pd.Series(100 * np.exp(np.cumsum(r)), index=idx)


def test_finds_planted_trend_persistence():
    rng = np.random.default_rng(0)
    n = 4000
    regime = np.repeat(rng.choice([-1, 1], n // 400 + 1), 400)[:n]   # long-lasting up/down regimes
    c = _series(regime * 0.0015 + rng.normal(0, 0.01, n))
    res = DR.research_asset(c)
    assert res["status"] == "OK" and res["proven"], res["best"]
    assert res["proven"][0]["rule"].startswith(("tsmom", "trend"))


def test_no_false_edge_in_random_walks():
    hits = 0
    for seed in range(8):
        rng = np.random.default_rng(100 + seed)
        res = DR.research_asset(_series(rng.normal(0.0002, 0.01, 4000)))
        hits += bool(res["proven"])
    assert hits <= 1            # Bonferroni + 3-period rule keeps false discoveries rare


def test_signals_are_causal():
    rng = np.random.default_rng(1)
    c = _series(rng.normal(0, 0.01, 600))
    a = DR.candidates(c)
    c2 = c.copy()
    c2.iloc[-50:] *= 3.0                       # change the future only
    b = DR.candidates(c2)
    for k in a:
        pd.testing.assert_series_equal(a[k].iloc[:-50], b[k].iloc[:-50], check_names=False)


def test_live_direction_uses_only_proven_rule():
    rng = np.random.default_rng(2)
    c = _series(np.r_[rng.normal(0, 0.01, 300), np.full(80, 0.004)])
    df = pd.DataFrame({"Close": c})
    res = {"assets": {"NQ": {"proven": [{"rule": "tsmom_60", "horizon_d": 5, "t_alpha": 3.1,
                                         "alpha_bps": 12.0, "hit": 0.55}]}}}
    out = DR.live_direction("NQ", df, res)
    assert out["side"] == 1 and out["rule"] == "tsmom_60"
    assert DR.live_direction("SPX", df, res) is None
    assert DR.live_direction("NQ", df, {"assets": {"NQ": {"proven": []}}}) is None


def test_proven_rule_drives_long_label_and_long_stop_side():
    import decision_panel as DP
    import stop_levels as SL
    v = {"verdict": "SAT", "learned_model_status": "NOT_PROVEN_ADVISORY",
         "research_direction": {"rule": "tsmom_120", "side": 1, "horizon_d": 5}}
    assert DP.long_label(v) == "🟢 AL · kanıtlı (Momentum 120 gün)"
    assert SL.long_side(v) == 1
    assert SL.long_side({"verdict": "SAT"}) == -1


def test_base_rate_is_reported_and_shown():
    import decision_panel as DP
    rng = np.random.default_rng(5)
    res = {"assets": {"NQ": DR.research_asset(_series(rng.normal(0.0005, 0.01, 4000)))}}
    b = DR.base_rate("NQ", res)
    assert b and 0.4 < b["up"] < 0.7 and b["horizon_d"] == 5
    lbl = DP.long_label({"verdict": "NÖTR (BEKLE)", "base_rate": b})
    assert "taban: %" in lbl and lbl.startswith("⚪ NÖTR")
