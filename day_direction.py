"""
Bugünün Yön Aklı (v17.0) — aday kuralların canlı turnuvası: AL / SAT / NÖTR
=========================================================================
Soru: "Bugün (sonraki 24 saat) fiyat hangi yöne gider?"

Tek bir kurala güvenilmez. Altı aday kural her saat AYNI ANDA hesaplanır,
deftere yazılır ve 24 saat sonra notlanır (day_direction_ledger.csv).
Canlıda yön veren kural, CANLI KAYITTA kendini kanıtlamış olandır:
  n ≥ 60 bağımsız gün (varlık-gün başına tek örnek, havuzlanmış),
  isabet > %50 ve tek yönlü z ≥ 2.5 (6 aday için Bonferroni),
  o varlıkta isabet ≥ %50.
Kanıtlı kural yoksa sıra şudur:
  1) kanıtlı şok-sonrası kural (Motor B, 1 gün) veya kanıtlı günlük kural,
  2) anlamlı 1 günlük taban oran (z ≥ 3) → "zayıf" yön,
  3) NÖTR.
Böylece sistem zamanla en iyi çalışan kuralı kendisi seçer; kanıt
kaybolursa kural kendiliğinden devreden çıkar.

Adaylar (önceden kayıtlı, RESEARCH_LOG #16):
  taban     : 1 günlük taban oran anlamlıysa yönü
  mom4h     : son 4 saat hareketi (ortak çift z, |z| ≥ 0.75) devam eder
  mom24h    : son 24 saat hareketi (günlük σ'ya göre |z| ≥ 0.75) devam eder
  rev24h    : son 24 saat hareketi geri döner
  charm     : SPX/NQ dealer charm akışı yönü (|akış| ≥ 1 mlr $, ET 9-15)
  gama_rev  : pozitif dealer gamasında son 24 saat hareketi geri döner
"""
from __future__ import annotations

import math
import os
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from system_clock import now_utc

LEDGER = "day_direction_ledger.csv"
CANDS = ("taban", "mom4h", "mom24h", "rev24h", "charm", "gama_rev")
Z_PROVE, MIN_DAYS = 2.5, 60
ET = ZoneInfo("America/New_York")
NAME_TR = {"taban": "tarihsel eğilim", "mom4h": "son 4 saat devamı", "mom24h": "son 24 saat devamı",
           "rev24h": "son 24 saat geri dönüşü", "charm": "dealer charm akışı",
           "gama_rev": "pozitif gamada geri dönüş"}
COLS = ["ts", "asset", "price", "chosen", "source"] + [f"c_{c}" for c in CANDS] + ["ret_24h", "graded", "logic"]


def _logic() -> str:
    try:
        from config import LOGIC_VERSION
        return LOGIC_VERSION
    except Exception:
        return "?"


def _ret24(df: Any, now: pd.Timestamp) -> Optional[float]:
    try:
        c = pd.to_numeric(df["Close"], errors="coerce").dropna()
        c.index = pd.to_datetime(df.index, utc=True)
        c = c[c.index <= now]
        start = c[c.index <= c.index[-1] - pd.Timedelta(hours=24)]
        return float(np.log(c.iloc[-1] / start.iloc[-1])) if len(start) else None
    except Exception:
        return None


def candidates(asset: str, v: Dict[str, Any], frame: Any, snap: Dict[str, Any], now: pd.Timestamp,
               ctx: Optional[Dict[str, Any]] = None) -> Dict[str, int]:
    import stop_levels as SL
    out = {c: 0 for c in CANDS}
    b1 = (v.get("base_rates") or {}).get("1") or (v.get("base_rates") or {}).get(1)
    out["taban"] = SL.base_rate_side(dict(b1, horizon_d=1)) if isinstance(b1, dict) else 0
    rm = v.get("recent_move") or {}
    if rm.get("z") is not None and abs(float(rm["z"])) >= 0.75:
        out["mom4h"] = 1 if float(rm["z"]) > 0 else -1
    r24 = _ret24(frame, now)
    s20 = ((ctx or v.get("market_structure") or {}).get("vol") or {}).get("s20")
    if r24 is not None and s20:
        z24 = r24 / float(s20)
        if abs(z24) >= 0.75:
            out["mom24h"] = 1 if z24 > 0 else -1
            out["rev24h"] = -out["mom24h"]
            if "POZ" in str((snap or {}).get("regime") or ""):
                out["gama_rev"] = -out["mom24h"]
    charm = (snap or {}).get("charm_flow_1d_usd")
    if asset in ("SPX", "NQ") and charm and abs(float(charm)) >= 1e9 and 9 <= now.tz_convert(ET).hour < 15:
        out["charm"] = 1 if float(charm) > 0 else -1
    return out


class DayDirectionLedger:
    def __init__(self, path: str = LEDGER):
        self.path = path
        try:
            self.df = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame(columns=COLS)
        except Exception:
            self.df = pd.DataFrame(columns=COLS)
        for c in COLS:
            if c not in self.df.columns:
                self.df[c] = np.nan

    def grade(self, frames: Dict[str, Any], now: pd.Timestamp) -> None:
        for i, row in self.df[self.df["graded"].fillna(0) == 0].iterrows():
            t0 = pd.Timestamp(row["ts"])
            t0 = t0.tz_localize("UTC") if t0.tzinfo is None else t0
            if now < t0 + pd.Timedelta(hours=24):
                continue
            f = frames.get(row["asset"])
            try:
                c = pd.to_numeric(f["Close"], errors="coerce").dropna()
                c.index = pd.to_datetime(f.index, utc=True)
                w = c[(c.index >= t0 + pd.Timedelta(hours=24)) & (c.index <= t0 + pd.Timedelta(hours=96))]
                if w.empty:
                    raise ValueError
                self.df.at[i, "ret_24h"] = float(np.log(w.iloc[0] / float(row["price"])))
                self.df.at[i, "graded"] = 1
            except Exception:
                if now > t0 + pd.Timedelta(days=5):
                    self.df.at[i, "graded"] = -1

    def stats(self, logic: Optional[str] = None) -> Dict[str, Any]:
        d = self.df[self.df["graded"] == 1].copy()
        if logic:
            d = d[d["logic"] == logic]
        if d.empty:
            return {}
        d["day"] = pd.to_datetime(d["ts"], utc=True).dt.date
        d = d.sort_values("ts").groupby(["asset", "day"]).head(1)      # varlık-gün başına tek örnek
        out = {}
        for c in CANDS:
            x = d[d[f"c_{c}"].fillna(0) != 0]
            if x.empty:
                out[c] = {"n": 0}
                continue
            hit = (np.sign(x[f"c_{c}"]) == np.sign(x["ret_24h"])).astype(float)
            n, p = int(len(hit)), float(hit.mean())
            z = (p - 0.5) / math.sqrt(0.25 / n)
            per = {a: round(float(h.mean()), 3) for a, h in hit.groupby(x["asset"])}
            out[c] = {"n": n, "hit": round(p, 3), "z": round(z, 2), "per_asset": per,
                      "proven": bool(n >= MIN_DAYS and z >= Z_PROVE)}
        ch = d[d["chosen"].fillna(0) != 0]
        if len(ch):
            hit = (np.sign(ch["chosen"]) == np.sign(ch["ret_24h"])).astype(float)
            out["_secilen"] = {"n": int(len(hit)), "hit": round(float(hit.mean()), 3)}
        return out


def choose(asset: str, v: Dict[str, Any], cands: Dict[str, int], stats: Dict[str, Any]) -> Dict[str, Any]:
    """Kanıtlı canlı aday > kanıtlı şok/günlük kural > anlamlı taban oran > NÖTR."""
    best = None
    for c in CANDS:
        s = stats.get(c) or {}
        if s.get("proven") and cands.get(c) and (s.get("per_asset") or {}).get(asset, 0.5) >= 0.5:
            if best is None or s["z"] > best[1]["z"]:
                best = (c, s)
    if best:
        c, s = best
        return {"side": cands[c], "source": c, "strength": "güçlü" if s["z"] >= 3.5 else "orta",
                "why": f"{NAME_TR[c]} (canlı kayıtta %{100 * s['hit']:.0f} isabet, {s['n']} gün)"}
    sd = v.get("shock_direction")
    if isinstance(sd, dict) and sd.get("side") and int(sd.get("h", 5)) == 1:
        return {"side": int(sd["side"]), "source": "sok", "strength": "orta", "why": f"kanıtlı şok sonrası: {sd['name']}"}
    rd = v.get("research_direction")
    if isinstance(rd, dict) and rd.get("side") and int(rd.get("horizon_d", 5)) == 1:
        return {"side": int(rd["side"]), "source": "gunluk_kural", "strength": "orta", "why": "kanıtlı günlük kural"}
    if cands.get("taban"):
        b1 = (v.get("base_rates") or {}).get("1") or (v.get("base_rates") or {}).get(1) or {}
        return {"side": cands["taban"], "source": "taban", "strength": "zayıf",
                "why": f"sadece tarihsel eğilim (günlerin %{100 * float(b1.get('up', 0.5)):.0f}'i yükseliş)"}
    return {"side": 0, "source": "yok", "strength": "-", "why": "kanıtlı yön yok"}


def run_cycle(verdicts: Dict[str, Dict[str, Any]], frames: Dict[str, Any], snaps: Dict[str, Any],
              path: str = LEDGER, now: Any = None, logic: Optional[str] = None,
              contexts: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    now = pd.Timestamp(now or now_utc())
    now = now.tz_localize("UTC") if now.tzinfo is None else now.tz_convert("UTC")
    logic = logic or _logic()
    contexts = contexts or {}
    led = DayDirectionLedger(path)
    led.grade(frames, now)
    stats = led.stats(logic)
    ts = now.floor("h").isoformat()
    for a, v in verdicts.items():
        ctx = contexts.get(a) or v.get("market_structure") or {}
        price = (ctx.get("levels") or {}).get("price") or (v.get("day_range") or {}).get("price")
        cands = candidates(a, v, frames.get(a), (snaps or {}).get(a) or {}, now, ctx)
        pick = choose(a, v, cands, stats)
        v["day_direction"] = dict(pick, candidates=cands)
        if price and not ((led.df["ts"] == ts) & (led.df["asset"] == a)).any():
            led.df.loc[len(led.df)] = {"ts": ts, "asset": a, "price": float(price), "chosen": pick["side"],
                                       "source": pick["source"], **{f"c_{c}": cands[c] for c in CANDS},
                                       "ret_24h": np.nan, "graded": 0, "logic": logic}
    led.df.tail(60000).to_csv(path, index=False)
    return stats
