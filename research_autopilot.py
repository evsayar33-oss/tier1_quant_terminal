"""Fail-closed, evidence-only decisions for the two existing Tier-1 observation windows.

There are NO production weights, entry gates, trading actions or automatic
strategy promotions here. Input is prospective raw ledgers, never legacy
historical_replay or RESEARCH_LOG performance claims. Immutable decisions are
saved only on an external audit branch by the GitHub workflow.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

ASSETS = ("SPX", "NQ", "XAU", "XAG", "BTC", "ETH")
START_V2 = "2026-10-23T00:00:00+00:00"  # Calendar-day lower bound, NOT claimed exact inception time
END_V2 = "2026-11-24T00:00:00+00:00"  # Include entire documented 23 November date
LOGIC_V2 = "2026.10.23-v2"
V2_GRACE_H = 96  # Allow prospective 24h grades and publication delays to settle
RESEARCH_GRACE_H = 48  # Allow 4h outcome window and delayed publication
MIN_V2_4H = 100
MIN_RESEARCH_4H = 100


def when(value):
    t = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError("UTC offset required")
    return t.astimezone(timezone.utc)


def iso(t):
    return t.astimezone(timezone.utc).isoformat(timespec="seconds")


def safe_float(value):
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError, OverflowError):
        return None


def load_csv(path):
    if not Path(path).exists():
        return None
    with Path(path).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_json(path):
    if not Path(path).exists():
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(paths):
    # Stable evidence fingerprint, not a claim that GitHub data are immutable.
    result = {}
    for name in paths:
        p = Path(name)
        result[name] = hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
    return result


def exact_mcnemar_one_sided(model_only, baseline_only):
    """P(X >= model_only), X ~ Bin(n discordances, 0.5)."""
    n = model_only + baseline_only
    if n == 0:
        return 1.0
    # Numerically stable small-n summation via binomial survival identity.
    return min(1.0, sum(math.comb(n, j) for j in range(model_only, n + 1)) / (2 ** n))


def v2_decision(start, end):
    path = "forecast_ledger.csv"
    rows = load_csv(path)
    trades = load_csv("trade_ledger.csv")
    result = {"study": "tier1_v2_forward", "source": "version-locked prospective forecast_ledger.csv",
              "source_sha256": digest([path, "trade_ledger.csv"]),
              "per_asset": {}, "trade_grading": {}, "policy": "NO_LIVE_PROMOTION"}
    if rows is None:
        result.update(decision="DATA_UNAVAILABLE", reason="forecast_ledger.csv missing; cannot evaluate")
        return result
    ready = []
    for asset in ASSETS:
        points = []
        for row in rows:
            if row.get("asset") != asset or row.get("logic") != LOGIC_V2:
                continue
            try:
                t = when(row["ts"])
            except (TypeError, KeyError, ValueError):
                continue
            if not (start <= t < end) or str(row.get("graded_4h")).strip() not in ("1", "1.0"):
                continue
            side, ret = safe_float(row.get("lean4h")), safe_float(row.get("ret_4h"))
            if side not in (-1, 1) or ret is None or ret == 0:
                continue
            points.append((t, side, ret))
        # Nonoverlap per asset; never multiply effective N with hourly repeats.
        points.sort(key=lambda p: p[0])
        selected, last = [], None
        for p in points:
            if last is None or p[0] >= last + timedelta(hours=4):
                selected.append(p)
                last = p[0]
        n = len(selected)
        model_only = baseline_only = model_hits = baseline_hits = 0
        mean_directional_bps = None
        if n:
            directional = []
            for _, side, ret in selected:
                actual = 1 if ret > 0 else -1
                model_good = side == actual
                base_good = actual == 1
                model_hits += model_good
                baseline_hits += base_good
                model_only += model_good and not base_good
                baseline_only += base_good and not model_good
                directional.append(side * ret * 10000)
            mean_directional_bps = round(sum(directional) / n, 3)
        p_adj = min(1.0, exact_mcnemar_one_sided(model_only, baseline_only) * len(ASSETS))
        # These direction observations cannot establish executable P&L.
        followup = (n >= MIN_V2_4H and
                    model_hits > baseline_hits and mean_directional_bps is not None and
                    mean_directional_bps > 0 and p_adj < 0.05)
        result["per_asset"][asset] = {
            "independent_4h_n": n, "model_hit": round(model_hits / n, 4) if n else None,
            "always_long_hit": round(baseline_hits / n, 4) if n else None,
            "mean_directional_bps_GROSS_NONEXECUTABLE": mean_directional_bps,
            "paired_one_sided_p_bonferroni_6": round(p_adj, 6),
            "suggested_status": "REPLICATE_PROSPECTIVELY" if followup else
                                "INSUFFICIENT" if n < MIN_V2_4H else "NOT_SUPPORTED",
        }
        if followup:
            ready.append(asset)
        if trades is not None:
            relevant = [r for r in trades if r.get("asset") == asset and
                        r.get("logic") == LOGIC_V2 and valid_between(r.get("ts"), start, end)]
            graded = [r for r in relevant if str(r.get("graded")).strip() in ("1", "1.0")
                      and safe_float(r.get("r_mult")) is not None]
            result["trade_grading"][asset] = {
                "proposed": len(relevant), "graded": len(graded),
                "note": "Theoretical R records, not verified executable fills or net NAV"}
    result.update(
        decision="REPLICATE_PROSPECTIVELY" if ready else
                 "DATA_INSUFFICIENT" if all(x["independent_4h_n"] < MIN_V2_4H for x in result["per_asset"].values())
                 else "NO_DEMONSTRATED_ADVANTAGE",
        followup_assets=ready,
        reason=("Only preregistered logic-version prospective records considered. "
                "Direction, proposed trades and paper R cannot authorize live execution."),
    )
    return result


def valid_between(stamp, start, end):
    try:
        return start <= when(stamp) < end
    except (TypeError, ValueError):
        return False


def research_decision(manifest):
    from research_30d_eval import evaluate

    rows = load_csv("research_30d/observations.csv")
    summary = load_json("independent_audit/summary.json")
    start, end = when(manifest["start_utc"]), when(manifest["end_utc"])
    result = {
        "study": "research30_crypto_flow", "experiment_id": manifest["experiment_id"],
        "source": "persisted spot/linear snapshots (not continuous CVD)",
        "source_sha256": digest(["research_30d/manifest.json",
                                 "research_30d/observations.csv",
                                 "independent_audit/summary.json"]),
        "per_asset": {}, "independent_audit": {}, "policy": "NO_LIVE_PROMOTION",
    }
    if rows is None:
        result.update(decision="DATA_UNAVAILABLE", reason="snapshot ledger missing")
        return result
    eligible = [r for r in rows if r.get("experiment_id") == manifest["experiment_id"]
                and valid_between(r.get("ts"), start, end)]
    scores = evaluate(eligible, min_n=MIN_RESEARCH_4H)
    followup = []
    for asset in ("BTC", "ETH"):
        rr = [r for r in eligible if r.get("asset") == asset and r.get("market") == "spot"]
        ok = sum(r.get("status") == "OK_SAMPLE" for r in rr)
        s = scores.get(asset) or {}
        n = int(s.get("non_overlapping_n") or 0)
        hit, base = s.get("direction_hit"), s.get("always_long_hit")
        # A descriptive advantage cannot be promoted to a live rule.
        candidate = bool(n >= MIN_RESEARCH_4H and
                         len(rr) >= MIN_RESEARCH_4H and
                         ok / len(rr) >= 0.80 and
                         hit is not None and base is not None and hit > base)
        result["per_asset"][asset] = {
            "nonoverlap_n": n, "hit": hit, "always_long": base,
            "observed_spot_samples": len(rr), "fresh_valid_spot_samples": ok,
            "sample_coverage": round(ok / len(rr), 4) if rr else None,
            "status": "INDEPENDENT_REPLICATION_NEEDED" if candidate
                      else "INSUFFICIENT" if n < MIN_RESEARCH_4H or len(rr) < MIN_RESEARCH_4H
                      else "NOT_SUPPORTED",
        }
        if candidate:
            followup.append(asset)
    if summary:
        result["independent_audit"] = {
            "entry_allowed": summary.get("entry_allowed"),
            "total_calls": summary.get("total_calls"),
            "note": "Independent audit prices are non-executable proxies; no fills, real NAV or funding"
        }
    result.update(
        decision="INDEPENDENT_REPLICATION_NEEDED" if followup else
                 "DATA_INSUFFICIENT" if all(v["status"] == "INSUFFICIENT" for v in result["per_asset"].values())
                 else "NO_DEMONSTRATED_ADVANTAGE",
        followup_assets=followup,
        reason=("Sampled aggressor flow is not full CVD. Even a positive "
                "descriptive result requires fresh untouched OOS, cost and execution proof."),
    )
    return result


def studies():
    fixed = {"id": "tier1_v2_forward", "start_utc": START_V2,
             "end_utc": END_V2, "grace_hours": V2_GRACE_H, "kind": "v2"}
    yield fixed
    manifest = load_json("research_30d/manifest.json")
    if manifest is None:
        # No invented end date or reset for an absent manifest.
        yield {"id": "research30_crypto_flow", "invalid": "Manifest missing",
               "kind": "research"}
    else:
        yield {"id": "research30_crypto_flow", "kind": "research",
               "start_utc": manifest.get("start_utc"), "end_utc": manifest.get("end_utc"),
               "grace_hours": RESEARCH_GRACE_H, "manifest": manifest}


def stage_record(study, now, stage, assessment):
    return {
        "schema": 1, "study_id": study["id"], "stage": stage,
        "as_of_utc": iso(now), "start_utc": study.get("start_utc"),
        "end_utc": study.get("end_utc"), "grace_hours": study.get("grace_hours"),
        "auto_applied": "RESEARCH_STATUS_ONLY",
        "live_orders": False, "production_logic_modified": False,
        "assessment": assessment,
    }


def generate(now, output):
    """Immutable once written. Return newly created decisions only."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    new = []
    for study in studies():
        if study.get("invalid"):
            # A missing manifest is a blocker, not permission to guess deadlines.
            continue
        try:
            start, end = when(study["start_utc"]), when(study["end_utc"])
        except (ValueError, TypeError, KeyError):
            continue
        if end <= start or now < end:
            continue
        close = output / (study["id"] + "-window_closed.json")
        if not close.exists():
            a = {"decision": "WINDOW_CLOSED_AWAITING_LABELS",
                 "reason": "Collection window closed; allow post-window label settlement before final decision",
                 "label_grace_until_utc": iso(end + timedelta(hours=study["grace_hours"]))}
            close.write_text(json.dumps(stage_record(study, now, "WINDOW_CLOSED", a),
                                       indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            new.append(close)
        final = output / (study["id"] + "-final.json")
        if now >= end + timedelta(hours=study["grace_hours"]) and not final.exists():
            try:
                a = v2_decision(start, end) if study["kind"] == "v2" else research_decision(study["manifest"])
            except Exception as exc:
                # No frozen final on transient data/parse errors. Retry the next scheduled run.
                print("BLOCKED_RETRY " + study["id"] + ": " + str(exc))
                continue
            if a["decision"] == "DATA_UNAVAILABLE":
                print("BLOCKED_RETRY " + study["id"] + ": missing required data")
                continue
            final.write_text(json.dumps(stage_record(study, now, "FINAL", a),
                                        indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            new.append(final)
    return new


def main():
    parser = argparse.ArgumentParser(description="Study-expiry research-only decisions")
    parser.add_argument("--out", default="research_decisions")
    parser.add_argument("--now", default=None, help="Offset-aware UTC ISO time; for offline tests")
    args = parser.parse_args()
    current = when(args.now) if args.now else datetime.now(timezone.utc)
    created = generate(current, args.out)
    for p in created:
        data = load_json(p)
        print(data["study_id"], data["stage"], data["assessment"]["decision"])
    print("New decisions:", len(created), "| No live actions, no promotion")


if __name__ == "__main__":
    main()
