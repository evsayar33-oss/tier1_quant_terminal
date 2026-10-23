"""
Önerilen Stop Seviyesi (v15.1) — analiz çıktısı, emir DEĞİL
============================================================
Piyasa yapıcı mantığı: stop emirleri belirgin seviyelerin hemen ötesinde
birikir ve likidite avında ilk onlar alınır. Bu yüzden stop:

1. Yönü geçersiz kılan en yakın YAPISAL seviyenin (salınım dibi/tepesi,
   önceki gün/hafta, gece aralığı, gama duvarı/flip) ÖTESİNE konur,
2. seviye ile stop arasına bir "likidite avı payı" bırakılır,
3. yuvarlak sayının tam üstüne/altına konmaz,
4. ufka uygun bir mesafe bandının içinde kalır (kısa vade: 1H ATR; uzun
   vade: piyasa yapıcının fiyatladığı günlük hareket veya günlük ATR),
5. −Γ rejiminde pay büyütülür (dealer hedge'i hareketi büyütür).

Kendi kendini kalibre eder: StopLedger her öneriyi ufuk sonunda notlar.
"Stop avlandı" = stop tetiklendi AMA ufuk sonunda yön yine doğru çıktı
(stop gereğinden yakındı). Bu oran hedefin (%10) üstündeyse pay büyür,
altındaysa küçülür. n ≥ 30 bağımsız gözlemden önce çarpan 1.0'dır.
"""
from __future__ import annotations

import math
import os
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from system_clock import now_utc

LEDGER_FILE = "stop_ledger.csv"

HORIZONS: Dict[str, Dict[str, Any]] = {
    # unit: "atr_1h" veya "daily" (gama beklenen hareketi, yoksa günlük ATR)
    "kisa": {"label": "Kısa vade (1-4 saat)", "hours": 4, "unit": "atr_1h",
             "min": 0.75, "max": 3.0, "buffer": 0.25, "fallback": 1.5, "sample_h": 4},
    "uzun": {"label": "Uzun vade (24 saat-1 hafta)", "hours": 72, "unit": "daily",
             "min": 0.40, "max": 1.75, "buffer": 0.15, "fallback": 1.0, "sample_h": 24},
}
STOP_CONFIG = {"hunted_target": 0.10, "min_n": 30, "mult_min": 0.8, "mult_max": 2.0, "neg_gamma_buffer": 1.5}

STRUCTURAL = {"PDH", "PDL", "ONH", "ONL", "PWH", "PWL", "SWH", "SWL", "VWAP"}
# Uzun pozisyonu geçersiz kılan seviyeler dip türüdür (stoplar diplerin altında
# birikir); kısa pozisyonda tepe türü. VWAP ve gamma flip iki yönde de geçerlidir.
ANCHORS = {1: {"PDL", "ONL", "PWL", "SWL", "VWAP", "PUT_WALL", "PUT_WALL_0DTE", "GAMMA_FLIP"},
           -1: {"PDH", "ONH", "PWH", "SWH", "VWAP", "CALL_WALL", "CALL_WALL_0DTE", "GAMMA_FLIP"}}


def short_side(verdict: Dict[str, Any]) -> int:
    lbl = str(verdict.get("current_direction", ""))
    if "YUKARI" in lbl:
        return 1
    if "AŞAĞI" in lbl:
        return -1
    return 0


def long_side(verdict: Dict[str, Any]) -> int:
    rd = verdict.get("research_direction")
    if isinstance(rd, dict) and rd.get("side") is not None:
        return int(rd["side"])           # v16.0: proven daily rule overrides the unproven model
    v = str(verdict.get("verdict", ""))
    if "SAT" in v:
        return -1
    if "AL" in v.replace("SAT", "") and "KRİZ" not in v:
        return 1
    return 0


Z_BASE = 3.0   # taban oran anlamlılığı: 6 varlık × 5 ufuk ≈ 30 test, Bonferroni (iki yönlü %5) ≈ 3.1
RECENT_Z = 0.75  # son 4 saatlik hareket, 4 saatlik normal oynaklığın en az 0.75 katı olmalı


def daily_vol(df: Any) -> Optional[Dict[str, float]]:
    """Günlük kapanıştan kapanışa oynaklık (1σ): son 20 gün ve son 1 yıl.
    Sağlam tahmin: medyan(|r|)/0.6745. Tek bir kriz günü (ör. 30 Ocak 2026 gümüş −%31)
    standart sapmayı aylarca şişirir ve her günü "sakin" gösterirdi."""
    try:
        c = pd.to_numeric(df["Close"], errors="coerce").dropna()
        r = np.log(c / c.shift(1)).dropna()
        if len(r) < 60:
            return None
        rs = lambda x: float(x.abs().median() / 0.6745)
        return {"s20": rs(r.tail(20)), "s252": rs(r.tail(252))}
    except Exception:
        return None


PAIRS = {"SPX": "NQ", "NQ": "SPX", "XAU": "XAG", "XAG": "XAU", "BTC": "ETH", "ETH": "BTC"}


def recent_move(df: Any, bars: int = 4) -> Optional[Dict[str, float]]:
    """Son `bars` saatlik getiri ve bunun normal 4 saatlik oynaklığa oranı (z).
    Başlangıç fiyatı ZAMANA göre alınır (son kayıt − 4 saat). Kaynak bazen yarım
    bir son bar ekler (ör. 11:04); bar saymak pencereyi 3 saate kısaltırdı."""
    try:
        s = pd.to_numeric(df["Close"], errors="coerce")
        s.index = pd.to_datetime(df.index, utc=True)
        s = s.dropna().sort_index()
        hourly = s[(s.index.minute == 0) & (s.index.second == 0)]
        r = np.log(hourly / hourly.shift(1)).dropna().tail(240)
        if len(r) < 48:
            return None
        t_end = s.index[-1]
        start = s[s.index <= t_end - pd.Timedelta(hours=bars)]
        if start.empty:
            return None
        ret = float(np.log(s.iloc[-1] / start.iloc[-1]))
        sd = float(r.abs().median() / 0.6745) * math.sqrt(bars)
        return {"ret_pct": round(100 * (math.exp(ret) - 1), 3), "z": round(ret / sd, 2) if sd > 0 else 0.0,
                "z_own": round(ret / sd, 2) if sd > 0 else 0.0, "bars": bars, "asof": t_end.isoformat()}
    except Exception:
        return None


def pair_consistent(moves: Dict[str, Dict[str, Any]]) -> None:
    """SPX/NQ, XAU/XAG, BTC/ETH aynı ortak faktörle hareket eder (korelasyon ~0.8-0.9).
    Aynı yöndeki küçük hareketler eşik kenarında farklı etiket almasın: işaretler aynıysa
    ikisi de çiftin ortalama z'sini kullanır (ortak hareket). İşaretler zıtsa ve en az biri
    belirginse bu GERÇEK bir ayrışmadır; her varlık kendi z'sini korur ve not düşülür."""
    for a, b in PAIRS.items():
        if a > b or a not in moves or b not in moves:
            continue
        za, zb = float(moves[a]["z_own"]), float(moves[b]["z_own"])
        if za * zb > 0:
            m = round((za + zb) / 2.0, 2)
            moves[a]["z"] = moves[b]["z"] = m
            moves[a]["pair"] = moves[b]["pair"] = "ortak"
        elif max(abs(za), abs(zb)) >= RECENT_Z:
            moves[a]["pair"] = moves[b]["pair"] = "ayrışma"


def model_proven(verdict: Dict[str, Any]) -> bool:
    return "NOT_PROVEN" not in str(verdict.get("learned_model_status", ""))


def base_rate_side(b: Optional[Dict[str, Any]]) -> int:
    """Taban oran sadece istatistiksel olarak anlamlıysa (|z| ≥ Z_BASE) yön verir."""
    b = b or {}
    up, n = b.get("up"), b.get("n") or 0
    if up is None or n < 50:
        return 0
    # Örnekler zaten örtüşmeyen pencerelerden gelir (direction_research: iloc[::h]).
    z = (float(up) - 0.5) / math.sqrt(0.25 / n)
    return 1 if z >= Z_BASE else -1 if z <= -Z_BASE else 0


def evidence_short_side(verdict: Dict[str, Any]) -> int:
    """Kısa vade yönü. Model kanıtsızsa (RESEARCH_LOG #1, #5) sadece fiyatın kendi hareketi:
    son 4 saatlik getiri, normal 4 saatlik oynaklığın RECENT_Z katını geçmeli."""
    if model_proven(verdict):
        return short_side(verdict)
    rm = verdict.get("recent_move")
    if isinstance(rm, dict) and rm.get("z") is not None:
        z = float(rm["z"])
        return 1 if z >= RECENT_Z else -1 if z <= -RECENT_Z else 0
    try:
        pz = float((verdict.get("short_term_parts") or {}).get("price_z"))
    except (TypeError, ValueError):
        return 0
    return 1 if pz >= 0.5 else -1 if pz <= -0.5 else 0


def evidence_long_side(verdict: Dict[str, Any]) -> int:
    """Uzun vade yönü: kanıtlı kural > kanıtlı model > anlamlı taban oran > yön yok."""
    if "KRİZ" in str(verdict.get("verdict", "")):
        return 0
    rd = verdict.get("research_direction")
    if isinstance(rd, dict) and rd.get("side") is not None:
        return int(rd["side"])
    if model_proven(verdict):
        return long_side(verdict)
    return base_rate_side(verdict.get("base_rate"))


def _candidates(levels: Optional[Dict[str, Any]], gamma: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = [dict(x) for x in (levels or {}).get("levels", []) if x.get("kind") in STRUCTURAL]
    for key, label in (("put_wall", "Put duvarı (gama)"), ("call_wall", "Call duvarı (gama)"),
                       ("put_wall_0dte", "0DTE put duvarı"), ("call_wall_0dte", "0DTE call duvarı"),
                       ("gamma_flip", "Gamma flip")):
        p = (gamma or {}).get(key)
        if p:
            out.append({"price": float(p), "kind": key.upper(), "label": label})
    return out


def suggest_stop(side: int, horizon: str, price: float, atr_1h: Optional[float], atr_1d: Optional[float] = None,
                 em_1d: Optional[float] = None, levels: Optional[Dict[str, Any]] = None,
                 gamma: Optional[Dict[str, Any]] = None, buffer_mult: float = 1.0,
                 move_factor: float = 1.0) -> Optional[Dict[str, Any]]:
    if side == 0 or not price or not atr_1h or atr_1h <= 0:
        return None
    h = HORIZONS[horizon]
    if h["unit"] == "atr_1h":
        unit, unit_name = float(atr_1h), "1s ATR"
    elif em_1d:
        unit, unit_name = float(em_1d), "günlük beklenen hareket (opsiyon)"
    elif atr_1d:
        unit, unit_name = float(atr_1d), "günlük ATR"
    else:
        unit, unit_name = float(atr_1h) * math.sqrt(23.0), "1s ATR × √23"
    # v16.2: tarihsel GEX kanıtı — yüksek dealer gamasında hareket küçük, düşükte büyük.
    unit *= float(move_factor or 1.0)
    buf = h["buffer"] * unit * float(buffer_mult)
    neg_gamma = (gamma or {}).get("regime") == "NEGATİF GAMA"
    if neg_gamma:
        buf *= STOP_CONFIG["neg_gamma_buffer"]
    lo, hi = h["min"] * unit, h["max"] * unit
    best = None
    for c in _candidates(levels, gamma):
        if c["kind"] not in ANCHORS[side]:
            continue
        dist = (price - c["price"]) * side            # level on the invalidation side -> dist > 0
        if dist <= 0:
            continue
        if lo <= dist + buf <= hi and (best is None or dist < best[0]):
            best = (dist, c)
    if best is not None:
        anchor = best[1]
        stop = anchor["price"] - side * buf
        basis = f"{anchor['label']} ({anchor['price']:.2f}) {'altı' if side > 0 else 'üstü'} + likidite avı payı"
    else:
        anchor = None
        stop = price - side * h["fallback"] * unit
        basis = f"Volatilite stopu ({h['fallback']:.1f} × {unit_name}; bantta yapısal seviye yok)"
    step = (levels or {}).get("round_step")
    if step:
        r = round(stop / step) * step
        if abs(stop - r) < 0.15 * unit:
            stop = r - side * 0.15 * unit         # stopu yuvarlak sayının ötesine taşı
    dist = (price - stop) * side
    return {"horizon": horizon, "label": h["label"], "side": side, "price": round(float(price), 4),
            "stop": round(float(stop), 4), "distance": round(float(dist), 4),
            "distance_pct": round(100.0 * dist / price, 3), "atr_1h_mult": round(dist / atr_1h, 2),
            "unit": unit_name, "basis": basis, "anchor": anchor, "negative_gamma": neg_gamma,
            "buffer_mult": round(float(buffer_mult), 3), "move_factor": round(float(move_factor or 1.0), 3)}


class StopLedger:
    COLS = ["ts", "asset", "horizon", "side", "price", "stop", "hours", "stop_hit", "ret_dir", "hunted"]

    def __init__(self, path: str = LEDGER_FILE):
        self.path = path
        try:
            self.df = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame(columns=self.COLS)
        except Exception:
            self.df = pd.DataFrame(columns=self.COLS)
        for c in self.COLS:
            if c not in self.df.columns:
                self.df[c] = np.nan

    def record(self, asset: str, s: Dict[str, Any], now: Any = None) -> bool:
        ts = pd.Timestamp(now or now_utc()).floor("h").isoformat()
        if ((self.df["ts"] == ts) & (self.df["asset"] == asset) & (self.df["horizon"] == s["horizon"])).any():
            return False
        self.df.loc[len(self.df)] = {"ts": ts, "asset": asset, "horizon": s["horizon"], "side": s["side"],
                                     "price": s["price"], "stop": s["stop"], "hours": HORIZONS[s["horizon"]]["hours"],
                                     "stop_hit": np.nan, "ret_dir": np.nan, "hunted": np.nan}
        return True

    def grade(self, frames: Dict[str, pd.DataFrame], now: Any = None) -> int:
        now = pd.Timestamp(now or now_utc())
        n = 0
        for i, row in self.df[self.df["stop_hit"].isna()].iterrows():
            df = frames.get(row["asset"])
            if not isinstance(df, pd.DataFrame) or df.empty:
                continue
            t0 = pd.Timestamp(row["ts"])
            t0 = t0.tz_localize("UTC") if t0.tzinfo is None else t0
            t1 = t0 + pd.Timedelta(hours=float(row["hours"]))
            if now < t1:
                continue
            idx = pd.to_datetime(df.index, utc=True)
            w = df[(idx > t0) & (idx <= t1)]
            if len(w) < max(2, int(row["hours"]) // 4):
                continue
            side, stop, p0 = int(row["side"]), float(row["stop"]), float(row["price"])
            hit = bool((pd.to_numeric(w["Low"]) <= stop).any()) if side > 0 else bool((pd.to_numeric(w["High"]) >= stop).any())
            ret = side * (float(pd.to_numeric(w["Close"]).iloc[-1]) / p0 - 1.0)
            self.df.at[i, "stop_hit"] = float(hit)
            self.df.at[i, "ret_dir"] = ret
            self.df.at[i, "hunted"] = float(hit and ret > 0)
            n += 1
        return n

    def stats(self, horizon: str) -> Dict[str, Any]:
        d = self.df[(self.df["horizon"] == horizon) & self.df["stop_hit"].notna()].copy()
        if d.empty:
            return {"n": 0, "buffer_mult": 1.0, "verdict": "VERİ YOK"}
        # Bağımsızlık: ufuk başına bir gözlem (çakışan pencereler şişirmesin).
        step = f"{HORIZONS[horizon]['sample_h']}h"
        d["slot"] = pd.to_datetime(d["ts"], utc=True).dt.floor(step)
        g = d.groupby(["slot", "asset"])[["stop_hit", "hunted"]].mean()
        n = int(len(g))
        hit, hunted = float(g["stop_hit"].mean()), float(g["hunted"].mean())
        mult = 1.0
        if n >= STOP_CONFIG["min_n"]:
            mult = float(np.clip(1.0 + 3.0 * (hunted - STOP_CONFIG["hunted_target"]),
                                 STOP_CONFIG["mult_min"], STOP_CONFIG["mult_max"]))
        return {"n": n, "stop_hit_rate": round(hit, 3), "hunted_rate": round(hunted, 3),
                "buffer_mult": round(mult, 3),
                "verdict": "KALİBRE" if n >= STOP_CONFIG["min_n"] else "KANIT TOPLANIYOR"}

    def save(self, max_rows: int = 30000) -> None:
        self.df.tail(max_rows).to_csv(self.path, index=False)


def run_cycle(verdicts: Dict[str, Dict[str, Any]], contexts: Dict[str, Dict[str, Any]],
              gamma_snapshots: Dict[str, Any], frames: Dict[str, pd.DataFrame],
              path: str = LEDGER_FILE, now: Any = None) -> Dict[str, Any]:
    led = StopLedger(path)
    led.grade(frames, now=now)
    stats = {h: led.stats(h) for h in HORIZONS}
    moves = {a: m for a in verdicts if (m := recent_move(frames.get(a)))}
    pair_consistent(moves)
    for asset, v in verdicts.items():
        ctx = contexts.get(asset) or {}
        if asset in moves:
            v["recent_move"] = moves[asset]
        lv = ctx.get("levels")
        price = (lv or {}).get("price")
        g = (gamma_snapshots or {}).get(asset)
        out = {}
        closed = (ctx.get("session") or {}).get("phase") == "Kapalı"
        args = lambda side, h: (side, h, price, ctx.get("atr_1h"), ctx.get("atr_1d"),
                                (g or {}).get("expected_move_1d"), lv, g, stats[h]["buffer_mult"],
                                ctx.get("move_factor", 1.0))
        for h, side in (("kisa", 0 if closed else evidence_short_side(v)), ("uzun", evidence_long_side(v))):
            s = suggest_stop(*args(side, h))
            out[h] = s
            if s:
                led.record(asset, s, now=now)
            elif not (closed and h == "kisa"):
                # Yön yok: iki senaryonun geçersizlik seviyesi gösterilir (deftere yazılmaz).
                out[h + "_iki_yon"] = {"al": suggest_stop(*args(1, h)), "sat": suggest_stop(*args(-1, h))}
        v["stop_suggestion"] = out
        # Bugünkü 1σ kapanış aralığı: opsiyon beklenen hareketi, yoksa son 20 günün oynaklığı
        # (ATR değil: ATR gün içi aralıktır, kapanışın 2/3 olasılık aralığı değildir).
        em, vol = (g or {}).get("expected_move_1d"), ctx.get("vol") or {}
        mf = float(ctx.get("move_factor", 1.0) or 1.0)
        if price:
            if em:
                sig, src = float(em) / float(price), "opsiyon"
            elif vol.get("s20"):
                sig, src = float(vol["s20"]), "son 20 gün"
            else:
                sig, src = None, None
            if sig:
                sig *= mf
                v["day_range"] = {"move": sig * float(price), "price": float(price), "source": src}
            if vol.get("s20") and vol.get("s252"):
                # Sakin/hareketli: aynı türden iki ölçüyü karşılaştır (gerçekleşen ↔ gerçekleşen).
                # Opsiyon beklenen hareketi oynaklık risk primi içerir; 1 yıllık gerçekleşenle kıyaslanmaz.
                exp = float(vol["s20"]) * mf
                v["vol_state"] = {"ratio": round(exp / vol["s252"], 2), "today_pct": round(100 * exp, 2),
                                  "recent_pct": round(100 * vol["s20"], 2), "normal_pct": round(100 * vol["s252"], 2),
                                  "move_factor": round(mf, 3)}
    led.save()
    return stats
