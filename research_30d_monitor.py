"""Production evidence audit for all six assets during a new 30-day window.

Reads the existing ledgers without modifying production and without treating
hourly overlapping forecasts as independent evidence of performance.
"""
from __future__ import annotations
import csv
from datetime import datetime
from pathlib import Path
from typing import Any

ASSETS = ("SPX", "NQ", "XAU", "XAG", "BTC", "ETH")
LEDGERS = {
    "forecast": Path("forecast_ledger.csv"),
    "trades": Path("trade_ledger.csv"),
    "clone_trades": Path("clone/trade_ledger.csv"),
    "stops": Path("stop_ledger.csv"),
    "gamma": Path("dealer_gamma_history.csv"),
    "shadow": Path("shadow_ledger.csv"),
}


def _read(path: Path, start: datetime, end: datetime) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    with path.open(newline="", encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            try:
                ts = datetime.fromisoformat(r["ts"])
                if ts.tzinfo is None:
                    continue
                if start <= ts < end:
                    out.append(r)
            except (ValueError, TypeError, KeyError):
                continue
    return out


def _graded(row: dict[str, Any], key: str) -> bool:
    return str(row.get(key) or "").strip() in ("1", "1.0", "True")


def audit(manifest: dict[str, Any]) -> dict[str, Any]:
    start, end = (datetime.fromisoformat(manifest[k])
                  for k in ("start_utc", "end_utc"))
    rows = {k: _read(p, start, end) for k, p in LEDGERS.items()}
    out: dict[str, Any] = {}
    for asset in ASSETS:
        f = [r for r in rows["forecast"] if r.get("asset") == asset]
        t = [r for r in rows["trades"] if r.get("asset") == asset]
        c = [r for r in rows["clone_trades"] if r.get("asset") == asset]
        st = [r for r in rows["stops"] if r.get("asset") == asset]
        g = [r for r in rows["gamma"] if r.get("asset") == asset]
        sh = [r for r in rows["shadow"] if r.get("asset") == asset]
        out[asset] = {
            "forecast_records": len(f),
            "forecast_4h_graded": sum(_graded(r, "graded_4h") for r in f),
            "forecast_24h_graded": sum(_graded(r, "graded_24h") for r in f),
            "trade_proposals": len(t),
            "trade_graded": sum(_graded(r, "graded") for r in t),
            "clone_trade_proposals": len(c),
            "clone_trade_graded": sum(_graded(r, "graded") for r in c),
            "stop_records": len(st),
            "gamma_records": len(g),
            "shadow_records": len(sh),
        }
    return out


def as_markdown(data: dict[str, Any]) -> list[str]:
    lines = ["## Six-asset production ledger coverage (same 30-day UTC window)", "",
             "Counts are pipeline coverage only; forecasts overlap and counts are NOT independent samples.",
             "Previously locked v2 experiment history remains unchanged and is not mixed with this window.", "",
             "| Asset | Forecasts | Graded 4h/24h | Champion trades graded/total | Clone trades graded/total | Stop | Gamma | Shadow |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for a, z in data.items():
        lines.append(
            f"| {a} | {z['forecast_records']} | "
            f"{z['forecast_4h_graded']}/{z['forecast_24h_graded']} | "
            f"{z['trade_graded']}/{z['trade_proposals']} | "
            f"{z['clone_trade_graded']}/{z['clone_trade_proposals']} | "
            f"{z['stop_records']} | {z['gamma_records']} | {z['shadow_records']} |")
    return lines
