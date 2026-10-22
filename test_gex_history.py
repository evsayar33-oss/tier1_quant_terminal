"""v16.2 — historical GEX: magnitude factor is learned from data, applied only when proven and fresh."""
import numpy as np
import pandas as pd

import gex_history as GH
import stop_levels as SL


def _frame(effect=True, n=1500, seed=0):
    rng = np.random.default_rng(seed)
    gex = rng.normal(0, 1, n).cumsum() * 0.2 + rng.normal(0, 1, n)
    rank = pd.Series(gex).rolling(252, min_periods=120).apply(lambda v: (v <= v[-1]).mean(), raw=True).fillna(0.5).values
    scale = (1.4 - 0.8 * rank) if effect else np.ones(n)
    r = rng.normal(0, 0.01, n) * np.r_[1.0, scale[:-1]]          # GEX on day t sets the size of day t+1
    idx = pd.bdate_range("2012-01-02", periods=n)
    return pd.DataFrame({"price": 100 * np.exp(np.cumsum(r)), "dix": 0.4, "gex": gex}, index=idx)


def test_learns_compression_and_scales_by_quintile():
    d = _frame(True)
    r = GH.analyze(d, now=d.index[-1])
    assert r["proven"] and r["ic"] < 0 and all(t < 0 for t in r["ic_thirds"])
    assert r["quintile_table"][0] > r["quintile_table"][-1]
    assert r["move_factor"] == r["quintile_table"][r["quintile"] - 1]


def test_no_effect_or_stale_data_gives_neutral_factor():
    d = _frame(False, seed=3)
    assert GH.analyze(d, now=d.index[-1])["move_factor"] == 1.0
    d2 = _frame(True)
    assert GH.analyze(d2, now=d2.index[-1] + pd.Timedelta(days=30))["move_factor"] == 1.0


def test_parse_rejects_garbage_and_factor_widens_stop():
    assert GH.parse("<html>nope</html>") is None
    lv = {"price": 100.0, "levels": []}
    a = SL.suggest_stop(+1, "kisa", 100.0, atr_1h=1.0, levels=lv, move_factor=1.0)
    b = SL.suggest_stop(+1, "kisa", 100.0, atr_1h=1.0, levels=lv, move_factor=1.3)
    assert b["distance"] > a["distance"] and b["move_factor"] == 1.3
