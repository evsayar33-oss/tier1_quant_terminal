"""
Robust Quant Processor: Accurate Z-Scores, Indicators & Crisis Engine
"""
import numpy as np
import pandas as pd
from config import CRISIS_CONFIG

class RobustQuantProcessor:
    @staticmethod
    def compute_z_score(series, window=32):
        if len(series) < 5:
            return 0.0
        w = min(window, len(series))
        rolling_mean = series.rolling(w).mean()
        rolling_std = series.rolling(w).std() + 1e-9
        z = (series.iloc[-1] - rolling_mean.iloc[-1]) / rolling_std.iloc[-1]
        return float(np.clip(z, -3.5, 3.5))

    @staticmethod
    def compute_momentum_score(df, window=14):
        """Fiyatın kısa-orta vadeli momentum ve trend gücünü hesaplar."""
        if df.empty or len(df) < window:
            return 0.0
        close = df["Close"]
        roc = ((close.iloc[-1] - close.iloc[-window]) / close.iloc[-window]) * 100.0
        sma = close.rolling(min(20, len(close))).mean().iloc[-1]
        dist_sma = ((close.iloc[-1] - sma) / sma) * 100.0
        score = (roc * 0.5) + (dist_sma * 1.5)
        return float(np.clip(score, -3.0, 3.0))

    @staticmethod
    def compute_ratio_z(df_num, df_denom, window=32):
        if df_num.empty or df_denom.empty:
            return 0.0
        aligned = pd.concat([df_num["Close"], df_denom["Close"]], axis=1, join="inner").dropna()
        if len(aligned) < 5:
            return 0.0
        w = min(window, len(aligned))
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        mean = ratio.rolling(w).mean().iloc[-1]
        std = ratio.rolling(w).std().iloc[-1] + 1e-9
        z = (ratio.iloc[-1] - mean) / std
        return float(np.clip(z, -3.5, 3.5))

    @staticmethod
    def detect_market_regime(spx_df):
        if spx_df.empty or len(spx_df) < 20:
            return "NEUTRAL"
        close = spx_df["Close"].iloc[-1]
        w = min(50, len(spx_df))
        sma = spx_df["Close"].rolling(w).mean().iloc[-1]
        return "BULL_EXPANSION" if close >= sma else "BEAR_CONTRACTION"

    @staticmethod
    def evaluate_crisis_lock_with_hysteresis(z_credit, z_vix, z_rates, z_dxy, current_vix_val, current_state=False, consecutive_breaches=0):
        cfg = CRISIS_CONFIG
        anomaly_score = float(np.linalg.norm([z_credit, z_vix, z_rates, z_dxy]) / 2.0)
        is_vix_above_floor = (current_vix_val >= cfg.get("vix_absolute_floor", 20.0))

        enter_condition = False
        if is_vix_above_floor:
            enter_condition = (
                (anomaly_score > cfg.get("upper_threshold", 2.2) and consecutive_breaches >= cfg.get("enter_consecutive_bars", 3)) or
                (z_vix > cfg.get("vix_spike_threshold", 2.5) and z_credit > cfg.get("credit_spike_threshold", 1.8))
            )

        exit_condition = (anomaly_score < cfg.get("lower_threshold", 1.5)) or (not is_vix_above_floor and anomaly_score < 2.0)

        new_state = current_state
        if not current_state and enter_condition:
            new_state = True
        elif current_state and exit_condition:
            new_state = False

        return new_state, anomaly_score, is_vix_above_floor
