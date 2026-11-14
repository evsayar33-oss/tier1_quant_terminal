"""Independent prospective, read-only Tier-1 audit.

Consumes only snapshots first observed by this job. Never reconstructs an
unobserved publication time from a historical bar. No production writes.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path

ASSETS = ("SPX", "NQ", "XAU", "XAG", "BTC", "ETH")
HOURS = (4, 24)
COST_BPS = (0, 10, 20, 40)
MIN_INDEP = 30


def dt(s):
    t = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError("naive timestamp")
    return t.astimezone(timezone.utc)


def utc(t):
    return t.isoformat().replace("+00:00", "Z")


def sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def load(path, default):
    return json.loads(Path(path).read_text()) if Path(path).exists() else default


def save(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    tmp.replace(p)


def direction(v):
    z = str(v.get("verdict") or "").upper()
    return 1 if z in ("AL", "BUY", "LONG") else -1 if z in ("SAT", "SELL", "SHORT") else 0


def wilson(k, n):
    if not n:
        return None
    z = 1.95996398454
    p = k / n
    den = 1 + z*z/n
    mid = (p + z*z/(2*n))/den
    half = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/den
    return [round(mid-half, 4), round(mid+half, 4)]


def mcnemar_one_sided(b, c):
    n = b+c
    if not n:
        return 1.0
    return sum(math.comb(n, i) for i in range(b, n+1)) / (2**n)


def observe(payload, store, now, manifest, price_rows=None):
    if not payload or not isinstance(payload.get("asset_verdicts"), dict):
        raise ValueError("terminal_state.json missing asset_verdicts")
    if now < dt(manifest["start_utc"]):
        return 0
    seen = store.setdefault("seen_publications", {})
    price_rows = price_rows or []
    snapshots = store.setdefault("snapshots", [])
    calls = store.setdefault("calls", [])
    added = 0
    pub = dt(payload["last_updated"])
    if pub > now + timedelta(minutes=5) or pub < now - timedelta(hours=3):
        raise ValueError("stale or future production publication")
    source_hash = sha({"updated": payload["last_updated"], "verdicts": payload["asset_verdicts"]})
    if source_hash in seen:
        return 0
    # The first audit observation is the earliest provable signal availability;
    # source publication is only metadata and never backdated as an entry.
    seen[source_hash] = utc(now)
    perf = payload.get("performance") or {}
    for asset in ASSETS:
        v = payload["asset_verdicts"].get(asset) or {}
        # A recorded price must be explicitly published in the same payload.
        # If not available, mark the call unpriceable; never use a later price.
        price = None
        for key in ("price", "last_price", "current_price"):
            z = v.get(key)
            try:
                if z is not None and math.isfinite(float(z)) and float(z)>0:
                    price = float(z)
                    break
            except (ValueError, TypeError):
                pass
        price_source = "verdict_quote" if price is not None else "UNAVAILABLE"
        if price is None:
            eligible = [r for r in price_rows if r.get("a") == asset and r.get("p") is not None
                        and r.get("rec") and dt(r["rec"]) <= now
                        and now - dt(r["rec"]) <= timedelta(hours=2)
                        and dt(r["rec"]) <= pub + timedelta(minutes=5)]
            if eligible:
                latest = max(eligible, key=lambda r: r["rec"])
                price = float(latest["p"])
                price_source = "lagged_1h_bar_proxy_NOT_EXECUTABLE"
        snap = {"asset": asset, "observed_utc": utc(now), "publication_utc": utc(pub),
                "source_hash": source_hash, "price": price, "price_source": price_source}
        snapshots.append(snap)
        side = direction(v)
        if not side:
            continue
        calls.append({"asset": asset, "observed_utc": utc(now), "publication_utc": utc(pub),
                      "source_hash": source_hash, "side": side, "entry_allowed": v.get("entry_allowed") is True,
                      "grade": str(v.get("entry_grade") or "-"), "entry_price": price, "price_source": price_source,
                      "model_stage": str(v.get("direction_stage") or ""),
                      "horizons": {}})
        added += 1
    store["last_audit_utc"] = utc(now)
    store["last_production_utc"] = utc(pub)
    store["last_production_records"] = perf.get("records_total")
    return added


def settle(store, now):
    snapshots = store.get("snapshots", [])
    byasset = {}
    for s in snapshots:
        if s["price"] is not None:
            byasset.setdefault(s["asset"], []).append(s)
    for rows in byasset.values():
        rows.sort(key=lambda x: x["observed_utc"])
    for c in store.get("calls", []):
        for h in HOURS:
            key = str(h)
            if key in c["horizons"]:
                continue
            t = dt(c["observed_utc"])
            if now < t + timedelta(hours=h+1):
                continue
            if c["entry_price"] is None:
                c["horizons"][key] = {"status": "UNPRICEABLE_ENTRY"}
                continue
            targets = [s for s in byasset.get(c["asset"], [])
                       if t+timedelta(hours=h) <= dt(s["observed_utc"]) <= t+timedelta(hours=h+1)]
            if not targets:
                # Missing label is explicit and final, never silently ignored.
                c["horizons"][key] = {"status": "MISSING_FUTURE_PRICE"}
                continue
            s = targets[0]
            gross = c["side"] * (s["price"] / c["entry_price"] - 1)
            c["horizons"][key] = {"status": "GRADED", "exit_observed_utc": s["observed_utc"],
                                  "exit_price": s["price"], "gross_return": gross,
                                  "baseline_long_return": s["price"] / c["entry_price"] - 1}


def nonoverlap(calls, h):
    last = {}
    selected = []
    for c in sorted(calls, key=lambda x: (x["asset"], x["observed_utc"])):
        o = c["horizons"].get(str(h), {})
        if o.get("status") != "GRADED":
            continue
        t = dt(c["observed_utc"])
        if c["asset"] in last and t < last[c["asset"]] + timedelta(hours=h+1):
            continue
        selected.append(c)
        last[c["asset"]] = t
    return selected


def stats(store, manifest, now):
    calls = [c for c in store.get("calls", []) if
             dt(manifest["start_utc"]) <= dt(c["observed_utc"]) < dt(manifest["end_utc"])]
    out = {"start_utc": manifest["start_utc"], "end_utc": manifest["end_utc"],
           "as_of_utc": utc(now), "total_calls": len(calls),
           "entry_allowed": sum(c["entry_allowed"] for c in calls),
           "unpriceable": sum(c["entry_price"] is None for c in calls),
           "horizons": {}}
    for h in HOURS:
        sel = nonoverlap(calls, h)
        n = len(sel)
        wins = sum(c["horizons"][str(h)]["gross_return"] > 0 for c in sel)
        longwins = sum(c["horizons"][str(h)]["baseline_long_return"] > 0 for c in sel)
        b = sum(c["horizons"][str(h)]["gross_return"] > 0 and
                c["horizons"][str(h)]["baseline_long_return"] <= 0 for c in sel)
        d = sum(c["horizons"][str(h)]["gross_return"] <= 0 and
                c["horizons"][str(h)]["baseline_long_return"] > 0 for c in sel)
        missing = sum(c["horizons"].get(str(h), {}).get("status") == "MISSING_FUTURE_PRICE" for c in calls)
        net = {}
        for cost in COST_BPS:
            returns = [c["horizons"][str(h)]["gross_return"] - cost/10000 for c in sel]
            net[str(cost)] = {"hypothetical_mean_bps": round(10000*sum(returns)/n, 2) if n else None,
                              "hypothetical_positive_fraction": round(sum(r>0 for r in returns)/n, 4) if n else None}
        p = mcnemar_one_sided(b,d)
        out["horizons"][str(h)] = {"independent_by_asset_n": n, "model_hit": round(wins/n,4) if n else None,
             "always_long_hit": round(longwins/n,4) if n else None,
             "model_wilson_95": wilson(wins,n), "paired_discordance": {"model_only": b,"baseline_only":d},
             "paired_one_sided_p_unadjusted": round(p, 6), "missing_labels": missing,
             "hypothetical_cost_scenarios_bps": net,
             "verdict": "DESCRIPTIVE_ONLY" if n>=MIN_INDEP else "INSUFFICIENT"}
    return out


def report(summary):
    lines = ["# Tier-1 Independent Prospective Audit", "",
             "Read-only audit. No orders. No observed fills. No realized NAV or proven trading edge.",
             "Signals are timestamped at FIRST audit observation, not the original bar timestamp.",
             "Prices are observed prospectively by the audit; when no quote exists, the latest published 1h bar close is used as a LAGGED NON-EXECUTABLE PROXY, never a live fill.",
             "Cost scenarios are hypothetical directional holding returns, NOT executable trade P&L.",
             "The test compares with always-long on paired windows; p-values are unadjusted, correlated assets remain.",
             "Neither a 30-day calendar window nor a significant directional result automatically authorizes trading.", "",
             f"Window: {summary['start_utc']} — {summary['end_utc']}",
             f"As of: {summary['as_of_utc']}",
             f"Directional calls: {summary['total_calls']}; entry permitted: {summary['entry_allowed']}; without quote: {summary['unpriceable']}", "",
             "| Horizon | Nonoverlap N | Model hit | Always long | Paired p (unadjusted) | Missing labels | Verdict |",
             "|---|---:|---:|---:|---:|---:|---|"]
    for h,x in summary["horizons"].items():
        fmt=lambda v:"—" if v is None else f"{v:.1%}"
        lines.append(f"| {h}h | {x['independent_by_asset_n']} | {fmt(x['model_hit'])} | {fmt(x['always_long_hit'])} | {x['paired_one_sided_p_unadjusted']:.4f} | {x['missing_labels']} | {x['verdict']} |")
    lines.extend(["", "## Hypothetical all-in cost sensitivity (not net NAV)", "",
                  "These calculations use first-seen published prices, often lagged 1h bar proxies, and fixed round-trip costs. No fill, funding, borrow, or slippage verification.", "",
                  "| Horizon | 0 bps | 10 bps | 20 bps | 40 bps |",
                  "|---|---:|---:|---:|---:|"])
    for h,x in summary["horizons"].items():
        cells=[x["hypothetical_cost_scenarios_bps"][str(c)]["hypothetical_mean_bps"] for c in COST_BPS]
        lines.append(f"| {h}h | " + " | ".join("—" if z is None else f"{z:+.1f}" for z in cells) + " |")
    lines.extend(["", "## Decision gate", "",
                  "BLOCKED: No realized trade P&L is produced by this audit. Independent samples and paired evidence are descriptive only.",
                  "Existing production entry gates, model weights, 30-day manifest, and research ledgers are untouched.", ""])
    return "\n".join(lines)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--state", default="terminal_state.json")
    p.add_argument("--manifest", default="research_30d/manifest.json")
    p.add_argument("--performance", default="performance_ledger.json")
    p.add_argument("--audit", default="independent_audit/ledger.json")
    p.add_argument("--summary", default="independent_audit/summary.json")
    p.add_argument("--report", default="independent_audit/report.md")
    p.add_argument("--now", default=None)
    args=p.parse_args()
    manifest=load(args.manifest,None)
    if not manifest:
        raise SystemExit("Missing existing 30-day manifest: fail closed, do not start/restart it")
    now=dt(args.now) if args.now else datetime.now(timezone.utc)
    store=load(args.audit,{"schema":"1.0","snapshots":[],"calls":[],"seen_publications":{}})
    payload=load(args.state,None)
    if payload is None:
        raise SystemExit("Missing published terminal state")
    performance = load(args.performance, {"records":[]})
    n=observe(payload,store,now,manifest,performance.get("records", []))
    settle(store,now)
    summary=stats(store,manifest,now)
    save(args.audit,store)
    save(args.summary,summary)
    Path(args.report).parent.mkdir(parents=True,exist_ok=True)
    Path(args.report).write_text(report(summary))
    print(f"Audit new calls={n}; 4h independent={summary['horizons']['4']['independent_by_asset_n']}; 24h independent={summary['horizons']['24']['independent_by_asset_n']}")


if __name__=="__main__":
    main()
