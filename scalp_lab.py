"""
Scalping lab (v10.0) — intraday bots on 5-minute bars, hundreds of trades a day
==============================================================================
The kind of bot seen on social media: many short trades per day on liquid
perpetuals, tight targets, fast exits. Tested on the 30 most traded Binance
USDT perps of each month (point-in-time, scalp_data.py), 2022 → today.

STRATEGY FAMILIES (long and short, decided at a 5-minute close, entered at
the NEXT bar's open):
  mr     mean reversion: price k standard deviations away from its 4-hour mean
         (k = 2 / 2.5 / 3), optionally only in the 1-hour trend direction
  rsi    RSI(14) < 20 / > 80 on 5m, optionally with the 1-hour trend
  flush  liquidation flush rebound: one 5m candle > k ATR (k = 3 / 5) on a
         volume spike -> fade it
  bo     breakout: close beyond the 4-hour high/low on a volume spike
         (2x / 4x) -> follow it
  flow   order flow: 15-minute taker-buy share > 65% (< 35%) with price
         above (below) its mean -> follow
EXITS: take-profit / stop-loss in ATR units (tp 0.5 / 1 / 2, sl 1 / 2), time
stop (2 or 4 hours). Inside a bar the STOP is assumed to be hit first;
a gap through the stop fills at the open.
COSTS: taker fee 0.05% + slippage 0.02% per side (0.14% round trip). The report
also shows the result if every entry/exit were a maker order (0.02%/side) - an
upper bound, real limit orders are not always filled.
PORTFOLIO: 30 equal sub-accounts (one per universe slot), each trade uses its
sub-account 1x; daily P&L = sum over trades closed that day.
PROOF: same protocol as the other labs - last 2 years sealed, yearly
walk-forward in training, Deflated Sharpe, exam t >= 1.5; family table.

CLI: python scalp_lab.py --data scalp_data --out scalp_out
"""
from __future__ import annotations

import argparse
import glob
import itertools
import json
import math
import os
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

import strategy_lab as L

try:                                                  # fast path on the CI runner (pip install numba)
    from numba import njit
except Exception:                                     # pragma: no cover - pure Python fallback
    def njit(*a, **k):
        def deco(f):
            return f
        return deco(a[0]) if a and callable(a[0]) else deco

HOLDOUT_DAYS = 730
FEE_TAKER = 0.0007            # per side: 0.05% taker + 0.02% slippage
FEE_MAKER = 0.0002
SLOTS = 30
CRIT = {"wf_t": 2.0, "wf_pos": 0.6, "dsr": 0.90, "exam_t": 1.5}
FAM_TR = {"mr": "Ortalamaya dönüş (z)", "rsi": "RSI(14) aşırılık", "flush": "Likidasyon mumu tepkisi",
          "bo": "Hacimli kırılım", "flow": "Emir akışı (taker oranı)"}


# ---------------------------------------------------------------- features (5m arrays, known at the bar close)
def _roll_mean(x, n):
    return pd.Series(x).rolling(n, min_periods=n // 2).mean().values


def features(a: np.ndarray) -> Dict[str, np.ndarray]:
    t, o, h, l, c, v, tb = (a[:, i] for i in range(7))
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    atr = _roll_mean(tr, 48)
    ma = _roll_mean(c, 48)
    sd = pd.Series(c).rolling(48, min_periods=24).std().values
    z = (c - ma) / np.where(sd > 0, sd, np.nan)
    d = np.diff(c, prepend=c[0])
    up = pd.Series(np.clip(d, 0, None)).ewm(alpha=1 / 14).mean().values
    dn = pd.Series(np.clip(-d, 0, None)).ewm(alpha=1 / 14).mean().values
    rsi = 100 - 100 / (1 + up / np.where(dn > 0, dn, np.nan))
    trend = np.sign(c - pd.Series(c).ewm(span=240, adjust=False).mean().values)        # ~20-hour EMA slope side
    hh = pd.Series(h).rolling(48, min_periods=24).max().shift(1).values
    ll = pd.Series(l).rolling(48, min_periods=24).min().shift(1).values
    vspike = v / pd.Series(v).rolling(288, min_periods=96).mean().shift(1).values
    body = (c - o) / np.where(atr > 0, atr, np.nan)
    tshare = pd.Series(tb).rolling(3).sum().values / np.where(pd.Series(v).rolling(3).sum().values > 0,
                                                             pd.Series(v).rolling(3).sum().values, np.nan)
    return {"t": t, "o": o, "h": h, "l": l, "c": c, "atr": atr, "z": z, "rsi": rsi, "trend": trend, "hh": hh, "ll": ll,
            "vspike": vspike, "body": body, "tshare": tshare, "ma": ma}


def signal(F: Dict[str, np.ndarray], cfg: dict) -> np.ndarray:
    """+1 long / -1 short / 0 at each bar close."""
    fam = cfg["fam"]
    with np.errstate(invalid="ignore"):
        if fam == "mr":
            s = np.where(F["z"] < -cfg["k"], 1, np.where(F["z"] > cfg["k"], -1, 0))
        elif fam == "rsi":
            s = np.where(F["rsi"] < 20, 1, np.where(F["rsi"] > 80, -1, 0))
        elif fam == "flush":
            big = F["vspike"] > 3
            s = np.where(big & (F["body"] < -cfg["k"]), 1, np.where(big & (F["body"] > cfg["k"]), -1, 0))
        elif fam == "bo":
            vs = F["vspike"] > cfg["k"]
            s = np.where(vs & (F["c"] > F["hh"]), 1, np.where(vs & (F["c"] < F["ll"]), -1, 0))
        elif fam == "flow":
            s = np.where((F["tshare"] > 0.65) & (F["c"] > F["ma"]), 1, np.where((F["tshare"] < 0.35) & (F["c"] < F["ma"]), -1, 0))
        else:
            raise ValueError(fam)
    if cfg.get("trend"):
        s = np.where(s == F["trend"], s, 0)
    return s.astype(np.int8)


@njit(cache=True)
def _trades(sig, ok, o, h, l, c, atr, tp, sl, hold, fee):
    """Sequential, one position at a time. Returns (exit_index, net_return, side) per trade."""
    n = len(c)
    ex_i = np.empty(n, np.int64)
    ret = np.empty(n, np.float64)
    sd = np.empty(n, np.int8)
    k = 0
    i = 0
    while i < n - 2:
        s = sig[i]
        if s == 0 or not ok[i] or not (atr[i] > 0):
            i += 1
            continue
        e = o[i + 1]
        if not (e > 0):
            i += 1
            continue
        up = e + s * tp * atr[i]
        st = e - s * sl * atr[i]
        px = 0.0
        j = i + 1
        last = min(n - 1, i + hold)
        done = False
        while j <= last:
            if s > 0:
                if l[j] <= st:
                    px = min(o[j], st) if j > i + 1 else st
                    done = True
                elif h[j] >= up:
                    px = up
                    done = True
            else:
                if h[j] >= st:
                    px = max(o[j], st) if j > i + 1 else st
                    done = True
                elif l[j] <= up:
                    px = up
                    done = True
            if done:
                break
            j += 1
        if not done:
            j = last
            px = c[j]
        ex_i[k] = j
        ret[k] = s * (px / e - 1.0) - 2 * fee
        sd[k] = s
        k += 1
        i = j                                           # next entry decided at the exit bar's close
    return ex_i[:k], ret[:k], sd[:k]


def configs() -> List[dict]:
    out = []
    ex = [dict(tp=tp, sl=sl, hold=hold) for tp, sl, hold in itertools.product((0.5, 1.0, 2.0), (1.0, 2.0), (24, 48))]
    for e in ex:
        for k, tr in itertools.product((2.0, 2.5, 3.0), (False, True)):
            out.append(dict(fam="mr", k=k, trend=tr, **e))
        for tr in (False, True):
            out.append(dict(fam="rsi", k=0, trend=tr, **e))
        for k in (3.0, 5.0):
            out.append(dict(fam="flush", k=k, trend=False, **e))
        for k in (2.0, 4.0):
            out.append(dict(fam="bo", k=k, trend=False, **e))
        out.append(dict(fam="flow", k=0, trend=False, **e))
    return out


def label(c: dict) -> str:
    p = {"mr": f"|z|>{c['k']:g}", "rsi": "20/80", "flush": f"mum>{c['k']:g}×ATR", "bo": f"hacim>{c['k']:g}×", "flow": "%65/%35"}[c["fam"]]
    return (f"{FAM_TR[c['fam']]} ({p}){' · trend yönünde' if c.get('trend') else ''} · TP {c['tp']:g}×ATR / SL {c['sl']:g}×ATR · "
            f"en fazla {c['hold'] * 5 // 60} saat")


# ---------------------------------------------------------------- research
def load(data_dir: str):
    U = json.load(open(os.path.join(data_dir, "universe.json")))
    S = {}
    for p in sorted(glob.glob(os.path.join(data_dir, "*.npz"))):
        sym = os.path.basename(p)[:-4]
        a = np.load(p)["a"]
        if len(a) > 2000:
            S[sym] = a
    return U, S


def research(U: Dict[str, List[str]], S: Dict[str, np.ndarray], cfgs: Optional[List[dict]] = None) -> dict:
    cfgs = cfgs or configs()
    days = pd.date_range(min(pd.Timestamp(m + "-01", tz="UTC") for m in U), pd.Timestamp.now("UTC").normalize(), freq="D")
    nd = len(days)
    R = np.zeros((len(cfgs), 2, nd))                   # [taker, maker] daily portfolio returns
    stats = [dict(n=0, wins=0, gw=0.0, gl=0.0) for _ in cfgs]
    first_day, last_day = nd, 0
    for sym, a in S.items():
        F = features(a)
        month = pd.to_datetime(F["t"], unit="ms", utc=True).strftime("%Y-%m").values
        allowed = {m for m, syms in U.items() if sym in syms}
        ok = np.isin(month, list(allowed))
        if not ok.any():
            continue
        day_of = ((F["t"] - days[0].value / 1e6) // 86_400_000).astype(np.int64)
        for ci, c in enumerate(cfgs):
            sig = signal(F, c)
            for fi, fee in enumerate((FEE_TAKER, FEE_MAKER)):
                ei, ret, sd = _trades(sig, ok, F["o"], F["h"], F["l"], F["c"], F["atr"], c["tp"], c["sl"], c["hold"], fee)
                if not len(ei):
                    continue
                di = day_of[ei]
                m = (di >= 0) & (di < nd)
                np.add.at(R[ci, fi], di[m], ret[m] / SLOTS)
                if fi == 0:
                    st = stats[ci]
                    st["n"] += len(ret); st["wins"] += int((ret > 0).sum())
                    st["gw"] += float(ret[ret > 0].sum()); st["gl"] += float(-ret[ret <= 0].sum())
                    first_day = min(first_day, int(di[m].min()) if m.any() else nd)
                    last_day = max(last_day, int(di[m].max()) if m.any() else 0)
    R = np.log1p(np.maximum(R[:, :, first_day:last_day + 1], -0.99))
    dts = days[first_day:last_day + 1]
    e0 = int(np.searchsorted(dts.values, (dts[-1] - pd.Timedelta(days=HOLDOUT_DAYS)).to_datetime64()))
    Rt = R[:, 0]
    sh = lambda X: np.where(X.std(1) > 0, X.mean(1) / np.where(X.std(1) > 0, X.std(1), 1) * math.sqrt(365), 0.0)
    s_tr, s_ex = sh(Rt[:, :e0]), sh(Rt[:, e0:])
    s_ex_m = sh(R[:, 1, e0:])
    # walk-forward
    oos, folds = [], []
    for y in sorted(set(dts[:e0].year)):
        s = int(np.searchsorted(dts.values, np.datetime64(f"{y}-01-01")))
        e = min(int(np.searchsorted(dts.values, np.datetime64(f"{y + 1}-01-01"))), e0)
        if s < 300 or e - s < 60:
            continue
        j = int(np.argmax(sh(Rt[:, :s])))
        oos.append(Rt[j, s:e]); folds.append((y, round(L.sharpe(Rt[j, s:e], 365), 2), label(cfgs[j])))
    wf = np.concatenate(oos) if oos else np.zeros(0)
    neff = L.n_effective(Rt[:, :e0])
    best = int(np.argmax(s_tr))
    dsr = L.deflated_sharpe(Rt[best, :e0], neff)
    ok = {"wf_t": L.t_stat(wf) >= CRIT["wf_t"], "wf_pos": (np.mean([f[1] > 0 for f in folds]) if folds else 0) >= CRIT["wf_pos"],
          "dsr": dsr >= CRIT["dsr"], "exam_t": L.t_stat(Rt[best, e0:]) >= CRIT["exam_t"]}

    def row(i):
        st = stats[i]
        n = max(st["n"], 1)
        return {"label": label(cfgs[i]), "fam": cfgs[i]["fam"], "trades": st["n"],
                "per_day": round(st["n"] / max(len(dts), 1), 1), "win_rate": round(st["wins"] / n, 3),
                "avg_win": round(st["gw"] / max(st["wins"], 1) * 100, 3), "avg_loss": round(st["gl"] / max(n - st["wins"], 1) * 100, 3),
                "per_trade_bps": round((st["gw"] - st["gl"]) / n * 1e4, 2),
                "train": round(float(s_tr[i]), 2), "exam": round(float(s_ex[i]), 2), "exam_maker": round(float(s_ex_m[i]), 2),
                "exam_ret": round(float(math.expm1(Rt[i, e0:].sum())), 4), "exam_dd": round(L.max_dd(Rt[i, e0:]), 4),
                "train_ret_yr": round(float(math.expm1(Rt[i, :e0].sum() * 365 / max(e0, 1))), 4)}
    rows = [row(i) for i in range(len(cfgs))]
    fam = {}
    for i, c in enumerate(cfgs):
        fam.setdefault(FAM_TR[c["fam"]] + (" · trend yönünde" if c.get("trend") else ""), []).append(i)
    fam_rows = []
    for k, ii in fam.items():
        ii = np.array(ii)
        wr = np.mean([rows[i]["win_rate"] for i in ii])
        fam_rows.append({"family": k, "n": len(ii), "win_rate": round(float(wr), 3),
                         "per_trade_bps": round(float(np.mean([rows[i]["per_trade_bps"] for i in ii])), 2),
                         "train_mean": round(float(s_tr[ii].mean()), 2), "exam_mean": round(float(s_ex[ii].mean()), 2),
                         "exam_maker_mean": round(float(s_ex_m[ii].mean()), 2), "exam_pos": round(float((s_ex[ii] > 0).mean()), 2)})
    hw = sorted(rows, key=lambda r: -r["win_rate"])[:10]
    return {"generated_at": pd.Timestamp.now("UTC").isoformat(), "window": [str(dts[0].date()), str(dts[-1].date())],
            "exam_start": str(dts[e0].date()), "n_symbols": len(S), "n_cfg": len(cfgs), "n_eff": round(neff, 1),
            "chosen": dict(row(best), dsr=round(dsr, 3), exam_t=round(L.t_stat(Rt[best, e0:]), 2)),
            "wf": {"sharpe": round(L.sharpe(wf, 365), 2), "t": round(L.t_stat(wf), 2), "folds": folds},
            "ok": ok, "proven": all(ok.values()),
            "top": sorted(rows, key=lambda r: -r["train"])[:20], "high_win": hw,
            "families": sorted(fam_rows, key=lambda r: -r["exam_mean"]),
            "leverage_exam": L.leverage_daily(Rt[best, e0:], max((len(dts) - e0) / 365, 0.1))}


def report_md(r: dict) -> str:
    c = r["chosen"]
    Lr = ["# ⚡ Scalping Laboratuvarı v10 — 5 dakikalık mumlar, son 2 yıl mühürlü", "",
          f"_Üretim: {r['generated_at'][:16]} UTC · her ayın en çok işlem gören 30 perp'i ({r['n_symbols']} farklı sembol) · "
          f"{r['n_cfg']} bot ayarı · eğitim {r['window'][0]} → {r['exam_start']} · **sınav {r['exam_start']} → {r['window'][1]}**_", "",
          "**Maliyet:** taker %0.05 + kayma %0.02 = işlem başına gidiş-dönüş %0.14. 'Maker' sütunu her emrin limit emirle "
          "(%0.02) dolduğu iyimser üst sınırdır. Mum içinde önce stop varsayılır.", "",
          "## 1) Eğitimin en iyi botu ve mühürlü sınav", "",
          "| Bot | İşlem/gün | Kazanma oranı | Ort. kazanç / kayıp | İşlem başı net | Eğitim Sharpe | **Sınav Sharpe** | Sınav (maker) | Sınav getiri / DD | DSR | Durum |",
          "|---|---|---|---|---|---|---|---|---|---|---|",
          f"| {c['label']} | {c['per_day']} | %{c['win_rate'] * 100:.1f} | +%{c['avg_win']:.2f} / −%{c['avg_loss']:.2f} | {c['per_trade_bps']:+.1f} bp | "
          f"{c['train']:.2f} | **{c['exam']:.2f}** | {c['exam_maker']:.2f} | {L._pct(c['exam_ret'])} / {L._pct(-c['exam_dd'])} | {c['dsr']:.2f} | "
          f"{'✅ KANITLI' if r['proven'] else '❌ kanıt yok'} |", "",
          f"**Yıllık walk-forward:** Sharpe {r['wf']['sharpe']:.2f} (t {r['wf']['t']:+.1f}) · " +
          " · ".join(f"{y}: {s:+.2f}" for y, s, _ in r["wf"]["folds"]), "",
          "## 2) Bot aileleri (tüm ayarların ortalaması)", "",
          "| Aile | Ayar | Kazanma oranı | İşlem başı net | Eğitim Sharpe | **Sınav Sharpe** | Sınav (maker) | Sınavda + |", "|---|---|---|---|---|---|---|---|"]
    for f in r["families"]:
        Lr.append(f"| {f['family']} | {f['n']} | %{f['win_rate'] * 100:.1f} | {f['per_trade_bps']:+.1f} bp | {f['train_mean']:.2f} | "
                  f"**{f['exam_mean']:.2f}** | {f['exam_maker_mean']:.2f} | %{f['exam_pos'] * 100:.0f} |")
    Lr += ["", "## 3) En yüksek kazanma oranlı 10 bot — kazanma oranı kâr demek mi?", "",
           "| Bot | Kazanma oranı | Ort. kazanç / kayıp | İşlem/gün | İşlem başı net | Sınav getiri | Sınav Sharpe |", "|---|---|---|---|---|---|---|"]
    for t in r["high_win"]:
        Lr.append(f"| {t['label']} | **%{t['win_rate'] * 100:.1f}** | +%{t['avg_win']:.2f} / −%{t['avg_loss']:.2f} | {t['per_day']} | "
                  f"{t['per_trade_bps']:+.1f} bp | {L._pct(t['exam_ret'])} | {t['exam']:.2f} |")
    Lr += ["", "## 4) Eğitimin en iyi 20 botu ve sınav sonuçları", "",
           "| # | Bot | Kazanma | İşlem/gün | Eğitim Sharpe | Eğitim yıllık | Sınav Sharpe | Sınav (maker) | Sınav getiri |", "|---|---|---|---|---|---|---|---|---|"]
    for k, t in enumerate(r["top"], 1):
        Lr.append(f"| {k} | {t['label']} | %{t['win_rate'] * 100:.0f} | {t['per_day']} | {t['train']:.2f} | {L._pct(t['train_ret_yr'])} | "
                  f"{t['exam']:.2f} | {t['exam_maker']:.2f} | {L._pct(t['exam_ret'])} |")
    return "\n".join(Lr) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="scalp_data")
    ap.add_argument("--out", default="scalp_out")
    a = ap.parse_args()
    U, S = load(a.data)
    print(f"[scalp] {len(S)} sembol yüklendi", flush=True)
    res = research(U, S)
    os.makedirs(a.out, exist_ok=True)
    json.dump(L._jsonable(res), open(os.path.join(a.out, "scalp_results.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(os.path.join(a.out, "scalp_report.md"), "w", encoding="utf-8").write(report_md(res))
    print(f"[scalp] seçilen: {res['chosen']['label']} · sınav Sharpe {res['chosen']['exam']} · "
          f"{'✅' if res['proven'] else '❌'}", flush=True)


if __name__ == "__main__":
    main()
