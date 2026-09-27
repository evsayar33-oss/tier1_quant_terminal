"""
State Schema Guard — versioned, crash-safe persistence for learned state
=========================================================================
The terminal "learns" into several JSON files that live in the repository
and are committed back by the GitHub Actions job every cycle:

    adaptive_regime_thresholds_state.json   macro trigger calibration
    data_freshness_state.json               per-symbol LIVE/STALE cutoff
    timeframe_confluence_state.json         HTF/MTF/LTF reliability weights
    stateful_adaptive_memory.json           score/factor/direction memory
    performance_ledger.json                 out-of-sample forward scoreboard

Over years of unattended running, two things WILL eventually happen:

1. A code update changes the structure of one of these files.
2. A file gets truncated/corrupted (interrupted commit, manual edit, merge).

Without a guard, (1) means the new code silently mis-reads old state
(wrong numbers flow into live decisions, no error is ever raised), and
(2) means the loader falls back to an empty default and the next save
OVERWRITES months of learned history with nothing.

This module gives every state file the same three guarantees:

* Every file carries an explicit ``schema_version``.
* A version the code does not understand is never interpreted. It is
  either migrated by a registered, explicit migration function, or it is
  moved aside into ``state_backups/`` and the store starts fresh.
* A corrupted file is never overwritten in place -- it is copied into
  ``state_backups/`` first, so nothing learned is ever destroyed silently.

Every backup/migration event is appended to ``state_backups/events.log`` so
it is visible later (the performance report surfaces it too).
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
from typing import Any, Callable, Dict, Optional, Tuple

from system_clock import now_utc

_LOCK = threading.RLock()
BACKUP_DIR = "state_backups"
EVENT_LOG = os.path.join(BACKUP_DIR, "events.log")

# (file_basename, from_version, to_version) -> migration(payload) -> payload
_MIGRATIONS: Dict[Tuple[str, str, str], Callable[[Dict[str, Any]], Dict[str, Any]]] = {}


def register_migration(basename: str, from_version: str, to_version: str):
    def deco(fn: Callable[[Dict[str, Any]], Dict[str, Any]]):
        _MIGRATIONS[(basename, str(from_version), str(to_version))] = fn
        return fn
    return deco


def _log_event(message: str) -> None:
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        with open(EVENT_LOG, "a", encoding="utf-8") as fh:
            fh.write(f"{now_utc().isoformat()} | {message}\n")
    except OSError:
        pass


def backup_file(path: str, reason: str) -> Optional[str]:
    """Copy ``path`` into state_backups/ with a timestamp + reason tag."""
    if not os.path.exists(path):
        return None
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        stamp = now_utc().strftime("%Y%m%dT%H%M%SZ")
        base = os.path.basename(path)
        safe_reason = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in reason)[:40]
        dest = os.path.join(BACKUP_DIR, f"{base}.{stamp}.{safe_reason}.bak")
        shutil.copy2(path, dest)
        _log_event(f"BACKUP {base} -> {dest} ({reason})")
        return dest
    except OSError:
        return None


def atomic_write_json(path: str, payload: Dict[str, Any], **dump_kwargs) -> None:
    d = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".state_", dir=d)
    kwargs = {"indent": 2, "sort_keys": True, "ensure_ascii": False, "default": str}
    kwargs.update(dump_kwargs)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, **kwargs)
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def _version_of(payload: Dict[str, Any]) -> Optional[str]:
    v = payload.get("schema_version", payload.get("version"))
    return None if v is None else str(v)


def load_versioned_json(
    path: str,
    expected_version: str,
    validator: Optional[Callable[[Dict[str, Any]], bool]] = None,
) -> Optional[Dict[str, Any]]:
    """Returns the payload (already migrated to ``expected_version``) or
    None when the store should start fresh. Never raises."""
    with _LOCK:
        if not os.path.exists(path):
            return None
        base = os.path.basename(path)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError, ValueError):
            backup_file(path, "corrupt")
            return None
        if not isinstance(payload, dict):
            backup_file(path, "not_a_dict")
            return None

        version = _version_of(payload)
        guard = 0
        while version != str(expected_version) and guard < 10:
            guard += 1
            step = next(
                ((k, fn) for k, fn in _MIGRATIONS.items() if k[0] == base and k[1] == version),
                None,
            )
            if step is None:
                backup_file(path, f"unknown_version_{version}")
                return None
            (_, _, to_version), fn = step
            try:
                payload = fn(dict(payload))
            except Exception as exc:  # migration bug must never crash the terminal
                backup_file(path, f"migration_failed_{version}")
                _log_event(f"MIGRATION_FAILED {base} {version}->{to_version}: {exc}")
                return None
            payload["schema_version"] = to_version
            _log_event(f"MIGRATED {base} {version} -> {to_version}")
            version = to_version

        if version != str(expected_version):
            backup_file(path, "version_loop")
            return None

        if validator is not None:
            try:
                ok = bool(validator(payload))
            except Exception:
                ok = False
            if not ok:
                backup_file(path, "failed_validation")
                return None
        return payload


def recent_events(max_lines: int = 20) -> list:
    try:
        with open(EVENT_LOG, "r", encoding="utf-8") as fh:
            lines = fh.read().strip().splitlines()
        return lines[-max_lines:]
    except OSError:
        return []
