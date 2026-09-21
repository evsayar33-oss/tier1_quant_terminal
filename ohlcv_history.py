"""
Tier-1 Quant Terminal - Persistent OHLCV History Store

Persists only REAL OHLCV bars returned by the direct market-data source.
It is intentionally independent from entry/signal logic.
"""
from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]
DEFAULT_MAX_BARS = 200
DEFAULT_HISTORY_DIR = "ohlcv_history"


def _history_dir() -> Path:
    raw = os.environ.get("OHLCV_HISTORY_DIR", DEFAULT_HISTORY_DIR).strip()
    path = Path(raw or DEFAULT_HISTORY_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_filename(symbol: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", str(symbol).strip())
    name = name.replace("=", "_")
    return (name or "UNKNOWN") + ".csv"


def history_path(symbol: str) -> Path:
    return _history_dir() / _safe_filename(symbol)


def _normalise_frame(frame: Any) -> pd.DataFrame:
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return pd.DataFrame(columns=REQUIRED_COLUMNS)

    x = frame.copy()
    if isinstance(x.columns, pd.MultiIndex):
        x.columns = [c[0] if isinstance(c, tuple) else c for c in x.columns]
    x = x.loc[:, ~x.columns.duplicated(keep="last")]

    for col in REQUIRED_COLUMNS:
        if col not in x.columns:
            if col == "Volume":
                x[col] = np.nan
            else:
                return pd.DataFrame(columns=REQUIRED_COLUMNS)

    x = x[REQUIRED_COLUMNS]
    for col in REQUIRED_COLUMNS:
        x[col] = pd.to_numeric(x[col], errors="coerce")

    # Never manufacture volume. Missing source volume stays NaN.
    x = x.replace([np.inf, -np.inf], np.nan)
    x = x.dropna(subset=["Open", "High", "Low", "Close"])

    idx = pd.to_datetime(x.index, errors="coerce", utc=True)
    x.index = idx
    x = x[~x.index.isna()]
    x = x[~x.index.duplicated(keep="last")].sort_index()
    return x


def load_history(symbol: str) -> pd.DataFrame:
    path = history_path(symbol)
    if not path.exists():
        return pd.DataFrame(columns=REQUIRED_COLUMNS)

    try:
        raw = pd.read_csv(path)
        if "timestamp" not in raw.columns:
            return pd.DataFrame(columns=REQUIRED_COLUMNS)
        raw["timestamp"] = pd.to_datetime(raw["timestamp"], errors="coerce", utc=True)
        raw = raw.dropna(subset=["timestamp"]).set_index("timestamp")
        return _normalise_frame(raw)
    except Exception:
        # History corruption must never crash the production data engine.
        return pd.DataFrame(columns=REQUIRED_COLUMNS)


def _atomic_write(symbol: str, frame: pd.DataFrame) -> None:
    path = history_path(symbol)
    payload = _normalise_frame(frame).reset_index(names="timestamp")
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            payload.to_csv(handle, index=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
        except OSError:
            pass


def merge_and_persist(symbol: str, live_frame: pd.DataFrame, max_bars: int = DEFAULT_MAX_BARS) -> pd.DataFrame:
    """Merge direct-source bars with persisted history; never synthesize rows."""
    incoming = _normalise_frame(live_frame)
    if incoming.empty:
        return load_history(symbol)

    prior = load_history(symbol)
    if prior.empty:
        merged = incoming.copy()
    else:
        merged = pd.concat([prior, incoming], axis=0, sort=False)
    merged = _normalise_frame(merged)
    merged = merged[~merged.index.duplicated(keep="last")].sort_index()
    merged = merged.tail(max(int(max_bars), 1))
    _atomic_write(symbol, merged)
    return merged.copy()


def persistent_history_summary(symbol: str, max_bars: int = DEFAULT_MAX_BARS) -> dict:
    frame = load_history(symbol).tail(max(int(max_bars), 1))
    if frame.empty:
        return {"symbol": symbol, "bars": 0, "first_bar": None, "last_bar": None}
    return {
        "symbol": symbol,
        "bars": int(len(frame)),
        "first_bar": frame.index[0].isoformat(),
        "last_bar": frame.index[-1].isoformat(),
    }
