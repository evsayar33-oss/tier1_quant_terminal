"""
Karma Lab (v13.0) — does the proven shock signal improve the karma portfolio?
=============================================================================
Karma portfolio = 50% risk parity (S&P 500, Nasdaq-100, gold, silver; 10% vol
target, x2) + 50% crypto long/short ensemble (carry 3/7/30 + risk-adjusted
momentum 28, vol-targeted 20%).

Overlay tested here (the only signal that survived v12.1 on both indices):
  while an EXTREME VIX panic is active, the equity legs (S&P/Nasdaq) of the risk
  parity get a temporary weight boost; optionally only if inflation is low.

Honesty:
  * every overlay variant is PRE-REGISTERED below (24 of them) and ALL are
    reported, plus the family average — no picking the best one afterwards;
  * all signals use only data known at the previous close (1-day lag);
  * 2000-2016 = period on which the shock signal was found; 2017+ = exam.
    NOTE: v12.1's exam already looked at 2017+ shock events, so the 2017+
    numbers here are NOT a fully clean test — the report says so;
  * the clean part is the PORTFOLIO question (did boosting really help after
    financing, costs and the losses of other days?) which v12.1 never tested.

CLI: python karma_lab.py --data shock_data --xs xs_data/xs_panel.csv.gz --out karma_out
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import os
from typing import Dict, Optional

import numpy as np
import pandas as pd

import shock_lab as S

TRAIN0, EXAM0 = pd.Timestamp("2000-09-01"), pd.Timestamp("2017-01-01")
RP_ASSETS = {"SPX": "^GSPC", "NQ": "^NDX", "XAU": "GC=F", "XAG": "SI=F"}
EQUITY = ("SPX", "NQ")
COST = 0.0005             # per unit of turnover (futures / perps)
TARGET = 0.10             # risk-parity vol target before the x2
RP_LEV = 2.0

TRIGGERS = {
    "VIX son 3 yılın %98 üstü": lambda F: F.vix_pct3y >= 0.98,
    "VIX ≥ 35": lambda F: F.vix >= 35,
    "VIX ≥ 200g ort. ×1.8": lambda F: F.vix_ma200 >= 1.8,
}
GATES = {"makro kapı yok": None, "TÜFE kendi tarihinin alt yarısı": lambda F: F.cpi_xpct < 0.5}
BOOSTS = (1.5, 2.0)       # equity-leg multiplier while active
DAYS = (40, 60)           # how long a trigger keeps the boost on


def variants():
    for (tn, t), (gn, g), b, d in itertools.product(TRIGGERS.items(), GATES.items(), BOOSTS, DAYS):
        yield {"ad": f"{tn} · {gn} · hisse ×{b:g} · {d}g", "trig": t, "gate": g, "boost": b, "days": d,
               "tetik": tn, "kapı": gn}


# ---------------------------------------------------------------- data
def closes(px: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    C = pd.DataFrame({k: px[s].Close for k, s in RP_ASSETS.items() if s in px})
    C = C[C.index >= pd.Timestamp("1999-01-01")].sort_index()
    return C.ffill(limit=3)


def active_mask(F: pd.DataFrame, v: dict) -> pd.Series:
    """Boost on for `days` sessions after a trigger day (trigger known at the close -> applied next day)."""
    m = v["trig"](F).fillna(False)
    if v["gate"] is not None:
        m = m & v["gate"](F).fillna(False)
    on = np.zeros(len(m), bool)
    for i in np.where(m.values)[0]:
        on[i + 1:i + 1 + v["days"]] = True
    return pd.Series(on, index=F.index)


def risk_parity(C: pd.DataFrame, tbill: pd.Series, boost: Optional[pd.Series] = None, mult: float = 1.0) -> pd.Series:
    r = np.log(C / C.shift(1))
    vol = r.rolling(60, min_periods=40).std() * math.sqrt(252)
    n = C.shape[1]
    w = (1.0 / vol).div(n) * TARGET
    w = w.where(C.notna())
    pv = (w.shift(1) * r).sum(1).rolling(60, min_periods=40).std() * math.sqrt(252)
    w = w.mul((TARGET / pv).clip(upper=3), axis=0) * RP_LEV
    if boost is not None:
        b = boost.reindex(C.index).fillna(False).values
        for k in EQUITY:
            if k in w:
                w.loc[b, k] = w.loc[b, k] * mult
    w = w.shift(1).fillna(0)                            # decided at d-1 close, held over day d
    gross = (w * np.expm1(r).fillna(0)).sum(1)
    turn = w.diff().abs().sum(1)
    fin = (w.sum(1) - 1).clip(lower=0) * tbill.reindex(C.index).ffill().fillna(0.03) / 252
    return (gross - COST * turn - fin).fillna(0)


def crypto_sleeve(path: Optional[str]) -> Optional[pd.Series]:
    if not path or not os.path.exists(path):
        return None
    import xs_lab as X
    P = pd.read_csv(path)
    W = X.wide(P)
    Cc = W["close"]
    R = np.log(Cc / Cc.shift(1)).values
    Fd = W["funding"].values
    F = X.features(W)
    vol = np.log(Cc / Cc.shift(1)).rolling(28, min_periods=20).std()
    outs = []
    for sig in ("carry:3", "carry:7", "carry:30", "rmom:28"):
        fam = []
        for n, q, wt, rb in itertools.product((20, 50, 100), (0.2, 0.33), ("ew", "iv"), (1, 7)):
            U = X.universe(W, n)
            w = X.weights(F[sig], U, q, "LS", wt, vol, rb)
            fam.append(np.expm1(X.pnl(w, R, Fd, X.COST_N[n])))
        outs.append(np.mean(fam, 0))
    ens = pd.Series(np.mean(outs, 0), index=Cc.index)
    rv = ens.rolling(60, min_periods=30).std().shift(1) * math.sqrt(365)
    s = ens * (0.20 / rv).clip(upper=3).fillna(1)
    s.index = pd.to_datetime(s.index, utc=True).tz_convert(None).normalize()
    return s


# ---------------------------------------------------------------- stats
def stats(s: pd.Series, a, b, per=252) -> dict:
    x = s[(s.index >= a) & (s.index < b)].dropna()
    if len(x) < 60:
        return {}
    eq = (1 + x).cumprod()
    yrs = (x.index[-1] - x.index[0]).days / 365.25
    sh = x.mean() / x.std() * math.sqrt(per) if x.std() > 0 else np.nan
    return {"cagr": float(eq.iloc[-1] ** (1 / max(yrs, 1e-9)) - 1), "maxdd": float(1 - (eq / eq.cummax()).min()),
            "sharpe": float(sh), "calmar": float((eq.iloc[-1] ** (1 / yrs) - 1) / max(1e-9, 1 - (eq / eq.cummax()).min()))}


def research(px, fred, xs_path=None) -> dict:
    C = closes(px)
    F = S.features(px, fred, "SPX").reindex(C.index).ffill(limit=3)
    tb = F["tbill"]
    end = C.index[-1] + pd.Timedelta(days=1)
    out = {"generated_at": pd.Timestamp.now("UTC").isoformat(), "assets": list(C.columns),
           "periods": {"eğitim": [str(TRAIN0.date()), str(EXAM0.date())], "sınav": [str(EXAM0.date()), str(end.date())]}}
    base = risk_parity(C, tb)
    spx = C["SPX"].pct_change().fillna(0)
    rows = []
    for lab, s in (("Risk paritesi ×2 (overlay yok)", base), ("S&P 500 al-tut 1x", spx),
                   ("S&P 500 al-tut 2x (T-bill finansmanlı)", 2 * spx - tb.fillna(0.03) / 252)):
        rows.append({"ad": lab, "eğitim": stats(s, TRAIN0, EXAM0), "sınav": stats(s, EXAM0, end), "tür": "referans"})
    series = {"base": base}
    for v in variants():
        on = active_mask(F, v)
        s = risk_parity(C, tb, on, v["boost"])
        series[v["ad"]] = s
        rows.append({"ad": v["ad"], "tetik": v["tetik"], "kapı": v["kapı"], "boost": v["boost"], "gün": v["days"], "tür": "overlay",
                     "eğitim": stats(s, TRAIN0, EXAM0), "sınav": stats(s, EXAM0, end),
                     "aktif_gün_eğitim": int(on[(on.index >= TRAIN0) & (on.index < EXAM0)].sum()),
                     "aktif_gün_sınav": int(on[on.index >= EXAM0].sum()),
                     "fark_sınav": _diff(s, base, EXAM0, end), "fark_eğitim": _diff(s, base, TRAIN0, EXAM0)})
    out["rp_rows"] = rows
    ov = [r for r in rows if r["tür"] == "overlay"]
    fam = {}
    for key in ("tetik", "kapı", "boost", "gün"):
        for val in sorted({r[key] for r in ov}, key=str):
            g = [r for r in ov if r[key] == val]
            fam[f"{key}: {val}"] = {"n": len(g),
                                    "Δsharpe_eğitim": float(np.mean([r["fark_eğitim"]["Δsharpe"] for r in g])),
                                    "Δsharpe_sınav": float(np.mean([r["fark_sınav"]["Δsharpe"] for r in g])),
                                    "Δcagr_sınav": float(np.mean([r["fark_sınav"]["Δcagr"] for r in g])),
                                    "Δdd_sınav": float(np.mean([r["fark_sınav"]["Δmaxdd"] for r in g])),
                                    "sınavda_iyileşen": float(np.mean([r["fark_sınav"]["Δsharpe"] > 0 for r in g]))}
    out["families"] = fam
    out["all_better_exam"] = float(np.mean([r["fark_sınav"]["Δsharpe"] > 0 for r in ov]))
    # yearly table: base vs family-average overlay
    avg = pd.concat([series[r["ad"]] for r in ov], axis=1).mean(1)
    yr = lambda s: {int(y): float((1 + g).prod() - 1) for y, g in s[s.index >= TRAIN0].groupby(s.index[s.index >= TRAIN0].year)}
    out["yearly"] = {"Risk paritesi ×2": yr(base), "Overlay ailesi ortalaması": yr(avg), "S&P 500 1x": yr(spx)}
    # karma portfolio (crypto sleeve available from 2021)
    cs = crypto_sleeve(xs_path)
    if cs is not None:
        k0 = pd.Timestamp("2021-01-01")
        kr = {}
        for lab, s in (("KARMA (overlay yok)", base), ("KARMA + overlay ailesi ortalaması", avg)):
            m = _join(s, cs, k0)
            kr[lab] = 0.5 * m.iloc[:, 0] + 0.5 * m.iloc[:, 1]
        best_tr = max(ov, key=lambda r: r["eğitim"].get("sharpe", -9))["ad"]
        m = _join(series[best_tr], cs, k0)
        kr[f"KARMA + eğitimin en iyi overlay'i ({best_tr})"] = 0.5 * m.iloc[:, 0] + 0.5 * m.iloc[:, 1]
        kr["S&P 500 1x"] = spx[spx.index >= k0]
        e = max(s.index[-1] for s in kr.values()) + pd.Timedelta(days=1)
        out["karma"] = {lab: {"2021+": stats(s, k0, e), "2021-2023": stats(s, k0, pd.Timestamp("2024-01-01")),
                              "2024+": stats(s, pd.Timestamp("2024-01-01"), e), "yearly": yr(s)} for lab, s in kr.items()}
    return out


def _join(a: pd.Series, b: pd.Series, k0) -> pd.DataFrame:
    """Calendar union: index legs earn 0 on weekends/holidays, crypto earns its 7-day returns."""
    m = pd.concat([a, b], axis=1, sort=True)
    last = min(a.index[-1], b.index[-1])
    return m[(m.index >= k0) & (m.index <= last)].fillna(0)


def _diff(s, b, a, e):
    x, y = stats(s, a, e), stats(b, a, e)
    if not x or not y:
        return {"Δsharpe": 0.0, "Δcagr": 0.0, "Δmaxdd": 0.0}
    return {"Δsharpe": x["sharpe"] - y["sharpe"], "Δcagr": x["cagr"] - y["cagr"], "Δmaxdd": x["maxdd"] - y["maxdd"]}


# ---------------------------------------------------------------- report
def _p(x, d=1):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"%{x * 100:+.{d}f}"


def _st(d):
    return "—" if not d else f"{_p(d['cagr'])} / %{d['maxdd'] * 100:.0f} / {d['sharpe']:.2f}"


def report_md(r: dict) -> str:
    L = ["# 🧪 Karma Lab v13 — uç VIX paniği katmanı karma portföyü iyileştiriyor mu?", "",
         f"_Üretim: {r['generated_at'][:16]} UTC · varlıklar: {', '.join(r['assets'])} · eğitim {r['periods']['eğitim'][0]}→{r['periods']['eğitim'][1]} · "
         f"sınav {r['periods']['sınav'][0]}→. 24 overlay varyantı ÖNCEDEN tanımlandı, hepsi aşağıda. "
         "Uyarı: 2017+ şok olayları v12.1'in sınavında görüldü; buradaki yeni soru, kaldıraç artışının finansman, maliyet ve diğer günlerin "
         "kayıplarından sonra portföyü gerçekten iyileştirip iyileştirmediği. Risk paritesi oynaklık hedeflidir: sakin yıllarda (ör. 2017) "
         "toplam kaldıraç 3–4.5x'e çıkar, bu yüzden o yılların getirisi yüksektir._", "",
         f"## Sonuç: 24 varyantın **%{r['all_better_exam'] * 100:.0f}'ı** sınavda Sharpe'ı artırdı", "",
         "### 1) Aileler (her satır, o özelliği taşıyan tüm varyantların ortalaması; fark = overlay − overlay'siz risk paritesi)", "",
         "| Aile | Varyant | ΔSharpe eğitim | **ΔSharpe sınav** | Δyıllık sınav | Δmaks. düşüş sınav | Sınavda iyileşen |", "|---|---|---|---|---|---|---|"]
    for k, f in r["families"].items():
        L.append(f"| {k} | {f['n']} | {f['Δsharpe_eğitim']:+.3f} | **{f['Δsharpe_sınav']:+.3f}** | {_p(f['Δcagr_sınav'], 2)} | {_p(f['Δdd_sınav'], 1)} | %{f['sınavda_iyileşen'] * 100:.0f} |")
    L += ["", "### 2) Tüm varyantlar (yıllık / maks. düşüş / Sharpe)", "",
          "| Strateji | Aktif gün eğitim / sınav | Eğitim | **Sınav** | ΔSharpe sınav |", "|---|---|---|---|---|"]
    for x in r["rp_rows"]:
        act = f"{x.get('aktif_gün_eğitim', '')} / {x.get('aktif_gün_sınav', '')}" if x["tür"] == "overlay" else "—"
        ds = f"{x['fark_sınav']['Δsharpe']:+.3f}" if x["tür"] == "overlay" else "—"
        L.append(f"| {x['ad']} | {act} | {_st(x['eğitim'])} | **{_st(x['sınav'])}** | {ds} |")
    L += ["", "### 3) Yıllar", "", "| Yıl | " + " | ".join(r["yearly"]) + " |", "|---" * (1 + len(r["yearly"])) + "|"]
    yrs = sorted(next(iter(r["yearly"].values())))
    for y in yrs:
        L.append(f"| {y} | " + " | ".join(_p(v.get(y), 0) for v in r["yearly"].values()) + " |")
    if r.get("karma"):
        L += ["", "### 4) KARMA portföy (50% risk paritesi + 50% kripto L/S, 2021→)", "",
              "| Portföy | 2021+ yıllık / DD / Sharpe | 2021–2023 | 2024+ |", "|---|---|---|---|"]
        for lab, v in r["karma"].items():
            L.append(f"| {lab} | {_st(v['2021+'])} | {_st(v['2021-2023'])} | {_st(v['2024+'])} |")
        ks = list(r["karma"])
        yy = sorted(r["karma"][ks[0]]["yearly"])
        L += ["", "| Yıl | " + " | ".join(ks) + " |", "|---" * (1 + len(ks)) + "|"]
        for y in yy:
            L.append(f"| {y} | " + " | ".join(_p(r["karma"][k]["yearly"].get(y), 0) for k in ks) + " |")
    else:
        L += ["", "_Kripto paneli bulunamadı (xsdata dalı): karma tablosu atlandı._"]
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="shock_data")
    ap.add_argument("--xs", default="xs_data/xs_panel.csv.gz")
    ap.add_argument("--out", default="karma_out")
    a = ap.parse_args()
    px, fred, _ = S.load(a.data)
    res = research(px, fred, a.xs)
    os.makedirs(a.out, exist_ok=True)
    open(os.path.join(a.out, "karma_report.md"), "w", encoding="utf-8").write(report_md(res))
    json.dump(json.loads(json.dumps(res, default=str)), open(os.path.join(a.out, "karma_results.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("[karma] bitti", flush=True)


if __name__ == "__main__":
    main()
