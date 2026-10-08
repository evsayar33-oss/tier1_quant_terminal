"""
Intraday (5-minute) data for the scalping lab (v10.0) — Binance archive, free
=============================================================================
Universe is POINT-IN-TIME: for every month, the 30 USDT perpetuals with the
largest traded value over the last 30 days BEFORE that month (taken from the
cross-sectional panel xs_data/xs_panel.csv.gz). Only those (symbol, month)
pairs are downloaded:

  data/futures/um/monthly/klines/{SYM}/5m/{SYM}-5m-{YYYY-MM}.zip
  (open, high, low, close, volume, quote volume, taker-buy volume)

Output: scalp_data/{SYM}.npz (t, o, h, l, c, v, tb) + scalp_data/universe.json
        {"YYYY-MM": [symbols]}  — a symbol may be traded only in its months.
CLI: python scalp_data.py --panel xs_data/xs_panel.csv.gz --out scalp_data [--top 30] [--start 2022-01]
"""
from __future__ import annotations

import argparse
import io
import json
import os
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

BASE = "https://data.binance.vision/data/futures/um/monthly/klines"


def universe(panel_path: str, top: int, start: str, last_full: str) -> Dict[str, List[str]]:
    P = pd.read_csv(panel_path, usecols=["date", "symbol", "quote_volume"])
    P["date"] = pd.to_datetime(P["date"], utc=True)
    qv = P.pivot_table(index="date", columns="symbol", values="quote_volume").sort_index()
    liq = qv.rolling(30, min_periods=20).mean()
    out = {}
    for m in pd.period_range(start, last_full, freq="M"):
        cut = pd.Timestamp(m.start_time, tz="UTC") - pd.Timedelta(days=1)       # last day BEFORE the month
        row = liq[liq.index <= cut]
        if row.empty:
            continue
        s = row.iloc[-1].dropna().sort_values(ascending=False)
        out[str(m)] = [x for x in s.index[:top] if x != "BTCDOMUSDT"]
    return out


def _get(url: str) -> Optional[bytes]:
    import requests
    for _ in range(3):
        try:
            r = requests.get(url, timeout=120, headers={"User-Agent": "tier1-quant-research"})
            if r.status_code == 200:
                return r.content
            if r.status_code == 404:
                return None
        except Exception:
            pass
    return None


def _month(sym: str, m: str) -> Optional[np.ndarray]:
    b = _get(f"{BASE}/{sym}/5m/{sym}-5m-{m}.zip")
    if not b:
        return None
    try:
        with zipfile.ZipFile(io.BytesIO(b)) as z:
            raw = z.read(z.namelist()[0]).decode("utf-8", "ignore")
        header = 0 if any(ch.isalpha() for ch in raw.split("\n", 1)[0]) else None
        d = pd.read_csv(io.StringIO(raw), header=header).iloc[:, [0, 1, 2, 3, 4, 5, 9]]
        a = d.apply(pd.to_numeric, errors="coerce").dropna().values.astype(np.float64)
        if a[:, 0].max() > 1e14:                    # microsecond timestamps in newer files
            a[:, 0] = a[:, 0] / 1000.0
        return a
    except Exception:
        return None


def build(panel: str, out: str, top: int = 30, start: str = "2022-01", workers: int = 16) -> dict:
    os.makedirs(out, exist_ok=True)
    now = datetime.now(timezone.utc)
    last_full = (pd.Timestamp(now.year, now.month, 1) - pd.Timedelta(days=1)).strftime("%Y-%m")
    U = universe(panel, top, start, last_full)
    json.dump(U, open(os.path.join(out, "universe.json"), "w"))
    need: Dict[str, List[str]] = {}
    for m, syms in U.items():
        for s in syms:
            need.setdefault(s, []).append(m)
    print(f"[scalp] {len(U)} ay · {len(need)} sembol · {sum(len(v) for v in need.values())} sembol-ay", flush=True)

    def one(sym: str) -> int:
        path = os.path.join(out, f"{sym}.npz")
        have = set()
        old = None
        if os.path.exists(path):                      # incremental: keep months already stored
            old = np.load(path)["a"]
            have = set(pd.to_datetime(old[:, 0], unit="ms", utc=True).strftime("%Y-%m"))
        parts = [old] if old is not None else []
        for m in need[sym]:
            if m in have:
                continue
            a = _month(sym, m)
            if a is not None:
                parts.append(a)
        if not parts:
            return 0
        A = np.concatenate(parts)
        A = A[np.argsort(A[:, 0], kind="stable")]
        A = A[np.r_[True, np.diff(A[:, 0]) > 0]]
        np.savez_compressed(path, a=A)                # columns: t(ms) o h l c v taker_buy_v
        return len(A)

    with ThreadPoolExecutor(workers) as ex:
        n = list(ex.map(one, sorted(need)))
    print(f"[scalp] {sum(n):,} adet 5 dakikalık mum", flush=True)
    return U


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default="xs_data/xs_panel.csv.gz")
    ap.add_argument("--out", default="scalp_data")
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--start", default="2022-01")
    a = ap.parse_args()
    build(a.panel, a.out, a.top, a.start)


if __name__ == "__main__":
    main()
