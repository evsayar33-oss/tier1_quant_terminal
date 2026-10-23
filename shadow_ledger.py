"""
Gölge Defter (shadow-v1) — kilit döneminde test edilecek fikirler, KARARA KARIŞMADAN
===================================================================================
Arayüz ve karar mantığı değişmez (mantık kilidi, LOGIC_VERSION aynı). Bu defter
yalnız üç hipotezin ham verisini saatte bir kaydeder; 4 saat / seans sonu /
24 saat sonra fiyatla doldurur. Değerlendirme: shadow_eval.py (RESEARCH_LOG #13-#15).

H13 Charm/vanna sürüklenmesi (SPX, NQ): dealer charm/vanna akışının işareti,
    sonraki 4 saatin ve seans sonuna (16:00 ET) kadarki getirinin işaretini
    tahmin eder mi? Özellikle 11:00 ET sonrası kayıtlarda.
H14 Duvar ve pin (SPX, NQ, BTC, ETH): fiyat 24 saat içinde call/put duvarına
    değerse duvar tutar mı (kapanış duvarın içinde kalır mı)? 0DTE pin'e
    uzaklık seans sonunda kayıt anına göre küçülür mü (mıknatıs)?
ŞAMPİYON / MEYDAN OKUYAN: her saat iki karar birlikte kaydedilir.
    champ_*: ekrandaki mevcut sistem (kısa vade yönü, kısa vade stopu AL/SAT).
    chal_*:  yeni fikirler eklenmiş BİRLEŞİK sistem —
             yön: mevcut yön; mevcut sistem "yön yok" derken SPX/NQ'da ET 11-15
                  arasında charm akışı güçlüyse charm yönü;
             stop: aynı stop algoritması, dayanak adaylarına önceki seansın
                  POC/VAH/VAL seviyeleri eklenmiş hali.
    30 gün sonra aynı saatlerde ikisi aynı fiyat hareketine karşı karşılaştırılır.
H15 Hacim profili (6 varlık): önceki seansın POC / değer alanı (VAH, VAL)
    seviyeleri, aynı uzaklıktaki rastgele seviyelere göre daha çok "dokun ve
    dön" üretir mi? (stop dayanağı adayı)
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from system_clock import now_utc

SHADOW_VERSION = "shadow-v1"
LEDGER = "shadow_ledger.csv"
MAX_ROWS = 60000
ET = ZoneInfo("America/New_York")
COLS = ["ts", "shadow", "asset", "price", "et_hour",
        "charm_1d", "charm_0dte", "vanna_ivdown", "net_gex", "regime",
        "call_wall", "put_wall", "call_wall_0dte", "put_wall_0dte", "pin_0dte", "flip",
        "poc", "vah", "val", "vp_session",
        "champ_lean", "chal_lean", "champ_stop_long", "chal_stop_long", "champ_stop_short", "chal_stop_short",
        "ret_4h", "ret_close", "close_et16", "hi_4h", "lo_4h", "hi_24h", "lo_24h", "close_24h", "graded"]
CHARM_MIN_USD = 1e9          # "güçlü" charm akışı eşiği (SPX/NQ, dolar)


def volume_profile(df5: Any, now: pd.Timestamp, bins: int = 60, va: float = 0.70) -> Optional[Dict[str, Any]]:
    """Önceki tamamlanmış ET gününün 5 dk barlarından hacim profili: POC, VAH, VAL."""
    try:
        d = df5.copy()
        d.index = pd.to_datetime(d.index, utc=True)
        d = d[d.index < now]
        day = d.index.tz_convert(ET).normalize()
        today = now.tz_convert(ET).normalize()
        prev = sorted(set(day[day < today]))
        if not prev:
            return None
        s = d[day == prev[-1]]
        vol = pd.to_numeric(s.get("Volume"), errors="coerce").fillna(0.0)
        if len(s) < 24 or vol.sum() <= 0:
            return None
        tp = (pd.to_numeric(s["High"]) + pd.to_numeric(s["Low"]) + pd.to_numeric(s["Close"])) / 3.0
        edges = np.linspace(float(s["Low"].min()), float(s["High"].max()), bins + 1)
        h, _ = np.histogram(tp, bins=edges, weights=vol)
        mid = (edges[:-1] + edges[1:]) / 2
        i = int(np.argmax(h))
        lo, hi, acc, tot = i, i, h[i], h.sum()
        while acc < va * tot and (lo > 0 or hi < bins - 1):
            left = h[lo - 1] if lo > 0 else -1
            right = h[hi + 1] if hi < bins - 1 else -1
            if right >= left:
                hi += 1
                acc += h[hi]
            else:
                lo -= 1
                acc += h[lo]
        return {"poc": float(mid[i]), "vah": float(edges[hi + 1]), "val": float(edges[lo]),
                "session": str(prev[-1].date())}
    except Exception:
        return None


def challenger(asset: str, v: Dict[str, Any], ctx: Dict[str, Any], g: Dict[str, Any],
               vp: Optional[Dict[str, Any]], et_hour: int, price: float) -> Dict[str, Any]:
    import stop_levels as SL
    champ = 0 if ((v.get("market_structure") or ctx or {}).get("session") or {}).get("phase") == "Kapalı" \
        else SL.evidence_short_side(v)
    chal = champ
    charm = g.get("charm_flow_1d_usd")
    if champ == 0 and asset in ("SPX", "NQ") and 11 <= et_hour < 15 and charm and abs(float(charm)) >= CHARM_MIN_USD:
        chal = 1 if float(charm) > 0 else -1
    lv = (ctx or {}).get("levels") or ((v.get("market_structure") or {}).get("levels")) or {}
    aug = dict(lv, levels=list(lv.get("levels") or []))
    if vp:
        aug["levels"] += [{"price": vp["val"], "kind": "SWL", "label": "Değer alanı dibi (VAL)"},
                          {"price": vp["vah"], "kind": "SWH", "label": "Değer alanı tepesi (VAH)"},
                          {"price": vp["poc"], "kind": "VWAP", "label": "POC"}]
    args = lambda side, levels: SL.suggest_stop(side, "kisa", price, (ctx or {}).get("atr_1h"), (ctx or {}).get("atr_1d"),
                                                g.get("expected_move_1d"), levels, g or None, 1.0,
                                                (ctx or {}).get("move_factor", 1.0))
    out = {"champ_lean": champ, "chal_lean": chal}
    for side, nm in ((1, "long"), (-1, "short")):
        a, b = args(side, lv), args(side, aug)
        out[f"champ_stop_{nm}"] = a["stop"] if a else np.nan
        out[f"chal_stop_{nm}"] = b["stop"] if b else np.nan
    return out


def _load(path: str) -> pd.DataFrame:
    if os.path.exists(path):
        try:
            d = pd.read_csv(path)
            for c in COLS:
                if c not in d.columns:
                    d[c] = np.nan
            return d[COLS]
        except Exception:
            pass
    return pd.DataFrame(columns=COLS)


def _series(df: Any) -> Optional[pd.DataFrame]:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return None
    d = df.copy()
    d.index = pd.to_datetime(d.index, utc=True)
    return d.sort_index()


def grade(d: pd.DataFrame, frames: Dict[str, pd.DataFrame], now: pd.Timestamp) -> int:
    n = 0
    for i, row in d[d["graded"].fillna(0) == 0].iterrows():
        t0 = pd.Timestamp(row["ts"])
        t0 = t0.tz_localize("UTC") if t0.tzinfo is None else t0
        if now < t0 + pd.Timedelta(hours=24):
            continue
        f = _series(frames.get(row["asset"]))
        if f is None:
            if now > t0 + pd.Timedelta(days=4):
                d.at[i, "graded"] = -1
            continue
        c = pd.to_numeric(f["Close"], errors="coerce")
        w = f[(f.index > t0) & (f.index <= t0 + pd.Timedelta(hours=24))]
        if len(w) < 4:
            if now > t0 + pd.Timedelta(days=4):
                d.at[i, "graded"] = -1
            continue
        p0 = float(row["price"])
        a4 = c[(c.index > t0) & (c.index <= t0 + pd.Timedelta(hours=4))]
        d.at[i, "ret_4h"] = float(np.log(a4.iloc[-1] / p0)) if len(a4) else np.nan
        w4 = f[(f.index > t0) & (f.index <= t0 + pd.Timedelta(hours=4))]
        if len(w4):
            d.at[i, "hi_4h"] = float(pd.to_numeric(w4["High"]).max())
            d.at[i, "lo_4h"] = float(pd.to_numeric(w4["Low"]).min())
        close16 = t0.tz_convert(ET).normalize() + pd.Timedelta(hours=16)
        cl = c[(c.index > t0) & (c.index <= close16.tz_convert("UTC"))]
        if len(cl) and close16.tz_convert("UTC") > t0:
            d.at[i, "close_et16"] = float(cl.iloc[-1])
            d.at[i, "ret_close"] = float(np.log(cl.iloc[-1] / p0))
        d.at[i, "hi_24h"] = float(pd.to_numeric(w["High"]).max())
        d.at[i, "lo_24h"] = float(pd.to_numeric(w["Low"]).min())
        d.at[i, "close_24h"] = float(pd.to_numeric(w["Close"]).iloc[-1])
        d.at[i, "graded"] = 1
        n += 1
    return n


def run_cycle(verdicts: Dict[str, Dict[str, Any]], snapshots: Dict[str, Any], frames: Dict[str, pd.DataFrame],
              intraday: Dict[str, pd.DataFrame], path: str = LEDGER, now: Any = None,
              contexts: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    now = pd.Timestamp(now or now_utc())
    now = now.tz_localize("UTC") if now.tzinfo is None else now.tz_convert("UTC")
    d = _load(path)
    n_graded = grade(d, frames, now)
    ts = now.floor("h").isoformat()
    added = 0
    for a, v in verdicts.items():
        if ((d["ts"] == ts) & (d["asset"] == a)).any():
            continue
        price = ((v.get("market_structure") or {}).get("levels") or {}).get("price")
        if not price:
            continue
        g = (snapshots or {}).get(a) or {}
        vp = volume_profile(intraday.get(a), now) if isinstance(intraday.get(a), pd.DataFrame) else None
        et_hour = int(now.tz_convert(ET).hour)
        try:
            cc = challenger(a, v, (contexts or {}).get(a) or {}, g, vp, et_hour, float(price))
        except Exception:
            cc = {}
        d.loc[len(d)] = {**{k: cc.get(k, np.nan) for k in ("champ_lean", "chal_lean", "champ_stop_long", "chal_stop_long",
                                                            "champ_stop_short", "chal_stop_short")},
            "ts": ts, "shadow": SHADOW_VERSION, "asset": a, "price": float(price),
            "et_hour": et_hour,
            "charm_1d": g.get("charm_flow_1d_usd"), "charm_0dte": g.get("charm_flow_0dte_usd"),
            "vanna_ivdown": g.get("vanna_flow_iv_down_1pt_usd"), "net_gex": g.get("net_gex_usd_1pct"),
            "regime": g.get("regime"), "call_wall": g.get("call_wall"), "put_wall": g.get("put_wall"),
            "call_wall_0dte": g.get("call_wall_0dte"), "put_wall_0dte": g.get("put_wall_0dte"),
            "pin_0dte": g.get("pin_0dte"), "flip": g.get("gamma_flip"),
            "poc": (vp or {}).get("poc"), "vah": (vp or {}).get("vah"), "val": (vp or {}).get("val"),
            "vp_session": (vp or {}).get("session"),
            "ret_4h": np.nan, "ret_close": np.nan, "close_et16": np.nan, "hi_4h": np.nan, "lo_4h": np.nan,
            "hi_24h": np.nan, "lo_24h": np.nan,
            "close_24h": np.nan, "graded": 0}
        added += 1
    d.tail(MAX_ROWS).to_csv(path, index=False)
    return {"shadow": SHADOW_VERSION, "added": added, "graded": n_graded,
            "rows": int(len(d)), "graded_total": int((d["graded"] == 1).sum())}
