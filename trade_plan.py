"""
Piyasa Nabzı + Nihai İşlem Önerisi (v17.0)
==========================================
1) PİYASA NABZI (giriş riski): fiyatın yönüne BAKMAZ, sadece oynaklığa bakar.
   * bugün:  bugünkü beklenen 1σ hareket / son 1 yılın normal günü
             (son 20 gün σ × kanıtlı çarpanlar: GEX, veri günü, şok)
   * şu an:  son 1 saatin 5 dk oynaklığı / son 5 günün normal 5 dk oynaklığı
   * olay:   aktif şok; 2 saat içinde açıklanacak ABD verisi
   Seviye = max(bugün, şu an) → 🟢 < 0.8 ≤ 🟡 < 1.25 ≤ 🟠 < 1.75 ≤ 🔴; şok veya
   yakın veri → 🔴. Notlanır: nabız skoru ↔ sonraki 4/24 saatlik |getiri|/σ.

2) NİHAİ İŞLEM ÖNERİSİ: yön (day_direction), giriş, stop, hedef — veya "işlem yok".
   * 🔴 nabız → işlem yok. Yön yok → işlem yok.
   * "zayıf" yön (sadece tarihsel eğilim) → sadece nabız 🟢/🟡 ve son 4 saat
     ters yönde değilse önerilir, güven "düşük" yazılır.
   * Giriş: şimdiki fiyat. Stop: kısa vade yapısal stop (stop_levels).
   * Hedef: yön tarafındaki en yakın yapısal/gama seviyesi (R ≥ 1.5 ve
     ≤ 1.5 günlük σ); yoksa 2R. R:R < 1.5 ise işlem yok.
   Her öneri trade_ledger.csv dosyasına yazılır ve 1 saatlik barlarla 24 saat
   boyunca izlenir: önce stop mu, hedef mi? Sonuç R cinsinden. Karne: isabet,
   ortalama R, beklenen değer — güven seviyesine göre ayrı.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from system_clock import now_utc

LEDGER = "trade_ledger.csv"
COLS = ["ts", "asset", "side", "entry", "stop", "target", "confidence", "source", "pulse",
        "outcome", "r_mult", "exit_ts", "graded", "logic"]
TARGET_KINDS = {1: {"PDH", "ONH", "PWH", "SWH", "CALL_WALL", "CALL_WALL_0DTE", "GAMMA_FLIP", "VWAP"},
                -1: {"PDL", "ONL", "PWL", "SWL", "PUT_WALL", "PUT_WALL_0DTE", "GAMMA_FLIP", "VWAP"}}


def _logic() -> str:
    try:
        from config import LOGIC_VERSION
        return LOGIC_VERSION
    except Exception:
        return "?"


# ---------------------------------------------------------------------------
# 1) Piyasa nabzı
# ---------------------------------------------------------------------------
def pulse(v: Dict[str, Any]) -> Dict[str, Any]:
    vs = v.get("vol_state") or {}
    today = float(vs["ratio"]) if vs.get("ratio") is not None else None
    now_r = float(v["vol_now"]) if v.get("vol_now") is not None else None
    parts = [x for x in (today, now_r) if x is not None]
    score = max(parts) if parts else None
    flags = []
    if v.get("shock_active"):
        flags.append("son saatlerde şok")
    mn = v.get("macro_next_min")
    if mn is not None and 0 <= float(mn) <= 120:
        flags.append(f"{int(mn)} dk içinde ABD verisi")
    if flags or (score is not None and score >= 1.75):
        lvl, word = 4, "🔴 Çok riskli — girme"
    elif score is None:
        lvl, word = 0, "⚪ Ölçülemedi"
    elif score >= 1.25:
        lvl, word = 3, "🟠 Hareketli — küçük pozisyon, geniş stop"
    elif score >= 0.8:
        lvl, word = 2, "🟡 Normal"
    else:
        lvl, word = 1, "🟢 Sakin — giriş için uygun ortam"
    bits = []
    if today is not None:
        bits.append(f"bugün beklenen hareket normalin ×{today:.2f}'i (±%{float(vs.get('today_pct', 0)):.1f})")
    if now_r is not None:
        bits.append(f"şu an ×{now_r:.2f}")
    txt = word + (" — " + ", ".join(bits) if bits else "") + (" · " + ", ".join(flags) if flags else "")
    return {"level": lvl, "score": round(score, 2) if score is not None else None, "text": txt, "flags": flags}


# ---------------------------------------------------------------------------
# 2) İşlem önerisi
# ---------------------------------------------------------------------------
def _target(side: int, price: float, risk: float, levels: Dict[str, Any], g: Dict[str, Any], sigma: Optional[float]):
    import stop_levels as SL
    cands = [c for c in SL._candidates(levels, g) if c["kind"] in TARGET_KINDS[side]]
    best = None
    for c in cands:
        dist = (c["price"] - price) * side
        if dist >= 1.5 * risk and (sigma is None or dist <= 1.5 * sigma):
            if best is None or dist < best[0]:
                best = (dist, c)
    if best:
        return best[1]["price"], best[1].get("label", best[1]["kind"])
    return price + side * 2.0 * risk, "2R (yakın seviye yok)"


def plan(asset: str, v: Dict[str, Any], ctx: Dict[str, Any], g: Dict[str, Any]) -> Dict[str, Any]:
    import stop_levels as SL
    if ((ctx.get("session") or {}).get("phase")) == "Kapalı":
        return {"action": "none", "text": "⏸️ Piyasa kapalı — işlem yok"}
    p = pulse(v)
    dd = v.get("day_direction") or {}
    side = int(dd.get("side") or 0)
    if p["level"] == 4:
        why = ", ".join(p["flags"]) if p["flags"] else "oynaklık çok yüksek"
        return {"action": "none", "text": f"⛔ İşlem yok — çok riskli ({why})", "pulse": p}
    if side == 0:
        return {"action": "none", "text": "⚪ İşlem yok — bugün için kanıtlı yön yok", "pulse": p}
    conf = {"güçlü": "yüksek", "orta": "orta", "zayıf": "düşük"}.get(dd.get("strength"), "düşük")
    if conf == "düşük":
        lean = SL.evidence_short_side(v)
        if p["level"] >= 3:
            return {"action": "none", "text": "⚪ İşlem yok — yön zayıf ve piyasa hareketli", "pulse": p}
        if lean == -side:
            return {"action": "none", "text": "⚪ İşlem yok — zayıf yön, son 4 saat ters yönde", "pulse": p}
    lv = ctx.get("levels") or {}
    price = lv.get("price") or (v.get("day_range") or {}).get("price")
    if not price:
        return {"action": "none", "text": "⚪ İşlem yok — fiyat yok", "pulse": p}
    st = SL.suggest_stop(side, "kisa", float(price), ctx.get("atr_1h"), ctx.get("atr_1d"), (g or {}).get("expected_move_1d"),
                         lv, g or None, 1.0, ctx.get("move_factor", 1.0))
    if not st:
        return {"action": "none", "text": "⚪ İşlem yok — stop hesaplanamadı", "pulse": p}
    risk = abs(float(price) - st["stop"])
    sigma = (v.get("day_range") or {}).get("move")
    tgt, tlabel = _target(side, float(price), risk, lv, g or {}, sigma)
    rr = abs(tgt - float(price)) / risk if risk > 0 else 0
    if rr < 1.5:
        return {"action": "none", "text": "⚪ İşlem yok — kazanç/risk oranı yetersiz", "pulse": p}
    dg = 0 if price > 5000 else 1 if price > 500 else 2
    word = "🟢 AL" if side > 0 else "🔴 SAT"
    txt = (f"{word} · giriş ~{price:,.{dg}f} · stop {st['stop']:,.{dg}f} · hedef {tgt:,.{dg}f} ({tlabel}) · "
           f"R:R {rr:.1f} · güven: {conf} ({dd.get('why', '')})")
    return {"action": "trade", "side": side, "entry": float(price), "stop": float(st["stop"]), "target": float(tgt),
            "rr": round(rr, 2), "confidence": conf, "source": dd.get("source"), "text": txt, "pulse": p}


# ---------------------------------------------------------------------------
# Defter: öneriler kaydedilir ve notlanır
# ---------------------------------------------------------------------------
def _load(path: str) -> pd.DataFrame:
    try:
        d = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame(columns=COLS)
    except Exception:
        d = pd.DataFrame(columns=COLS)
    for c in COLS:
        if c not in d.columns:
            d[c] = np.nan
    return d


def grade(d: pd.DataFrame, frames: Dict[str, Any], now: pd.Timestamp) -> None:
    for i, r in d[d["graded"].fillna(0) == 0].iterrows():
        t0 = pd.Timestamp(r["ts"])
        t0 = t0.tz_localize("UTC") if t0.tzinfo is None else t0
        f = frames.get(r["asset"])
        if not isinstance(f, pd.DataFrame) or f.empty:
            continue
        x = f.copy()
        x.index = pd.to_datetime(x.index, utc=True)
        w = x[(x.index > t0) & (x.index <= t0 + pd.Timedelta(hours=24))]
        side, e, s, t = int(r["side"]), float(r["entry"]), float(r["stop"]), float(r["target"])
        risk = abs(e - s)
        done = None
        for ts, b in w.iterrows():
            hi, lo = float(b["High"]), float(b["Low"])
            hit_s = lo <= s if side > 0 else hi >= s
            hit_t = hi >= t if side > 0 else lo <= t
            if hit_s:                                   # aynı barda ikisi de varsa muhafazakâr: stop
                done = ("stop", -1.0, ts)
                break
            if hit_t:
                done = ("hedef", abs(t - e) / risk, ts)
                break
        if done is None and now >= t0 + pd.Timedelta(hours=24) and len(w):
            last = float(w["Close"].iloc[-1])
            done = ("süre doldu", side * (last - e) / risk, w.index[-1])
        if done:
            d.at[i, "outcome"], d.at[i, "r_mult"], d.at[i, "exit_ts"] = done[0], round(done[1], 3), str(done[2])
            d.at[i, "graded"] = 1
        elif now > t0 + pd.Timedelta(days=4):
            d.at[i, "graded"] = -1


def scorecard(d: pd.DataFrame, logic: Optional[str] = None) -> Dict[str, Any]:
    g = d[d["graded"] == 1]
    if logic:
        g = g[g["logic"] == logic]
    if g.empty:
        return {"n": 0}
    out = {"n": int(len(g)), "win": round(float((g["r_mult"] > 0).mean()), 3),
           "avg_r": round(float(g["r_mult"].mean()), 3)}
    for c, x in g.groupby("confidence"):
        out[f"güven_{c}"] = {"n": int(len(x)), "win": round(float((x["r_mult"] > 0).mean()), 3),
                             "avg_r": round(float(x["r_mult"].mean()), 3)}
    return out


def run_cycle(verdicts: Dict[str, Dict[str, Any]], contexts: Dict[str, Dict[str, Any]], snaps: Dict[str, Any],
              frames: Dict[str, Any], path: str = LEDGER, now: Any = None, logic: Optional[str] = None) -> Dict[str, Any]:
    now = pd.Timestamp(now or now_utc())
    now = now.tz_localize("UTC") if now.tzinfo is None else now.tz_convert("UTC")
    logic = logic or _logic()
    d = _load(path)
    grade(d, frames, now)
    for a, v in verdicts.items():
        pl = plan(a, v, contexts.get(a) or {}, (snaps or {}).get(a) or {})
        v["pulse"] = pl.get("pulse") or pulse(v)
        v["trade_plan"] = pl
        if pl.get("action") != "trade":
            continue
        today = now.date().isoformat()
        same = d[(d["asset"] == a) & (d["ts"].astype(str).str[:10] == today) & (d["side"] == pl["side"])]
        open_ = d[(d["asset"] == a) & (d["graded"].fillna(0) == 0)]
        if len(same) or len(open_):                      # günde aynı yönde tek öneri; açık öneri varken yenisi yok
            continue
        d.loc[len(d)] = {"ts": now.isoformat(), "asset": a, "side": pl["side"], "entry": pl["entry"], "stop": pl["stop"],
                         "target": pl["target"], "confidence": pl["confidence"], "source": pl["source"],
                         "pulse": (pl.get("pulse") or {}).get("score"), "outcome": None, "r_mult": np.nan,
                         "exit_ts": None, "graded": 0, "logic": logic}
    d.tail(20000).to_csv(path, index=False)
    return scorecard(d, logic)
