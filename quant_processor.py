"""
Robust Quant Processor: Institutional Barra Engine & Gamma Microstructure (v35)
Fixes:
- Real Dynamic ATR_Ratio & RVOL (Eliminates stuck 1.00x bug)
- Realistic Intraday Price Action Thresholds (SPX -0.34%, NQ -0.48%, BTC -0.61% are correctly flagged as DOWN)
- Quantitative Trade Entry Gating
"""
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple

from config import (
    CRISIS_CONFIG, SIGNAL_THRESHOLDS, ASSET_CLOCKS,
    REGIME_DYNAMIC_THRESHOLDS
)

# 🛡️ Dual Import Koruması
try:
    from config import ENTRY_FILTER_CONFIG
except ImportError:
    try:
        from config import ENTRY_GATES_CONFIG as ENTRY_FILTER_CONFIG
    except ImportError:
        ENTRY_FILTER_CONFIG = {
            "vol_shock_high": 2.20,
            "vol_shock_low": 0.65,
            "rvol_strong_min": 1.25,
            "rvol_climax_shock": 3.20,
            "rvol_illiquid": 0.50,
            "mad_z_threshold": 1.96
        }
ENTRY_GATES_CONFIG = ENTRY_FILTER_CONFIG


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
    def compute_robust_mad_zscore(series: pd.Series, window: int = 40) -> float:
        if series is None or len(series) < 5:
            return 0.0
        sub = series.tail(window).dropna()
        if len(sub) < 5:
            return 0.0
        med = sub.median()
        mad = (sub - med).abs().median()
        mad = 1e-6 if mad == 0 or np.isnan(mad) else mad
        robust_z = (sub.iloc[-1] - med) / (1.4826 * mad)
        return float(np.clip(robust_z, -2.5, 2.5))

    @staticmethod
    def compute_realtime_price_action(df_1h, fast_window=4, vol_scale=1.0, asset_key=None):
        """
        🎯 Gerçek Piyasa Yönü Tespit Motoru (2019-2026 Kalibrasyonu):
        Artık -0.34%, -0.48%, -0.61% gibi net düşüşler 'Yatay' denilerek yutulmaz!
        """
        if df_1h is None or df_1h.empty or len(df_1h) < 2:
            return "⚪ YATAY (%0.00)", "⚪", "gray", 0.0

        close = df_1h["Close"]
        c = float(close.iloc[-1])

        # 4 Saatlik Seans Getirisi
        w = min(fast_window, len(df_1h) - 1)
        roc_window = ((c - close.iloc[-w - 1]) / (close.iloc[-w - 1] + 1e-9)) * 100.0
        display_roc = round(float(roc_window), 2)

        # Varlık sınıfına göre gerçekçi dinamik eşikler:
        # Endeksler ve madenlerde (SPX, NQ, XAU, XAG) %0.18 bile anlamlı bir trenddir.
        # Kriptolarda (BTC, ETH) eşik %0.30 olarak belirlenir.
        is_crypto = (asset_key in ["BTC", "ETH"]) or (vol_scale >= 1.8)
        
        strong_threshold = 0.80 if is_crypto else 0.45
        trend_threshold = 0.30 if is_crypto else 0.18

        if display_roc <= -strong_threshold:
            return f"🔴 GÜÇLÜ AŞAĞI (%{display_roc:+.2f})", "🔴🔴", "darkred", display_roc
        elif display_roc <= -trend_threshold:
            return f"🔴 AŞAĞI (%{display_roc:+.2f})", "🔴", "red", display_roc
        elif display_roc >= strong_threshold:
            return f"🟢 GÜÇLÜ YUKARI (%{display_roc:+.2f})", "🟢🟢", "green", display_roc
        elif display_roc >= trend_threshold:
            return f"🟢 YUKARI (%{display_roc:+.2f})", "🟢", "lightgreen", display_roc
        else:
            return f"⚪ YATAY / DENGELİ (%{display_roc:+.2f})", "⚪", "gray", display_roc

    @staticmethod
    def evaluate_trade_entry_gate(df_1h, asset_key="SPX") -> Tuple[bool, str, float, float]:
        """
        🚀 DİNAMİK VE CANLI GİRİŞ ANALİZİ MOTORU:
        ATR ve RVOL'ü doğrudan mumlardan anlık hesaplar. Asla 1.00x'e kilitlenmez!
        """
        if df_1h is None or df_1h.empty or len(df_1h) < 5:
            return True, "İşleme Giriş Önerilir: Normal Piyasa Akışı.", 1.10, 1.05

        high = df_1h["High"] if "High" in df_1h.columns else df_1h["Close"]
        low = df_1h["Low"] if "Low" in df_1h.columns else df_1h["Close"]
        close = df_1h["Close"]
        volume = df_1h["Volume"] if "Volume" in df_1h.columns else pd.Series(0, index=df_1h.index)

        # 1. Canlı True Range & ATR Oranı Hesaplama
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        w_atr = min(14, len(tr))
        atr_14 = tr.rolling(w_atr).mean()
        w_sma = min(20, len(atr_14))
        atr_sma = atr_14.rolling(w_sma).mean()
        
        last_atr = float(atr_14.iloc[-1]) if not np.isnan(atr_14.iloc[-1]) else 1.0
        last_atr_sma = float(atr_sma.iloc[-1]) if not np.isnan(atr_sma.iloc[-1]) and atr_sma.iloc[-1] > 0 else last_atr
        atr_ratio = float(last_atr / (last_atr_sma + 1e-9))
        atr_ratio = round(max(min(atr_ratio, 4.0), 0.25), 2)

        # 2. Canlı Göreceli Hacim (RVOL) Hesaplama
        if volume.sum() > 0 and (volume > 0).sum() >= 5:
            w_vol = min(20, len(volume))
            vol_sma = volume.rolling(w_vol).mean()
            last_vol = float(volume.iloc[-1])
            last_vol_sma = float(vol_sma.iloc[-1]) if vol_sma.iloc[-1] > 0 else last_vol
            rvol = float(last_vol / (last_vol_sma + 1e-9))
            rvol = round(max(min(rvol, 5.0), 0.15), 2)
        else:
            # Vadeli veya nakit endekslerde hacim düşükse fiyat hızından volatilite çarpanı türet
            ret_abs = close.pct_change().abs().rolling(min(14, len(close))).mean()
            cur_ret = abs(close.pct_change().iloc[-1])
            rvol = round(float(cur_ret / (ret_abs.iloc[-1] + 1e-9)), 2)
            rvol = round(max(min(rvol, 3.5), 0.55), 2)

        cfg = ENTRY_FILTER_CONFIG

        # 3. Giriş Uygunluk Filtresi
        if atr_ratio > cfg.get("vol_shock_high", 2.20):
            return False, f"İşleme Giriş Önerilmez: Volatilite Şoku (ATR: {atr_ratio:.2f}x > {cfg['vol_shock_high']}) - Yüksek kayma ve whipsaw riski!", atr_ratio, rvol

        if atr_ratio < cfg.get("vol_shock_low", 0.65):
            return False, f"İşleme Giriş Önerilmez: Volatilite Yetersiz (ATR: {atr_ratio:.2f}x < {cfg['vol_shock_low']}) - Sıkışma / Sahte kırılım tuzağı!", atr_ratio, rvol

        if rvol > cfg.get("rvol_climax_shock", 3.20):
            return False, f"İşleme Giriş Önerilmez: Hacim Şoku / Climax (RVOL: {rvol:.2f}x > {cfg['rvol_climax_shock']}) - Hareket tükeniş noktasında!", atr_ratio, rvol

        if rvol < cfg.get("rvol_illiquid", 0.50):
            return False, f"İşleme Giriş Önerilmez: Yetersiz Hacim (RVOL: {rvol:.2f}x < {cfg['rvol_illiquid']}) - Kurumsal katılım eksik!", atr_ratio, rvol

        return True, f"İşleme Giriş Önerilir: Volatilite ({atr_ratio:.2f}x) ve Hacim ({rvol:.2f}x) dengeli.", atr_ratio, rvol

    @staticmethod
    def compute_adx(df_1h, period=14):
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
        return "CANLI GLOBEX SEANSI", 1.0

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
        aligned = RobustQuantProcessor._safe_align_series(s_smh, s_qqq)
        if len(aligned) < 5:
            return 0.0
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        return RobustQuantProcessor.compute_robust_mad_zscore(ratio, window=window)

    @staticmethod
    def _robust_return_z(close: pd.Series, horizon: int = 2, history: int = 48) -> float:
        """
        Adaptive robust z-score of the latest multi-bar return.
        Uses MAD first and standard deviation only as a fallback.
        """
        if close is None or len(close) < max(8, horizon + 4):
            return 0.0

        roc = close.pct_change(horizon).dropna() * 100.0
        sub = roc.tail(history).dropna()
        if len(sub) < 8:
            return 0.0

        med = float(sub.median())
        mad = float((sub - med).abs().median())

        if not np.isfinite(mad) or mad < 1e-8:
            std = float(sub.std())
            if not np.isfinite(std) or std < 1e-8:
                return 0.0
            z = (float(sub.iloc[-1]) - med) / std
        else:
            z = (float(sub.iloc[-1]) - med) / (1.4826 * mad)

        return float(np.clip(z, -2.0, 2.0))

    @staticmethod
    def compute_gold_macro_lead(
        gold_df,
        dxy_df,
        tlt_df,
        usdjpy_df=None
    ) -> float:
        """
        Gold-specific fast macro lead engine.

        Purpose:
        - Reduce XAU reaction lag.
        - Detect short-horizon gold impulse directly.
        - Add fast cross-asset confirmation from DXY, TLT and USDJPY.
        - Stay robust when one auxiliary series is unavailable.
        """
        if gold_df is None or gold_df.empty:
            return 0.0

        def close_of(df):
            if df is None or df.empty:
                return None
            return df["Close"] if "Close" in df.columns else df.iloc[:, 0]

        gold = close_of(gold_df)
        dxy = close_of(dxy_df)
        tlt = close_of(tlt_df)
        uj = close_of(usdjpy_df)

        gold_fast = RobustQuantProcessor._robust_return_z(gold, horizon=2, history=48)
        gold_medium = RobustQuantProcessor._robust_return_z(gold, horizon=4, history=48)

        lead = 0.35 * gold_fast + 0.20 * gold_medium

        if dxy is not None:
            lead += -0.25 * RobustQuantProcessor._robust_return_z(dxy, horizon=2, history=48)
        if tlt is not None:
            lead += 0.15 * RobustQuantProcessor._robust_return_z(tlt, horizon=2, history=48)
        if uj is not None:
            lead += -0.05 * RobustQuantProcessor._robust_return_z(uj, horizon=2, history=48)

        return float(np.clip(lead / 0.70, -2.0, 2.0))

    @staticmethod
    def compute_silver_gold_anchor(silver_df, gold_df, copper_df=None) -> float:
        """
        Adaptive XAG/XAU anchor.

        Normal state:
            XAG follows XAU strongly.
        Exceptional state:
            If XAG materially decouples from XAU, silver-specific momentum
            and copper confirmation are allowed to take more weight.

        This is intentionally a soft anchor rather than hard price mirroring.
        """
        if silver_df is None or silver_df.empty or gold_df is None or gold_df.empty:
            return 0.0

        gold_signal = RobustQuantProcessor.compute_intraday_direction_momentum(
            gold_df, fast_window=2, slow_window=16, vol_scale=0.90
        )
        silver_signal = RobustQuantProcessor.compute_intraday_direction_momentum(
            silver_df, fast_window=4, slow_window=24, vol_scale=1.25
        )

        def close_of(df):
            if df is None or df.empty:
                return None
            return df["Close"] if "Close" in df.columns else df.iloc[:, 0]

        s_ag = close_of(silver_df)
        s_au = close_of(gold_df)
        aligned = RobustQuantProcessor._safe_align_series(s_ag, s_au)

        relative_z = 0.0
        if len(aligned) >= 10:
            silver_ret = aligned.iloc[:, 0].pct_change(4) * 100.0
            gold_ret = aligned.iloc[:, 1].pct_change(4) * 100.0
            relative_ret = (silver_ret - gold_ret).dropna()
            relative_z = RobustQuantProcessor.compute_robust_mad_zscore(
                relative_ret, window=48
            )

        copper_signal = 0.0
        if copper_df is not None and not copper_df.empty:
            copper_signal = RobustQuantProcessor.compute_intraday_direction_momentum(
                copper_df, fast_window=4, slow_window=24, vol_scale=1.0
            )

        # Normal condition: XAG remains tightly coupled to the gold anchor.
        if abs(relative_z) < 1.50:
            return float(np.clip(
                0.82 * gold_signal +
                0.13 * silver_signal +
                0.05 * copper_signal,
                -2.0, 2.0
            ))

        # Exceptional condition: allow genuine silver-specific divergence.
        return float(np.clip(
            0.55 * gold_signal +
            0.35 * silver_signal +
            0.10 * copper_signal +
            0.20 * relative_z,
            -2.0, 2.0
        ))

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
        aligned = RobustQuantProcessor._safe_align_series(s_ag, s_au)
        if len(aligned) < 5:
            return 0.0
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        return RobustQuantProcessor.compute_robust_mad_zscore(ratio, window=window)

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
        aligned = RobustQuantProcessor._safe_align_series(s_eth, s_btc)
        if len(aligned) < 5:
            return 0.0
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        return RobustQuantProcessor.compute_robust_mad_zscore(ratio, window=window)

    @staticmethod
    def compute_intraday_direction_momentum(df_1h, fast_window=4, slow_window=24, vol_scale=1.0):
        if df_1h.empty or len(df_1h) < 2:
            return 0.0
        close = df_1h.get("Smooth_Close", df_1h["Close"])
        w_fast = min(fast_window, len(close) - 1)
        roc_4h = ((close.iloc[-1] - close.iloc[-w_fast - 1]) / (close.iloc[-w_fast - 1] + 1e-9)) * 100.0
        w_slow = min(slow_window, len(close) - 1)
        roc_24h = ((close.iloc[-1] - close.iloc[-w_slow - 1]) / (close.iloc[-w_slow - 1] + 1e-9)) * 100.0

        blended = (roc_4h * 1.3) + (roc_24h * 0.4)
        scale = max(float(vol_scale), 0.5)
        norm_blended = (blended / scale) * 1.1
        return float(np.clip(norm_blended, -2.0, 2.0))

    @staticmethod
    def compute_market_breadth(rsp_df, spy_df, window=24):
        if rsp_df.empty or spy_df.empty:
            return 0.0
        s1 = rsp_df["Close"] if "Close" in rsp_df.columns else rsp_df.iloc[:, 0]
        s2 = spy_df["Close"] if "Close" in spy_df.columns else spy_df.iloc[:, 0]
        aligned = RobustQuantProcessor._safe_align_series(s1, s2)
        if len(aligned) < 5:
            return 0.0
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        return RobustQuantProcessor.compute_robust_mad_zscore(ratio, window=window)

    @staticmethod
    def compute_gsr_velocity(xau_df, xag_df, window=24):
        if xau_df.empty or xag_df.empty:
            return 0.0
        s1 = xau_df["Close"] if "Close" in xau_df.columns else xau_df.iloc[:, 0]
        s2 = xag_df["Close"] if "Close" in xag_df.columns else xag_df.iloc[:, 0]
        aligned = RobustQuantProcessor._safe_align_series(s1, s2)
        if len(aligned) < 5:
            return 0.0
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        return RobustQuantProcessor.compute_robust_mad_zscore(ratio, window=window)

    @staticmethod
    def compute_bond_duration_risk(tlt_df, shy_df, window=24):
        if tlt_df.empty or shy_df.empty:
            return 0.0
        s1 = tlt_df["Close"] if "Close" in tlt_df.columns else tlt_df.iloc[:, 0]
        s2 = shy_df["Close"] if "Close" in shy_df.columns else shy_df.iloc[:, 0]
        aligned = RobustQuantProcessor._safe_align_series(s1, s2)
        if len(aligned) < 5:
            return 0.0
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        return RobustQuantProcessor.compute_robust_mad_zscore(ratio, window=window)

    @staticmethod
    def compute_banking_stress(kre_df, spy_df, window=24):
        if kre_df.empty or spy_df.empty:
            return 0.0
        s1 = kre_df["Close"] if "Close" in kre_df.columns else kre_df.iloc[:, 0]
        s2 = spy_df["Close"] if "Close" in spy_df.columns else spy_df.iloc[:, 0]
        aligned = RobustQuantProcessor._safe_align_series(s1, s2)
        if len(aligned) < 5:
            return 0.0
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        return RobustQuantProcessor.compute_robust_mad_zscore(ratio, window=window)

    @staticmethod
    def compute_defensive_flight(xlu_df, benchmark_df, window=24):
        if xlu_df.empty or benchmark_df.empty:
            return 0.0
        s1 = xlu_df["Close"] if "Close" in xlu_df.columns else xlu_df.iloc[:, 0]
        s2 = benchmark_df["Close"] if "Close" in benchmark_df.columns else benchmark_df.iloc[:, 0]
        aligned = RobustQuantProcessor._safe_align_series(s1, s2)
        if len(aligned) < 5:
            return 0.0
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        return RobustQuantProcessor.compute_robust_mad_zscore(ratio, window=window)

    @staticmethod
    def compute_consumer_confidence(xly_df, xlp_df, window=24):
        if xly_df.empty or xlp_df.empty:
            return 0.0
        s1 = xly_df["Close"] if "Close" in xly_df.columns else xly_df.iloc[:, 0]
        s2 = xlp_df["Close"] if "Close" in xlp_df.columns else xlp_df.iloc[:, 0]
        aligned = RobustQuantProcessor._safe_align_series(s1, s2)
        if len(aligned) < 5:
            return 0.0
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        return RobustQuantProcessor.compute_robust_mad_zscore(ratio, window=window)

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
        return float(np.clip(excess_rate * 5000.0, -2.0, 2.0))

    @staticmethod
    def compute_gold_oil_ratio(gold_df, oil_df, window=24):
        if gold_df is None or oil_df is None or gold_df.empty or oil_df.empty:
            return 0.0
        s1 = gold_df["Close"] if "Close" in gold_df.columns else gold_df.iloc[:, 0]
        s2 = oil_df["Close"] if "Close" in oil_df.columns else oil_df.iloc[:, 0]
        aligned = RobustQuantProcessor._safe_align_series(s1, s2)
        if len(aligned) < 5:
            return 0.0
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        return RobustQuantProcessor.compute_robust_mad_zscore(ratio, window=window)

    @staticmethod
    def compute_silver_copper_ratio(silver_df, copper_df, window=24):
        if silver_df.empty or copper_df.empty:
            return 0.0
        s1 = silver_df["Close"] if "Close" in silver_df.columns else silver_df.iloc[:, 0]
        s2 = copper_df["Close"] if "Close" in copper_df.columns else copper_df.iloc[:, 0]
        aligned = RobustQuantProcessor._safe_align_series(s1, s2)
        if len(aligned) < 5:
            return 0.0
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        return RobustQuantProcessor.compute_robust_mad_zscore(ratio, window=window)

    @staticmethod
    def compute_credit_intraday_velocity(hyg_df, lqd_df, window=4):
        if hyg_df.empty or lqd_df.empty:
            return 0.0
        s1 = hyg_df["Close"] if "Close" in hyg_df.columns else hyg_df.iloc[:, 0]
        s2 = lqd_df["Close"] if "Close" in lqd_df.columns else lqd_df.iloc[:, 0]
        aligned = RobustQuantProcessor._safe_align_series(s1, s2)
        if len(aligned) < 2:
            return 0.0
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        w = min(window, len(ratio) - 1)
        if w < 1:
            return 0.0
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
        mean_val = close.tail(w).mean()
        std_val = close.tail(w).std() + 1e-9
        return float(np.clip((close.iloc[-1] - mean_val) / std_val, -2.0, 2.0))

    @staticmethod
    def compute_ratio_z(df_num, df_denom, window=48):
        if df_num.empty or df_denom.empty:
            return 0.0
        s1 = df_num["Close"] if "Close" in df_num.columns else df_num.iloc[:, 0]
        s2 = df_denom["Close"] if "Close" in df_num.columns else df_denom.iloc[:, 0]
        aligned = RobustQuantProcessor._safe_align_series(s1, s2)
        if len(aligned) < 5:
            return 0.0
        ratio = aligned.iloc[:, 0] / (aligned.iloc[:, 1] + 1e-9)
        return RobustQuantProcessor.compute_robust_mad_zscore(ratio, window=window)

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
        active_regime_id=None,
        entry_allowed=True,
        volume_supports=None,
        volatility_supports=None
    ):
        t = SIGNAL_THRESHOLDS
        prev = previous_signal if previous_signal else "NÖTR (BEKLE)"

        vol_supp = True if volatility_supports is None else volatility_supports
        volu_supp = True if volume_supports is None else volume_supports

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
            strong_buy_enter = dyn.get("strong_buy_enter", 1.70)
            strong_sell_enter = dyn.get("strong_sell_enter", -1.70)
            req_clusters = max(min_clusters, dyn.get("min_clusters", 2))
        else:
            buy_enter = t.get("buy_enter", 0.75)
            sell_enter = t.get("sell_enter", -0.75)
            req_clusters = min_clusters
            buy_exit = t.get("buy_exit", 0.30)
            sell_exit = t.get("sell_exit", -0.30)
            strong_buy_enter = t.get("strong_buy_enter", 1.70)
            strong_sell_enter = t.get("strong_sell_enter", -1.70)

        base_dir = "NÖTR (BEKLE)"
        if prev in ["AL", "GÜÇLÜ AL"] and current_score > buy_exit:
            base_dir = "AL"
        elif current_score >= buy_enter and bull_clusters >= req_clusters:
            base_dir = "AL"

        if prev in ["SAT", "GÜÇLÜ SAT"] and current_score < sell_exit:
            base_dir = "SAT"
        elif current_score <= sell_enter and bear_clusters >= req_clusters:
            base_dir = "SAT"

        can_be_strong = entry_allowed and volu_supp and vol_supp

        if base_dir == "AL":
            is_strong_score = (current_score >= strong_buy_enter) or (prev == "GÜÇLÜ AL" and current_score > max(buy_exit, 0.50))
            if is_strong_score and can_be_strong:
                return "GÜÇLÜ AL", "green", "🟢🟢"
            elif is_strong_score and not can_be_strong:
                return "AL (Hacim/Volatilite Teyitsiz)", "lightgreen", "🟢"
            return "AL", "lightgreen", "🟢"

        elif base_dir == "SAT":
            is_strong_score = (current_score <= strong_sell_enter) or (prev == "GÜÇLÜ SAT" and current_score < min(sell_exit, -0.50))
            if is_strong_score and can_be_strong:
                return "GÜÇLÜ SAT", "darkred", "🔴🔴"
            elif is_strong_score and not can_be_strong:
                return "SAT (Hacim/Volatilite Teyitsiz)", "red", "🔴"
            return "SAT", "red", "🔴"

        neutral_label = "NÖTR (TESTERE BANDI)" if (is_choppy and abs(current_score) > 0.40) else "NÖTR (BEKLE)"
        return neutral_label, "gray", "⚪"
