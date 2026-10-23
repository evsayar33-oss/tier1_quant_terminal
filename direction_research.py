"""
Yön Araştırması (v16.0) — "Uzun vade" yönü için kanıt arayan haftalık araştırma
==============================================================================
Neden: 2 yıllık saatlik walk-forward paneli, faktör kütüphanesinin 24-72 saat
yönünde kullanılabilir bilgi taşımadığını gösterdi (havuzlanmış ridge dahil
bütün modeller "Hep AL"ın altında; IC işaretleri dönemden döneme değişiyor).
Yön için literatürde en çok belgelenmiş girdiler fiyatın kendi uzun vadeli
yapısıdır: zaman serisi momentumu (CTA trendi), trend filtresi ve stres
anında kısa vadeli geri dönüş (likidite sağlama primi). Bunlar ancak çok
yıllık GÜNLÜK veriyle sınanabilir.

Kurallar (önceden kayıtlı, sonradan eklenmez/seçilmez):
* Her aday parametresizdir (öğrenme yok) → seçim yanlılığı sadece "hangi
  aday" seçimidir; bunun bedeli Bonferroni ile ödenir.
* Ölçüt: "Hep AL"a göre ZAMANLAMA ALFASI. e_t = (sinyal_t − 1) · r_{t→t+h}.
  Pozitif ortalama = kural, sadece elde tutmaktan daha iyi.
  Çakışmayan pencereler kullanılır (h günde bir gözlem).
* Kanıt: t(e) ≥ t_gerekli (Bonferroni), son 10 yılın 3 eşit döneminin en az
  2'sinde e > 0, ve yön isabeti ≥ %50.
* Kanıtlanmayan varlıkta canlı sistem uzun vade yönünü "kanıtsız" gösterir.

Çalıştırma: python direction_research.py --out validation_reports
"""
from __future__ import annotations

import argparse
import json
import math
import os
from datetime import datetime, timezone
from statistics import NormalDist
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd

SYMBOLS = {"SPX": "ES=F", "NQ": "NQ=F", "XAU": "GC=F", "XAG": "SI=F", "BTC": "BTC-USD", "ETH": "ETH-USD"}
VIX = "^VIX"
HORIZONS_D = (1, 5)
BASE_HORIZONS_D = (1, 2, 3, 4, 5)   # taban oran: yarın ve haftanın kalan günleri (kural testi değil)
TEST_YEARS = 10
MIN_OBS = 150
RESULT_FILE = "direction_research.json"


# ---------------------------------------------------------------------------
# Adaylar — hepsi nedensel: t günündeki karar sadece t kapanışına kadarki veriyi kullanır
# ---------------------------------------------------------------------------
def _sma(c: pd.Series, n: int) -> pd.Series:
    return c.rolling(n, min_periods=n).mean()


def _vix_stress(vix: Optional[pd.Series], idx: pd.Index) -> pd.Series:
    if vix is None or vix.empty:
        return pd.Series(False, index=idx)
    v = vix.reindex(idx).ffill()
    z = (v - v.rolling(252, min_periods=120).mean()) / v.rolling(252, min_periods=120).std()
    return (z > 1.0).fillna(False)


def candidates(c: pd.Series, vix: Optional[pd.Series] = None) -> Dict[str, pd.Series]:
    lr = np.log(c)
    out: Dict[str, pd.Series] = {"always_long": pd.Series(1.0, index=c.index)}
    tsm = {}
    for k in (20, 60, 120, 250):
        s = np.sign(lr - lr.shift(k))
        tsm[k] = s
        out[f"tsmom_{k}"] = s
    out["tsmom_ensemble"] = pd.concat(tsm.values(), axis=1).mean(axis=1)
    out["trend_ma200"] = np.sign(c - _sma(c, 200))
    out["long_or_flat_ma200"] = (c > _sma(c, 200)).astype(float).where(_sma(c, 200).notna())
    rev5 = -np.sign(lr - lr.shift(5))
    stress = _vix_stress(vix, c.index)
    out["drift_plus_stress_reversal"] = pd.Series(np.where(stress, rev5, 1.0), index=c.index).where(rev5.notna())
    return out


# ---------------------------------------------------------------------------
# Değerlendirme
# ---------------------------------------------------------------------------
def required_t(n_tests: int) -> float:
    return float(NormalDist().inv_cdf(1.0 - 0.025 / max(int(n_tests), 1)))


def evaluate(sig: pd.Series, c: pd.Series, h: int, start: pd.Timestamp) -> Optional[Dict[str, Any]]:
    fwd = np.log(c.shift(-h) / c)
    d = pd.DataFrame({"s": sig, "r": fwd}).dropna()
    d = d[d.index >= start].iloc[::h]                 # çakışmayan pencereler
    if len(d) < MIN_OBS:
        return None
    e = (d["s"] - 1.0) * d["r"]                       # Hep AL'a göre zamanlama alfası
    sd = float(e.std(ddof=1))
    t_e = float(e.mean() / sd * math.sqrt(len(e))) if sd > 0 else 0.0
    calls = d[d["s"] != 0]
    hit = float((np.sign(calls["s"]) == np.sign(calls["r"])).mean()) if len(calls) else float("nan")
    thirds = np.array_split(e, 3)
    return {"n": int(len(d)), "alpha_bps": round(float(e.mean()) * 1e4, 2), "t_alpha": round(t_e, 2),
            "hit": round(hit, 4), "mean_bps": round(float((d["s"] * d["r"]).mean()) * 1e4, 2),
            "long_bps": round(float(d["r"].mean()) * 1e4, 2),
            "thirds_alpha_bps": [round(float(x.mean()) * 1e4, 2) for x in thirds],
            "from": str(d.index[0].date()), "to": str(d.index[-1].date())}


def research_asset(c: pd.Series, vix: Optional[pd.Series] = None, test_years: int = TEST_YEARS) -> Dict[str, Any]:
    c = c.dropna()
    c = c[c > 0]
    if len(c) < 400:
        return {"status": "INSUFFICIENT_DATA", "rows": int(len(c))}
    start = max(c.index[0] + pd.Timedelta(days=380), c.index[-1] - pd.DateOffset(years=test_years))
    cands = candidates(c, vix)
    rows = []
    for name, sig in cands.items():
        if name == "always_long":
            continue
        for h in HORIZONS_D:
            r = evaluate(sig, c, h, start)
            if r:
                rows.append({"rule": name, "horizon_d": h, **r})
    # Taban oran: kural yokken bilinen en iyi yön tahmini, tarihsel yükseliş sıklığıdır.
    fwd_base = {}
    for h in BASE_HORIZONS_D:
        r = np.log(c.shift(-h) / c)
        r = r[r.index >= start].dropna().iloc[::h]
        if len(r) >= MIN_OBS:
            fwd_base[str(h)] = {"up": round(float((r > 0).mean()), 4), "mean_bps": round(float(r.mean()) * 1e4, 2),
                                "n": int(len(r))}
    n_tests = max(len(rows), 1)
    t_req = required_t(n_tests)
    for r in rows:
        r["proven"] = bool(r["t_alpha"] >= t_req and sum(x > 0 for x in r["thirds_alpha_bps"]) >= 2
                           and r["hit"] == r["hit"] and r["hit"] >= 0.50)
    rows.sort(key=lambda r: -r["t_alpha"])
    best = rows[0] if rows else None
    return {"status": "OK", "n_tests": n_tests, "t_required": round(t_req, 2), "base_rates": fwd_base,
            "best": best, "proven": [r for r in rows if r["proven"]], "all": rows,
            "data_from": str(c.index[0].date()), "data_to": str(c.index[-1].date())}


def run(closes: Dict[str, pd.Series], vix: Optional[pd.Series] = None) -> Dict[str, Any]:
    res = {"version": "dr-1.0", "generated_at": datetime.now(timezone.utc).isoformat(),
           "horizons_d": list(HORIZONS_D), "test_years": TEST_YEARS, "assets": {}}
    for a, c in closes.items():
        try:
            res["assets"][a] = research_asset(c, vix)
        except Exception as exc:
            res["assets"][a] = {"status": f"ERROR: {exc}"}
    return res


# ---------------------------------------------------------------------------
# Canlı kullanım: kanıtlanmış kuralın BUGÜNKÜ sinyali
# ---------------------------------------------------------------------------
def load_result(path: str = os.path.join("validation_reports", RESULT_FILE)) -> Optional[Dict[str, Any]]:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def base_rate(asset: str, result: Optional[Dict[str, Any]], horizon_d: int = 5) -> Optional[Dict[str, Any]]:
    node = ((result or {}).get("assets") or {}).get(asset) or {}
    b = (node.get("base_rates") or {}).get(str(horizon_d))
    return dict(b, horizon_d=horizon_d) if b else None


def live_direction(asset: str, df_daily: Any, result: Optional[Dict[str, Any]],
                   vix_daily: Any = None) -> Optional[Dict[str, Any]]:
    node = ((result or {}).get("assets") or {}).get(asset) or {}
    proven = node.get("proven") or []
    if not proven or not isinstance(df_daily, pd.DataFrame) or df_daily.empty:
        return None
    rule = proven[0]
    c = pd.to_numeric(df_daily["Close"], errors="coerce").dropna()
    v = pd.to_numeric(vix_daily["Close"], errors="coerce").dropna() if isinstance(vix_daily, pd.DataFrame) and not vix_daily.empty else None
    sig = candidates(c, v).get(rule["rule"])
    if sig is None or sig.dropna().empty:
        return None
    s = float(sig.dropna().iloc[-1])
    return {"rule": rule["rule"], "horizon_d": rule["horizon_d"], "signal": s,
            "side": 1 if s > 0.05 else -1 if s < -0.05 else 0,
            "t_alpha": rule["t_alpha"], "alpha_bps": rule["alpha_bps"], "hit": rule["hit"]}


# ---------------------------------------------------------------------------
# Rapor
# ---------------------------------------------------------------------------
RULE_TR = {
    "tsmom_20": "Momentum 20 gün", "tsmom_60": "Momentum 60 gün", "tsmom_120": "Momentum 120 gün",
    "tsmom_250": "Momentum 250 gün", "tsmom_ensemble": "CTA momentum topluluğu",
    "trend_ma200": "200 gün ortalama (al/sat)", "long_or_flat_ma200": "200 gün ortalama (al/bekle)",
    "drift_plus_stress_reversal": "Hep AL + stres anında 5 gün geri dönüş",
}


def report_lines(res: Dict[str, Any]) -> List[str]:
    L = ["# 🧭 Yön Araştırması (günlük veri, Hep AL'a göre zamanlama alfası)", "",
         f"_Üretim: {res.get('generated_at', '')[:16]} UTC · test penceresi: son {res.get('test_years')} yıl · "
         f"ufuklar: {res.get('horizons_d')} gün_", "",
         "Bir kural sadece şu üç koşulu sağlarsa **KANITLI** sayılır: zamanlama alfası t ≥ gerekli t "
         "(denenen her kural için Bonferroni düzeltmesi), 3 dönemin en az 2'sinde pozitif alfa, yön isabeti ≥ %50.", ""]
    for a, n in (res.get("assets") or {}).items():
        L.append(f"## {a}")
        if n.get("status") != "OK":
            L += [f"- Durum: {n.get('status')}", ""]
            continue
        L.append(f"Veri {n['data_from']} → {n['data_to']} · test sayısı {n['n_tests']} · gerekli t {n['t_required']}")
        L.append("")
        L.append("| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |")
        L.append("|---|---|---|---|---|---|---|")
        for r in n["all"][:8]:
            L.append(f"| {RULE_TR.get(r['rule'], r['rule'])} | {r['horizon_d']}g | {r['alpha_bps']:+.1f} | "
                     f"{r['t_alpha']:+.2f} | %{100 * r['hit']:.1f} | "
                     f"{' / '.join(f'{x:+.1f}' for x in r['thirds_alpha_bps'])} | "
                     f"{'✅ KANITLI' if r['proven'] else '—'} |")
        L.append("")
    return L


def _download(sym: str, years: int = 16) -> Optional[pd.Series]:
    import yfinance as yf
    df = yf.download(sym, period=f"{years}y", interval="1d", progress=False, auto_adjust=False, threads=False)
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    s = pd.to_numeric(df["Close"], errors="coerce").dropna()
    s.index = pd.to_datetime(s.index).tz_localize(None)
    return s


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="validation_reports")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    closes = {k: s for k, sym in SYMBOLS.items() if (s := _download(sym)) is not None}
    vix = _download(VIX)
    res = run(closes, vix)
    with open(os.path.join(a.out, RESULT_FILE), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    with open(os.path.join(a.out, "direction_research_report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(report_lines(res)))
    print("\n".join(report_lines(res))[:4000])


if __name__ == "__main__":
    main()
