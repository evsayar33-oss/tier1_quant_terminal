"""Isolated 30-day market-microstructure research; no production decision authority.

Public Bybit recent-trade samples are NOT continuous CVD or full footprint.
Persist small UTC-stamped observations for SPOT and linear futures. Never
interpolate missed data or substitute synthetic observations.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path("research_30d")
MANIFEST = ROOT / "manifest.json"
LEDGER = ROOT / "observations.csv"
REPORT = ROOT / "report.md"
ASSETS = ("BTC", "ETH")
MARKETS = ("spot", "linear")
FIELDS = ("ts", "experiment_id", "asset", "market", "source", "trade_count",
          "first_trade_ms", "last_trade_ms", "sample_span_s", "buy_usdt",
          "sell_usdt", "signed_usdt", "imbalance", "last_trade_price",
          "reference_price", "observed_at_ms", "status", "detail")
API = "https://api.bybit.com/v5/market/recent-trade"
MAX_AGE_SECONDS = 300
MIN_TRADES = 20
MAX_SNAPSHOT_SPAN_SECONDS = 600
MAX_LINES = 7000


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def timestamp(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def read_manifest() -> dict[str, Any] | None:
    if not MANIFEST.exists():
        return None
    with MANIFEST.open(encoding="utf-8") as f:
        return json.load(f)


def start(now: datetime | None = None, *, experiment_id: str = "") -> dict[str, Any]:
    """Idempotent start. Reset is intentionally unsupported; archive before a new run."""
    now = now or utcnow()
    old = read_manifest()
    if old:
        return old
    ROOT.mkdir(parents=True, exist_ok=True)
    exp = experiment_id or "evidence-" + now.strftime("%Y%m%dT%H%M%SZ")
    obj = {"schema": 1, "experiment_id": exp, "start_utc": timestamp(now),
           "end_utc": timestamp(now + timedelta(days=30)),
           "duration_days": 30, "status": "COLLECTING",
           "production_policy": "ADVISORY_ONLY",
           "candidate_policy": "NO_AUTOMATIC_PROMOTION",
           "markets": list(MARKETS), "assets": list(ASSETS),
           "data_semantics": "RECENT_TRADES_SAMPLE_NOT_CONTINUOUS_CVD",
           "primary_question": "Do sampled taker imbalances predict independent 4h forward returns?",
           "model_revision": "research30-v1"}
    tmp = MANIFEST.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, MANIFEST)
    return obj


def parse_recent_trades(raw: list[dict[str, Any]], *, now_ms: int) -> dict[str, Any]:
    seen = set()
    clean = []
    for r in raw:
        try:
            key = str(r["execId"])
            if key in seen or r.get("isBlockTrade") is True:
                continue
            seen.add(key)
            price = float(r["price"])
            size = float(r["size"])
            ms = int(r["time"])
            side = r["side"]
            if side not in ("Buy", "Sell") or not (math.isfinite(price) and math.isfinite(size)):
                continue
            if price <= 0 or size <= 0 or ms > now_ms + 2000:
                continue
            clean.append((ms, side, price, size))
        except (KeyError, ValueError, TypeError, OverflowError):
            continue
    if not clean:
        raise ValueError("no valid public trades")
    clean.sort(key=lambda x: x[0])
    oldest, newest = clean[0][0], clean[-1][0]
    buy = sum(px * sz for _, side, px, sz in clean if side == "Buy")
    sell = sum(px * sz for _, side, px, sz in clean if side == "Sell")
    span = max(0, (newest - oldest) / 1000)
    age = (now_ms - newest) / 1000
    # Recent-trade APIs return bounded samples; in active markets this often
    # spans only seconds, so it must not be described as an hourly CVD.
    status = ("OK_SAMPLE" if len(clean) >= MIN_TRADES and
              age <= MAX_AGE_SECONDS and span <= MAX_SNAPSHOT_SPAN_SECONDS
              else "INSUFFICIENT_SAMPLE")
    return {"trade_count": len(clean), "first_trade_ms": oldest,
            "last_trade_ms": newest, "sample_span_s": round(span, 3),
            "buy_usdt": round(buy, 4), "sell_usdt": round(sell, 4),
            "signed_usdt": round(buy - sell, 4),
            "imbalance": round((buy - sell) / (buy + sell), 6) if buy + sell else 0,
            "last_trade_price": clean[-1][2], "status": status,
            "detail": f"last_trade_age_s={age:.1f}"}


def fetch_sample(asset: str, market: str, *, now_ms: int,
                 session: requests.Session | None = None) -> dict[str, Any]:
    sess = session or requests
    params = {"category": market, "symbol": asset + "USDT",
              "limit": 60 if market == "spot" else 1000}
    resp = sess.get(API, params=params, timeout=12)
    resp.raise_for_status()
    obj = resp.json()
    if str(obj.get("retCode")) != "0":
        raise RuntimeError("exchange API rejected request: " + str(obj.get("retCode")))
    rows = (obj.get("result") or {}).get("list") or []
    return parse_recent_trades(rows, now_ms=now_ms)


def read_rows() -> list[dict[str, str]]:
    if not LEDGER.exists():
        return []
    with LEDGER.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_rows(rows: list[dict[str, Any]]) -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    tmp = LEDGER.with_suffix(".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows[-MAX_LINES:])
    os.replace(tmp, LEDGER)


def _ref_price(payload: dict[str, Any], asset: str) -> float | None:
    v = (payload.get("asset_verdicts") or {}).get(asset) or {}
    p = (v.get("day_range") or {}).get("price")
    try:
        x = float(p)
        return x if math.isfinite(x) and x > 0 else None
    except (TypeError, ValueError):
        return None


def collect(payload: dict[str, Any] | None = None, *, now: datetime | None = None,
            session: requests.Session | None = None) -> dict[str, Any]:
    """Collect one bounded public snapshot for each market. Never create experiment implicitly."""
    now = now or utcnow()
    m = read_manifest()
    if not m:
        return {"status": "NOT_STARTED", "message": "Run 30-day workflow start first"}
    start_at = datetime.fromisoformat(m["start_utc"])
    end_at = datetime.fromisoformat(m["end_utc"])
    if now < start_at or now >= end_at:
        m["status"] = "COMPLETE" if now >= end_at else "NOT_STARTED"
        MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report(m)
        return {"status": m["status"], "experiment_id": m["experiment_id"]}
    rows = read_rows()
    bucket = now.replace(minute=0, second=0, microsecond=0).isoformat()
    existing = {(r["ts"], r["asset"], r["market"]) for r in rows}
    new = 0
    failed = 0
    now_ms = int(now.timestamp() * 1000)
    for asset in ASSETS:
        for market in MARKETS:
            if (bucket, asset, market) in existing:
                continue
            item = dict.fromkeys(FIELDS, "")
            item.update(ts=bucket, experiment_id=m["experiment_id"], asset=asset,
                        market=market, source="bybit_public_recent_trade",
                        reference_price=_ref_price(payload or {}, asset) or "",
                        observed_at_ms=now_ms)
            try:
                item.update(fetch_sample(asset, market, now_ms=now_ms, session=session))
                from research_30d_enrichment import snapshot
                item.update(snapshot(asset, market, session=session))
            except (requests.RequestException, ValueError, RuntimeError, KeyError) as e:
                item.update(status="ERROR", detail=str(e)[:180])
                failed += 1
            rows.append(item)
            new += 1
    if new:
        write_rows(rows)
    report(m, rows)
    return {"status": "COLLECTING", "experiment_id": m["experiment_id"],
            "new_snapshots": new, "errors": failed,
            "elapsed_days": round((now - start_at).total_seconds() / 86400, 2),
            "deadline": m["end_utc"], "policy": "advisory_only"}


def report(m: dict[str, Any] | None = None,
           rows: list[dict[str, Any]] | None = None) -> str:
    m = m or read_manifest()
    if not m:
        return "Experiment has not been started."
    rows = rows if rows is not None else read_rows()
    status = {}
    for asset in ASSETS:
        for market in MARKETS:
            rr = [r for r in rows if r["asset"] == asset and r["market"] == market]
            valid = [r for r in rr if r["status"] == "OK_SAMPLE"]
            status[(asset, market)] = (len(rr), len(valid))
    lines = ["# 30-day evidence observation report", "",
             f"- Experiment: `{m['experiment_id']}`",
             f"- Window (UTC): {m['start_utc']} to {m['end_utc']}",
             f"- Status: {m['status']}",
             "- Scope: observational only; production decisions unchanged",
             "- Important: Bybit recent-trade samples are not continuous CVD, DOM, or a full footprint",
             "- Orderbook data are isolated snapshots, not observed executions or proof of absorption",
             "- OI and funding are historical published readings; do not assume same timestamp as trades",
             "- No demonstrated forecast edge or profitability can be inferred from sample imbalance", "",
             "| Asset | Market | Samples | Fresh valid samples |",
             "|---|---|---:|---:|"]
    for (asset, market), (total, good) in status.items():
        lines.append(f"| {asset} | {market} | {total} | {good} |")
    try:
        from research_30d_monitor import audit, as_markdown as monitor_md
        lines += [""] + monitor_md(audit(m))
    except Exception as exc:
        lines += ["", "Six-asset audit unavailable: " + str(exc)]
    try:
        from research_30d_eval import evaluate, as_markdown
        lines += [""] + as_markdown(evaluate(rows))
    except Exception as exc:
        lines += ["", "Evaluation unavailable: " + str(exc)]
    lines += ["", "## Promotion criteria (not automatically executed)",
              "1. Continuous trade capture with proven gap coverage, or discard a CVD hypothesis.",
              "2. Point-in-time independent labels, non-overlapping windows and no lookahead.",
              "3. Walk-forward split plus baseline, costs, slippage, and multiple-test adjustment.",
              "4. At least 30 calendar days AND sufficient independent observations; extend otherwise.",
              "5. Manual review before any direction, risk, or stop rule changes.", ""]
    ROOT.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("start", "collect", "report", "check"))
    parser.add_argument("--experiment-id", default="")
    args = parser.parse_args()
    if args.command == "start":
        print(json.dumps(start(experiment_id=args.experiment_id), ensure_ascii=False, indent=2))
    elif args.command == "collect":
        print(json.dumps(collect(), ensure_ascii=False, indent=2))
    elif args.command == "report":
        print(report())
    else:
        m = read_manifest()
        print(json.dumps({"manifest": m, "observations": len(read_rows())},
                         ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
