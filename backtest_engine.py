"""
Backtest Engine: Multi-Regime Quantitative Evaluation for Macro Event Interpretation System v1.0
Evaluates Hit Rate, Sharpe Ratio, Profit Factor, Max Drawdown, and Whipsaw reduction across all 5 Macro Regimes:
1. Küresel Enflasyon & Stagflasyon Şoku (Regime 1 - SHOCK)
2. Sistemik Likidite Şoku & Carry Çöküşü (Regime 2 - SHOCK)
3. Reel Faiz Şoku (Regime 3 - SHOCK)
4. Kredi Temerrüt Baskısı (Regime 4 - SHOCK)
5. Küresel Likidite Rallisi (Regime 5 - RISK_ON)
6. REJIMSIZ_GECIS (Transitional / Fallback)

Compares Static Baseline (±0.60 Fixed) vs Calibrated Dynamic Thresholds.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List

from config import ASSET_MATRICES, REGIME_DYNAMIC_THRESHOLDS
from quant_processor import RobustQuantProcessor
from gatekeeper import PreTradeGatekeeper
from macro_regime_engine import MacroRegimeEngine

np.random.seed(42)


def generate_regime_dataset(regime_id, n_bars=250):
    """
    Generates synthetic 1h OHLCV data grid mimicking intermarket dynamics for each regime.
    """
    dates = [datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(hours=i) for i in range(n_bars)]
    
    if regime_id == 1:
        # Küresel Enflasyon & Stagflasyon Şoku
        trend = -0.0010
        vol = 0.012
        oil_drift = 0.0030
        bdi_drift = -0.0020
        vix_drift = 0.03
        base_vix = 22.0
        dxy_drift = 0.0005
        credit_drift = -0.0015
        gold_drift = 0.0015
    elif regime_id == 2:
        # Sistemik Likidite Şoku & Carry Çöküşü
        trend = -0.0035
        vol = 0.022
        oil_drift = -0.0020
        bdi_drift = -0.0025
        vix_drift = 0.09
        base_vix = 32.0
        dxy_drift = 0.0025
        credit_drift = -0.0035
        gold_drift = -0.0010
    elif regime_id == 3:
        # Reel Faiz Şoku (Tech/Duration hit, curve moves)
        trend = -0.0015
        vol = 0.013
        oil_drift = -0.0005
        bdi_drift = 0.0000
        vix_drift = 0.02
        base_vix = 19.5
        dxy_drift = 0.0012
        credit_drift = -0.0008
        gold_drift = -0.0018
    elif regime_id == 4:
        # Kredi Temerrüt Baskısı
        trend = -0.0020
        vol = 0.016
        oil_drift = -0.0010
        bdi_drift = -0.0015
        vix_drift = 0.05
        base_vix = 25.0
        dxy_drift = 0.0009
        credit_drift = -0.0028
        gold_drift = 0.0005
    elif regime_id == 5:
        # Küresel Likidite Rallisi (Risk-On)
        trend = 0.0018
        vol = 0.006
        oil_drift = 0.0008
        bdi_drift = 0.0010
        vix_drift = -0.03
        base_vix = 13.5
        dxy_drift = -0.0005
        credit_drift = 0.0012
        gold_drift = 0.0010
    else:
        # REJIMSIZ_GECIS (Denge / Testere)
        trend = 0.0000
        vol = 0.008
        oil_drift = 0.0000
        bdi_drift = 0.0000
        vix_drift = 0.00
        base_vix = 16.0
        dxy_drift = 0.0000
        credit_drift = 0.0000
        gold_drift = 0.0000

    grid = {}

    def make_df(init_p, mu, sigma, is_mean_rev=False):
        prices = [init_p]
        for _ in range(1, n_bars):
            if is_mean_rev:
                ret = -0.08 * (prices[-1] - init_p) / init_p + np.random.normal(0, sigma)
            else:
                ret = mu + np.random.normal(0, sigma)
            p = max(prices[-1] * (1.0 + ret), 0.5)
            prices.append(p)
        df = pd.DataFrame({
            "Open": prices,
            "High": [p * (1.0 + abs(np.random.normal(0, sigma * 0.4))) for p in prices],
            "Low": [p * (1.0 - abs(np.random.normal(0, sigma * 0.4))) for p in prices],
            "Close": prices,
            "Volume": [int(100000 + abs(np.random.normal(0, 20000))) for _ in prices]
        }, index=dates)
        return df

    is_chop = (regime_id == "REJIMSIZ_GECIS")
    grid["SPY"] = make_df(500.0, trend, vol, is_chop)
    grid["QQQ"] = make_df(450.0, trend * 1.3, vol * 1.3, is_chop)
    grid["GC"] = make_df(2300.0, gold_drift, vol * 0.7, is_chop)
    grid["GC=F"] = grid["GC"]
    grid["SI"] = make_df(28.0, gold_drift * 1.2, vol * 1.3, is_chop)
    grid["SI=F"] = grid["SI"]
    grid["BTC-USD"] = make_df(65000.0, trend * 2.0, vol * 2.2, is_chop)
    grid["ETH-USD"] = make_df(3400.0, trend * 2.2, vol * 2.4, is_chop)
    grid["SMH"] = make_df(220.0, trend * 1.5, vol * 1.5, is_chop)
    grid["RSP"] = make_df(160.0, trend * 0.9, vol * 0.9, is_chop)
    grid["XLU"] = make_df(70.0, -trend * 0.4, vol * 0.7, is_chop)
    grid["XLY"] = make_df(180.0, trend, vol, is_chop)
    grid["XLP"] = make_df(75.0, trend * 0.3, vol * 0.5, is_chop)
    grid["TLT"] = make_df(92.0, credit_drift, vol * 0.8, is_chop)
    grid["SHY"] = make_df(82.0, 0.00005, vol * 0.1, is_chop)
    grid["KRE"] = make_df(50.0, credit_drift * 1.5, vol * 1.2, is_chop)
    grid["HYG"] = make_df(77.0, credit_drift, vol * 0.5, is_chop)
    grid["LQD"] = make_df(108.0, credit_drift * 0.5, vol * 0.4, is_chop)
    grid["DXY"] = make_df(104.0, dxy_drift, vol * 0.3, is_chop)
    grid["USO"] = make_df(75.0, oil_drift, vol * 1.2, is_chop)
    grid["CL"] = grid["USO"]
    grid["IYT"] = make_df(260.0, bdi_drift, vol * 1.0, is_chop)
    grid["BDRY"] = grid["IYT"]
    grid["USDJPY"] = make_df(155.0, dxy_drift * 0.8 if regime_id != 2 else -0.0035, vol * 0.6, is_chop)
    grid["TIP"] = make_df(105.0, -credit_drift * 0.8, vol * 0.5, is_chop)
    grid["IEF"] = make_df(95.0, credit_drift * 0.6, vol * 0.4, is_chop)
    grid["HG"] = make_df(4.2, trend * 0.7, vol * 1.0, is_chop)
    grid["HG=F"] = grid["HG"]
    grid["TNX"] = make_df(4.2, -credit_drift * 5.0, vol * 0.5, is_chop)

    # VIX series
    vix_vals = [base_vix]
    for _ in range(1, n_bars):
        v = max(vix_vals[-1] + vix_drift + np.random.normal(0, 0.35), 11.0)
        vix_vals.append(v)
    grid["VIX"] = pd.DataFrame({"Close": vix_vals}, index=dates)
    grid["VIX3M"] = pd.DataFrame({"Close": [v * 1.05 for v in vix_vals]}, index=dates)

    return grid


def run_single_regime_simulation(regime_id, use_dynamic_thresholds=True):
    assets = ["SPX", "NQ", "XAU", "XAG", "BTC", "ETH"]
    grid = generate_regime_dataset(regime_id, n_bars=240)
    gk = PreTradeGatekeeper()
    gk.grid_1h = grid

    trades = []
    for t in range(50, 230):
        sliced_grid = {sym: df.iloc[:t].copy() for sym, df in grid.items()}
        gk.grid_1h = sliced_grid

        # Simulate macro engine evaluation
        vix_df = sliced_grid.get("VIX", pd.DataFrame())
        cur_vix = float(vix_df["Close"].iloc[-1])
        z_vix = gk.processor.compute_vix_stress(vix_df)
        dxy_vel = gk.processor.compute_usd_strength_impulse(sliced_grid.get("DXY", pd.DataFrame()))
        cred_vel = gk.processor.compute_credit_intraday_velocity(
            sliced_grid.get("HYG", pd.DataFrame()),
            sliced_grid.get("LQD", pd.DataFrame())
        )
        stag_z = gk.processor.compute_stagflation_shock(
            sliced_grid.get("USO", pd.DataFrame()),
            sliced_grid.get("IYT", pd.DataFrame())
        )

        gk.current_vix = cur_vix
        gk.dxy_velocity = dxy_vel
        gk.credit_velocity = cred_vel
        gk.stagflation_z = stag_z

        gk.active_macro_regime_id = regime_id
        if use_dynamic_thresholds:
            active_key = regime_id if regime_id in REGIME_DYNAMIC_THRESHOLDS else "REJIMSIZ_GECIS"
            gk.dynamic_thresholds = REGIME_DYNAMIC_THRESHOLDS.get(active_key, REGIME_DYNAMIC_THRESHOLDS["REJIMSIZ_GECIS"])
        else:
            # Static baseline thresholds
            gk.dynamic_thresholds = {
                "buy_enter": 0.60, "buy_exit": 0.30,
                "sell_enter": -0.60, "sell_exit": -0.30,
                "strong_buy_enter": 1.60, "strong_sell_enter": -1.60,
                "min_clusters": 2, "risk_scale": 1.0
            }

        verdicts = gk.evaluate_all_assets_harmonized()

        for a in assets:
            bench = ASSET_MATRICES[a]["benchmark_symbol"]
            clean_b = bench.replace("^", "").replace("=X", "").replace("=F", "")
            full_close = grid[clean_b]["Close"]
            cur_p = full_close.iloc[t - 1]
            fwd_p = full_close.iloc[min(t + 7, len(full_close) - 1)]
            fwd_ret = (fwd_p - cur_p) / (cur_p + 1e-9)

            v_data = verdicts.get(a, {})
            verdict = v_data.get("verdict", "NÖTR (BEKLE)")
            sig_dir = 0
            if "AL" in verdict:
                sig_dir = 1
            elif "SAT" in verdict:
                sig_dir = -1

            strat_ret = sig_dir * fwd_ret
            trades.append(strat_ret)

    trades = np.array(trades)
    active_trades = trades[trades != 0]

    if len(active_trades) > 0:
        wins = active_trades[active_trades > 0]
        losses = active_trades[active_trades < 0]
        win_rate = (len(wins) / len(active_trades)) * 100.0
        gross_profit = wins.sum()
        gross_loss = abs(losses.sum()) + 1e-9
        pf = gross_profit / gross_loss
        mean_ret = active_trades.mean()
        std_ret = active_trades.std() + 1e-9
        sharpe = (mean_ret / std_ret) * np.sqrt(252 * 6)
        cum = np.cumprod(1.0 + active_trades)
        peak = np.maximum.accumulate(cum)
        dd = (cum - peak) / peak
        max_dd = abs(dd.min()) * 100.0
    else:
        win_rate, pf, sharpe, max_dd = 0.0, 0.0, 0.0, 0.0

    neutral_rate = (np.sum(trades == 0) / len(trades)) * 100.0
    return {
        "trades_count": len(trades),
        "active_trades": len(active_trades),
        "neutral_rate_pct": round(neutral_rate, 1),
        "win_rate_pct": round(win_rate, 1),
        "profit_factor": round(pf, 2),
        "sharpe_ratio": round(sharpe, 2),
        "max_drawdown_pct": round(max_dd, 1),
        "avg_ret_trade_pct": round(active_trades.mean() * 100.0, 3) if len(active_trades) > 0 else 0.0
    }


def run_full_comparative_backtest():
    """Runs backtest across all 5 macro regimes + fallback comparing static vs dynamic."""
    regimes = [
        (1, "Küresel Enflasyon & Stagflasyon Şoku"),
        (2, "Sistemik Likidite Şoku & Carry Çöküşü"),
        (3, "Reel Faiz Şoku"),
        (4, "Kredi Temerrüt Baskısı"),
        (5, "Küresel Likidite Rallisi (Risk-On)"),
        ("REJIMSIZ_GECIS", "Rejimsiz Geçiş / Makro Denge")
    ]

    report = []
    print("==================================================================================")
    print("🏁 BACKTEST: STATİK EŞİKLER vs KALİBRE EDİLMİŞ DİNAMİK REJİM EŞİKLERİ")
    print("==================================================================================")

    for r_id, r_name in regimes:
        static_res = run_single_regime_simulation(r_id, use_dynamic_thresholds=False)
        dynamic_res = run_single_regime_simulation(r_id, use_dynamic_thresholds=True)

        delta_sharpe = dynamic_res["sharpe_ratio"] - static_res["sharpe_ratio"]
        delta_pf = dynamic_res["profit_factor"] - static_res["profit_factor"]
        delta_dd = static_res["max_drawdown_pct"] - dynamic_res["max_drawdown_pct"]

        report.append({
            "regime_id": r_id,
            "regime_name": r_name,
            "static_sharpe": static_res["sharpe_ratio"],
            "dynamic_sharpe": dynamic_res["sharpe_ratio"],
            "delta_sharpe": round(delta_sharpe, 2),
            "static_pf": static_res["profit_factor"],
            "dynamic_pf": dynamic_res["profit_factor"],
            "delta_pf": round(delta_pf, 2),
            "static_winrate": static_res["win_rate_pct"],
            "dynamic_winrate": dynamic_res["win_rate_pct"],
            "static_maxdd": static_res["max_drawdown_pct"],
            "dynamic_maxdd": dynamic_res["max_drawdown_pct"],
            "drawdown_reduction": round(delta_dd, 1)
        })

        print(f"\n[REJİM {r_id}]: {r_name}")
        print(f"  Statik Eşikler  -> Sharpe: {static_res['sharpe_ratio']:+.2f} | PF: {static_res['profit_factor']:.2f} | WinRate: {static_res['win_rate_pct']:.1f}% | MaxDD: {static_res['max_drawdown_pct']:.1f}%")
        print(f"  Dinamik Eşikler -> Sharpe: {dynamic_res['sharpe_ratio']:+.2f} | PF: {dynamic_res['profit_factor']:.2f} | WinRate: {dynamic_res['win_rate_pct']:.1f}% | MaxDD: {dynamic_res['max_drawdown_pct']:.1f}%")
        print(f"  Net İyileşme    -> ΔSharpe: {delta_sharpe:+.2f} | ΔPF: {delta_pf:+.2f} | DD İyileşmesi: -{delta_dd:.1f}%")

    return report


if __name__ == "__main__":
    results = run_full_comparative_backtest()
