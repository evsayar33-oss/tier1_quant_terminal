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


def test_model_zoo_pays_for_selection_luck():
    assert 2.7 < W.required_t(8) < 2.8          # best-of-8 must clear ~2.73, not 2.0
    assert abs(W.required_t(1) - 1.96) < 0.01


def test_optimize_records_all_candidates_and_regime_keys_are_normalised():
    fr, mr, c = _synthetic("SIG", True, 3, days=300)
    mr = [(a, t, (3 if i % 2 else "3.0"), s) for i, (a, t, _r, s) in enumerate(mr)]   # mixed types like the CSV
    panel = W.build_panel(fr, mr, {"SIG": c})
    res = W.optimize(panel, horizons=(24,), families=("ridge_regime", "equal"))
    m = res["assets"]["SIG"]
    assert len(m["candidates"]) == 2 and m["family"] in ("ridge_regime", "equal")
    assert set(m.get("regime_terms", {}).keys()) <= {"3"}


def test_advisory_policy_keeps_direction_live_but_closes_entry(tmp_path):
    import json, os
    import stateful_adaptive_controller as C
    from config import ASSET_MATRICES
    f = [x["id"] for x in ASSET_MATRICES["SPX"]["factors"]]
    model = {"assets": {"SPX": {"status": "OK", "deploy": False, "features": f, "mu": [0] * len(f), "sd": [1] * len(f),
                                "intercept": 0, "weights": [0] * len(f), "regime_terms": {}, "z_scale": 1,
                                "t_required": 2.73, "oos": {"ic": 0.01, "t_ic": 0.3, "learned": {}, "always_long": {},
                                                            "legacy_model": {}}}}}
    p = tmp_path / "lm.json"
    p.write_text(json.dumps(model))
    import config
    old = config.LEARNED_MODEL_PATH
    config.LEARNED_MODEL_PATH = str(p)
    C.StatefulAdaptiveController._LEARNED_CACHE.update({"mtime": None, "data": None, "path": None})
    try:
        ctrl = C.StatefulAdaptiveController.__new__(C.StatefulAdaptiveController)
        sm = {"score": -0.9, "bull_clusters": 0, "bear_clusters": 3}
        info = ctrl._apply_learned_model("SPX", 3, [], sm)
        assert info["learned_model_status"] == "NOT_PROVEN_ADVISORY"
        assert sm["score"] == -0.9                     # old score still drives direction/velocity
    finally:
        config.LEARNED_MODEL_PATH = old
        C.StatefulAdaptiveController._LEARNED_CACHE.update({"mtime": None, "data": None, "path": None})
