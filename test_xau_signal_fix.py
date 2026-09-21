import numpy as np
import pandas as pd

import gatekeeper


def make_pair():
    idx = pd.date_range("2026-01-01", periods=40, freq="h", tz="UTC")
    base = np.array([0.0008,0.0012,0.0006,0.0011,0.0009,0.0013,0.0007,0.0010]*5, dtype=float)
    base[-1] = 0.0010
    au_close = 100 * np.cumprod(1 + base)
    ag_close = 50 * np.cumprod(1 + base * 1.02)
    xau = pd.DataFrame({"Open": au_close, "High": au_close * 1.001, "Low": au_close * 0.999, "Close": au_close}, index=idx)
    xag = pd.DataFrame({"Open": ag_close, "High": ag_close * 1.001, "Low": ag_close * 0.999, "Close": ag_close}, index=idx)
    return xau, xag


class Proc:
    @staticmethod
    def compute_direction_score(df):
        return (1.0, {"roc_1h": 0.01})

    @staticmethod
    def format_direction_score(score, roc):
        return ("🟢 YUKARI", "🟢", "lightgreen", roc)


def test_xau_follow_silver():
    xau, xag = make_pair()
    old = gatekeeper.ASSET_MATRICES
    gatekeeper.ASSET_MATRICES = {"XAU": {}, "XAG": {}}
    try:
        gk = gatekeeper.PreTradeGatekeeper.__new__(gatekeeper.PreTradeGatekeeper)
        gk.grid_1h = {"XAU": xau, "XAG": xag}
        gk.processor = Proc()
        gk.market_regime = "TREND"
        gk.active_macro_regime_id = "REJIMSIZ_GECIS"
        def fake(asset_key, previous_signal="NÖTR (BEKLE)"):
            if asset_key == "XAU":
                return {"verdict":"NÖTR (BEKLE)","forecast_direction":"NÖTR (BEKLE)","score":0.10, "current_direction":"⚪ YATAY", "current_icon":"⚪", "current_color":"gray"}
            return {"verdict":"AL","forecast_direction":"AL","score":1.00, "current_direction":"🟢 YUKARI", "current_icon":"🟢", "current_color":"lightgreen"}
        gk.evaluate_asset_direction = fake
        out = gk.evaluate_all_assets_harmonized({})
        assert out["XAU"]["verdict"] == "AL"
        assert out["XAG"]["verdict"] == "AL"
        assert out["XAU"]["xau_silver_lead_confirmation"].startswith("XAG AL")
    finally:
        gatekeeper.ASSET_MATRICES = old


def test_xau_bearish_is_not_overridden():
    xau, xag = make_pair()
    old = gatekeeper.ASSET_MATRICES
    gatekeeper.ASSET_MATRICES = {"XAU": {}, "XAG": {}}
    try:
        gk = gatekeeper.PreTradeGatekeeper.__new__(gatekeeper.PreTradeGatekeeper)
        gk.grid_1h = {"XAU": xau, "XAG": xag}
        gk.processor = Proc()
        def fake(asset_key, previous_signal="NÖTR (BEKLE)"):
            if asset_key == "XAU":
                return {"verdict":"SAT","forecast_direction":"SAT","score":-0.80, "current_direction":"🔴 AŞAĞI", "current_icon":"🔴", "current_color":"red"}
            return {"verdict":"AL","forecast_direction":"AL","score":1.00, "current_direction":"🟢 YUKARI", "current_icon":"🟢", "current_color":"lightgreen"}
        gk.evaluate_asset_direction = fake
        out = gk.evaluate_all_assets_harmonized({})
        assert out["XAU"]["verdict"] == "SAT"
    finally:
        gatekeeper.ASSET_MATRICES = old


if __name__ == "__main__":
    test_xau_follow_silver()
    test_xau_bearish_is_not_overridden()
    print("XAU-only regression tests: PASS")
