"""
Gölge Defter Değerlendirmesi — RESEARCH_LOG #13-#15 (önceden kayıtlı testler)
============================================================================
Çalıştırma: python shadow_eval.py --ledger shadow_ledger.csv --out shadow_eval_report.md
Örtüşmeyi azaltmak için her varlık-gün için TEK örnek kullanılır.
Toplam test sayısı üzerinden Bonferroni: geçme eşiği p < 0.05 / test sayısı.

H13 Charm/vanna: SPX/NQ, ET 11:00-15:00 arasındaki ilk kayıt. sign(akış) ile
    seans sonuna kadar getirinin işareti → isabet, binom p (tek yönlü, > %50).
H14 Duvar/pin ve H15 hacim profili: "dokun ve tut" oranı. Seviye 24 saatte
    dokunulduysa ve 24 saat kapanışı kayıt anındaki tarafta kaldıysa "tuttu".
    Kontrol: aynı satırların seviye uzaklıkları satırlar arasında karıştırılır
    (2000 permütasyon) → rastgele seviyenin tutma oranı. p = permütasyonların
    gerçek oranı ≥ olanların payı. Pin: seans sonunda pine uzaklık küçüldü mü,
    aynı permütasyon kontrolü.
"""
from __future__ import annotations

import argparse
import math
from statistics import NormalDist
from typing import Any, Dict, List

import numpy as np
import pandas as pd

N_PERM = 2000
MIN_N = 20


def _one_per_day(d: pd.DataFrame, hour_from: int = 0, hour_to: int = 24) -> pd.DataFrame:
    d = d.copy()
    d["t"] = pd.to_datetime(d["ts"], utc=True)
    d = d[(d["et_hour"] >= hour_from) & (d["et_hour"] < hour_to)]
    d["day"] = d["t"].dt.tz_convert("America/New_York").dt.date
    return d.sort_values("t").groupby(["asset", "day"]).head(1)


def sign_test(x: pd.Series, y: pd.Series) -> Dict[str, Any]:
    m = pd.DataFrame({"x": x, "y": y}).dropna()
    m = m[(m["x"] != 0) & (m["y"] != 0)]
    n = len(m)
    if n < MIN_N:
        return {"n": n, "status": "VERİ YETERSİZ"}
    hit = float((np.sign(m["x"]) == np.sign(m["y"])).mean())
    z = (hit - 0.5) / math.sqrt(0.25 / n)
    p = 1 - NormalDist().cdf(z)
    return {"n": n, "hit": round(hit, 3), "z": round(z, 2), "p": round(p, 4)}


def hold_test(d: pd.DataFrame, col: str, rng: np.random.Generator) -> Dict[str, Any]:
    m = d.dropna(subset=[col, "price", "hi_24h", "lo_24h", "close_24h"]).copy()
    m = m[m[col] > 0]
    if len(m) < MIN_N:
        return {"n_rows": int(len(m)), "status": "VERİ YETERSİZ"}
    p, hi, lo, cl = (m[k].to_numpy(float) for k in ("price", "hi_24h", "lo_24h", "close_24h"))
    rel = m[col].to_numpy(float) / p - 1.0

    def rate(r: np.ndarray):
        L = p * (1 + r)
        touched = (lo <= L) & (L <= hi) & (np.abs(r) > 1e-9)
        if touched.sum() == 0:
            return np.nan, 0
        held = np.sign(cl - L) == np.sign(p - L)
        return float(held[touched].mean()), int(touched.sum())

    actual, n_touch = rate(rel)
    if n_touch < MIN_N:
        return {"n_rows": int(len(m)), "n_touch": n_touch, "status": "VERİ YETERSİZ"}
    perm = np.array([rate(rng.permutation(rel))[0] for _ in range(N_PERM)])
    perm = perm[~np.isnan(perm)]
    pval = float((perm >= actual).mean()) if len(perm) else 1.0
    return {"n_rows": int(len(m)), "n_touch": n_touch, "hold": round(actual, 3),
            "control_hold": round(float(perm.mean()), 3), "p": round(pval, 4)}


def pin_test(d: pd.DataFrame, rng: np.random.Generator) -> Dict[str, Any]:
    m = d.dropna(subset=["pin_0dte", "price", "close_et16"])
    if len(m) < MIN_N:
        return {"n": int(len(m)), "status": "VERİ YETERSİZ"}
    p, c, pin = (m[k].to_numpy(float) for k in ("price", "close_et16", "pin_0dte"))
    rel = pin / p - 1.0

    def rate(r):
        P = p * (1 + r)
        return float((np.abs(c - P) < np.abs(p - P)).mean())

    actual = rate(rel)
    perm = np.array([rate(rng.permutation(rel)) for _ in range(N_PERM)])
    return {"n": int(len(m)), "closer": round(actual, 3), "control": round(float(perm.mean()), 3),
            "p": round(float((perm >= actual).mean()), 4)}


def head_to_head(d: pd.DataFrame) -> Dict[str, Any]:
    """Şampiyon (ekrandaki sistem) ↔ meydan okuyan (yeni fikirlerle birleşik sistem), aynı saatler."""
    out: Dict[str, Any] = {}
    m = d.dropna(subset=["ret_4h"]).copy()
    m["t"] = pd.to_datetime(m["ts"], utc=True)
    m = m.sort_values("t")
    keep, last = [], {}
    for i, r in m.iterrows():                       # varlık başına en az 4 saat arayla (örtüşmesiz)
        if r["asset"] not in last or r["t"] - last[r["asset"]] >= pd.Timedelta(hours=4):
            keep.append(i)
            last[r["asset"]] = r["t"]
    m = m.loc[keep]

    def lean_stats(col):
        x = m[m[col].fillna(0) != 0]
        if len(x) < MIN_N:
            return {"n": int(len(x)), "status": "VERİ YETERSİZ"}
        hit = float((np.sign(x[col]) == np.sign(x["ret_4h"])).mean())
        return {"n": int(len(x)), "hit": round(hit, 3),
                "mean_bps": round(float((np.sign(x[col]) * x["ret_4h"]).mean()) * 1e4, 2)}

    out["Yön · şampiyon"] = lean_stats("champ_lean")
    out["Yön · birleşik"] = lean_stats("chal_lean")
    diff = m[(m["chal_lean"].fillna(0) != m["champ_lean"].fillna(0)) & (m["chal_lean"].fillna(0) != 0)]
    if len(diff) >= MIN_N:
        out["Yön · sadece farklı saatler (charm katkısı)"] = sign_test(diff["chal_lean"], diff["ret_4h"])
    else:
        out["Yön · sadece farklı saatler (charm katkısı)"] = {"n": int(len(diff)), "status": "VERİ YETERSİZ"}
    for side, nm in ((1, "long"), (-1, "short")):
        s = m.dropna(subset=[f"champ_stop_{nm}", f"chal_stop_{nm}", "hi_4h", "lo_4h"])
        s = s[s[f"champ_stop_{nm}"] != s[f"chal_stop_{nm}"]]
        if len(s) < MIN_N:
            out[f"Stop {nm} · şampiyon ↔ birleşik"] = {"n_farklı": int(len(s)), "status": "VERİ YETERSİZ"}
            continue
        res = {}
        for who in ("champ", "chal"):
            st = s[f"{who}_stop_{nm}"].to_numpy(float)
            hit = (s["lo_4h"].to_numpy(float) <= st) if side > 0 else (s["hi_4h"].to_numpy(float) >= st)
            fav = np.sign(s["ret_4h"].to_numpy(float)) == side
            dist = np.abs(s["price"].to_numpy(float) - st) / s["price"].to_numpy(float)
            res[who] = {"tetiklenme": round(float(hit.mean()), 3), "avlanma": round(float((hit & fav).mean()), 3),
                        "uzaklık_%": round(100 * float(dist.mean()), 3)}
        out[f"Stop {nm} · şampiyon ↔ birleşik"] = {"n_farklı": int(len(s)), "şampiyon": res["champ"], "birleşik": res["chal"]}
    return out


def evaluate(path: str, seed: int = 7) -> Dict[str, Any]:
    d = pd.read_csv(path)
    d = d[(d["shadow"] == "shadow-v1") & (d["graded"] == 1)]
    rng = np.random.default_rng(seed)
    out: Dict[str, Any] = {}
    us = d[d["asset"].isin(["SPX", "NQ"])]
    h13 = _one_per_day(us, 11, 15)
    out["H13a charm_1d → seans sonu"] = sign_test(h13["charm_1d"], h13["ret_close"])
    out["H13b charm_0dte → seans sonu"] = sign_test(h13["charm_0dte"], h13["ret_close"])
    out["H13c vanna → 4 saat"] = sign_test(h13["vanna_ivdown"], h13["ret_4h"])
    g = _one_per_day(d[d["asset"].isin(["SPX", "NQ", "BTC", "ETH"])])
    for col in ("call_wall", "put_wall", "call_wall_0dte", "put_wall_0dte", "flip"):
        out[f"H14 {col} tutma"] = hold_test(g, col, rng)
    out["H14 pin_0dte mıknatıs"] = pin_test(_one_per_day(us, 9, 15), rng)
    a = _one_per_day(d)
    for col in ("poc", "vah", "val"):
        out[f"H15 {col} tutma"] = hold_test(a, col, rng)
    n_tests = sum(1 for v in out.values() if "p" in v)
    thr = 0.05 / max(n_tests, 1)
    for v in out.values():
        if "p" in v:
            v["status"] = "KANITLANDI" if v["p"] < thr else "REDDEDİLDİ"
    return {"tests": out, "n_tests": n_tests, "p_threshold": round(thr, 5), "rows": int(len(d)),
            "head_to_head": head_to_head(d)}


def compare_clone(state_dir: str) -> List[str]:
    """Şampiyon (ekrandaki) ↔ klon sistem: AYNI ölçüm koduyla (forecast_ledger.scorecard, StopLedger.stats)."""
    import os
    import forecast_ledger as FL
    import stop_levels as SL
    from config import LOGIC_VERSION
    L = ["", "## Şampiyon ↔ Klon (tam kopya, yeni fikirler dahil)", "",
         "| Varlık | Sistem | Aralık isabeti (hedef %68) | 4s eğilim isabeti | Brier beceri |", "|---|---|---|---|---|"]
    paths = {"Şampiyon": (os.path.join(state_dir, "forecast_ledger.csv"), LOGIC_VERSION),
             "Klon": (os.path.join(state_dir, "clone", "forecast_ledger.csv"), LOGIC_VERSION + "+klon1")}
    leds = {k: FL.ForecastLedger(p) for k, (p, _) in paths.items() if os.path.exists(p)}
    assets = sorted(set().union(*[set(l.df["asset"].dropna()) for l in leds.values()])) if leds else []
    for a in assets:
        for k, led in leds.items():
            c = led.scorecard(a, logic=paths[k][1])
            r, l, p = c.get("range") or {}, c.get("lean4h") or {}, c.get("p_up") or {}
            L.append(f"| {a} | {k} | {r.get('coverage', '—')} (n={r.get('n_days', 0)}) | "
                     f"{l.get('hit', '—')} (n={l.get('n', 0)}, {l.get('status', '—')}) | {p.get('skill', '—')} |")
    L += ["", "| Sistem | Ufuk | Stop istatistikleri |", "|---|---|---|"]
    for k, sub in (("Şampiyon", ""), ("Klon", "clone")):
        p = os.path.join(state_dir, sub, "stop_ledger.csv")
        if os.path.exists(p):
            led = SL.StopLedger(p)
            for h in SL.HORIZONS:
                L.append(f"| {k} | {h} | {led.stats(h)} |")
    return L


def report(res: Dict[str, Any]) -> List[str]:
    L = ["# 🧪 Gölge Defter Değerlendirmesi (H13-H15)", "",
         f"Notlanmış satır: {res['rows']} · test sayısı: {res['n_tests']} · geçme eşiği p < {res['p_threshold']}", "",
         "| Test | Sonuç | Ayrıntı |", "|---|---|---|"]
    for k, v in res["tests"].items():
        det = ", ".join(f"{a}={b}" for a, b in v.items() if a != "status")
        L.append(f"| {k} | {v.get('status')} | {det} |")
    L += ["", "## Şampiyon (ekrandaki sistem) ↔ birleşik sistem (yeni fikirler dahil)", "",
          "Daha iyi stop: aynı veya daha düşük tetiklenme/avlanma oranıyla daha yakın stop. "
          "Daha iyi yön: daha yüksek isabet ve ortalama getiri.", ""]
    L += [f"- **{k}**: {v}" for k, v in (res.get("head_to_head") or {}).items()]
    return L


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", default="shadow_ledger.csv")
    ap.add_argument("--out", default="shadow_eval_report.md")
    ap.add_argument("--state", default=None, help="state dalı klasörü: şampiyon ↔ klon karşılaştırması")
    a = ap.parse_args()
    res = evaluate(a.ledger)
    lines = report(res)
    if a.state:
        lines += compare_clone(a.state)
    txt = "\n".join(lines)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
