"""
Robust Quant Processor: Institutional Barra Engine & Gamma Microstructure (v34)
Enhanced with:
- Noise-Filtered Robust Divergence Engine (Median Absolute Deviation - MAD)
- Dynamic Pre-Market / Globex Active Price Action (Fixes the 16:30 TSI Sideways Bug)
- Full Volatility & Volume Gatekeeper (Trade Entry Suitability Engine)
- Strict Institutional 'GÜÇLÜ AL' / 'GÜÇLÜ SAT' Multi-Factor Confirmation Gate
"""
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple

from config import (
    CRISIS_CONFIG, SIGNAL_THRESHOLDS, ASSET_CLOCKS,
    REGIME_DYNAMIC_THRESHOLDS, ENTRY_FILTER_CONFIG
)
CATALYST_WINDOWS_UTC = []


class RobustQuantProcessor:
    @staticmethod
    def _safe_align_series(s1: pd.Series, s2: pd.Series) -> pd.DataFrame:
        if s1 is None or s2 is None or len(s1) == 0 or len(s2) == 0:
            return pd.DataFrame()

        idx1 = s1.index.tz_localize(None) if getattr(s1.index, "tz", None) is not None else s1.index
        idx2 = s2.index.tz_localize(None) if getattr(s2.index, "tz", None) is not None else s2.index

        s1_clean = pd.Series(s1.values, index=idx1, name="s1").sort_index()
        s2_clean = pd.Series(s2.values, index=idx2, name="s2").sort_index()

        s1_clean = s1_clean[~s1_clean.index.duplicated(keep="last")]
        s2_clean = s2_clean[~s2_clean.index.duplicated(keep="last")]

        df_aligned = pd.concat([s1_clean, s2_clean], axis=1, join="outer").sort_index()
        df_aligned = df_aligned.ffill().bfill().dropna()
        return df_aligned

    @staticmethod
    def _get_cash_session_liquidity_multiplier() -> float:
        """
        Vadeli kontratlar ve küresel makro veriler için seans ölçekleyicisi.
        """
        now = datetime.now(timezone.utc)
        if now.weekday() in [5, 6]:
            return 0.70
        return 1.0

    @staticmethod
    def compute_realtime_price_action(df_1h, fast_window=4, vol_scale=1.0, asset_key=None):
        """
        📍 Stabilize Edilmiş & Seans Duyarlı Fiyat Hareketi Motoru:
        - 16:30 TSİ öncesi vadeli barlarındaki gerçek hareketi algılar.
        - Tek barlık rastgele iğneleri eler, seans momentumunu yansıtır.
        """
        if df_1h is None or df_1h.empty or len(df_1h) < 2:
            return "⚪ YATAY (%0.00)", "⚪", "gray", 0.0

        close = df_1h["Close"]
        c = float(close.iloc[-1])

        # 1. 4 Saatlik Seans Getirisi (Oturaklı Gövde)
        w = min(fast_window, len(df_1h) - 1)
        roc_window = ((c - close.iloc[-w - 1]) / (close.iloc[-w - 1] + 1e-9)) * 100.0
        display_roc = round(float(roc_window), 2)

        # 2. Canlı Bar Sapması (İç Gürültü Filtreli)
        last_bar = df_1h.iloc[-1]
        o = float(last_bar["Open"]) if "Open" in df_1h.columns else float(close.iloc[-2])
        instant_drift = ((c - o) / (o + 1e-9)) * 100.0

        # 3. Bar İçi Kapanış Konumu (CLV)
        h = float(last_bar["High"]) if "High" in df_1h.columns else max(c, o)
        l = float(last_bar["Low"]) if "Low" in df_1h.columns else min(c, o)
        bar_range = max(h - l, 1e-9)
        clv = ((c - l) - (h - c)) / bar_range

        # 4. Hacim Ağırlığı
        vol_weight = 1.0
        if "Volume" in df_1h.columns and len(df_1h) >= 12:
            avg_vol = df_1h["Volume"].tail(12).mean()
            if avg_vol > 0:
                cur_vol = float(last_bar["Volume"])
                vol_weight = float(np.clip(cur_vol / avg_vol, 0.7, 1.5))

        eff_scale = max(float(vol_scale), 0.5)
        noise_threshold = 0.25 * eff_scale

        blended_momentum = (roc_window * 0.75) + (instant_drift * 0.20)
        micro_score = ((blended_momentum * vol_weight) / noise_threshold) + (clv * 0.05)

        if display_roc > 0:
            if micro_score >= 1.0:
                return f"🟢 GÜÇLÜ YUKARI (%{display_roc:+.2f})", "🟢🟢", "green", display_roc
            elif micro_score >= 0.40 or display_roc >= (0.25 * eff_scale):
                return f"🟢 YUKARI (%{display_roc:+.2f})", "🟢", "lightgreen", display_roc
            elif display_roc >= 0.10:
                return f"⚪ YATAY / OLASI YÜKSELİŞ (%{display_roc:+.2f})", "⚪", "gray", display_roc
            else:
                return f"⚪ YATAY / TESTERE (%{display_roc:+.2f})", "⚪", "gray", display_roc

        elif display_roc < 0:
            if micro_score <= -1.0:
                return f"🔴 GÜÇLÜ AŞAĞI (%{display_roc:+.2f})", "🔴🔴", "darkred", display_roc
            elif micro_score <= -0.40 or display_roc <= -(0.25 * eff_scale):
                return f"🔴 AŞAĞI (%{display_roc:+.2f})", "🔴", "red", display_roc
            elif display_roc <= -0.10:
                return f"⚪ YATAY / OLASI DÜŞÜŞ (%{display_roc:+.2f})", "⚪", "gray", display_roc
            else:
                return f"⚪ YATAY / TESTERE (%{display_roc:+.2f})", "⚪", "gray", display_roc

        else:
            return "⚪ YATAY (%0.00)", "⚪", "gray", 0.0

    # =========================================================================
    # 🛡️ GİRİŞ ANALİZİ MOTORU (VOLATİLİTE & HACİM ŞOK KAPISI)
    # =========================================================================
    @staticmethod
    def compute_asset_volatility_metrics(df_1h, period=14) -> Tuple[float, bool, str]:
        """
        Varlığın anlık ATR oranını ve şok durumunu hesaplar.
        """
        if df_1h is None or df_1h.empty or len(df_1h) < (period + 10):
            return 1.0, True, "Normal Volatilite"

        high = df_1h["High"] if "High" in df_1h.columns else df_1h["Close"]
        low = df_1h["Low"] if "Low" in df_1h.columns else df_1h["Close"]
        close = df_1h["Close"]

        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr_14 = tr.rolling(period).mean()
        atr_sma = atr_14.rolling(20).mean()

        last_atr = float(atr_14.iloc[-1])
        last_sma = float(atr_sma.iloc[-1]) if not np.isnan(atr_sma.iloc[-1]) and atr_sma.iloc[-1] > 0 else last_atr
        atr_ratio = float(np.clip(last_atr / (last_sma + 1e-9), 0.1, 5.0))

        cfg = ENTRY_FILTER_CONFIG
        if atr_ratio > cfg["vol_shock_high"]:
            return atr_ratio, False, f"Volatilite Şoku (ATR Oranı: {atr_ratio:.2f} > {cfg['vol_shock_high']}) - Yüksek Slippage Riski!"
        elif atr_ratio < cfg["vol_shock_low"]:
            return atr_ratio, False, f"Volatilite Yetersiz (ATR Oranı: {atr_ratio:.2f} < {cfg['vol_shock_low']}) - Sıkışma & Sahte Kırılım Tuzağı!"
        else:
            return atr_ratio, True, f"Volatilite Uygun ({atr_ratio:.2f})"

    @staticmethod
    def compute_asset_volume_metrics(df_1h, window=20) -> Tuple[float, bool, str]:
        """
        Göreceli Seans Hacmini (RVOL) hesaplar ve şok/likidite durumunu denetler.
        """
        if df_1h is None or df_1h.empty or "Volume" not in df_1h.columns or len(df_1h) < (window + 2):
            return 1.0, True, "Normal Hacim"

        vol = df_1h["Volume"]
        cur_vol = float(vol.iloc[-1])
        avg_vol = float(vol.tail(window).mean())

        rvol = float(np.clip(cur_vol / (avg_vol + 1e-9), 0.1, 10.0))
        cfg = ENTRY_FILTER_CONFIG

        if rvol > cfg["rvol_climax_shock"]:
            return rvol, False, f"Hacim Şoku / Climax Tükenişi (RVOL: {rvol:.2f} > {cfg['rvol_climax_shock']}) - Tükeniş Riski!"
        elif rvol < cfg["rvol_illiquid"]:
            return rvol, False, f"Yetersiz Hacim / Likidite Boşluğu (RVOL: {rvol:.2f} < {cfg['rvol_illiquid']}) - Kurumsal İlgi Yok!"
        else:
            return rvol, True, f"Hacim Uygun ({rvol:.2f})"

    @staticmethod
    def evaluate_entry_analysis(df_1h, asset_key="SPX") -> Dict[str, Any]:
        """
        Yönden bağımsız olarak piyasanın işleme giriş güvenliğini test eder.
        """
        atr_ratio, vol_ok, vol_msg = RobustQuantProcessor.compute_asset_volatility_metrics(df_1h)
        rvol, volume_ok, volume_msg = RobustQuantProcessor.compute_asset_volume_metrics(df_1h)

        entry_allowed = vol_ok and volume_ok
        if entry_allowed:
            verdict = "İşleme Giriş Önerilir"
            reason = f"Volatilite ({atr_ratio:.2f}) ve Hacim ({rvol:.2f}) dengeli ve kurumsal akışa uygun."
            color = "lightgreen"
            icon = "✅"
        else:
            verdict = "İşleme Giriş Önerilmez"
            failed_reasons = []
            if not vol_ok: failed_reasons.append(vol_msg)
            if not volume_ok: failed_reasons.append(volume_msg)
            reason = " | ".join(failed_reasons)
            color = "red"
            icon = "🚫"

        return {
            "verdict": verdict,
            "entry_allowed": entry_allowed,
            "reason": reason,
            "color": color,
            "icon": icon,
            "atr_ratio": round(atr_ratio, 2),
            "rvol": round(rvol, 2),
            "vol_supported": (ENTRY_FILTER_CONFIG["vol_healthy_min"] <= atr_ratio <= ENTRY_FILTER_CONFIG["vol_healthy_max"]),
            "volume_supported": (rvol >= ENTRY_FILTER_CONFIG["rvol_strong_min"])
        }

    # =========================================================================
    # 🎯 ROBUST AYRIŞMA HESAPLAYICI (MAD FİLTRELİ - ABARTMAYI ÖNLER)
    # =========================================================================
    @staticmethod
    def _compute_robust_divergence_z(series1: pd.Series, series2: pd.Series, window=24) -> float:
        """
        İki seri arasındaki ayrışmayı klasik ROC patlaması yerine
        Median Absolute Deviation (MAD) ile hesaplar. Anlık iğneleri filtreler.
        """
        aligned = RobustQuantProcessor._safe_align_series(series1, series2)
        if len(aligned) < 4:
            return 0.0

        # Rasyoyu yumuşat (3 barlık EMA)
        ratio = (aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)).ewm(span=3, adjust=False).mean()
        w = min(window, len(ratio) - 1)
        if w < 3:
            return 0.0

        # Robust Z-Score: Median ve MAD
        recent_window = ratio.tail(w)
        median_val = float(recent_window.median())
        mad_val = float((recent_window - median_val).abs().median())
        mad_val = 1e-6 if mad_val == 0 else mad_val

        # 1.4826 normal dağılım tutarlılık ölçeğidir
        robust_z = (ratio.iloc[-1] - median_val) / (1.4826 * mad_val)
        return float(np.clip(robust_z * 0.75, -1.8, 1.8))

    @staticmethod
    def compute_adx(df_1h, period=14):
        if df_1h is None or df_1h.empty or len(df_1h) < (period * 2):
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
        """
        SPX ve NQ vadeli seansına göre ayarlandı (23 saat canlı).
        """
        clocks = ASSET_CLOCKS.get(asset_key, {})
        c_type = clocks.get("type", "FUTURES_23H")
        if c_type == "CRYPTO_24_7":
            return "CANLI (24/7)", 1.0

        now = datetime.now(timezone.utc)
        current_day = now.weekday()
        if current_day in [5, 6]:
            return "HAFTA SONU (KAPALI)", 1.0

        # Globex vadeli seansı
        return "CANLI (VADELİ/GLOBEX)", 1.0

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

    @staticmethod
    def compute_equity_duration_drag(df_asset, real_yield_z):
        z_val = float(real_yield_z) if real_yield_z is not None else 0.0
        drag = z_val * 0.85
        return float(np.clip(drag, -2.0, 2.0))

    @staticmethod
    def compute_tech_breadth_dispersion(smh_df, arkk_df, qqq_df, window=24):
        if smh_df.empty or qqq_df.empty:
            return 0.0
        s_smh = smh_df["Close"] if "Close" in smh_df.columns else smh_df.iloc[:, 0]
        s_qqq = qqq_df["Close"] if "Close" in qqq_df.columns else qqq_df.iloc[:, 0]
        return RobustQuantProcessor._compute_robust_divergence_z(s_smh, s_qqq, window=window)

    @staticmethod
    def compute_gold_sovereign_decoupling(gold_df, real_yield_z, dxy_df, window=24):
        if gold_df.empty or len(gold_df) < 2:
            return 0.0
        close = gold_df["Close"]
        w = min(window, len(close) - 1)
        gold_roc = ((close.iloc[-1] - close.iloc[-w - 1]) / (close.iloc[-w - 1] + 1e-9)) * 100.0

        if real_yield_z > 0.40 and gold_roc > 0.0:
            sovereign_bonus = (gold_roc * 1.5) + (real_yield_z * 0.8)
            return float(np.clip(sovereign_bonus, 0.2, 2.0))
        elif real_yield_z < -0.40 and gold_roc > 0.0:
            return float(np.clip(gold_roc * 1.2, -2.0, 2.0))
        else:
            return float(np.clip(gold_roc * 1.1 - (real_yield_z * 0.5), -2.0, 2.0))

    @staticmethod
    def compute_silver_monetary_catchup(silver_df, gold_df, copper_df, window=24):
        if silver_df.empty or gold_df.empty:
            return 0.0
        s_ag = silver_df["Close"] if "Close" in silver_df.columns else silver_df.iloc[:, 0]
        s_au = gold_df["Close"] if "Close" in gold_df.columns else gold_df.iloc[:, 0]
        return RobustQuantProcessor._compute_robust_divergence_z(s_ag, s_au, window=window)

    @staticmethod
    def compute_crypto_stablecoin_usd_impulse(flow_ratio, funding_rate, ndl_z):
        taker_term = np.tanh(np.log(flow_ratio + 1e-6) * 2.0) * 1.3
        ndl_term = np.clip(ndl_z * 0.4, -0.6, 0.6)
        fr_term = np.clip((funding_rate - 0.0001) * 1500.0, -0.5, 0.5)
        blended = taker_term + ndl_term + fr_term
        return float(np.clip(blended, -2.0, 2.0))

    @staticmethod
    def compute_liquidation_squeeze_risk(funding_rate, df_crypto, window=24):
        excess_funding = funding_rate - 0.0001
        stress = excess_funding * 6000.0
        return float(np.clip(stress, -2.0, 2.0))

    @staticmethod
    def compute_eth_staking_utility_drift(eth_df, btc_df, window=24):
        if eth_df.empty or btc_df.empty:
            return 0.0
        s_eth = eth_df["Close"] if "Close" in eth_df.columns else eth_df.iloc[:, 0]
        s_btc = btc_df["Close"] if "Close" in btc_df.columns else btc_df.iloc[:, 0]
        return RobustQuantProcessor._compute_robust_divergence_z(s_eth, s_btc, window=window)

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
    def compute_market_breadth(rsp_df, spy_df, window=24):
        if rsp_df.empty or spy_df.empty:
            return 0.0
        s1 = rsp_df["Close"] if "Close" in rsp_df.columns else rsp_df.iloc[:, 0]
        s2 = spy_df["Close"] if "Close" in spy_df.columns else spy_df.iloc[:, 0]
        return RobustQuantProcessor._compute_robust_divergence_z(s1, s2, window=window)

    @staticmethod
    def compute_gsr_velocity(xau_df, xag_df, window=24):
        if xau_df.empty or xag_df.empty:
            return 0.0
        s1 = xau_df["Close"] if "Close" in xau_df.columns else xau_df.iloc[:, 0]
        s2 = xag_df["Close"] if "Close" in xag_df.columns else xag_df.iloc[:, 0]
        return RobustQuantProcessor._compute_robust_divergence_z(s1, s2, window=window)

    @staticmethod
    def compute_bond_duration_risk(tlt_df, shy_df, window=24):
        if tlt_df.empty or shy_df.empty:
            return 0.0
        s1 = tlt_df["Close"] if "Close" in tlt_df.columns else tlt_df.iloc[:, 0]
        s2 = shy_df["Close"] if "Close" in shy_df.columns else shy_df.iloc[:, 0]
        return RobustQuantProcessor._compute_robust_divergence_z(s1, s2, window=window)

    @staticmethod
    def compute_banking_stress(kre_df, spy_df, window=24):
        if kre_df.empty or spy_df.empty:
            return 0.0
        s1 = kre_df["Close"] if "Close" in kre_df.columns else kre_df.iloc[:, 0]
        s2 = spy_df["Close"] if "Close" in spy_df.columns else spy_df.iloc[:, 0]
        return RobustQuantProcessor._compute_robust_divergence_z(s1, s2, window=window)

    @staticmethod
    def compute_defensive_flight(xlu_df, benchmark_df, window=24):
        if xlu_df.empty or benchmark_df.empty:
            return 0.0
        s1 = xlu_df["Close"] if "Close" in xlu_df.columns else xlu_df.iloc[:, 0]
        s2 = benchmark_df["Close"] if "Close" in benchmark_df.columns else benchmark_df.iloc[:, 0]
        return RobustQuantProcessor._compute_robust_divergence_z(s1, s2, window=window)

    @staticmethod
    def compute_consumer_confidence(xly_df, xlp_df, window=24):
        if xly_df.empty or xlp_df.empty:
            return 0.0
        s1 = xly_df["Close"] if "Close" in xly_df.columns else xly_df.iloc[:, 0]
        s2 = xlp_df["Close"] if "Close" in xlp_df.columns else xlp_df.iloc[:, 0]
        return RobustQuantProcessor._compute_robust_divergence_z(s1, s2, window=window)

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
            gamma_stress = np.tanh((ratio - 0.98) * 5.0) * 1.8
            return float(np.clip(gamma_stress, -2.0, 2.0))
        return float(np.clip((cur_vix - 17.5) / 4.0, -1.8, 1.8))

    @staticmethod
    def compute_crypto_funding_stress(funding_rate):
        excess_rate = funding_rate - 0.0001
        stress = float(np.clip(excess_rate * 5000.0, -2.0, 2.0))
        return stress

    @staticmethod
    def compute_gold_oil_ratio(gold_df, oil_df, window=24):
        if gold_df is None or oil_df is None or gold_df.empty or oil_df.empty:
            return 0.0
        s1 = gold_df["Close"] if "Close" in gold_df.columns else gold_df.iloc[:, 0]
        s2 = oil_df["Close"] if "Close" in oil_df.columns else oil_df.iloc[:, 0]
        return RobustQuantProcessor._compute_robust_divergence_z(s1, s2, window=window)

    @staticmethod
    def compute_silver_copper_ratio(silver_df, copper_df, window=24):
        if silver_df.empty or copper_df.empty:
            return 0.0
        s1 = silver_df["Close"] if "Close" in silver_df.columns else silver_df.iloc[:, 0]
        s2 = copper_df["Close"] if "Close" in copper_df.columns else copper_df.iloc[:, 0]
        return RobustQuantProcessor._compute_robust_divergence_z(s1, s2, window=window)

    @staticmethod
    def compute_credit_intraday_velocity(hyg_df, lqd_df, window=4):
        if hyg_df.empty or lqd_df.empty:
            return 0.0
        s1 = hyg_df["Close"] if "Close" in hyg_df.columns else hyg_df.iloc[:, 0]
        s2 = lqd_df["Close"] if "Close" in lqd_df.columns else lqd_df.iloc[:, 0]
        return RobustQuantProcessor._compute_robust_divergence_z(s1, s2, window=window)

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
        mean_val = close.tail(w).mean()
        std_val = close.tail(w).std() + 1e-9
        return float(np.clip((close.iloc[-1] - mean_val) / std_val, -2.0, 2.0))

    @staticmethod
    def compute_ratio_z(df_num, df_denom, window=48):
        if df_num.empty or df_denom.empty:
            return 0.0
        s1 = df_num["Close"] if "Close" in df_num.columns else df_num.iloc[:, 0]
        s2 = df_denom["Close"] if "Close" in df_num.columns else df_denom.iloc[:, 0]
        return RobustQuantProcessor._compute_robust_divergence_z(s1, s2, window=window)

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

    # =========================================================================
    # 🔒 KURUMSAL SİNYAL & GÜÇLÜ AL/SAT ONAY MATRİSİ
    # =========================================================================
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
        active_regime_id=None,
        vol_supported=True,
        volume_supported=True,
        entry_allowed=True
    ):
        """
        GÜÇLÜ AL ve GÜÇLÜ SAT için Hacim ve Volatilite desteğini zorunlu kılar.
        """
        t = SIGNAL_THRESHOLDS
        prev = previous_signal if previous_signal else "NÖTR (BEKLE)"

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
            buy_enter = dyn.get("buy_enter", 0.75)
            sell_enter = dyn.get("sell_enter", -0.75)
            buy_exit = dyn.get("buy_exit", 0.30)
            sell_exit = dyn.get("sell_exit", -0.30)
            strong_buy_enter = dyn.get("strong_buy_enter", 1.60)
            strong_sell_enter = dyn.get("strong_sell_enter", -1.60)
            req_clusters = max(min_clusters, dyn.get("min_clusters", 2))
        else:
            buy_enter = 0.75
            sell_enter = -0.75
            req_clusters = max(min_clusters, 2)
            buy_exit = 0.30
            sell_exit = -0.30
            strong_buy_enter = 1.60
            strong_sell_enter = -1.60

        # 🚀 GÜÇLÜ AL KONTROLÜ (Hacim VE Volatilite VE Giriş İzni Şarttır)
        strong_gate_pass = vol_supported and volume_supported and entry_allowed

        if prev == "GÜÇLÜ AL":
            if current_score > max(buy_exit, 0.50):
                if strong_gate_pass:
                    return "GÜÇLÜ AL", "green", "🟢🟢"
                else:
                    return "AL", "lightgreen", "🟢"
        else:
            if current_score >= strong_buy_enter and bull_clusters >= req_clusters:
                if strong_gate_pass:
                    return "GÜÇLÜ AL", "green", "🟢🟢"
                else:
                    # Hacim veya volatilite desteklemiyorsa 'GÜÇLÜ' verilemez!
                    return "AL", "lightgreen", "🟢"

        # 2. AL KONTROLÜ
        if prev in ["AL", "GÜÇLÜ AL"]:
            if current_score > buy_exit:
                return "AL", "lightgreen", "🟢"
        else:
            if current_score >= buy_enter and bull_clusters >= req_clusters:
                return "AL", "lightgreen", "🟢"
            if not is_choppy and bull_clusters >= 3 and current_score >= max(buy_enter - 0.10, 0.40):
                return "AL", "lightgreen", "🟢"

        # 🚀 GÜÇLÜ SAT KONTROLÜ (Hacim VE Volatilite VE Giriş İzni Şarttır)
        if prev == "GÜÇLÜ SAT":
            if current_score < min(sell_exit, -0.50):
                if strong_gate_pass:
                    return "GÜÇLÜ SAT", "darkred", "🔴🔴"
                else:
                    return "SAT", "red", "🔴"
        else:
            if current_score <= strong_sell_enter and bear_clusters >= req_clusters:
                if strong_gate_pass:
                    return "GÜÇLÜ SAT", "darkred", "🔴🔴"
                else:
                    # Hacim veya volatilite desteklemiyorsa 'GÜÇLÜ' verilemez!
                    return "SAT", "red", "🔴"

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
