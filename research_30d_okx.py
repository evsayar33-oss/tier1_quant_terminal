"""OKX public REST fallback for bounded research snapshots (not continuous CVD).

SPOT sizes are base units. USDT linear SWAP sizes are *contracts*, and only
a verified public ctVal/ctValCcy instrument response can convert them to base.
Never interpret a contract count directly as BTC/ETH notional.
"""
from __future__ import annotations
import math
from typing import Any
import requests

ROOT = "https://www.okx.com"


def _get(path: str, params: dict[str, Any], *, session=None) -> list[dict]:
    resp = (session or requests).get(ROOT + path, params=params, timeout=12)
    resp.raise_for_status()
    obj = resp.json()
    if str(obj.get("code")) != "0":
        raise ValueError("OKX code=" + str(obj.get("code")))
    rows = obj.get("data")
    if not isinstance(rows, list) or not rows:
        raise ValueError("OKX missing response data: " + path)
    return rows


def instrument(asset: str, *, session=None) -> dict[str, Any]:
    inst_id = asset + "-USDT-SWAP"
    rows = _get("/api/v5/public/instruments",
                {"instType": "SWAP", "instId": inst_id}, session=session)
    row = next((r for r in rows if r.get("instId") == inst_id), None)
    if not row:
        raise ValueError("OKX swap instrument not found")
    if row.get("ctValCcy") != asset:
        raise ValueError("unsupported OKX contract value currency")
    multiplier = float(row["ctVal"])
    if not math.isfinite(multiplier) or multiplier <= 0:
        raise ValueError("invalid OKX ctVal")
    return {"inst_id": inst_id, "base_per_contract": multiplier,
            "contract_value_currency": row["ctValCcy"]}


def get_trades(asset: str, market: str, *, session=None) -> tuple[list[dict], dict]:
    inst_id = asset + ("-USDT" if market == "spot" else "-USDT-SWAP")
    mult = 1.0
    if market == "linear":
        mult = instrument(asset, session=session)["base_per_contract"]
    elif market != "spot":
        raise ValueError("unsupported market")
    records = _get("/api/v5/market/trades",
                   {"instId": inst_id, "limit": "500"}, session=session)
    converted = []
    for item in records:
        if item.get("instId") != inst_id:
            continue
        side = {"buy": "Buy", "sell": "Sell"}.get(item.get("side"))
        if not side:
            continue
        # Reuse Bybit's strict range, dedup and future timestamp validation.
        converted.append({"execId": str(item["tradeId"]), "time": item["ts"],
                          "price": item["px"],
                          "size": str(float(item["sz"]) * mult),
                          "side": side})
    return converted, {"venue": "okx", "instrument_id": inst_id,
                       "sample_qty_unit": "base_" + asset,
                       "contract_value_base": mult if market == "linear" else ""}


def orderbook(asset: str, market: str, *, session=None) -> dict[str, Any]:
    inst_id = asset + ("-USDT" if market == "spot" else "-USDT-SWAP")
    mult = instrument(asset, session=session)["base_per_contract"] if market == "linear" else 1.0
    row = _get("/api/v5/market/books",
               {"instId": inst_id, "sz": "50"}, session=session)[0]
    bids = [(float(p), float(q) * mult) for p, q, *_ in row.get("bids", [])]
    asks = [(float(p), float(q) * mult) for p, q, *_ in row.get("asks", [])]
    if not bids or not asks:
        raise ValueError("empty OKX order book")
    bid = max(p for p, _ in bids)
    ask = min(p for p, _ in asks)
    if bid <= 0 or ask <= bid:
        raise ValueError("crossed OKX book")
    if any(p <= 0 or q < 0 or not math.isfinite(q) for p, q in bids + asks):
        raise ValueError("invalid OKX book data")
    b = sum(p * q for p, q in bids)
    a = sum(p * q for p, q in asks)
    if a + b <= 0:
        raise ValueError("zero OKX book notional")
    return {"book_imbalance": round((b - a) / (a + b), 6),
            "spread_bps": round(20000 * (ask - bid) / (ask + bid), 4),
            "book_ts": str(row.get("ts") or ""),
            "book_qty_unit": "base_" + asset}


def open_interest(asset: str, *, session=None) -> dict[str, Any]:
    inst_id = asset + "-USDT-SWAP"
    row = _get("/api/v5/public/open-interest",
               {"instType": "SWAP", "instId": inst_id}, session=session)[0]
    if row.get("instId") != inst_id:
        raise ValueError("mismatched OKX open interest instrument")
    out = {"oi_ts": str(row["ts"]), "oi_unit": "contracts"}
    for src, dst in (("oi", "oi_contracts"), ("oiCcy", "oi_base"), ("oiUsd", "oi_usdt")):
        if row.get(src) not in (None, ""):
            x = float(row[src])
            if not math.isfinite(x) or x < 0:
                raise ValueError("invalid OKX open interest")
            out[dst] = x
    if "oi_contracts" not in out:
        raise ValueError("missing OKX open interest")
    return out


def funding(asset: str, *, session=None) -> dict[str, Any]:
    inst_id = asset + "-USDT-SWAP"
    row = _get("/api/v5/public/funding-rate",
               {"instId": inst_id}, session=session)[0]
    if row.get("instId") != inst_id:
        raise ValueError("mismatched OKX funding instrument")
    value = float(row["fundingRate"])
    if not math.isfinite(value):
        raise ValueError("invalid OKX funding")
    return {"funding_rate": value, "funding_ts": str(row.get("fundingTime") or ""),
            "funding_kind": "current_or_predicted"}


def snapshot(asset: str, market: str, *, session=None) -> dict[str, Any]:
    calls = [(orderbook, (asset, market))]
    if market == "linear":
        calls.extend([(open_interest, (asset,)), (funding, (asset,))])
    result: dict[str, Any] = {"enrichment_source": "okx"}
    failures = []
    for fn, args in calls:
        try:
            result.update(fn(*args, session=session))
        except (ValueError, KeyError, TypeError, requests.RequestException) as exc:
            failures.append(fn.__name__ + ": " + str(exc)[:95])
    result["enrichment_status"] = "OK" if not failures else "PARTIAL: " + "; ".join(failures)
    return result
