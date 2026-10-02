"""
Tier-1 continuous engine (v3.8, Aşama 2)
========================================
GitHub's 30-minute cron fired every 1-6 hours in practice. This loop runs
INSIDE one long Actions job (~5h50m; the hourly schedule queues the next
job so coverage is continuous) and executes the full production cycle at a
fixed moment: CYCLE_DELAY_S after every hourly bar closes. After each cycle
it publishes:
  * the learning state       -> branch `state` (one commit, no growth)
  * signals.json             -> the contract a trading bot reads (Aşama 3)
  * bot_status.json          -> heartbeat shown in the app

Single writer: same concurrency group as the old tracker workflow, whose
schedule is removed (it stays as a manual fallback).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

import state_sync

CYCLE_DELAY_S = 90            # Yahoo publishes the closed hourly bar within ~1 min
SIGNAL_VALID_H = 1            # a signal is valid until the next bar closes
SL_ATR, TP_ATR = 1.5, 2.5     # PROVISIONAL; Aşama 4 replaces them with walk-forward-proven values
SYMBOLS = {"SPX": "ES=F", "NQ": "NQ=F", "XAU": "GC=F", "XAG": "SI=F", "BTC": "BTC-USD", "ETH": "ETH-USD"}
OKX_INST = {"BTC": "BTC-USDT", "ETH": "ETH-USDT"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def next_cycle_time(now: datetime) -> datetime:
    t = now.replace(minute=0, second=0, microsecond=0) + timedelta(seconds=CYCLE_DELAY_S)
    return t if t > now else t + timedelta(hours=1)


def _atr_abs(symbol: str, n: int = 14):
    p = os.path.join("ohlcv_history", symbol.replace("=", "_") + ".csv")
    try:
        d = pd.read_csv(p).tail(200)
        h, l, c = d["High"].astype(float), d["Low"].astype(float), d["Close"].astype(float)
        tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        return float(tr.tail(n).mean()), float(c.iloc[-1])
    except Exception:
        return None, None


def build_signals(state: dict, now: datetime) -> dict:
    """The bot contract. `tradeable` is True only when BOTH the model has
    out-of-sample proof (walk-forward deploy) AND the entry gate is open."""
    out = {"generated_at": now.isoformat(), "valid_until": (now.replace(minute=0, second=0, microsecond=0)
                                                             + timedelta(hours=SIGNAL_VALID_H + 1)).isoformat(),
           "schema": "tier1.signals.v1", "risk_note": f"SL={SL_ATR}xATR, TP={TP_ATR}xATR (geçici; Aşama 4'te kanıtla güncellenecek)",
           "assets": {}}
    for k, v in (state.get("asset_verdicts") or {}).items():
        verdict = str(v.get("verdict", "NÖTR (BEKLE)"))
        side = "LONG" if ("AL" in verdict.replace("SAT", "")) else ("SHORT" if "SAT" in verdict else "FLAT")
        proven = v.get("learned_model_status") == "ACTIVE"
        tradeable = bool(proven and v.get("entry_allowed") and side != "FLAT")
        atr, last = _atr_abs(SYMBOLS.get(k, k))
        sl = tp = None
        if atr and last and side != "FLAT":
            sgn = 1 if side == "LONG" else -1
            sl, tp = round(last - sgn * SL_ATR * atr, 6), round(last + sgn * TP_ATR * atr, 6)
        out["assets"][k] = {
            "side": side, "model_verdict": verdict, "stage": v.get("direction_stage"),
            "model_score": v.get("score"), "short_term": v.get("current_direction"),
            "short_term_score": v.get("live_score"), "entry_allowed": bool(v.get("entry_allowed")),
            "entry_grade": v.get("entry_grade"), "evidence": v.get("learned_model_status", "NO_MODEL"),
            "tradeable": tradeable, "last_close": last, "atr_1h": atr, "stop_loss": sl, "take_profit": tp,
            "yahoo_symbol": SYMBOLS.get(k), "okx_inst": OKX_INST.get(k),
        }
    return out


def run_cycle() -> bool:
    r = subprocess.run([sys.executable, "stateful_background_tracker.py"], capture_output=True, text=True, timeout=1200)
    tail = (r.stdout or "")[-400:] + (r.stderr or "")[-400:]
    print(tail.strip()[-600:], flush=True)
    return r.returncode == 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-minutes", type=float, default=340.0)
    ap.add_argument("--once", action="store_true", help="tek döngü (test)")
    args = ap.parse_args()
    started = _now()
    deadline = started + timedelta(minutes=args.max_minutes)
    cycles, last_ok = 0, None
    first = True
    while True:
        now = _now()
        if not first:
            nxt = next_cycle_time(now)
            if nxt > deadline:
                print(f"[loop] süre doldu; sıradaki iş {nxt:%H:%M} döngüsünü alacak", flush=True)
                break
            time.sleep(max(0.0, (nxt - _now()).total_seconds()))
        first = False
        t0 = _now()
        ok = run_cycle()
        cycles += 1
        if ok:
            last_ok = t0
        try:
            state_sync.prune()
            state = json.load(open("terminal_state.json", encoding="utf-8"))
            sig = build_signals(state, t0)
            json.dump(sig, open("signals.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            status = {"engine": "github-actions-loop", "last_cycle": t0.isoformat(), "last_cycle_ok": ok,
                      "last_success": last_ok.isoformat() if last_ok else None,
                      "next_cycle": next_cycle_time(_now()).isoformat(), "job_started": started.isoformat(),
                      "job_deadline": deadline.isoformat(), "cycles_this_job": cycles,
                      "tradeable_assets": [a for a, x in sig["assets"].items() if x["tradeable"]]}
            json.dump(status, open("bot_status.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            state_sync.build_bundle()
            pub = state_sync.publish("state", state_sync.STATE_PUBLISH_PATHS, message=f"🤖 state {t0:%Y-%m-%dT%H:%MZ}")
            print(f"[loop] döngü {cycles} {'OK' if ok else 'HATA'} · yayın {'OK' if pub else 'YOK'} · "
                  f"işlem yapılabilir: {status['tradeable_assets'] or '—'}", flush=True)
        except Exception as exc:
            print(f"[loop] yayın hatası: {exc}", flush=True)
        if args.once:
            break


if __name__ == "__main__":
    main()
