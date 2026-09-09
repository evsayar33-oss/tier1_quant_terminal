"""
Robust Quant Processor: Real-Time Macro Shock & Liquidity Engine (No Lagging MAs!)
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
        """Fiyatın anlık ivmesini ve hızını hesaplar."""
        if df.empty or len(df) < window:
            return 0.0
        close = df["Close"]
        roc = ((close.iloc[-1] - close.iloc[-window]) / close.iloc[-window]) * 100.0
        # Gecikmeli ortalama yok; sadece anlık getiri ivmesi
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
    def detect_realtime_macro_regime(z_dxy, z_credit, z_rates, z_copper_gold, z_vix):
        """
        🔥 HAREKETLİ ORTALAMASIZ GERÇEK MAKRO ŞOK & LİKİDİTE DEDEKTÖRÜ:
        Fiyata değil; Dolar Likiditesi, Kredi Yayılımı, Tahvil Şoku ve VIX'e bakar.
        """
        # 1. SİSTEMİK LİKİDİTE ŞOKU (Global Liquidity Crunch)
        # Dolar fırlamış, Kredi çökmüş ve VIX yukarı patlamışsa
        if z_dxy > 1.0 and z_credit < -1.0 and z_vix > 1.2:
            return "🚨 SİSTEMİK LİKİDİTE ŞOKU (NAKDE KAÇIŞ)"

        # 2. TAHVİL / FAİZ ŞOKU (Rate Shock Spike)
        # 10 Yıllık faiz hızla tırmanıyor ve Dolar güçleniyorsa (Teknoloji katili)
        elif z_rates > 1.2 and z_dxy > 0.5:
            return "⚡ TAHVİL & FAİZ ŞOKU (TECH BASKISI)"

        # 3. KÜRESEL LİKİDİTE BOLLUĞU / RALLİ (Global Risk-On Injection)
        # Dolar zayıflıyor, Kredi piyasası coşkulu, Sanayi (Bakır/Altın) güçlü
        elif z_dxy < -0.5 and z_credit > 0.5 and z_copper_gold > 0.0:
            return "🟢 KÜRESEL LİKİDİTE RALLİSİ (RISK-ON)"

        # 4. KREDİ TEMERRÜT BASKISI (Credit Deterioration)
        elif z_credit < -1.2:
            return "⚠️ KREDİ PİYASASI STRESİ (BORÇLANMA KRİZİ)"

        # 5. DENGE / SIKIŞMA
        return "⚪ MAKRO DENGE / YATAY REJİM"

    @staticmethod
    def evaluate_crisis_lock_with_hysteresis(z_credit, z_vix, z_rates, z_dxy, current_vix_val, current_state=False, consecutive_breaches=0):
        cfg = CRISIS_CONFIG
        anomaly_score = float(np.linalg.norm([z_credit, z_vix, z_rates, z_dxy]) / 2.0)
        is_vix_above_floor = (current_vix_val >= cfg.get("vix_absolute_floor", 20.0))

        enter_condition = False
        if is_vix_above_floor:
            enter_condition = (
                (anomaly_score > cfg.get("upper_threshold", 2.2) and consecutive_breaches >= cfg.get("enter_consecutive_bars", 3)) or
                (z_vix > cfg.get("vix_spike_threshold", 2.5) and z_credit < -1.5)
            )

        exit_condition = (anomaly_score < cfg.get("lower_threshold", 1.5)) or (not is_vix_above_floor and anomaly_score < 2.0)

        new_state = current_state
        if not current_state and enter_condition:
            new_state = True
        elif current_state and exit_condition:
            new_state = False

        return new_state, anomaly_score, is_vix_above_floor
