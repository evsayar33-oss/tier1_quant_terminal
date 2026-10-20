"""
Tier-1 analysis engine loop
===========================
Runs the production analysis cycle (stateful_background_tracker.py) once per
hourly bar and publishes the learning state to the `state` branch.

v15.1: this system is a DIRECTION + ENTRY-TIMING analysis terminal, not a
trading bot. The former bot layer (signals.json trade contract, paper
broker, strategy labs, SL/TP orders) was removed; it had been tried and was
unprofitable. The suggested stop shown in the app is analysis output only
(stop_levels.py) -- nothing here places or simulates orders.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

import state_sync

CYCLE_DELAY_S = 90            # Yahoo publishes the closed hourly bar within ~1 min


def _now() -> datetime:
    return datetime.now(timezone.utc)


def next_cycle_time(now: datetime) -> datetime:
    t = now.replace(minute=0, second=0, microsecond=0) + timedelta(seconds=CYCLE_DELAY_S)
    return t if t > now else t + timedelta(hours=1)


def run_cycle() -> bool:
    r = subprocess.run([sys.executable, "stateful_background_tracker.py"], capture_output=True, text=True, timeout=1200)
    tail = (r.stdout or "")[-400:] + (r.stderr or "")[-400:]
    print(tail.strip()[-600:], flush=True)
    return r.returncode == 0


def recent_cycle(min_gap_minutes: float, path: str = "engine_status.json", now: datetime = None) -> bool:
    """GitHub drops most scheduled runs, so the workflow is scheduled several
    times per hour; whichever run arrives first does the cycle, the others exit."""
    if min_gap_minutes <= 0:
        return False
    try:
        with open(path, encoding="utf-8") as fh:
            last = datetime.fromisoformat(json.load(fh)["last_success"])
    except Exception:
        return False
    return ((now or _now()) - last) < timedelta(minutes=min_gap_minutes)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-minutes", type=float, default=340.0)
    ap.add_argument("--once", action="store_true", help="tek döngü")
    ap.add_argument("--min-gap-minutes", type=float, default=0.0,
                    help="son başarılı döngü bundan yeniyse hiçbir şey yapmadan çık")
    args = ap.parse_args()
    if recent_cycle(args.min_gap_minutes):
        print(f"[loop] son döngü {args.min_gap_minutes:.0f} dk'dan yeni; atlandı", flush=True)
        return
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
            status = {"engine": "github-actions-loop", "last_cycle": t0.isoformat(), "last_cycle_ok": ok,
                      "last_success": last_ok.isoformat() if last_ok else None,
                      "next_cycle": next_cycle_time(_now()).isoformat(), "job_started": started.isoformat(),
                      "job_deadline": deadline.isoformat(), "cycles_this_job": cycles}
            json.dump(status, open("engine_status.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            state_sync.build_bundle()
            pub = state_sync.publish("state", state_sync.STATE_PUBLISH_PATHS, message=f"state {t0:%Y-%m-%dT%H:%MZ}")
            print(f"[loop] döngü {cycles} {'OK' if ok else 'HATA'} · yayın {'OK' if pub else 'YOK'}", flush=True)
        except Exception as exc:
            print(f"[loop] yayın hatası: {exc}", flush=True)
        if args.once:
            break


if __name__ == "__main__":
    main()
