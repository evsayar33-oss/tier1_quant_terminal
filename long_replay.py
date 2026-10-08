"""
Long replay (v8.0) — the REAL production pipeline on a DAILY clock, ~10 years
==========================================================================
historical_replay.py replays the system hour by hour, but free hourly history
stops at ~730 days. Free DAILY history (Yahoo) and FRED go back decades, so
this module runs exactly the same production cycle (gatekeeper -> stateful
prepare -> harmonized evaluation -> stateful finalize -> pair reconciliation
-> final entry gate) once per day, feeding DAILY bars where the live system
uses hourly bars.

  * POINT-IN-TIME: the decision at day D+1 00:30 UTC sees only daily bars that
    closed by then (bar D and earlier) and FRED observations dated <= D-1.
  * The system's internal "N-bar" calculations become N-DAY calculations
    (e.g. its 4-bar velocity = 4-day velocity). This is the system's daily
    -clock version - the right question for the weekly/monthly horizons where
    its macro signals showed value - not a bit-exact copy of the hourly system.
    Disclosed in the report.
  * All adaptive memories start cold and learn only from the past.

Outputs (in --out):
  signal_panel_daily.csv.gz   every system output per asset per day
  prices_daily.csv.gz         daily OHLC of the 6 traded assets (for long_lab.py)
The panel is checkpointed every 200 days, and --max-minutes stops cleanly
before the CI time limit (what is done so far is kept).

CLI:  python long_replay.py --years 10 --out long_reports [--data-dir cache] [--max-minutes 300]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from typing import Dict, List, Optional

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_SYMBOL = {"SPX": "ES=F", "NQ": "NQ=F", "XAU": "GC=F", "XAG": "SI=F", "BTC": "BTC-USD", "ETH": "ETH-USD"}
DECISION_OFFSET = "30min"           # decide at 00:30 UTC: yesterday's daily bars are closed
WARMUP_DAYS = 300                   # first decision after 300 days of history (200-bar lookbacks + z windows)


def download_daily(cache_dir: str, years: int) -> Dict[str, int]:
    import pandas as pd
    import yfinance as yf
    sys.path.insert(0, REPO_DIR)
    os.environ["OHLCV_HISTORY_DIR"] = cache_dir
    from data_engine import GRID_TICKERS
    from gatekeeper import _DAILY_FETCH_SYMBOLS
    from ohlcv_history import _atomic_write
    out = {}
    for sym in sorted(set(GRID_TICKERS) | set(_DAILY_FETCH_SYMBOLS.values())):
        df = pd.DataFrame()
        for attempt in range(3):
            try:
                df = yf.download(sym, period=f"{years}y", interval="1d", progress=False, auto_adjust=False, timeout=60)
            except Exception:
                df = pd.DataFrame()
            if df is not None and len(df) > 50:
                break
            time.sleep(2)
        if df is not None and len(df):
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]
            _atomic_write(f"{sym}_1D", df)
        out[sym] = int(len(df)) if df is not None else 0
        time.sleep(0.3)
    return out


def _load_daily(cache_dir: str) -> Dict[str, "pd.DataFrame"]:
    import pandas as pd
    os.environ["OHLCV_HISTORY_DIR"] = cache_dir
    sys.path.insert(0, REPO_DIR)
    from data_engine import GRID_TICKERS
    from gatekeeper import _DAILY_FETCH_SYMBOLS
    from ohlcv_history import load_history
    full = {}
    for sym in sorted(set(GRID_TICKERS) | set(_DAILY_FETCH_SYMBOLS.values())):
        df = load_history(f"{sym}_1D")
        if len(df):
            df = df[~df.index.duplicated(keep="last")].sort_index()
            df.index = df.index.normalize()
            full[sym] = df
    return full


def run(cache_dir: str, out_dir: str, years: float, max_minutes: float = 300.0,
        end: Optional[str] = None, max_cycles: Optional[int] = None, step_days: int = 1) -> dict:
    cache_dir, out_dir = os.path.abspath(cache_dir), os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    workdir = tempfile.mkdtemp(prefix="tier1_longreplay_")
    prev = os.getcwd()
    os.chdir(workdir)
    os.environ["OHLCV_HISTORY_DIR"] = cache_dir
    os.environ["TIER1_DISABLE_LEARNED"] = "1"
    sys.path.insert(0, REPO_DIR)
    try:
        return _run(cache_dir, out_dir, years, max_minutes, end, max_cycles, step_days)
    finally:
        os.chdir(prev)
        shutil.rmtree(workdir, ignore_errors=True)


def _run(cache_dir, out_dir, years, max_minutes, end, max_cycles, step_days):
    import pandas as pd

    import signal_panel as SP
    import system_clock
    from data_engine import ResilientDataEngine, _FRESHNESS_STORE
    from gatekeeper import PreTradeGatekeeper
    from ohlcv_history import DEFAULT_MAX_BARS
    from stateful_adaptive_controller import StatefulAdaptiveController

    full = _load_daily(cache_dir)
    if not full:
        raise SystemExit("Günlük veri yok.")
    fred = {}
    fp = os.path.join(cache_dir, "fred_series.json")
    if os.path.exists(fp):
        raw = json.load(open(fp, encoding="utf-8"))
        fred = {k: pd.Series([v for _, v in rows], index=pd.to_datetime([d for d, _ in rows], utc=True))
                for k, rows in raw.items() if rows}

    # prices of the traded assets
    prows = []
    for a, sym in ASSET_SYMBOL.items():
        d = full.get(sym)
        if d is None:
            continue
        x = d[["Open", "High", "Low", "Close"]].copy()
        x["asset"], x["date"] = a, x.index
        prows.append(x.reset_index(drop=True))
    if prows:
        pd.concat(prows, ignore_index=True).to_csv(os.path.join(out_dir, "prices_daily.csv.gz"), index=False,
                                                   compression="gzip", float_format="%.6g")

    starts = [full[s].index[0] for s in ASSET_SYMBOL.values() if s in full]
    last = min(full[s].index[-1] for s in ASSET_SYMBOL.values() if s in full)
    t_end = pd.Timestamp(end, tz="UTC") if end else last + pd.Timedelta(days=1)
    t0 = max(min(starts) + pd.Timedelta(days=WARMUP_DAYS), t_end - pd.Timedelta(days=365.25 * years))
    times = list(pd.date_range(t0.normalize(), t_end.normalize(), freq=f"{int(step_days)}D") + pd.Timedelta(DECISION_OFFSET))
    if max_cycles:
        times = times[:max_cycles]

    def closed(df, now):                                   # bar dated D is closed at D+1 00:00 UTC
        return df[df.index + pd.Timedelta(days=1) <= now]

    class DailyClockEngine(ResilientDataEngine):
        def __init__(self):
            super().__init__(fred_api_key="REPLAY" if fred else "")

        def _now(self):
            return pd.Timestamp(system_clock.now_utc())

        def fetch_single_ticker_1h(self, symbol, period="5d"):
            src = str(symbol)
            df, now = full.get(src), self._now()
            frame = closed(df, now).tail(DEFAULT_MAX_BARS) if df is not None else None
            if frame is None or len(frame) < 30 or (now - frame.index[-1]) > pd.Timedelta(days=6):
                self.data_quality[src] = {"status": "UNAVAILABLE", "quality": "UNAVAILABLE", "source": src,
                                          "execution_eligible": False, "reason": "LONG_REPLAY_NO_DATA_AT_T"}
                return src, pd.DataFrame()
            frame = frame.copy()
            _FRESHNESS_STORE.update(f"BAR_AGE_SECONDS::{src}", 0.0)    # on the daily clock the last closed bar is current
            frame.attrs.update({"source": src, "source_type": "DIRECT", "is_real": True, "is_synthetic": False,
                                "fetched_at": now.isoformat(), "last_bar_time": frame.index[-1].isoformat(),
                                "age_seconds": 0.0, "cache_age_seconds": None, "status": "LIVE", "quality": "LIVE",
                                "execution_eligible": True, "reason": "LONG_REPLAY_DAILY_CLOCK"})
            self.data_quality[src] = dict(frame.attrs)
            self.data_sources[src] = src
            return src, frame

        def fetch_single_ticker_daily(self, symbol, period="1y"):
            src = str(symbol)
            df = full.get(src)
            if df is None:
                return src, pd.DataFrame()
            return src, closed(df, self._now()).tail(400)

        def fetch_fred_series_observations(self, series_id, limit=300):
            s = fred.get(series_id)
            if s is None or s.empty:
                return []
            cut = self._now().normalize() - pd.Timedelta(days=1)
            return [float(v) for v in s[s.index <= cut].tail(int(limit)).values[::-1]]

        def fetch_crypto_taker_flow(self, ccy="BTC"):
            return {"value": None, "confidence": 0.0, "status": "UNAVAILABLE_IN_REPLAY"}

        def fetch_crypto_funding_rate(self, ccy="BTC"):
            return {"rate": None, "confidence": 0.0, "status": "UNAVAILABLE_IN_REPLAY"}

    fsigns = SP.factor_signs()
    rows: List[dict] = []
    prev_map: Dict[str, str] = {}
    crisis, breaches, errors = False, 0, 0
    wall = time.time()
    panel_path = os.path.join(out_dir, "signal_panel_daily.csv.gz")

    def save():
        if rows:
            P = pd.DataFrame(rows)
            P = P[["asset", "t"] + [c for c in P.columns if c not in ("asset", "t")]]
            P.to_csv(panel_path, index=False, compression="gzip", float_format="%.6g")

    done = 0
    stopped = False
    for i, t in enumerate(times):
        if (time.time() - wall) / 60.0 > max_minutes:
            print(f"[long] süre sınırı: {i}/{len(times)} gün işlendi, kalan atlandı", flush=True)
            stopped = True
            break
        system_clock.set_frozen_now(t)
        try:
            gk = PreTradeGatekeeper(fred_api_key="REPLAY")
            gk.data_engine = DailyClockEngine()
            gk.crisis_active, gk.consecutive_breaches = crisis, breaches
            gk.refresh_market()
            ctl = StatefulAdaptiveController(memory_file="stateful_adaptive_memory.json")
            ctl.prepare_cycle(gk)
            raw = gk.evaluate_all_assets_harmonized(prev_map or {k: "NÖTR (BEKLE)" for k in ASSET_SYMBOL})
            v, _ = ctl.finalize_cycle(gk, raw, previous_signals=prev_map, cycle_id=t.isoformat())
            v = gk.apply_final_entry_gate(gk.reconcile_pairs_post_adaptive(v))
            crisis, breaches = gk.crisis_active, gk.consecutive_breaches
            prev_map = {k: x.get("verdict", "NÖTR (BEKLE)") for k, x in v.items()}
            mac = SP.macro_of(gk)
            for ak, x in v.items():
                r = SP.flatten(x, mac, fsigns)
                r.update({"asset": ak, "t": t})
                rows.append(r)
            done += 1
        except Exception:
            errors += 1
            if errors <= 5:
                import traceback
                traceback.print_exc()
        if (i + 1) % 50 == 0:
            el = time.time() - wall
            print(f"[long] {i + 1}/{len(times)} gün · {el / (i + 1):.2f}s/gün · hata={errors}", flush=True)
        if (i + 1) % 200 == 0:
            save()
    system_clock.clear_frozen_now()
    save()
    meta = {"start": str(times[0]) if times else None, "end": str(times[min(done + errors, len(times)) - 1]) if times else None,
            "days_planned": len(times), "days_done": done, "errors": errors, "stopped_by_time": stopped,
            "clock": "daily", "decision": "D+1 00:30 UTC, bars <= D, FRED <= D-1"}
    json.dump(meta, open(os.path.join(out_dir, "long_replay_meta.json"), "w", encoding="utf-8"), indent=1)
    print(f"[long] bitti: {json.dumps(meta, ensure_ascii=False)}", flush=True)
    return meta


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=float, default=10.0)
    ap.add_argument("--out", default="long_reports")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--max-minutes", type=float, default=300.0)
    ap.add_argument("--max-cycles", type=int, default=None)
    ap.add_argument("--step-days", type=int, default=1)
    ap.add_argument("--end", default=None)
    a = ap.parse_args()
    if a.data_dir:
        cache = os.path.abspath(a.data_dir)
    else:
        cache = tempfile.mkdtemp(prefix="tier1_long_data_")
        print("[long] günlük veri indiriliyor...", flush=True)
        print(json.dumps(download_daily(cache, int(a.years) + 2)), flush=True)
        key = os.environ.get("FRED_API_KEY", "").strip()
        if key:
            import historical_replay as HR
            start = f"{int(time.strftime('%Y')) - int(a.years) - 3}-01-01"
            print(json.dumps(HR.download_fred(cache, key, start=start)), flush=True)
        else:
            print("[long] FRED_API_KEY yok: FRED faktörleri eksik kalacak", flush=True)
    run(cache, a.out, a.years, a.max_minutes, a.end, a.max_cycles, a.step_days)


if __name__ == "__main__":
    main()
