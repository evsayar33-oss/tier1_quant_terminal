"""Shared, exact prospective market-data labels. Never fill a missing timestamp.

Endpoint returns are non-executable price proxies. Four-hour and barrier
paths require contiguous hourly bars; multi-day endpoint returns may span
session closures but never substitute an earlier/later endpoint.
"""
from __future__ import annotations

import math
import numpy as np
import pandas as pd

SCHEMA = "NEXT_HOUR_OPEN_TO_OPEN_V2"


def utc(value):
    t = pd.Timestamp(value)
    if pd.isna(t) or t.tzinfo is None:
        raise ValueError("Timezone-aware timestamp required")
    return t.tz_convert("UTC")


def window(observed, hours):
    start = utc(observed).floor("h") + pd.Timedelta(hours=1)
    return start, start + pd.Timedelta(hours=hours)


def bars(frame, columns):
    if not isinstance(frame, pd.DataFrame) or frame.empty or not set(columns).issubset(frame.columns):
        return pd.DataFrame(columns=columns, index=pd.DatetimeIndex([], tz="UTC"))
    x = frame[list(columns)].copy()
    x.index = pd.to_datetime(x.index, utc=True, errors="coerce")
    x = x[~x.index.isna() & ~x.index.duplicated(keep=False)].sort_index()
    x = x.apply(pd.to_numeric, errors="coerce")
    return x.where(np.isfinite(x) & (x > 0))


def exact_return(frame, start, end, *, contiguous=False):
    x = bars(frame, ["Open"])
    required = pd.date_range(start, end, freq="h") if contiguous else [start, end]
    vals = x["Open"].reindex(required).to_numpy(dtype=float)
    if not np.isfinite(vals).all():
        return None
    return float(vals[0]), float(vals[-1]), math.log(float(vals[-1]) / float(vals[0]))


def grade_endpoint(frame, observed, hours, now, *, contiguous=False, grace=96):
    start, end = window(observed, hours)
    now = utc(now)
    if now < end + pd.Timedelta(hours=1):
        return {"status": "PENDING"}
    value = exact_return(frame, start, end, contiguous=contiguous)
    if value is None:
        return {"status": "MISSING_EXACT_WINDOW" if now > end + pd.Timedelta(hours=grace) else "PENDING"}
    p0, p1, ret = value
    return {"status": "EXACT", "start": start.isoformat(), "end": end.isoformat(),
            "start_price": p0, "end_price": p1, "log_return": ret,
            "graded_at": now.isoformat()}


def fresh_frame(frame, observed):
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return False
    if frame.attrs.get("is_synthetic") or frame.attrs.get("status") in ("STALE", "MISSING", "PROXY"):
        return False
    x = bars(frame, ["Close"])
    expected = utc(observed).floor("h") - pd.Timedelta(hours=1)
    return expected in x.index and pd.notna(x.loc[expected, "Close"])


def barrier_path(frame, observed, hours, now, side, stop, target=None, *, asset=None):
    """OHLC bracket diagnostic with chronological completed bars.

    No inferred fills at missing bars; gaps THROUGH a bracket on later valid
    bars are priced at their opens. Same bar stop/target is stop-first.
    An opening outside the original proposed bracket is not a valid entry.
    """
    start, end = window(observed, hours)
    now = utc(now)
    if now < start + pd.Timedelta(hours=1):
        return {"status": "PENDING"}
    x = bars(frame, ["Open", "High", "Low", "Close"])
    expiry = now > end + pd.Timedelta(hours=96)
    missing = {"status": "MISSING_CONTIGUOUS_PATH" if expiry else "PENDING"}
    if start not in x.index or pd.isna(x.loc[start, "Open"]):
        return missing
    entry = float(x.loc[start, "Open"])
    if side not in (-1, 1) or not np.isfinite(stop) or (target is not None and not np.isfinite(target)):
        return {"status": "INVALID_BRACKET"}
    risk = side * (entry - stop)
    if risk <= 0 or (target is not None and side * (target - entry) <= 0):
        return {"status": "OPEN_OUTSIDE_BRACKET"}
    hit_stop = False
    first_hit = None
    skipped_closed = 0
    for t in pd.date_range(start, end - pd.Timedelta(hours=1), freq="h"):
        if now < t + pd.Timedelta(hours=1):
            return {"status": "PENDING"}
        if t not in x.index:
            # Explicit routine closures from the repository's existing session
            # calendar are not feed outages. No inferred holiday or exceptional
            # early closure and no fake bars; the next actual open carries gaps.
            if hours > 4 and asset in ("SPX", "NQ", "XAU", "XAG"):
                from market_structure import session_phase
                if session_phase(t + pd.Timedelta(minutes=30), asset)["phase"] == "Kapalı":
                    skipped_closed += 1
                    continue
            return missing
        if x.loc[t].isna().any():
            return missing
        b = x.loc[t]
        if b.High < max(b.Open, b.Close) or b.Low > min(b.Open, b.Close) or b.High < b.Low:
            return missing
        stopped = b.Low <= stop if side == 1 else b.High >= stop
        reached = target is not None and (b.High >= target if side == 1 else b.Low <= target)
        hit_stop = hit_stop or stopped
        if target is not None:
            # An opening through a barrier is known to precede intrabar highs/lows.
            if side * (b.Open - stop) <= 0:
                first_hit = ("stop", float(b.Open), t)
            elif side * (b.Open - target) >= 0:
                first_hit = ("hedef", float(b.Open), t)
            elif stopped:
                first_hit = ("stop", stop, t)
            elif reached:
                first_hit = ("hedef", target, t)
            if first_hit:
                break
    if first_hit is None:
        if now < end + pd.Timedelta(hours=1):
            return {"status": "PENDING"}
        if end not in x.index or pd.isna(x.loc[end, "Open"]):
            return missing
        first_hit = ("süre doldu", float(x.loc[end, "Open"]), end)
    outcome, exit_price, exit_ts = first_hit
    return {"status": "EXACT_PATH", "entry_proxy": entry, "exit_proxy": exit_price,
            "exit_ts": exit_ts.isoformat(), "outcome": outcome, "r": side * (exit_price - entry) / risk,
            "stop_hit": hit_stop, "direction_return": side * (exit_price / entry - 1),
            "skipped_regular_closure_hours": skipped_closed}
