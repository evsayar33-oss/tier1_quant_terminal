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
    return {"tests": out, "n_tests": n_tests, "p_threshold": round(thr, 5), "rows": int(len(d))}


def report(res: Dict[str, Any]) -> List[str]:
    L = ["# 🧪 Gölge Defter Değerlendirmesi (H13-H15)", "",
         f"Notlanmış satır: {res['rows']} · test sayısı: {res['n_tests']} · geçme eşiği p < {res['p_threshold']}", "",
         "| Test | Sonuç | Ayrıntı |", "|---|---|---|"]
    for k, v in res["tests"].items():
        det = ", ".join(f"{a}={b}" for a, b in v.items() if a != "status")
        L.append(f"| {k} | {v.get('status')} | {det} |")
    return L


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", default="shadow_ledger.csv")
    ap.add_argument("--out", default="shadow_eval_report.md")
    a = ap.parse_args()
    res = evaluate(a.ledger)
    txt = "\n".join(report(res))
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
