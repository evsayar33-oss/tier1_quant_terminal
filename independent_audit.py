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
import statistics
from datetime import datetime, timezone, timedelta
from pathlib import Path

ASSETS = ("SPX", "NQ", "XAU", "XAG", "BTC", "ETH")
HOURS = (4, 24)
COST_BPS = (0, 10, 20, 40)
MIN_INDEP = 30
PRICE_SYMBOLS = {"SPX": "^GSPC", "NQ": "^NDX", "XAU": "GC=F", "XAG": "SI=F", "BTC": "BTC-USD", "ETH": "ETH-USD"}
PRICE_MAX_AGE_HOURS = 2
OUTCOME_GRACE_HOURS = 48


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


def _valid_price(value):
    try:
        x = float(value)
        return x if math.isfinite(x) and x > 0 else None
    except (ValueError, TypeError, OverflowError):
        return None


def fetch_independent_prices(now, provider=None):
    """One independently timestamped quote/bar per asset per audit invocation.

    Yahoo Finance hourly bars are delayed/non-executable. Futures are
    continuous proxies, not investable contracts. No data is synthesized.
    """
    if provider is None:
        import yfinance as yf
        provider = yf.Ticker
    result = {}
    for asset, symbol in PRICE_SYMBOLS.items():
        try:
            bars = provider(symbol).history(period="5d", interval="1h", auto_adjust=True)
            if bars is None or bars.empty or "Close" not in bars:
                raise ValueError("EMPTY_HOURLY_BARS")
            if bars.index.tz is None:
                raise ValueError("BAR_TIMESTAMP_MISSING_TIMEZONE")
            latest = bars.dropna(subset=["Close"]).iloc[-1]
            timestamp = dt(bars.dropna(subset=["Close"]).index[-1].isoformat())
            age = (now-timestamp).total_seconds()
            if age < -3600 or age > PRICE_MAX_AGE_HOURS*3600:
                raise ValueError("STALE_OR_FUTURE_HOURLY_BAR")
            price = _valid_price(latest["Close"])
            if price is None:
                raise ValueError("INVALID_HOURLY_CLOSE")
            result[asset] = {"price":price,"bar_utc":utc(timestamp),
                             "source":"YAHOO_HOURLY_DELAYED_NON_EXECUTABLE",
                             "symbol":symbol}
        except Exception as exc:
            result[asset] = {"price":None,"source":"UNAVAILABLE",
                             "symbol":symbol,"error":str(exc)[:160]}
    return result


def append_price_snapshots(store, now, prices):
    """Observe independently of publication hash, including unchanged signals."""
    snaps=store.setdefault("snapshots", [])
    previous=store.get("last_price_poll_utc")
    if previous and dt(previous)>=now:
        raise ValueError("PRICE_POLL_OUT_OF_ORDER")
    for asset in ASSETS:
        item=prices.get(asset) or {}
        price=_valid_price(item.get("price"))
        # A single failed feed never turns into a fabricated price.
        snaps.append({"asset":asset,"observed_utc":utc(now),
                      "publication_utc":None,"source_hash":None,
                      "price":price,"price_source":item.get("source","UNAVAILABLE"),
                      "price_bar_utc":item.get("bar_utc"),
                      "symbol":item.get("symbol",PRICE_SYMBOLS[asset]),
                      "error":item.get("error")})
    store["last_price_poll_utc"]=utc(now)
    return len(ASSETS)


def observe(payload, store, now, manifest, price_rows=None, independent_prices=None):
    if not payload or not isinstance(payload.get("asset_verdicts"), dict):
        raise ValueError("terminal_state.json missing asset_verdicts")
    if now < dt(manifest["start_utc"]) or now >= dt(manifest["end_utc"]):
        return 0
    seen = store.setdefault("seen_publications", {})
    price_rows = price_rows or []
    independent_prices = independent_prices or {}
    snapshots = store.setdefault("snapshots", [])
    calls = store.setdefault("calls", [])
    added = 0
    pub = dt(payload["last_updated"])
    if pub > now + timedelta(minutes=5):
        raise ValueError("future production publication")
    if pub < now - timedelta(hours=3):
        store["stale_production_publication_utc"] = utc(pub)
        return 0
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
                        and dt(r["rec"]) <= pub + timedelta(minutes=5)
                        and (not r.get("t") or dt(r["t"]) <= pub)]
            if eligible:
                latest = max(eligible, key=lambda r: r["rec"])
                price = _valid_price(latest["p"])
                if price is not None:
                    price_source = "lagged_1h_bar_proxy_NOT_EXECUTABLE"
        live = independent_prices.get(asset) or {}
        if _valid_price(live.get("price")) is not None:
            price = float(live["price"])
            price_source = live.get("source", "INDEPENDENT_DELAYED_PROXY")
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
            if c["horizons"].get(key, {}).get("status") in ("GRADED","UNPRICEABLE_ENTRY"):
                continue
            t = dt(c["observed_utc"])
            if now < t + timedelta(hours=h):
                continue
            if c["entry_price"] is None:
                c["horizons"][key] = {"status": "UNPRICEABLE_ENTRY"}
                continue
            targets = [s for s in byasset.get(c["asset"], [])
                       if t+timedelta(hours=h) <= dt(s["observed_utc"]) <= t+timedelta(hours=h+1)]
            if not targets:
                status = "MISSING_FUTURE_PRICE" if now >= t+timedelta(hours=h+OUTCOME_GRACE_HOURS) else "PENDING_PRICE"
                c["horizons"][key] = {"status": status}
                continue
            s = min(targets, key=lambda x: x["observed_utc"])
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
           "price_polls":len({s["observed_utc"] for s in store.get("snapshots",[]) if s.get("source_hash") is None}),
           "last_price_poll_utc":store.get("last_price_poll_utc"),
           "price_coverage":{},
           "horizons": {}}
    for asset in ASSETS:
        samples=[s for s in store.get("snapshots",[]) if s.get("asset")==asset and s.get("source_hash") is None]
        out["price_coverage"][asset]={"polls":len(samples),"valid":sum(_valid_price(s.get("price")) is not None for s in samples),
             "last_source":samples[-1].get("price_source") if samples else None}
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
        pending = sum(c["horizons"].get(str(h), {}).get("status") == "PENDING_PRICE" for c in calls)
        net = {}
        for cost in COST_BPS:
            returns = [c["horizons"][str(h)]["gross_return"] - cost/10000 for c in sel]
            net[str(cost)] = {"hypothetical_mean_bps": round(10000*sum(returns)/n, 2) if n else None,
                              "hypothetical_positive_fraction": round(sum(r>0 for r in returns)/n, 4) if n else None}
        p = mcnemar_one_sided(b,d)
        out["horizons"][str(h)] = {"independent_by_asset_n": n, "model_hit": round(wins/n,4) if n else None,
             "always_long_hit": round(longwins/n,4) if n else None,
             "model_wilson_95": wilson(wins,n), "paired_discordance": {"model_only": b,"baseline_only":d},
             "paired_one_sided_p_unadjusted": round(p, 6), "missing_labels": missing, "pending_labels":pending,
             "hypothetical_cost_scenarios_bps": net,
             "verdict": "DESCRIPTIVE_ONLY" if n>=MIN_INDEP else "INSUFFICIENT",
             "multiple_testing_adjusted_p_bonferroni_12":min(1.,round(p*12,6)),
             "independent_assets_assumption_verified":False}
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
             f"Directional calls: {summary['total_calls']}; entry permitted: {summary['entry_allowed']}; without quote: {summary['unpriceable']}",
             f"Independent price polls: {summary.get('price_polls',0)}; last: {summary.get('last_price_poll_utc')}", "",
             "| Horizon | Nonoverlap N | Model hit | Always long | Paired p (unadjusted) | Missing labels | Verdict |",
             "|---|---:|---:|---:|---:|---:|---|"]
    for h,x in summary["horizons"].items():
        fmt=lambda v:"—" if v is None else f"{v:.1%}"
        lines.append(f"| {h}h | {x['independent_by_asset_n']} | {fmt(x['model_hit'])} | {fmt(x['always_long_hit'])} | {x['paired_one_sided_p_unadjusted']:.4f} | {x['missing_labels']} | {x['verdict']} |")
    lines.extend(["", "## Independent hourly reference price coverage", "",
                  "| Asset | Polls | Valid | Last source |","|---|---:|---:|---|"])
    for asset, q in summary.get("price_coverage",{}).items():
        lines.append(f"| {asset} | {q['polls']} | {q['valid']} | {q['last_source']} |")
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
    p.add_argument("--skip-market-fetch", action="store_true")
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
    prices={} if args.skip_market_fetch else fetch_independent_prices(now)
    if not args.skip_market_fetch:
        append_price_snapshots(store,now,prices)
    n=observe(payload,store,now,manifest,performance.get("records", []),prices)
    settle(store,now)
    summary=stats(store,manifest,now)
    save(args.audit,store)
    save(args.summary,summary)
    Path(args.report).parent.mkdir(parents=True,exist_ok=True)
    Path(args.report).write_text(report(summary))
    print(f"Audit new calls={n}; 4h independent={summary['horizons']['4']['independent_by_asset_n']}; 24h independent={summary['horizons']['24']['independent_by_asset_n']}")


if __name__=="__main__":
    main()
