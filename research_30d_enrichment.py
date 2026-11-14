"""Auxiliary, time-stamped Bybit order book / open interest / funding snapshots.

They are contemporaneous observations, not inferred liquidations or proof of
market-maker position. Each source can fail independently.
"""
from __future__ import annotations
import math
from typing import Any
import requests

ROOT = "https://api.bybit.com"


def _get(session, path: str, params: dict[str, Any]) -> dict:
    r = (session or requests).get(ROOT + path, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    if str(data.get("retCode")) != "0":
        raise ValueError("Bybit API retCode=" + str(data.get("retCode")))
    return data.get("result") or {}


def _valid_float(v: Any) -> float:
    x = float(v)
    if not math.isfinite(x) or x < 0:
        raise ValueError("invalid magnitude")
    return x


def book(asset: str, market: str, *, session=None) -> dict[str, Any]:
    data = _get(session, "/v5/market/orderbook",
                {"category": market, "symbol": asset + "USDT", "limit": 50})
    bids = [(float(x[0]), _valid_float(x[1])) for x in data.get("b", [])]
    asks = [(float(x[0]), _valid_float(x[1])) for x in data.get("a", [])]
    if not bids or not asks:
        raise ValueError("empty orderbook")
    bid, ask = bids[0][0], asks[0][0]
    if bid <= 0 or ask <= bid:
        raise ValueError("crossed / zero-spread book")
    b = sum(p * q for p, q in bids)
    a = sum(p * q for p, q in asks)
    if b + a <= 0:
        raise ValueError("empty notional")
    return {"book_imbalance": round((b - a) / (a + b), 6),
            "spread_bps": round(20000 * (ask - bid) / (ask + bid), 4),
            "book_ts": str(data.get("ts") or ""),
            "book_qty_unit": "bybit_venue_native"}


def open_interest(asset: str, *, session=None) -> dict[str, Any]:
    data = _get(session, "/v5/market/open-interest",
                {"category": "linear", "symbol": asset + "USDT",
                 "intervalTime": "5min", "limit": 2})
    rows = data.get("list") or []
    if not rows:
        raise ValueError("missing open interest")
    newest = max(rows, key=lambda x: int(x.get("timestamp") or 0))
    return {"oi_contracts": _valid_float(newest["openInterest"]),
            "oi_ts": str(newest["timestamp"]), "oi_unit": "bybit_venue_native"}


def funding(asset: str, *, session=None) -> dict[str, Any]:
    data = _get(session, "/v5/market/funding/history",
                {"category": "linear", "symbol": asset + "USDT", "limit": 1})
    rows = data.get("list") or []
    if not rows:
        raise ValueError("missing funding")
    x = float(rows[0]["fundingRate"])
    if not math.isfinite(x):
        raise ValueError("invalid funding")
    return {"funding_rate": x,
            "funding_ts": str(rows[0]["fundingRateTimestamp"]),
            "funding_kind": "historical_settled"}


def snapshot(asset: str, market: str, *, session=None,
             venue: str = "bybit") -> dict[str, Any]:
    """Never mix an OKX trade sample with Bybit order book or vice versa."""
    if venue == "okx":
        from research_30d_okx import snapshot as okx_snapshot
        return okx_snapshot(asset, market, session=session)
    if venue != "bybit":
        raise ValueError("unsupported snapshot venue")
    out: dict[str, Any] = {"enrichment_source": "bybit"}
    errors = []
    calls = [(book, (asset, market))]
    if market == "linear":
        calls += [(open_interest, (asset,)), (funding, (asset,))]
    for fn, args in calls:
        try:
            out.update(fn(*args, session=session))
        except (requests.RequestException, KeyError, ValueError, TypeError) as e:
            errors.append(fn.__name__ + ":" + str(e)[:60])
    out["enrichment_status"] = "OK" if not errors else "PARTIAL: " + "; ".join(errors)
    return out
