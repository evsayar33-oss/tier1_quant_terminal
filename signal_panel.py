"""
System signal panel (v5.0)
==========================
Turns ONE production verdict (what the terminal shows for an asset at time t)
into a flat row of numbers, so that EVERY output of the system can be tested
by the Strategy Lab - alone and in combinations - and the live bot evaluates
the winning rule from exactly the same numbers.

Used in two places with the same function:
  * historical_replay.py  -> validation_reports/signal_panel.csv.gz
                             (point-in-time, 700 days, every replay step)
  * bot_loop.py           -> signal_history.csv (live, every hourly cycle)

Column families (prefix):
  sys::  scalar outputs of the verdict (scores, z's, velocities, rvol, atr,
         adx, entry flags, live score, pair scores, cluster counts ...)
  cat::  categorical outputs as codes (verdict, short-term tier, stage,
         entry grade, adx regime, live-vs-model, intraday trend/vol state)
  f::    every factor value, sign-aligned (same convention as factor_panel)
  mac::  market-wide state (regime id, USD risk, VIX, real-yield z, crisis ...)
"""
from __future__ import annotations

import math
import os
from typing import Any, Dict, Optional

# nested dicts whose numeric leaves are useful signals
_NESTED = {
    "timeframe_confluence": ("confluence_score", "all_aligned", "entry_confirmed", "weight_total"),
    "pair_stats": ("corr", "residual_z", "divergence_z_used", "spread"),
    "adaptive_cluster_scores": ("A", "B", "C", "D", "E"),
    "short_term_parts": ("model_z", "price_z", "model_part", "price_part", "price_share"),
    "intraday_regime": ("adx_val", "atr_ratio"),
    "pair_common_factor": ("rho", "common_score", "gap_before", "gap_after", "divergence_evidence"),
    "stateful_entry_profile": ("atr_rank", "rvol_rank"),
}
# scalar keys that are configuration/bookkeeping, not signals
_SKIP = {"score_smoothing_half_life_h", "factor_total_count", "factor_failure_count", "direction_runtime_n",
         "factor_data_coverage", "active_regime_id"}


def _num(x) -> Optional[float]:
    if isinstance(x, bool):
        return 1.0 if x else 0.0
    if isinstance(x, (int, float)):
        v = float(x)
        return v if math.isfinite(v) else None
    return None


def _dir_code(text: Any) -> float:
    """'GÜÇLÜ AL' -> +2, 'AL' -> +1, 'SAT' -> -1, '🔴🔴' -> -2, 'LONG' -> +1 ..."""
    t = str(text or "").upper()
    strong = 2.0 if ("GÜÇLÜ" in t or "🟢🟢" in t or "🔴🔴" in t or "STRONG" in t) else 1.0
    if "🟢" in t or "LONG" in t or "YUKARI" in t or "BULL" in t or \
            (" AL" in f" {t}" and "SAT" not in t and "KAPALI" not in t):
        return strong
    if "🔴" in t or "SHORT" in t or "AŞAĞI" in t or "BEAR" in t or "SAT" in t:
        return -strong
    return 0.0


_STAGE = {"NEUTRAL": 0.0, "HELD": 0.5, "EARLY": 1.0, "CONFIRMED": 2.0}
_GRADE = {"A": 3.0, "B": 2.0, "C": 1.0}
_LVM = {"ALIGNED": 1.0, "OPPOSED": -1.0}


def flatten(verdict: Dict[str, Any], macro: Optional[Dict[str, Any]] = None,
            factor_sign: Optional[Dict[str, tuple]] = None) -> Dict[str, float]:
    v = verdict or {}
    row: Dict[str, float] = {}
    for k, x in v.items():
        if k in _SKIP:
            continue
        n = _num(x)
        if n is not None:
            row[f"sys::{k}"] = n
    for k, leaves in _NESTED.items():
        d = v.get(k)
        if isinstance(d, dict):
            for leaf in leaves:
                n = _num(d.get(leaf))
                if n is not None:
                    row[f"sys::{k}.{leaf}"] = n
    # categorical -> codes
    row["cat::verdict"] = _dir_code(v.get("verdict"))
    row["cat::forecast"] = _dir_code(v.get("forecast_direction"))
    row["cat::short_term"] = _dir_code(v.get("current_direction") or v.get("current_icon"))
    row["cat::live_tier"] = _dir_code(v.get("live_tier"))
    d = str(v.get("direction") or "").upper()
    sgn = 1.0 if "LONG" in d else (-1.0 if "SHORT" in d else 0.0)
    row["cat::direction"] = sgn
    row["cat::stage"] = sgn * _STAGE.get(str(v.get("direction_stage") or "").upper(), 0.0)
    row["cat::entry_grade"] = _GRADE.get(str(v.get("entry_grade") or "").strip().upper()[:1], 0.0)
    row["cat::live_vs_model"] = _LVM.get(str(v.get("live_vs_model") or "").upper(), 0.0)
    row["cat::adx_trend"] = 0.0 if "YATAY" in str(v.get("adx_regime") or "").upper() else 1.0
    ir = v.get("intraday_regime") or {}
    row["cat::intraday_trend"] = _dir_code(ir.get("trend_state")) if isinstance(ir, dict) else 0.0
    vs = str((ir or {}).get("vol_state") or "").upper() if isinstance(ir, dict) else ""
    row["cat::intraday_vol"] = 1.0 if "YÜKSEK" in vs or "HIGH" in vs else (-1.0 if "DÜŞÜK" in vs or "LOW" in vs else 0.0)
    # factors (sign-aligned like factor_panel: value * base_sign, keyed by factor id)
    for r in v.get("details", []) or []:
        if not isinstance(r, dict):
            continue
        val = _num(r.get("ham_deger"))
        if val is None:
            continue
        name = str(r.get("faktör"))
        if factor_sign is not None:
            meta = factor_sign.get(name)
            if meta is None:
                continue
            fid, sgn = meta
            row[f"f::{fid}"] = val * sgn
        else:
            row[f"f::{r.get('id') or name}"] = val
    for k, x in (macro or {}).items():
        n = _num(x)
        if n is not None:
            row[f"mac::{k}"] = n
    reg = (macro or {}).get("regime_id", v.get("active_regime_id"))
    try:
        row["mac::regime_id"] = float(reg)
    except (TypeError, ValueError):
        row["mac::regime_id"] = 0.0          # REJIMSIZ_GECIS
    return row


def macro_of(gk) -> Dict[str, Any]:
    """Market-wide numbers from a gatekeeper object (replay) or a terminal state dict (live)."""
    keys = ("composite_usd_risk", "dxy_velocity", "ndl_z", "current_vix", "stagflation_z", "yen_carry_z",
            "dfii10_z", "anomaly_score", "real_yield_z", "breakeven_z", "credit_velocity")
    get = (lambda k: gk.get(k)) if isinstance(gk, dict) else (lambda k: getattr(gk, k, None))
    out = {k: get(k) for k in keys}
    crisis = gk.get("crisis_state", {}).get("is_active") if isinstance(gk, dict) else getattr(gk, "crisis_active", None)
    out["crisis_active"] = bool(crisis)
    out["regime_id"] = get("active_regime_id") if not isinstance(gk, dict) else gk.get("active_regime_id")
    return out


def factor_signs() -> Dict[str, tuple]:
    """factor name -> (id, base_sign), from config (same convention as the replay)."""
    from config import ASSET_MATRICES
    out: Dict[str, tuple] = {}
    for m in ASSET_MATRICES.values():
        for f in m.get("factors", []):
            out[str(f.get("name"))] = (str(f.get("id")), float(f.get("base_sign", 1.0)))
    return out


# ------------------------------------------------------------------ live history
HISTORY = "signal_history.csv"
MAX_HISTORY_ROWS = 6 * 24 * 30          # 30 days of hourly rows for 6 assets


def append_history(state: Dict[str, Any], t, root: str = ".") -> int:
    """Append this cycle's flattened verdicts (all assets) to signal_history.csv."""
    import pandas as pd
    fs = factor_signs()
    mac = macro_of(state)
    rows = []
    for a, v in (state.get("asset_verdicts") or {}).items():
        r = flatten(v, mac, fs)
        r.update({"asset": a, "t": pd.Timestamp(t).isoformat()})
        rows.append(r)
    if not rows:
        return 0
    path = os.path.join(root, HISTORY)
    new = pd.DataFrame(rows)
    try:
        old = pd.read_csv(path)
        df = pd.concat([old, new], ignore_index=True)
    except Exception:
        df = new
    df = df.drop_duplicates(["asset", "t"], keep="last").tail(MAX_HISTORY_ROWS)
    df.to_csv(path, index=False, float_format="%.6g")
    return len(new)
