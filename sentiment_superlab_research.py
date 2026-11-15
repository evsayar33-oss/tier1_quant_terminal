"""Point-in-time Tier-1 -> quant_superlab research handoff.

This is a PREREGISTERED, finite exploratory grid. It imports the actual
quant_superlab statistical metrics; no legacy replay scores or backfilled
sentiment values. 30 days is insufficient for a valid long-run strategy gate.
NO orders, registry ACCEPT, model changes or paper auto-promotion.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ASSETS = ("SPX", "NQ", "XAU", "XAG", "BTC", "ETH")
COST_BPS = (0.0, 20.0, 40.0)  # synthetic stress only; not measured real fills
MIN_DISCOVERY_DAYS = 20
MIN_WF_TRAIN_DAYS = 90
MIN_WF_TEST_DAYS = 90
MIN_STAT_DAYS = 180
CONFIGS = ("reversal_25_75", "reversal_20_80",
           "momentum_25_75", "momentum_20_80")


def dt(value):
    t = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError("Time must include UTC offset")
    return t.astimezone(timezone.utc)


def valid_float(value):
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except (ValueError, TypeError, OverflowError):
        return None


def integrity(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_source(root):
    root = Path(root)
    manifest_file = root / "manifest.json"
    ledger_file = root / "observations.csv"
    if not manifest_file.exists() or not ledger_file.exists():
        raise ValueError("Required prospective manifest and observation ledger missing")
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if manifest.get("schema") != 1:
        raise ValueError("Unknown prospective schema")
    if set(manifest.get("assets", [])) != set(ASSETS):
        raise ValueError("Six-asset coverage contract mismatch")
    start, end = dt(manifest["start_utc"]), dt(manifest["end_utc"])
    if end <= start or end - start != timedelta(days=30):
        raise ValueError("The preregistered 30-day window has been changed")
    with ledger_file.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        if row.get("experiment_id") != manifest["experiment_id"]:
            raise ValueError("Cross-experiment row contamination")
    if len(rows) != len({(r["observed_utc"], r["asset"]) for r in rows}):
        raise ValueError("Duplicate asset/UTC hour rows")
    return manifest, rows, {
        "manifest_sha256": integrity(manifest_file),
        "observations_sha256": integrity(ledger_file),
    }


def sample_days(manifest, rows, asset):
    """One feature observation per UTC calendar day, future price strictly later.

    FNG is published daily: counting 6 hourly observations as 6 independent
    trials would be pseudo-replication. We conservatively use daily blocks for
    all assets, including implied-vol proxies.
    """
    start, end = dt(manifest["start_utc"]), dt(manifest["end_utc"])
    rr = sorted(
        (r for r in rows if r["asset"] == asset),
        key=lambda x: x["observed_utc"])
    future_prices = []
    for row in rr:
        price = valid_float(row.get("price"))
        if price is None or price <= 0 or row.get("price_status") != "OK":
            continue
        try:
            seen = dt(row["observed_utc"])
            bar = dt(row["price_bar_utc"])
        except (ValueError, KeyError):
            continue
        if not (start <= seen < end + timedelta(hours=48)):
            continue
        # A price bar must be known strictly before the observation.
        if bar > seen:
            continue
        future_prices.append((seen, price))
    chosen = {}
    for row in rr:
        try:
            seen = dt(row["observed_utc"])
        except (ValueError, KeyError):
            continue
        if not (start <= seen < end) or row.get("data_status") != "OBSERVED":
            continue
        if row.get("price_status") != "OK":
            continue
        price = valid_float(row.get("price"))
        if price is None or price <= 0:
            continue
        if asset in ("BTC", "ETH"):
            feature = valid_float(row.get("sentiment_value"))
            if row.get("sentiment_status") != "OK" or feature is None:
                continue
            # Recorded first-seen UTC must not be after the signal.
            try:
                if dt(row["sentiment_first_seen_utc"]) > seen:
                    continue
                if dt(row["sentiment_published_utc"]) > seen:
                    continue
            except (KeyError, ValueError):
                continue
        else:
            feature = valid_float(row.get("iv_percentile"))
            if row.get("iv_status") != "OK" or feature is None:
                continue
            try:
                if dt(row["iv_bar_utc"]) > seen:
                    continue
            except (KeyError, ValueError):
                continue
        day = seen.date().isoformat()
        if day in chosen:
            continue
        # First qualifying observation for each UTC date, not best in hindsight.
        chosen[day] = (seen, price, feature)
    samples = []
    for day, (seen, price, feature) in sorted(chosen.items()):
        # Future labels are only observations recorded AFTER target.
        eligible = [(ts, p) for ts, p in future_prices
                    if seen + timedelta(hours=24) <= ts <= seen + timedelta(hours=27)]
        if not eligible:
            continue
        _, future_price = min(eligible, key=lambda x: x[0])
        samples.append({"day": day, "seen": seen.isoformat(), "feature": feature,
                        "forward_24h": future_price / price - 1})
    return samples


def direction(name, feature):
    threshold_low, threshold_high = (20, 80) if "20_80" in name else (25, 75)
    is_low, is_high = feature <= threshold_low, feature >= threshold_high
    if not is_low and not is_high:
        return 0
    reverse = name.startswith("reversal_")
    return (1 if is_low else -1) * (1 if reverse else -1)


def series_for(samples, name, cost_bps):
    # Independent 24h hold proxy. Costs are assumed, not executable fills.
    values = [direction(name, s["feature"]) * s["forward_24h"] -
              abs(direction(name, s["feature"])) * cost_bps / 10000 for s in samples]
    return pd.Series(values, index=pd.to_datetime([s["day"] for s in samples], utc=True))


def discovery(manifest, rows, source_hashes, superlab_dir, now):
    root = Path(superlab_dir).resolve()
    if not (root / "lab" / "metrics.py").is_file() or not (root / "lab" / "validation.py").is_file():
        raise ValueError("Not a quant_superlab checkout; independent validation unavailable")
    sys.path.insert(0, str(root))
    from lab import metrics, validation  # True external quant_superlab routines
    metrics.set_periods(365)  # daily sampling, crypto continuous; comparisons not approval.
    dates = dt(manifest["end_utc"])
    if now < dates + timedelta(hours=int(manifest.get("label_grace_hours", 48))):
        raise ValueError("Study is not past predeclared label-settlement grace")
    report = {
        "schema": 1, "study": manifest["experiment_id"],
        "end_utc": manifest["end_utc"], "completed_utc": now.isoformat(),
        "tier1_inputs_sha256": source_hashes,
        "quant_superlab_git_sha": None, "source_policy": "PROSPECTIVE_ONLY",
        "legacy_results_used": False, "automatic_trade_approval": False,
        "production_mutated": False, "statistical_gate": "NOT_ELIGIBLE",
        "cost_scenarios_bps": list(COST_BPS),
        "trials_pre_registered": len(CONFIGS) * len(ASSETS) * len(COST_BPS),
        "assets": {}, "trials": [],
        "limitations": [
            "A single 30-day collection is insufficient for 3-year quant_superlab OOS gate",
            "Proxy sentiment and delayed 1h closes are NOT executable market fills",
            "Trading costs are hypothetical scenario assumptions",
            "Correlated SPX/NQ and BTC/ETH observations do not count as independent markets",
            "FNG is daily and Bitcoin-weighted; ETH inherits market context, not an ETH index",
            "A new untouched prospective test is mandatory before paper approval",
        ],
    }
    max_days = 0
    for asset in ASSETS:
        samples = sample_days(manifest, rows, asset)
        max_days = max(max_days, len(samples))
        z = {"independent_daily_24h_labels": len(samples),
             "usable_days": len({s["day"] for s in samples}),
             "classification": "INSUFFICIENT" if len(samples) < MIN_STAT_DAYS else "RESEARCH_ELIGIBLE"}
        if not samples:
            report["assets"][asset] = z
            continue
        baseline = pd.Series([x["forward_24h"] for x in samples],
                             index=pd.to_datetime([x["day"] for x in samples], utc=True))
        z["always_long_gross_mean_bps"] = round(float(baseline.mean()*10000), 3)
        matrix = {}
        for variant in CONFIGS:
            # Trial count includes losers and flat configurations.
            net = series_for(samples, variant, 20.0)
            matrix[variant] = net
            for cost in COST_BPS:
                r = series_for(samples, variant, cost)
                turn = sum(direction(variant, x["feature"]) != 0 for x in samples)
                item = {
                    "asset": asset, "variant": variant, "cost_bps_roundtrip": cost,
                    "n_independent_days": len(samples), "positions": turn,
                    "mean_net_bps": round(float(r.mean()*10000), 3),
                    "total_net_compounded": round(float((1+r).prod()-1), 6),
                    "sharpe_exploratory": round(float(metrics.sharpe(r)), 3),
                    "max_drawdown_exploratory": round(float(metrics.max_drawdown(r)), 5),
                    "candidate_verdict": "INSUFFICIENT_OUT_OF_SAMPLE",
                }
                report["trials"].append(item)
        # No significance output on 30 days: don't pretend bootstrap/DSR
        # can fix inadequate temporal market-regime coverage.
        if len(samples) >= MIN_STAT_DAYS:
            R = pd.DataFrame(matrix)
            z["pbo"] = metrics.pbo(R)
            z["reality_check_p"] = metrics.reality_check(R, n=300, block=7)
            z["dsr"] = {k: metrics.dsr(R[k], len(CONFIGS), 
                          [metrics.sharpe(R[v]) / math.sqrt(365) for v in CONFIGS])
                        for k in CONFIGS}
            # Requires >=90 training and >=90 untouched evaluation days.
            z["walk_forward"] = "REQUIRES_NEW_LOCKED_PROSPECTIVE_PERIOD"
            # Bootstrap conditional *only* on sufficient day blocks.
            z["block_bootstrap"] = {
                k: validation.block_bootstrap(R[k], n=300, block=7)
                for k in CONFIGS}
        report["assets"][asset] = z
    report["unique_days_max_per_asset"] = max_days
    report["decision"] = "NEED_MORE_INDEPENDENT_PROSPECTIVE_DATA"
    try:
        report["quant_superlab_git_sha"] = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        raise ValueError("quant_superlab code revision could not be established")
    report["study_id"] = "tier1_sentiment_superlab"
    report["stage"] = "FINAL"
    report["assessment"] = {
        "decision": report["decision"],
        "reason": "30-day new-factor observations cannot satisfy the multi-year independent profitability gate",
        "followup_assets": [asset for asset, d in report["assets"].items()
                            if d["independent_daily_24h_labels"] >= MIN_DISCOVERY_DAYS],
        "per_asset": {asset: {"nonoverlap_n": d["independent_daily_24h_labels"],
                               "status": d["classification"]}
                      for asset, d in report["assets"].items()},
    }
    report["next_action"] = (
        "Preregister a longer independent research window, preserve raw first-seen ledgers, "
        "obtain executable bid/ask and fill-cost evidence, then run full quant_superlab PIPELINE. "
        "Do not claim profitable strategy or auto-merge an ACCEPT.")
    return report


def write_report(result, dest):
    out = Path(dest)
    out.mkdir(parents=True, exist_ok=True)
    js = out / "tier1_sentiment_superlab-final.json"
    tmp = js.with_suffix(".tmp")
    tmp.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    tmp.replace(js)
    trial_csv = out / "tier1_sentiment_superlab-trials.csv"
    columns = ["asset", "variant", "cost_bps_roundtrip", "n_independent_days",
               "positions", "mean_net_bps", "total_net_compounded",
               "sharpe_exploratory", "max_drawdown_exploratory", "candidate_verdict"]
    with trial_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, columns)
        writer.writeheader()
        writer.writerows(result["trials"])
    return js


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="sentiment_30d")
    ap.add_argument("--superlab", required=True)
    ap.add_argument("--out", default="sentiment_study_decisions")
    args = ap.parse_args()
    m, rows, checksums = load_source(args.input)
    result = discovery(m, rows, checksums, args.superlab, datetime.now(timezone.utc))
    write_report(result, args.out)
    print("Research verdict:", result["decision"], "| trials:", result["trials_pre_registered"])


if __name__ == "__main__":
    main()
