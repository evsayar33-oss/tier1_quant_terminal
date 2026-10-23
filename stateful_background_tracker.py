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
from performance_ledger import run_ledger_cycle
from data_engine import FRED_ONLY_METRIC_KEYS
from state_schema import recent_events


STATE_FILE = "terminal_state.json"
MEMORY_FILE = "stateful_adaptive_memory.json"
HISTORY_FILE = "terminal_history_stateful.csv"
VERSION = "3.2.0-foundation"


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

    # Same post-adaptive steps as app.py, in the same order, so the state
    # the background job publishes is the SAME decision the UI would show.
    # (Previously the tracker skipped pair reconciliation entirely.)
    try:
        verdicts = gk.reconcile_pairs_post_adaptive(verdicts)
    except Exception as exc:
        print(f"Pair reconciliation atlandı: {exc}")
    try:
        verdicts = gk.apply_final_entry_gate(verdicts)
    except Exception as exc:
        print(f"Final entry gate atlandı: {exc}")

    # v15.1: market structure (session, options calendar, liquidity levels,
    # sweeps, CTA / vol-control proxies) + 5-minute bars for level tests.
    import market_structure as MS
    frames = {a: StatefulAdaptiveController._asset_df(gk.grid_1h, a) for a in ASSET_MATRICES}
    daily = {a: gk.grid_daily.get(a, gk.grid_daily.get(str(ASSET_MATRICES[a].get("benchmark_symbol"))))
             for a in ASSET_MATRICES}
    intraday: Dict[str, Any] = {}
    for a, sym in MS.FIVE_MIN_SYMBOLS.items():
        df5 = MS.fetch_5m(sym)
        if df5 is not None:
            intraday[a] = df5
    contexts: Dict[str, Any] = {}
    for a in ASSET_MATRICES:
        try:
            contexts[a] = MS.build_context(a, frames.get(a), daily.get(a), intraday.get(a))
            import stop_levels as _SL
            contexts[a]["vol"] = _SL.daily_vol(daily.get(a))
        except Exception as exc:
            print(f"[yapı] {a} atlandı: {exc}")
    calendar = MS.options_calendar()

    # v16.2: 15-year SPX dealer-gamma history -> move-size factor (proven, magnitude only).
    gex_hist = None
    try:
        import gex_history as GH
        gex_hist = GH.run()
        if gex_hist:
            for a in GH.APPLIES_TO:
                if a in contexts:
                    contexts[a]["move_factor"] = gex_hist["move_factor"]
                    contexts[a]["gex_history"] = gex_hist
            print(f"[gex] {gex_hist['note']}")
    except Exception as exc:
        print(f"GEX geçmişi atlandı: {exc}")

    # v16.5: ABD makro veri takvimi (FRED). Olay günü etkisi her döngüde ölçülür;
    # sadece kanıtlıysa (t ≥ 3) o gün hareket çarpanına eklenir.
    macro_cal: Dict[str, Any] = {}
    try:
        import macro_calendar as MC
        macro_cal = MC.run(daily)
        for a in ASSET_MATRICES:
            eff = (macro_cal.get("effects") or {}).get(a) or {}
            if a in contexts and macro_cal.get("today") and eff.get("proven"):
                contexts[a]["move_factor"] = float(contexts[a].get("move_factor", 1.0) or 1.0) * float(eff["factor"])
                contexts[a]["event_factor"] = eff["factor"]
        for a, v in verdicts.items():
            v["macro_note"] = MC.note(a, macro_cal)
            v["macro_pending"] = any(not e["passed"] for e in macro_cal.get("today") or [])
        print(f"[makro] bugün: {[e['event'] for e in macro_cal.get('today', [])]} · sorun: {macro_cal.get('problems')}")
    except Exception as exc:
        macro_cal = {"error": str(exc)}
        print(f"Makro takvim atlandı: {exc}")

    # v16.6: Şok dedektörü — 11 göstergenin 5 dk verisinde ani hareket (haber okumadan).
    shock: Dict[str, Any] = {}
    try:
        import shock_monitor as SM
        shock = SM.run(intraday)
        for a, v in verdicts.items():
            f = SM.factor(shock, a)
            if a in contexts and f > 1.0:
                contexts[a]["move_factor"] = float(contexts[a].get("move_factor", 1.0) or 1.0) * f
                contexts[a]["shock_factor"] = round(f, 3)
            v["shock_note"] = SM.note(shock, a)
            v["shock_active"] = bool(shock.get("active") and a in (shock.get("affected") or []))
        print(f"[şok] aktif={shock.get('active')} {shock.get('desc', '')}")
    except Exception as exc:
        shock = {"error": str(exc)}
        print(f"Şok dedektörü atlandı: {exc}")

    # v16.0: proven daily-data direction rule (weekly research) for the long horizon.
    try:
        import direction_research as DR
        research = DR.load_result()
        for a, v in verdicts.items():
            v["research_direction"] = DR.live_direction(a, daily.get(a), research, gk.grid_daily.get("VIX"))
            v["base_rate"] = DR.base_rate(a, research)
            v["base_rates"] = {h: DR.base_rate(a, research, h) for h in DR.BASE_HORIZONS_D}
    except Exception as exc:
        print(f"Yön araştırması atlandı: {exc}")

    # v15.0: dealer gamma map (options-market levels + hedge-flow regime).
    # Timing context only; it never changes direction and never grants entry.
    dealer_gamma: Dict[str, Any] = {}
    try:
        import dealer_gamma as DG
        dealer_gamma = DG.run_cycle(gk.grid_1h, verdicts, frames, intraday_frames=intraday)
        print(f"[gamma] harita: {list(dealer_gamma.get('snapshots', {}))} · "
              f"defter {dealer_gamma.get('history_rows')} satır")
    except Exception as exc:
        dealer_gamma = {"error": str(exc)}
        print(f"Dealer gamma atlandı: {exc}")

    # v15.1: suggested stop per horizon (analysis output, not an order).
    stop_stats: Dict[str, Any] = {}
    try:
        import stop_levels as SL
        stop_stats = SL.run_cycle(verdicts, contexts, dealer_gamma.get("snapshots", {}), frames)
    except Exception as exc:
        stop_stats = {"error": str(exc)}
        print(f"Stop önerisi atlandı: {exc}")

    # v16.4: Tahmin Karnesi — arayüz tahminlerini kaydet, ufuk dolunca notla, aralığı kalibre et.
    forecast_cards: Dict[str, Any] = {}
    try:
        import forecast_ledger as FL
        forecast_cards = FL.run_cycle(verdicts, frames)
    except Exception as exc:
        forecast_cards = {"error": str(exc)}
        print(f"Tahmin karnesi atlandı: {exc}")
    for a, v in verdicts.items():
        if a in contexts:
            v["market_structure"] = contexts[a]

    # Out-of-sample scoreboard: settle earlier calls, record this cycle's
    # FINAL decisions, refresh performance_report.md. Pure observer -- it
    # never feeds back into the model, so it cannot destabilize it.
    performance: Dict[str, Any] = {}
    try:
        events = recent_events(10)
        extra = ["## Durum dosyası olayları (yedekleme / göç)"] + (
            [f"- {e}" for e in events] if events else ["- Kayıt yok ✅"]
        )
        performance = run_ledger_cycle(
            gk, verdicts, StatefulAdaptiveController._asset_df, extra_report_lines=extra
        )
    except Exception as exc:
        performance = {"error": str(exc)}
        print(f"Performance ledger atlandı: {exc}")

    data_health = {}
    for key, v in verdicts.items():
        rows = v.get("details", []) or []
        missing = [
            str(r.get("faktör") or r.get("faktor") or r.get("faktor_id"))
            for r in rows
            if r.get("ham_deger") is None
        ]
        data_health[key] = {
            "factors_total": len(rows),
            "factors_missing": len(missing),
            "missing": missing,
            "coverage": round(1.0 - len(missing) / len(rows), 3) if rows else 0.0,
        }

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
        "performance": performance,
        # Published so the Streamlit app (which cannot see GitHub Actions
        # secrets) can use the same FRED numbers; fetch time travels along.
        "fred_metrics": {
            k: v for k, v in (getattr(gk, "fred_metrics", {}) or {}).items()
            if k in FRED_ONLY_METRIC_KEYS or k in ("fred_fetched_at", "source")
        },
        "data_health": data_health,
        "dealer_gamma": dealer_gamma,
        "market_calendar": calendar,
        "gex_history": gex_hist,
        "stop_calibration": stop_stats,
        "forecast_scorecard": forecast_cards,
        "macro_calendar": macro_cal,
        "shock": shock,
    }
    # v16.3: the system checks its own health and logs problems permanently.
    try:
        import system_health as SH
        payload["system_health"] = SH.run(payload)
        for e in payload["system_health"]["new_events"]:
            print(f"[sağlık] {e['check']} {e['event']}: {e['detail']}")
    except Exception as exc:
        print(f"Sağlık kontrolü atlandı: {exc}")
    _save_json(STATE_FILE, payload)

    row = {
        "timestamp": now,
        "active_regime_id": gk.active_macro_regime_id,
        "market_regime": gk.market_regime,
        "pair_residual_z": adaptive_diag.get("pair_state", {}).get("residual_z"),
        "pair_beta_gold": adaptive_diag.get("pair_state", {}).get("beta_gold"),
        "pair_beta_copper": adaptive_diag.get("pair_state", {}).get("beta_copper"),
        "direction_early_assets": sum(1 for v in adaptive_diag.get("direction", {}).values() if v.get("stage") == "EARLY"),
        "direction_confirmed_assets": sum(1 for v in adaptive_diag.get("direction", {}).values() if v.get("stage") == "CONFIRMED"),
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
