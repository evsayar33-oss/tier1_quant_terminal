"""Tier-1 prospective six-asset sentiment / market-state observation.

Research-only. No signal/stop/weight mutation. Every row is first-seen
after its source bar was available, and missing data are explicit.
"""
from __future__ import annotations
import csv
import json
import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

ROOT = Path("sentiment_30d")
MANIFEST = ROOT / "manifest.json"
ROWS = ROOT / "observations.csv"
FNG_CACHE = ROOT / "crypto_fng_cache.json"
ASSETS = ("SPX", "NQ", "XAU", "XAG", "BTC", "ETH")
IV_MAP = {"SPX": "VIX", "NQ": "VXN", "XAU": "GVZ", "XAG": "VXSLV"}
FIELDS = ("observed_utc", "experiment_id", "asset", "logic_version", "price",
          "price_bar_utc", "price_source", "price_status", "iv_index",
          "iv_value", "iv_bar_utc", "iv_percentile", "iv_status",
          "sentiment_value", "sentiment_source", "sentiment_published_utc",
          "sentiment_first_seen_utc", "sentiment_status", "fear_greed_effective_day",
          "risk_regime", "shock_active", "entry_allowed",
          "model_direction", "data_status",
          "factor_values_json", "gamma_values_json", "market_levels_json",
          "aux_diagnostics_json")


def timestamp(t):
    return t.astimezone(timezone.utc).isoformat(timespec="seconds")


def aware(t):
    x = pd.Timestamp(t)
    if x.tzinfo is None:
        raise ValueError("no source timezone")
    return x.tz_convert("UTC").to_pydatetime()


def fnum(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (ValueError, TypeError, OverflowError):
        return None


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).exists() else None


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def initialize(now):
    old = read_json(MANIFEST)
    if old is not None:
        if old.get("schema") != 1 or old.get("experiment_id") is None:
            raise ValueError("unrecognized sentiment observation manifest")
        return old
    exp = "tier1-sentiment-" + now.strftime("%Y%m%dT%H%M%SZ")
    manifest = {
        "schema": 1, "experiment_id": exp, "start_utc": timestamp(now),
        "end_utc": timestamp(now + timedelta(days=30)), "label_grace_hours": 48,
        "assets": list(ASSETS), "production_policy": "READ_ONLY",
        "evaluation": "PRE_REGISTERED_GRID_NOT_LIVE_TRADING",
        "feature_semantics": {
            "BTC": "Bitcoin-weighted Alternative.me Crypto Fear & Greed DAILY",
            "ETH": "Bitcoin-weighted broader crypto sentiment context; NOT ETH-specific",
            "SPX": "VIX implied volatility stress percentile, NOT CNN Fear and Greed",
            "NQ": "VXN implied volatility stress percentile, NOT CNN Fear and Greed",
            "XAU": "GVZ gold ETF implied volatility stress percentile, NOT gold Fear and Greed",
            "XAG": "VXSLV silver ETF implied volatility stress percentile, NOT silver Fear and Greed",
        },
        "label_policy": "prices in post-window 48h are outcome-only; no fabricated backfill",
    }
    atomic_json(MANIFEST, manifest)
    return manifest


def close_snapshot(frame, now, *, max_age_h=2.5):
    if not isinstance(frame, pd.DataFrame) or frame.empty or "Close" not in frame:
        return {"price": None, "bar": None, "status": "UNAVAILABLE"}
    values = pd.to_numeric(frame["Close"], errors="coerce").dropna()
    values = values[values > 0]
    if values.empty:
        return {"price": None, "bar": None, "status": "INVALID"}
    try:
        t = aware(values.index[-1])
    except (TypeError, ValueError):
        return {"price": None, "bar": None, "status": "BAR_TIME_UNVERIFIED"}
    age = (now - t).total_seconds() / 3600
    # Hourly bar indexes usually represent bar OPEN, not close. Reject a
    # potentially unfinished hour rather than inadvertently using its close.
    if age < 0.98 or age > max_age_h:
        return {"price": None, "bar": timestamp(t), "status": "UNCONFIRMED_OR_STALE_BAR"}
    return {"price": float(values.iloc[-1]), "bar": timestamp(t), "status": "OK"}


def iv_snapshot(frame, now):
    if not isinstance(frame, pd.DataFrame) or frame.empty or "Close" not in frame:
        return {"status": "UNAVAILABLE"}
    clean = pd.to_numeric(frame["Close"], errors="coerce").dropna()
    clean = clean[(clean > 0) & (clean < 1000)].sort_index()
    if len(clean) < 20:
        return {"status": "INSUFFICIENT_HISTORY"}
    last = close_snapshot(clean.to_frame(name="Close"), now, max_age_h=72)
    if last["status"] != "OK":
        return {"status": last["status"], "bar": last["bar"]}
    # Historical IV rank is descriptive; not normalized fear/greed.
    # Use distinct daily observations when available, not 40 near-duplicate hourly bars.
    hist = clean.iloc[:-1].tail(252)
    hist = hist[~hist.index.duplicated(keep="last")]
    if len(hist) < 20:
        return {"status": "INSUFFICIENT_HISTORY"}
    return {"status": "OK", "bar": last["bar"],
            "value": last["price"],
            "pct": round(float((hist <= last["price"]).mean() * 100), 2)}


def fetch_crypto_fng(now, session=None):
    """First-seen daily BTC-weighted crypto sentiment; never pretend ETH-specific."""
    old = read_json(FNG_CACHE)
    if old:
        try:
            last_seen = datetime.fromisoformat(old["first_seen_utc"])
            if now - last_seen < timedelta(hours=18) and last_seen <= now:
                return old
        except (TypeError, ValueError, KeyError):
            pass
    try:
        get = (session or requests).get
        response = get("https://api.alternative.me/fng/",
                       params={"limit": 1, "format": "json"}, timeout=10)
        response.raise_for_status()
        item = response.json()["data"][0]
        value = fnum(item.get("value"))
        src_at = datetime.fromtimestamp(int(item["timestamp"]), tz=timezone.utc)
        if value is None or not (0 <= value <= 100) or src_at > now + timedelta(minutes=5):
            raise ValueError("invalid or future FNG reading")
        record = {"value": value, "published_utc": timestamp(src_at),
                  "first_seen_utc": timestamp(now), "source": "alternative.me",
                  "status": "OK"}
        atomic_json(FNG_CACHE, record)
        return record
    except (ValueError, TypeError, KeyError, IndexError, requests.RequestException) as exc:
        # Preserve earlier reading but never mark an old value fresh.
        if old:
            old = dict(old)
            old["status"] = "STALE_OR_FETCH_FAILED"
            return old
        return {"status": "UNAVAILABLE", "error": str(exc)[:160]}


def _value(v):
    return "" if v is None else v


def compact_observed_features(asset, view, payload, now):
    """Compact actual same-cycle factor inputs; retain no invented unavailable data.

    These values are DATA for later hypotheses, never live decision changes.
    Gamma is a modeled proxy with its own as-of stamp, not a verified dealer fill.
    """
    raw = {}
    for item in (view.get("details") or [])[:100]:
        if not isinstance(item, dict):
            continue
        fid = str(item.get("faktor_id") or "").strip()
        number = fnum(item.get("ham_deger"))
        if fid and len(fid) <= 65 and number is not None and fid not in raw:
            raw[fid] = number
    gamma = {}
    snapshot = ((payload.get("dealer_gamma") or {}).get("snapshots") or {}).get(asset) or {}
    try:
        as_of = datetime.fromisoformat(snapshot["as_of"])
        if as_of.tzinfo and as_of <= now + timedelta(minutes=5):
            for key in ("gamma_flip", "call_wall", "put_wall", "pin_strike",
                        "net_gex_usd_1pct", "share_0dte", "atm_iv",
                        "expected_move_1d", "vanna_flow_iv_down_1pt_usd",
                        "charm_flow_1d_usd"):
                val = fnum(snapshot.get(key))
                if val is not None:
                    gamma[key] = val
            gamma["as_of"] = timestamp(as_of)
            gamma["source_type"] = "MODELED_DEALER_PROXY_NOT_EXECUTABLE"
    except (TypeError, KeyError, ValueError):
        pass
    levels = []
    struct = (view.get("market_structure") or {}).get("levels") or {}
    for x in (struct.get("levels") or [])[:30]:
        if not isinstance(x, dict):
            continue
        px = fnum(x.get("price"))
        if px is not None and px > 0:
            levels.append({"kind": str(x.get("kind") or "")[:24], "price": px})
    extras = {}
    for key in ("score", "raw_model_score", "adaptive_score", "live_score",
                "direction_score_z", "adx_val", "rvol", "atr_ratio"):
        val = fnum(view.get(key))
        if val is not None:
            extras[key] = val
    for key in ("vol_ratio", "pair_residual_z"):
        src = (view.get("vol_state") or {}).get("ratio") if key == "vol_ratio" else (view.get("pair_stats") or {}).get("residual_z")
        val = fnum(src)
        if val is not None:
            extras[key] = val
    return tuple(json.dumps(x, separators=(",", ":"), sort_keys=True)
                 for x in (raw, gamma, levels, extras))


def collect(payload, frames, grid, *, now=None, session=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("timezone-aware now required")
    manifest = initialize(now)
    start = datetime.fromisoformat(manifest["start_utc"])
    end = datetime.fromisoformat(manifest["end_utc"])
    grace_end = end + timedelta(hours=int(manifest["label_grace_hours"]))
    if now < start or now >= grace_end:
        return {"status": "COMPLETE" if now >= grace_end else "NOT_STARTED",
                "experiment_id": manifest["experiment_id"], "end_utc": manifest["end_utc"]}
    observed = timestamp(now)  # actual first-seen, never backdate to the hour
    bucket = observed[:13]
    ROOT.mkdir(exist_ok=True)
    prior = []
    if ROWS.exists():
        with ROWS.open(newline="", encoding="utf-8") as f:
            prior = list(csv.DictReader(f))
    existing = {(x["observed_utc"][:13], x["asset"]) for x in prior}
    signal_window = now < end
    crypto = fetch_crypto_fng(now, session=session) if signal_window else None
    new = []
    for asset in ASSETS:
        if (bucket, asset) in existing:
            continue
        snap = close_snapshot(frames.get(asset), now)
        iv_id = IV_MAP.get(asset)
        iv = iv_snapshot(grid.get(iv_id), now) if iv_id and signal_window else {"status": "NOT_APPLICABLE"}
        view = (payload.get("asset_verdicts") or {}).get(asset) or {}
        if signal_window:
            if asset in ("BTC", "ETH"):
                fng = crypto or {}
                age = None
                if fng.get("published_utc"):
                    age = (now - datetime.fromisoformat(fng["published_utc"])).total_seconds() / 3600
                sentiment_ok = fng.get("status") == "OK" and age is not None and 0 <= age <= 48
                sent_status = "OK" if sentiment_ok else "STALE_OR_UNAVAILABLE"
                sent_val = fng.get("value") if sentiment_ok else None
                sent_day = fng.get("published_utc", "")[:10] if sentiment_ok else ""
                source = "ALTME_BTC_CONTEXT" if asset == "ETH" else "ALTME_BTC"
            else:
                sent_status = "PROXY_ONLY" if iv.get("status") == "OK" else "UNAVAILABLE"
                sent_val = None
                sent_day = ""
                source = "NONE_NOT_REAL_FNG"
        else:
            sent_status, sent_val, sent_day, source = "POST_WINDOW_LABEL_ONLY", None, "", "NONE"
        factor_json, gamma_json, levels_json, diagnostics_json = (
            compact_observed_features(asset, view, payload, now)
            if signal_window else ("{}", "{}", "[]", "{}"))
        new.append({
            "factor_values_json": factor_json, "gamma_values_json": gamma_json,
            "market_levels_json": levels_json, "aux_diagnostics_json": diagnostics_json,
            "observed_utc": observed, "experiment_id": manifest["experiment_id"],
            "asset": asset, "logic_version": str(payload.get("logic_version") or ""),
            "price": _value(snap.get("price")), "price_bar_utc": _value(snap.get("bar")),
            "price_source": "tier1_observed_1h_close", "price_status": snap["status"],
            "iv_index": iv_id or "", "iv_value": _value(iv.get("value")),
            "iv_bar_utc": _value(iv.get("bar")), "iv_percentile": _value(iv.get("pct")),
            "iv_status": iv["status"], "sentiment_value": _value(sent_val),
            "sentiment_source": source,
            "sentiment_published_utc": (crypto or {}).get("published_utc", "") if signal_window and asset in ("BTC", "ETH") else "",
            "sentiment_first_seen_utc": (crypto or {}).get("first_seen_utc", "") if signal_window and asset in ("BTC", "ETH") else "",
            "sentiment_status": sent_status, "fear_greed_effective_day": sent_day,
            "risk_regime": str(payload.get("active_regime_id") or "") if signal_window else "",
            "shock_active": str(bool((payload.get("shock") or {}).get("active"))) if signal_window else "",
            "entry_allowed": str(view.get("entry_allowed")) if signal_window else "",
            "model_direction": str(view.get("verdict") or "") if signal_window else "",
            "data_status": "OBSERVED" if signal_window else "LABEL_ONLY",
        })
    if new:
        temp = ROWS.with_suffix(".tmp")
        with temp.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(FIELDS))
            writer.writeheader()
            writer.writerows(prior + new)
        os.replace(temp, ROWS)
    return {"status": "COLLECTING" if signal_window else "LABEL_GRACE",
            "experiment_id": manifest["experiment_id"], "end_utc": manifest["end_utc"],
            "added": len(new), "fresh_prices": sum(x["price_status"] == "OK" for x in new),
            "sentiment_ok": sum(x["sentiment_status"] in ("OK", "PROXY_ONLY") for x in new),
            "production_policy": "READ_ONLY"}
