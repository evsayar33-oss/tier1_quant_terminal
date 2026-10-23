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


def market_closed(v: Dict[str, Any]) -> bool:
    return ((v.get("market_structure") or {}).get("session") or {}).get("phase") == "Kapalı"


def short_label(v: Dict[str, Any]) -> str:
    if market_closed(v):
        return "⏸️ Piyasa kapalı"
    lbl = str(v.get("current_direction") or "⚪ VERİ YETERSİZ")
    return re.sub(r"\s*\([^)]*%[^)]*\)", "", lbl).strip()


def long_label(v: Dict[str, Any]) -> str:
    verdict = str(v.get("verdict") or "NÖTR (BEKLE)")
    if "KRİZ" in verdict:
        return "⛔ KRİZ KİLİDİ"
    rd = v.get("research_direction")
    if isinstance(rd, dict):
        from direction_research import RULE_TR
        word = {1: "AL", -1: "SAT"}.get(rd.get("side"), "BEKLE")
        return f"{_ARROW[rd.get('side', 0)]} {word} · kanıtlı ({RULE_TR.get(rd.get('rule'), rd.get('rule'))})"
    side = long_side(v)
    word = {1: "AL", -1: "SAT"}.get(side, "NÖTR")
    strong = "GÜÇLÜ " if "GÜÇLÜ" in verdict else ""
    out = f"{_ARROW[side]} {strong}{word}"
    if side and "NOT_PROVEN" in str(v.get("learned_model_status", "")):
        out += " · kanıtsız"
    b = v.get("base_rate")
    if isinstance(b, dict) and b.get("up") is not None:
        out += f" · taban: %{100 * b['up']:.0f} yükseliş ({b.get('horizon_d', 5)}g, 10 yıl)"
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
    if market_closed(v):
        return "⏸️ Piyasa kapalı — giriş yok"
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
            "Stop · kısa vade": "—" if market_closed(v) else stop_label(st.get("kisa"), dg),
            "Stop · uzun vade": stop_label(st.get("uzun"), dg),
            "Zamanlama": timing_label(v),
        })
    return rows


# ---------------------------------------------------------------------------
# Basit Özet — yeni başlayan biri için, teknik terim olmadan
# ---------------------------------------------------------------------------
def _sign(lbl: str) -> int:
    return 1 if "🟢" in lbl else -1 if "🔴" in lbl else 0


def simple_action(v: Dict[str, Any]) -> str:
    if market_closed(v):
        return "⏸️ Piyasa kapalı"
    if "KRİZ" in str(v.get("verdict", "")):
        return "⛔ Uzak dur — piyasada kriz sinyali var"
    if v.get("entry_allowed"):
        return "✅ Koşullar uygun"
    why = {"model kanıtı yok (t < 2)": "sinyal güvenilir değil",
           "zaman dilimleri yönle uyumsuz": "kısa ve uzun vade aynı yönü göstermiyor",
           "gama duvarına çok yakın": "fiyat güçlü bir engele çok yakın",
           "volatilite aşırı / ölü": "fiyat ya çok sert ya çok durgun",
           "hacim yetersiz": "işlem hacmi düşük",
           "veri yetersiz": "veri eksik"}.get(entry_reason_short(v), "koşullar oluşmadı")
    return f"✋ Bekle — {why}"


def simple_now(v: Dict[str, Any]) -> str:
    if market_closed(v):
        return "—"
    s = _sign(str(v.get("current_direction") or ""))
    return {1: "🟢 Son saatlerde yükseliyor", -1: "🔴 Son saatlerde düşüyor"}.get(s, "⚪ Yatay, belirgin yön yok")


def simple_week(v: Dict[str, Any]) -> str:
    rd = v.get("research_direction")
    if isinstance(rd, dict) and rd.get("side"):
        return ("🟢 Test edilmiş bir kural yükseliş diyor" if rd["side"] > 0
                else "🔴 Test edilmiş bir kural düşüş diyor")
    b = v.get("base_rate")
    if isinstance(b, dict) and b.get("up") is not None:
        n = round(10 * float(b["up"]))
        return f"🤷 Kesin bilinmez. Geçmişte 10 haftadan {n} tanesi yükselişle bitti"
    return "🤷 Kesin bilinmez"


def simple_calm(v: Dict[str, Any], gex: Optional[Dict[str, Any]] = None, asset: str = "") -> str:
    regime = str((v.get("dealer_gamma") or {}).get("regime") or "")
    mf = (gex or {}).get("move_factor") if asset in ("SPX", "NQ") else None
    extra = ""
    if mf and abs(float(mf) - 1.0) >= 0.05:
        extra = f" (normalden %{abs(100 * (float(mf) - 1)):.0f} {'büyük' if mf > 1 else 'küçük'} hareket beklenir)"
    if "NEGAT" in regime:
        return "🌪️ Hareketli — fiyat sert ve hızlı oynayabilir" + extra
    if "POZ" in regime:
        return "🧘 Sakin — büyük hareketler frenlenir" + extra
    try:
        r = float(v.get("atr_ratio"))
    except (TypeError, ValueError):
        return "—"
    return ("🌪️ Normalden hareketli" if r > 1.3 else "🧘 Normalden sakin" if r < 0.8 else "〰️ Normal") + extra


def simple_stop(v: Dict[str, Any]) -> str:
    st = v.get("stop_suggestion") or {}
    s = (None if market_closed(v) else st.get("kisa")) or st.get("uzun")
    if not s:
        return "—"
    price = ((v.get("market_structure") or {}).get("levels") or {}).get("price")
    lvl = f"{s['stop']:,.{_digits(price)}f}"
    if s["side"] > 0:
        return f"Yükseliş fikri {lvl} altında geçersiz (%{s['distance_pct']:.1f} aşağıda)"
    return f"Düşüş fikri {lvl} üstünde geçersiz (%{s['distance_pct']:.1f} yukarıda)"


def _lean(v: Dict[str, Any]) -> Dict[str, int]:
    rd = v.get("research_direction")
    b = v.get("base_rate") or {}
    hist = rd.get("side", 0) if isinstance(rd, dict) else (1 if (b.get("up") or 0.5) > 0.55 else -1 if (b.get("up") or 0.5) < 0.45 else 0)
    return {"now": 0 if market_closed(v) else short_side(v), "hist": hist}


def simple_today(v: Dict[str, Any]) -> str:
    if market_closed(v):
        return "⏸️ Piyasa kapalı"
    r = v.get("day_range") or {}
    now = _lean(v)["now"]
    tilt = {1: "🟢 hafif yukarı eğilim", -1: "🔴 hafif aşağı eğilim"}.get(now, "⚪ belirgin eğilim yok")
    if not r.get("move") or not r.get("price"):
        return tilt
    p, m, dg = r["price"], r["move"], _digits(r["price"])
    return (f"Büyük olasılıkla {p - m:,.{dg}f} – {p + m:,.{dg}f} arasında (±%{100 * m / p:.1f}) · {tilt}")


def simple_risk(v: Dict[str, Any]) -> str:
    if market_closed(v):
        return "—"
    if "KRİZ" in str(v.get("verdict", "")):
        return "🔴 Çok riskli — kriz sinyali"
    neg = "NEGAT" in str((v.get("dealer_gamma") or {}).get("regime") or "")
    l = _lean(v)
    mixed = l["now"] and l["hist"] and l["now"] != l["hist"]
    if v.get("entry_allowed") and not neg:
        return "🟢 Düşük risk — koşullar uygun"
    if neg or mixed:
        why = "fiyat sert oynayabilir" if neg else "sinyaller birbiriyle çelişiyor"
        return f"🔴 Riskli — {why}"
    return "🟡 Orta risk — net bir fırsat yok"


def simple_side(v: Dict[str, Any]) -> str:
    if market_closed(v):
        return "—"
    l = _lean(v)
    word = {1: "🟢 Yükseliş (AL) yönü", -1: "🔴 Düşüş (SAT) yönü"}
    if l["now"] and l["now"] == l["hist"]:
        return f"{word[l['now']]} — kısa vade ve geçmiş eğilim aynı"
    if l["now"] and l["hist"]:
        return f"⚖️ Çelişkili — kısa vade {'yükseliş' if l['now'] > 0 else 'düşüş'}, geçmiş eğilim {'yükseliş' if l['hist'] > 0 else 'düşüş'}. Girmemek daha iyi"
    if l["hist"]:
        return f"{word[l['hist']]} — sadece geçmiş eğilime göre (zayıf)"
    if l["now"]:
        return f"{word[l['now']]} — sadece kısa vadeye göre (zayıf)"
    return "⚪ Belirgin yön yok"


def simple_rows(verdicts: Dict[str, Dict[str, Any]], order: List[str],
                gex: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
    rows = []
    for k in order:
        v = verdicts.get(k) or {}
        rows.append({"Varlık": k,
                     "Şimdi ne yapmalı?": simple_action(v),
                     "Bugün fiyat ne yapabilir?": simple_today(v),
                     "Şimdi girmek riskli mi?": simple_risk(v),
                     "Girersen hangi yön daha iyi?": simple_side(v),
                     "Önümüzdeki hafta": simple_week(v),
                     "Piyasa sakin mi?": simple_calm(v, gex, k),
                     "Fikir nerede bozulur?": simple_stop(v)})
    return rows


SIMPLE_GUIDE = """
**Bu tablo nasıl okunur?**
- **Şimdi ne yapmalı?** — Sistem bütün kontrolleri yapar. Hepsi uygunsa ✅ yazar. Çoğu zaman ✋ Bekle yazar; bu normaldir. İyi fırsat az olur.
- **Bugün fiyat ne yapabilir?** — Opsiyon piyasasının fiyatladığı günlük aralıktır. Fiyat günlerin yaklaşık 2/3'ünde bu aralıkta kalır. Eğilim sadece son saatlerin yönüdür; zayıf bir bilgidir.
- **Şimdi girmek riskli mi?** — 🟢 düşük, 🟡 orta, 🔴 yüksek. Sert piyasa veya çelişen sinyaller riski yükseltir.
- **Girersen hangi yön daha iyi?** — Kısa vade ve geçmiş eğilim aynı yönü gösterirse o yön yazılır. Çelişirse "girmemek daha iyi" yazılır.
- **Önümüzdeki hafta** — Hiç kimse yönü kesin bilemez. Sistem bunu test etti ve kanıt bulamadı. Bu yüzden geçmişteki yükseliş sıklığını gösterir.
- **Piyasa sakin mi?** — Sistemin en güçlü bilgisi budur (15 yıllık veride kanıtlı). Hareketli piyasada küçük pozisyon ve geniş stop gerekir.
- **Fikir nerede bozulur?** — Fiyat bu seviyeyi geçerse fikriniz yanlıştır. Bu bir emir değil, risk sınırıdır.

⚠️ Bu tablo yatırım tavsiyesi değildir.
"""


def stop_basis_lines(verdicts: Dict[str, Dict[str, Any]], order: List[str]) -> List[str]:
    out = []
    for k in order:
        st = (verdicts.get(k) or {}).get("stop_suggestion") or {}
        parts = [f"{s['label'].split(' (')[0]}: {s['basis']}" for s in (st.get("kisa"), st.get("uzun")) if s]
        if parts:
            out.append(f"**{k}** — " + " · ".join(parts))
    return out
