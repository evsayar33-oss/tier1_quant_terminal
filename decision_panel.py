"""
Karar Özeti (v15.1) — arayüzün en üstündeki tek bakışlık tablo
================================================================
Her varlık için: Giriş önerilir / önerilmez · Kısa vade yönü · Uzun vade
yönü · önerilen stop (her ufuk için). Sadece yayınlanmış karardan okur;
karar mantığını değiştirmez. Bu sistem bir al-sat botu değildir: tablo bir
yön ve giriş-zamanlaması analizidir.
"""
from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional

from stop_levels import (Z_BASE, base_rate_side, evidence_long_side, evidence_short_side, long_side, model_proven,
                         short_side)

_ARROW = {1: "🟢", -1: "🔴", 0: "⚪"}


def market_closed(v: Dict[str, Any]) -> bool:
    return ((v.get("market_structure") or {}).get("session") or {}).get("phase") == "Kapalı"


def short_label(v: Dict[str, Any]) -> str:
    if market_closed(v):
        return "⏸️ Piyasa kapalı"
    lbl = str(v.get("current_direction") or "⚪ VERİ YETERSİZ")
    lbl = re.sub(r"\s*\([^)]*%[^)]*\)", "", lbl).strip()
    if model_proven(v) or "VERİ" in lbl:
        return lbl
    side = evidence_short_side(v)
    rm = v.get("recent_move") or {}
    tag = f" (son 4s %{rm['ret_pct']:+.2f})" if rm.get("ret_pct") is not None else " (fiyat)"
    if rm.get("pair") == "ayrışma":
        tag += " · eşinden ayrışıyor"
    out = {1: "🟢 YUKARI", -1: "🔴 AŞAĞI"}.get(side, "⚪ YATAY") + tag
    m = short_side(v)
    if m and m != side:
        out += f" · model {'YUKARI' if m > 0 else 'AŞAĞI'} diyor, kanıtsız"
    return out


def long_label(v: Dict[str, Any]) -> str:
    verdict = str(v.get("verdict") or "NÖTR (BEKLE)")
    if "KRİZ" in verdict:
        return "⛔ KRİZ KİLİDİ"
    sd = v.get("shock_direction")
    if isinstance(sd, dict) and sd.get("side"):
        return (f"{_ARROW[sd['side']]} {'AL' if sd['side'] > 0 else 'SAT'} · kanıtlı şok sonrası: {sd['name']} "
                f"({sd['event_date']}, {sd['h']}g, t={sd['t']:+.1f}, {sd['days_left']} gün kaldı)")
    rd = v.get("research_direction")
    if isinstance(rd, dict):
        from direction_research import RULE_TR
        word = {1: "AL", -1: "SAT"}.get(rd.get("side"), "BEKLE")
        return f"{_ARROW[rd.get('side', 0)]} {word} · kanıtlı ({RULE_TR.get(rd.get('rule'), rd.get('rule'))})"
    b = v.get("base_rate") if isinstance(v.get("base_rate"), dict) else {}
    if model_proven(v):
        side = long_side(v)
        out = f"{_ARROW[side]} {'GÜÇLÜ ' if 'GÜÇLÜ' in verdict else ''}{ {1: 'AL', -1: 'SAT'}.get(side, 'NÖTR') } · model kanıtlı"
    else:
        side = base_rate_side(b)
        out = {1: "🟢 AL eğilimi (geçmiş)", -1: "🔴 SAT eğilimi (geçmiş)"}.get(side, "⚪ NÖTR · kanıt yok")
        m = long_side(v)
        if m:
            out += f" · model {'AL' if m > 0 else 'SAT'} diyor, kanıtsız"
    if b.get("up") is not None:
        sig = "anlamlı" if base_rate_side(b) else "anlamsız"
        out += f" · taban: %{100 * b['up']:.0f} yükseliş ({b.get('horizon_d', 5)}g, {sig})"
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
    if evidence_long_side(v) == 0 and evidence_short_side(v) == 0:
        return "⚪ Kanıtlı yön yok — giriş yok"
    if v.get("entry_allowed"):
        return "✅ Giriş önerilir"
    return f"⛔ Önerilmez · {entry_reason_short(v)}"


def timing_label(v: Dict[str, Any]) -> str:
    if market_closed(v) or (evidence_long_side(v) == 0 and evidence_short_side(v) == 0):
        return "—"
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


def _stop_cell(st: Dict[str, Any], h: str, dg: int) -> str:
    if st.get(h):
        return stop_label(st[h], dg)
    two = st.get(h + "_iki_yon") or {}
    if two.get("al") and two.get("sat"):
        return f"Yön yok · AL ise {two['al']['stop']:,.{dg}f} / SAT ise {two['sat']['stop']:,.{dg}f}"
    return "—"


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
            "Stop · kısa vade": "—" if market_closed(v) else _stop_cell(st, "kisa", dg),
            "Stop · uzun vade": _stop_cell(st, "uzun", dg),
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


def _z(b: Dict[str, Any]) -> float:
    return (float(b["up"]) - 0.5) / math.sqrt(0.25 / max(int(b.get("n") or 1), 1))


def _remaining_days(asset: str, now: Any = None) -> int:
    """Bu haftanın kalan işlem günü (bugünden sonra). Kripto 7/24: Pazar'a kadar."""
    import datetime as _dt
    wd = (now or _dt.datetime.now(_dt.timezone.utc)).weekday()
    return max((6 if asset in ("BTC", "ETH") else 4) - wd, 0)


def simple_days(v: Dict[str, Any], asset: str = "", now: Any = None) -> str:
    sd = v.get("shock_direction")
    if isinstance(sd, dict) and sd.get("side"):
        return (f"{'🟢 Yükseliş' if sd['side'] > 0 else '🔴 Düşüş'} — {sd['name']} sonrası tarihte "
                f"%{100 * sd['hit']:.0f} isabet, ortalama {sd['alpha_bps']:+.0f} bps ({sd['n']} olay, kanıtlı)")
    rd = v.get("research_direction")
    if isinstance(rd, dict) and rd.get("side"):
        return ("🟢 Test edilmiş bir kural yükseliş diyor" if rd["side"] > 0
                else "🔴 Test edilmiş bir kural düşüş diyor")
    br = v.get("base_rates") or {}
    br = {int(k): x for k, x in br.items() if isinstance(x, dict) and x.get("up") is not None}
    if not br and isinstance(v.get("base_rate"), dict):
        br = {int(v["base_rate"].get("horizon_d", 5)): v["base_rate"]}

    def part(name: str, b: Dict[str, Any]) -> str:
        z = _z(b)
        tag = "anlamlı eğilim" if abs(z) >= Z_BASE else "yazı-tura"
        return f"{name}: %{100 * b['up']:.0f} yükseliş ({tag})"

    bits = []
    if 1 in br:
        bits.append(part("Sonraki gün", br[1]))
    k = _remaining_days(asset, now)
    if k >= 2 and k in br:
        bits.append(part(f"Hafta sonuna kadar ({k} gün)", br[k]))
    elif 5 in br:
        bits.append(part("Gelecek 5 gün", br[5]))
    return " · ".join(bits) + " — geçmiş 10 yıl" if bits else "🤷 Kesin bilinmez"


def _hot(v: Dict[str, Any]) -> bool:
    vs = v.get("vol_state") or {}
    if vs.get("ratio") is not None:
        return float(vs["ratio"]) > 1.25
    return "NEGAT" in str((v.get("dealer_gamma") or {}).get("regime") or "")


def simple_calm(v: Dict[str, Any], gex: Optional[Dict[str, Any]] = None, asset: str = "") -> str:
    vs = v.get("vol_state") or {}
    if vs.get("ratio") is None:
        return "—"
    r = float(vs["ratio"])
    head = ("🌪️ Normalden hareketli" if r > 1.25 else "🧘 Normalden sakin" if r < 0.8 else "〰️ Normal")
    out = f"{head} — son 20 gün ±%{vs.get('recent_pct', vs['today_pct']):.1f}/gün, son 1 yıl ±%{vs['normal_pct']:.1f}/gün"
    mf = float(vs.get("move_factor") or 1.0)
    if abs(mf - 1.0) >= 0.05:
        out += f" · opsiyon pozisyonu: hareket ×{mf:.2f} beklenir"
    # Dealer gaması sadece SPX/NQ'da kanıtlı (RESEARCH_LOG #7); kripto için işaret varsayımı güvenilir değil.
    if asset in ("SPX", "NQ"):
        reg = str((v.get("dealer_gamma") or {}).get("regime") or "")
        if "NEGAT" in reg:
            out += " (dealer gaması negatif: hareketi büyütür)"
        elif "POZ" in reg:
            out += " (dealer gaması pozitif: hareketi frenler)"
    return out


def _with_macro(fn):
    def wrap(v, *a, **k):
        out = fn(v, *a, **k)
        return out + str(v.get("macro_note") or "") + str(v.get("shock_note") or "") if out != "—" else out
    return wrap


simple_calm = _with_macro(simple_calm)


def simple_stop(v: Dict[str, Any]) -> str:
    st = v.get("stop_suggestion") or {}
    s = (None if market_closed(v) else st.get("kisa")) or st.get("uzun")
    price = ((v.get("market_structure") or {}).get("levels") or {}).get("price")
    if not s:
        two = st.get("uzun_iki_yon") or {}
        if two.get("al") and two.get("sat"):
            dg = _digits(price)
            return (f"Yön yok · alırsan {two['al']['stop']:,.{dg}f} altında, "
                    f"satarsan {two['sat']['stop']:,.{dg}f} üstünde fikir bozulur")
        return "—"
    lvl = f"{s['stop']:,.{_digits(price)}f}"
    if s["side"] > 0:
        return f"Yükseliş fikri {lvl} altında geçersiz (%{s['distance_pct']:.1f} aşağıda)"
    return f"Düşüş fikri {lvl} üstünde geçersiz (%{s['distance_pct']:.1f} yukarıda)"


def _lean(v: Dict[str, Any]) -> Dict[str, int]:
    return {"now": 0 if market_closed(v) else evidence_short_side(v), "hist": evidence_long_side(v)}


def simple_today(v: Dict[str, Any]) -> str:
    if market_closed(v):
        return "⏸️ Piyasa kapalı"
    r = v.get("day_range") or {}
    now = _lean(v)["now"]
    tilt = {1: "🟢 son 4 saat yukarı", -1: "🔴 son 4 saat aşağı"}.get(now, "⚪ son 4 saat yatay")
    rm = v.get("recent_move") or {}
    if rm.get("ret_pct") is not None:
        tilt += f" (%{rm['ret_pct']:+.2f})"
    if rm.get("pair") == "ayrışma":
        tilt += " · eşinden ayrışıyor"
    if not r.get("move") or not r.get("price"):
        return tilt
    p, m, dg = r["price"], r["move"], _digits(r["price"])
    return (f"Büyük olasılıkla {p - m:,.{dg}f} – {p + m:,.{dg}f} arasında (±%{100 * m / p:.1f}) · {tilt}")


def simple_risk(v: Dict[str, Any]) -> str:
    if market_closed(v):
        return "—"
    if "KRİZ" in str(v.get("verdict", "")):
        return "🔴 Çok riskli — kriz sinyali"
    if v.get("shock_active"):
        return "🔴 Riskli — son saatlerde şok hareket oldu"
    if v.get("macro_pending"):
        return "🔴 Riskli — bugün önemli ABD verisi açıklanacak"
    neg = _hot(v)
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
    sd = v.get("shock_direction")
    if isinstance(sd, dict) and sd.get("side"):
        return f"{word[sd['side']]} — kanıtlı şok sonrası kural ({sd['name']}, {sd['days_left']} gün)"
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
                     "Yarın ve bu hafta": simple_days(v, k),
                     "Piyasa sakin mi?": simple_calm(v, gex, k),
                     "Fikir nerede bozulur?": simple_stop(v)})
    return rows


SIMPLE_GUIDE = """
**Bu tablo nasıl okunur?**
- **Şimdi ne yapmalı?** — Sistem bütün kontrolleri yapar. Hepsi uygunsa ✅ yazar. Çoğu zaman ✋ Bekle yazar; bu normaldir. İyi fırsat az olur.
- **Bugün fiyat ne yapabilir?** — Günlük 1σ aralığıdır (opsiyon piyasası; yoksa son 20 günün oynaklığı). Fiyat günlerin yaklaşık 2/3'ünde bu aralıkta kapanır. Eğilim son 4 saatin hareketidir; tahmin değil, betimlemedir.
- **Şimdi girmek riskli mi?** — 🟢 düşük, 🟡 orta, 🔴 yüksek. Sert piyasa veya çelişen sinyaller riski yükseltir.
- **Girersen hangi yön daha iyi?** — Kısa vade ve geçmiş eğilim aynı yönü gösterirse o yön yazılır. Çelişirse "girmemek daha iyi" yazılır.
- **Yarın ve bu hafta** — Geçmiş 10 yılda sonraki günün ve haftanın kalan günlerinin yüzde kaçının yükselişle bittiğini gösterir. "Yazı-tura" yazıyorsa bu oran şanstan ayırt edilemez.
- **Piyasa sakin mi?** — Son 20 günün günlük hareketini son 1 yılın normal günüyle karşılaştırır (SPX/NQ'da opsiyon pozisyonu çarpanıyla). Tek bir kriz günü ortalamayı bozmasın diye medyan kullanılır. Oynaklık kümelenir: bu, sistemin en güçlü bilgisidir (15 yıllık veride kanıtlı). Hareketli piyasada küçük pozisyon ve geniş stop gerekir.
- **⚠️ Bugün veri** — TÜFE, istihdam, FOMC gibi ABD verileri açıklanan günlerde fiyat çok hızlı hareket edebilir. Sistem bu günlerin etkisini kendi verisinde ölçer. Etki kanıtlıysa beklenen aralığı ve stopları genişletir.
- **Şok sonrası yön** — Ayrı bir motor, 10 yıllık veride her şok türünden (ABD/küresel hisse çöküşü, dolar, faiz, petrol, kredi, güvenli liman, kripto) sonra fiyatın ne yaptığını ölçer. Sadece kanıtlı kural varsa yön yazar.
- **⚡ Şok** — Sistem 11 göstergeyi (hisse vadelileri, altın, gümüş, kripto, VIX, dolar, yen, faiz, petrol) 5 dakikalık veriyle izler. Bir gösterge normalin 4-5 katı hızlı hareket ederse bunu şok sayar. Şoktan sonra 4 saat aralık ve stoplar genişler, risk 🔴 olur.
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
