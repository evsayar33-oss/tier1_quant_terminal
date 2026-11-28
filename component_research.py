"""Prospective component-level scoreboard, not an execution or promotion engine.

One observation per asset/hour, including abstentions and data exclusions.
All fixed comparators share the same non-overlapping label windows. No
backfill of predictions, parameter search, or result-dependent selection.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from collections import Counter

import pandas as pd

from config import LOGIC_VERSION
from evidence_windows import SCHEMA, utc, window, fresh_frame, grade_endpoint
from system_clock import now_utc
from state_schema import atomic_write_json
from stop_levels import evidence_short_side, short_side
from performance_ledger import _sign_from_verdict

LEDGER = "component_evidence.json"
REPORT = "component_research_report.json"
HORIZONS = (4, 24, 72, 120)
MAX_RECORDS = 20000
MIN_N = 100
METHOD = "COMPONENT_FORWARD_V1"


def _num(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def _side(x):
    return int(x) if x in (-1, 0, 1) else 0


def snapshot(asset, v, frame, ctx, observed):
    observed = utc(observed)
    closed = (ctx.get("session") or {}).get("phase") == "Kapalı"
    valid = not closed and fresh_frame(frame, observed)
    day = v.get("day_direction") or {}
    move = v.get("recent_move") or {}
    z = _num(move.get("z_own"))
    trend = 1 if z is not None and z > 0 else -1 if z is not None and z < 0 else 0
    raw = _sign_from_verdict(v.get("verdict"))
    proposal = v.get("trade_plan") or {}
    return {"asset": asset, "observed": observed.isoformat(), "bucket": observed.floor("h").isoformat(),
            "logic": LOGIC_VERSION, "method": METHOD,
            "eligibility": "FRESH" if valid else "MARKET_CLOSED" if closed else "STALE_OR_MISSING",
            "model_status": str(v.get("learned_model_status") or "NO_MODEL"),
            "short": _side(evidence_short_side(v)), "raw_short": _side(short_side(v)),
            "raw_model": raw, "trend": trend, "reverse_trend": -trend,
            "day": _side(day.get("side")), "day_source": str(day.get("source") or "none"),
            "day_candidates": {str(k): _side(x) for k, x in (day.get("candidates") or {}).items()},
            "entry_allowed": v.get("entry_allowed") is True,
            "entry_grade": str(v.get("entry_grade") or "-"),
            "entry_reason": str(v.get("entry_status") or "")[:120],
            "gated": raw if v.get("entry_allowed") is True else 0,
            "proposal": proposal.get("action") == "trade",
            "proposal_side": _side(proposal.get("side")),
            "pulse": _num((v.get("pulse") or {}).get("score")),
            "sigma": _num((v.get("day_range") or {}).get("move_raw", (v.get("day_range") or {}).get("move"))),
            "price": _num((v.get("day_range") or {}).get("price")),
            "labels": {}}


def settle(rows, frames, now):
    for row in rows:
        if row.get("eligibility") != "FRESH" or row.get("method") != METHOD:
            continue
        for h in HORIZONS:
            k = str(h)
            if k in row["labels"]:
                continue
            ev = grade_endpoint(frames.get(row["asset"]), row["observed"], h, now, contiguous=h == 4)
            if ev["status"] != "PENDING":
                row["labels"][k] = ev


def sample(rows, h):
    # Pre-specified earliest-window schedule; even neutral and missing-label
    # slots reserve their full horizon. No selection on signal or outcome.
    result, last = [], None
    for r in sorted(rows, key=lambda r: r["observed"]):
        if r["eligibility"] != "FRESH":
            continue
        start, end = window(r["observed"], h)
        if last is not None and start < last:
            continue
        result.append(r)
        last = end
    return result


def metrics(selected, h, signal):
    valid = [r for r in selected if r["labels"].get(str(h), {}).get("status") == "EXACT"]
    active = [(r, r["labels"][str(h)]["log_return"], signal(r)) for r in valid]
    chosen = [(r, ret, side) for r, ret, side in active if side in (-1, 1)]
    n = len(chosen)
    hit = sum(side * ret > 0 for _, ret, side in chosen)
    base = sum(ret > 0 for _, ret, _ in chosen)
    # Paired always-long and simple momentum on identical active timestamps.
    # Zero returns are reported, not removed to make the signal look better.
    trend = [(r, ret, side) for r, ret, side in chosen if r["trend"]]
    return {"selected_windows": len(selected), "exact_labels": len(valid),
            "invalid_or_pending": len(selected) - len(valid),
            "active": n, "neutral": len(valid) - n,
            "zero_returns": sum(ret == 0 for _, ret, _ in chosen),
            "coverage": round(n / len(valid), 4) if valid else None,
            "direction_hit": round(hit / n, 4) if n else None,
            "always_long_same_windows": round(base / n, 4) if n else None,
            "trend_pair_n": len(trend),
            "trend_pair_model_hit": round(sum(side * ret > 0 for _, ret, side in trend) / len(trend), 4) if trend else None,
            "trend_pair_baseline_hit": round(sum(r["trend"] * ret > 0 for r, ret, _ in trend) / len(trend), 4) if trend else None,
            "mean_gross_bps_when_active": round(1e4 * sum(side * ret for _, ret, side in chosen) / n, 3) if n else None,
            "mean_gross_bps_all_exact_windows": round(1e4 * sum(side * ret for _, ret, side in active) / len(valid), 3) if valid else None,
            "status": "DESCRIPTIVE_ONLY" if n >= MIN_N else "INSUFFICIENT",
            "live_promotion": False}


def summarize(rows, now):
    by_version = {}
    for r in rows:
        by_version.setdefault(r["logic"], {}).setdefault(r["asset"], []).append(r)
    result = {}
    for logic, assets in by_version.items():
        result[logic] = {}
        for asset, rr in assets.items():
            item = {"observations": len(rr), "eligibility_counts": dict(Counter(r["eligibility"] for r in rr)),
                    "model_states": dict(Counter(r["model_status"] for r in rr)),
                    "day_sources": dict(Counter(r["day_source"] for r in rr)),
                    "entry_allowed_count": sum(r["entry_allowed"] for r in rr),
                    "proposal_count": sum(r["proposal"] for r in rr),
                    "entry_gate_reasons": dict(Counter(r["entry_reason"] for r in rr)),
                    "horizons": {}}
            for h in HORIZONS:
                selected = sample(rr, h)
                fields = ["raw_model", "gated", "trend", "reverse_trend"]
                if h == 4:
                    fields += ["short", "raw_short"]
                if h == 24:
                    fields += ["day", "proposal_side"]
                report = {k: metrics(selected, h, lambda r, k=k: r.get(k, 0)) for k in fields}
                if h == 24:
                    for name in ("taban", "mom4h", "mom24h", "rev24h", "charm", "gama_rev"):
                        report["day_candidate_" + name] = metrics(selected, h, lambda r, name=name: r["day_candidates"].get(name, 0))
                    vals = [r for r in selected if r["labels"].get("24", {}).get("status") == "EXACT"]
                    range_rows = [(r, r["labels"]["24"]["log_return"]) for r in vals if r["sigma"] and r["price"] and r["sigma"] > 0 and r["price"] > 0]
                    report["range_24h"] = {"n": len(range_rows), "cover": round(sum(abs(math.expm1(ret)) <= r["sigma"] / r["price"] for r, ret in range_rows) / len(range_rows), 4) if range_rows else None}
                    p = [(r["pulse"], abs(r["labels"]["24"]["log_return"])) for r in vals if r["pulse"] is not None]
                    corr = None
                    if len(p) >= 10:
                        a,b = zip(*p)
                        if len(set(a)) > 1 and len(set(b)) > 1:
                            corr = _num(pd.Series(a).rank().corr(pd.Series(b).rank()))
                    report["risk_pulse_24h"] = {"n": len(p), "rank_correlation_abs_return": corr}
                item["horizons"][str(h)] = report
            result[logic][asset] = item
    return {"method": METHOD, "label_schema": SCHEMA, "as_of": utc(now).isoformat(),
            "status": "RESEARCH_ONLY", "scope": "Independent components, exact endpoint prices, no fills/costs or profit proof",
            "no_live_promotion": True, "versions": result}


def bracket_diagnostics(trade_file="trade_ledger.csv", stop_file="stop_ledger.csv"):
    """Only new exact-path evidence; legacy R and stops remain archived."""
    out = {}
    for path, kind in ((trade_file, "trade"), (stop_file, "stop")):
        if not Path(path).exists():
            continue
        with Path(path).open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("logic") != LOGIC_VERSION or row.get("label_schema") != SCHEMA:
                    continue
                asset = row.get("asset", "?")
                key = kind if kind == "trade" else "stop_" + row.get("horizon", "?")
                stats = out.setdefault(asset, {}).setdefault(key, {"counts": {}, "values": []})
                reason = row.get("label_reason") or "PENDING"
                stats["counts"][reason] = stats["counts"].get(reason, 0) + 1
                if reason == "EXACT_PATH":
                    x = _num(row.get("r_mult" if kind == "trade" else "hunted"))
                    if x is not None:
                        stats["values"].append(x)
    for data in out.values():
        for key, stats in data.items():
            vals = stats.pop("values")
            stats["n"] = len(vals)
            stats["mean_theoretical_r" if key == "trade" else "hunted_rate"] = round(sum(vals)/len(vals), 4) if vals else None
    return out


def run_cycle(verdicts, frames, contexts, *, now=None, ledger=LEDGER, report=REPORT):
    now = utc(now or now_utc())
    path = Path(ledger)
    rows = json.loads(path.read_text(encoding="utf-8"))["rows"] if path.exists() else []
    if not isinstance(rows, list):
        raise ValueError("Corrupt component evidence; refusing reset")
    settle(rows, frames, now)
    existing = {(r["asset"], r["bucket"], r["logic"], r["method"]) for r in rows}
    for a, v in verdicts.items():
        rec = snapshot(a, v, frames.get(a), contexts.get(a) or {}, now)
        key = (a, rec["bucket"], rec["logic"], rec["method"])
        if key not in existing:
            rows.append(rec)
    rows = rows[-MAX_RECORDS:]
    result = summarize(rows, now)
    result["bracket_diagnostics"] = bracket_diagnostics()
    atomic_write_json(str(path), {"schema_version": "1.0.0", "rows": rows}, indent=None)
    atomic_write_json(str(report), result, indent=2)
    return {"method": METHOD, "status": "RESEARCH_ONLY", "records": len(rows), "report": str(report)}
