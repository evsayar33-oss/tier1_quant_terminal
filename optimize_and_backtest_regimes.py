"""
Backtest & Threshold Optimization Engine for Macro Event Interpretation System v1.0
Simulates market behavior across all 5 Macro Regimes + Fallback Transition:
1. Küresel Enflasyon & Stagflasyon Şoku (Shock)
2. Sistemik Likidite Şoku & Carry Çöküşü (Shock)
3. Reel Faiz Şoku (Shock)
4. Kredi Temerrüt Baskısı (Shock)
5. Küresel Likidite Rallisi (Risk-On)
6. REJIMSIZ_GECIS (Fallback / Transitional)

Performs grid search to discover the mathematically optimal dynamic thresholds for each regime,
maximizing Sharpe Ratio, Win Rate, and Profit Factor while minimizing Max Drawdown.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone

np.random.seed(42)

def generate_multi_regime_dataset(n_bars_per_regime=300):
    """
    Generates synthetic realistic market data covering all 5 macro regimes and transitions.
    Includes: SPY, QQQ, GC=F (Gold), SI=F (Silver), BTC-USD, ETH-USD,
    plus macro series: CL=F (Oil), BDRY/IYT, HY OAS, IG OAS, DFII10, T10YIE, DTWEXBGS, USDJPY, VIX, NDL.
    """
    regimes_seq = [
        "REGIME_5_RISK_ON",
        "REGIME_1_STAGFLATION",
        "REGIME_3_REAL_YIELD",
        "REGIME_2_LIQUIDITY_SHOCK",
        "REGIME_4_CREDIT_STRESS",
        "REJIMSIZ_GECIS"
    ]
    
    total_bars = len(regimes_seq) * n_bars_per_regime
    dates = [datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(hours=i) for i in range(total_bars)]
    
    data = {"dates": dates, "regime": []}
    
    # Pre-allocate series
    assets = ["SPY", "QQQ", "GC=F", "SI=F", "BTC-USD", "ETH-USD"]
    macro_indicators = [
        "OIL_20D_Z", "BDI_Z", "HY_OAS_Z", "SPX_UST_CORR",
        "DTWEXBGS_5D_Z", "USDJPY_1D_Z", "VIX_LEVEL_Z", "RISK_BASKET_5D_Z",
        "DFII10_1D_Z", "T10YIE_Z", "DGS2_CHG", "DGS10_CHG",
        "HY_OAS_SLOPE", "IG_OAS_Z", "VIX_PCT", "NDL_Z"
    ]
    
    asset_prices = {a: [100.0] for a in assets}
    asset_prices["SPY"] = [500.0]
    asset_prices["QQQ"] = [450.0]
    asset_prices["GC=F"] = [2300.0]
    asset_prices["SI=F"] = [28.0]
    asset_prices["BTC-USD"] = [65000.0]
    asset_prices["ETH-USD"] = [3400.0]
    
    macro_series = {m: [] for m in macro_indicators}
    
    for r_idx, reg in enumerate(regimes_seq):
        for b in range(n_bars_per_regime):
            data["regime"].append(reg)
            
            # Set macro regime conditions
            if reg == "REGIME_1_STAGFLATION":
                # Oil spike, BDI drop, HY OAS stress, SPX/UST positive correlation
                oil_z = 1.8 + np.random.normal(0, 0.2)
                bdi_z = -1.4 + np.random.normal(0, 0.2)
                hy_z = 0.8 + np.random.normal(0, 0.15)
                corr = 0.45 + np.random.normal(0, 0.1)
                dxy_z = 0.3 + np.random.normal(0, 0.2)
                jpy_z = -0.5 + np.random.normal(0, 0.3)
                vix_z = 0.9 + np.random.normal(0, 0.2)
                rb_z = -0.8 + np.random.normal(0, 0.3)
                dfii_z = 0.4 + np.random.normal(0, 0.2)
                t10yie_z = 1.2 + np.random.normal(0, 0.2)  # High inflation expectations
                d2_chg, d10_chg = 0.05, 0.08
                hy_slope = 0.02
                ig_z = 0.6
                vix_pct = 55.0
                ndl_z = -0.2
                
                # Asset returns: Equities down/volatile, Gold resilient/up
                drifts = {"SPY": -0.0006, "QQQ": -0.0009, "GC=F": 0.0011, "SI=F": 0.0008, "BTC-USD": -0.0012, "ETH-USD": -0.0015}
                vols = {"SPY": 0.009, "QQQ": 0.012, "GC=F": 0.007, "SI=F": 0.012, "BTC-USD": 0.018, "ETH-USD": 0.021}
                
            elif reg == "REGIME_2_LIQUIDITY_SHOCK":
                # DTWEXBGS spike, USDJPY collapse, VIX spike, Risk Basket crash
                oil_z = -0.5 + np.random.normal(0, 0.3)
                bdi_z = -0.8 + np.random.normal(0, 0.3)
                hy_z = 1.4 + np.random.normal(0, 0.2)
                corr = -0.1 + np.random.normal(0, 0.1)
                dxy_z = 1.6 + np.random.normal(0, 0.2)
                jpy_z = -2.6 + np.random.normal(0, 0.3)
                vix_z = 2.4 + np.random.normal(0, 0.3)
                rb_z = -2.2 + np.random.normal(0, 0.3)
                dfii_z = 0.5 + np.random.normal(0, 0.2)
                t10yie_z = 0.1 + np.random.normal(0, 0.2)
                d2_chg, d10_chg = -0.10, -0.05
                hy_slope = 0.08
                ig_z = 1.2
                vix_pct = 92.0
                ndl_z = -1.5
                
                # Asset returns: Acute crash across all risk assets (crypto & equities hardest)
                drifts = {"SPY": -0.0025, "QQQ": -0.0032, "GC=F": -0.0008, "SI=F": -0.0020, "BTC-USD": -0.0045, "ETH-USD": -0.0055}
                vols = {"SPY": 0.016, "QQQ": 0.020, "GC=F": 0.012, "SI=F": 0.020, "BTC-USD": 0.028, "ETH-USD": 0.034}
                
            elif reg == "REGIME_3_REAL_YIELD":
                # Real yield surge, low inflation expectations
                oil_z = -0.2 + np.random.normal(0, 0.2)
                bdi_z = 0.1 + np.random.normal(0, 0.2)
                hy_z = 0.3 + np.random.normal(0, 0.15)
                corr = -0.3 + np.random.normal(0, 0.1)
                dxy_z = 0.6 + np.random.normal(0, 0.2)
                jpy_z = 0.2 + np.random.normal(0, 0.2)
                vix_z = 0.4 + np.random.normal(0, 0.2)
                rb_z = -0.5 + np.random.normal(0, 0.2)
                dfii_z = 2.1 + np.random.normal(0, 0.2)
                t10yie_z = 0.2 + np.random.normal(0, 0.15)  # Breakeven low < 0.5
                d2_chg, d10_chg = 0.04, 0.12  # Bear Steepener
                hy_slope = 0.01
                ig_z = 0.4
                vix_pct = 45.0
                ndl_z = -0.4
                
                # Asset returns: Tech & Crypto hit by discount rate surge, Gold dips
                drifts = {"SPY": -0.0007, "QQQ": -0.0016, "GC=F": -0.0010, "SI=F": -0.0014, "BTC-USD": -0.0022, "ETH-USD": -0.0028}
                vols = {"SPY": 0.008, "QQQ": 0.013, "GC=F": 0.008, "SI=F": 0.014, "BTC-USD": 0.019, "ETH-USD": 0.022}
                
            elif reg == "REGIME_4_CREDIT_STRESS":
                # HY OAS > 2.0, slope > 0, IG OAS > 1.0
                oil_z = -0.4 + np.random.normal(0, 0.2)
                bdi_z = -0.6 + np.random.normal(0, 0.2)
                hy_z = 2.5 + np.random.normal(0, 0.2)
                corr = 0.1 + np.random.normal(0, 0.1)
                dxy_z = 0.5 + np.random.normal(0, 0.2)
                jpy_z = -0.8 + np.random.normal(0, 0.3)
                vix_z = 1.3 + np.random.normal(0, 0.2)
                rb_z = -1.2 + np.random.normal(0, 0.3)
                dfii_z = 0.3 + np.random.normal(0, 0.2)
                t10yie_z = -0.2 + np.random.normal(0, 0.2)
                d2_chg, d10_chg = -0.04, -0.02
                hy_slope = 0.05
                ig_z = 1.4 + np.random.normal(0, 0.1)
                vix_pct = 75.0
                ndl_z = -0.8
                
                # Asset returns: Credit contraction drag
                drifts = {"SPY": -0.0014, "QQQ": -0.0018, "GC=F": 0.0004, "SI=F": -0.0005, "BTC-USD": -0.0025, "ETH-USD": -0.0030}
                vols = {"SPY": 0.011, "QQQ": 0.014, "GC=F": 0.008, "SI=F": 0.014, "BTC-USD": 0.022, "ETH-USD": 0.026}
                
            elif reg == "REGIME_5_RISK_ON":
                # HY OAS < -0.5, DXY between -1.0 and 0.5, VIX pct < 30, NDL > 0
                oil_z = 0.3 + np.random.normal(0, 0.2)
                bdi_z = 0.5 + np.random.normal(0, 0.2)
                hy_z = -1.1 + np.random.normal(0, 0.15)
                corr = -0.4 + np.random.normal(0, 0.1)
                dxy_z = -0.6 + np.random.normal(0, 0.2)
                jpy_z = 0.4 + np.random.normal(0, 0.2)
                vix_z = -1.2 + np.random.normal(0, 0.2)
                rb_z = 1.5 + np.random.normal(0, 0.2)
                dfii_z = -0.4 + np.random.normal(0, 0.2)
                t10yie_z = 0.3 + np.random.normal(0, 0.2)
                d2_chg, d10_chg = 0.01, 0.02
                hy_slope = -0.03
                ig_z = -0.8
                vix_pct = 18.0
                ndl_z = 1.4 + np.random.normal(0, 0.2)
                
                # Asset returns: Strong sustained bull rally across all assets
                drifts = {"SPY": 0.0012, "QQQ": 0.0017, "GC=F": 0.0008, "SI=F": 0.0015, "BTC-USD": 0.0028, "ETH-USD": 0.0032}
                vols = {"SPY": 0.005, "QQQ": 0.007, "GC=F": 0.005, "SI=F": 0.009, "BTC-USD": 0.012, "ETH-USD": 0.015}
                
            else: # REJIMSIZ_GECIS
                # Mean-reverting choppy baseline
                oil_z = 0.1 + np.random.normal(0, 0.2)
                bdi_z = -0.1 + np.random.normal(0, 0.2)
                hy_z = 0.0 + np.random.normal(0, 0.2)
                corr = -0.1 + np.random.normal(0, 0.1)
                dxy_z = 0.0 + np.random.normal(0, 0.2)
                jpy_z = 0.0 + np.random.normal(0, 0.2)
                vix_z = 0.0 + np.random.normal(0, 0.2)
                rb_z = 0.0 + np.random.normal(0, 0.2)
                dfii_z = 0.0 + np.random.normal(0, 0.2)
                t10yie_z = 0.0 + np.random.normal(0, 0.2)
                d2_chg, d10_chg = 0.0, 0.0
                hy_slope = 0.0
                ig_z = 0.0
                vix_pct = 42.0
                ndl_z = 0.0
                
                drifts = {"SPY": 0.0, "QQQ": 0.0, "GC=F": 0.0, "SI=F": 0.0, "BTC-USD": 0.0, "ETH-USD": 0.0}
                vols = {"SPY": 0.007, "QQQ": 0.009, "GC=F": 0.006, "SI=F": 0.010, "BTC-USD": 0.015, "ETH-USD": 0.018}
                
            # Append macro series
            macro_series["OIL_20D_Z"].append(oil_z)
            macro_series["BDI_Z"].append(bdi_z)
            macro_series["HY_OAS_Z"].append(hy_z)
            macro_series["SPX_UST_CORR"].append(corr)
            macro_series["DTWEXBGS_5D_Z"].append(dxy_z)
            macro_series["USDJPY_1D_Z"].append(jpy_z)
            macro_series["VIX_LEVEL_Z"].append(vix_z)
            macro_series["RISK_BASKET_5D_Z"].append(rb_z)
            macro_series["DFII10_1D_Z"].append(dfii_z)
            macro_series["T10YIE_Z"].append(t10yie_z)
            macro_series["DGS2_CHG"].append(d2_chg)
            macro_series["DGS10_CHG"].append(d10_chg)
            macro_series["HY_OAS_SLOPE"].append(hy_slope)
            macro_series["IG_OAS_Z"].append(ig_z)
            macro_series["VIX_PCT"].append(vix_pct)
            macro_series["NDL_Z"].append(ndl_z)
            
            # Step asset prices
            for a in assets:
                mu = drifts[a]
                sigma = vols[a]
                if reg == "REJIMSIZ_GECIS":
                    # Mean reverting price
                    ret = -0.05 * (asset_prices[a][-1] - asset_prices[a][0]) / asset_prices[a][0] + np.random.normal(0, sigma)
                else:
                    ret = mu + np.random.normal(0, sigma)
                new_p = max(asset_prices[a][-1] * (1.0 + ret), 1.0)
                asset_prices[a].append(new_p)

    # Trim last price to match length
    for a in assets:
        asset_prices[a] = asset_prices[a][:-1]
        
    df_data = pd.DataFrame(data)
    for a in assets:
        df_data[a] = asset_prices[a]
    for m in macro_indicators:
        df_data[m] = macro_series[m]
        
    return df_data

def evaluate_regime_conditions(row):
    """
    Evaluates triggers and confirmations based on the JSON specification.
    Returns triggered shock regimes and risk-on regime candidates.
    """
    triggers = {}
    
    # Regime 1: Küresel Enflasyon & Stagflasyon Şoku
    r1_trig = (row["OIL_20D_Z"] > 1.5) and (row["BDI_Z"] < -1.0)
    r1_conf = (row["HY_OAS_Z"] > 0.5) and (row["SPX_UST_CORR"] > 0.0)
    if r1_trig and r1_conf:
        triggers[1] = {"main_z": abs(row["OIL_20D_Z"]), "name": "Küresel Enflasyon & Stagflasyon Şoku", "type": "SHOCK"}
        
    # Regime 2: Sistemik Likidite Şoku & Carry Çöküşü
    r2_trig = (row["DTWEXBGS_5D_Z"] > 1.0) or (row["USDJPY_1D_Z"] < -2.0) or (row["VIX_LEVEL_Z"] > 1.5)
    r2_conf = (row["RISK_BASKET_5D_Z"] < -1.5)
    if r2_trig and r2_conf:
        main_z = max(abs(row["DTWEXBGS_5D_Z"]), abs(row["USDJPY_1D_Z"]), abs(row["VIX_LEVEL_Z"]))
        triggers[2] = {"main_z": main_z, "name": "Sistemik Likidite Şoku & Carry Çöküşü", "type": "SHOCK"}
        
    # Regime 3: Reel Faiz Şoku
    r3_trig = (row["DFII10_1D_Z"] > 1.5) and (row["T10YIE_Z"] < 0.5)
    if r3_trig:
        triggers[3] = {"main_z": abs(row["DFII10_1D_Z"]), "name": "Reel Faiz Şoku", "type": "SHOCK"}
        
    # Regime 4: Kredi Temerrüt Baskısı
    r4_trig = (row["HY_OAS_Z"] > 2.0) and (row["HY_OAS_SLOPE"] > 0)
    r4_conf = (row["IG_OAS_Z"] > 1.0)
    if r4_trig and r4_conf:
        triggers[4] = {"main_z": abs(row["HY_OAS_Z"]), "name": "Kredi Temerrüt Baskısı", "type": "SHOCK"}
        
    # Regime 5: Küresel Likidite Rallisi (Risk-On)
    r5_trig = (
        (row["HY_OAS_Z"] < -0.5) and
        (-1.0 <= row["DTWEXBGS_5D_Z"] <= 0.5) and
        (row["VIX_PCT"] < 30.0) and
        (row["NDL_Z"] > 0.0)
    )
    if r5_trig:
        triggers[5] = {"main_z": abs(row["NDL_Z"]), "name": "Küresel Likidite Rallisi (Risk-On)", "type": "RISK_ON"}
        
    # Apply Priority & Conflict Rules
    shock_keys = [k for k in triggers.keys() if k in [1, 2, 3, 4]]
    if shock_keys:
        # Special case: Regime 1 vs Regime 3
        if 1 in shock_keys and 3 in shock_keys and len(shock_keys) == 2:
            if row["T10YIE_Z"] > 0.5:
                selected_regime = 1
            else:
                selected_regime = 3
        else:
            # Highest absolute Z-score of main trigger
            selected_regime = max(shock_keys, key=lambda k: triggers[k]["main_z"])
    elif 5 in triggers:
        selected_regime = 5
    else:
        selected_regime = "REJIMSIZ_GECIS"
        
    return selected_regime

def run_threshold_grid_search(df_data):
    """
    Grid search across candidate threshold sets for each regime.
    Finds the exact configuration that maximizes Sharpe, Win Rate, and Profit Factor.
    """
    assets = ["SPY", "QQQ", "GC=F", "SI=F", "BTC-USD", "ETH-USD"]
    
    # Candidate parameter ranges
    regimes_to_tune = [1, 2, 3, 4, 5, "REJIMSIZ_GECIS"]
    
    # Realistic test grid for each regime
    candidate_profiles = {
        1: [ # Stagflation Shock: Equities suffer margin compression, commodities may hold
            {"buy_enter": 0.60, "sell_enter": -0.60, "buy_exit": 0.30, "sell_exit": -0.30, "min_clusters": 2, "label": "Baseline Symmetric"},
            {"buy_enter": 0.75, "sell_enter": -0.50, "buy_exit": 0.35, "sell_exit": -0.25, "min_clusters": 2, "label": "Moderate Asymmetric"},
            {"buy_enter": 0.85, "sell_enter": -0.45, "buy_exit": 0.40, "sell_exit": -0.20, "min_clusters": 3, "label": "Calibrated Defensive"},
            {"buy_enter": 1.00, "sell_enter": -0.40, "buy_exit": 0.45, "sell_exit": -0.20, "min_clusters": 3, "label": "Aggressive Bearish"}
        ],
        2: [ # Systemic Liquidity Shock & Carry Unwind: Cash is king, massive drawdown hazard
            {"buy_enter": 0.60, "sell_enter": -0.60, "buy_exit": 0.30, "sell_exit": -0.30, "min_clusters": 2, "label": "Baseline Symmetric"},
            {"buy_enter": 0.90, "sell_enter": -0.45, "buy_exit": 0.45, "sell_exit": -0.20, "min_clusters": 2, "label": "High Hurdle"},
            {"buy_enter": 1.20, "sell_enter": -0.35, "buy_exit": 0.60, "sell_exit": -0.15, "min_clusters": 3, "label": "Crisis Protective"},
            {"buy_enter": 1.40, "sell_enter": -0.30, "buy_exit": 0.70, "sell_exit": -0.15, "min_clusters": 3, "label": "Ultra Protective"}
        ],
        3: [ # Real Yield Shock: Duration & Tech valuation hit
            {"buy_enter": 0.60, "sell_enter": -0.60, "buy_exit": 0.30, "sell_exit": -0.30, "min_clusters": 2, "label": "Baseline Symmetric"},
            {"buy_enter": 0.75, "sell_enter": -0.50, "buy_exit": 0.35, "sell_exit": -0.25, "min_clusters": 2, "label": "Discount-Rate Dampened"},
            {"buy_enter": 0.80, "sell_enter": -0.50, "buy_exit": 0.35, "sell_exit": -0.25, "min_clusters": 2, "label": "Calibrated Valuation Filter"},
            {"buy_enter": 0.95, "sell_enter": -0.45, "buy_exit": 0.40, "sell_exit": -0.20, "min_clusters": 3, "label": "High Tech Squeeze"}
        ],
        4: [ # Credit Default Stress: Spreads expanding, high insolvency risk
            {"buy_enter": 0.60, "sell_enter": -0.60, "buy_exit": 0.30, "sell_exit": -0.30, "min_clusters": 2, "label": "Baseline Symmetric"},
            {"buy_enter": 0.80, "sell_enter": -0.50, "buy_exit": 0.40, "sell_exit": -0.25, "min_clusters": 2, "label": "Spread Aware"},
            {"buy_enter": 0.95, "sell_enter": -0.40, "buy_exit": 0.45, "sell_exit": -0.20, "min_clusters": 3, "label": "Credit Contagion Shield"},
            {"buy_enter": 1.10, "sell_enter": -0.35, "buy_exit": 0.50, "sell_exit": -0.15, "min_clusters": 3, "label": "Maximum Default Defense"}
        ],
        5: [ # Global Liquidity Rally (Risk-On): Strong secular uptrend, shorting is hazardous
            {"buy_enter": 0.60, "sell_enter": -0.60, "buy_exit": 0.30, "sell_exit": -0.30, "min_clusters": 2, "label": "Baseline Symmetric"},
            {"buy_enter": 0.50, "sell_enter": -0.75, "buy_exit": 0.25, "sell_exit": -0.35, "min_clusters": 2, "label": "Trend Friendly"},
            {"buy_enter": 0.45, "sell_enter": -0.85, "buy_exit": 0.20, "sell_exit": -0.40, "min_clusters": 2, "label": "Calibrated Alpha Runner"},
            {"buy_enter": 0.35, "sell_enter": -1.00, "buy_exit": 0.15, "sell_exit": -0.50, "min_clusters": 1, "label": "Aggressive Trend Following"}
        ],
        "REJIMSIZ_GECIS": [ # Choppy Transition: Whipsaw prevention
            {"buy_enter": 0.60, "sell_enter": -0.60, "buy_exit": 0.30, "sell_exit": -0.30, "min_clusters": 2, "label": "Baseline Symmetric"},
            {"buy_enter": 0.70, "sell_enter": -0.70, "buy_exit": 0.35, "sell_exit": -0.35, "min_clusters": 2, "label": "Moderate Deadband"},
            {"buy_enter": 0.75, "sell_enter": -0.75, "buy_exit": 0.35, "sell_exit": -0.35, "min_clusters": 2, "label": "Calibrated Anti-Chop"},
            {"buy_enter": 0.90, "sell_enter": -0.90, "buy_exit": 0.45, "sell_exit": -0.45, "min_clusters": 3, "label": "Ultra Deadband"}
        ]
    }
    
    # Calculate synthetic multi-factor raw scores
    # Factor score correlates with momentum and macro tailwind
    factor_scores = {}
    for a in assets:
        prices = df_data[a].values
        # 4-bar and 24-bar ROC
        ret_4 = np.zeros(len(prices))
        ret_4[4:] = (prices[4:] - prices[:-4]) / (prices[:-4] + 1e-9) * 100.0
        ret_24 = np.zeros(len(prices))
        ret_24[24:] = (prices[24:] - prices[:-24]) / (prices[:-24] + 1e-9) * 100.0
        
        raw_score = (ret_4 * 0.7 + ret_24 * 0.3)
        # normalize to [-2.5, 2.5]
        norm_score = np.clip(raw_score * 0.8, -2.5, 2.5)
        factor_scores[a] = norm_score
        
    # Evaluate regimes across bars
    detected_regimes = [evaluate_regime_conditions(df_data.iloc[i]) for i in range(len(df_data))]
    
    best_results = {}
    
    for r_target in candidate_profiles.keys():
        r_indices = [i for i, reg in enumerate(detected_regimes) if reg == r_target]
        if not r_indices:
            continue
            
        print(f"\n=======================================================")
        print(f"🔍 OPTIMIZING THRESHOLDS FOR REGIME: {r_target} ({len(r_indices)} Bars)")
        print(f"=======================================================")
        
        candidates = candidate_profiles[r_target]
        grid_evals = []
        
        for cand in candidates:
            b_enter = cand["buy_enter"]
            s_enter = cand["sell_enter"]
            b_exit = cand["buy_exit"]
            s_exit = cand["sell_exit"]
            
            # Simulate trading in this regime across 6 assets
            trades = []
            for a in assets:
                scores = factor_scores[a]
                prices = df_data[a].values
                
                pos = 0 # -1, 0, 1
                for idx in r_indices:
                    sc = scores[idx]
                    
                    # State machine with hysteresis
                    if pos == 0:
                        if sc >= b_enter:
                            pos = 1
                        elif sc <= s_enter:
                            pos = -1
                    elif pos == 1:
                        if sc < b_exit:
                            pos = 0
                    elif pos == -1:
                        if sc > s_exit:
                            pos = 0
                            
                    # Forward 8-bar return
                    if idx + 8 < len(prices):
                        fwd_ret = (prices[idx + 8] - prices[idx]) / prices[idx]
                        strat_ret = pos * fwd_ret
                        trades.append(strat_ret)
                        
            # Metrics
            trades = np.array(trades)
            active_trades = trades[trades != 0]
            if len(active_trades) > 50:
                win_rate = np.mean(active_trades > 0) * 100.0
                g_profit = np.sum(active_trades[active_trades > 0])
                g_loss = abs(np.sum(active_trades[active_trades < 0])) + 1e-9
                pf = g_profit / g_loss
                sharpe = (np.mean(active_trades) / (np.std(active_trades) + 1e-9)) * np.sqrt(252 * 6)
                cum = np.cumprod(1.0 + active_trades)
                peak = np.maximum.accumulate(cum)
                dd = (cum - peak) / peak
                max_dd = abs(np.min(dd)) * 100.0
                
                score = sharpe * (win_rate / 50.0) * min(pf, 3.0) - (max_dd * 0.05)
            else:
                win_rate, pf, sharpe, max_dd, score = 0, 0, 0, 0, -999
                
            res = {
                "profile": cand["label"],
                "params": cand,
                "win_rate": round(win_rate, 1),
                "profit_factor": round(pf, 2),
                "sharpe": round(sharpe, 2),
                "max_drawdown": round(max_dd, 1),
                "active_bars": len(active_trades),
                "score": round(score, 2)
            }
            grid_evals.append(res)
            print(f" -> [{cand['label']}]: WinRate={res['win_rate']}%, PF={res['profit_factor']}, Sharpe={res['sharpe']}, MaxDD={res['max_drawdown']}%, Score={res['score']}")
            
        best_cand = max(grid_evals, key=lambda x: x["score"])
        best_results[r_target] = best_cand
        print(f"🏆 WINNER for {r_target}: {best_cand['profile']} (Sharpe: {best_cand['sharpe']}, PF: {best_cand['profit_factor']})")

    return best_results

if __name__ == "__main__":
    df_data = generate_multi_regime_dataset(n_bars_per_regime=300)
    print(f"Generated {len(df_data)} bars across all 6 regime states.")
    results = run_threshold_grid_search(df_data)
