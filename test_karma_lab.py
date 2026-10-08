"""Tests for karma_lab (v13.0): overlay timing has no look-ahead; no-boost overlay == base."""
import numpy as np
import pandas as pd

import karma_lab as K
from test_shock_lab import _market


def _px():
    px, fred = _market(seed=5, start="1998-01-01", end="2012-12-31")
    px["GC=F"] = px["^GSPC"] * 0 + 1000 * np.exp(np.cumsum(np.random.default_rng(1).normal(0, 0.01, len(px["^GSPC"]))))[:, None]
    return px, fred


def test_boost_one_equals_base_and_mask_is_lagged():
    px, fred = _px()
    C = K.closes(px)
    tb = pd.Series(0.02, index=C.index)
    on = pd.Series(False, index=C.index); on.iloc[500:540] = True
    assert np.allclose(K.risk_parity(C, tb), K.risk_parity(C, tb, on, 1.0))
    F = pd.DataFrame({"vix": np.where(np.arange(len(C)) == 300, 50.0, 15.0)}, index=C.index)
    v = {"trig": lambda F: F.vix >= 35, "gate": None, "days": 5}
    m = K.active_mask(F, v)
    assert not m.iloc[300] and m.iloc[301:306].all() and not m.iloc[306]     # applied from the NEXT day only


def test_future_prices_do_not_change_past_returns():
    px, fred = _px()
    C = K.closes(px)
    tb = pd.Series(0.02, index=C.index)
    a = K.risk_parity(C, tb)
    cut = C.index[2000]
    b = K.risk_parity(C[C.index <= cut], tb)
    assert np.allclose(a[a.index <= cut].values, b.values)
