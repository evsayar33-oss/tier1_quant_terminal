"""
Robust Quant Processor: Institutional Macro Engine & Curve Decomposer (v6)
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
        s1 = df_num["Close"].copy()
        s2 = df_denom["Close"].copy()
        s1.index = s1.index.tz_localize(None) if s1.index.tz is not None else s1.index
        s2.index = s2.index.tz_localize(None) if s2.index.tz is not None else s2.index

        aligned = pd.concat([s1, s2], axis=1, join="inner").dropna()
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
        """🛢️ Petrol / Taşımacılık Rasyosu (Saat Dilimi Düzeltilmiş)"""
        if oil_df.empty or transport_df.empty:
            return 0.0
        s1 = oil_df["Close"].copy()
        s2 = transport_df["Close"].copy()
        s1.index = s1.index.tz_localize(None) if s1.index.tz is not None else s1.index
        s2.index = s2.index.tz_localize(None) if s2.index.tz is not None else s2.index

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
        """💴 USD/JPY Çapraz Kur Şoku (Yen ani güçlenmesi)"""
        if usdjpy_df.empty or len(usdjpy_df) < 5:
            return 0.0
        close = usdjpy_df["Close"]
        w = min(window, len(close))
        mean_val = close.rolling(w).mean().iloc[-1]
        std_val = close.rolling(w).std().iloc[-1] + 1e-9
        # USD/JPY düşüşü Yen'in değer kazandığını (Carry çözülmesini) gösterir
        return float(np.clip((close.iloc[-1] - mean_val) / std_val, -3.0, 3.0))

    @staticmethod
    def classify_yield_curve_dynamics(df_2y, df_10y, window=5):
        """
        📈 4'LÜ GETİRİ EĞRİSİ ANATOMİSİ:
        Bear/Bull Steepener & Flattener sınıflandırması.
        """
        if df_2y.empty or df_10y.empty or len(df_2y) < window or len(df_10y) < window:
            return "NÖTR EĞRİ", 0.0, 0.0

        d2y = df_2y["Close"].iloc[-1] - df_2y["Close"].iloc[-window]
        d10y = df_10y["Close"].iloc[-1] - df_10y["Close"].iloc[-window]

        if d10y > 0 and d2y > 0:
            if d10y >= d2y:
                label = "BEAR STEEPENER (Term Premium / Mali Endişe)"
            else:
                label = "BEAR FLATTENER (Şahin Fed / Faiz Artış Korkusu)"
        elif d10y < 0 and d2y < 0:
            if abs(d2y) >= abs(d10y):
                label = "BULL STEEPENER (Agresif Fed İndirimi / Resesyon)"
            else:
                label = "BULL FLATTENER (Disinflasyon Rallisi)"
        elif d10y > 0 and d2y <= 0:
            label = "STEEPENER (Eğri Dikleşiyor)"
        else:
            label = "FLATTENER (Eğri Yataylaşıyor)"

        return label, float(d2y), float(d10y)

    @staticmethod
    def detect_realtime_macro_regime(z_dxy, z_credit, z_real_rate, z_breakeven, z_vix, stagflation_z, yen_carry_z, gold_mom, curve_label):
        """
        🏛️ REVİZE GERÇEK ZAMANLI KURUMSAL MAKRO ŞOK & REJİM MOTORU
        """
        # =====================================================================
        # 1. ENFLASYON & STAGFLASYON ŞOKU
        # =====================================================================
        # Petrol/Taşımacılık patlamış VE/VEYA Breakeven enflasyon fırlamışsa
        if stagflation_z > 1.2 or (z_breakeven > 1.3 and z_real_rate < 0.5):
            return "🛢️ KÜRESEL STAGFLASYON ŞOKU (PETROL/ENFLASYON BASKISI)"

        # =====================================================================
        # 2. TAHVİL REEL GETİRİ ŞOKU (DFII10 DETERMINİSTİK TETİKLEYİCİ)
        # =====================================================================
        # 10Y TIPS Reel Getirisi (DFII10) sert sıçradıysa -> Nasdaq ve Çarpan Katili
        if z_real_rate > 1.2:
            return f"⚡ TAHVİL REEL GETİRİ ŞOKU: {curve_label}"

        # =====================================================================
        # 3. YEN CARRY TRADE ÇÖZÜLME ŞOKU (DXY'DEN AYRI ÇAPRAZ KUR TETİKLEYİCİ)
        # =====================================================================
        # Yen aniden fırlamışsa (USD/JPY sert çakılmışsa), DXY'ye bakılmaksızın tetiklenir
        if yen_carry_z < -1.4 and z_vix > 1.0:
            return "🚨 YEN CARRY TRADE ÇÖZÜLMESİ (KÜRESEL MARGİN CALL)"

        # =====================================================================
        # 4. SİSTEMİK LİKİDİTE SIKIŞMASI (GENİŞ DOLAR BASKISI)
        # =====================================================================
        if z_dxy > 1.2 and z_credit < -1.0:
            return "🚨 SİSTEMİK DOLAR LİKİDİTE SIKIŞMASI (NAKDE KAÇIŞ)"

        # =====================================================================
        # 5. KREDİ TEMERRÜT BASKISI
        # =====================================================================
        if z_credit < -1.4:
            return "⚠️ KREDİ PİYASASI TEMERRÜT STRESİ (HY OAS GENİŞLİYOR)"

        # =====================================================================
        # 6. KÜRESEL LİKİDİTE RALLİSİ (RISK-ON) — ALTINSIZ TETİKLEYİCİ
        # =====================================================================
        # Ana Tetikleyiciler: Kredi güçlü, DXY stres bandında değil (-1 ile +0.5), VIX sakin
        is_risk_on_triggered = (z_credit > 0.5) and (-1.0 <= z_dxy <= 0.5) and (z_vix < 0.0)

        if is_risk_on_triggered:
            # İKİNCİL ETİKETLEME (Altın ve Dolar alt-tipi belirler, tetikleyici değildir)
            if z_dxy < -0.6 and gold_mom > 0.5:
                return "🟢 REFLASYONİST RISK-ON (DOLAR ZAYIFLIĞI ÖNCÜLÜKLÜ RALLİ)"
            else:
                return "🟢 KLASİK GOLDILOCKS RISK-ON (DİSİNFLASYONİST BÜYÜME)"

        return "⚪ MAKRO DENGE / SIKIŞMA"

    @staticmethod
    def evaluate_crisis_lock_with_hysteresis(z_credit, z_vix, z_real_rate, z_dxy, current_vix_val, current_state=False, consecutive_breaches=0):
        cfg = CRISIS_CONFIG
        anomaly_score = float(np.linalg.norm([z_credit, z_vix, z_real_rate, z_dxy]) / 2.0)
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
