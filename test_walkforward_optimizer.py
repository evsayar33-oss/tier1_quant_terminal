"""v3.4 tests: self-optimising walk-forward model + live-learner sign fix."""
import numpy as np
import pandas as pd

import walkforward_optimizer as W


def _synthetic(asset, signal, seed, days=420):
    rng = np.random.default_rng(seed)
    H = 24 * days
    idx = pd.date_range("2025-01-01", periods=H, freq="h", tz="UTC")
    k = 4
    F = np.zeros((H, k))
    for j in range(k):
        e = rng.normal(0, 1, H)
        for i in range(1, H):
            F[i, j] = 0.995 * F[i - 1, j] + 0.0999 * e[i]
    mu = (0.00015 * F[:, 0] - 0.00015 * F[:, 1]) if signal else np.zeros(H)
    close = pd.Series(100 * np.exp(np.cumsum(mu + rng.normal(0, 0.004, H))), index=idx)
    fr, mr = [], []
    for t in idx[::3][60:]:
        i = idx.get_loc(t)
        for j in range(k):
            fr.append((asset, t, f"x{j}", "n", "E", float(np.clip(F[i, j], -1.8, 1.8))))
        mr.append((asset, t, "3", 0.0))
    return fr, mr, close


def test_recovers_signal_flips_reversed_factor_and_rejects_noise():
    fr1, mr1, c1 = _synthetic("SIG", True, 1)
    fr2, mr2, c2 = _synthetic("NOISE", False, 2)
    panel = W.build_panel(fr1 + fr2, mr1 + mr2, {"SIG": c1, "NOISE": c2})
    res = W.optimize(panel)
    sig, noise = res["assets"]["SIG"], res["assets"]["NOISE"]
    w = dict(zip(sig["features"], sig["weights"]))
    assert sig["deploy"] is True
    assert w["x0"] > 0 and w["x1"] < 0            # reversed factor is flipped, not just down-weighted
    assert noise["deploy"] is False


def test_forward_returns_never_use_data_before_t_or_after_horizon():
    idx = pd.date_range("2025-01-01", periods=200, freq="h", tz="UTC")
    close = pd.Series(np.arange(1, 201, dtype=float), index=idx)
    t = idx[50]
    panel = W.build_panel([("A", t, "x0", "n", "E", 0.1)], [("A", t, "3", 0.0)], {"A": close})
    assert abs(panel["r24"].iloc[0] - np.log(75 / 51)) < 1e-12
    assert abs(panel["past_24h"].iloc[0] - np.log(51 / 27)) < 1e-12


def test_score_live_applies_regime_terms_and_reports_missing():
    m = {"status": "OK", "features": ["a", "b"], "mu": [0, 0], "sd": [1, 1], "intercept": 0.1,
         "weights": [0.5, -0.5], "regime_terms": {"3": {"intercept": 0.0, "weights": [0.5, 0.0]}}, "z_scale": 1.0}
    r_base = W.score_live(m, {"a": 1.0}, "2")
    r_reg = W.score_live(m, {"a": 1.0}, "3")
    assert r_reg["z"] > r_base["z"] and r_base["missing"] == ["b"]


def test_live_learner_uses_signed_values_and_migrates_old_stats(tmp_path):
    from stateful_memory_store import StatefulMemoryStore
    from config import ASSET_MATRICES
    neg = next(f["id"] for f in ASSET_MATRICES["SPX"]["factors"] if float(f.get("base_sign", 1)) < 0)
    s = StatefulMemoryStore(path=tmp_path / "m.json")
    # pre-v3.4 raw stats: raw value positively related to returns => factor (sign -1) is WRONG
    for i in range(200):
        x = 1.0 if i % 2 else -1.0
        s.record_factor_outcome("SPX", neg, x, 0.01 * x)
    ic_before, _ = s.factor_ic("SPX", neg)
    s.migrate_factor_signs_v34()
    ic_after, _ = s.factor_ic("SPX", neg)
    assert ic_before > 0 and ic_after < 0
    assert s.factor_weight_multiplier("SPX", neg)["multiplier"] < 0.65   # can now be switched off
