"""
Long Strategy Lab (v8.0) — 8-10 years, daily bars, an UNTOUCHED final 2 years
============================================================================
Answers "does anything survive a long test?" with the protocol a fund would
use before allocating:

1. DATA  signal_panel_daily.csv.gz (long_replay.py: the system's every output,
         point-in-time, once a day for ~10 years) + prices_daily.csv.gz +
         CFTC COT positioning (alt_data.py, weekly, published lag respected).
2. SPLIT the LAST 2 YEARS of every asset are a sealed exam: no selection,
         ranking, parameter or threshold ever looks at them.
         Everything before is the TRAINING period.
3. NARROW universe (a few thousand rules, not 165,000): every system output,
         every factor, COT positioning and a handful of classic trend rules,
         at 3 holding horizons (1 day / 1 week / 1 month, weekly and monthly
         use the average of the signal over the period), sign or strong-only
         (|z|>0.5), with or against, long+short / long-only / short-only,
         exit by signal or by a 3xATR trailing stop.
4. TRAINING evidence: yearly walk-forward of the selection procedure (pick the
         best rule on all data BEFORE each year, trade it during that year),
         Deflated Sharpe with the effective number of trials.
5. EXAM: the rule picked on the whole training period is traded ONCE on the
         sealed 2 years. Also the top 20 of training are shown with their exam
         result (how much "great backtests" decay) and whole rule families
         are scored on the exam (family-level evidence has almost no
         selection bias).

Execution: decision before the open of day D+1 from data <= day D; entries and
exits at the next OPEN (overnight gap belongs to the old position); stops on
the daily low/high, a gap through the stop fills at the open; fees per side and
perp funding (longs pay, shorts get nothing) as in strategy_lab.

CLI: python long_lab.py --panel long_reports/signal_panel_daily.csv.gz \
                        --prices long_reports/prices_daily.csv.gz --alt long_reports/cot_long.csv.gz --out long_out
"""
from __future__ import annotations

import argparse
import json
import math
import os
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

import strategy_lab as L

HOLDOUT_DAYS = 730
CADS = (1, 5, 21)                       # trading-day horizons: day / week / month
CAD_TR = {1: "1 gün", 5: "1 hafta", 21: "1 ay"}
MODES = ("LS", "LO", "SO")
EXITS = ({"type": "sig"}, {"type": "trail", "k": 3.0})
Z_N, Z_MIN = 252, 60
MIN_TRADES = 6                          # per selection window (monthly rules trade rarely)
CRIT = {"wf_t": 2.0, "wf_pos": 0.6, "dsr": 0.90, "exam_t": 1.5, "exam_alpha_t": 1.0}
TECH = {"tsmom": (20, 60, 120, 250), "ema": (50, 100, 200)}
EXCLUDE = ("asset", "t", "mac::regime_id")


# ---------------------------------------------------------------- features
def _per_year(a: str) -> float:
    return 365.0 if a in ("BTC", "ETH") else 252.0


def build_features(px: pd.DataFrame, panel: Optional[pd.DataFrame], alt: Optional[pd.DataFrame]) -> Dict[str, np.ndarray]:
    """Every feature value KNOWN BEFORE the open of each bar (index = bar date)."""
    dates = px.index
    decision = dates + pd.Timedelta("30min")                      # replay decided at D 00:30 from bars <= D-1
    F: Dict[str, np.ndarray] = {}
    if panel is not None and len(panel):
        S = panel.sort_values("t").drop_duplicates("t", keep="last").set_index("t")
        S = S[[c for c in S.columns if c not in EXCLUDE]].apply(pd.to_numeric, errors="coerce")
        S = S.loc[:, S.notna().mean() > 0.3]
        tv = S.index.values
        pos = np.searchsorted(tv, decision.values, side="right") - 1
        ok = (pos >= 0) & ((decision.values - tv[np.clip(pos, 0, len(tv) - 1)]) <= np.timedelta64(5, "D"))
        for c in S.columns:
            v = S[c].values.astype(float)
            F[c] = np.where(ok, v[np.clip(pos, 0, len(v) - 1)], np.nan)
    if alt is not None and len(alt):
        A = alt[["t"] + [c for c in alt.columns if c.startswith("alt::cot")]].groupby("t").last().sort_index()
        for c in A.columns:
            x = A[c].dropna()
            if len(x) < 30:
                continue
            tv = x.index.values
            pos = np.searchsorted(tv, decision.values, side="right") - 1
            ok = (pos >= 0) & ((decision.values - tv[np.clip(pos, 0, len(tv) - 1)]) <= np.timedelta64(15, "D"))
            F[c] = np.where(ok, x.values[np.clip(pos, 0, len(x) - 1)], np.nan)
    c = px["Close"]
    for n in TECH["tsmom"]:                                        # known at the open: uses closes up to D-1
        F[f"tech:tsmom:{n}"] = np.log(c / c.shift(n)).shift(1).values
    for n in TECH["ema"]:
        F[f"tech:ema:{n}"] = (c / c.ewm(span=n, adjust=False).mean() - 1).shift(1).values
    return F


def _z(x: np.ndarray) -> np.ndarray:
    s = pd.Series(x)
    return ((s - s.rolling(Z_N, min_periods=Z_MIN).mean()) / s.rolling(Z_N, min_periods=Z_MIN).std()).values


def _period_start(dates: pd.DatetimeIndex, cad: int) -> np.ndarray:
    if cad == 1:
        return np.ones(len(dates), bool)
    key = (dates.isocalendar().week.values + 100 * dates.isocalendar().year.values) if cad == 5 else (dates.month + 100 * dates.year).values
    key = np.asarray(key)
    return np.r_[True, key[1:] != key[:-1]]


def target(x: np.ndarray, dates: pd.DatetimeIndex, cad: int, op: str, inv: bool) -> np.ndarray:
    """Desired position (-1/0/+1) at each open."""
    s = pd.Series(x, dtype=float)
    if cad > 1:
        s = s.rolling(cad, min_periods=1).mean()                   # average of the signal over the period
    v = s.values
    if op == "z":
        z = _z(v)
        out = np.where(z > 0.5, 1.0, np.where(z < -0.5, -1.0, 0.0))
    else:
        out = np.sign(np.nan_to_num(v))
    if inv:
        out = -out
    if cad > 1:                                                    # decided at the first open of the period, held
        first = _period_start(dates, cad)
        idx = np.maximum.accumulate(np.where(first, np.arange(len(v)), 0))
        out = out[idx]
    return out


# ---------------------------------------------------------------- simulator
def simulate(T: np.ndarray, exits: List[dict], px: pd.DataFrame, cost: float, fund_day: float) -> Tuple[np.ndarray, np.ndarray]:
    """T: (N, n) desired positions; returns daily net log returns (N, n) and trade counts (N,)."""
    O, H, Lw, C = (px[k].values.astype(float) for k in ("Open", "High", "Low", "Close"))
    n = len(C)
    tr = np.maximum(H - Lw, np.maximum(np.abs(H - np.r_[C[0], C[:-1]]), np.abs(Lw - np.r_[C[0], C[:-1]])))
    atr = pd.Series(tr).rolling(14, min_periods=5).mean().shift(1).values        # known at the open
    gap_days = np.r_[1.0, np.diff(px.index.values).astype("timedelta64[h]").astype(float) / 24.0]
    k = np.array([e.get("k", np.inf) if e["type"] == "trail" else np.inf for e in exits])
    N = T.shape[0]
    R = np.zeros((N, n))
    ntr = np.zeros(N)
    pos = np.zeros(N)
    ext = np.zeros(N)
    blocked = np.zeros(N)
    for t in range(1, n):
        g = math.log(O[t] / C[t - 1])
        r = pos * g                                                # overnight: old position
        want = T[:, t]
        want = np.where((blocked != 0) & (want == blocked), 0.0, want)
        blocked = np.where(T[:, t] != blocked, 0.0, blocked)
        chg = want != pos
        r -= cost * np.abs(want - pos)
        ntr += chg & (want != 0)
        newpos = want
        ext = np.where(chg, O[t], ext)
        a = atr[t] if np.isfinite(atr[t]) else np.inf
        stop = np.where(newpos > 0, ext - k * a, np.where(newpos < 0, ext + k * a, np.nan))
        with np.errstate(invalid="ignore"):
            hit = ((newpos > 0) & (Lw[t] <= stop)) | ((newpos < 0) & (H[t] >= stop))
        fill = np.where(newpos > 0, np.minimum(O[t], stop), np.maximum(O[t], stop))
        intra = np.where(hit, newpos * np.log(np.where(hit, fill, C[t]) / O[t]), newpos * math.log(C[t] / O[t]))
        r += intra - np.where(hit, cost * np.abs(newpos), 0.0)
        r -= np.where(newpos > 0, fund_day * gap_days[t], 0.0)
        blocked = np.where(hit, newpos, blocked)
        pos = np.where(hit, 0.0, newpos)
        ext = np.where(pos > 0, np.maximum(ext, H[t]), np.where(pos < 0, np.minimum(ext, Lw[t]), ext))
        R[:, t] = r
    return R, ntr


# ---------------------------------------------------------------- universe
def universe(F: Dict[str, np.ndarray], dates: pd.DatetimeIndex, train_end: int):
    """(meta, target) for every rule. A signal enters only if it has enough
    history IN THE TRAINING PERIOD (decided without looking at the exam)."""
    out = []
    for src, x in F.items():
        xt = x[:train_end]
        fin = np.isfinite(xt)
        if fin.sum() < 250 or np.nanstd(xt) == 0:
            continue
        two_sided = (np.nanmean(xt > 0) > 0.1) and (np.nanmean(xt < 0) > 0.1)
        ops = (("sign", "z") if two_sided else ("z",))
        for cad in CADS:
            for op in ops:
                for inv in (False, True):
                    tg = target(x, dates, cad, op, inv)
                    out.append(({"src": src, "cad": cad, "op": op, "inv": inv}, tg))
    out.append(({"src": "bench:long", "cad": 1, "op": "sign", "inv": False}, np.ones(len(dates))))
    return out


def label(m: dict) -> str:
    if m["src"] == "bench:long":
        return "Sürekli long (referans)"
    src = m["src"]
    if src.startswith("tech:"):
        _, fam, p = src.split(":")
        nm = {"tsmom": "Momentum", "ema": "EMA trend"}[fam] + f" ({p} gün)"
    else:
        nm = L.tr_name(src)
    s = ("TERS " if m["inv"] else "") + nm + (" (güçlü ∣z∣>0.5)" if m["op"] == "z" else "")
    s += f" · {CAD_TR[m['cad']]}" + (" ort." if m["cad"] > 1 else "")
    mode = {"LS": "long+short", "LO": "sadece long", "SO": "sadece short"}[m.get("mode", "LS")]
    ex = m.get("exit", {"type": "sig"})
    return f"{s} · {mode} · " + ("sinyalle çıkış" if ex["type"] == "sig" else f"iz süren stop {ex['k']:.0f}×ATR")


def family(m: dict) -> str:
    s = m["src"]
    fam = ("referans" if s.startswith("bench") else "teknik" if s.startswith("tech:") else "COT" if "cot" in s
           else "faktör" if s.startswith(("f::", "z::f::")) else "makro" if s.startswith("mac::") else "sistem")
    return f"{fam} · {CAD_TR[m['cad']]}" + (" · TERS" if m["inv"] else "")


def _rank_corr(a, b, ii) -> Optional[float]:
    if len(ii) < 6:
        return None
    v = pd.Series(a[ii]).rank().corr(pd.Series(b[ii]).rank())
    return round(float(v), 2) if np.isfinite(v) else None


def _sh(x, py):
    return L.sharpe(x, py)


def _rows_sh(R, py):
    mu, sd = R.mean(1), R.std(1, ddof=1)
    return np.where(sd > 0, mu / np.where(sd > 0, sd, 1) * math.sqrt(py), 0.0)


# ---------------------------------------------------------------- research
def research_asset(a: str, px: pd.DataFrame, panel, alt) -> dict:
    py = _per_year(a)
    dates = px.index
    exam0 = int(np.searchsorted(dates.values, (dates[-1] - pd.Timedelta(days=HOLDOUT_DAYS)).to_datetime64()))
    F = build_features(px, panel, alt)
    # the system panel defines the usable start (first day with system data)
    sysf = [k for k in F if not k.startswith(("tech:", "alt::"))]
    if sysf:
        first = min(int(np.argmax(np.isfinite(F[k]))) for k in sysf if np.isfinite(F[k]).any())
    else:
        first = 260
    first = max(first, 1)
    U = universe(F, dates, exam0)
    metas, rows = [], []
    for m, tg in U:
        if not np.any(tg[first:exam0]):
            continue
        modes = ("LS",) if m["src"].startswith("bench") else MODES
        for mode in modes:
            p = tg if mode == "LS" else (np.clip(tg, 0, 1) if mode == "LO" else np.clip(tg, -1, 0))
            if not np.any(p[first:]):
                continue
            for ex in (EXITS[:1] if m["src"].startswith("bench") else EXITS):
                metas.append(dict(m, mode=mode, exit=ex))
                rows.append(p)
    P = np.nan_to_num(np.vstack(rows))
    sub = px.iloc[first:]
    cost, fund = L.COST.get(a, 0.0008), L.FUND_LONG_H * 24
    R = np.zeros((len(metas), len(sub)))
    NT = np.zeros(len(metas))
    for i in range(0, len(metas), 1500):
        r, nt = simulate(P[i:i + 1500, first:], [m["exit"] for m in metas[i:i + 1500]], sub, cost, fund)
        R[i:i + 1500], NT[i:i + 1500] = r, nt
    e0 = exam0 - first
    sdates = sub.index
    Rtr, Rex = R[:, :e0], R[:, e0:]
    bench = [i for i, m in enumerate(metas) if m["src"] == "bench:long"][0]
    # trades inside training (approximate: proportional)
    CH = np.cumsum(np.diff(P[:, first:exam0], axis=1, prepend=0.0) != 0, axis=1, dtype=np.int32)   # position changes so far
    tr_tr = CH[:, -1]
    s_tr = _rows_sh(Rtr, py)
    s_ex = _rows_sh(Rex, py)
    elig = (tr_tr >= MIN_TRADES)
    elig[bench] = False
    # ---- yearly walk-forward of the selection procedure (training only)
    years = sorted(set(sdates[:e0].year))
    oos, picks, folds = [], [], []
    for y in years:
        s = int(np.searchsorted(sdates.values[:e0], np.datetime64(f"{y}-01-01")))
        e = int(np.searchsorted(sdates.values[:e0], np.datetime64(f"{y + 1}-01-01")))
        if s < 2 * py or e - s < 40:                            # at least 2 years before the first pick
            continue
        sc = _rows_sh(R[:, :s], py)
        ok_s = CH[:, s - 1] >= MIN_TRADES                        # trade count known at the time of the pick
        ok_s[bench] = False
        sc = np.where(ok_s, sc, -np.inf)
        j = int(np.argmax(sc))
        oos.append(R[j, s:e]); picks.append(label(metas[j])); folds.append((y, _sh(R[j, s:e], py)))
    wf = np.concatenate(oos) if oos else np.zeros(0)
    wf_t = L.t_stat(wf)
    wf_pos = float(np.mean([f[1] > 0 for f in folds])) if folds else 0.0
    neff = L.n_effective(Rtr) if len(metas) > 1 else 1.0
    best = int(np.argmax(np.where(elig, s_tr, -np.inf)))
    dsr = L.deflated_sharpe(Rtr[best], neff)
    ex_t = L.t_stat(Rex[best])
    al, be, ex_at = L.alpha_t(Rex[best], Rex[bench])
    ok = {"wf_t": wf_t >= CRIT["wf_t"], "wf_pos": wf_pos >= CRIT["wf_pos"], "dsr": dsr >= CRIT["dsr"],
          "exam_t": ex_t >= CRIT["exam_t"], "exam_alpha_t": ex_at >= CRIT["exam_alpha_t"]}
    top = []
    for j in np.argsort(-np.where(elig, s_tr, -np.inf))[:20]:
        top.append({"label": label(metas[j]), "train": round(float(s_tr[j]), 2), "exam": round(float(s_ex[j]), 2),
                    "exam_ret": round(float(math.expm1(Rex[j].sum())), 4), "trades": int(tr_tr[j])})
    fam = {}
    for i, m in enumerate(metas):
        if i == bench:
            continue
        fam.setdefault(family(m), []).append(i)
    fam_rows = []
    for k, ii in fam.items():
        ii = np.array(ii)
        fam_rows.append({"family": k, "n": len(ii), "train_mean": round(float(s_tr[ii].mean()), 2),
                         "exam_mean": round(float(s_ex[ii].mean()), 2), "exam_pos": round(float((s_ex[ii] > 0).mean()), 2),
                         # does training rank carry over? correlation of train vs exam Sharpe inside the family
                         # (only plain long+short signal-exit rules: TERS/long/short twins are mirror images and would
                         #  create a correlation even for pure noise)
                         "rank_corr": _rank_corr(s_tr, s_ex, [i for i in ii if metas[i]["mode"] == "LS" and not metas[i]["inv"]
                                                              and metas[i]["exit"]["type"] == "sig"])})
    # combinations chosen on training only: pairs of the top-12 distinct signals that must agree
    combos = []
    seen, tops = set(), []
    for j in np.argsort(-np.where(elig, s_tr, -np.inf)):
        m = metas[j]
        if m["mode"] != "LS" or m["exit"]["type"] != "sig" or m["src"] in seen:
            continue
        seen.add(m["src"]); tops.append(j)
        if len(tops) == 12:
            break
    cm, cp = [], []
    for x in range(len(tops)):
        for y in range(x + 1, len(tops)):
            p1, p2 = P[tops[x]], P[tops[y]]
            pp = np.where(p1 == p2, p1, 0.0)
            if np.any(pp[first:exam0]):
                cm.append((tops[x], tops[y])); cp.append(pp)
    if cp:
        CP = np.vstack(cp)
        Rc, _ = simulate(CP[:, first:], [EXITS[0]] * len(cp), sub, cost, fund)
        ctr, cex = _rows_sh(Rc[:, :e0], py), _rows_sh(Rc[:, e0:], py)
        order = np.argsort(-ctr)
        cj = int(order[0])
        combos = {"n": len(cp), "chosen": {"label": f"[{label(metas[cm[cj][0]])}] & [{label(metas[cm[cj][1]])}]",
                                           "train": round(float(ctr[cj]), 2), "exam": round(float(cex[cj]), 2),
                                           "exam_t": round(L.t_stat(Rc[cj, e0:]), 2)},
                  "exam_mean": round(float(cex.mean()), 2), "exam_pos": round(float((cex > 0).mean()), 2),
                  "top": [{"label": f"[{label(metas[cm[k][0]])}] & [{label(metas[cm[k][1]])}]", "train": round(float(ctr[k]), 2),
                           "exam": round(float(cex[k]), 2)} for k in order[:8]]}
    yrs_ex = len(Rex[best]) / py
    return {
        "asset": a, "window": [str(sdates[0].date()), str(sdates[-1].date())], "exam_start": str(sdates[e0].date()),
        "n_rules": len(metas), "n_eff": round(neff, 1), "n_signals": len(F),
        "chosen": {"label": label(metas[best]), "rule": metas[best], "train": round(float(s_tr[best]), 2),
                   "exam": round(float(s_ex[best]), 2), "exam_t": round(ex_t, 2), "exam_alpha_t": round(ex_at, 2),
                   "exam_ret": round(float(math.expm1(Rex[best].sum())), 4), "exam_dd": round(L.max_dd(Rex[best]), 4),
                   "dsr": round(dsr, 3), "trades": int(tr_tr[best])},
        "wf": {"sharpe": round(_sh(wf, py), 2), "t": round(wf_t, 2), "pos": round(wf_pos, 2), "folds": folds, "picks": picks,
               "ret": round(float(math.expm1(wf.sum())), 4) if len(wf) else 0.0},
        "bench": {"train": round(float(s_tr[bench]), 2), "exam": round(float(s_ex[bench]), 2),
                  "exam_ret": round(float(math.expm1(Rex[bench].sum())), 4)},
        "ok": ok, "proven": all(ok.values()), "top": top, "families": fam_rows, "combos": combos,
        "leverage_exam": L.leverage_daily(Rex[best], max(yrs_ex, 0.1)),
    }


def research(prices: pd.DataFrame, panel: Optional[pd.DataFrame], alt: Optional[pd.DataFrame], assets=None) -> dict:
    res = {"generated_at": pd.Timestamp.now("UTC").isoformat(), "crit": CRIT, "holdout_days": HOLDOUT_DAYS, "assets": {}}
    for a in (assets or sorted(prices["asset"].unique())):
        px = prices[prices["asset"] == a].copy()
        px["date"] = pd.to_datetime(px["date"], utc=True)
        px = px.set_index("date").sort_index()[["Open", "High", "Low", "Close"]].astype(float).dropna()
        px = px[(px["Open"] > 0) & (px["Close"] > 0)]
        if len(px) < 1000:
            print(f"[long-lab] {a}: veri yetersiz ({len(px)} gün)", flush=True)
            continue
        sp = panel[panel["asset"] == a] if panel is not None else None
        al = alt[alt["asset"] == a] if alt is not None else None
        r = research_asset(a, px, sp, al)
        res["assets"][a] = r
        print(f"[long-lab] {a}: {r['n_rules']} kural · eğitim {r['window'][0]}→{r['exam_start']} · sınav →{r['window'][1]} · "
              f"seçilen sınav Sharpe {r['chosen']['exam']} · {'✅' if r['proven'] else '❌'}", flush=True)
    return res


def report_md(res: dict) -> str:
    Lr = ["# 🧭 Uzun Dönem Laboratuvarı v8 — ~10 yıl, son 2 yıl mühürlü sınav", "",
          f"_Üretim: {res['generated_at'][:16]} UTC. Son {res['holdout_days']} gün hiçbir seçimde kullanılmadı; "
          "seçim yalnızca önceki dönemde yapıldı, sınav bir kez uygulandı._", "",
          "**Kanıt şartı (önceden sabit):** eğitimde yıllık walk-forward t ≥ 2 ve yılların ≥%60'ı pozitif · DSR ≥ 0.90 · "
          "sınavda t ≥ 1.5 ve sürekli long'a karşı alfa t ≥ 1.0. Kararlar günlük kapanış verisiyle, ertesi gün açılışında uygulanır; "
          "komisyon/kayma ve perp fonlaması düşülmüştür.", "",
          "⚠️ Sistem burada **günlük saatle** çalıştırıldı (canlı sistem saatlik çalışır; içindeki 'N mum' hesapları burada 'N gün'). "
          "Bu, sistemin haftalık/aylık ufuktaki değerini ölçmek için doğru sorudur; saatlik sistemin birebir kopyası değildir.", "",
          "## 1) Varlık bazında sonuç", "",
          "| Varlık | Eğitim → sınav | Kural sayısı (etkin) | Seçilen kural (eğitimin en iyisi) | Eğitim Sharpe | **Sınav Sharpe** | Sınav getiri / DD | Sınav t · alfa t | WF Sharpe (t) · + yıl | DSR | Sürekli long eğitim / sınav | Durum |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for a, r in res["assets"].items():
        c, w, b = r["chosen"], r["wf"], r["bench"]
        Lr.append(f"| {a} | {r['window'][0][:4]}–{r['exam_start'][:7]} → {r['window'][1][:7]} | {r['n_rules']:,} ({r['n_eff']:.0f}) | {c['label']} | "
                  f"{c['train']:.2f} | **{c['exam']:.2f}** | {L._pct(c['exam_ret'])} / {L._pct(-c['exam_dd'])} | {c['exam_t']:+.1f} · {c['exam_alpha_t']:+.1f} | "
                  f"{w['sharpe']:.2f} ({w['t']:+.1f}) · %{w['pos'] * 100:.0f} | {c['dsr']:.2f} | {b['train']:.2f} / {b['exam']:.2f} | "
                  f"{'✅ KANITLI' if r['proven'] else '❌ kanıt yok'} |")
    Lr += ["", "## 2) 'Harika geçmiş test' sınavda ne oluyor? (eğitimin ilk 20'si ve sınav sonuçları)", ""]
    for a, r in res["assets"].items():
        Lr += [f"**{a}**", "", "| # | Kural | Eğitim Sharpe | Sınav Sharpe | Sınav getiri | İşlem (eğitim) |", "|---|---|---|---|---|---|"]
        for k, t in enumerate(r["top"], 1):
            Lr.append(f"| {k} | {t['label']} | {t['train']:.2f} | {t['exam']:.2f} | {L._pct(t['exam_ret'])} | {t['trades']} |")
        Lr.append("")
    Lr += ["## 3) Aile bazında sınav (seçim yanlılığı yok denecek kadar az)", "",
           "_Bir ailedeki TÜM kuralların sınav ortalaması. 'Sıra korelasyonu': eğitimde iyi olan sınavda da iyi mi? (0 = hayır)._", "",
           "| Varlık | Aile · ufuk | Kural | Eğitim ort. Sharpe | Sınav ort. Sharpe | Sınavda pozitif | Sıra korelasyonu |", "|---|---|---|---|---|---|---|"]
    for a, r in res["assets"].items():
        for f in sorted(r["families"], key=lambda x: -x["exam_mean"]):
            rc = "—" if f["rank_corr"] is None or not np.isfinite(f["rank_corr"]) else f"{f['rank_corr']:+.2f}"
            Lr.append(f"| {a} | {f['family']} | {f['n']} | {f['train_mean']:.2f} | {f['exam_mean']:.2f} | %{f['exam_pos'] * 100:.0f} | {rc} |")
    Lr += ["", "## 4) Kombinasyonlar (eğitimin en iyi 12 sinyalinin ikilileri, ikisi aynı yönde → işlem)", ""]
    for a, r in res["assets"].items():
        c = r.get("combos")
        if not c:
            continue
        ch = c["chosen"]
        Lr += [f"**{a}** · {c['n']} ikili · seçilen: {ch['label']} · eğitim {ch['train']:.2f} → **sınav {ch['exam']:.2f}** (t {ch['exam_t']:+.1f}) · "
               f"tüm ikililerin sınav ortalaması {c['exam_mean']:.2f}, pozitif %{c['exam_pos'] * 100:.0f}", ""]
    Lr += ["## 5) Yıllık walk-forward seçimleri (eğitim dönemi)", ""]
    for a, r in res["assets"].items():
        Lr.append(f"**{a}**: " + " · ".join(f"{y}: {s:+.2f} ({p})" for (y, s), p in zip(r["wf"]["folds"], r["wf"]["picks"])))
        Lr.append("")
    Lr += ["## 6) Kaldıraç — seçilen kural, sınav dönemi", "", "| Varlık | 1x | 2x | 3x | 5x | 10x |", "|---|---|---|---|---|---|"]
    for a, r in res["assets"].items():
        m = {str(x["lev"]): x for x in r["leverage_exam"]}
        cell = lambda x: f"{L._pct(x['cagr'], 0)} / {L._pct(-x['maxdd'], 0)}" + (f" · {x['liquidations']} lik." if x["liquidations"] else "")
        Lr.append(f"| {a} | " + " | ".join(cell(m[k]) for k in ("1", "2", "3", "5", "10") if k in m) + " |")
    return "\n".join(Lr) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default="long_reports/signal_panel_daily.csv.gz")
    ap.add_argument("--prices", default="long_reports/prices_daily.csv.gz")
    ap.add_argument("--alt", default="long_reports/cot_long.csv.gz")
    ap.add_argument("--out", default="long_out")
    ap.add_argument("--assets", default=None)
    a = ap.parse_args()
    prices = pd.read_csv(a.prices)
    panel = None
    if os.path.exists(a.panel):
        panel = pd.read_csv(a.panel, low_memory=False)
        panel["t"] = pd.to_datetime(panel["t"], utc=True)
    else:
        print("[long-lab] sistem paneli yok: yalnızca teknik + COT", flush=True)
    alt = None
    if a.alt and os.path.exists(a.alt):
        import alt_data
        alt = alt_data.load((a.alt,))
    res = research(prices, panel, alt, a.assets.split(",") if a.assets else None)
    os.makedirs(a.out, exist_ok=True)
    json.dump(L._jsonable(res), open(os.path.join(a.out, "long_lab_results.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(os.path.join(a.out, "long_lab_report.md"), "w", encoding="utf-8").write(report_md(res))
    print(f"[long-lab] kanıtlı: {[k for k, r in res['assets'].items() if r['proven']] or 'yok'}", flush=True)


if __name__ == "__main__":
    main()
