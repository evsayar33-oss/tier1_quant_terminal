"""
Robust Quant Processor: Mathematics, VIX Floor Shield & Dual-Regime Calibration
"""
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from config import CRISIS_CONFIG, THRESHOLD_CLAMPS

class RobustQuantProcessor:
    @staticmethod
    def compute_z_score(series, window=32):
        if len(series) < window or series.std() == 0:
            return 0.0
        rolling_mean = series.rolling(window).mean()
        rolling_std = series.rolling(window).std() + 1e-9
        return float((series.iloc[-1] - rolling_mean.iloc[-1]) / rolling_std.iloc[-1])

    @staticmethod
    def compute_ratio_z(df_num, df_denom, window=32):
        if df_num.empty or df_denom.empty:
            return 0.0
        aligned = pd.concat([df_num["Close"], df_denom["Close"]], axis=1, join="inner").dropna()
        if len(aligned) < window:
            return 0.0
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        mean = ratio.rolling(window).mean().iloc[-1]
        std = ratio.rolling(window).std().iloc[-1] + 1e-9
        return float((ratio.iloc[-1] - mean) / std)

    @staticmethod
    def detect_market_regime(spx_df):
        """
        BOĞA / AYI REJİM DEDEKTÖRÜ:
        SPX fiyatının 50 ve 200 günlük ortalamalara konumuna göre rejimi belirler.
        """
        if spx_df.empty or len(spx_df) < 50:
            return "NEUTRAL"
        
        close = spx_df["Close"].iloc[-1]
        sma50 = spx_df["Close"].rolling(50).mean().iloc[-1]
        
        if len(spx_df) >= 200:
            sma200 = spx_df["Close"].rolling(200).mean().iloc[-1]
            if close > sma50 and close > sma200:
                return "BULL_EXPANSION"
            elif close < sma50 and close < sma200:
                return "BEAR_CONTRACTION"
        else:
            if close > sma50:
                return "BULL_EXPANSION"
            elif close < sma50:
                return "BEAR_CONTRACTION"
                
        return "NEUTRAL"

    @staticmethod
    def compute_lagged_rolling_correlation(factor_series, asset_series, window=60, lag=3):
        if len(factor_series) < (window + lag) or len(asset_series) < (window + lag):
            return 1.0, False
        
        delta_factor = factor_series.diff().iloc[-(window + lag):-lag].values
        asset_returns = asset_series.pct_change().iloc[-window:].values

        if len(delta_factor) != len(asset_returns) or np.std(delta_factor) == 0 or np.std(asset_returns) == 0:
            return 1.0, False

        corr, _ = spearmanr(delta_factor, asset_returns)
        if np.isnan(corr):
            return 1.0, False

        if abs(corr) <= 0.15:
            return 0.0, True
        
        sign = 1.0 if corr > 0 else -1.0
        return sign, False

    @staticmethod
    def compute_frequency_matched_weight(base_weight, hit_rate, regime="BULL_EXPANSION", cluster="D", alpha=0.8, w_min=0.5, w_max=4.0):
        """
        REJİM-KOŞULLU ÇİFT HAFIZA AĞIRLIK MOTORU:
        Boğada hacim/momentum faktörlerini, ayıda kredi/faiz defansif faktörlerini korur.
        """
        # Rejime göre öncül teşvik çarpanı
        regime_multiplier = 1.0
        if regime == "BULL_EXPANSION":
            if cluster == "D": # Mikroyapı ve momentum boğada daha etkilidir
                regime_multiplier = 1.15
            elif cluster == "C":
                regime_multiplier = 0.90
        elif regime == "BEAR_CONTRACTION":
            if cluster in ["B", "C"]: # Kredi ve faiz ayıda daha belirleyicidir
                regime_multiplier = 1.20
            elif cluster == "D":
                regime_multiplier = 0.85

        dynamic_w = base_weight * regime_multiplier * (1.0 + alpha * (hit_rate - 0.5))
        return float(np.clip(dynamic_w, w_min, w_max))

    @staticmethod
    def evaluate_crisis_lock_with_hysteresis(z_credit, z_vix, z_rates, z_dxy, current_vix_val, current_state=False, consecutive_breaches=0):
        """
        🛡️ VIX MUTLAK TABAN KALKANI İLE GÜÇLENDİRİLMİŞ HYSTERESIS KRİZ KİLİDİ:
        VIX mutlak değeri 20'nin altındayken standart sapma ne olursa olsun kriz kilitlenemez!
        """
        cfg = CRISIS_CONFIG
        anomaly_score = float(np.linalg.norm([z_credit, z_vix, z_rates, z_dxy]) / 2.0)

        # Mutlak VIX Güvenlik Kalkanı
        is_vix_above_floor = (current_vix_val >= cfg["vix_absolute_floor"])

        # Kriz tetikleme şartı (Sadece VIX gerçekten yüksekse)
        enter_condition = False
        if is_vix_above_floor:
            enter_condition = (
                (anomaly_score > cfg["upper_threshold"] and consecutive_breaches >= cfg["enter_consecutive_bars"]) or
                (z_vix > cfg["vix_spike_threshold"] and z_credit > cfg["credit_spike_threshold"])
            )

        exit_condition = (anomaly_score < cfg["lower_threshold"]) or (not is_vix_above_floor and anomaly_score < cfg["upper_threshold"])

        new_state = current_state
        if not current_state and enter_condition:
            new_state = True
        elif current_state and exit_condition:
            new_state = False

        return new_state, anomaly_score, is_vix_above_floor
