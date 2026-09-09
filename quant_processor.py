"""
Robust Quant Processor: Mathematics, Correlation Sign & Self-Calibration
"""
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from config import CRISIS_CONFIG

class RobustQuantProcessor:
    @staticmethod
    def compute_z_score(series, window=32):
        """Belirtilen pencerede Z-Score hesaplar."""
        if len(series) < window or series.std() == 0:
            return 0.0
        rolling_mean = series.rolling(window).mean()
        rolling_std = series.rolling(window).std() + 1e-9
        return float((series.iloc[-1] - rolling_mean.iloc[-1]) / rolling_std.iloc[-1])

    @staticmethod
    def compute_ratio_z(df_num, df_denom, window=32):
        """İki serinin rasyosunun Z-Score'unu hesaplar (Örn: HYG/LQD, Bakır/Altın)."""
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
    def compute_lagged_rolling_correlation(factor_series, asset_series, window=60, lag=3):
        """
        SIFIR LOOK-AHEAD BİAS KORELASYON MOTORU:
        Canlı barda ileri getiri bilinemeyeceğinden k periyot geriden teyitli hesaplar.
        """
        if len(factor_series) < (window + lag) or len(asset_series) < (window + lag):
            return 1.0, False # Yetersiz veride öncülü koru
        
        # k periyot kaydırılmış faktör değişimi ile varlık getirisini eşleştir
        delta_factor = factor_series.diff().iloc[-(window + lag):-lag].values
        asset_returns = asset_series.pct_change().iloc[-window:].values

        if len(delta_factor) != len(asset_returns) or np.std(delta_factor) == 0 or np.std(asset_returns) == 0:
            return 1.0, False

        corr, _ = spearmanr(delta_factor, asset_returns)
        if np.isnan(corr):
            return 1.0, False

        # Rejim kararsız bandı (-0.15 ile +0.15 arası pasif)
        if abs(corr) <= 0.15:
            return 0.0, True # Kararsız rejim
        
        sign = 1.0 if corr > 0 else -1.0
        return sign, False

    @staticmethod
    def compute_frequency_matched_weight(base_weight, hit_rate, alpha=0.8, w_min=0.5, w_max=4.0):
        """
        FREKANS-DUYARLI ÖZ-KALİBRASYON:
        Her faktörün kendi zaman pencereli yön isabetine göre dinamik ağırlık çarpanı.
        """
        # HitRate 0.5 ise ağırlık değişmez; 0.5'ten yüksekse ödül, düşükse ceza alır
        dynamic_w = base_weight * (1.0 + alpha * (hit_rate - 0.5))
        return float(np.clip(dynamic_w, w_min, w_max))

    @staticmethod
    def evaluate_crisis_lock_with_hysteresis(z_credit, z_vix, z_rates, z_dxy, current_state=False, consecutive_breaches=0):
        """
        HYSTERESIS KRİZ KİLİDİ:
        Giriş ve çıkış eşikleri farklıdır; tekil iğneler sistemi gereksiz kilitlemez.
        """
        cfg = CRISIS_CONFIG
        anomaly_score = float(np.linalg.norm([z_credit, z_vix, z_rates, z_dxy]) / 2.0)

        enter_condition = (
            (anomaly_score > cfg["upper_threshold"] and consecutive_breaches >= cfg["enter_consecutive_bars"]) or
            (z_vix > cfg["vix_spike_threshold"] and z_credit > cfg["credit_spike_threshold"])
        )
        exit_condition = (anomaly_score < cfg["lower_threshold"])

        new_state = current_state
        if not current_state and enter_condition:
            new_state = True
        elif current_state and exit_condition:
            new_state = False

        return new_state, anomaly_score
