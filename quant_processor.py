"""
Robust Quant Processor: Volume Flow, Intraday Velocity & Hysteresis State Transition
"""
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from config import CRISIS_CONFIG, ASSET_CLOCKS, CATALYST_WINDOWS_UTC, SIGNAL_THRESHOLDS

class RobustQuantProcessor:
    @staticmethod
    def get_asset_session_status(asset_key):
        clock = ASSET_CLOCKS.get(asset_key, {})
        if not clock:
            return "CANLI", 1.0

        now = datetime.now(timezone.utc)
        current_hour = now.hour + (now.minute / 60.0)
        current_day = now.weekday()

        if clock["market"] == "CRYPTO":
            return "CANLI (24/7)", 1.0

        if current_day not in clock.get("days", [0, 1, 2, 3, 4]):
            return "HAFTA SONU (KAPALI)", 0.4

        open_h = clock["open_utc"]
        close_h = clock["close_utc"]

        if open_h <= current_hour <= close_h:
            return "CANLI SEANS", 1.0
        elif (open_h - 4.0) <= current_hour < open_h:
            return "SEANS ÖNCESİ (PRE-MARKET)", 0.6
        else:
            return "KAPALI (SEANS DIŞI)", 0.5

    @staticmethod
    def check_catalyst_event_window():
        now = datetime.now(timezone.utc)
        current_hour = now.hour + (now.minute / 60.0)
        current_day = now.weekday()

        if current_day in [0, 1, 2, 3, 4]:
            for w in CATALYST_WINDOWS_UTC:
                if w["start"] <= current_hour <= w["end"]:
                    return True, w["desc"]
        return False, "Sakin Veri Dönemi"

    @staticmethod
    def compute_intraday_direction_momentum(df_1h, fast_window=4, slow_window=24):
        """
        🧭 1. SÜTUN: VARLIĞA ÖZEL YÖN İVMESİ
        4 saatlik anlık yön (%60) ile 24 saatlik yapısal yönü (%40) harmanlayarak
        gürültüyü süzer ama yön kırılımını kaçırmaz.
        """
        if df_1h.empty or len(df_1h) < 2:
            return 0.0
        close = df_1h["Close"]
        w_fast = min(fast_window, len(close) - 1)
        roc_4h = ((close.iloc[-1] - close.iloc[-w_fast - 1]) / (close.iloc[-w_fast - 1] + 1e-9)) * 100.0
        w_slow = min(slow_window, len(close) - 1)
        roc_24h = ((close.iloc[-1] - close.iloc[-w_slow - 1]) / (close.iloc[-w_slow - 1] + 1e-9)) * 100.0

        blended = (roc_4h * 1.2) + (roc_24h * 0.4)
        return float(np.clip(blended * 1.2, -3.5, 3.5))

    @staticmethod
    def compute_asset_volume_liquidity_flow(df_1h, window=24):
        """
        💧 2. SÜTUN: VARLIĞA ÖZEL LİKİDİTE VE HACİM AKIŞI
        RVOL (Göreceli Hacim) + CLV (Kapanış Gücü) = Kurumsal Para Giriş/Çıkışı.
        """
        if df_1h.empty or len(df_1h) < 4 or "Volume" not in df_1h.columns:
            return 0.0
        
        close = df_1h["Close"]
        high = df_1h["High"]
        low = df_1h["Low"]
        vol = df_1h["Volume"]

        # 1. Kapanış Lokasyon Değeri (CLV): Mumun tepesinde mi kapattı dibinde mi?
        range_span = high.iloc[-1] - low.iloc[-1]
        clv = ((close.iloc[-1] - low.iloc[-1]) - (high.iloc[-1] - close.iloc[-1])) / (range_span + 1e-9)

        # 2. Göreceli Hacim (RVOL): Son saatlerin hacmi ortalamanın kaç katı?
        w = min(window, len(vol) - 1)
        mean_vol = vol.tail(w).mean() + 1e-9
        rvol = vol.iloc[-1] / mean_vol

        # 3. Akış Puanı = CLV * RVOL
        flow_score = clv * min(max(rvol, 0.5), 3.0) * 2.0
        return float(np.clip(flow_score, -3.0, 3.0))

    @staticmethod
    def compute_usd_strength_impulse(dxy_df_1h, window=4):
        """
        💵 3. SÜTUN: USD GÜCÜ & DOLAR LİKİDİTE BASKISI
        Doların son 4 saatlik ve 24 saatlik ivmesini ölçer.
        """
        if dxy_df_1h.empty or len(dxy_df_1h) < 2:
            return 0.0
        close = dxy_df_1h["Close"]
        w = min(window, len(close) - 1)
        roc_4h = ((close.iloc[-1] - close.iloc[-w - 1]) / (close.iloc[-w - 1] + 1e-9)) * 100.0
        return float(np.clip(roc_4h * 5.0, -3.0, 3.0))

    @staticmethod
    def resolve_signal_with_hysteresis(current_score, previous_signal="NÖTR (BEKLE)", bull_clusters=0, bear_clusters=0):
        """
        🛡️ SİNYAL TİTREŞİMİNİ (WHIPSAW) ÖNLEYEN HİSTEREZİS (SCHMITT TRIGGER) MOTORU:
        Sinyal küçük dalgalanmalarda değişmez; yön değişimi için net bir eşik kırılımı gerekir.
        """
        t = SIGNAL_THRESHOLDS
        prev = previous_signal if previous_signal else "NÖTR (BEKLE)"

        # 1. GÜÇLÜ AL KONTROLÜ
        if prev == "GÜÇLÜ AL":
            if current_score >= t["strong_buy_exit"]:
                return "GÜÇLÜ AL", "green", "🟢🟢"
        else:
            if current_score >= t["strong_buy_enter"] and bull_clusters >= 3:
                return "GÜÇLÜ AL", "green", "🟢🟢"

        # 2. AL KONTROLÜ
        if prev in ["AL", "GÜÇLÜ AL"]:
            # AL'a girdikten sonra puan 0.50'nin altına düşmedikçe NÖTR'e dönmez!
            if current_score >= t["buy_exit"]:
                return "AL", "lightgreen", "🟢"
        else:
            # Yeni AL sinyali için en az 1.20 aşılmalıdır
            if current_score >= t["buy_enter"]:
                return "AL", "lightgreen", "🟢"

        # 3. GÜÇLÜ SAT KONTROLÜ
        if prev == "GÜÇLÜ SAT":
            if current_score <= t["strong_sell_exit"]:
                return "GÜÇLÜ SAT", "darkred", "🔴🔴"
        else:
            if current_score <= t["strong_sell_enter"] and bear_clusters >= 3:
                return "GÜÇLÜ SAT", "darkred", "🔴🔴"

        # 4. SAT KONTROLÜ
        if prev in ["SAT", "GÜÇLÜ SAT"]:
            # SAT'a girdikten sonra puan -0.50'nin üstüne çıkmadıkça NÖTR'e dönmez!
            if current_score <= t["sell_exit"]:
                return "SAT", "red", "🔴"
        else:
            # Yeni SAT için en az -1.20 kırılmalıdır
            if current_score <= t["sell_enter"]:
                return "SAT", "red", "🔴"

        # 5. NÖTR (Ölü Bant)
        return "NÖTR (BEKLE)", "gray", "⚪"

    @staticmethod
    def compute_credit_intraday_velocity(hyg_df, lqd_df, window=4):
        if hyg_df.empty or lqd_df.empty:
            return 0.0
        s1 = hyg_df["Close"]
        s2 = lqd_df["Close"]
        aligned = pd.concat([s1, s2], axis=1, join="inner").dropna()
        if len(aligned) < 2:
            return 0.0
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        w = min(window, len(ratio) - 1)
        roc_4h = ((ratio.iloc[-1] - ratio.iloc[-w - 1]) / (ratio.iloc[-w - 1] + 1e-9)) * 100.0
        return float(np.clip(roc_4h * 6.0, -3.0, 3.0))

    @staticmethod
    def compute_stagflation_shock(oil_df, transport_df, window=24):
        if oil_df.empty or transport_df.empty:
            return 0.0
        p_oil = float(oil_df["Close"].iloc[-1])
        p_iyt = float(transport_df["Close"].iloc[-1])
        mean_oil = oil_df["Close"].tail(window).mean()
        mean_iyt = transport_df["Close"].tail(window).mean()
        current_ratio = p_oil / (p_iyt + 1e-9)
        baseline_ratio = mean_oil / (mean_iyt + 1e-9)
        dev_pct = ((current_ratio - baseline_ratio) / (baseline_ratio + 1e-9)) * 100.0
        return float(np.clip(dev_pct * 0.4, -3.0, 3.0))

    @staticmethod
    def compute_yen_carry_shock(usdjpy_df, window=20):
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
        if len(aligned) < 2:
            return 0.0
        w = min(window, len(aligned))
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        mean = ratio.rolling(w).mean().iloc[-1]
        std = ratio.rolling(w).std().iloc[-1] + 1e-9
        return float(np.clip((ratio.iloc[-1] - mean) / std, -3.0, 3.0))

    @staticmethod
    def compute_z_score(series, window=24):
        if len(series) < 2:
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
                (z_vix > 2.5 and credit_velocity < -1.5)
            )

        exit_condition = (anomaly_score < cfg.get("lower_threshold", 1.5)) or (not is_vix_above_floor and anomaly_score < 2.0)
        new_state = current_state
        if not current_state and enter_condition:
            new_state = True
        elif current_state and exit_condition:
            new_state = False

        return new_state, anomaly_score, is_vix_above_floor
