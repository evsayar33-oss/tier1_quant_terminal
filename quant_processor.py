"""
Robust Quant Processor: 4-Hour Velocity & Intraday Shock Engine (No Lagging MAs!)
"""
import numpy as np
import pandas as pd
from config import CRISIS_CONFIG

class RobustQuantProcessor:
    @staticmethod
    def compute_intraday_momentum(df_1h, fast_window=4, slow_window=24):
        """
        ⚡ 4 SAATLİK VE 24 SAATLİK ANLIK İVME MOTORU:
        14 günlük geçmiş ortalamaları çöpe atar; son 4 saatlik sert çöküşü anında yakalar.
        """
        if df_1h.empty or len(df_1h) < 4:
            return 0.0
        close = df_1h["Close"]
        
        # 4 Saatlik Değişim
        w_fast = min(fast_window, len(close) - 1)
        roc_4h = ((close.iloc[-1] - close.iloc[-w_fast - 1]) / close.iloc[-w_fast - 1]) * 100.0

        # 24 Saatlik (1 Günlük) Değişim
        w_slow = min(slow_window, len(close) - 1)
        roc_24h = ((close.iloc[-1] - close.iloc[-w_slow - 1]) / close.iloc[-w_slow - 1]) * 100.0

        # Anlık 4 saate %70, 24 saate %30 ağırlık ver
        blended_roc = (roc_4h * 1.5) + (roc_24h * 0.5)
        return float(np.clip(blended_roc * 1.2, -3.5, 3.5))

    @staticmethod
    def compute_dxy_intraday_velocity(dxy_df_1h, window=4):
        """
        ⚡ DXY 4 SAATLİK ANLIK LİKİDİTE ŞOKU HIZI:
        Dolar son 4 saatte yukarı patladıysa pozitif Z-hızı üretir (Hisseleri ezer).
        """
        if dxy_df_1h.empty or len(dxy_df_1h) < 4:
            return 0.0
        close = dxy_df_1h["Close"]
        w = min(window, len(close) - 1)
        roc_4h = ((close.iloc[-1] - close.iloc[-w - 1]) / close.iloc[-w - 1]) * 100.0
        # Dolar için %0.2'lik 4 saatlik hareket devasadır
        return float(np.clip(roc_4h * 5.0, -3.0, 3.0))

    @staticmethod
    def compute_credit_intraday_velocity(hyg_df, lqd_df, window=4):
        """⚡ HYG/LQD 4 SAATLİK ANLIK KREDİ AKIŞ HIZI"""
        if hyg_df.empty or lqd_df.empty:
            return 0.0
        s1 = hyg_df["Close"]
        s2 = lqd_df["Close"]
        aligned = pd.concat([s1, s2], axis=1, join="inner").dropna()
        if len(aligned) < 4:
            return 0.0
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        w = min(window, len(ratio) - 1)
        roc_4h = ((ratio.iloc[-1] - ratio.iloc[-w - 1]) / ratio.iloc[-w - 1]) * 100.0
        return float(np.clip(roc_4h * 6.0, -3.0, 3.0))

    @staticmethod
    def compute_stagflation_shock(oil_df, transport_df, window=24):
        """🛢️ Petrol / Taşımacılık 24 Saatlik Şok Rasyosu"""
        if oil_df.empty or transport_df.empty:
            return 0.0
        s1 = oil_df["Close"]
        s2 = transport_df["Close"]
        aligned = pd.concat([s1, s2], axis=1, join="inner").dropna()
        if len(aligned) < 5:
            return 0.0
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        w = min(window, len(ratio))
        mean_val = ratio.rolling(w).mean().iloc[-1]
        std_val = ratio.rolling(w).std().iloc[-1] + 1e-9
        return float(np.clip((ratio.iloc[-1] - mean_val) / std_val, -3.0, 3.0))

    @staticmethod
    def compute_yen_carry_shock(usdjpy_df, window=20):
        """💴 USD/JPY 4-20 Saatlik Carry İvmesi"""
        if usdjpy_df.empty or len(usdjpy_df) < 5:
            return 0.0
        close = usdjpy_df["Close"]
        w = min(window, len(close))
        mean_val = close.rolling(w).mean().iloc[-1]
        std_val = close.rolling(w).std().iloc[-1] + 1e-9
        return float(np.clip((close.iloc[-1] - mean_val) / std_val, -3.0, 3.0))

    @staticmethod
    def compute_ratio_z(df_num, df_denom, window=24):
        if df_num.empty or df_denom.empty:
            return 0.0
        s1 = df_num["Close"]
        s2 = df_denom["Close"]
        aligned = pd.concat([s1, s2], axis=1, join="inner").dropna()
        if len(aligned) < 5:
            return 0.0
        w = min(window, len(aligned))
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        mean = ratio.rolling(w).mean().iloc[-1]
        std = ratio.rolling(w).std().iloc[-1] + 1e-9
        return float(np.clip((ratio.iloc[-1] - mean) / std, -3.0, 3.0))

    @staticmethod
    def compute_z_score(series, window=24):
        if len(series) < 5:
            return 0.0
        w = min(window, len(series))
        return float(np.clip((series.iloc[-1] - series.rolling(w).mean().iloc[-1]) / (series.rolling(w).std().iloc[-1] + 1e-9), -3.0, 3.0))

    @staticmethod
    def detect_realtime_macro_regime(dxy_velocity, credit_velocity, z_real_rate, z_vix, stagflation_z, yen_carry_z):
        if stagflation_z > 1.2:
            return "🛢️ KÜRESEL STAGFLASYON ŞOKU (PETROL BASKISI)"
        elif (dxy_velocity > 1.0 and credit_velocity < -0.8) or (yen_carry_z < -1.4 and z_vix > 1.0):
            return "🚨 SİSTEMİK LİKİDİTE & CARRY ÇÖZÜLME ŞOKU (NAKDE KAÇIŞ)"
        elif z_real_rate > 1.2:
            return "⚡ TAHVİL REEL GETİRİ ŞOKU (TECH BASKISI)"
        elif credit_velocity < -1.2:
            return "⚠️ KREDİ PİYASASI ANLIK TEMERRÜT STRESİ"
        elif dxy_velocity < -0.5 and credit_velocity > 0.5:
            return "🟢 KÜRESEL LİKİDİTE RALLİSİ (RISK-ON BOĞA)"
        return "⚪ MAKRO DENGE / SIKIŞMA"

    @staticmethod
    def evaluate_crisis_lock_with_hysteresis(credit_velocity, z_vix, z_real_rate, dxy_velocity, current_vix_val, current_state=False, consecutive_breaches=0):
        cfg = CRISIS_CONFIG
        anomaly_score = float(np.linalg.norm([abs(credit_velocity), z_vix, z_real_rate, abs(dxy_velocity)]) / 2.0)
        is_vix_above_floor = (current_vix_val >= cfg.get("vix_absolute_floor", 20.0))

        enter_condition = False
        if is_vix_above_floor:
            enter_condition = (
                (anomaly_score > cfg.get("upper_threshold", 2.2) and consecutive_breaches >= cfg.get("enter_consecutive_bars", 3)) or
                (z_vix > cfg.get("vix_spike_threshold", 2.5) and credit_velocity < -1.5)
            )

        exit_condition = (anomaly_score < cfg.get("lower_threshold", 1.5)) or (not is_vix_above_floor and anomaly_score < 2.0)
        new_state = current_state
        if not current_state and enter_condition:
            new_state = True
        elif current_state and exit_condition:
            new_state = False

        return new_state, anomaly_score, is_vix_above_floor
