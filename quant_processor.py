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


# Dinamik giriş profili. Bunlar piyasa değeri eşiği değildir; eşiklerin
# son gerçekleşmiş barların kendi dağılımından çıkarılmasını tanımlar.
# Böylece BTC, ETH, ES, NQ, GC, SI vb. aynı ham RVOL/ATR sınırlarına zorlanmaz.
ADAPTIVE_ENTRY_CONFIG = {
    "window": 150,
    "min_history": 60,
    "rvol_baseline_period": 20,
    "atr_period": 14,
    "atr_baseline_period": 20,
    "rvol_illiquid_percentile": 0.05,
    "rvol_strong_percentile": 0.70,
    "rvol_climax_percentile": 0.99,
    "atr_low_percentile": 0.05,
    "atr_high_percentile": 0.95,
}


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
    def _direction_stats(df_1h):
        if df_1h is None or not isinstance(df_1h, pd.DataFrame) or df_1h.empty:
            return None
        df = df_1h.copy()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns=[c[0] if isinstance(c,tuple) else c for c in df.columns]
        if "Close" not in df.columns or any(c not in df.columns for c in ("Open","High","Low","Close")):
            return None
        df=df.loc[:,~df.columns.duplicated(keep="last")].copy()
        for c in ("Open","High","Low","Close"): df[c]=pd.to_numeric(df[c],errors="coerce")
        df=df.replace([np.inf,-np.inf],np.nan).dropna(subset=["Open","High","Low","Close"])
        if len(df)<8: return None
        close=df["Close"]

        # --- Volatilite normalizasyonu için TABAN (floor) ---
        # `norm_impulse` ve aşağıdaki `ret_z_1h`, kısa dönem (son 40 bar)
        # gerçekleşen volatiliteye bölerek normalize eder. Bir varlığın kısa
        # dönemi tesadüfen sakinleşirse (vol ~0'a yaklaşırsa), bölen küçüldüğü
        # için AYNI küçük ham fiyat hareketi bile yapay şekilde "GÜÇLÜ" bir
        # sinyale şişebiliyordu. Bu, iki gerçekte birlikte hareket eden varlık
        # (ör. BTC/ETH) arasında, sadece biri kısa süreliğine sakinleşmiş diye
        # "Canlı Fiyat Yönü" etiketlerinin gereğinden fazla ayrışmasına yol
        # açan asıl mekanizmaydı. Çözüm: kısa dönem volatiliteyi, varlığın
        # kendi daha uzun (150 bar) temel volatilitesinin bir payının ALTINA
        # düşürmemek (taban uygulamak). Bu sadece anormal sıkışma anlarında
        # devreye girer; normal/yüksek volatilite dönemlerinde etkisizdir.
        _all_rets = close.pct_change().dropna()
        baseline_vol = float(_all_rets.tail(150).std()) if len(_all_rets) >= 30 else 0.0
        # NOT (denetim düzeltmesi): İlk sürümde taban çok gevşekti (kısa vol
        # baseline'ın %35'inin altına her düştüğünde devreye giriyordu) ve bu
        # NORMAL günlük volatilite dalgalanmalarında bile sık sık tetiklenip
        # skorları gereğinden fazla söndürerek "Canlı Fiyat Yönü"nün genel
        # olarak nötrleşmesine katkı yapmış olabilirdi. Artık taban SADECE
        # gerçekten patolojik bir sıkışmada (kısa vol, temel volatilitenin
        # %20'sinin ALTINA düşerse) devreye girer ve o %20 seviyesine kadar
        # kaldırır — normal aralıktaki dalgalanmalara dokunmaz.
        VOL_FLOOR_TRIGGER_RATIO = 0.20
        VOL_FLOOR_LEVEL_RATIO = 0.20

        def _apply_vol_floor(vol):
            if baseline_vol > 0 and vol < (VOL_FLOOR_TRIGGER_RATIO * baseline_vol):
                return VOL_FLOOR_LEVEL_RATIO * baseline_vol
            return vol

        def norm_impulse(x,bars):
            if len(x)<=bars: return 0.0
            ret=float(x.iloc[-1]/x.iloc[-bars-1]-1.0)
            prev=x.pct_change().tail(40).dropna(); vol=float(prev.std()) if len(prev)>=8 else 0.0
            vol = _apply_vol_floor(vol)
            atr=float((x.diff().abs()).rolling(14,min_periods=14).mean().iloc[-1]) if len(x)>=15 else 0.0
            price=float(x.iloc[-1]); scale=(vol*max(bars,1)) if vol>0 else (atr/max(price,1e-9)*max(bars,1) if atr>0 else 0.0)
            return float(np.clip(ret/(scale+1e-12),-4.0,4.0))
        def persistence(x,n):
            r=x.diff().tail(n).dropna()
            if len(r)<3: return 0.0
            return float(np.clip(np.sign(r).mean(),-1.0,1.0))
        def adx_di(x,period=14):
            high=df["High"] if x is close else x["High"]; low=df["Low"] if x is close else x["Low"]; c=x if isinstance(x,pd.Series) else x["Close"]
            prev=c.shift(1); tr=pd.concat([high-low,(high-prev).abs(),(low-prev).abs()],axis=1).max(axis=1)
            up=high.diff(); down=-low.diff(); plus=pd.Series(np.where((up>down)&(up>0),up,0.0),index=high.index); minus=pd.Series(np.where((down>up)&(down>0),down,0.0),index=high.index)
            atr=tr.rolling(period,min_periods=period).mean(); pdi=100*plus.rolling(period,min_periods=period).mean()/(atr+1e-12); mdi=100*minus.rolling(period,min_periods=period).mean()/(atr+1e-12)
            dx=100*(pdi-mdi).abs()/(pdi+mdi+1e-12); adx=dx.rolling(period,min_periods=period).mean()
            a=float(adx.iloc[-1]) if np.isfinite(adx.iloc[-1]) else 0.0; p=float(pdi.iloc[-1]) if np.isfinite(pdi.iloc[-1]) else 0.0; m=float(mdi.iloc[-1]) if np.isfinite(mdi.iloc[-1]) else 0.0
            bias=(p-m)/(p+m+1e-12) if (p+m)>0 else 0.0; return a,float(np.clip(bias,-1,1))
        df2=df.resample("2h",label="right",closed="right").agg({"Open":"first","High":"max","Low":"min","Close":"last"}).dropna()
        df4=df.resample("4h",label="right",closed="right").agg({"Open":"first","High":"max","Low":"min","Close":"last"}).dropna()
        i1=norm_impulse(close,1); i2=norm_impulse(close,2); i4=norm_impulse(df4["Close"],1) if len(df4)>=16 else norm_impulse(close,4)
        p1=persistence(close,6); p2=persistence(close,3); p4=persistence(df4["Close"],5) if len(df4)>=7 else 0.0
        a1,b1=adx_di(df,14); a4,b4=adx_di(df4,14) if len(df4)>=28 else (0.0,0.0)

        # --- Gerçek yüzdesel değişimler (ekranda gösterilecek ve kısa-ufuk
        # skorunun temel girdisi olacak ham % hareketler; normalize edilmiş
        # "impulse" değerlerinden ayrı tutulur ki etiket / % gösterimi asla
        # birbiriyle çelişmesin). ---
        roc_1h = float((close.iloc[-1] / close.iloc[-2] - 1.0) * 100.0)
        roc_2h = float((close.iloc[-1] / close.iloc[-3] - 1.0) * 100.0) if len(close) >= 3 else roc_1h
        roc_4h = (
            float((df4["Close"].iloc[-1] / df4["Close"].iloc[-2] - 1.0) * 100.0)
            if len(df4) >= 2 else roc_2h
        )

        # 1 saatlik getirinin kendi son (40 barlık) dağılımına göre z-skoru.
        # Ham % değişim piyasadan piyasaya kıyaslanamaz; z-skoru bunu
        # varlığın kendi güncel volatilite rejimine göre normalize eder.
        hourly_returns = close.pct_change().tail(40).dropna()
        if len(hourly_returns) >= 10:
            mu = float(hourly_returns.mean())
            sd = float(hourly_returns.std())
            sd = _apply_vol_floor(sd)
            ret_z_1h = float(np.clip((hourly_returns.iloc[-1] - mu) / (sd + 1e-9), -3.5, 3.5))
        else:
            ret_z_1h = 0.0

        return {
            "roc_1h": roc_1h, "roc_2h": roc_2h, "roc_4h": roc_4h,
            "ret_z_1h": ret_z_1h,
            "impulse_1h": i1, "impulse_2h": i2, "impulse_4h": i4,
            "persist_1h": p1, "persist_2h": p2, "persist_4h": p4,
            "adx_1h": a1, "adx_4h": a4, "di_1h": b1, "di_4h": b4,
        }

    @staticmethod
    def compute_direction_score(df_1h):
        """Return the normalized MODEL_DIRECTION score without formatting it."""
        s = RobustQuantProcessor._direction_stats(df_1h)
        if s is None:
            return None, None

        base = (
            0.45 * s["impulse_1h"]
            + 0.30 * s["impulse_2h"]
            + 0.45 * s["impulse_4h"]
            + 0.20 * s["persist_1h"]
            + 0.20 * s["persist_4h"]
            + 0.15 * s["di_1h"]
            + 0.25 * s["di_4h"]
        )
        adx_strength = float(np.clip(max(s["adx_1h"], s["adx_4h"]) / 35.0, 0.0, 1.0))
        score = float(np.clip(base * (0.85 + 0.30 * adx_strength), -4.0, 4.0))

        strong_1h = abs(s["impulse_1h"]) >= 1.15
        flat_4h = abs(s["impulse_4h"]) < 0.35 and abs(s["persist_4h"]) < 0.35
        if strong_1h and flat_4h:
            score = float(
                s["impulse_1h"]
                * (0.85 + 0.15 * np.sign(s["impulse_1h"]) * np.sign(s["impulse_2h"]))
            )

        return score, s

    @staticmethod
    def format_direction_score(score, roc_1h):
        """Format a direction score consistently for UI and pair reconciliation."""
        if score is None or roc_1h is None:
            return "⚪ VERİ YETERSİZ", "⚪", "gray", 0.0
        up, down = 0.65, 1.35
        roc = float(roc_1h)
        score = float(score)
        if score >= down:
            return f"🟢 GÜÇLÜ YUKARI (%{roc:+.2f})", "🟢🟢", "darkgreen", round(roc, 2)
        if score >= up:
            return f"🟢 YUKARI (%{roc:+.2f})", "🟢", "lightgreen", round(roc, 2)
        if score <= -down:
            return f"🔴 GÜÇLÜ AŞAĞI (%{roc:+.2f})", "🔴🔴", "darkred", round(roc, 2)
        if score <= -up:
            return f"🔴 AŞAĞI (%{roc:+.2f})", "🔴", "red", round(roc, 2)
        return f"⚪ YATAY / DENGELİ (%{roc:+.2f})", "⚪", "gray", round(roc, 2)

    @staticmethod
    def compute_realtime_price_action(df_1h, fast_window=4, vol_scale=1.0, asset_key=None):
        """MODEL_DIRECTION: direct-data 1H/2H/4H impulse + persistence + ADX/DI."""
        score, s = RobustQuantProcessor.compute_direction_score(df_1h)
        if s is None:
            return "⚪ VERİ YETERSİZ", "⚪", "gray", 0.0
        return RobustQuantProcessor.format_direction_score(score, s["roc_1h"])

    # =========================================================================
    # CANLI FİYAT YÖNÜ (LIVE / 1-4 SAAT UFUK) — bağımsız kısa-ufuk motoru
    # =========================================================================
    # NOT: `compute_direction_score` (yukarıda) 1H+2H+4H etkilerini tek bir
    # skorda karıştırır; bu da ekranda görünen ham 1H % değişim ile etiketin
    # (ör. "🟢 YUKARI" yanında negatif bir %) çelişebilmesine yol açıyordu,
    # çünkü etiketi 4 saatlik bileşen belirleyip yüzdeyi 1 saatlik getiri
    # gösteriyordu. "Canlı Fiyat Yönü" tanım gereği ŞİMDİKİ (1-4 saat ileriye
    # dönük) durumu yansıtmalı; bu yüzden 4 saatlik bileşen buradan tamamen
    # çıkarılmış, skor ve gösterilen % aynı kısa-ufuk girdilerinden üretilir.
    # Model Sinyali (orta ufuk, 24 saat-1 hafta) zaten ayrı bir çok-faktörlü
    # motor (gatekeeper.py + stateful_adaptive_*) tarafından hesaplanıyor.
    @staticmethod
    def compute_live_horizon_score(df_1h):
        """
        Kısa-ufuk (1-4 saat) canlı yön skoru: 1H/2H itki + 1H getiri z-skoru +
        kısa vadeli yön kalıcılığı (DI) karışımı. 4 saatlik/daha yavaş
        bileşenler kasıtlı olarak dışarıda bırakılır (onlar Model Sinyali'nin
        işi). Dönen `score` ile `meta` içindeki ham % değişimler HER ZAMAN
        aynı girdilerden türetildiği için etiket/yüzde çelişkisi oluşmaz.
        """
        s = RobustQuantProcessor._direction_stats(df_1h)
        if s is None:
            return None, None

        base = (
            0.40 * s["ret_z_1h"]
            + 0.55 * s["impulse_1h"]
            + 0.30 * s["impulse_2h"]
            + 0.25 * s["persist_1h"]
            + 0.15 * s["persist_2h"]
            + 0.20 * s["di_1h"]
        )
        # ADX düşükken (yatay/testere piyasa) kısa-ufuk sinyalin gürültü
        # olma ihtimali yüksektir; ADX yükseldikçe skor hafifçe güçlendirilir.
        adx_strength = float(np.clip(s["adx_1h"] / 30.0, 0.0, 1.0))
        score = float(np.clip(base * (0.80 + 0.35 * adx_strength), -4.0, 4.0))

        meta = dict(s)
        meta["ret_pct_1h"] = s["roc_1h"]
        meta["ret_pct_2h"] = s["roc_2h"]
        return score, meta

    @staticmethod
    def classify_intraday_regime(adx_val, atr_ratio):
        """
        Günün (gün-içi) rejimini trend gücü (ADX) ve volatilite (ATR oranı)
        eksenlerinde sınıflandırır. Bu etiket, "Canlı Fiyat Yönü" için hangi
        dinamik eşiklerin ve ne kadar güvenin uygulanacağını belirler.
        """
        try:
            adx_val = float(adx_val)
        except (TypeError, ValueError):
            adx_val = 25.0
        try:
            atr_ratio = float(atr_ratio)
        except (TypeError, ValueError):
            atr_ratio = 1.0

        # --- Veri-kalitesi koruması ---
        # `evaluate_trade_entry_gate()` gerçek/taze veri veya yeterli profil
        # bulamadığında atr_ratio'yu KASITLI OLARAK 0.0 döndürür (bkz.
        # quant_processor.evaluate_trade_entry_gate ilk guard'ları). Bu 0.0
        # bir "hesaplanmış düşük volatilite" değeri DEĞİLDİR; "ölçülemedi"
        # anlamına gelir. Önceden bu ayrım yapılmadığı için özellikle NQ
        # (seans dışı/stale veri anları) ve ETH gibi varlıklarda veri
        # kalitesi sorunu yanlışlıkla "DÜŞÜK VOLATİLİTE / SIKIŞMA" gün-içi
        # rejimi olarak gösteriliyordu. Bu durumda volatilite bilinmiyor
        # kabul edilir; sahte bir vol_state üretilmez.
        atr_known = atr_ratio > 0.05

        if adx_val >= 25.0:
            trend_state = "GÜÇLÜ TREND"
        elif adx_val >= 20.0:
            trend_state = "GELİŞEN TREND"
        else:
            trend_state = "YATAY / TESTERE"

        if not atr_known:
            vol_state = "VOLATİLİTE BİLİNMİYOR (VERİ YETERSİZ)"
        elif atr_ratio >= 1.35:
            vol_state = "YÜKSEK VOLATİLİTE"
        elif atr_ratio <= 0.70:
            vol_state = "DÜŞÜK VOLATİLİTE / SIKIŞMA"
        else:
            vol_state = "NORMAL VOLATİLİTE"

        label = f"{trend_state} · {vol_state}"
        return {"label": label, "trend_state": trend_state, "vol_state": vol_state,
                "adx_val": adx_val, "atr_ratio": atr_ratio, "atr_known": atr_known}

    @staticmethod
    def _adaptive_entry_profile(df_1h):
        """
        Giriş eşiğini ham sabit sayılardan değil, varlığın kendi son
        gerçekleşmiş bar dağılımından çıkarır.

        Önemli kurallar:
        - Current bar RVOL baseline'a dahil edilmez.
        - Current bar, threshold dağılımına dahil edilmez.
        - ATR ve RVOL eşikleri yüzdelik konumdan türetilir.
        - Minimum tarihçe yoksa giriş güvenli biçimde reddedilir.
        """
        if df_1h is None or not isinstance(df_1h, pd.DataFrame) or df_1h.empty:
            return None, "Gerçek piyasa verisi yok."

        cfg = ADAPTIVE_ENTRY_CONFIG
        atr_period = int(cfg["atr_period"])
        atr_base_period = int(cfg["atr_baseline_period"])
        rvol_base_period = int(cfg["rvol_baseline_period"])
        window = int(cfg["window"])
        min_history = int(cfg["min_history"])

        df = df_1h.copy()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df = df.loc[:, ~df.columns.duplicated(keep="last")].copy()

        for c in ("Open", "High", "Low", "Close", "Volume"):
            if c not in df.columns:
                if c == "Volume":
                    df[c] = np.nan
                else:
                    return None, f"{c} verisi yok."
            df[c] = pd.to_numeric(df[c], errors="coerce")

        if len(df) < max(30, atr_period + atr_base_period + rvol_base_period + min_history // 2):
            return None, f"Dinamik eşik için yetersiz tarihçe ({len(df)} bar)."

        h = df["High"]
        l = df["Low"]
        c = df["Close"]
        v = df["Volume"].replace([np.inf, -np.inf], np.nan)

        if not isinstance(v, pd.Series) or v.dropna().empty:
            return None, "Hacim verisi yok; RVOL üretilemedi."

        prev_close = c.shift(1)
        tr = pd.concat(
            [h - l, (h - prev_close).abs(), (l - prev_close).abs()],
            axis=1,
        ).max(axis=1)

        atr = tr.rolling(atr_period, min_periods=atr_period).mean()

        # Hem mevcut ATR oranının hem de tarihsel ATR dağılımının
        # referansı ilgili barın kendisini dışarıda bırakır.
        atr_baseline = atr.shift(1).rolling(atr_base_period, min_periods=atr_base_period).mean()
        atr_ratio_series = atr / (atr_baseline + 1e-12)

        last_atr_ratio = atr_ratio_series.iloc[-1]
        if not np.isfinite(last_atr_ratio) or last_atr_ratio <= 0:
            return None, "ATR dinamik referansı hesaplanamadı."

        # Gerçek RVOL: current volume / önceki 20 barın ortalaması.
        rvol_baseline = v.shift(1).rolling(
            rvol_base_period,
            min_periods=rvol_base_period,
        ).mean()
        rvol_series = v / (rvol_baseline + 1e-12)
        last_rvol = rvol_series.iloc[-1]

        if not np.isfinite(last_rvol) or last_rvol <= 0:
            return None, "Gerçek RVOL hesaplanamadı."

        # Threshold dağılımında current bar kesinlikle yok.
        atr_history = atr_ratio_series.iloc[:-1].replace([np.inf, -np.inf], np.nan).dropna()
        rvol_history = rvol_series.iloc[:-1].replace([np.inf, -np.inf], np.nan).dropna()

        atr_history = atr_history.tail(window)
        rvol_history = rvol_history[rvol_history > 0].tail(window)

        if len(atr_history) < min_history or len(rvol_history) < min_history:
            return None, (
                f"Dinamik eşik için yeterli tarihçe yok "
                f"(ATR {len(atr_history)}/{min_history}, RVOL {len(rvol_history)}/{min_history})."
            )

        atr_low = float(np.quantile(
            atr_history.to_numpy(dtype=float),
            float(cfg["atr_low_percentile"]),
        ))
        atr_high = float(np.quantile(
            atr_history.to_numpy(dtype=float),
            float(cfg["atr_high_percentile"]),
        ))
        rvol_low = float(np.quantile(
            rvol_history.to_numpy(dtype=float),
            float(cfg["rvol_illiquid_percentile"]),
        ))
        rvol_climax = float(np.quantile(
            rvol_history.to_numpy(dtype=float),
            float(cfg["rvol_climax_percentile"]),
        ))

        # Yüzdelik konum, ham 0.50x / 3.20x gibi evrensel rakamlardan
        # bağımsızdır ve aynı varlığın kendi son rejimine göre değişir.
        atr_rank = float((atr_history <= float(last_atr_ratio)).mean())
        rvol_rank = float((rvol_history <= float(last_rvol)).mean())

        rvol_strong = float(np.quantile(
            rvol_history.to_numpy(dtype=float),
            float(cfg["rvol_strong_percentile"]),
        ))

        return {
            "atr_ratio": float(last_atr_ratio),
            "rvol": float(last_rvol),
            "atr_low": atr_low,
            "atr_high": atr_high,
            "rvol_low": rvol_low,
            "rvol_strong": rvol_strong,
            "rvol_climax": rvol_climax,
            "atr_rank": atr_rank,
            "rvol_rank": rvol_rank,
            "atr_history_n": int(len(atr_history)),
            "rvol_history_n": int(len(rvol_history)),
        }, None

    @staticmethod
    def _publish_dynamic_entry_thresholds(profile):
        """
        Gatekeeper dosyasına dokunmadan onun uyumluluk eşiklerini de
        o an değerlendirilen varlığın gerçek dağılımına günceller.

        Böylece gatekeeper içindeki volume_supports / volatility_supports
        kontrolleri de sabit 1.25x / 0.65x / 2.20x vb. değerlerle değil,
        aynı 150-bar dağılımından türetilen sınırlarla çalışır.
        """
        try:
            import config
            dynamic_values = {
                "vol_shock_high": float(profile["atr_high"]),
                "vol_shock_low": float(profile["atr_low"]),
                "rvol_strong_min": float(profile["rvol_strong"]),
                "rvol_climax_shock": float(profile["rvol_climax"]),
                "rvol_illiquid": float(profile["rvol_low"]),
            }
            config.ENTRY_GATES_CONFIG.update(dynamic_values)
            config.ENTRY_FILTER_CONFIG.update(dynamic_values)
        except Exception:
            # Dynamic entry gate itself remains authoritative; this bridge is
            # only for gatekeeper compatibility and must never cause a crash.
            pass

    @staticmethod
    def evaluate_trade_entry_gate(df_1h, asset_key="SPX"):
        """
        EXECUTION_GATE: yalnızca gerçek/fresh veri + dağılım-temelli dinamik ATR/RVOL.

        Artık ham piyasa seviyesi için sabit 0.65x / 2.20x / 0.50x / 3.20x
        veto eşikleri kullanılmaz. Eşikler her varlığın son 150 barındaki
        gerçek ATR/RVOL dağılımından türetilir.
        """
        if df_1h is None or not isinstance(df_1h, pd.DataFrame) or df_1h.empty:
            return False, "İşleme Giriş Önerilmez: Gerçek piyasa verisi yok.", 0.0, 0.0

        attrs = getattr(df_1h, "attrs", {}) or {}
        if not attrs.get("is_real", False) or attrs.get("source_type") != "DIRECT":
            return False, "İşleme Giriş Önerilmez: Kaynak DIRECT/gerçek değil.", 0.0, 0.0
        if attrs.get("status") != "LIVE" or attrs.get("execution_eligible") is not True:
            return False, "İşleme Giriş Önerilmez: Veri LIVE/işlem uygunluğunda değil.", 0.0, 0.0

        profile, profile_error = RobustQuantProcessor._adaptive_entry_profile(df_1h)
        if profile is None:
            return False, f"İşleme Giriş Önerilmez: {profile_error}", 0.0, 0.0

        RobustQuantProcessor._publish_dynamic_entry_thresholds(profile)

        atr_ratio = round(profile["atr_ratio"], 2)
        rvol = round(profile["rvol"], 2)
        atr_rank_pct = profile["atr_rank"] * 100.0
        rvol_rank_pct = profile["rvol_rank"] * 100.0

        # Aynı mantıksal veto rolleri korunur; fakat sınırlar her zaman
        # mevcut varlığın kendi dağılımından gelir.
        if profile["atr_ratio"] > profile["atr_high"]:
            return (
                False,
                f"İşleme Giriş Önerilmez: Dinamik yüksek volatilite "
                f"(ATR {atr_ratio:.2f}x | dağılım P{atr_rank_pct:.0f}; "
                f"P95={profile['atr_high']:.2f}x).",
                atr_ratio,
                rvol,
            )

        if profile["atr_ratio"] < profile["atr_low"]:
            return (
                False,
                f"İşleme Giriş Önerilmez: Dinamik düşük volatilite "
                f"(ATR {atr_ratio:.2f}x | dağılım P{atr_rank_pct:.0f}; "
                f"P05={profile['atr_low']:.2f}x).",
                atr_ratio,
                rvol,
            )

        if profile["rvol"] > profile["rvol_climax"]:
            return (
                False,
                f"İşleme Giriş Önerilmez: Dinamik hacim climax "
                f"(RVOL {rvol:.2f}x | dağılım P{rvol_rank_pct:.0f}; "
                f"P99={profile['rvol_climax']:.2f}x).",
                atr_ratio,
                rvol,
            )

        if profile["rvol"] < profile["rvol_low"]:
            return (
                False,
                f"İşleme Giriş Önerilmez: Dinamik düşük likidite "
                f"(RVOL {rvol:.2f}x | dağılım P{rvol_rank_pct:.0f}; "
                f"P05={profile['rvol_low']:.2f}x).",
                atr_ratio,
                rvol,
            )

        return (
            True,
            f"İşleme Giriş Uygun: LIVE/DIRECT | "
            f"ATR {atr_ratio:.2f}x (P{atr_rank_pct:.0f}) | "
            f"RVOL {rvol:.2f}x (P{rvol_rank_pct:.0f}) | "
            f"150 bar dinamik eşik.",
            atr_ratio,
            rvol,
        )

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
        # BUGFIX: test the denominator frame itself. The previous implementation
        # checked df_num.columns, which could silently select df_denom.iloc[:, 0]
        # (Open) instead of denominator.Close on normal OHLCV frames.
        s2 = df_denom["Close"] if "Close" in df_denom.columns else df_denom.iloc[:, 0]
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
