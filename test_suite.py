
def test_dynamic_adaptive_thresholds():
    qp = RobustQuantProcessor()
    
    # 1. Choppy regime -> 0.70 score is blocked as NÖTR (TESTERE BANDI)
    sig_chop, _, _ = qp.resolve_signal_with_hysteresis(
        0.70, previous_signal="NÖTR (BEKLE)", bull_clusters=2,
        market_regime="⚪ MAKRO DENGE / SIKIŞMA", adx_val=16.0
    )
    assert "NÖTR" in sig_chop, f"Expected NÖTR in choppy regime, got {sig_chop}"
    
    # 2. Trending regime -> 0.70 score successfully triggers AL
    sig_trend, _, _ = qp.resolve_signal_with_hysteresis(
        0.70, previous_signal="NÖTR (BEKLE)", bull_clusters=2,
        market_regime="🟢 KÜRESEL LİKİDİTE RALLİSİ (RISK-ON)", adx_val=32.0
    )
    assert sig_trend == "AL", f"Expected AL in trending regime, got {sig_trend}"
    
    print("✅ Dynamic Adaptive Thresholds Test Passed!")
"""
Automated Test Suite for Tier-1 Quant Terminal
"""
import numpy as np
import pandas as pd
from config import ASSET_MATRICES, SIGNAL_THRESHOLDS, CRISIS_CONFIG
from quant_processor import RobustQuantProcessor
from gatekeeper import PreTradeGatekeeper


def test_hysteresis_logic():
    qp = RobustQuantProcessor()
    
    # 1. Neutral to AL
    sig, col, icon = qp.resolve_signal_with_hysteresis(0.75, previous_signal="NÖTR (BEKLE)", bull_clusters=2)
    assert sig == "AL", f"Expected AL, got {sig}"

    # 2. Retrace within deadband (0.50 is above buy_exit 0.25) -> Must STAY AL
    sig, col, icon = qp.resolve_signal_with_hysteresis(0.50, previous_signal="AL", bull_clusters=1)
    assert sig == "AL", f"Expected AL to persist due to hysteresis, got {sig}"

    # 3. Exit to NÖTR when falling below 0.25
    sig, col, icon = qp.resolve_signal_with_hysteresis(0.20, previous_signal="AL", bull_clusters=0)
    assert sig == "NÖTR (BEKLE)", f"Expected NÖTR (BEKLE), got {sig}"

    # 4. Neutral to SAT
    sig, col, icon = qp.resolve_signal_with_hysteresis(-0.75, previous_signal="NÖTR (BEKLE)", bear_clusters=2)
    assert sig == "SAT", f"Expected SAT, got {sig}"

    # 5. Retrace within deadband (-0.40 is below sell_exit -0.25) -> Must STAY SAT
    sig, col, icon = qp.resolve_signal_with_hysteresis(-0.40, previous_signal="SAT", bear_clusters=1)
    assert sig == "SAT", f"Expected SAT to persist, got {sig}"

    # 6. Exit to NÖTR when rising above -0.25
    sig, col, icon = qp.resolve_signal_with_hysteresis(-0.15, previous_signal="SAT", bear_clusters=0)
    assert sig == "NÖTR (BEKLE)", f"Expected NÖTR (BEKLE), got {sig}"

    # 7. Strong Buy with sufficient cluster confirmation
    sig, col, icon = qp.resolve_signal_with_hysteresis(1.90, previous_signal="NÖTR (BEKLE)", bull_clusters=3, min_clusters=2)
    assert sig == "GÜÇLÜ AL", f"Expected GÜÇLÜ AL, got {sig}"

    print("✅ Hysteresis Test Passed!")


def test_volatility_scaling():
    qp = RobustQuantProcessor()
    dates = pd.date_range("2026-09-01", periods=30, freq="1h")
    
    # SPX with 0.5% move (vol_scale = 1.0)
    spx_prices = [100.0] * 25 + [100.1, 100.2, 100.3, 100.4, 100.5]
    spx_df = pd.DataFrame({"Close": spx_prices}, index=dates)
    spx_mom = qp.compute_intraday_direction_momentum(spx_df, vol_scale=1.0)

    # BTC with 3.0% move (vol_scale = 1.8)
    btc_prices = [100.0] * 25 + [100.5, 101.0, 101.8, 102.5, 103.0]
    btc_df = pd.DataFrame({"Close": btc_prices}, index=dates)
    btc_mom = qp.compute_intraday_direction_momentum(btc_df, vol_scale=1.8)

    print(f"SPX Momentum: {spx_mom:.2f}, BTC Momentum: {btc_mom:.2f}")
    assert -2.0 <= spx_mom <= 2.0
    assert -2.0 <= btc_mom <= 2.0
    # Both should be well-behaved positive numbers, neither stuck at 0 nor wildly distorted
    assert spx_mom > 0.4
    assert btc_mom > 1.0
    print("✅ Volatility Scaling Test Passed!")


def test_crisis_lock():
    qp = RobustQuantProcessor()
    # Severe stress scenario: VIX at 32, high credit drop, soaring DXY
    state, score, floor = qp.evaluate_crisis_lock_with_hysteresis(
        credit_velocity=-2.0,
        z_vix=2.8,
        z_real_rate=1.5,
        dxy_velocity=1.5,
        current_vix_val=32.0,
        current_state=False,
        consecutive_breaches=3
    )
    assert state == True, "Expected crisis lock to trigger"
    assert floor == True, "Expected VIX floor active"
    print(f"✅ Crisis Lock Triggered Properly! (Anomaly Score: {score:.2f})")


def test_all_assets_evaluation():
    gk = PreTradeGatekeeper()
    # Populate mock grid for 6 assets
    dates = pd.date_range("2026-09-01", periods=30, freq="1h")
    for k in ["SPX", "NQ", "XAU", "XAG", "BTC", "ETH", "SMH", "RSP", "HYG", "LQD", "DXY", "VIX", "OIL", "IYT", "TIPS", "IEF", "USDJPY", "COPPER"]:
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
        assert "details" in res
        assert len(res["details"]) > 0
        print(f"Asset {asset_key}: Verdict={res['verdict']}, Score={res['score']:+.2f}, Clusters={res['cluster_agreement']}")
    print("✅ All 6 Assets Evaluation Test Passed!")



def test_calibrations():
    qp = RobustQuantProcessor()
    # 1. VIX 16.0 should be calm (negative or near-zero stress)
    dates = pd.date_range('2026-09-01', periods=30, freq='1h')
    vix_df = pd.DataFrame({'Close': [15.5]*25 + [16.0]*5}, index=dates)
    vix_stress = qp.compute_vix_stress(vix_df)
    assert vix_stress < 0.8, f'VIX at 16 should not produce high stress, got {vix_stress}'
    
    # 2. Crypto funding at normal 0.0001 must be 0.0 stress
    fr_stress = qp.compute_crypto_funding_stress(0.0001)
    assert abs(fr_stress) < 1e-5, f'Baseline funding should be 0, got {fr_stress}'
    
    # 3. Small oil/transport move should not explode stagflation
    oil_df = pd.DataFrame({'Close': [100.0]*25 + [102.0]*5}, index=dates)
    iyt_df = pd.DataFrame({'Close': [100.0]*25 + [99.5]*5}, index=dates)
    stag_z = qp.compute_stagflation_shock(oil_df, iyt_df)
    assert stag_z < 1.0, f'Small fluctuation should not trigger stagflation shock, got {stag_z}'
    print('✅ New Calibrations Test Passed!')

if __name__ == "__main__":
    test_calibrations()
    test_hysteresis_logic()
    test_volatility_scaling()
    test_crisis_lock()
    test_all_assets_evaluation()
    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")
