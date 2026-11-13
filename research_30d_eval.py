"""Pre-registered descriptive 4h holdout for the sample-imbalance hypothesis.

Signals and labels use ONLY persisted observations. 4h blocks do not overlap.
No model fitting, hyperparameter search, automatic promotion or trade claim.
"""
from __future__ import annotations
import math
from datetime import datetime, timedelta
from typing import Any


def _float(x):
    try:
        a = float(x)
        return a if math.isfinite(a) else None
    except (TypeError, ValueError):
        return None


def evaluate(rows: list[dict[str, Any]], *,
             horizon_hours: int = 4, min_n: int = 100) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for asset in ("BTC", "ETH"):
        obs = []
        # One stable reference price per hour, independent of exchange sample.
        for r in rows:
            if r.get("asset") != asset or r.get("market") != "spot":
                continue
            p = _float(r.get("reference_price"))
            if p is None or p <= 0:
                continue
            try:
                t = datetime.fromisoformat(r["ts"])
            except (ValueError, TypeError, KeyError):
                continue
            obs.append((t, p, r))
        obs.sort(key=lambda x: x[0])
        selected = []
        last_signal = None
        for t, p, r in obs:
            if r.get("status") != "OK_SAMPLE":
                continue
            im = _float(r.get("imbalance"))
            if im is None or im == 0:
                continue
            if last_signal is not None and t < last_signal + timedelta(hours=horizon_hours):
                continue
            # Only future timestamps may provide the label. Require a
            # 4h..5h observation (never substitute a stale 24h bar).
            future = next(((ft, fp) for ft, fp, _ in obs
                           if t + timedelta(hours=horizon_hours) <= ft <=
                           t + timedelta(hours=horizon_hours + 1)), None)
            if future is None:
                continue
            ft, fp = future
            if fp == p:
                continue
            ret = fp / p - 1
            selected.append({"signal_ts": t, "target_ts": ft,
                             "pred": 1 if im > 0 else -1,
                             "actual": 1 if ret > 0 else -1,
                             "return_4h": ret})
            last_signal = t
        n = len(selected)
        hit = sum(x["pred"] == x["actual"] for x in selected)
        baseline = sum(x["actual"] > 0 for x in selected)
        if n:
            p = hit / n
            # Wilson 95% interval. Not a proof of independent trials.
            z = 1.96
            den = 1 + z * z / n
            center = (p + z * z / (2 * n)) / den
            width = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
            ci = [round(center - width, 4), round(center + width, 4)]
        else:
            ci = None
        out[asset] = {"non_overlapping_n": n,
                      "direction_hit": round(hit / n, 4) if n else None,
                      "always_long_hit": round(baseline / n, 4) if n else None,
                      "wilson_95_unadjusted": ci,
                      "readiness": "DESCRIPTIVE_ONLY" if n >= min_n else "INSUFFICIENT",
                      "qualifiers": "snapshot bias, asset-specific venue, no execution costs, unadjusted interval; no promotion"}
    return out


def as_markdown(data: dict[str, Any]) -> list[str]:
    lines = ["## 4-hour prospective diagnostic (NOT trading edge)", "",
             "Signals use sampled spot aggressor flow, non-overlapping 4h windows, and later observed reference prices.",
             "The interval is unadjusted and cannot establish causal alpha.",
             "",
             "| Asset | Non-overlap N | Hit | Always-long | Wilson 95% | Verdict |",
             "|---|---:|---:|---:|---|---|"]
    for a, z in data.items():
        fmt = lambda v: "-" if v is None else f"{100*v:.1f}%"
        ci = z["wilson_95_unadjusted"]
        citxt = "-" if ci is None else f"{fmt(ci[0])} to {fmt(ci[1])}"
        lines.append(f"| {a} | {z['non_overlapping_n']} | {fmt(z['direction_hit'])} | "
                     f"{fmt(z['always_long_hit'])} | {citxt} | {z['readiness']} |")
    return lines
