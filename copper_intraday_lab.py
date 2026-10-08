"""
Copper intraday lab (v15) — 1-hour and 4-hour bars, every family, funding charged at the real 4h timestamps
=========================================================================================================
Data: COMEX copper HG=F hourly from Yahoo (free history ~2.4 years) + the daily lab's regime views (known at the
previous daily close). The sample is SHORT: first 2/3 = training (selection), last 1/3 = sealed exam (~9 months).
Results must be read with that in mind (Deflated Sharpe is reported for every row).

Families
  * the full daily view library (trend, mean reversion, breakout) re-run on 1h and 4h bars
  * hour-of-day (learnt walk-forward from past days only), trading sessions (Asia / Europe / US / overnight),
    US-session opening-range breakout, last-hour drift
  * pairs: every intraday view x daily regime filters (copper trend, miners leading, China leading indicator, ...)
  * funding-aware variants: the same signal but FLAT across the funding timestamps (00/04/08/12/16/20 UTC)
Costs: 0.08% per unit of turnover (taker + slippage). Funding: at each 4h timestamp an open long pays and an open short
receives rate/2190 (scenarios 0 / 3 / 8 / 15.8 % per year).
CLI: python copper_intraday_lab.py --data copper_data --out copper_out
"""
from __future__ import annotations

import argparse
import json
import math
import os
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

import copper_lab as CL

COST = 0.0008
FUND_HOURS = (0, 4, 8, 12, 16, 20)
SCEN = (0.0, 0.03, 0.08, 0.158)
TRAIN_SHARE = 2 / 3


def bars(H: pd.DataFrame, rule: Optional[str]) -> pd.DataFrame:
    h = H.set_index("time").sort_index()[["Open", "High", "Low", "Close"]].dropna()
    h = h[h.Close > 0]
    if rule:
        h = h.resample(rule, label="left", closed="left").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()
    F = pd.DataFrame({"o": h.Open, "h": h.High, "l": h.Low, "c": h.Close})
    F["r"] = F.c.pct_change()
    F.loc[F.r.abs() > 0.15, "r"] = 0.0                      # bad ticks
    F["atr"] = CL.atr(F.h, F.l, F.c)
    F["rvol20"] = F.r.rolling(20).std() * math.sqrt(252)
    for col in ("gold", "oil", "dxy", "aud", "cny", "spx", "vix", "fxi", "shc", "fcx", "copx", "silver", "realy", "bei", "curve",
                "bdollar", "usdcny_f", "usdaud_f", "tbill", "hy", "nfci", "indpro", "cli_cn", "cli_us", "spec_net", "mm_net"):
        F[col] = np.nan                                      # intraday views use price only; macro enters via daily filters
    return F


def funding_events(F: pd.DataFrame, hours_per_bar: int) -> np.ndarray:
    """events[i] = number of funding timestamps crossed while holding the position chosen at the close of bar i
    (i.e. during bar i+1)."""
    start = F.index
    nxt = np.r_[start[1:].values, (start[-1] + pd.Timedelta(hours=hours_per_bar)).to_datetime64()]
    out = np.zeros(len(F))
    for k in range(len(F)):
        a, b = pd.Timestamp(nxt[k]), pd.Timestamp(nxt[k]) + pd.Timedelta(hours=hours_per_bar)
        # a funding stamp t is crossed if a < t <= b  (position held over (a, b])
        h0 = a.floor("h")
        n = 0
        t = h0 + pd.Timedelta(hours=1)
        while t <= b:
            if t.hour in FUND_HOURS and t.minute == 0:
                n += 1
            t += pd.Timedelta(hours=1)
        out[k] = n
    return out


def rets(pos, F, ev, f, cost=COST):
    p = np.nan_to_num(np.asarray(pos, float))
    rn = np.r_[F.r.to_numpy()[1:], np.nan]
    turn = np.abs(np.diff(np.r_[0.0, p]))
    return p * np.nan_to_num(rn) - cost * turn - p * ev * f / (6 * 365)


def st(x: np.ndarray, per_year: float) -> dict:
    x = x[np.isfinite(x)]
    if len(x) < 200 or x.std() == 0:
        return {}
    eq = np.cumprod(1 + x)
    yrs = len(x) / per_year
    return {"sharpe": float(x.mean() / x.std() * math.sqrt(per_year)), "cagr": float(eq[-1] ** (1 / max(yrs, 1e-9)) - 1),
            "maxdd": float(1 - (eq / np.maximum.accumulate(eq)).min())}


def hour_of_day(F: pd.DataFrame, min_days=60) -> np.ndarray:
    """Walk-forward: each day, long the 3 best and short the 3 worst hours by mean NEXT-bar return over past days only."""
    fwd = F.r.shift(-1)
    hrs = F.index.hour
    days = F.index.normalize()
    out = np.zeros(len(F))
    ud = days.unique()
    for i, d in enumerate(ud):
        if i < min_days:
            continue
        past = days < d - pd.Timedelta(days=1)                         # labels fully known
        m = pd.Series(fwd[past].values, index=hrs[past]).groupby(level=0).mean()
        good, bad = set(m.nlargest(3).index), set(m.nsmallest(3).index)
        cur = days == d
        out[cur] = [1.0 if h in good else (-1.0 if h in bad else 0.0) for h in hrs[cur]]
    return out


def intraday_views(F: pd.DataFrame, tf: str) -> Dict[str, Tuple[str, np.ndarray]]:
    V = {k: v for k, v in CL.views(F).items() if v[0] in ("TREND", "MEANREV", "BREAKOUT")}
    if tf == "1h":
        hr = F.index.hour
        V["saat profili (ileri yürüyen)"] = ("SAAT", hour_of_day(F))
        for nm, hs in (("Asya seansı 00-07 UTC", range(0, 7)), ("Avrupa seansı 07-13 UTC", range(7, 13)),
                       ("ABD seansı 13-20 UTC", range(13, 20)), ("gece 20-24 UTC", range(20, 24))):
            V[f"{nm} long"] = ("SEANS", np.isin(hr, list(hs)).astype(float))
        # US opening range: high/low of the 13:00 UTC bar; breakout inside the US session, flat after 20:00
        day = F.index.normalize()
        orh = F.h.where(hr == 13).groupby(day).transform("max")
        orl = F.l.where(hr == 13).groupby(day).transform("min")
        sess = (hr > 13) & (hr < 20)
        V["ABD açılış aralığı kırılımı"] = ("SEANS", np.where(sess & (F.c > orh), 1.0, np.where(sess & (F.c < orl), -1.0, 0.0)))
        V["son saat (19 UTC) yönü devam"] = ("SEANS", np.where(hr == 19, np.sign(F.c - F.o.where(hr == 13).groupby(day).transform("max")), 0.0))
    return V


def daily_filters(px, fred, cot, idx: pd.DatetimeIndex) -> Dict[str, np.ndarray]:
    """Daily regime views known at the PREVIOUS daily close, mapped onto intraday bars."""
    Fd = CL.frame(px, fred, cot)
    Vd = CL.views(Fd)
    keep = ["madenciler bakırı öncülüyor (FCX−bakır 1 ay)", "Çin öncü göstergesi yükseliyor", "fiyat > SMA200", "momentum 63g",
            "momentum topluluğu 1-3-6-12 ay", "Donchian 200 kırılımı", "dolar (DXY) 3 ay düşüyor", "bakır/altın oranı > SMA100",
            "S&P 500 > SMA200", "COT fon (managed money) 4 hafta artıyor → aynı yön"]
    out = {}
    days = idx.normalize()
    for k in keep:
        if k not in Vd:
            continue
        s = pd.Series(Vd[k][1], index=Fd.index).shift(1)               # yesterday's close -> usable all of today
        ud = days.unique()
        m = s.reindex(s.index.union(ud)).ffill().reindex(ud).fillna(0)
        out[k] = m.reindex(days).to_numpy()
    return out


def run_tf(H, tf: str, filters: Dict[str, np.ndarray], fast=False) -> dict:
    rule = None if tf == "1h" else "4h"
    hpb = 1 if tf == "1h" else 4
    F = bars(H, rule)
    per_year = len(F) / max((F.index[-1] - F.index[0]).days / 365.25, 1e-9)
    ev = funding_events(F, hpb)
    cut = F.index[int(len(F) * TRAIN_SHARE)]
    tr, ex = F.index < cut, F.index >= cut
    V = intraday_views(F, tf)
    flt = {k: v for k, v in (daily_filters(*filters["src"], F.index) if filters else {}).items()}
    fund_bar = np.isin(((F.index + pd.Timedelta(hours=hpb)).hour), FUND_HOURS)    # bar ends on a funding stamp
    rows, store = [], {}

    def add(name, fam, mode, pos):
        row = {"strateji": name, "aile": fam, "yön": mode}
        for f in SCEN:
            r = rets(pos, F, ev, f)
            a, b = st(r[tr], per_year), st(r[ex], per_year)
            if not a or not b:
                return
            row[f"eğ_{f}"], row[f"sı_{f}"], row[f"sı_yıllık_{f}"], row[f"sı_dd_{f}"] = a["sharpe"], b["sharpe"], b["cagr"], b["maxdd"]
        p = np.nan_to_num(np.asarray(pos, float))
        row["işlem_eğitim"] = int((np.abs(np.diff(p[tr])) > 0).sum())
        row["piyasada"] = float((p != 0).mean())
        row["eğ_en_kötü"] = min(row[f"eğ_{f}"] for f in SCEN)
        rows.append(row)
        store[(name, mode)] = pos

    for name, (fam, v) in V.items():
        for mode, fn in CL.MODES.items():
            pos = fn(np.nan_to_num(v))
            add(name, fam, mode, pos)
            if tf == "1h":
                add(f"{name} · fonlama anında pozisyonsuz", fam + "+FONLAMASIZ", mode, np.where(fund_bar, 0.0, pos))
    T = pd.DataFrame(rows)
    if len(T) and flt:
        base = T.sort_values("eğ_en_kötü", ascending=False).drop_duplicates(["strateji", "yön"]).head(10 if fast else 30)
        for b in base.itertuples():
            bp = store[(b.strateji, b.yön)]
            for fn, fv in flt.items():
                add(f"{b.strateji} + [günlük] {fn}", "İKİLİ", b.yön, np.where(np.sign(bp) == np.sign(fv), bp, 0.0))
    T = pd.DataFrame(rows)
    n = len(T)
    var = float(T.eğ_en_kötü.var()) if n > 1 else 0.0
    T["dsr"] = [CL.deflated_sharpe(s * math.sqrt(252 / per_year), int(tr.sum()), n, var * 252 / per_year) for s in T.eğ_en_kötü]
    cand = T[T.işlem_eğitim >= 30].sort_values("eğ_en_kötü", ascending=False)
    bh = {f"{f}": st(rets(np.ones(len(F)), F, ev, f)[ex], per_year).get("cagr") for f in SCEN}
    fam = T.groupby(["aile", "yön"]).agg(n=("strateji", "size"), eğitim=("eğ_0.03", "mean"), sınav=("sı_0.03", "mean"),
                                         sınav_158=("sı_0.158", "mean")).reset_index().sort_values("sınav", ascending=False)
    return {"tf": tf, "bars": len(F), "train_until": str(cut), "exam_bars": int(ex.sum()), "n_trials": n, "bh": bh,
            "chosen": CL._row(cand.iloc[0]) if len(cand) else None, "top": cand.head(20).round(3).to_dict("records"),
            "families": fam.round(3).to_dict("records"),
            "exam_positive_share_3": float((T["sı_0.03"] > 0).mean()), "_T": T}


def report(R: dict) -> str:
    L = ["# 🟠 Bakır gün içi laboratuvarı v15 — 1 saatlik ve 4 saatlik mumlar", "",
         "_Veri: COMEX bakır (HG=F) saatlik, ~2,4 yıl. İlk 2/3 eğitim (seçim), son 1/3 mühürlü sınav (~9 ay). Maliyet %0,08/işlem; "
         "fonlama yalnızca 00/04/08/12/16/20 UTC anlarında açık olan pozisyondan kesilir (long öder, short alır). "
         "**Kısa örneklem: sınav sonuçları güçlü kanıt değildir; Deflated Sharpe (DSR) her satırda.**_", ""]
    for tf in ("1h", "4h"):
        r = R.get(tf)
        if not r:
            continue
        L += [f"## {tf} — {r['bars']:,} mum · eğitim {r['train_until'][:10]}'e kadar · {r['n_trials']:,} deneme", "",
              "Bakırı tutmak (sınav yıllık): " + " · ".join(f"fonlama %{float(k) * 100:.1f}: {CL._p(v)}" for k, v in r["bh"].items()),
              f"Sınavda pozitif Sharpe veren denemelerin oranı (fonlama %3): %{r['exam_positive_share_3'] * 100:.0f}", ""]
        c = r.get("chosen")
        if c:
            L += [f"**Eğitimin seçimi** (4 fonlama senaryosunun en kötüsüne göre): {c['strateji']} · {c['yön']} · DSR {c['dsr']:.2f}", "",
                  "| | " + " | ".join(f"%{f * 100:.1f}" for f in SCEN) + " |", "|---" * (len(SCEN) + 1) + "|",
                  "| eğitim Sharpe | " + " | ".join(f"{c[f'eğ_{f}']:.2f}" for f in SCEN) + " |",
                  "| **sınav Sharpe** | " + " | ".join(f"**{c[f'sı_{f}']:.2f}**" for f in SCEN) + " |",
                  "| sınav yıllık | " + " | ".join(CL._p(c[f"sı_yıllık_{f}"]) for f in SCEN) + " |", ""]
        L += ["| Aile | Yön | Deneme | Eğitim Sharpe (%3) | **Sınav Sharpe (%3)** | Sınav Sharpe (%15,8) |", "|---|---|---|---|---|---|"]
        for f in r["families"]:
            L.append(f"| {f['aile']} | {f['yön']} | {f['n']} | {f['eğitim']:.2f} | **{f['sınav']:.2f}** | {f['sınav_158']:.2f} |")
        L += ["", "| # | Strateji | Yön | Eğitim (en kötü) | DSR | Sınav Sharpe %0 / %3 / %8 / %15,8 | Sınav yıllık (%3) |", "|---|---|---|---|---|---|---|"]
        for i, t in enumerate(r["top"], 1):
            L.append(f"| {i} | {t['strateji']} | {t['yön']} | {t['eğ_en_kötü']:.2f} | {t['dsr']:.2f} | "
                     + " / ".join(f"{t[f'sı_{f}']:.2f}" for f in SCEN) + f" | {CL._p(t['sı_yıllık_0.03'])} |")
        L.append("")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="copper_data")
    ap.add_argument("--out", default="copper_out")
    a = ap.parse_args()
    px, fred, cot, hourly, bg, bgc = CL.load(a.data)
    if hourly is None or len(hourly) < 2000:
        print("[bakır-gün içi] saatlik veri yok", flush=True)
        return
    R = {}
    for tf in ("1h", "4h"):
        R[tf] = run_tf(hourly, tf, {"src": (px, fred, cot)})
        R[tf].pop("_T").to_csv(os.path.join(a.out, f"copper_intraday_{tf}.csv.gz"), index=False, compression="gzip", float_format="%.5g")
    os.makedirs(a.out, exist_ok=True)
    open(os.path.join(a.out, "copper_intraday_report.md"), "w", encoding="utf-8").write(report(R))
    print("[bakır-gün içi] bitti", flush=True)


if __name__ == "__main__":
    main()
