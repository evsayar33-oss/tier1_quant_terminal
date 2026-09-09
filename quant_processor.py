"""
Robust Quant Processor: Real-Time Institutional Shock & Leading Indicator Engine
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
        if df.empty or len(df) < window:
            return 0.0
        close = df["Close"]
        roc = ((close.iloc[-1] - close.iloc[-window]) / close.iloc[-window]) * 100.0
        return float(np.clip(roc * 0.8, -3.0, 3.0))

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
    def compute_stagflation_shock(oil_df, transport_df, window=24):
        """
        🛢️ KÜRESEL STAGFLASYON / ENFLASYON ŞOKU MATEMATİĞİ:
        Küresel Ticaret/Navlun (IYT) düşerken Ham Petrol (CL=F) fırlıyorsa pozitif şok skoru üretir.
        """
        if oil_df.empty or transport_df.empty:
            return 0.0
        aligned = pd.concat([oil_df["Close"], transport_df["Close"]], axis=1, join="inner").dropna()
        if len(aligned) < 10:
            return 0.0
        
        # Petrol / Taşımacılık Rasyosu
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        w = min(window, len(ratio))
        z_ratio = (ratio.iloc[-1] - ratio.rolling(w).mean().iloc[-1]) / (ratio.rolling(w).std().iloc[-1] + 1e-9)
        return float(np.clip(z_ratio, -3.0, 3.0))

    @staticmethod
    def compute_yen_carry_shock(usdjpy_df, window=20):
        """
        💴 YEN CARRY TRADE ÇÖZÜLME ŞOKU:
        USD/JPY aniden çöküyorsa (Yen değer kazanıyorsa), küresel kaldıraç tasfiye ediliyor demektir!
        """
        if usdjpy_df.empty or len(usdjpy_df) < 5:
            return 0.0
        close = usdjpy_df["Close"]
        w = min(window, len(close))
        z = (close.iloc[-1] - close.rolling(w).mean().iloc[-1]) / (close.rolling(w).std().iloc[-1] + 1e-9)
        # Z-skorunun negatifi: Yen ne kadar sert fırlarsa risk o kadar büyür
        return float(np.clip(z, -3.0, 3.0))

    @staticmethod
    def detect_realtime_macro_regime(z_dxy, z_credit, z_rates, z_copper_gold, z_vix, stagflation_z, yen_carry_z):
        """
        🔥 5 BOYUTLU GERÇEK ZAMANLI KURUMSAL MAKRO ŞOK VE REJİM MOTORU
        """
        # 1. KÜRESEL ENFLASYON & STAGFLASYON ŞOKU
        if stagflation_z > 1.3 and z_rates > 0.5:
            return "🛢️ KÜRESEL ENFLASYON & STAGFLASYON ŞOKU (PETROL BASKISI)"

        # 2. SİSTEMİK LİKİDİTE ŞOKU & CARRY ÇÖZÜLMESİ
        elif (z_dxy > 1.0 and z_credit < -1.0) or (yen_carry_z < -1.8 and z_vix > 1.2):
            return "🚨 SİSTEMİK LİKİDİTE & CARRY ÇÖZÜLME ŞOKU (NAKDE KAÇIŞ)"

        # 3. TAHVİL / FAİZ ŞOKU
        elif z_rates > 1.4:
            return "⚡ TAHVİL & GETİRİ EĞRİSİ ŞOKU (TECH BASKISI)"

        # 4. KREDİ TEMERRÜT BASKISI
        elif z_credit < -1.4:
            return "⚠️ KREDİ PİYASASI TEMERRÜT STRESİ"

        # 5. KÜRESEL LİKİDİTE RALLİSİ (RISK-ON)
        elif z_dxy < -0.6 and z_credit > 0.6 and stagflation_z < 0.2:
            return "🟢 KÜRESEL LİKİDİTE RALLİSİ (RISK-ON BOĞA)"

        # 6. DENGE
        return "⚪ MAKRO DENGE / SIKIŞMA"

    @staticmethod
    def evaluate_crisis_lock_with_hysteresis(z_credit, z_vix, z_rates, z_dxy, current_vix_val, current_state=False, consecutive_breaches=0):
        cfg = CRISIS_CONFIG
        anomaly_score = float(np.linalg.norm([z_credit, z_vix, z_rates, z_dxy]) / 2.0)
        is_vix_above_floor = (current_vix_val >= cfg.get("vix_absolute_floor", 20.0))

        enter_condition = False
        if is_vix_above_floor:
            enter_condition = (
                (anomaly_score > cfg.get("upper_threshold", 2.2) and consecutive_breaches >= cfg.get("enter_consecutive_bars", 3)) or
                (z_vix > cfg.get("vix_spike_threshold", 2.5) and z_credit < -1.8)
            )

        exit_condition = (anomaly_score < cfg.get("lower_threshold", 1.5)) or (not is_vix_above_floor and anomaly_score < 2.0)

        new_state = current_state
        if not current_state and enter_condition:
            new_state = True
        elif current_state and exit_condition:
            new_state = False

        return new_state, anomaly_score, is_vix_above_floor
