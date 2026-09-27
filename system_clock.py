"""
System Clock — single source of "now" for the whole terminal
=============================================================
Every module that needs the current time asks this module instead of
calling ``datetime.now()`` directly.

Why: in production this is byte-for-byte the same as ``datetime.now(UTC)``.
But the historical replay / walk-forward validator (historical_replay.py)
must be able to run the REAL production pipeline at a past moment ``t``
without any component peeking at the real wall clock -- otherwise pending
predictions would be "settled" against the future, freshness checks would
mark every historical bar as STALE, and decay/half-life calculations would
be computed against 2026 instead of the replayed date. A frozen clock is
what makes the replay point-in-time (no look-ahead) by construction.

Usage:
    from system_clock import now_utc
    ts = now_utc()

Replay only:
    from system_clock import set_frozen_now, clear_frozen_now
    set_frozen_now(pd.Timestamp("2025-03-04 14:00", tz="UTC"))
    ...
    clear_frozen_now()
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Optional

_LOCK = threading.RLock()
_FROZEN: Optional[datetime] = None


def now_utc() -> datetime:
    """Timezone-aware current UTC time (or the frozen replay time)."""
    with _LOCK:
        if _FROZEN is not None:
            return _FROZEN
    return datetime.now(timezone.utc)


def now_iso() -> str:
    return now_utc().isoformat()


def now_timestamp() -> float:
    """Epoch seconds, consistent with now_utc()."""
    return now_utc().timestamp()


def set_frozen_now(moment) -> None:
    """Freeze the clock at ``moment`` (datetime or pandas Timestamp)."""
    global _FROZEN
    if moment is None:
        clear_frozen_now()
        return
    if hasattr(moment, "to_pydatetime"):
        moment = moment.to_pydatetime()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    with _LOCK:
        _FROZEN = moment.astimezone(timezone.utc)


def clear_frozen_now() -> None:
    global _FROZEN
    with _LOCK:
        _FROZEN = None


def is_frozen() -> bool:
    with _LOCK:
        return _FROZEN is not None
