"""
Karar Özeti (v15.1) — arayüzün en üstündeki tek bakışlık tablo
================================================================
Her varlık için: Giriş önerilir / önerilmez · Kısa vade yönü · Uzun vade
yönü · önerilen stop (her ufuk için). Sadece yayınlanmış karardan okur;
karar mantığını değiştirmez. Bu sistem bir al-sat botu değildir: tablo bir
yön ve giriş-zamanlaması analizidir.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from stop_levels import long_side, short_side

_ARROW = {1: "🟢", -1: "🔴", 0: "⚪"}


def short_label(v: Dict[str, Any]) -> str:
    lbl = str(v.get("current_direction") or "⚪ VERİ YETERSİZ")
    return re.sub(r"\s*\([^)]*%[^)]*\)", "", lbl).strip()


def long_label(v: Dict[str, Any]) -> str:
    verdict = str(v.get("verdict") or "NÖTR (BEKLE)")
    if "KRİZ" in verdict:
        return "⛔ KRİZ KİLİDİ"
    side = long_side(v)
    word = {1: "AL", -1: "SAT"}.get(side, "NÖTR")
    strong = "GÜÇLÜ " if "GÜÇLÜ" in verdict else ""
    out = f"{_ARROW[side]} {strong}{word}"
    if side and "NOT_PROVEN" in str(v.get("learned_model_status", "")):
        out += " · kanıtsız"
    return out


def entry_reason_short(v: Dict[str, Any]) -> str:
    r = str(v.get("entry_reason") or "")
    if "Kanıt yok" in r or "KANITSIZ" in str(v.get("entry_status", "")):
        return "model kanıtı yok (t < 2)"
    if "KRİZ" in str(v.get("verdict", "")) or "Kriz" in r:
        return "sistemik kriz kilidi"
    if "confluence" in r or "zaman dilim" in r.lower():
        return "zaman dilimleri yönle uyumsuz"
    if "gama kapısı" in r:
        return "gama duvarına çok yakın"
    if "volatilite" in r.lower():
        return "volatilite aşırı / ölü"
    if "likidite" in r.lower() or "RVOL" in r:
        return "hacim yetersiz"
    if "veri" in r.lower():
        return "veri yetersiz"
    return (r.split("|")[0].split(":")[-1].strip()[:60]) or "koşullar sağlanmadı"


def entry_label(v: Dict[str, Any]) -> str:
    if long_side(v) == 0 and short_side(v) == 0:
        return "⚪ Yön yok — giriş yok"
    if v.get("entry_allowed"):
        return "✅ Giriş önerilir"
    return f"⛔ Önerilmez · {entry_reason_short(v)}"


def timing_label(v: Dict[str, Any]) -> str:
    g = v.get("entry_grade")
    if g in (None, "", "-", "N/A"):
        return "—"
    txt = {"A": "A · tüm zaman dilimleri yönle aynı", "B": "B · tetik döndü, üst zaman dilimi nötr",
           "C": "C · tetik yok / ters"}.get(str(g), str(g))
    return txt


def stop_label(s: Optional[Dict[str, Any]], price_digits: int = 2) -> str:
    if not s:
        return "—"
    return (f"{s['stop']:,.{price_digits}f} ({-s['side'] * s['distance_pct']:+.2f}% · "
            f"{s['atr_1h_mult']:.1f}×ATR)")


def _digits(price: Optional[float]) -> int:
    if not price:
        return 2
    return 0 if price > 5000 else 1 if price > 500 else 2


def build_rows(verdicts: Dict[str, Dict[str, Any]], order: List[str]) -> List[Dict[str, str]]:
    rows = []
    for k in order:
        v = verdicts.get(k) or {}
        st = v.get("stop_suggestion") or {}
        price = ((v.get("market_structure") or {}).get("levels") or {}).get("price")
        dg = _digits(price)
        rows.append({
            "Varlık": k,
            "Giriş": entry_label(v),
            "Kısa vade (1-4 saat)": short_label(v),
            "Uzun vade (24 saat-1 hafta)": long_label(v),
            "Stop · kısa vade": stop_label(st.get("kisa"), dg),
            "Stop · uzun vade": stop_label(st.get("uzun"), dg),
            "Zamanlama": timing_label(v),
        })
    return rows


def stop_basis_lines(verdicts: Dict[str, Dict[str, Any]], order: List[str]) -> List[str]:
    out = []
    for k in order:
        st = (verdicts.get(k) or {}).get("stop_suggestion") or {}
        parts = [f"{s['label'].split(' (')[0]}: {s['basis']}" for s in (st.get("kisa"), st.get("uzun")) if s]
        if parts:
            out.append(f"**{k}** — " + " · ".join(parts))
    return out
