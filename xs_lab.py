"""
Cross-sectional crypto perp lab (v9.0) — portfolios, not single-asset timing
===========================================================================
Why: small, persistent edges are invisible in 6 correlated assets but become
measurable when the same rule is applied to dozens of coins at once (breadth).
This lab tests the classic, published cross-sectional crypto premia on EVERY
Binance USDT-M perpetual (delisted ones included), with the same honesty
protocol as long_lab.py:

  UNIVERSE  point-in-time: on each day the top N contracts by 30-day average
            traded value (N = 20 / 50 / 100), listed for >= 60 days.
  SIGNALS   momentum (1,3,7,14,28,56,84 days), risk-adjusted momentum,
            funding carry (3/7/30-day funding paid), low volatility, attention
            (7d/30d traded value) - each also contrarian (TERS).
  PORTFOLIO rank the universe; long the top q, short the bottom q (q = 20% /
            33%), equal or inverse-volatility weights, 0.5 long + 0.5 short
            (market-neutral, gross 1x) or long-only top q (gross 1x);
            rebalanced daily or weekly.
  EXECUTION weights decided at the 00:00 UTC close from data <= that day,
            held over the next day; real funding cash flows (longs pay,
            shorts receive the historical rates); fees+slippage per side
            0.06% (top 20), 0.10% (top 50), 0.15% (top 100) on turnover.
            A contract that stops trading is exited at its last close.
  PROOF     last 2 years sealed; selection only in training; yearly
            walk-forward; Deflated Sharpe; exam t >= 1.5 and alpha t >= 1
            against holding BTC; family-level exam table.

CLI: python xs_lab.py --panel xs_data/xs_panel.csv.gz --out xs_out
"""
from __future__ import annotations

import argparse
import json
import math
import os
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

import strategy_lab as L

HOLDOUT_DAYS = 730
NS = (20, 50, 100)
QS = (0.2, 0.33)
REBAL = (1, 7)
COST_N = {20: 0.0006, 50: 0.0010, 100: 0.0015}
MIN_AGE = 60
CRIT = {"wf_t": 2.0, "wf_pos": 0.6, "dsr": 0.90, "exam_t": 1.5, "exam_alpha_t": 1.0}
SIG_TR = {"mom": "Momentum", "rmom": "Riske göre momentum", "carry": "Fonlama carry", "lowvol": "Düşük volatilite",
          "attn": "İlgi (hacim 7g/30g)"}


# ---------------------------------------------------------------- data
def wide(panel: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    p = panel.copy()
    p["date"] = pd.to_datetime(p["date"], utc=True)
    p = p.drop_duplicates(["date", "symbol"], keep="last")
    W = {k: p.pivot(index="date", columns="symbol", values=k).sort_index() for k in ("close", "quote_volume", "funding")}
    full = pd.date_range(W["close"].index[0], W["close"].index[-1], freq="D", tz="UTC")
    return {k: v.reindex(full) for k, v in W.items()}


def features(W: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """Every feature at day d uses data up to and including day d (decided at its close)."""
    C = W["close"]
    lr = np.log(C / C.shift(1))
    vol = lr.rolling(28, min_periods=20).std()
    F = {}
    for n in (1, 3, 7, 14, 28, 56, 84):
        F[f"mom:{n}"] = np.log(C / C.shift(n))
    F["rmom:28"] = F["mom:28"] / (vol * math.sqrt(28))
    fund = W["funding"].fillna(0.0)
    for n in (3, 7, 30):
        F[f"carry:{n}"] = -fund.rolling(n, min_periods=max(2, n // 2)).sum()           # paying lots of funding -> short
    F["lowvol:28"] = -vol
    qv = W["quote_volume"]
    F["attn:7"] = np.log(qv.rolling(7, min_periods=5).mean() / qv.rolling(30, min_periods=20).mean())
    return F


def universe(W: Dict[str, pd.DataFrame], n: int) -> pd.DataFrame:
    C, qv = W["close"], W["quote_volume"]
    age = C.notna().cumsum()
    liq = qv.rolling(30, min_periods=20).mean()
    ok = (age >= MIN_AGE) & C.notna() & liq.notna()
    rank = liq.where(ok).rank(axis=1, ascending=False, method="first")
    return rank <= n


# ---------------------------------------------------------------- portfolios
def weights(X: pd.DataFrame, U: pd.DataFrame, q: float, mode: str, wt: str, vol: pd.DataFrame, rebal: int) -> np.ndarray:
    Xu = X.where(U)
    pct = Xu.rank(axis=1, pct=True)
    cnt = Xu.notna().sum(axis=1)
    enough = (cnt >= 10).values[:, None]
    long = (pct > 1 - q).values & enough
    short = (pct <= q).values & enough
    base = np.ones(X.shape) if wt == "ew" else np.nan_to_num(1.0 / np.where(vol.values > 0, vol.values, np.nan), nan=0.0)
    lw = np.where(long, base, 0.0)
    sw = np.where(short, base, 0.0)
    ls, ss = lw.sum(1, keepdims=True), sw.sum(1, keepdims=True)
    lw = np.divide(lw, ls, out=np.zeros_like(lw), where=ls > 0)
    sw = np.divide(sw, ss, out=np.zeros_like(sw), where=ss > 0)
    w = (0.5 * lw - 0.5 * sw) if mode == "LS" else lw
    if rebal > 1:
        dow = X.index.dayofweek.values
        keep = np.where(dow == 6)[0]                       # decided at the Sunday 24:00 close -> weekly from Monday
        idx = np.maximum.accumulate(np.where(np.isin(np.arange(len(w)), keep), np.arange(len(w)), 0))
        w = w[idx]
    return w


def pnl(w: np.ndarray, R: np.ndarray, Fd: np.ndarray, cost: float) -> np.ndarray:
    """w[d] decided at the close of d -> earns day d+1 (R = daily LOG returns,
    output = the book's daily LOG return). A contract whose next return is
    missing (stopped trading) is exited at its last close."""
    alive = np.isfinite(R[1:])
    held = np.where(alive, w[:-1], 0.0)
    prev = np.vstack([np.zeros((1, w.shape[1])), held[:-1]])
    out = np.zeros(len(w))
    simple = np.expm1(np.nan_to_num(R[1:]))                 # portfolio P&L adds SIMPLE returns (a short gains at most 100%)
    port = ((held * simple).sum(1) - (held * np.nan_to_num(Fd[1:])).sum(1)
            - cost * np.abs(w[:-1] - prev).sum(1) - cost * np.abs(np.where(alive, 0.0, w[:-1])).sum(1))
    out[1:] = np.log1p(np.maximum(port, -0.99))
    return out


def label(m: dict) -> str:
    fam, n = m["sig"].split(":")
    s = ("TERS " if m["inv"] else "") + f"{SIG_TR[fam]} ({n} gün)"
    side = (f"en iyi %{m['q'] * 100:.0f} long / en kötü %{m['q'] * 100:.0f} short" if m["mode"] == "LS"
            else f"en iyi %{m['q'] * 100:.0f} sadece long")
    return (f"{s} · ilk {m['n']} coin · {side} · {'eşit' if m['wt'] == 'ew' else 'ters-volatilite'} ağırlık · "
            f"{'günlük' if m['rebal'] == 1 else 'haftalık'} yenileme")


FAM_SHARE = 0.8          # a family is "on" when >= 80% of its variants were profitable so far


def fam_key(m: dict) -> str:
    return f"{m['sig']}|{'inv' if m['inv'] else 'dir'}"


def ensemble_pick(Rm: np.ndarray, metas: List[dict], s: int) -> List[str]:
    """Procedure B (pre-specified, mechanical): using ONLY days [0, s), keep the
    market-neutral (long/short) families whose variants were profitable in at
    least 80% of cases and on average. No single 'best' variant is picked."""
    sh = _rows_sh(Rm[:, :s])
    act = (np.abs(Rm[:, :s]) > 0).mean(1) > 0.5
    fams: Dict[str, List[int]] = {}
    for i, m in enumerate(metas):
        if m["mode"] == "LS" and act[i]:
            fams.setdefault(fam_key(m), []).append(i)
    return sorted(k for k, ii in fams.items() if len(ii) >= 6 and np.mean(sh[ii] > 0) >= FAM_SHARE and np.mean(sh[ii]) > 0)


def ensemble_returns(Rm: np.ndarray, metas: List[dict], keys: List[str], s: int, e: int) -> np.ndarray:
    """Equal capital in every chosen family; inside a family equal capital in every variant."""
    if not keys:
        return np.zeros(e - s)
    fam_r = []
    for k in keys:
        ii = [i for i, m in enumerate(metas) if m["mode"] == "LS" and fam_key(m) == k]
        fam_r.append(np.expm1(Rm[ii, s:e]).mean(0))
    return np.log1p(np.mean(fam_r, axis=0))


def _sh(x):
    return L.sharpe(x, 365.0)


def _rows_sh(R):
    mu, sd = R.mean(1), R.std(1, ddof=1)
    return np.where(sd > 0, mu / np.where(sd > 0, sd, 1) * math.sqrt(365.0), 0.0)


# ---------------------------------------------------------------- research
def research(panel: pd.DataFrame, ns=NS, qs=QS, rebals=REBAL) -> dict:
    W = wide(panel)
    dates = W["close"].index
    C = W["close"]
    R = np.log(C / C.shift(1)).values
    Fd = W["funding"].values
    F = features(W)
    vol = np.log(C / C.shift(1)).rolling(28, min_periods=20).std()
    metas, rows, turn = [], [], []
    for n in ns:
        U = universe(W, n)
        if U.sum(axis=1).max() < min(n, 10) + 0:
            continue
        cost = COST_N[n]
        for sig, X in F.items():
            for inv in (False, True):
                Xs = -X if inv else X
                for q in qs:
                    for wt in ("ew", "iv"):
                        for rb in rebals:
                            for mode in ("LS", "LO"):
                                w = weights(Xs, U, q, mode, wt, vol, rb)
                                rows.append(pnl(w, R, Fd, cost))
                                turn.append(float(np.abs(np.diff(w, axis=0)).sum(1).mean()))
                                metas.append({"sig": sig, "inv": inv, "n": n, "q": q, "wt": wt, "rebal": rb, "mode": mode})
        print(f"[xs] ilk {n}: {len(metas)} portföy", flush=True)
    # benchmarks: BTC and the equal-weight top-20 basket, long
    btc = np.nan_to_num(R[:, list(C.columns).index("BTCUSDT")]) if "BTCUSDT" in C.columns else np.zeros(len(dates))
    btc = btc - np.nan_to_num(Fd[:, list(C.columns).index("BTCUSDT")]) if "BTCUSDT" in C.columns else btc
    Rm = np.vstack(rows)
    # start of the test: first day with an active book in at least one rule
    active = (np.abs(Rm) > 0).any(0)
    t0 = int(np.argmax(active))
    Rm, btc, dts = Rm[:, t0:], btc[t0:], dates[t0:]
    e0 = int(np.searchsorted(dts.values, (dts[-1] - pd.Timedelta(days=HOLDOUT_DAYS)).to_datetime64()))
    Rtr, Rex = Rm[:, :e0], Rm[:, e0:]
    s_tr, s_ex = _rows_sh(Rtr), _rows_sh(Rex)
    live_tr = (np.abs(Rtr) > 0).mean(1)
    elig = live_tr > 0.5                                       # active at least half of the training period
    # yearly walk-forward of the selection
    oos, folds, picks = [], [], []
    for y in sorted(set(dts[:e0].year)):
        s = int(np.searchsorted(dts.values[:e0], np.datetime64(f"{y}-01-01")))
        e = int(np.searchsorted(dts.values[:e0], np.datetime64(f"{y + 1}-01-01")))
        if s < 365 or e - s < 60:
            continue
        ok_s = (np.abs(Rm[:, :s]) > 0).mean(1) > 0.5
        sc = np.where(ok_s, _rows_sh(Rm[:, :s]), -np.inf)
        j = int(np.argmax(sc))
        oos.append(Rm[j, s:e]); folds.append((y, round(_sh(Rm[j, s:e]), 2))); picks.append(label(metas[j]))
    wf = np.concatenate(oos) if oos else np.zeros(0)
    # ---- procedure B: family ensemble, same walk-forward and the same sealed exam
    e_oos, e_folds = [], []
    for y in sorted(set(dts[:e0].year)):
        s_ = int(np.searchsorted(dts.values[:e0], np.datetime64(f"{y}-01-01")))
        e_ = int(np.searchsorted(dts.values[:e0], np.datetime64(f"{y + 1}-01-01")))
        if s_ < 365 or e_ - s_ < 60:
            continue
        keys = ensemble_pick(Rm, metas, s_)
        rr = ensemble_returns(Rm, metas, keys, s_, e_)
        e_oos.append(rr); e_folds.append((y, round(_sh(rr), 2), keys))
    ewf = np.concatenate(e_oos) if e_oos else np.zeros(0)
    ekeys = ensemble_pick(Rm, metas, e0)
    eex = ensemble_returns(Rm, metas, ekeys, e0, Rm.shape[1])
    _, ebeta, e_at = L.alpha_t(eex, btc[e0:])
    eok = {"wf_t": L.t_stat(ewf) >= CRIT["wf_t"],
           "wf_pos": (np.mean([f[1] > 0 for f in e_folds]) if e_folds else 0) >= CRIT["wf_pos"],
           "exam_t": L.t_stat(eex) >= CRIT["exam_t"], "exam_alpha_t": e_at >= CRIT["exam_alpha_t"]}
    fam_name = lambda k: (("TERS " if k.endswith("inv") else "") + f"{SIG_TR[k.split(':')[0]]} ({k.split(':')[1].split('|')[0]}g)")
    ensemble = {"families": [fam_name(k) for k in ekeys], "keys": ekeys,
                "wf": {"sharpe": round(_sh(ewf), 2), "t": round(L.t_stat(ewf), 2),
                       "folds": [(y, sh_, [fam_name(k) for k in ks]) for y, sh_, ks in e_folds]},
                "exam": round(_sh(eex), 2), "exam_t": round(L.t_stat(eex), 2), "exam_alpha_t": round(e_at, 2),
                "exam_beta": round(ebeta, 2), "exam_ret": round(float(math.expm1(eex.sum())), 4),
                "exam_dd": round(L.max_dd(eex), 4), "ok": eok, "proven": bool(ekeys) and all(eok.values()),
                "yearly_exam": {str(y): round(_sh(g), 2) for y, g in pd.Series(eex, index=dts[e0:]).groupby(dts[e0:].year)},
                "leverage_exam": L.leverage_daily(eex, max(len(eex) / 365.0, 0.1))}
    neff = L.n_effective(Rtr)
    best = int(np.argmax(np.where(elig, s_tr, -np.inf)))
    dsr = L.deflated_sharpe(Rtr[best], neff)
    ex_t = L.t_stat(Rex[best])
    _, beta, ex_at = L.alpha_t(Rex[best], btc[e0:])
    ok = {"wf_t": L.t_stat(wf) >= CRIT["wf_t"],
          "wf_pos": (np.mean([f[1] > 0 for f in folds]) if folds else 0) >= CRIT["wf_pos"],
          "dsr": dsr >= CRIT["dsr"], "exam_t": ex_t >= CRIT["exam_t"], "exam_alpha_t": ex_at >= CRIT["exam_alpha_t"]}
    top = [{"label": label(metas[j]), "train": round(float(s_tr[j]), 2), "exam": round(float(s_ex[j]), 2),
            "exam_ret": round(float(math.expm1(Rex[j].sum())), 4), "turnover": round(turn[j], 3)}
           for j in np.argsort(-np.where(elig, s_tr, -np.inf))[:25]]
    # families: signal x orientation x mode (all N / q / weights / rebalance pooled)
    fam: Dict[str, List[int]] = {}
    for i, m in enumerate(metas):
        fam.setdefault(f"{SIG_TR[m['sig'].split(':')[0]]} ({m['sig'].split(':')[1]}g){' · TERS' if m['inv'] else ''} · "
                       f"{'long/short' if m['mode'] == 'LS' else 'sadece long'}", []).append(i)
    fam_rows = []
    for k, ii in fam.items():
        ii = np.array(ii)
        rc = pd.Series(s_tr[ii]).rank().corr(pd.Series(s_ex[ii]).rank())
        fam_rows.append({"family": k, "n": len(ii), "train_mean": round(float(s_tr[ii].mean()), 2),
                         "train_pos": round(float((s_tr[ii] > 0).mean()), 2), "exam_mean": round(float(s_ex[ii].mean()), 2),
                         "exam_pos": round(float((s_ex[ii] > 0).mean()), 2), "rank_corr": round(float(rc), 2) if np.isfinite(rc) else None})
    # pre-registered family rule: a family is credible only if it is positive in training AND in the exam on average
    yrs_ex = Rex.shape[1] / 365.0
    return {
        "generated_at": pd.Timestamp.now("UTC").isoformat(), "crit": CRIT,
        "window": [str(dts[0].date()), str(dts[-1].date())], "exam_start": str(dts[e0].date()),
        "n_symbols": int(C.shape[1]), "n_rules": len(metas), "n_eff": round(neff, 1),
        "chosen": {"label": label(metas[best]), "rule": metas[best], "train": round(float(s_tr[best]), 2),
                   "exam": round(float(s_ex[best]), 2), "exam_t": round(ex_t, 2), "exam_alpha_t": round(ex_at, 2),
                   "exam_beta": round(beta, 2), "exam_ret": round(float(math.expm1(Rex[best].sum())), 4),
                   "exam_dd": round(L.max_dd(Rex[best]), 4), "dsr": round(dsr, 3), "turnover": round(turn[best], 3)},
        "wf": {"sharpe": round(_sh(wf), 2), "t": round(L.t_stat(wf), 2), "folds": folds, "picks": picks,
               "ret": round(float(math.expm1(wf.sum())), 4) if len(wf) else 0.0},
        "btc": {"train": round(_sh(btc[:e0]), 2), "exam": round(_sh(btc[e0:]), 2)},
        "ok": ok, "proven": all(ok.values()), "top": top, "ensemble": ensemble,
        "families": sorted(fam_rows, key=lambda r: -(min(r["train_mean"], r["exam_mean"]))),
        "leverage_exam": L.leverage_daily(Rex[best], max(yrs_ex, 0.1)),
    }


def report_md(r: dict) -> str:
    c, w = r["chosen"], r["wf"]
    Lr = ["# 🌐 Kesitsel Kripto Perp Laboratuvarı v9 — portföy stratejileri, son 2 yıl mühürlü", "",
          f"_Üretim: {r['generated_at'][:16]} UTC · {r['n_symbols']} USDT perp (kapanmışlar dahil) · {r['n_rules']:,} portföy kuralı "
          f"(etkin bağımsız {r['n_eff']:.0f}) · eğitim {r['window'][0]} → {r['exam_start']} · **sınav {r['exam_start']} → {r['window'][1]}**_", "",
          "**Kanıt şartı (önceden sabit):** eğitimde yıllık walk-forward t ≥ 2 ve yılların ≥%60'ı pozitif · DSR ≥ 0.90 · "
          "sınavda t ≥ 1.5 ve BTC'ye karşı alfa t ≥ 1.0. Gerçek fonlama ödemeleri, komisyon+kayma (ilk 20: %0.06, ilk 50: %0.10, "
          "ilk 100: %0.15 / taraf) düşülmüştür; işlem bir sonraki gün uygulanır.", "",
          "## 1) Seçilen strateji (eğitimin en iyisi) ve mühürlü sınav", "",
          "| Kural | Eğitim Sharpe | **Sınav Sharpe** | Sınav getiri / DD | Sınav t · alfa t (β) | WF Sharpe (t) | DSR | Günlük devir | Durum |",
          "|---|---|---|---|---|---|---|---|---|",
          f"| {c['label']} | {c['train']:.2f} | **{c['exam']:.2f}** | {L._pct(c['exam_ret'])} / {L._pct(-c['exam_dd'])} | "
          f"{c['exam_t']:+.1f} · {c['exam_alpha_t']:+.1f} ({c['exam_beta']:.2f}) | {w['sharpe']:.2f} ({w['t']:+.1f}) | {c['dsr']:.2f} | "
          f"{c['turnover']:.2f} | {'✅ KANITLI' if r['proven'] else '❌ kanıt yok'} |", "",
          f"BTC'yi tutmak: eğitim Sharpe {r['btc']['train']:.2f} · sınav {r['btc']['exam']:.2f}", "",
          "**Yıllık walk-forward seçimleri:** " + " · ".join(f"{y}: {s:+.2f} ({p})" for (y, s), p in zip(w["folds"], w["picks"])), "",
          "## 1b) Prosedür B — aile topluluğu (tek 'en iyi' seçmeden)", "",
          "_Önceden sabit kural: o güne kadarki veride varyantlarının ≥%80'i kârlı olan piyasa-nötr (long/short) aileler seçilir; "
          "her aileye eşit sermaye, aile içinde her varyanta eşit sermaye. Aynı yıllık walk-forward ve aynı mühürlü sınav._", "",
          "| Seçilen aileler (eğitimin tamamıyla) | WF Sharpe (t) | **Sınav Sharpe** | Sınav getiri / DD | Sınav t · alfa t (β) | Durum |",
          "|---|---|---|---|---|---|",
          f"| {', '.join(r['ensemble']['families']) or '—'} | {r['ensemble']['wf']['sharpe']:.2f} ({r['ensemble']['wf']['t']:+.1f}) | "
          f"**{r['ensemble']['exam']:.2f}** | {L._pct(r['ensemble']['exam_ret'])} / {L._pct(-r['ensemble']['exam_dd'])} | "
          f"{r['ensemble']['exam_t']:+.1f} · {r['ensemble']['exam_alpha_t']:+.1f} ({r['ensemble']['exam_beta']:.2f}) | "
          f"{'✅ KANITLI' if r['ensemble']['proven'] else '❌ kanıt yok'} |", "",
          "**Yıllık seçim (walk-forward):** " + " · ".join(f"{y}: {s_:+.2f} [{', '.join(k) or '—'}]" for y, s_, k in r["ensemble"]["wf"]["folds"]), "",
          "**Sınav yılları:** " + " · ".join(f"{y}: {v:+.2f}" for y, v in r["ensemble"]["yearly_exam"].items()), "",
          "## 2) Strateji aileleri — eğitimde VE sınavda (aile ortalaması, seçim yanlılığı neredeyse yok)", "",
          "_Bir aile = aynı sinyalin tüm evren/eşik/ağırlık/yenileme varyantları. Güvenilir aile: eğitimde de sınavda da pozitif, "
          "varyantlarının çoğu pozitif._", "",
          "| Aile | Varyant | Eğitim ort. Sharpe | Eğitimde + | **Sınav ort. Sharpe** | Sınavda + | Sıra korelasyonu |", "|---|---|---|---|---|---|---|"]
    for f in r["families"]:
        rc = "—" if f["rank_corr"] is None else f"{f['rank_corr']:+.2f}"
        Lr.append(f"| {f['family']} | {f['n']} | {f['train_mean']:.2f} | %{f['train_pos'] * 100:.0f} | **{f['exam_mean']:.2f}** | "
                  f"%{f['exam_pos'] * 100:.0f} | {rc} |")
    Lr += ["", "## 3) Eğitimin en iyi 25 kuralı ve sınav sonuçları", "",
           "| # | Kural | Eğitim Sharpe | Sınav Sharpe | Sınav getiri | Günlük devir |", "|---|---|---|---|---|---|"]
    for k, t in enumerate(r["top"], 1):
        Lr.append(f"| {k} | {t['label']} | {t['train']:.2f} | {t['exam']:.2f} | {L._pct(t['exam_ret'])} | {t['turnover']:.2f} |")
    Lr += ["", "## 4) Kaldıraç — seçilen kural, sınav dönemi", "", "| 1x | 2x | 3x | 5x | 10x |", "|---|---|---|---|---|"]
    m = {str(x["lev"]): x for x in r["leverage_exam"]}
    Lr.append("| " + " | ".join(f"{L._pct(m[k]['cagr'], 0)} / {L._pct(-m[k]['maxdd'], 0)}" + (f" · {m[k]['liquidations']} lik." if m[k]["liquidations"] else "")
                                for k in ("1", "2", "3", "5", "10") if k in m) + " |")
    Lr += ["", "_Not: kapanan (delist) kontratlar son kapanıştan çıkılmış sayılır; gerçekte kapanıştan önce düşüş olabilir. "
           "Short tarafında borç/likidite kısıtı yok varsayıldı (perp'lerde short serbesttir)._"]
    return "\n".join(Lr) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default="xs_data/xs_panel.csv.gz")
    ap.add_argument("--out", default="xs_out")
    a = ap.parse_args()
    panel = pd.read_csv(a.panel)
    res = research(panel)
    os.makedirs(a.out, exist_ok=True)
    json.dump(L._jsonable(res), open(os.path.join(a.out, "xs_results.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(os.path.join(a.out, "xs_report.md"), "w", encoding="utf-8").write(report_md(res))
    print(f"[xs] seçilen: {res['chosen']['label']} · sınav Sharpe {res['chosen']['exam']} · "
          f"{'✅ KANITLI' if res['proven'] else '❌ kanıt yok'}", flush=True)


if __name__ == "__main__":
    main()
