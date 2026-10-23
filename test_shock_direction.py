import numpy as np
import pandas as pd

import shock_direction as SD


def _closes(seed=0, effect=0.02):
    idx = pd.bdate_range("2013-01-01", "2026-10-22")
    rng = np.random.default_rng(seed)
    out = {}
    for k in SD.PANEL_D:
        out[k] = pd.Series(rng.normal(0.0003, 0.01, len(idx)), index=idx)
    # Petrol şoku (↑, z ≥ 3) → altın sonraki gün +effect (bilinen etki)
    shock_days = idx[300::60]
    out["CL"][shock_days] = 0.06
    for d in shock_days:
        j = idx.get_loc(d)
        if j + 1 < len(idx):
            out["GC"].iloc[j + 1] += effect
    return {k: 100 * np.exp(r.cumsum()) for k, r in out.items()}, shock_days


def test_study_finds_planted_effect_and_rejects_noise():
    closes, _ = _closes()
    res = SD.study(closes)
    proven = {(x["type"], x["asset"], x["h"]) for x in res["proven"]}
    assert ("petrol_yukari", "XAU", 1) in proven
    assert all(x["type"] == "petrol_yukari" for x in res["proven"])        # gürültüden sahte kural yok
    assert res["t_required"] > 2.5 and res["n_tests"] >= 6


def test_live_activates_only_recent_proven_rule():
    closes, days = _closes()
    res = SD.study(closes)
    last = days[-1]
    out = SD.live({k: v[v.index <= last] for k, v in closes.items()}, res, now=last)
    assert out["assets"]["XAU"]["side"] == 1 and out["assets"]["XAU"]["days_left"] == 1
    later = SD.live({k: v[v.index <= last + pd.Timedelta(days=7)] for k, v in closes.items()}, res,
                    now=last + pd.Timedelta(days=7))
    assert "XAU" not in later["assets"]


def test_evidence_priority():
    import stop_levels as SL
    v = {"shock_direction": {"side": -1, "h": 5}, "base_rate": {"up": 0.63, "n": 503}}
    assert SL.evidence_long_side(v) == -1
    v2 = {"shock_direction": {"side": 1, "h": 1}, "learned_model_status": "NOT_PROVEN", "recent_move": {"z": -2}}
    assert SL.evidence_short_side(v2) == 1
