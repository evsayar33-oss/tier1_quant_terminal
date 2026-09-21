"""
Stateful background runner for Tier-1 Quant Terminal.

This is a new runner; the original background_tracker.py remains untouched.
It writes the same terminal_state.json used by the Streamlit UI, while adding
stateful_adaptive diagnostics and the persistent model memory file.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict

import pandas as pd
import requests

from config import ASSET_MATRICES
from gatekeeper import PreTradeGatekeeper
from stateful_adaptive_controller import StatefulAdaptiveController


STATE_FILE = "terminal_state.json"
MEMORY_FILE = "stateful_adaptive_memory.json"
HISTORY_FILE = "terminal_history_stateful.csv"
VERSION = "3.0.0-stateful"


def _load_json(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_json(path: str, data: Dict[str, Any]) -> None:
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2, allow_nan=False, default=str)
    os.replace(tmp, path)


def _send_telegram(message: str) -> None:
    token = os.environ.get("TELEGRAM_TOKEN", "").strip()
    chat_id = os.environ.get("CHAT_ID", "").strip()
    if not token or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as exc:
        print(f"Telegram alert hatası: {exc}")


def run_background_cycle() -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    fred_api_key = os.environ.get("FRED_API_KEY", "").strip()
    previous_state = _load_json(STATE_FILE)
    previous_verdicts = previous_state.get("asset_verdicts", {})
    previous_map = {
        key: previous_verdicts.get(key, {}).get("verdict", "NÖTR (BEKLE)")
        for key in ASSET_MATRICES.keys()
    }

    prior_crisis = bool(previous_state.get("crisis_state", {}).get("is_active", False))
    prior_breaches = int(previous_state.get("crisis_state", {}).get("consecutive_breaches", 0))

    print(f"[{now}] 🔄 Stateful Adaptive background cycle başladı.")

    gk = PreTradeGatekeeper(fred_api_key=fred_api_key)
    gk.crisis_active = prior_crisis
    gk.consecutive_breaches = prior_breaches
    gk.refresh_market()

    controller = StatefulAdaptiveController(memory_file=MEMORY_FILE)
    regime_diag = controller.prepare_cycle(gk)

    # Original model computes all raw factor evidence. The stateful layer then
    # recalibrates scores/weights and replaces the final signal state.
    raw_verdicts = gk.evaluate_all_assets_harmonized(previous_map)
    verdicts, adaptive_diag = controller.finalize_cycle(
        gk,
        raw_verdicts,
        previous_signals=previous_map,
        cycle_id=now,
    )

    payload = {
        "v22_version": VERSION,
        "last_updated": now,
        "status": "OK",
        "active_regime_id": gk.active_macro_regime_id,
        "active_regime_name": gk.active_macro_regime_name,
        "market_regime": gk.market_regime,
        "active_subtype": gk.active_subtype,
        "dynamic_thresholds": gk.dynamic_thresholds,
        "macro_diagnostics": gk.macro_diagnostics,
        "stateful_adaptive": adaptive_diag,
        "composite_usd_risk": gk.composite_usd_risk,
        "usd_risk_label": gk.usd_risk_label,
        "usd_risk_status": gk.usd_risk_status,
        "dxy_velocity": gk.dxy_velocity,
        "ndl_z": gk.ndl_z,
        "current_vix": gk.current_vix,
        "stagflation_z": gk.stagflation_z,
        "yen_carry_z": gk.yen_carry_z,
        "dfii10_z": gk.dfii10_z,
        "curve_label": gk.curve_label,
        "crisis_state": {
            "is_active": gk.crisis_active,
            "consecutive_breaches": gk.consecutive_breaches,
            "anomaly_score": gk.anomaly_score,
            "vix_floor_active": bool(gk.current_vix is not None and gk.current_vix < 20.0),
        },
        "data_quality": gk.data_engine.data_quality,
        "data_sources": gk.data_engine.data_sources,
        "asset_verdicts": verdicts,
    }
    _save_json(STATE_FILE, payload)

    row = {
        "timestamp": now,
        "active_regime_id": gk.active_macro_regime_id,
        "market_regime": gk.market_regime,
        "pair_residual_z": adaptive_diag.get("pair_state", {}).get("residual_z"),
        "pair_beta_gold": adaptive_diag.get("pair_state", {}).get("beta_gold"),
        "pair_beta_copper": adaptive_diag.get("pair_state", {}).get("beta_copper"),
        "memory_pending": adaptive_diag.get("memory", {}).get("pending_observations"),
        "memory_settled": adaptive_diag.get("memory", {}).get("settled_observations"),
        "anomaly_score": gk.anomaly_score,
        "current_vix": gk.current_vix,
    }
    pd.DataFrame([row]).to_csv(
        HISTORY_FILE,
        mode="a",
        header=not os.path.exists(HISTORY_FILE),
        index=False,
    )

    if gk.crisis_active and not prior_crisis:
        _send_telegram("🚨 <b>Stateful Adaptive: Sistemik kriz kilidi devrede.</b>")

    print(f"[{now}] ✅ Stateful Adaptive cycle tamamlandı.")
    return payload


if __name__ == "__main__":
    run_background_cycle()
