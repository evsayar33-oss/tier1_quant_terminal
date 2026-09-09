"""
Robust Quant Processor: Real-Time ETF Metrics & Strict Barra Normalization (v13)
"""
import numpy as np
import pandas as pd
from datetime import datetime, timezone

class RobustQuantProcessor:
    @staticmethod
    def get_asset_session_status(asset_key):
        clocks = {
            "SPX": {"open_utc": 13.5, "close_utc": 20.0, "crypto": False},
            "NQ":  {"open_utc": 13.5, "close_utc": 20.0, "crypto": False},
            "XAU": {"open_utc": 7.0,  "close_utc": 21.0, "crypto": False},
            "XAG": {"open_utc": 7.0,  "close_utc": 21.0, "crypto": False},
            "BTC": {"open_utc": 0.0,  "close_utc": 24.0, "crypto": True},
            "ETH": {"open_utc": 0.0,  "close_utc": 24.0, "crypto": True}
        }
        clock = clocks.get(asset_key, {})
        if clock.get("crypto", False):
            return "CANLI (24/7)", 1.0

        now = datetime.now(timezone.utc)
        current_hour = now.hour + (now.minute / 60.0)
        current_day = now.weekday()

        if current_day in [5, 6]:
            return "HAFTA SONU (KAPALI)", 0.4

        open_h = clock.get("open_utc", 13.5)
        close_h = clock.get("close_utc", 20.0)

        if open_h <= current_hour <= close_h:
            return "CANLI SEANS", 1.0
        elif (open_h - 4.0) <= current_hour < open_h:
            return "SEANS ÖNCESİ (PRE-MARKET)", 0.7
        else:
            return "KAPALI (SEANS DIŞI)", 0.5

    @staticmethod
    def check_catalyst_event_window():
        now = datetime.now(timezone.utc)
        current_hour = now.hour + (now.minute / 60.0)
        current_day = now.weekday()
        if current_day in [0, 1, 2, 3, 4]:
            if 12.5 <= current_hour <= 13.5:
                return True, "ABD Makro Veri Saati (TÜFE/İstihdam)"
            elif 18.0 <= current_hour <= 19.5:
                return True, "Fed / FOMC Karar Saati"
        return False, "Sakin Veri Dönemi"

    @staticmethod
    def compute_intraday_direction_momentum(df_1h, fast_window=4, slow_window=24):
        if df_1h.empty or len(df_1h) < 2: return 0.0
        close = df_1h["Close"]
        w_fast = min(fast_window, len(close) - 1)
        roc_4h = ((close.iloc[-1] - close.iloc[-w_fast - 1]) / (close.iloc[-w_fast - 1] + 1e-9)) * 100.0
        w_slow = min(slow_window, len(close) - 1)
        roc_24h = ((close.iloc[-1] - close.iloc[-w_slow - 1]) / (close.iloc[-w_slow - 1] + 1e-9)) * 100.0
        blended = (roc_4h * 1.2) + (roc_24h * 0.4)
        return float(np.clip(blended * 1.0, -2.0, 2.0))

    @staticmethod
    def compute_asset_volume_liquidity_flow(df_1h, window=24):
        if df_1h.empty or len(df_1h) < 4 or "Volume" not in df_1h.columns: return 0.0
        close = df_1h["Close"]
        high = df_1h["High"]
        low = df_1h["Low"]
        vol = df_1h["Volume"]
        range_span = high.iloc[-1] - low.iloc[-1]
        clv = ((close.iloc[-1] - low.iloc[-1]) - (high.iloc[-1] - close.iloc[-1])) / (range_span + 1e-9)
        w = min(window, len(vol) - 1)
        rvol = vol.iloc[-1] / (vol.tail(w).mean() + 1e-9)
        return float(np.clip(clv * min(max(rvol, 0.5), 2.5), -1.8, 1.8))

    @staticmethod
    def compute_usd_strength_impulse(dxy_df_1h, window=4):
        if dxy_df_1h.empty or len(dxy_df_1h) < 2: return 0.0
        close = dxy_df_1h["Close"]
        w = min(window, len(close) - 1)
        roc_4h = ((close.iloc[-1] - close.iloc[-w - 1]) / (close.iloc[-w - 1] + 1e-9)) * 100.0
        return float(np.clip(roc_4h * 4.0, -2.0, 2.0))

    @staticmethod
    def compute_market_breadth(rsp_df, spy_df, window=24):
        """RSP / SPY Rasyosu İvmesi (Piyasa Genişliği)"""
        if rsp_df.empty or spy_df.empty: return 0.0
        s1 = rsp_df["Close"]
        s2 = spy_df["Close"]
        aligned = pd.concat([s1, s2], axis=1, join="inner").dropna()
        if len(aligned) < 2: return 0.0
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        w = min(window, len(ratio) - 1)
        roc = ((ratio.iloc[-1] - ratio.iloc[-w - 1]) / (ratio.iloc[-w - 1] + 1e-9)) * 100.0
        return float(np.clip(roc * 2.5, -1.8, 1.8))

    @staticmethod
    def compute_gsr_velocity(xau_df, xag_df, window=24):
        """Altın / Gümüş Rasyosu (GSR) İvmesi"""
        if xau_df.empty or xag_df.empty: return 0.0
        s1 = xau_df["Close"]
        s2 = xag_df["Close"]
        aligned = pd.concat([s1, s2], axis=1, join="inner").dropna()
        if len(aligned) < 2: return 0.0
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        w = min(window, len(ratio) - 1)
        roc = ((ratio.iloc[-1] - ratio.iloc[-w - 1]) / (ratio.iloc[-w - 1] + 1e-9)) * 100.0
        return float(np.clip(roc * 2.0, -1.5, 1.5))

    @staticmethod
    def compute_credit_intraday_velocity(hyg_df, lqd_df, window=4):
        if hyg_df.empty or lqd_df.empty: return 0.0
        s1 = hyg_df["Close"]
        s2 = lqd_df["Close"]
        aligned = pd.concat([s1, s2], axis=1, join="inner").dropna()
        if len(aligned) < 2: return 0.0
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        w = min(window, len(ratio) - 1)
        roc_4h = ((ratio.iloc[-1] - ratio.iloc[-w - 1]) / (ratio.iloc[-w - 1] + 1e-9)) * 100.0
        return float(np.clip(roc_4h * 4.0, -2.0, 2.0))

    @staticmethod
    def compute_stagflation_shock(oil_df, transport_df, window=24):
        if oil_df.empty or transport_df.empty: return 0.0
        p_oil = float(oil_df["Close"].iloc[-1])
        p_iyt = float(transport_df["Close"].iloc[-1])
        mean_oil = oil_df["Close"].tail(window).mean()
        mean_iyt = transport_df["Close"].tail(window).mean()
        current_ratio = p_oil / (p_iyt + 1e-9)
        baseline_ratio = mean_oil / (mean_iyt + 1e-9)
        dev_pct = ((current_ratio - baseline_ratio) / (baseline_ratio + 1e-9)) * 100.0
        return float(np.clip(dev_pct * 0.3, -2.0, 2.0))

    @staticmethod
    def compute_yen_carry_shock(usdjpy_df, window=20):
        if usdjpy_df.empty or len(usdjpy_df) < 5: return 0.0
        close = usdjpy_df["Close"]
        w = min(window, len(close))
        mean_val = close.rolling(w).mean().iloc[-1]
        std_val = close.rolling(w).std().iloc[-1] + 1e-9
        return float(np.clip((close.iloc[-1] - mean_val) / std_val, -2.0, 2.0))

    @staticmethod
    def compute_ratio_z(df_num, df_denom, window=24):
        if df_num.empty or df_denom.empty: return 0.0
        s1 = df_num["Close"]
        s2 = df_denom["Close"]
        aligned = pd.concat([s1, s2], axis=1, join="inner").dropna()
        if len(aligned) < 2: return 0.0
        w = min(window, len(aligned))
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        mean = ratio.rolling(w).mean().iloc[-1]
        std = ratio.rolling(w).std().iloc[-1] + 1e-9
        return float(np.clip((ratio.iloc[-1] - mean) / std, -2.0, 2.0))

    @staticmethod
    def compute_z_score(series, window=24):
        if len(series) < 2: return 0.0
        w = min(window, len(series))
        return float(np.clip((series.iloc[-1] - series.rolling(w).mean().iloc[-1]) / (series.rolling(w).std().iloc[-1] + 1e-9), -2.0, 2.0))

    @staticmethod
    def detect_realtime_macro_regime(dxy_velocity, credit_velocity, real_yield_z, z_vix, stagflation_z, yen_carry_z):
        if stagflation_z > 1.0: return "🛢️ KÜRESEL STAGFLASYON ŞOKU (PETROL BASKISI)"
        elif (dxy_velocity > 0.8 and credit_velocity < -0.6) or (yen_carry_z < -1.2 and z_vix > 0.8): return "🚨 SİSTEMİK LİKİDİTE ŞOKU (NAKDE KAÇIŞ)"
        elif real_yield_z > 1.0: return "⚡ TAHVİL REEL GETİRİ ŞOKU (TECH BASKISI)"
        elif credit_velocity < -1.0: return "⚠️ KREDİ PİYASASI TEMERRÜT STRESİ"
        elif dxy_velocity < -0.4 and credit_velocity > 0.4: return "🟢 KÜRESEL LİKİDİTE RALLİSİ (RISK-ON)"
        return "⚪ MAKRO DENGE / SIKIŞMA"

    @staticmethod
    def resolve_signal_with_hysteresis(current_score, previous_signal="NÖTR (BEKLE)", bull_clusters=0, bear_clusters=0):
        prev = previous_signal if previous_signal else "NÖTR (BEKLE)"

        if prev == "GÜÇLÜ AL":
            if current_score >= 1.6: return "GÜÇLÜ AL", "green", "🟢🟢"
        else:
            if current_score >= 2.0 and bull_clusters >= 3: return "GÜÇLÜ AL", "green", "🟢🟢"

        if prev in ["AL", "GÜÇLÜ AL"]:
            if current_score >= 0.4: return "AL", "lightgreen", "🟢"
        else:
            if current_score >= 0.9: return "AL", "lightgreen", "🟢"

        if prev == "GÜÇLÜ SAT":
            if current_score <= -1.6: return "GÜÇLÜ SAT", "darkred", "🔴🔴"
        else:
            if current_score <= -2.0 and bear_clusters >= 3: return "GÜÇLÜ SAT", "darkred", "🔴🔴"

        if prev in ["SAT", "GÜÇLÜ SAT"]:
            if current_score <= -0.4: return "SAT", "red", "🔴"
        else:
            if current_score <= -0.9: return "SAT", "red", "🔴"

        return "NÖTR (BEKLE)", "gray", "⚪"
