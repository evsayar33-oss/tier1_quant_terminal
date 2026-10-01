"""
Historical Walk-Forward Replay — point-in-time validation of the REAL system
===========================================================================
backtest_engine.py and optimize_and_backtest_regimes.py evaluate the
model on RANDOMLY GENERATED data whose drift was designed to match each
regime's hypothesis. That can confirm the code runs, but it cannot tell
whether the system predicts real markets (the answer is baked into the
synthetic data). This module replaces that question with a real one.

What it does
------------
1. Downloads real history (yfinance 1H for the whole 36-instrument grid,
   ~730 days max; 1D history for the HTF/vol-baseline symbols; FRED macro
   series with their observation DATES).
2. Walks forward through time. At each replay moment ``t`` it:
     * freezes the system clock at ``t`` (system_clock.py), so every
       freshness check, decay, pending-prediction settlement and
       timestamp inside the production code sees ``t`` as "now";
     * feeds the production PreTradeGatekeeper a data engine that returns
       ONLY data that existed at ``t`` (1H bars <= t, the last 200 like
       production; daily bars from earlier sessions plus today's partial
       bar built from 1H bars <= t; FRED observations dated at least one
       day before t, i.e. already published);
     * runs EXACTLY the production cycle of stateful_background_tracker:
       refresh -> stateful prepare -> harmonized evaluation -> stateful
       finalize -> pair reconciliation -> final entry-timing gate ->
       performance ledger.
   All adaptive state (thresholds, pair bars, timeframe reliability,
   stateful memory) starts cold and learns only from the past, exactly as
   a fresh deployment on that date would have.
3. Writes a report: hit-rates vs. naive baselines (same code as the live
   scoreboard), plus a factor Information-Coefficient table -- the
   rank-correlation of every factor's signed reading with the next 24h /
   72h return. That table is the objective evidence base for any future
   weight change (the "which factor really leads?" question).

Isolation
---------
The replay runs inside a temporary working directory, so none of the
repository's live state files are read or modified.

Known, disclosed limitations (printed in the report as well)
------------------------------------------------------------
* OKX/Bybit taker-flow and funding endpoints have no public history ->
  those crypto factors are absent in replay (BTC/ETH are judged with
  fewer leading inputs than live -- a conservative bias).
* FRED market series (OAS, breakevens, real yields) are rarely revised,
  but the replay uses current vintages.
* yfinance limits 1H history to ~730 days.

Usage
-----
    python historical_replay.py --days 365 --step-hours 6
    python historical_replay.py --data-dir ohlcv_history --days 5 --step-hours 2   # offline smoke test
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional

REPO_DIR = os.path.dirname(os.path.abspath(__file__))


# ----------------------------------------------------------------------
# Data acquisition (network) -> cache directory in ohlcv_history format
# ----------------------------------------------------------------------
def download_market_data(cache_dir: str, daily_years: int = 4) -> Dict[str, Any]:
    import pandas as pd
    import yfinance as yf
    sys.path.insert(0, REPO_DIR)
    os.environ["OHLCV_HISTORY_DIR"] = cache_dir
    os.environ["TIER1_DISABLE_LEARNED"] = "1"      # v3.4: judge/learn from the hand-weighted model only
    from data_engine import GRID_TICKERS
    from gatekeeper import _DAILY_FETCH_SYMBOLS
    from ohlcv_history import _atomic_write

    report = {"1h": {}, "1d": {}}

    def clean(raw):
        if raw is None or raw.empty:
            return pd.DataFrame()
        x = raw.copy()
        if isinstance(x.columns, pd.MultiIndex):
            x.columns = [c[0] for c in x.columns]
        return x

    for sym in GRID_TICKERS:
        df = pd.DataFrame()
        for period in ("730d", "720d", "700d", "365d"):
            try:
                df = clean(yf.download(sym, period=period, interval="1h", prepost=True,
                                       progress=False, auto_adjust=False, timeout=30))
            except Exception:
                df = pd.DataFrame()
            if len(df) > 50:
                break
        if len(df):
            _atomic_write(sym, df)
        report["1h"][sym] = int(len(df))
        time.sleep(0.4)

    for sym in sorted(set(_DAILY_FETCH_SYMBOLS.values())):
        try:
            df = clean(yf.download(sym, period=f"{daily_years}y", interval="1d",
                                   progress=False, auto_adjust=False, timeout=30))
        except Exception:
            df = pd.DataFrame()
        if len(df):
            _atomic_write(f"{sym}_1D", df)
        report["1d"][sym] = int(len(df))
        time.sleep(0.4)
    return report


FRED_SERIES = ("DFII10", "T10YIE", "BAMLH0A0HYM2", "BAMLC0A0CM", "DTWEXBGS", "VIXCLS",
               "DGS2", "DGS10", "WALCL", "WTREGEN", "RRPONTSYD")


def download_fred(cache_dir: str, api_key: str, start: str = "2018-01-01") -> Dict[str, int]:
    import requests
    out = {}
    fred = {}
    for sid in FRED_SERIES:
        url = ("https://api.stlouisfed.org/fred/series/observations"
               f"?series_id={sid}&api_key={api_key}&file_type=json&sort_order=asc&observation_start={start}")
        try:
            res = requests.get(url, timeout=30)
            obs = res.json().get("observations", []) if res.status_code == 200 else []
        except Exception:
            obs = []
        rows = [(o["date"], float(o["value"])) for o in obs if o.get("value") not in (".", None, "")]
        fred[sid] = rows
        out[sid] = len(rows)
        time.sleep(0.3)
    with open(os.path.join(cache_dir, "fred_series.json"), "w", encoding="utf-8") as fh:
        json.dump(fred, fh)
    return out


# ----------------------------------------------------------------------
# Replay
# ----------------------------------------------------------------------
def run_replay(cache_dir: str, out_dir: str, days: float, step_hours: float,
               max_cycles: Optional[int] = None, end: Optional[str] = None) -> Dict[str, Any]:
    cache_dir = os.path.abspath(cache_dir)
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    workdir = tempfile.mkdtemp(prefix="tier1_replay_")
    prev_cwd = os.getcwd()
    os.chdir(workdir)                 # every relative state file lands here
    os.environ["OHLCV_HISTORY_DIR"] = cache_dir
    os.environ["TIER1_DISABLE_LEARNED"] = "1"      # v3.4: judge/learn from the hand-weighted model only
    sys.path.insert(0, REPO_DIR)
    try:
        return _run_replay_inner(cache_dir, out_dir, days, step_hours, max_cycles, end)
    finally:
        os.chdir(prev_cwd)
        shutil.rmtree(workdir, ignore_errors=True)


def _run_replay_inner(cache_dir, out_dir, days, step_hours, max_cycles, end):
    import numpy as np
    import pandas as pd

    import system_clock
    from config import ASSET_MATRICES
    from data_engine import GRID_TICKERS, ResilientDataEngine, _FRESHNESS_STORE, _live_cutoff_seconds
    from gatekeeper import PreTradeGatekeeper, _DAILY_FETCH_SYMBOLS
    from ohlcv_history import load_history, DEFAULT_MAX_BARS
    from performance_ledger import PerformanceLedger, build_series_map, _close_series
    from stateful_adaptive_controller import StatefulAdaptiveController

    # ---------------- load cache ----------------
    full_1h: Dict[str, pd.DataFrame] = {}
    for sym in GRID_TICKERS:
        df = load_history(sym)
        if len(df):
            full_1h[sym] = df
    full_1d: Dict[str, pd.DataFrame] = {}
    for sym in set(_DAILY_FETCH_SYMBOLS.values()):
        df = load_history(f"{sym}_1D")
        if len(df):
            full_1d[sym] = df
    fred_raw: Dict[str, List] = {}
    fred_path = os.path.join(cache_dir, "fred_series.json")
    if os.path.exists(fred_path):
        with open(fred_path, "r", encoding="utf-8") as fh:
            fred_raw = json.load(fh)
    fred = {
        sid: pd.Series([v for _, v in rows], index=pd.to_datetime([d for d, _ in rows], utc=True))
        for sid, rows in fred_raw.items() if rows
    }
    if not full_1h:
        raise SystemExit("Önbellekte 1H veri yok; önce --download ile veri indirin.")

    asset_syms = [str(m.get("benchmark_symbol")) for m in ASSET_MATRICES.values()]
    last_common = min(full_1h[s].index[-1] for s in asset_syms if s in full_1h)
    t_end = pd.Timestamp(end, tz="UTC") if end else last_common
    t_start = t_end - pd.Timedelta(days=float(days))
    first_ok = max(full_1h[s].index[0] for s in asset_syms if s in full_1h) + pd.Timedelta(days=3)
    t_start = max(t_start, first_ok)
    times = list(pd.date_range(t_start.ceil("h"), t_end, freq=f"{int(round(step_hours * 60))}min"))
    if max_cycles:
        times = times[: int(max_cycles)]

    # ---------------- point-in-time data engine ----------------
    class ReplayDataEngine(ResilientDataEngine):
        def __init__(self):
            super().__init__(fred_api_key="REPLAY" if fred else "")

        def _now(self):
            return pd.Timestamp(system_clock.now_utc())

        def fetch_single_ticker_1h(self, symbol, period="5d"):
            source = str(symbol)
            df = full_1h.get(source)
            now = self._now()
            if df is None:
                self.data_quality[source] = {"status": "UNAVAILABLE", "quality": "UNAVAILABLE", "source": source,
                                             "execution_eligible": False, "reason": "REPLAY_NO_DATA"}
                return source, pd.DataFrame()
            frame = df[df.index + pd.Timedelta(hours=1) <= now].tail(DEFAULT_MAX_BARS)   # v3.5: closed bars only
            if len(frame) < 2 or (now - frame.index[-1]) > pd.Timedelta(days=10):
                self.data_quality[source] = {"status": "UNAVAILABLE", "quality": "UNAVAILABLE", "source": source,
                                             "execution_eligible": False, "reason": "REPLAY_NO_DATA_AT_T"}
                return source, pd.DataFrame()
            frame = frame.copy()
            age = max(0.0, (now - (frame.index[-1] + pd.Timedelta(hours=1))).total_seconds())
            _FRESHNESS_STORE.update(f"BAR_AGE_SECONDS::{source}", age)
            status = "LIVE" if age <= _live_cutoff_seconds(source) else "STALE"
            frame.attrs.update({
                "source": source, "source_type": "DIRECT", "is_real": True, "is_synthetic": False,
                "fetched_at": now.isoformat(), "last_bar_time": frame.index[-1].isoformat(),
                "age_seconds": round(age, 1), "cache_age_seconds": None, "status": status,
                "quality": status, "execution_eligible": status == "LIVE", "reason": "REPLAY",
            })
            self.data_quality[source] = dict(frame.attrs)
            self.data_sources[source] = source
            return source, frame

        def fetch_single_ticker_daily(self, symbol, period="1y"):
            source = str(symbol)
            now = self._now()
            d = full_1d.get(source)
            if d is None or d.empty:
                return source, pd.DataFrame()
            hist = d[d.index.normalize() < now.normalize()]     # v3.5: closed daily bars only (as live)
            return source, hist.tail(400)

        def fetch_fred_series_observations(self, series_id, limit=300):
            s = fred.get(series_id)
            if s is None or s.empty:
                return []
            cutoff = self._now().normalize() - pd.Timedelta(days=1)   # published by t
            vals = s[s.index <= cutoff].tail(int(limit))
            return [float(v) for v in vals.values[::-1]]

        def fetch_crypto_taker_flow(self, ccy="BTC"):
            return {"value": None, "confidence": 0.0, "status": "UNAVAILABLE_IN_REPLAY"}

        def fetch_crypto_funding_rate(self, ccy="BTC"):
            return {"rate": None, "confidence": 0.0, "status": "UNAVAILABLE_IN_REPLAY"}

    # ---------------- walk forward ----------------
    base_sign = {}
    for ak, m in ASSET_MATRICES.items():
        for f in m.get("factors", []):
            base_sign[(ak, f.get("name"))] = (f.get("id"), float(f.get("base_sign", 1.0)), f.get("cluster"))

    factor_rows: List[tuple] = []
    meta_rows: List[tuple] = []          # v3.4: (asset, t, regime, legacy score) for the optimizer
    replay_ledger = PerformanceLedger(path="replay_ledger.json", max_records=None)
    prev_map = {k: "NÖTR (BEKLE)" for k in ASSET_MATRICES}
    crisis, breaches = False, 0
    errors = 0
    t_wall = time.time()
    for i, t in enumerate(times):
        system_clock.set_frozen_now(t)
        try:
            gk = PreTradeGatekeeper(fred_api_key="REPLAY")
            gk.data_engine = ReplayDataEngine()
            gk.crisis_active, gk.consecutive_breaches = crisis, breaches
            gk.refresh_market()
            controller = StatefulAdaptiveController(memory_file="stateful_adaptive_memory.json")
            controller.prepare_cycle(gk)
            raw = gk.evaluate_all_assets_harmonized(prev_map)
            verdicts, _ = controller.finalize_cycle(gk, raw, previous_signals=prev_map, cycle_id=t.isoformat())
            verdicts = gk.reconcile_pairs_post_adaptive(verdicts)
            verdicts = gk.apply_final_entry_gate(verdicts)
            # One in-memory ledger for the whole replay (no per-cycle file
            # round-trip, NO record cap): every cycle of the period is
            # graded at the end. (v3.2 capped this at the live 3000-record
            # window, so a 700-day run was judged on its last ~3 weeks.)
            replay_ledger.record_cycle(
                verdicts, gk.grid_1h, StatefulAdaptiveController._asset_df,
                gk.active_macro_regime_id,
            )
            replay_ledger.update_health(verdicts)
            crisis, breaches = gk.crisis_active, gk.consecutive_breaches
            prev_map = {k: v.get("verdict", "NÖTR (BEKLE)") for k, v in verdicts.items()}
            for ak, v in verdicts.items():
                _ls = v.get("legacy_score", v.get("score"))
                meta_rows.append((ak, t, str(gk.active_macro_regime_id),
                                  float(_ls) if _ls is not None else 0.0))
            for ak, v in verdicts.items():
                for row in v.get("details", []) or []:
                    val = row.get("ham_deger")
                    meta = base_sign.get((ak, row.get("faktör")))
                    if val is None or meta is None:
                        continue
                    fid, sgn, cluster = meta
                    factor_rows.append((ak, t, fid, row.get("faktör"), cluster, float(val) * sgn))
        except Exception as exc:
            errors += 1
            if errors <= 5:
                import traceback
                traceback.print_exc()
        if (i + 1) % 25 == 0:
            el = time.time() - t_wall
            print(f"[replay] {i + 1}/{len(times)} döngü · {el / (i + 1):.2f}s/döngü · hata={errors}", flush=True)

    # final settlement with the clock at the end of the data
    system_clock.set_frozen_now(t_end + pd.Timedelta(days=6))
    ledger = replay_ledger

    class _G:  # minimal holder for build_series_map
        pass
    g = _G()
    g.grid_1h = {k: v for k, v in full_1h.items()}
    for k, aliases in (("ES=F", ("SPX",)), ("NQ=F", ("NQ",)), ("GC=F", ("XAU",)), ("SI=F", ("XAG",))):
        for a in aliases:
            if k in full_1h:
                g.grid_1h[a] = full_1h[k]
    g.grid_daily = {}
    for ak, m in ASSET_MATRICES.items():
        sym = m.get("benchmark_symbol")
        if sym in full_1d:
            g.grid_daily[ak] = full_1d[sym]
    ledger.settle(build_series_map(g, ASSET_MATRICES.keys(), StatefulAdaptiveController._asset_df))
    ledger.data.setdefault("meta", {})["cycles"] = len(times)
    system_clock.clear_frozen_now()

    # ---------------- factor information coefficients ----------------
    ic_lines = _factor_ic_section(factor_rows, g, ASSET_MATRICES, StatefulAdaptiveController._asset_df)

    # ---------------- v3.4: self-optimisation (walk-forward, out-of-sample) ----------------
    opt_lines: List[str] = []
    try:
        import walkforward_optimizer as WFO
        closes = {a: _close_series(StatefulAdaptiveController._asset_df(g.grid_1h, a)) for a in ASSET_MATRICES}
        panel = WFO.build_panel(factor_rows, meta_rows, closes)
        if not panel.empty:
            panel.to_csv(os.path.join(out_dir, "factor_panel.csv.gz"), index=False, compression="gzip")
        learned = WFO.optimize(panel)
        learned["replay_window"] = {"start": str(times[0]) if times else None, "end": str(times[-1]) if times else None,
                                    "step_hours": step_hours, "cycles": len(times)}
        WFO.save(learned, os.path.join(out_dir, "learned_model.json"))
        opt_lines = WFO.report_lines(learned)
    except Exception as exc:
        opt_lines = ["## 🤖 Kendini optimize eden model", f"- Optimizasyon çalışmadı: {exc}", ""]

    header = [
        "## Tarihsel tekrar oynatma (walk-forward) — kapsam ve sınırlar",
        f"- Dönem: {times[0] if times else '-'} → {times[-1] if times else '-'} · adım: {step_hours} saat · döngü: {len(times)} · hata: {errors}",
        "- Sistem her an için SADECE o ana kadar var olan veriyle, canlı arka plan döngüsünün birebir aynısıyla çalıştırıldı (saat dondurularak).",
        "- Tüm adaptif hafızalar dönem başında sıfırdan başladı ve sadece geçmişten öğrendi.",
        "- ⚠️ OKX/Bybit taker akışı & fonlama oranı geçmişi olmadığı için BTC/ETH'de bu öncü faktörler replay'de yok (tutucu yanlılık).",
        "- ⚠️ FRED serileri güncel vintage ile kullanıldı (piyasa serileri nadiren revize edilir).",
        "",
    ]
    report_path = os.path.join(out_dir, "historical_replay_report.md")
    summary = ledger.write_report(report_path, extra_lines=header + opt_lines + ic_lines)
    # retitle
    with open(report_path, "r", encoding="utf-8") as fh:
        text = fh.read()
    text = text.replace("# 📊 Canlı Performans Karnesi (örneklem dışı, ileriye dönük)",
                        "# 🧪 Tarihsel Doğrulama Raporu (walk-forward, zaman-noktası doğru)", 1)
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(text)
    with open(os.path.join(out_dir, "historical_replay_summary.json"), "w", encoding="utf-8") as fh:
        json.dump({"summary": summary, "cycles": len(times), "errors": errors,
                   "start": str(times[0]) if times else None, "end": str(times[-1]) if times else None},
                  fh, ensure_ascii=False, indent=1, default=str)
    return {"cycles": len(times), "errors": errors, "report": report_path}


def _factor_ic_section(factor_rows, g, asset_matrices, frame_lookup) -> List[str]:
    import numpy as np
    import pandas as pd
    from performance_ledger import _close_series

    lines = ["## Faktör bilgi katsayısı (IC) — hangi faktör gerçekten öncü?",
             "IC = faktörün (işareti düzeltilmiş) değeri ile sonraki getirinin sıra korelasyonu. "
             "**+0,03 ve üzeri** kurumsal ölçekte anlamlı kabul edilir; negatif IC = faktör ters çalışıyor. "
             "t = IC·√(bağımsız örnek); |t| ≥ 2 istatistiksel olarak güvenilir.", ""]
    if not factor_rows:
        return lines + ["- Veri yok."]
    df = pd.DataFrame(factor_rows, columns=["asset", "t", "fid", "name", "cluster", "x"])
    closes = {a: _close_series(frame_lookup(g.grid_1h, a)) for a in asset_matrices}
    for h in (24, 72):
        def fwd(row):
            s = closes.get(row.asset)
            if s is None:
                return np.nan
            t0 = pd.Timestamp(row.t)
            p0 = s[s.index <= t0]
            p1 = s[(s.index > t0) & (s.index <= t0 + pd.Timedelta(hours=h))]
            if p0.empty or p1.empty or s.index[-1] < t0 + pd.Timedelta(hours=h):
                return np.nan
            return math.log(float(p1.iloc[-1]) / float(p0.iloc[-1]))
        df[f"r{h}"] = df.apply(fwd, axis=1)
    for asset in sorted(df.asset.unique()):
        lines.append(f"### {asset}")
        lines.append("| Faktör | Küme | IC 24s | IC 72s | t(72s) | n |")
        lines.append("|---|---|---|---|---|---|")
        sub = df[df.asset == asset]
        rows = []
        for (fid, name, cl), grp in sub.groupby(["fid", "name", "cluster"]):
            vals = {}
            for h in (24, 72):
                gg = grp[["x", f"r{h}"]].dropna()
                if len(gg) < 20 or gg["x"].nunique() < 3:
                    vals[h] = None
                    continue
                vals[h] = float(gg["x"].rank().corr(gg[f"r{h}"].rank()))
            n = int(grp["r72"].notna().sum())
            span_h = (pd.Timestamp(grp.t.max()) - pd.Timestamp(grp.t.min())).total_seconds() / 3600.0
            n_ind = max(1.0, span_h / 72.0)
            tstat = None if vals[72] is None else vals[72] * math.sqrt(n_ind)
            rows.append((vals[72] if vals[72] is not None else -9, name, cl, vals[24], vals[72], tstat, n))
        for _, name, cl, i24, i72, ts, n in sorted(rows, key=lambda r: -r[0]):
            f = lambda v: "—" if v is None else f"{v:+.3f}"
            ft = "—" if ts is None else f"{ts:+.1f}"
            lines.append(f"| {name} | {cl} | {f(i24)} | {f(i72)} | {ft} | {n} |")
        lines.append("")
    return lines


def main() -> None:
    ap = argparse.ArgumentParser(description="Tier-1 tarihsel walk-forward doğrulama")
    ap.add_argument("--days", type=float, default=365.0)
    ap.add_argument("--step-hours", type=float, default=6.0)
    ap.add_argument("--max-cycles", type=int, default=None)
    ap.add_argument("--end", type=str, default=None, help="ISO tarih; varsayılan verinin sonu")
    ap.add_argument("--data-dir", type=str, default=None,
                    help="Hazır veri önbelleği (ohlcv_history biçimi). Verilmezse indirilir.")
    ap.add_argument("--out", type=str, default=os.path.join(REPO_DIR, "validation_reports"))
    args = ap.parse_args()

    if args.data_dir:
        cache_dir = os.path.abspath(args.data_dir)
    else:
        cache_dir = tempfile.mkdtemp(prefix="tier1_replay_data_")
        print("[replay] piyasa verisi indiriliyor...", flush=True)
        rep = download_market_data(cache_dir)
        print(json.dumps(rep), flush=True)
        key = os.environ.get("FRED_API_KEY", "").strip()
        if key:
            print("[replay] FRED indiriliyor...", flush=True)
            print(json.dumps(download_fred(cache_dir, key)), flush=True)
        else:
            print("[replay] FRED_API_KEY yok: makro FRED faktörleri replay'de eksik kalacak.", flush=True)

    res = run_replay(cache_dir, args.out, args.days, args.step_hours, args.max_cycles, args.end)
    print(json.dumps(res, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
