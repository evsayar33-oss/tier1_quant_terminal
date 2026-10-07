"""
Paper broker (v3.9, Aşama 3)
=============================
OKX TR has no demo API, so the evidence is collected here: every hourly cycle
the signals are executed on paper against REAL closed hourly bars, with costs.

No look-ahead, by construction:
  * a signal produced after bar t closes is filled at the OPEN of the first
    bar after t (+ slippage) - never at the close it was computed from;
  * SL/TP are checked bar by bar on High/Low; if one bar touches both, the
    STOP is assumed (conservative);
  * signal flips exit at the next bar's open, like a real order would.

Several strategies run side by side in "shadow" mode so we learn WHICH layer
of the system carries an edge (the real `tradeable` flag stays False until a
strategy passes the proof bar):
  gate        model direction, only when the entry gate is open (the design)
  model       model direction, ignoring the gate
  short_term  "Kısa Vade Yön" (1-4h) direction
Benchmark: buy-and-hold of the same asset over the same window.

Proof bar (per strategy): >= 30 closed trades, t-stat of net returns >= 2,
positive expectancy after costs, and better than buy-and-hold.
Files: paper_ledger.json (capped), paper_report.md.
"""
from __future__ import annotations

import json
import math
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import pandas as pd

LEDGER = "paper_ledger.json"
REPORT = "paper_report.md"
STRATEGIES = ("gate", "model", "short_term", "lab")
SIGNAL_EXIT = {"lab"}             # these exit when their signal goes FLAT and have no time stop
SL_ATR, TP_ATR = 1.5, 2.5          # provisional; Aşama 4 learns them
MAX_HOLD_H = 24
STALE_FILL_H = 3                   # cancel an order if the market had no bar this soon after the signal
MAX_CLOSED = 3000
# one-way cost in fraction of price (fee + slippage)
# v4.0: same one-way cost table as strategy_lab (perp-exchange level, conservative)
COST = {"BTC": 0.0010, "ETH": 0.0010, "SPX": 0.0008, "NQ": 0.0008, "XAU": 0.0008, "XAG": 0.0010}
DEFAULT_COST = 0.0010
MIN_TRADES, MIN_T = 30, 2.0
SYMBOLS = {"SPX": "ES=F", "NQ": "NQ=F", "XAU": "GC=F", "XAG": "SI=F", "BTC": "BTC-USD", "ETH": "ETH-USD"}


# ------------------------------------------------------------------ helpers
def _bars(asset: str, root: str = ".") -> Optional[pd.DataFrame]:
    p = os.path.join(root, "ohlcv_history", SYMBOLS[asset].replace("=", "_") + ".csv")
    try:
        d = pd.read_csv(p)
        d["ts"] = pd.to_datetime(d["timestamp"], utc=True)
        return d.sort_values("ts").drop_duplicates("ts").reset_index(drop=True)
    except Exception:
        return None


def _atr(d: pd.DataFrame, upto_idx: int, n: int = 14) -> Optional[float]:
    x = d.iloc[max(0, upto_idx - 3 * n): upto_idx + 1]
    if len(x) < n + 1:
        return None
    h, l, c = x["High"].astype(float), x["Low"].astype(float), x["Close"].astype(float)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    v = float(tr.tail(n).mean())
    return v if v > 0 else None


def side_for(strategy: str, a: dict) -> str:
    if strategy == "lab":
        return str((a.get("lab") or {}).get("side") or "FLAT")
    if strategy == "short_term":
        txt = str(a.get("short_term") or "")
        return "LONG" if "🟢" in txt else ("SHORT" if "🔴" in txt else "FLAT")
    side = a.get("side", "FLAT")
    if strategy == "gate" and not a.get("entry_allowed"):
        return "FLAT"
    return side


def _load(root: str) -> dict:
    try:
        return json.load(open(os.path.join(root, LEDGER), encoding="utf-8"))
    except Exception:
        return {"schema": "tier1.paper.v1", "positions": {}, "orders": {}, "closed": [], "benchmark": {}}


def _close(led: dict, key: str, pos: dict, ts, price: float, reason: str) -> None:
    sgn = 1 if pos["side"] == "LONG" else -1
    cost = COST.get(pos["asset"], DEFAULT_COST)
    gross = sgn * (price / pos["entry"] - 1.0)
    net = gross - 2 * cost
    risk = SL_ATR * pos["atr"] / pos["entry"]
    led["closed"].append({
        "strategy": pos["strategy"], "asset": pos["asset"], "side": pos["side"],
        "entry_ts": pos["entry_ts"], "exit_ts": str(ts), "entry": pos["entry"], "exit": price,
        "net_ret": round(net, 6), "r": round(net / risk, 3) if risk > 0 else None, "reason": reason,
    })
    led["positions"].pop(key, None)


# ------------------------------------------------------------------ engine
def _walk(led: dict, key: str, d: pd.DataFrame) -> None:
    """Advance an open position through every new closed bar."""
    pos = led["positions"].get(key)
    if not pos:
        return
    last = pd.Timestamp(pos["last_bar"])
    for _, b in d[d["ts"] > last].iterrows():
        hi, lo = float(b["High"]), float(b["Low"])
        sl, tp = pos.get("sl"), pos.get("tp")
        if pos["side"] == "LONG":
            hit_sl, hit_tp = sl is not None and lo <= sl, tp is not None and hi >= tp
        else:
            hit_sl, hit_tp = sl is not None and hi >= sl, tp is not None and lo <= tp
        if hit_sl:                       # both touched -> stop first (conservative)
            fill = min(float(b["Open"]), pos["sl"]) if pos["side"] == "LONG" else max(float(b["Open"]), pos["sl"])
            return _close(led, key, pos, b["ts"], fill, "SL")
        if hit_tp:
            return _close(led, key, pos, b["ts"], pos["tp"], "TP")
        pos["last_bar"] = str(b["ts"])
        if pos["strategy"] not in SIGNAL_EXIT and \
                (b["ts"] - pd.Timestamp(pos["entry_ts"])) >= pd.Timedelta(hours=MAX_HOLD_H - 1):
            return _close(led, key, pos, b["ts"], float(b["Close"]), "TIME")


def _fill(led: dict, key: str, d: pd.DataFrame) -> None:
    """Execute a pending order at the open of the first bar after its signal bar."""
    o = led["orders"].get(key)
    if not o:
        return
    after = d[d["ts"] > pd.Timestamp(o["signal_bar"])]
    if after.empty:
        return
    b = after.iloc[0]
    led["orders"].pop(key)
    if b["ts"] - pd.Timestamp(o["signal_bar"]) > pd.Timedelta(hours=STALE_FILL_H):
        return                                            # market was closed; signal is stale
    px = float(b["Open"])
    pos = led["positions"].get(key)
    if pos and pos["side"] != o["side"]:
        _close(led, key, pos, b["ts"], px, "FLIP" if o["side"] != "FLAT" else "EXIT")
    if o["side"] == "FLAT" or key in led["positions"]:
        return
    idx = int(after.index[0])
    atr = _atr(d, idx - 1)
    if not atr:
        return
    sgn = 1 if o["side"] == "LONG" else -1
    if "sl_dist" in o:          # lab strategy: its own tested exit rule (None = exit on signal only)
        sl = px - sgn * o["sl_dist"] if o.get("sl_dist") else None
        tp = px + sgn * o["tp_dist"] if o.get("tp_dist") else None
    else:
        sl, tp = px - sgn * SL_ATR * atr, px + sgn * TP_ATR * atr
    led["positions"][key] = {
        "strategy": o["strategy"], "asset": o["asset"], "side": o["side"], "entry_ts": str(b["ts"]),
        "entry": px, "atr": atr, "sl": sl, "tp": tp,
        "last_bar": str(after.iloc[0]["ts"] - pd.Timedelta(seconds=1)),   # entry bar itself is checked too
    }


def step(signals: dict, root: str = ".") -> dict:
    led = _load(root)
    for asset in SYMBOLS:
        d = _bars(asset, root)
        if d is None or d.empty:
            continue
        bm = led["benchmark"].setdefault(asset, {"start_ts": str(d["ts"].iloc[-1]), "start": float(d["Close"].iloc[-1])})
        bm["last"] = float(d["Close"].iloc[-1])
        for s in STRATEGIES:
            key = f"{s}:{asset}"
            _fill(led, key, d)
            _walk(led, key, d)
        a = (signals.get("assets") or {}).get(asset)
        if not a:
            continue
        sig_bar = str(d["ts"].iloc[-1])
        for s in STRATEGIES:
            key = f"{s}:{asset}"
            want = side_for(s, a)
            pos = led["positions"].get(key)
            have = pos["side"] if pos else "FLAT"
            if want == have or (want == "FLAT" and not pos):
                led["orders"].pop(key, None)
                continue
            if want == "FLAT" and s not in SIGNAL_EXIT:
                continue          # no fresh signal: let SL/TP/time manage the open trade
            order = {"strategy": s, "asset": asset, "side": want, "signal_bar": sig_bar}
            if s == "lab":
                lab = a.get("lab") or {}
                e, sl, tp = lab.get("entry"), lab.get("sl"), lab.get("tp")
                order["sl_dist"] = abs(e - sl) if e and sl else None
                order["tp_dist"] = abs(tp - e) if e and tp else None
            led["orders"][key] = order
    led["closed"] = led["closed"][-MAX_CLOSED:]
    led["updated_at"] = datetime.now(timezone.utc).isoformat()
    json.dump(led, open(os.path.join(root, LEDGER), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    sc = scorecard(led)
    open(os.path.join(root, REPORT), "w", encoding="utf-8").write(report_md(led, sc))
    return sc


# ------------------------------------------------------------------ evaluation
def _stats(rets: List[float]) -> dict:
    n = len(rets)
    if n == 0:
        return {"n": 0}
    m = sum(rets) / n
    sd = math.sqrt(sum((r - m) ** 2 for r in rets) / (n - 1)) if n > 1 else 0.0
    wins = [r for r in rets if r > 0]
    loss = [-r for r in rets if r < 0]
    return {"n": n, "win": len(wins) / n, "avg": m, "sum": sum(rets),
            "t": (m / (sd / math.sqrt(n))) if sd > 0 else 0.0,
            "pf": (sum(wins) / sum(loss)) if loss else float("inf") if wins else 0.0}


def scorecard(led: dict) -> dict:
    out = {}
    bh = {k: v["last"] / v["start"] - 1 for k, v in led.get("benchmark", {}).items() if v.get("start")}
    for s in STRATEGIES:
        tr = [t for t in led["closed"] if t["strategy"] == s]
        st = _stats([t["net_ret"] for t in tr])
        assets = sorted({t["asset"] for t in tr})
        bh_avg = sum(bh.get(a, 0) for a in assets) / len(assets) if assets else 0.0
        st["buy_hold"] = bh_avg
        st["proven"] = bool(st["n"] >= MIN_TRADES and st.get("t", 0) >= MIN_T and st.get("avg", 0) > 0
                            and st.get("sum", 0) > bh_avg)
        st["per_asset"] = {a: _stats([t["net_ret"] for t in tr if t["asset"] == a]) for a in assets}
        out[s] = st
    return out


NAMES = {"gate": "Model + giriş kapısı", "model": "Sadece model yönü", "short_term": "Kısa Vade Yön (1-4s)",
         "lab": "🧪 Strateji Lab adayı"}


def report_md(led: dict, sc: dict) -> str:
    L = [f"# 📒 Paper Trading Karnesi", f"_Güncelleme: {led.get('updated_at', '')[:16]} UTC · maliyetler dahil · "
         f"kanıt eşiği: ≥{MIN_TRADES} işlem, t ≥ {MIN_T}, al-tut'u geçmek_", "",
         "| Strateji | İşlem | Kazanma | Ort. net | Toplam net | t | PF | Al-tut | Durum |",
         "|---|---|---|---|---|---|---|---|---|"]
    for s, st in sc.items():
        if st["n"] == 0:
            L.append(f"| {NAMES[s]} | 0 | — | — | — | — | — | — | ⏳ veri bekleniyor |")
            continue
        pf = "∞" if st["pf"] == float("inf") else f"{st['pf']:.2f}"
        state = "✅ KANITLI" if st["proven"] else ("⏳ az örnek" if st["n"] < MIN_TRADES else "❌ kanıt yok")
        L.append(f"| {NAMES[s]} | {st['n']} | %{st['win']*100:.0f} | %{st['avg']*100:+.2f} | %{st['sum']*100:+.1f} | "
                 f"{st['t']:+.2f} | {pf} | %{st['buy_hold']*100:+.1f} | {state} |")
    L += ["", f"Açık pozisyon: {len(led['positions'])} · bekleyen emir: {len(led['orders'])}", ""]
    for k, p in sorted(led["positions"].items()):
        _f = lambda v: "—" if v is None else f"{v:.4g}"
        L.append(f"- `{k}` {p['side']} @ {p['entry']:.4g} · SL {_f(p.get('sl'))} · TP {_f(p.get('tp'))} · giriş {p['entry_ts'][:16]}")
    last = led["closed"][-10:]
    if last:
        L += ["", "**Son kapanan işlemler**", ""]
        for t in reversed(last):
            L.append(f"- {t['exit_ts'][:16]} · {NAMES[t['strategy']]} · {t['asset']} {t['side']} · "
                     f"%{t['net_ret']*100:+.2f} ({t['reason']})")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    print(report_md(_load("."), scorecard(_load("."))))
