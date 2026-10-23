"""
Şok Dedektörü (v16.6) — haberi okumadan, fiyatlardan şok tespiti
================================================================
Bir haber şoku önce fiyatlarda görünür. Bu modül 11 göstergenin 5 dakikalık
verisinde ani hareketleri ölçer:
  ES, NQ, altın, gümüş, BTC, ETH, VIX, dolar endeksi (DXY), USDJPY,
  ABD 10 yıllık faiz (TNX), petrol (CL).

Ölçü: 15 dakikalık ve 60 dakikalık getiri / o göstergenin NORMAL oynaklığı
(medyan tabanlı σ, son 5 gün). |z15| ≥ 5 veya |z60| ≥ 4 → şok.
Genişlik: aynı 30 dakikada kaç gösterge şok verdi. ≥ 3 → piyasa geneli şok.
Desen (işaretlerden): risk-off, risk-on, dolar şoku, faiz şoku, petrol şoku,
kriptoya özgü.

Etki: şok sonrası 4 saat "şok durumu". Oynaklık kümelenir; bu süre içinde
aralık ve stoplar o anki gün içi oynaklık oranıyla (√ oranı, 1.0–2.0)
genişletilir ve giriş riski 🔴 gösterilir.

Kendini ölçer: her şok shock_ledger.csv dosyasına yazılır; 4 saat sonra
notlanır (devam mı / geri dönüş mü, sonraki hareket büyüklüğü). Önceden
kayıtlı hipotez: RESEARCH_LOG #11.

Sınır: motor saatte bir çalışır. Şok en geç ~1 saat sonra görünür.
"""
from __future__ import annotations

import math
import os
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from system_clock import now_utc

PANEL = {"ES": "ES=F", "NQ": "NQ=F", "GC": "GC=F", "SI": "SI=F", "BTC": "BTC-USD", "ETH": "ETH-USD",
         "VIX": "^VIX", "DXY": "DX-Y.NYB", "USDJPY": "JPY=X", "TNX": "^TNX", "CL": "CL=F",
         "DAX": "^GDAXI", "N225": "^N225", "HSI": "^HSI", "EEM": "EEM", "HYG": "HYG"}
REGION = {"DAX": "Avrupa", "N225": "Japonya", "HSI": "Hong Kong/Çin", "EEM": "Gelişen piyasalar",
          "ES": "ABD", "NQ": "ABD", "HYG": "ABD kredi"}
ASSET_OF = {"ES": "SPX", "NQ": "NQ", "GC": "XAU", "SI": "XAG", "BTC": "BTC", "ETH": "ETH"}
NAME_TR = {"ES": "S&P vadeli", "NQ": "Nasdaq vadeli", "GC": "Altın", "SI": "Gümüş", "BTC": "BTC", "ETH": "ETH",
           "VIX": "VIX", "DXY": "Dolar endeksi", "USDJPY": "USDJPY", "TNX": "ABD 10y faiz", "CL": "Petrol",
           "DAX": "DAX", "N225": "Nikkei", "HSI": "Hang Seng", "EEM": "Gelişen piyasalar", "HYG": "Yüksek getirili tahvil"}
Z15, Z60, BREADTH = 5.0, 4.0, 3
ACTIVE_H = 4
LEDGER = "shock_ledger.csv"


def fetch_panel(have: Optional[Dict[str, pd.DataFrame]] = None, period: str = "5d") -> Dict[str, pd.DataFrame]:
    """5 dakikalık panel. Motorun zaten indirdiği varlık verisi yeniden kullanılır."""
    out: Dict[str, pd.DataFrame] = {}
    have = have or {}
    for k, a in ASSET_OF.items():
        if isinstance(have.get(a), pd.DataFrame) and not have[a].empty:
            out[k] = have[a]
    missing = [k for k in PANEL if k not in out]
    if missing:
        try:
            import market_structure as MS
            for k in missing:
                d = MS.fetch_5m(PANEL[k], period=period)
                if d is not None:
                    out[k] = d
        except Exception:
            pass
    return out


def scan(df: pd.DataFrame, now: pd.Timestamp, lookback_h: float = ACTIVE_H) -> Optional[Dict[str, Any]]:
    """Son `lookback_h` saatteki en büyük 15dk / 60dk hareket (z) ve şu anki gün içi oynaklık oranı."""
    try:
        c = pd.to_numeric(df["Close"], errors="coerce").dropna()
        c.index = pd.to_datetime(c.index, utc=True)
        c = c[c.index <= now].sort_index()
        r = np.log(c / c.shift(1)).dropna()
        r = r[r != 0] if (r == 0).mean() > 0.5 else r        # kapalı seans düz barlarını ayıkla
        if len(r) < 60:                                      # TNX gibi sadece nakit seansta işleyenler için
            return None
        sig = float(r.abs().median() / 0.6745)
        if sig <= 0:
            return None
        recent = r[r.index > now - pd.Timedelta(hours=lookback_h)]
        if recent.empty:
            return None
        z15 = (r.rolling(3).sum() / (sig * math.sqrt(3)))[recent.index]
        z60 = (r.rolling(12).sum() / (sig * math.sqrt(12)))[recent.index]
        i15, i60 = z15.abs().idxmax(), z60.abs().idxmax()
        last12 = r.tail(12)
        vol_now = float(last12.abs().median() / 0.6745) / sig if len(last12) >= 6 else 1.0
        return {"z15": round(float(z15[i15]), 2), "t15": i15.isoformat(),
                "z60": round(float(z60[i60]), 2), "t60": i60.isoformat(),
                "vol_now_ratio": round(vol_now, 2), "price": float(c.iloc[-1])}
    except Exception:
        return None


def classify(hits: Dict[str, Dict[str, Any]]) -> str:
    s = {k: (1 if (h["z15"] if abs(h["z15"]) >= abs(h["z60"]) else h["z60"]) > 0 else -1) for k, h in hits.items()}
    eq_down = s.get("ES", 0) < 0 or s.get("NQ", 0) < 0
    eq_up = s.get("ES", 0) > 0 or s.get("NQ", 0) > 0
    glob = [k for k in ("DAX", "N225", "HSI", "EEM") if k in s]
    if glob and "DXY" not in s:
        d = sum(s[k] for k in glob)
        if d < 0:
            return "küresel hisse şoku ↓ (dolar dışı)"
        if d > 0:
            return "küresel hisse şoku ↑ (dolar dışı)"
    if s.get("HYG", 0) < 0 and eq_down:
        return "kredi şoku (tahvil ↓, hisse ↓)"
    if s.get("CL", 0) > 0 and s.get("GC", 0) > 0 and not eq_up:
        return "jeopolitik desen (petrol ↑, altın ↑)"
    if eq_down and (s.get("VIX", 0) > 0 or s.get("USDJPY", 0) < 0 or s.get("GC", 0) > 0):
        return "risk-off (hisse ↓, korku ↑)"
    if eq_up and (s.get("VIX", 0) < 0 or s.get("USDJPY", 0) > 0):
        return "risk-on (hisse ↑, korku ↓)"
    if "DXY" in s and ("GC" in s or "SI" in s) and s["DXY"] * s.get("GC", s.get("SI", 0)) < 0:
        return "dolar şoku" + (" (dolar ↑)" if s["DXY"] > 0 else " (dolar ↓)")
    if "TNX" in s:
        return "faiz şoku" + (" (faiz ↑)" if s["TNX"] > 0 else " (faiz ↓)")
    if "CL" in s and len(s) <= 2:
        return "petrol şoku"
    if set(s) <= {"BTC", "ETH"}:
        return "kriptoya özgü"
    return "karışık"


def detect(panel: Dict[str, pd.DataFrame], now: Any = None) -> Dict[str, Any]:
    now = pd.Timestamp(now or now_utc())
    now = now.tz_localize("UTC") if now.tzinfo is None else now.tz_convert("UTC")
    scans = {k: s for k, df in panel.items() if (s := scan(df, now))}
    hits = {k: s for k, s in scans.items() if abs(s["z15"]) >= Z15 or abs(s["z60"]) >= Z60}
    if not hits:
        return {"active": False, "scanned": sorted(scans), "n_panel": len(panel)}
    t_hit = {k: pd.Timestamp(h["t15"] if abs(h["z15"]) / Z15 >= abs(h["z60"]) / Z60 else h["t60"]) for k, h in hits.items()}
    t0 = max(t_hit.values())
    cluster = {k: h for k, h in hits.items() if abs((t_hit[k] - t0).total_seconds()) <= 1800}
    broad = len(cluster) >= BREADTH
    affected = sorted(set(ASSET_OF.values())) if broad else sorted({ASSET_OF[k] for k in hits if k in ASSET_OF})
    if not broad and ({"SPX", "NQ"} & set(affected)):
        affected = sorted(set(affected) | {"SPX", "NQ"})
    pattern = classify(cluster if broad else hits)
    first = min(cluster, key=lambda k: t_hit[k])
    origin = REGION.get(first, NAME_TR.get(first, first))
    desc = ", ".join(f"{NAME_TR[k]} {'↑' if (h['z15'] if abs(h['z15']) >= abs(h['z60']) else h['z60']) > 0 else '↓'}"
                     f"{max(abs(h['z15']), abs(h['z60'])):.0f}σ" for k, h in sorted(hits.items(), key=lambda x: -max(abs(x[1]['z15']), abs(x[1]['z60']))))
    return {"active": True, "broad": broad, "pattern": pattern, "origin": origin, "affected": affected, "time": t0.isoformat(),
            "hits": hits, "desc": desc, "n_panel": len(panel),
            "vol_now": {ASSET_OF[k]: s["vol_now_ratio"] for k, s in scans.items() if k in ASSET_OF}}


# ---------------------------------------------------------------------------
# Defter: her şok kaydedilir, 4 saat sonra notlanır
# ---------------------------------------------------------------------------
COLS = ["t_shock", "inst", "asset", "z", "pattern", "broad", "price", "ret_4h", "mag_4h", "graded"]


def _load(path: str) -> pd.DataFrame:
    if os.path.exists(path):
        try:
            d = pd.read_csv(path)
            for c in COLS:
                if c not in d.columns:
                    d[c] = np.nan
            return d
        except Exception:
            pass
    return pd.DataFrame(columns=COLS)


def ledger_cycle(shock: Dict[str, Any], panel: Dict[str, pd.DataFrame], path: str = LEDGER, now: Any = None) -> Dict[str, Any]:
    now = pd.Timestamp(now or now_utc())
    now = now.tz_localize("UTC") if now.tzinfo is None else now.tz_convert("UTC")
    d = _load(path)
    for k, h in (shock.get("hits") or {}).items():
        t = h["t15"] if abs(h["z15"]) / Z15 >= abs(h["z60"]) / Z60 else h["t60"]
        if ((d["t_shock"] == t) & (d["inst"] == k)).any():
            continue
        z = h["z15"] if abs(h["z15"]) / Z15 >= abs(h["z60"]) / Z60 else h["z60"]
        df = panel.get(k)
        p = None
        if isinstance(df, pd.DataFrame):
            c = pd.to_numeric(df["Close"], errors="coerce").dropna()
            c.index = pd.to_datetime(c.index, utc=True)
            c = c[c.index <= pd.Timestamp(t)]
            p = float(c.iloc[-1]) if len(c) else None
        d.loc[len(d)] = {"t_shock": t, "inst": k, "asset": ASSET_OF.get(k, ""), "z": z, "pattern": shock.get("pattern"),
                         "broad": bool(shock.get("broad")), "price": p, "ret_4h": np.nan, "mag_4h": np.nan, "graded": 0}
    for i, row in d[d["graded"].fillna(0) == 0].iterrows():
        t1 = pd.Timestamp(row["t_shock"]) + pd.Timedelta(hours=4)
        df = panel.get(row["inst"])
        if now < t1 or not isinstance(df, pd.DataFrame) or not row["price"] == row["price"]:
            if now > t1 + pd.Timedelta(days=3):
                d.at[i, "graded"] = -1
            continue
        c = pd.to_numeric(df["Close"], errors="coerce").dropna()
        c.index = pd.to_datetime(c.index, utc=True)
        w = c[(c.index > pd.Timestamp(row["t_shock"])) & (c.index <= t1)]
        r_all = np.log(c / c.shift(1)).dropna()
        sig = float(r_all.abs().median() / 0.6745) * math.sqrt(48)
        if len(w) < 6 or sig <= 0:
            continue
        ret = float(np.log(w.iloc[-1] / float(row["price"])))
        d.at[i, "ret_4h"] = ret
        d.at[i, "mag_4h"] = abs(ret) / sig
        d.at[i, "graded"] = 1
    d.tail(5000).to_csv(path, index=False)
    g = d[d["graded"] == 1]
    if g.empty:
        return {"n": 0, "n_open": int((d["graded"] == 0).sum())}
    cont = (np.sign(g["ret_4h"]) == np.sign(g["z"])).astype(float)
    return {"n": int(len(g)), "n_open": int((d["graded"] == 0).sum()),
            "continuation": round(float(cont.mean()), 3),
            "mag_4h_mean": round(float(g["mag_4h"].mean()), 2),
            "note": "devam > %50 ise şok yönü sürer; mag > 1 ise oynaklık 4 saat yüksek kalır"}


def run(intraday: Optional[Dict[str, pd.DataFrame]] = None, now: Any = None, path: str = LEDGER) -> Dict[str, Any]:
    panel = fetch_panel(intraday)
    shock = detect(panel, now)
    try:
        shock["ledger"] = ledger_cycle(shock, panel, path=path, now=now)
    except Exception as exc:
        shock["ledger"] = {"error": str(exc)}
    n_scan = len(shock.get("scanned") or []) if not shock.get("active") else len(panel)
    if len(panel) < 8 or n_scan < len(PANEL) - 4:   # Asya/Avrupa endeksleri kendi seansları dışında seyrek olabilir
        shock["error"] = f"şok paneli eksik: {len(panel)}/{len(PANEL)} indirildi, {n_scan} tarandı"
    return shock


def factor(shock: Dict[str, Any], asset: str) -> float:
    """Şok durumunda aralık/stop çarpanı: √(gün içi oynaklık oranı), 1.0–2.0."""
    if not shock.get("active") or asset not in (shock.get("affected") or []):
        return 1.0
    vr = float((shock.get("vol_now") or {}).get(asset, 1.0) or 1.0)
    return float(np.clip(math.sqrt(max(vr, 1.0)), 1.0, 2.0))


def note(shock: Dict[str, Any], asset: str) -> str:
    if not shock.get("active") or asset not in (shock.get("affected") or []):
        return ""
    t = pd.Timestamp(shock["time"]).tz_convert("Europe/Istanbul").strftime("%H:%M")
    scope = "piyasa geneli" if shock.get("broad") else "yerel"
    return f" · ⚡ Şok {t} TSİ ({scope}, {shock['pattern']}, kaynak: {shock.get('origin', '?')}): {shock['desc']}"
