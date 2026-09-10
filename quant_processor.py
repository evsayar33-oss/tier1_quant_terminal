"""
Robust Quant Processor: Real-Time ETF Metrics, 3-Pillar USD Risk & Barra Normalization (v27)
Enhanced with:
- Unified 3-Pillar USD Risk Architecture (Spot DXY, Net Dollar Liquidity NDL, USD/JPY FX Carry)
- Idiosyncratic Asset-Specific Risk Models (Duration Drag, Mega-Cap Dispersion, Sovereign Decoupling, Squeeze Risk)
- Dynamic Regime Adaptation and Hysteresis Deadband Engine
"""
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple

from config import (
    CRISIS_CONFIG, SIGNAL_THRESHOLDS, ASSET_CLOCKS,
    REGIME_DYNAMIC_THRESHOLDS
)
CATALYST_WINDOWS_UTC = []


class RobustQuantProcessor:
    @staticmethod
    def compute_realtime_price_action(df_1h, fast_window=4):
        """
        📍 Canlı / Şu Anki Fiyat Yönü (Real-Time Price Action):
        Kullanıcının grafikte anlık gördüğü fiyat hareketini ve son 4 saatlik
        yüzdesel değişimini objektif olarak ölçer.
        """
        if df_1h.empty or len(df_1h) < 2:
            return "⚪ YATAY (%0.00)", "⚪", "gray", 0.0
        close = df_1h["Close"]
        w = min(fast_window, len(close) - 1)
        roc_4h = ((close.iloc[-1] - close.iloc[-w - 1]) / (close.iloc[-w - 1] + 1e-9)) * 100.0
        roc_val = round(float(roc_4h), 2)

        if roc_val >= 0.35:
            return f"🟢 YUKARI (%{roc_val:+.2f})", "🟢", "lightgreen", roc_val
        elif roc_val <= -0.35:
            return f"🔴 AŞAĞI (%{roc_val:+.2f})", "🔴", "red", roc_val
        else:
            return f"⚪ YATAY / NÖTR (%{roc_val:+.2f})", "⚪", "gray", roc_val

    @staticmethod
    def compute_adx(df_1h, period=14):
        """
        Average Directional Index (ADX) Trend Güç Göstergesi:
        ADX < 20: Yatay / Testere Piyasası (Trend Yok)
        20 <= ADX < 25: Zayıf / Gelişen Trend
        ADX >= 25: Güçlü / Kararlı Trend
        """
        if df_1h.empty or len(df_1h) < (period * 2):
            return 25.0, "BELİRSİZ"

        df = df_1h.copy()
        high = df["High"]
        low = df["Low"]
        close = df["Close"]

        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        up_move = high - high.shift(1)
        down_move = low.shift(1) - low

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

        atr = tr.rolling(period).mean()
        plus_di = 100.0 * (pd.Series(plus_dm, index=df.index).rolling(period).mean() / (atr + 1e-9))
        minus_di = 100.0 * (pd.Series(minus_dm, index=df.index).rolling(period).mean() / (atr + 1e-9))

        dx = 100.0 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-9))
        adx_series = dx.rolling(period).mean()

        last_adx = adx_series.iloc[-1]
        adx_val = round(float(last_adx), 1) if not np.isnan(last_adx) else 25.0

        if adx_val < 20.0:
            regime = "YATAY / TESTERE"
        elif adx_val < 25.0:
            regime = "GELİŞEN TREND"
        else:
            regime = "GÜÇLÜ TREND"

        return adx_val, regime

    @staticmethod
    def get_asset_session_status(asset_key):
        clocks = {
            "SPX": {"open_utc": 13.5, "close_utc": 20.0, "crypto": False},
            "NQ":  {"open_utc": 13.5, "close_utc": 20.0, "crypto": False},
            "XAU": {"open_utc": 0.0,  "close_utc": 24.0, "crypto": True},
            "XAG": {"open_utc": 0.0,  "close_utc": 24.0, "crypto": True},
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
            return "HAFTA SONU (KAPALI)", 1.0

        open_h = clock.get("open_utc", 13.5)
        close_h = clock.get("close_utc", 20.0)

        if open_h <= current_hour <= close_h:
            return "CANLI SEANS", 1.0
        elif (open_h - 4.0) <= current_hour < open_h:
            return "SEANS ÖNCESİ (PRE-MARKET)", 1.0
        else:
            return "KAPALI (SEANS DIŞI)", 1.0

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

    # =========================================================================
    # 💵 3-PILLAR USD RISK VE KÜRESEL LİKİDİTE HESAPLAMALARI
    # =========================================================================
    @staticmethod
    def compute_composite_usd_risk(dxy_velocity, ndl_z, usdjpy_1d_z):
        """
        Bileşik 3-Pillar USD Risk Endeksi [-2.0, +2.0]:
        1. DXY Kısa Vade İvmesi (Spot momentum)
        2. Fed Net Dolar Likiditesi (NDL Z-skoru - Ters yönlü etki)
        3. USD/JPY Carry Yayılımı (Carry çöküşünde küresel USD tasfiyesi)
        """
        dxy_term = float(np.clip(dxy_velocity * 0.45, -1.0, 1.0))
        ndl_term = float(np.clip(-ndl_z * 0.35, -1.0, 1.0))
        carry_term = float(np.clip(-usdjpy_1d_z * 0.20, -0.8, 0.8))

        composite_score = float(np.clip(dxy_term + ndl_term + carry_term, -2.0, 2.0))

        if composite_score > 0.50:
            label = "🔴 YÜKSEK DOLAR SIKIŞMASI (Likidite Daralması)"
            status = "STRESS"
        elif composite_score < -0.50:
            label = "🟢 DÜŞÜK USD BASKISI (Küresel Likidite Bol)"
            status = "EXPANSION"
        else:
            label = "🟡 NÖTR / DENGELİ USD İKLİMİ"
            status = "NEUTRAL"

        return composite_score, label, status

    @staticmethod
    def compute_usd_strength_impulse(dxy_df_1h, window=4):
        if dxy_df_1h.empty or len(dxy_df_1h) < 2:
            return 0.0
        close = dxy_df_1h["Close"]
        w = min(window, len(close) - 1)
        roc_4h = ((close.iloc[-1] - close.iloc[-w - 1]) / (close.iloc[-w - 1] + 1e-9)) * 100.0
        return float(np.clip(roc_4h * 3.5, -2.0, 2.0))

    # =========================================================================
    # 🎯 VARLIĞA ÖZEL İDİOSİNKRATİK RİSK MODELLERİ
    # =========================================================================
    @staticmethod
    def compute_equity_duration_drag(df_asset, real_yield_z):
        """
        Hisse Senedi Değerleme & Süre Baskısı (Equity Duration Drag):
        TIPS 10Y Reel Getiri arttığında hisse çarpanlarında (F/K) sıkışma riskini ölçer.
        """
        if real_yield_z > 0.30:
            drag = (real_yield_z - 0.30) * 1.2
            return float(np.clip(drag, 0.0, 2.0))
        elif real_yield_z < -0.30:
            boost = (real_yield_z + 0.30) * 0.9
            return float(np.clip(boost, -2.0, 0.0))
        return 0.0

    @staticmethod
    def compute_tech_breadth_dispersion(smh_df, arkk_df, qqq_df, window=24):
        """
        Teknoloji Katılım & Çip İvmesi Ayrışması:
        SMH (Çip) ve ARKK (Yüksek Beta) öncülüğünü QQQ ile kıyaslar.
        """
        if smh_df.empty or qqq_df.empty:
            return 0.0
        s_smh = smh_df["Close"]
        s_qqq = qqq_df["Close"]
        aligned = pd.concat([s_smh, s_qqq], axis=1, join="inner").dropna()
        if len(aligned) < 2:
            return 0.0
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        w = min(window, len(ratio) - 1)
        roc = ((ratio.iloc[-1] - ratio.iloc[-w - 1]) / (ratio.iloc[-w - 1] + 1e-9)) * 100.0
        return float(np.clip(roc * 2.2, -1.8, 1.8))

    @staticmethod
    def compute_gold_sovereign_decoupling(gold_df, real_yield_z, dxy_df, window=24):
        """
        Altın Merkez Bankası & Jeopolitik Rezerv Talebi (Sovereign Decoupling):
        Altının klasik finans kurallarını aşarak reel faiz veya DXY artarken bile
        güçlü kalmasını ölçer (De-dolarizasyon ve egemen rezerv birikimi).
        """
        if gold_df.empty or len(gold_df) < 2:
            return 0.0
        close = gold_df["Close"]
        w = min(window, len(close) - 1)
        gold_roc = ((close.iloc[-1] - close.iloc[-w - 1]) / (close.iloc[-w - 1] + 1e-9)) * 100.0

        # Eğer reel getiri pozitifken altın yükseliyorsa egemen rezerv talebi çok güçlüdür
        if real_yield_z > 0.40 and gold_roc > 0.0:
            sovereign_bonus = (gold_roc * 1.5) + (real_yield_z * 0.8)
            return float(np.clip(sovereign_bonus, 0.2, 2.0))
        elif real_yield_z < -0.40 and gold_roc > 0.0:
            return float(np.clip(gold_roc * 1.2, -2.0, 2.0))
        else:
            return float(np.clip(gold_roc * 1.1 - (real_yield_z * 0.5), -2.0, 2.0))

    @staticmethod
    def compute_silver_monetary_catchup(silver_df, gold_df, copper_df, window=24):
        """
        Gümüş Parasal Yakalama & Değerleme İvmesi:
        Gümüşün hem parasal altın rallisine hem de bakır sanayi talebine göre
        göreceli iskonto/prim hızını hesaplar.
        """
        if silver_df.empty or gold_df.empty:
            return 0.0
        s_ag = silver_df["Close"]
        s_au = gold_df["Close"]
        aligned = pd.concat([s_ag, s_au], axis=1, join="inner").dropna()
        if len(aligned) < 2:
            return 0.0
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        w = min(window, len(ratio) - 1)
        roc = ((ratio.iloc[-1] - ratio.iloc[-w - 1]) / (ratio.iloc[-w - 1] + 1e-9)) * 100.0
        return float(np.clip(roc * 2.0, -1.8, 1.8))

    @staticmethod
    def compute_crypto_stablecoin_usd_impulse(flow_ratio, funding_rate, ndl_z):
        """
        Kripto-Yerel USD Likiditesi & Taker İştahı:
        Spot taker hacmi, türev fonlama primi ve Fed net dolar likiditesini sentezler.
        """
        taker_term = np.tanh(np.log(flow_ratio + 1e-6) * 2.0) * 1.3
        ndl_term = np.clip(ndl_z * 0.4, -0.6, 0.6)
        fr_term = np.clip((funding_rate - 0.0001) * 1500.0, -0.5, 0.5)
        blended = taker_term + ndl_term + fr_term
        return float(np.clip(blended, -2.0, 2.0))

    @staticmethod
    def compute_liquidation_squeeze_risk(funding_rate, df_crypto, window=24):
        """
        Türev Kaldıraç & Likidasyon Sıkışması Riski:
        Aşırı pozitif fonlama (>%0.04) long tasfiye riski yaratır.
        Aşırı negatif fonlama (<-%0.02) short squeeze yakıtı üretir.
        """
        excess_funding = funding_rate - 0.0001
        stress = excess_funding * 6000.0
        return float(np.clip(stress, -2.0, 2.0))

    @staticmethod
    def compute_eth_staking_utility_drift(eth_df, btc_df, window=24):
        """
        ETH/BTC Ağ Aktivitesi & Göreceli Değer İvmesi:
        """
        if eth_df.empty or btc_df.empty:
            return 0.0
        s_eth = eth_df["Close"]
        s_btc = btc_df["Close"]
        aligned = pd.concat([s_eth, s_btc], axis=1, join="inner").dropna()
        if len(aligned) < 2:
            return 0.0
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        w = min(window, len(ratio) - 1)
        roc = ((ratio.iloc[-1] - ratio.iloc[-w - 1]) / (ratio.iloc[-w - 1] + 1e-9)) * 100.0
        return float(np.clip(roc * 2.5, -1.8, 1.8))

    # =========================================================================
    # 📈 STANDART FAKTÖR VE PİYASA BİLEŞENLERİ
    # =========================================================================
    @staticmethod
    def compute_intraday_direction_momentum(df_1h, fast_window=4, slow_window=24, vol_scale=1.0):
        if df_1h.empty or len(df_1h) < 2:
            return 0.0
        close = df_1h["Close"]
        w_fast = min(fast_window, len(close) - 1)
        roc_4h = ((close.iloc[-1] - close.iloc[-w_fast - 1]) / (close.iloc[-w_fast - 1] + 1e-9)) * 100.0
        w_slow = min(slow_window, len(close) - 1)
        roc_24h = ((close.iloc[-1] - close.iloc[-w_slow - 1]) / (close.iloc[-w_slow - 1] + 1e-9)) * 100.0

        blended = (roc_4h * 1.5) + (roc_24h * 0.5)
        scale = max(float(vol_scale), 0.5)
        norm_blended = (blended / scale) * 1.3
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
        return float(np.clip(roc * 2.0, -1.8, 1.8))

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
    def compute_vix_stress(vix_df, window=48):
        if vix_df.empty:
            return 0.0
        close = vix_df["Close"]
        cur_vix = float(close.iloc[-1])
        abs_stress = (cur_vix - 17.5) / 5.0
        w = min(window, len(close))
        mean_val = close.rolling(w).mean().iloc[-1]
        std_val = close.rolling(w).std().iloc[-1] + 1e-9
        rel_z = (cur_vix - mean_val) / std_val
        blended = (abs_stress * 0.6) + (rel_z * 0.4)
        return float(np.clip(blended, -2.0, 2.0))

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
        return float(np.clip((cur_vix - 17.5) / 4.0, -1.8, 1.8))

    @staticmethod
    def compute_crypto_funding_stress(funding_rate):
        excess_rate = funding_rate - 0.0001
        stress = float(np.clip(excess_rate * 5000.0, -2.0, 2.0))
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
    def compute_stagflation_shock(oil_df, transport_df, window=48):
        if oil_df.empty or transport_df.empty:
            return 0.0
        p_oil = float(oil_df["Close"].iloc[-1])
        p_iyt = float(transport_df["Close"].iloc[-1])
        w = min(window, len(oil_df), len(transport_df))
        mean_oil = oil_df["Close"].tail(w).mean()
        mean_iyt = transport_df["Close"].tail(w).mean()
        current_ratio = p_oil / (p_iyt + 1e-9)
        baseline_ratio = mean_oil / (mean_iyt + 1e-9)
        dev_pct = ((current_ratio - baseline_ratio) / (baseline_ratio + 1e-9)) * 100.0
        return float(np.clip(dev_pct * 0.12, -2.0, 2.0))

    @staticmethod
    def compute_yen_carry_shock(usdjpy_df, window=24):
        if usdjpy_df.empty or len(usdjpy_df) < 5:
            return 0.0
        close = usdjpy_df["Close"]
        w = min(window, len(close))
        mean_val = close.rolling(w).mean().iloc[-1]
        std_val = close.rolling(w).std().iloc[-1] + 1e-9
        return float(np.clip((close.iloc[-1] - mean_val) / std_val, -2.0, 2.0))

    @staticmethod
    def compute_ratio_z(df_num, df_denom, window=48):
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
    def compute_z_score(series, window=48):
        if len(series) < 2:
            return 0.0
        w = min(window, len(series))
        return float(np.clip((series.iloc[-1] - series.rolling(w).mean().iloc[-1]) / (series.rolling(w).std().iloc[-1] + 1e-9), -2.0, 2.0))

    @staticmethod
    def detect_realtime_macro_regime(dxy_velocity, credit_velocity, real_yield_z, z_vix, stagflation_z, yen_carry_z):
        if stagflation_z > 1.35:
            return "🛢️ [REJİM 1] Küresel Enflasyon & Stagflasyon Şoku"
        elif (dxy_velocity > 0.8 and credit_velocity < -0.6) or (yen_carry_z < -1.2 and z_vix > 0.8):
            return "🚨 [REJİM 2] Sistemik Likidite Şoku & Carry Çöküşü"
        elif real_yield_z > 1.2:
            return "⚡ [REJİM 3] Reel Faiz Şoku"
        elif credit_velocity < -1.0:
            return "⚠️ [REJİM 4] Kredi Temerrüt Baskısı"
        elif dxy_velocity < -0.4 and credit_velocity > 0.4:
            return "🟢 [REJİM 5] Küresel Likidite Rallisi (Risk-On)"
        return "⚪ REJIMSIZ_GECIS (Makro Denge / Sıkışma)"

    @staticmethod
    def evaluate_crisis_lock_with_hysteresis(credit_velocity, z_vix, z_real_rate, dxy_velocity, current_vix_val, current_state=False, consecutive_breaches=0):
        cfg = CRISIS_CONFIG
        credit_stress = max(-credit_velocity, 0.0)
        vix_stress = max(z_vix, 0.0) if current_vix_val >= cfg.get("vix_absolute_floor", 20.0) else 0.0
        dxy_stress = max(dxy_velocity, 0.0)
        rate_stress = max(z_real_rate, 0.0)

        anomaly_score = float(np.linalg.norm([credit_stress, vix_stress, rate_stress, dxy_stress]) / 1.7)
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
    def resolve_signal_with_hysteresis(
        current_score,
        previous_signal="NÖTR (BEKLE)",
        bull_clusters=0,
        bear_clusters=0,
        min_clusters=2,
        market_regime="TREND",
        adx_val=25.0,
        dynamic_thresholds=None,
        active_regime_id=None
    ):
        """
        Dinamik Rejime Duyarlı Sinyal Çözümleyici:
        Aktif makro rejime (1..5 veya REJIMSIZ_GECIS) göre kalibre edilmiş dinamik eşikleri uygular.
        """
        t = SIGNAL_THRESHOLDS
        prev = previous_signal if previous_signal else "NÖTR (BEKLE)"

        # 🧠 DİNAMİK REJİM KALİBRASYON ENTEGRASYONU
        dyn = dynamic_thresholds
        if dyn is None and active_regime_id is not None:
            dyn = REGIME_DYNAMIC_THRESHOLDS.get(active_regime_id)
        elif dyn is None and market_regime:
            for r_id in [1, 2, 3, 4, 5, "REJIMSIZ_GECIS"]:
                if f"REJİM {r_id}" in market_regime or f"REJİM_{r_id}" in market_regime:
                    dyn = REGIME_DYNAMIC_THRESHOLDS.get(r_id)
                    break

        is_choppy = ("DENGE" in market_regime or "SIKIŞMA" in market_regime or "REJIMSIZ_GECIS" in market_regime) or (adx_val < 20.0)

        if dyn is not None:
            buy_enter = dyn.get("buy_enter", 0.60)
            sell_enter = dyn.get("sell_enter", -0.60)
            buy_exit = dyn.get("buy_exit", 0.30)
            sell_exit = dyn.get("sell_exit", -0.30)
            strong_buy_enter = dyn.get("strong_buy_enter", 1.60)
            strong_sell_enter = dyn.get("strong_sell_enter", -1.60)
            req_clusters = max(min_clusters, dyn.get("min_clusters", 2))
        elif is_choppy:
            buy_enter = 0.85
            sell_enter = -0.85
            req_clusters = max(min_clusters, 3)
            buy_exit = 0.35
            sell_exit = -0.35
            strong_buy_enter = 1.70
            strong_sell_enter = -1.70
        else:
            buy_enter = t.get("buy_enter", 0.60)
            sell_enter = t.get("sell_enter", -0.60)
            req_clusters = min_clusters
            buy_exit = t.get("buy_exit", 0.30)
            sell_exit = t.get("sell_exit", -0.30)
            strong_buy_enter = t.get("strong_buy_enter", 1.60)
            strong_sell_enter = t.get("strong_sell_enter", -1.60)

        # 1. GÜÇLÜ AL KONTROLÜ
        if prev == "GÜÇLÜ AL":
            if current_score > max(buy_exit, 0.50):
                return "GÜÇLÜ AL", "green", "🟢🟢"
        else:
            if current_score >= strong_buy_enter and bull_clusters >= req_clusters:
                return "GÜÇLÜ AL", "green", "🟢🟢"

        # 2. AL KONTROLÜ
        if prev in ["AL", "GÜÇLÜ AL"]:
            if current_score > buy_exit:
                return "AL", "lightgreen", "🟢"
        else:
            if current_score >= buy_enter and bull_clusters >= req_clusters:
                return "AL", "lightgreen", "🟢"
            if not is_choppy and bull_clusters >= 3 and current_score >= max(buy_enter - 0.10, 0.40):
                return "AL", "lightgreen", "🟢"

        # 3. GÜÇLÜ SAT KONTROLÜ
        if prev == "GÜÇLÜ SAT":
            if current_score < min(sell_exit, -0.50):
                return "GÜÇLÜ SAT", "darkred", "🔴🔴"
        else:
            if current_score <= strong_sell_enter and bear_clusters >= req_clusters:
                return "GÜÇLÜ SAT", "darkred", "🔴🔴"

        # 4. SAT KONTROLÜ
        if prev in ["SAT", "GÜÇLÜ SAT"]:
            if current_score < sell_exit:
                return "SAT", "red", "🔴"
        else:
            if current_score <= sell_enter and bear_clusters >= req_clusters:
                return "SAT", "red", "🔴"
            if not is_choppy and bear_clusters >= 3 and current_score <= min(sell_enter + 0.10, -0.40):
                return "SAT", "red", "🔴"

        neutral_label = "NÖTR (TESTERE BANDI)" if (is_choppy and abs(current_score) > 0.40) else "NÖTR (BEKLE)"
        return neutral_label, "gray", "⚪"
