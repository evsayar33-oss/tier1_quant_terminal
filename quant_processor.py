"""
Robust Quant Processor: Real-Time ETF Metrics & Strict Barra Normalization (v18)
"""
import numpy as np
import pandas as pd
from datetime import datetime, timezone

try:
    from config import CRISIS_CONFIG, SIGNAL_THRESHOLDS, ASSET_CLOCKS, CATALYST_WINDOWS_UTC
except Exception:
    CRISIS_CONFIG = {
        "upper_threshold": 2.2, "lower_threshold": 1.5,
        "enter_consecutive_bars": 3, "vix_spike_threshold": 2.5,
        "vix_absolute_floor": 20.0
    }
    SIGNAL_THRESHOLDS = {
        "strong_buy_enter": 1.8, "strong_buy_exit": 1.1,
        "buy_enter": 0.7, "buy_exit": 0.25,
        "strong_sell_enter": -1.8, "strong_sell_exit": -1.1,
        "sell_enter": -0.7, "sell_exit": -0.25
    }
    ASSET_CLOCKS = {}
    CATALYST_WINDOWS_UTC = []


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
    def compute_intraday_direction_momentum(df_1h, fast_window=4, slow_window=24, vol_scale=1.0):
        if df_1h.empty or len(df_1h) < 2:
            return 0.0
        close = df_1h["Close"]
        w_fast = min(fast_window, len(close) - 1)
        roc_4h = ((close.iloc[-1] - close.iloc[-w_fast - 1]) / (close.iloc[-w_fast - 1] + 1e-9)) * 100.0
        w_slow = min(slow_window, len(close) - 1)
        roc_24h = ((close.iloc[-1] - close.iloc[-w_slow - 1]) / (close.iloc[-w_slow - 1] + 1e-9)) * 100.0
        blended = (roc_4h * 1.2) + (roc_24h * 0.4)

        scale = max(float(vol_scale), 0.5)
        norm_blended = (blended / scale) * 1.2
        return float(np.clip(norm_blended, -2.0, 2.0))

    @staticmethod
    def compute_asset_volume_liquidity_flow(df_1h, window=24):
        if df_1h.empty or len(df_1h) < 4 or "Volume" not in df_1h.columns:
            return 0.0
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
        if dxy_df_1h.empty or len(dxy_df_1h) < 2:
            return 0.0
        close = dxy_df_1h["Close"]
        w = min(window, len(close) - 1)
        roc_4h = ((close.iloc[-1] - close.iloc[-w - 1]) / (close.iloc[-w - 1] + 1e-9)) * 100.0
        return float(np.clip(roc_4h * 4.0, -2.0, 2.0))

    @staticmethod
    def compute_market_breadth(rsp_df, spy_df, window=24):
        if rsp_df.empty or spy_df.empty:
            return 0.0
        s1 = rsp_df["Close"]
        s2 = spy_df["Close"]
        aligned = pd.concat([s1, s2], axis=1, join="inner").dropna()
        if len(aligned) < 2:
            return 0.0
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        w = min(window, len(ratio) - 1)
        roc = ((ratio.iloc[-1] - ratio.iloc[-w - 1]) / (ratio.iloc[-w - 1] + 1e-9)) * 100.0
        return float(np.clip(roc * 2.5, -1.8, 1.8))

    @staticmethod
    def compute_gsr_velocity(xau_df, xag_df, window=24):
        if xau_df.empty or xag_df.empty:
            return 0.0
        s1 = xau_df["Close"]
        s2 = xag_df["Close"]
        aligned = pd.concat([s1, s2], axis=1, join="inner").dropna()
        if len(aligned) < 2:
            return 0.0
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        w = min(window, len(ratio) - 1)
        roc = ((ratio.iloc[-1] - ratio.iloc[-w - 1]) / (ratio.iloc[-w - 1] + 1e-9)) * 100.0
        return float(np.clip(roc * 2.0, -1.5, 1.5))

    @staticmethod
    def compute_bond_duration_risk(tlt_df, shy_df, window=24):
        if tlt_df.empty or shy_df.empty:
            return 0.0
        s1 = tlt_df["Close"]
        s2 = shy_df["Close"]
        aligned = pd.concat([s1, s2], axis=1, join="inner").dropna()
        if len(aligned) < 2:
            return 0.0
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        w = min(window, len(ratio) - 1)
        roc = ((ratio.iloc[-1] - ratio.iloc[-w - 1]) / (ratio.iloc[-w - 1] + 1e-9)) * 100.0
        return float(np.clip(roc * 2.0, -1.8, 1.8))

    @staticmethod
    def compute_banking_stress(kre_df, spy_df, window=24):
        if kre_df.empty or spy_df.empty:
            return 0.0
        s1 = kre_df["Close"]
        s2 = spy_df["Close"]
        aligned = pd.concat([s1, s2], axis=1, join="inner").dropna()
        if len(aligned) < 2:
            return 0.0
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        w = min(window, len(ratio) - 1)
        roc = ((ratio.iloc[-1] - ratio.iloc[-w - 1]) / (ratio.iloc[-w - 1] + 1e-9)) * 100.0
        return float(np.clip(roc * 2.0, -1.8, 1.8))

    @staticmethod
    def compute_defensive_flight(xlu_df, benchmark_df, window=24):
        if xlu_df.empty or benchmark_df.empty:
            return 0.0
        s1 = xlu_df["Close"]
        s2 = benchmark_df["Close"]
        aligned = pd.concat([s1, s2], axis=1, join="inner").dropna()
        if len(aligned) < 2:
            return 0.0
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        w = min(window, len(ratio) - 1)
        roc = ((ratio.iloc[-1] - ratio.iloc[-w - 1]) / (ratio.iloc[-w - 1] + 1e-9)) * 100.0
        return float(np.clip(roc * 2.0, -1.8, 1.8))

    @staticmethod
    def compute_consumer_confidence(xly_df, xlp_df, window=24):
        if xly_df.empty or xlp_df.empty:
            return 0.0
        s1 = xly_df["Close"]
        s2 = xlp_df["Close"]
        aligned = pd.concat([s1, s2], axis=1, join="inner").dropna()
        if len(aligned) < 2:
            return 0.0
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        w = min(window, len(ratio) - 1)
        roc = ((ratio.iloc[-1] - ratio.iloc[-w - 1]) / (ratio.iloc[-w - 1] + 1e-9)) * 100.0
        return float(np.clip(roc * 2.0, -1.8, 1.8))

    @staticmethod
    def compute_vix_term_structure(vix_df, vix3m_df):
        if vix_df.empty:
            return 0.0
        cur_vix = float(vix_df["Close"].iloc[-1])
        if not vix3m_df.empty:
            cur_vix3m = float(vix3m_df["Close"].iloc[-1])
            ratio = cur_vix / (cur_vix3m + 1e-9)
            stress = (ratio - 1.0) * 8.0
            return float(np.clip(stress, -2.0, 2.0))
        return float(np.clip((cur_vix - 16.0) / 4.0, -1.8, 1.8))

    @staticmethod
    def compute_crypto_funding_stress(funding_rate):
        stress = float(np.clip(funding_rate * 5000.0, -2.0, 2.0))
        return stress

    @staticmethod
    def compute_gold_oil_ratio(gold_df, oil_df, window=24):
        if gold_df.empty or oil_df.empty:
            return 0.0
        s1 = gold_df["Close"]
        s2 = oil_df["Close"]
        aligned = pd.concat([s1, s2], axis=1, join="inner").dropna()
        if len(aligned) < 2:
            return 0.0
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        w = min(window, len(ratio) - 1)
        roc = ((ratio.iloc[-1] - ratio.iloc[-w - 1]) / (ratio.iloc[-w - 1] + 1e-9)) * 100.0
        return float(np.clip(roc * 1.5, -1.8, 1.8))

    @staticmethod
    def compute_silver_copper_ratio(silver_df, copper_df, window=24):
        if silver_df.empty or copper_df.empty:
            return 0.0
        s1 = silver_df["Close"]
        s2 = copper_df["Close"]
        aligned = pd.concat([s1, s2], axis=1, join="inner").dropna()
        if len(aligned) < 2:
            return 0.0
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        w = min(window, len(ratio) - 1)
        roc = ((ratio.iloc[-1] - ratio.iloc[-w - 1]) / (ratio.iloc[-w - 1] + 1e-9)) * 100.0
        return float(np.clip(roc * 1.8, -1.8, 1.8))

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
        return float(np.clip(roc_4h * 4.0, -2.0, 2.0))

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
        return float(np.clip(dev_pct * 0.3, -2.0, 2.0))

    @staticmethod
    def compute_yen_carry_shock(usdjpy_df, window=20):
        if usdjpy_df.empty or len(usdjpy_df) < 5:
            return 0.0
        close = usdjpy_df["Close"]
        w = min(window, len(close))
        mean_val = close.rolling(w).mean().iloc[-1]
        std_val = close.rolling(w).std().iloc[-1] + 1e-9
        return float(np.clip((close.iloc[-1] - mean_val) / std_val, -2.0, 2.0))

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
        return float(np.clip((ratio.iloc[-1] - mean) / std, -2.0, 2.0))

    @staticmethod
    def compute_z_score(series, window=24):
        if len(series) < 2:
            return 0.0
        w = min(window, len(series))
        return float(np.clip((series.iloc[-1] - series.rolling(w).mean().iloc[-1]) / (series.rolling(w).std().iloc[-1] + 1e-9), -2.0, 2.0))

    @staticmethod
    def detect_realtime_macro_regime(dxy_velocity, credit_velocity, real_yield_z, z_vix, stagflation_z, yen_carry_z):
        if stagflation_z > 1.0:
            return "🛢️ KÜRESEL STAGFLASYON ŞOKU (PETROL BASKISI)"
        elif (dxy_velocity > 0.8 and credit_velocity < -0.6) or (yen_carry_z < -1.2 and z_vix > 0.8):
            return "🚨 SİSTEMİK LİKİDİTE ŞOKU (NAKDE KAÇIŞ)"
        elif real_yield_z > 1.0:
            return "⚡ TAHVİL REEL GETİRİ ŞOKU (TECH BASKISI)"
        elif credit_velocity < -1.0:
            return "⚠️ KREDİ PİYASASI TEMERRÜT STRESİ"
        elif dxy_velocity < -0.4 and credit_velocity > 0.4:
            return "🟢 KÜRESEL LİKİDİTE RALLİSİ (RISK-ON)"
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

    @staticmethod
    def resolve_signal_with_hysteresis(current_score, previous_signal="NÖTR (BEKLE)", bull_clusters=0, bear_clusters=0, min_clusters=2):
        t = SIGNAL_THRESHOLDS
        prev = previous_signal if previous_signal else "NÖTR (BEKLE)"

        # 1. GÜÇLÜ AL KONTROLÜ
        if prev == "GÜÇLÜ AL":
            if current_score >= t.get("strong_buy_exit", 1.0):
                return "GÜÇLÜ AL", "green", "🟢🟢"
        else:
            if current_score >= t.get("strong_buy_enter", 1.6) and bull_clusters >= min_clusters:
                return "GÜÇLÜ AL", "green", "🟢🟢"

        # 2. AL KONTROLÜ
        if prev in ["AL", "GÜÇLÜ AL"]:
            if current_score >= t.get("buy_exit", 0.20):
                return "AL", "lightgreen", "🟢"
        else:
            if current_score >= t.get("buy_enter", 0.60):
                return "AL", "lightgreen", "🟢"
            # Küme mutlak çoğunluğu (>=3) ve pozitif ivme varsa AL teyidi
            if bull_clusters >= 3 and current_score >= 0.50:
                return "AL", "lightgreen", "🟢"

        # 3. GÜÇLÜ SAT KONTROLÜ
        if prev == "GÜÇLÜ SAT":
            if current_score <= t.get("strong_sell_exit", -1.0):
                return "GÜÇLÜ SAT", "darkred", "🔴🔴"
        else:
            if current_score <= t.get("strong_sell_enter", -1.6) and bear_clusters >= min_clusters:
                return "GÜÇLÜ SAT", "darkred", "🔴🔴"

        # 4. SAT KONTROLÜ
        if prev in ["SAT", "GÜÇLÜ SAT"]:
            if current_score <= t.get("sell_exit", -0.20):
                return "SAT", "red", "🔴"
        else:
            if current_score <= t.get("sell_enter", -0.60):
                return "SAT", "red", "🔴"
            # Küme mutlak çoğunluğu (>=3) ve negatif ivme varsa SAT teyidi
            if bear_clusters >= 3 and current_score <= -0.50:
                return "SAT", "red", "🔴"

        return "NÖTR (BEKLE)", "gray", "⚪"
