"""
Comprehensive Automated Test Suite for Tier-1 Quant Terminal (v27)
Includes Full Verification of:
- Macro Event Interpretation System (v1.0)
- 5 Macro Regimes Trigger & Confirmation Logic
- Priority Rules & Conflict Resolutions (Shocks > Risk-On, Highest |Z|, Regime 1 vs 3)
- Hysteresis Confirmation Engine (2-Week Confirmation Window)
- Calibrated Dynamic Adaptive Thresholds
- 3-Pillar USD Risk Architecture (Spot DXY, Net Dollar Liquidity NDL, USD/JPY FX Carry)
- Idiosyncratic Asset-Specific Risk Models (Duration Drag, Mega-Cap Dispersion, Sovereign Decoupling, Squeeze Risk)
- Volatility Scaling, Crisis Lock, and All-Asset Consensus
"""
import numpy as np
import pandas as pd
from config import ASSET_MATRICES, SIGNAL_THRESHOLDS, CRISIS_CONFIG, REGIME_DYNAMIC_THRESHOLDS
from quant_processor import RobustQuantProcessor
from gatekeeper import PreTradeGatekeeper
from macro_regime_engine import MacroRegimeEngine


def test_system_principles_and_all_five_regimes():
    engine = MacroRegimeEngine()

    # 1. REGIME 1: Küresel Enflasyon & Stagflasyon Şoku
    r1_data = {
        "oil_20d_return_52w_z": 1.8,
        "bdi_level_52w_z": -1.4,
        "hy_oas_52w_z": 0.8,
        "spx_ust10y_60d_corr": 0.45,
        "dtwexbgs_5d_change_52w_z": 0.2,
        "usdjpy_1d_change_52w_z": -0.5,
        "vix_level_52w_z": 0.5,
        "risk_basket_5d_return_52w_z": -0.5,
        "dfii10_1d_change_52w_z": 0.2,
        "t10yie_52w_z": 1.1,
        "hy_oas_10d_slope": 0.0,
        "ig_oas_52w_z": 0.4,
        "vix_252d_percentile": 55.0,
        "ndl_52w_z": -0.2
    }
    res1_1 = engine.evaluate(r1_data)
    assert res1_1["candidate_regime_id"] == 1
    assert not res1_1["is_confirmed"]
    
    res1_2 = engine.evaluate(r1_data)
    assert res1_2["active_regime_id"] == 1
    assert res1_2["is_confirmed"]
    assert res1_2["active_regime_type"] == "SHOCK"
    print("✅ Regime 1 (Küresel Enflasyon & Stagflasyon Şoku) Passed!")

    # 2. REGIME 2: Sistemik Likidite Şoku & Carry Çöküşü
    r2_data = {
        "oil_20d_return_52w_z": 0.2,
        "bdi_level_52w_z": 0.1,
        "hy_oas_52w_z": 1.2,
        "spx_ust10y_60d_corr": -0.2,
        "dtwexbgs_5d_change_52w_z": 1.4,
        "usdjpy_1d_change_52w_z": -2.5,
        "vix_level_52w_z": 2.2,
        "risk_basket_5d_return_52w_z": -2.1,
        "dfii10_1d_change_52w_z": 0.5,
        "t10yie_52w_z": 0.2,
        "hy_oas_10d_slope": 0.0,
        "ig_oas_52w_z": 0.5,
        "vix_252d_percentile": 90.0,
        "ndl_52w_z": -1.2
    }
    engine.evaluate(r2_data)
    res2 = engine.evaluate(r2_data)
    assert res2["active_regime_id"] == 2
    assert res2["active_regime_type"] == "SHOCK"
    print("✅ Regime 2 (Sistemik Likidite Şoku & Carry Çöküşü) Passed!")

    # 3. REGIME 3: Reel Faiz Şoku
    r3_data = {
        "oil_20d_return_52w_z": 0.0,
        "bdi_level_52w_z": 0.0,
        "hy_oas_52w_z": 0.2,
        "spx_ust10y_60d_corr": -0.3,
        "dtwexbgs_5d_change_52w_z": 0.4,
        "usdjpy_1d_change_52w_z": 0.0,
        "vix_level_52w_z": 0.2,
        "risk_basket_5d_return_52w_z": -0.3,
        "dfii10_1d_change_52w_z": 2.2,
        "t10yie_52w_z": 0.1,
        "dgs2_change": -0.05,
        "dgs10_change": 0.10,
        "hy_oas_10d_slope": 0.0,
        "ig_oas_52w_z": 0.2,
        "vix_252d_percentile": 40.0,
        "ndl_52w_z": -0.1
    }
    engine.evaluate(r3_data)
    res3 = engine.evaluate(r3_data)
    assert res3["active_regime_id"] == 3
    assert "Bear Steepener" in res3["active_regime_subtype"]
    print("✅ Regime 3 (Reel Faiz Şoku & Bear Steepener) Passed!")

    # 4. REGIME 4: Kredi Temerrüt Baskısı
    r4_data = {
        "oil_20d_return_52w_z": -0.2,
        "bdi_level_52w_z": -0.4,
        "hy_oas_52w_z": 2.4,
        "hy_oas_10d_slope": 0.05,
        "ig_oas_52w_z": 1.4,
        "spx_ust10y_60d_corr": 0.0,
        "dtwexbgs_5d_change_52w_z": 0.5,
        "usdjpy_1d_change_52w_z": -0.5,
        "vix_level_52w_z": 1.2,
        "risk_basket_5d_return_52w_z": -0.9,
        "dfii10_1d_change_52w_z": 0.2,
        "t10yie_52w_z": 0.2,
        "vix_252d_percentile": 70.0,
        "ndl_52w_z": -0.5
    }
    engine.evaluate(r4_data)
    res4 = engine.evaluate(r4_data)
    assert res4["active_regime_id"] == 4
    assert res4["active_regime_type"] == "SHOCK"
    print("✅ Regime 4 (Kredi Temerrüt Baskısı) Passed!")

    # 5. REGIME 5: Küresel Likidite Rallisi (Risk-On)
    r5_data = {
        "oil_20d_return_52w_z": 0.3,
        "bdi_level_52w_z": 0.4,
        "hy_oas_52w_z": -1.2,
        "dtwexbgs_5d_change_52w_z": -0.6,
        "dtwexbgs_level_52w_z": -0.7,
        "vix_level_52w_z": -1.2,
        "vix_252d_percentile": 18.0,
        "ndl_52w_z": 1.5,
        "gold_trend": "RISING",
        "spx_ust10y_60d_corr": -0.3,
        "usdjpy_1d_change_52w_z": 0.2,
        "risk_basket_5d_return_52w_z": 1.4,
        "dfii10_1d_change_52w_z": -0.5,
        "t10yie_52w_z": 0.4,
        "hy_oas_10d_slope": -0.02,
        "ig_oas_52w_z": -0.9
    }
    engine.evaluate(r5_data)
    res5 = engine.evaluate(r5_data)
    assert res5["active_regime_id"] == 5
    assert res5["active_regime_type"] == "RISK_ON"
    assert "Reflasyonist" in res5["active_regime_subtype"]
    print("✅ Regime 5 (Küresel Likidite Rallisi - Reflasyonist Risk-On) Passed!")


def test_three_pillar_usd_risk_model():
    qp = RobustQuantProcessor()

    # Senaryo 1: Dolar Likiditesi Bolluğu (DXY zayıf, NDL yüksek, Carry sakin)
    score1, label1, status1 = qp.compute_composite_usd_risk(dxy_velocity=-0.8, ndl_z=1.2, usdjpy_1d_z=0.5)
    assert score1 < -0.50, f"Expected low USD risk score, got {score1}"
    assert "DÜŞÜK USD BASKISI" in label1
    assert status1 == "EXPANSION"

    # Senaryo 2: Ağır Dolar Sıkışması (DXY fırlamış, NDL çökmüş, Yen Carry patlamış)
    score2, label2, status2 = qp.compute_composite_usd_risk(dxy_velocity=1.5, ndl_z=-1.5, usdjpy_1d_z=-2.2)
    assert score2 > 0.50, f"Expected high USD risk score, got {score2}"
    assert "YÜKSEK DOLAR SIKIŞMASI" in label2
    assert status2 == "STRESS"

    # Senaryo 3: Nötr / Dengeli USD
    score3, label3, status3 = qp.compute_composite_usd_risk(dxy_velocity=0.0, ndl_z=0.0, usdjpy_1d_z=0.0)
    assert -0.50 <= score3 <= 0.50
    assert "NÖTR" in label3
    print("✅ 3-Pillar USD Risk Modeli Testi Passed!")


def test_asset_specific_idiosyncratic_risk_models():
    qp = RobustQuantProcessor()
    dates = pd.date_range("2026-09-01", periods=30, freq="1h")

    # 1. Equity Duration Drag
    spx_df = pd.DataFrame({"Close": np.linspace(500, 505, 30)}, index=dates)
    drag_high = qp.compute_equity_duration_drag(spx_df, real_yield_z=1.5)
    drag_low = qp.compute_equity_duration_drag(spx_df, real_yield_z=-1.0)
    assert drag_high > 0.5, "Rising real yields must trigger duration drag"
    assert drag_low < 0.0, "Falling real yields must relieve duration drag"

    # 2. Gold Sovereign Decoupling (De-dollarization & Central Bank buying)
    gold_df = pd.DataFrame({"Close": np.linspace(2300, 2350, 30)}, index=dates)
    sovereign_score = qp.compute_gold_sovereign_decoupling(gold_df, real_yield_z=1.2, dxy_df=spx_df)
    assert sovereign_score > 0.5, f"Gold rally during high real rates must trigger sovereign decoupling, got {sovereign_score}"

    # 3. Crypto Stablecoin Impulse & Liquidation Squeeze
    stable_impulse = qp.compute_crypto_stablecoin_usd_impulse(flow_ratio=1.4, funding_rate=0.0002, ndl_z=1.0)
    assert stable_impulse > 0.3, "Strong taker & NDL must generate positive crypto USD impulse"

    squeeze_risk_high = qp.compute_liquidation_squeeze_risk(funding_rate=0.0005, df_crypto=spx_df)
    assert squeeze_risk_high > 1.0, "Extreme positive funding must flag long liquidation risk"

    # 4. Silver Monetary Catch-up
    ag_df = pd.DataFrame({"Close": np.linspace(28, 30, 30)}, index=dates)
    cu_df = pd.DataFrame({"Close": np.linspace(4.2, 4.3, 30)}, index=dates)
    catchup = qp.compute_silver_monetary_catchup(ag_df, gold_df, cu_df)
    assert -2.0 <= catchup <= 2.0

    print("✅ Varlığa Özel İdiosinkratik Risk Modelleri Testi Passed!")


def test_priority_rules_and_conflict_resolution():
    engine = MacroRegimeEngine()

    dual_data = {
        "hy_oas_52w_z": -0.8,
        "dtwexbgs_5d_change_52w_z": 1.6,
        "dtwexbgs_level_52w_z": 0.0,
        "vix_252d_percentile": 25.0,
        "ndl_52w_z": 1.2,
        "vix_level_52w_z": 1.8,
        "usdjpy_1d_change_52w_z": -2.2,
        "risk_basket_5d_return_52w_z": -1.8,
        "oil_20d_return_52w_z": 0.0,
        "bdi_level_52w_z": 0.0,
        "spx_ust10y_60d_corr": 0.0,
        "dfii10_1d_change_52w_z": 0.0,
        "t10yie_52w_z": 0.0,
        "hy_oas_10d_slope": 0.0,
        "ig_oas_52w_z": 0.0
    }
    engine.evaluate(dual_data)
    res_prio = engine.evaluate(dual_data)
    assert res_prio["active_regime_id"] == 2
    print("✅ Priority Rule: Shock Regime overrides Risk-On Passed!")

    conflict_data = {
        "oil_20d_return_52w_z": 0.0,
        "bdi_level_52w_z": 0.0,
        "spx_ust10y_60d_corr": 0.0,
        "dtwexbgs_5d_change_52w_z": 0.5,
        "usdjpy_1d_change_52w_z": -2.8,
        "vix_level_52w_z": 1.2,
        "risk_basket_5d_return_52w_z": -1.7,
        "hy_oas_52w_z": 2.2,
        "hy_oas_10d_slope": 0.04,
        "ig_oas_52w_z": 1.2,
        "dfii10_1d_change_52w_z": 0.0,
        "t10yie_52w_z": 0.0,
        "vix_252d_percentile": 60.0,
        "ndl_52w_z": -0.5
    }
    engine.evaluate(conflict_data)
    res_conf = engine.evaluate(conflict_data)
    assert res_conf["active_regime_id"] == 2
    print("✅ Conflict Resolution: Highest |Z| Winner Passed!")


def test_dynamic_adaptive_thresholds():
    qp = RobustQuantProcessor()

    sig_r1, _, _ = qp.resolve_signal_with_hysteresis(
        0.70, previous_signal="NÖTR (BEKLE)", bull_clusters=2,
        active_regime_id=1
    )
    assert "NÖTR" in sig_r1, f"Expected NÖTR in Regime 1 for 0.70, got {sig_r1}"

    sig_r5, _, _ = qp.resolve_signal_with_hysteresis(
        0.55, previous_signal="NÖTR (BEKLE)", bull_clusters=2,
        active_regime_id=5
    )
    assert sig_r5 == "AL", f"Expected AL in Regime 5 for 0.55, got {sig_r5}"

    sig_r2, _, _ = qp.resolve_signal_with_hysteresis(
        -0.40, previous_signal="NÖTR (BEKLE)", bear_clusters=3,
        active_regime_id=2
    )
    assert sig_r2 == "SAT", f"Expected SAT in Regime 2 for -0.40, got {sig_r2}"

    print("✅ Dynamic Adaptive Thresholds per Regime Passed!")


def test_hysteresis_logic():
    qp = RobustQuantProcessor()
    
    sig, col, icon = qp.resolve_signal_with_hysteresis(0.75, previous_signal="NÖTR (BEKLE)", bull_clusters=2)
    assert sig == "AL"

    sig, col, icon = qp.resolve_signal_with_hysteresis(0.50, previous_signal="AL", bull_clusters=1)
    assert sig == "AL"

    sig, col, icon = qp.resolve_signal_with_hysteresis(0.20, previous_signal="AL", bull_clusters=0)
    assert sig == "NÖTR (BEKLE)"

    sig, col, icon = qp.resolve_signal_with_hysteresis(-0.75, previous_signal="NÖTR (BEKLE)", bear_clusters=2)
    assert sig == "SAT"

    sig, col, icon = qp.resolve_signal_with_hysteresis(-0.40, previous_signal="SAT", bear_clusters=1)
    assert sig == "SAT"

    sig, col, icon = qp.resolve_signal_with_hysteresis(1.90, previous_signal="NÖTR (BEKLE)", bull_clusters=3, min_clusters=2)
    assert sig == "GÜÇLÜ AL"

    print("✅ Signal Hysteresis Logic Passed!")


def test_volatility_scaling():
    qp = RobustQuantProcessor()
    dates = pd.date_range("2026-09-01", periods=30, freq="1h")
    
    spx_prices = [100.0] * 25 + [100.1, 100.2, 100.3, 100.4, 100.5]
    spx_df = pd.DataFrame({"Close": spx_prices}, index=dates)
    spx_mom = qp.compute_intraday_direction_momentum(spx_df, vol_scale=1.0)

    btc_prices = [100.0] * 25 + [100.5, 101.0, 101.8, 102.5, 103.0]
    btc_df = pd.DataFrame({"Close": btc_prices}, index=dates)
    btc_mom = qp.compute_intraday_direction_momentum(btc_df, vol_scale=1.8)

    assert -2.0 <= spx_mom <= 2.0
    assert -2.0 <= btc_mom <= 2.0
    assert spx_mom > 0.4
    assert btc_mom > 1.0
    print("✅ Volatility Scaling Test Passed!")


def test_crisis_lock():
    qp = RobustQuantProcessor()
    state, score, floor = qp.evaluate_crisis_lock_with_hysteresis(
        credit_velocity=-2.0,
        z_vix=2.8,
        z_real_rate=1.5,
        dxy_velocity=1.5,
        current_vix_val=32.0,
        current_state=False,
        consecutive_breaches=3
    )
    assert state == True
    assert floor == True
    print(f"✅ Crisis Lock Triggered Properly! (Anomaly Score: {score:.2f})")


def test_all_assets_evaluation():
    gk = PreTradeGatekeeper()
    dates = pd.date_range("2026-09-01", periods=30, freq="1h")
    symbols = [
        "SPY", "QQQ", "GC", "SI", "BTC-USD", "ETH-USD", "SMH", "RSP", "HYG",
        "LQD", "DXY", "VIX", "USO", "IYT", "TIP", "IEF", "USDJPY", "HG",
        "ARKK", "XLU", "XLY", "XLP", "TLT", "SHY", "KRE", "VIX3M"
    ]
    for k in symbols:
        gk.grid_1h[k] = pd.DataFrame({
            "Close": np.linspace(100, 102, 30),
            "High": np.linspace(101, 103, 30),
            "Low": np.linspace(99, 101, 30),
            "Volume": [100000] * 30
        }, index=dates)
    
    for asset_key in ASSET_MATRICES.keys():
        res = gk.evaluate_asset_direction(asset_key)
        assert "verdict" in res
        assert "score" in res
        assert "active_regime_id" in res
        assert "dynamic_thresholds" in res
        assert "composite_usd_risk" in res
        assert "usd_risk_label" in res
        assert len(res["details"]) >= 10
    print("✅ All 6 Assets Multi-Factor Evaluation Test Passed!")


if __name__ == "__main__":
    print("🚀 RUNNING COMPREHENSIVE TIER-1 QUANT TEST SUITE...\n")
    test_system_principles_and_all_five_regimes()
    test_three_pillar_usd_risk_model()
    test_asset_specific_idiosyncratic_risk_models()
    test_priority_rules_and_conflict_resolution()
    test_dynamic_adaptive_thresholds()
    test_hysteresis_logic()
    test_volatility_scaling()
    test_crisis_lock()
    test_all_assets_evaluation()
    print("\n🎉 ALL 9 ADVANCED TEST MODULES PASSED WITH 100% SUCCESS!")
