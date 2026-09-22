import numpy as np
import pandas as pd

from xau_xag_dynamic_pair import DynamicXAU_XAGModel


def make_pair():
    idx = pd.date_range("2026-01-01", periods=80, freq="h", tz="UTC")
    base = np.array([0.0008,0.0012,0.0006,0.0011,0.0009,0.0013,0.0007,0.0010]*10, dtype=float)
    au_close = 100 * np.cumprod(1 + base)
    ag_close = 50 * np.cumprod(1 + base * 1.02)
    hg_close = 4.0 * np.cumprod(1 + base * 0.7)
    return {
        "GC": pd.DataFrame({"Close": au_close}, index=idx),
        "SI": pd.DataFrame({"Close": ag_close}, index=idx),
        "HG": pd.DataFrame({"Close": hg_close}, index=idx),
    }


def test_pair_model_requires_real_residual_for_divergence():
    grid = make_pair()
    state = DynamicXAU_XAGModel(window=72).fit(grid)
    assert state["available"] is True
    assert state["divergence_supported"] is False
    assert 0.0 <= state["coherence_blend"] <= 0.25


def test_pair_model_does_not_force_xau_to_follow_xag():
    grid = make_pair()
    state = DynamicXAU_XAGModel(window=72).fit(grid)
    xau, xag = DynamicXAU_XAGModel.reconcile_scores(0.10, 1.00, state)
    assert xau > 0.10
    assert xag < 1.00
    assert xau != 1.00
