"""
Backtest Engine: Multi-Regime Quantitative Evaluation for Tier-1 Quant Terminal
Evaluates Hit Rate, Sharpe, Profit Factor, Max Drawdown, and Whipsaw across:
1. Strong Bull Trend (Boğa Rallisi)
2. Severe Bear Crash (Sert Çöküş / Risk-Off)
3. Choppy / Mean-Reverting (Yatay / Testere Bandı)
4. Stagflation / Liquidity Shock (Stagflasyon Şoku)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from config import ASSET_MATRICES
from quant_processor import RobustQuantProcessor
from gatekeeper import PreTradeGatekeeper

np.random.seed(42)

def generate_regime_dataset(regime_type, n_bars=300):
    """
    Generates synthetic 1h OHLCV data grid mimicking real intermarket dynamics.
    """
    dates = [datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(hours=i) for i in range(n_bars)]
    
    # Base Brownian Motions with intermarket correlation
    if regime_type == "BULL":
        trend = 0.0012      # Steady upward drift
        vol = 0.006
        vix_drift = -0.02
        base_vix = 14.5
        dxy_drift = -0.0003
        credit_drift = 0.0008
    elif regime_type == "BEAR":
        trend = -0.0022     # Strong downward crash
        vol = 0.015
        vix_drift = 0.06
        base_vix = 28.0
        dxy_drift = 0.0015
        credit_drift = -0.0025
    elif regime_type == "CHOPPY":
        trend = 0.0000      # Zero drift, high mean-reversion
        vol = 0.008
        vix_drift = 0.00
        base_vix = 16.0
        dxy_drift = 0.0001
        credit_drift = 0.0000
    elif regime_type == "STAGFLATION":
        trend = -0.0008     # Stagflationary drag
        vol = 0.011
        vix_drift = 0.02
        base_vix = 21.0
        dxy_drift = 0.0008
        credit_drift = -0.0012

    # Asset Price Paths
    grid = {}
    
    def make_df(init_p, mu, sigma, is_mean_reverting=False):
        prices = [init_p]
        for i in range(1, n_bars):
            if is_mean_reverting:
                ret = -0.08 * (prices[-1] - init_p) / init_p + np.random.normal(0, sigma)
            else:
                ret = mu + np.random.normal(0, sigma)
            p = max(prices[-1] * (1.0 + ret), 0.5)
            prices.append(p)
        df = pd.DataFrame({
            "Open": prices,
            "High": [p * (1.0 + abs(np.random.normal(0, sigma*0.4))) for p in prices],
            "Low": [p * (1.0 - abs(np.random.normal(0, sigma*0.4))) for p in prices],
            "Close": prices,
            "Volume": [int(100000 + abs(np.random.normal(0, 20000))) for _ in prices]
        }, index=dates)
        return df

    is_chop = (regime_type == "CHOPPY")
    grid["SPY"] = make_df(500.0, trend, vol, is_chop)
    grid["QQQ"] = make_df(450.0, trend * 1.2, vol * 1.25, is_chop)
    grid["GC=F"] = make_df(2300.0, trend * 0.8 if regime_type != "STAGFLATION" else 0.0018, vol * 0.8, is_chop)
    grid["SI=F"] = make_df(28.0, trend * 1.1 if regime_type != "STAGFLATION" else 0.0022, vol * 1.4, is_chop)
    grid["BTC-USD"] = make_df(65000.0, trend * 1.8, vol * 2.0, is_chop)
    grid["ETH-USD"] = make_df(3400.0, trend * 1.9, vol * 2.2, is_chop)
    grid["SMH"] = make_df(220.0, trend * 1.4, vol * 1.4, is_chop)
    grid["RSP"] = make_df(160.0, trend * 0.9, vol * 0.9, is_chop)
    grid["XLU"] = make_df(70.0, -trend * 0.5, vol * 0.7, is_chop)
    grid["XLY"] = make_df(180.0, trend, vol, is_chop)
    grid["XLP"] = make_df(75.0, trend * 0.3, vol * 0.5, is_chop)
    grid["TLT"] = make_df(92.0, credit_drift, vol * 0.8, is_chop)
    grid["SHY"] = make_df(82.0, 0.00005, vol * 0.1, is_chop)
    grid["KRE"] = make_df(50.0, credit_drift * 1.5, vol * 1.2, is_chop)
    grid["HYG"] = make_df(77.0, credit_drift, vol * 0.5, is_chop)
    grid["LQD"] = make_df(108.0, credit_drift * 0.5, vol * 0.4, is_chop)
    grid["DXY"] = make_df(104.0, dxy_drift, vol * 0.3, is_chop)
    grid["USO"] = make_df(75.0, 0.0025 if regime_type == "STAGFLATION" else trend * 0.5, vol * 1.2, is_chop)
    grid["IYT"] = make_df(260.0, -0.0015 if regime_type == "STAGFLATION" else trend * 0.8, vol * 1.0, is_chop)
    grid["USDJPY"] = make_df(155.0, dxy_drift * 0.8, vol * 0.4, is_chop)
    
    # VIX series
    vix_vals = [base_vix]
    for _ in range(1, n_bars):
        v = max(vix_vals[-1] + vix_drift + np.random.normal(0, 0.35), 11.0)
        vix_vals.append(v)
    grid["VIX"] = pd.DataFrame({"Close": vix_vals}, index=dates)
    grid["VIX3M"] = pd.DataFrame({"Close": [v * 1.05 for v in vix_vals]}, index=dates)

    return grid


def run_backtest_simulation():
    regimes = ["BULL", "BEAR", "CHOPPY", "STAGFLATION"]
    assets = ["SPX", "NQ", "XAU", "XAG", "BTC", "ETH"]
    
    overall_results = {}

    for regime in regimes:
        grid = generate_regime_dataset(regime, n_bars=240)
        gk = PreTradeGatekeeper()
        gk.grid_1h = grid
        
        regime_trades = []
        
        # Walk forward through bars (starting from bar 50 to have rolling warmup)
        for t in range(50, 230):
            # Window slice
            sliced_grid = {sym: df.iloc[:t].copy() for sym, df in grid.items()}
            gk.grid_1h = sliced_grid
            
            # Refresh gatekeeper state
            vix_df = sliced_grid.get("VIX", pd.DataFrame())
            gk.current_vix = float(vix_df["Close"].iloc[-1])
            z_vix = gk.processor.compute_vix_stress(vix_df)
            gk.dxy_velocity = gk.processor.compute_usd_strength_impulse(sliced_grid.get("DXY", pd.DataFrame()))
            gk.credit_velocity = gk.processor.compute_credit_intraday_velocity(
                sliced_grid.get("HYG", pd.DataFrame()),
                sliced_grid.get("LQD", pd.DataFrame())
            )
            gk.stagflation_z = gk.processor.compute_stagflation_shock(
                sliced_grid.get("USO", pd.DataFrame()),
                sliced_grid.get("IYT", pd.DataFrame())
            )
            
            # Evaluate all assets
            verdicts = gk.evaluate_all_assets_harmonized()
            
            # Evaluate forward 8-bar (8h) and 24-bar (24h) return for each asset
            for a in assets:
                bench = ASSET_MATRICES[a]["benchmark_symbol"]
                full_close = grid[bench]["Close"]
                cur_price = full_close.iloc[t-1]
                future_price_8h = full_close.iloc[min(t + 7, len(full_close) - 1)]
                future_ret_8h = (future_price_8h - cur_price) / cur_price
                
                v_data = verdicts.get(a, {})
                verdict = v_data.get("verdict", "NÖTR (BEKLE)")
                score = float(v_data.get("score", 0.0))
                
                # Signal Direction
                sig_dir = 0
                if "AL" in verdict:
                    sig_dir = 1
                elif "SAT" in verdict:
                    sig_dir = -1
                
                # Strategy Return
                strat_ret = sig_dir * future_ret_8h
                
                regime_trades.append({
                    "asset": a,
                    "bar": t,
                    "verdict": verdict,
                    "score": score,
                    "sig_dir": sig_dir,
                    "future_ret": future_ret_8h,
                    "strat_ret": strat_ret
                })

        df_trades = pd.DataFrame(regime_trades)
        
        # Calculate Quantitative Metrics
        active_trades = df_trades[df_trades["sig_dir"] != 0]
        if len(active_trades) > 0:
            wins = active_trades[active_trades["strat_ret"] > 0]
            losses = active_trades[active_trades["strat_ret"] < 0]
            win_rate = (len(wins) / len(active_trades)) * 100.0
            
            gross_profit = wins["strat_ret"].sum()
            gross_loss = abs(losses["strat_ret"].sum()) + 1e-9
            profit_factor = gross_profit / gross_loss
            
            mean_ret = active_trades["strat_ret"].mean()
            std_ret = active_trades["strat_ret"].std() + 1e-9
            sharpe = (mean_ret / std_ret) * np.sqrt(252 * 6)  # Annualized
            
            # Cumulative returns and Max Drawdown
            cum_rets = (1.0 + active_trades["strat_ret"]).cumprod()
            rolling_max = cum_rets.cummax()
            drawdowns = (cum_rets - rolling_max) / rolling_max
            max_dd = abs(drawdowns.min()) * 100.0
        else:
            win_rate = 0.0
            profit_factor = 0.0
            sharpe = 0.0
            max_dd = 0.0
            
        neutral_rate = (len(df_trades[df_trades["sig_dir"] == 0]) / len(df_trades)) * 100.0
        
        overall_results[regime] = {
            "Total_Signals": len(df_trades),
            "Active_Trades": len(active_trades),
            "Neutral_Rate_%": round(neutral_rate, 1),
            "Win_Rate_%": round(win_rate, 1),
            "Profit_Factor": round(profit_factor, 2),
            "Sharpe_Ratio": round(sharpe, 2),
            "Max_Drawdown_%": round(max_dd, 1),
            "Avg_Return_Per_Trade_%": round(active_trades["strat_ret"].mean() * 100.0, 3) if len(active_trades) > 0 else 0.0
        }

    return overall_results

if __name__ == "__main__":
    results = run_backtest_simulation()
    print("=== QUANTITATIVE BACKTEST PERFORMANCE SUMMARY ===")
    for regime, stats in results.items():
        print(f"\n[{regime} REGIME]:")
        for k, v in stats.items():
            print(f"  {k}: {v}")
