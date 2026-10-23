"""
Şok Sonrası Yön Aklı (Motor B, v16.7) — şoklardan sonra piyasa yönü
===================================================================
Motor A (shock_monitor) şoku GÜN İÇİNDE tespit eder ve sadece riski/aralığı
ayarlar. Bu motor ayrı bir sorunun cevabını arar: "Bu TÜR bir şoktan sonra
fiyat tarihsel olarak hangi yöne gitti?" Yön, sadece kanıt varsa verilir.

Veri: 16 göstergenin 10+ yıllık günlük kapanışı (ABD, Avrupa, Japonya,
Hong Kong, gelişen piyasalar, kredi, VIX, dolar, yen, faiz, petrol, altın,
gümüş, kripto). Her gösterge için günlük z = getiri / önceki 60 günün
medyan tabanlı σ'sı (nedensel).

Şok türleri (önceden kayıtlı, sonradan eklenmez — RESEARCH_LOG #12):
  ABD hisse çöküşü / sıçraması, küresel hisse çöküşü (dolar dışı / dolarla),
  dolar şoku ↑/↓, faiz şoku ↑/↓, petrol şoku ↑/↓, güvenli limana kaçış,
  kredi şoku, volatilite patlaması, kripto çöküşü.

Test: her tür × varlık × ufuk (1 ve 5 gün). Olaylar kümelenmez (h gün
arayla ilk olay). Ölçü: olay sonrası ortalama getiri − koşulsuz ortalama
(drift'e göre alfa). Kanıt: n ≥ 15, |t| ≥ Bonferroni t, 3 dönemin en az
2'sinde aynı işaret, olay sonrası ortalama getirinin işareti alfayla aynı.

Canlı: son günün (gün kapanmadıysa geçici) z'leri ile türler tespit edilir;
kanıtlı bir kural etkinse (olaydan bu yana < h gün) yön verilir.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from datetime import datetime, timezone
from statistics import NormalDist
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

PANEL_D = {"ES": "ES=F", "NQ": "NQ=F", "GC": "GC=F", "SI": "SI=F", "BTC": "BTC-USD", "ETH": "ETH-USD",
           "VIX": "^VIX", "DXY": "DX-Y.NYB", "USDJPY": "JPY=X", "TNX": "^TNX", "CL": "CL=F",
           "DAX": "^GDAXI", "N225": "^N225", "HSI": "^HSI", "EEM": "EEM", "HYG": "HYG"}
ASSET_INST = {"SPX": "ES", "NQ": "NQ", "XAU": "GC", "XAG": "SI", "BTC": "BTC", "ETH": "ETH"}
GLOBAL_EQ = ("DAX", "N225", "HSI", "EEM")
HORIZONS = (1, 5)
TEST_YEARS = 10
MIN_EVENTS = 15
RESULT_FILE = "shock_direction.json"

TYPE_TR = {
    "abd_hisse_cokusu": "ABD hisse çöküşü", "abd_hisse_sicramasi": "ABD hisse sıçraması",
    "kuresel_cokus_dolar_disi": "Küresel hisse çöküşü (dolar dışı)",
    "kuresel_cokus_dolarli": "Küresel hisse çöküşü (dolar yükselirken)",
    "dolar_yukari": "Dolar şoku ↑", "dolar_asagi": "Dolar şoku ↓",
    "faiz_yukari": "Faiz şoku ↑", "faiz_asagi": "Faiz şoku ↓",
    "petrol_yukari": "Petrol şoku ↑", "petrol_asagi": "Petrol şoku ↓",
    "guvenli_liman": "Güvenli limana kaçış (altın ↑, hisse ↓)", "kredi_soku": "Kredi şoku",
    "vol_patlamasi": "Volatilite patlaması", "kripto_cokusu": "Kripto çöküşü",
}
CRYPTO_ONLY = {"kripto_cokusu"}


def zscores(closes: Dict[str, pd.Series]) -> pd.DataFrame:
    """Günlük z = log getiri / önceki 60 günün medyan tabanlı σ'sı. Ortak takvim: ES iş günleri + kripto."""
    out = {}
    for k, c in closes.items():
        c = c.dropna()
        c = c[c > 0]
        r = np.log(c / c.shift(1))
        sig = r.abs().rolling(60, min_periods=40).median().shift(1) / 0.6745
        out[k] = r / sig
    return pd.DataFrame(out)


def flags(z: pd.DataFrame) -> pd.DataFrame:
    g = lambda k: z[k] if k in z else pd.Series(np.nan, index=z.index)
    geq = z[[k for k in GLOBAL_EQ if k in z]].mean(axis=1) if any(k in z for k in GLOBAL_EQ) else pd.Series(np.nan, index=z.index)
    dxy = g("DXY")
    f = {
        "abd_hisse_cokusu": g("ES") <= -3, "abd_hisse_sicramasi": g("ES") >= 3,
        "kuresel_cokus_dolar_disi": (geq <= -2.5) & (dxy.abs() < 2),
        "kuresel_cokus_dolarli": (geq <= -2.5) & (dxy >= 2),
        "dolar_yukari": dxy >= 3, "dolar_asagi": dxy <= -3,
        "faiz_yukari": g("TNX") >= 3, "faiz_asagi": g("TNX") <= -3,
        "petrol_yukari": g("CL") >= 3, "petrol_asagi": g("CL") <= -3,
        "guvenli_liman": (g("GC") >= 2.5) & (g("ES") <= -1.5),
        "kredi_soku": g("HYG") <= -3, "vol_patlamasi": g("VIX") >= 4,
        "kripto_cokusu": g("BTC") <= -3,
    }
    return pd.DataFrame({k: v.fillna(False).astype(bool) for k, v in f.items()})


def _decluster(dates: pd.DatetimeIndex, h: int) -> List[pd.Timestamp]:
    out, last = [], None
    for d in dates:
        if last is None or (d - last).days > h * 1.5:
            out.append(d)
            last = d
    return out


def required_t(n_tests: int) -> float:
    return float(NormalDist().inv_cdf(1.0 - 0.025 / max(int(n_tests), 1)))


def study(closes: Dict[str, pd.Series], test_years: int = TEST_YEARS) -> Dict[str, Any]:
    z = zscores(closes)
    fl = flags(z)
    end = z.index.max()
    start = end - pd.DateOffset(years=test_years)
    fl = fl[fl.index >= start]
    rows = []
    for asset, inst in ASSET_INST.items():
        c = closes.get(inst)
        if c is None or len(c) < 500:
            continue
        c = c.dropna()
        for typ in fl.columns:
            if typ in CRYPTO_ONLY and asset not in ("BTC", "ETH"):
                continue
            ev_all = fl.index[fl[typ]]
            for h in HORIZONS:
                fwd = np.log(c.shift(-h) / c)
                base = fwd[fwd.index >= start].dropna()
                # olay günü varlığın o günkü (veya sonraki ilk) kapanışı
                evd = [d for d in _decluster(ev_all, h)]
                vals = []
                for d in evd:
                    j = fwd.index.searchsorted(d)
                    if j < len(fwd) and (fwd.index[j] - d).days <= 3 and fwd.iloc[j] == fwd.iloc[j]:
                        vals.append((fwd.index[j], float(fwd.iloc[j])))
                if len(vals) < MIN_EVENTS or len(base) < 200:
                    rows.append({"type": typ, "asset": asset, "h": h, "n": len(vals), "proven": False})
                    continue
                r = pd.Series([v for _, v in vals], index=[d for d, _ in vals])
                mu = float(base.mean())
                a = r - mu
                sd = float(r.std(ddof=1))
                t = float(a.mean() / sd * math.sqrt(len(r))) if sd > 0 else 0.0
                thirds = [float(x.mean()) for x in np.array_split(a, 3)]
                side = int(np.sign(a.mean()))
                hit = float((np.sign(r) == side).mean()) if side else 0.5
                rows.append({"type": typ, "asset": asset, "h": h, "n": int(len(r)),
                             "event_bps": round(float(r.mean()) * 1e4, 1), "drift_bps": round(mu * 1e4, 1),
                             "alpha_bps": round(float(a.mean()) * 1e4, 1), "t": round(t, 2), "hit": round(hit, 3),
                             "thirds_bps": [round(x * 1e4, 1) for x in thirds], "side": side,
                             "last_event": str(r.index[-1].date())})
    tested = [x for x in rows if "t" in x]
    t_req = required_t(len(tested))
    for x in tested:
        same = sum(1 for v in x["thirds_bps"] if np.sign(v) == x["side"])
        x["proven"] = bool(abs(x["t"]) >= t_req and same >= 2 and np.sign(x["event_bps"]) == x["side"]
                           and x["hit"] >= 0.5)
    tested.sort(key=lambda x: -abs(x["t"]))
    counts = {typ: int(fl[typ].sum()) for typ in fl.columns}
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "test_years": test_years, "n_tests": len(tested),
            "t_required": round(t_req, 2), "event_counts": counts, "rows": tested,
            "proven": [x for x in tested if x["proven"]],
            "data_to": str(end.date()) if pd.notna(end) else None}


# ---------------------------------------------------------------------------
# Canlı
# ---------------------------------------------------------------------------
def load_result(path: str = os.path.join("validation_reports", RESULT_FILE)) -> Optional[Dict[str, Any]]:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def fetch_live(period: str = "6mo") -> Dict[str, pd.Series]:
    out = {}
    try:
        import yfinance as yf
        df = yf.download(list(PANEL_D.values()), period=period, interval="1d", progress=False,
                         auto_adjust=False, threads=True, group_by="ticker")
        for k, sym in PANEL_D.items():
            try:
                s = pd.to_numeric(df[sym]["Close"], errors="coerce").dropna()
                s.index = pd.to_datetime(s.index).tz_localize(None)
                if len(s) > 60:
                    out[k] = s
            except Exception:
                continue
    except Exception:
        pass
    return out


def live(closes: Dict[str, pd.Series], result: Optional[Dict[str, Any]], now: Any = None) -> Dict[str, Any]:
    """Son 5 iş günündeki şok türleri ve her varlık için etkin KANITLI yön kuralları."""
    now = pd.Timestamp(now) if now is not None else pd.Timestamp.now(tz="UTC")
    now = now.tz_convert(None) if now.tzinfo else now
    if not closes:
        return {"error": "günlük şok paneli indirilemedi", "events": [], "assets": {}}
    fl = flags(zscores(closes))
    recent = fl[fl.index >= now.normalize() - pd.Timedelta(days=8)]
    events = [{"date": str(d.date()), "type": t, "name": TYPE_TR[t], "provisional": d.normalize() >= now.normalize()}
              for d, row in recent.iterrows() for t in fl.columns if row[t]]
    assets: Dict[str, Any] = {}
    for x in (result or {}).get("proven") or []:
        hits = [e for e in events if e["type"] == x["type"]]
        if not hits:
            continue
        e = hits[-1]
        bdays = int(np.busday_count(pd.Timestamp(e["date"]).date(), now.date()))
        if bdays >= x["h"]:
            continue
        cur = assets.get(x["asset"])
        if cur is None or abs(x["t"]) > abs(cur["t"]):
            assets[x["asset"]] = {"side": x["side"], "type": x["type"], "name": TYPE_TR[x["type"]], "h": x["h"],
                                  "t": x["t"], "alpha_bps": x["alpha_bps"], "hit": x["hit"], "n": x["n"],
                                  "event_date": e["date"], "provisional": e["provisional"],
                                  "days_left": x["h"] - bdays}
    return {"events": events, "assets": assets, "n_proven_rules": len((result or {}).get("proven") or []),
            "research_date": (result or {}).get("generated_at", "")[:10] or None}


# ---------------------------------------------------------------------------
# Rapor
# ---------------------------------------------------------------------------
def report_lines(res: Dict[str, Any]) -> List[str]:
    L = ["# ⚡ Şok Sonrası Yön Araştırması (Motor B)", "",
         f"_Üretim: {res.get('generated_at', '')[:16]} UTC · son {res.get('test_years')} yıl · test sayısı "
         f"{res.get('n_tests')} · gerekli |t| {res.get('t_required')}_", "",
         "Ölçü: şoktan sonraki 1/5 günlük getiri − koşulsuz ortalama (drift). KANITLI: |t| ≥ gerekli t, "
         "3 dönemin en az 2'sinde aynı işaret, olay sonrası ortalama getiri aynı yönde, isabet ≥ %50.", "",
         "## Olay sayıları (10 yıl, kümelenmeden önce)", ""]
    L += [f"- {TYPE_TR[k]}: {v}" for k, v in (res.get("event_counts") or {}).items()]
    L += ["", "## En güçlü 25 sonuç", "", "| Şok türü | Varlık | Ufuk | n | Olay sonrası (bps) | Alfa (bps) | t | İsabet | 3 dönem | Durum |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for x in (res.get("rows") or [])[:25]:
        L.append(f"| {TYPE_TR[x['type']]} | {x['asset']} | {x['h']}g | {x['n']} | {x['event_bps']:+.1f} | "
                 f"{x['alpha_bps']:+.1f} | {x['t']:+.2f} | %{100 * x['hit']:.0f} | "
                 f"{' / '.join(f'{v:+.0f}' for v in x['thirds_bps'])} | {'✅ KANITLI' if x['proven'] else '—'} |")
    return L


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="validation_reports")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    import direction_research as DR
    closes = {k: s for k, sym in PANEL_D.items() if (s := DR._download(sym, years=12)) is not None}
    res = study(closes)
    res["instruments"] = sorted(closes)
    with open(os.path.join(a.out, RESULT_FILE), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    with open(os.path.join(a.out, "shock_direction_report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(report_lines(res)))
    print("\n".join(report_lines(res))[:5000])


if __name__ == "__main__":
    main()
