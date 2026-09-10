"""
Tier-1 Quant Terminal - Headless Background Tracker (Zero Crash Guarantee) (v28)
Enhanced with:
- Macro Event Interpretation System v1.0 & Calibrated Dynamic Thresholds
- Automatic FRED_API_KEY Injection from GitHub Actions Secrets & Environment
- Full 3-Pillar USD Risk State Persistence (composite_usd_risk, dxy_velocity, ndl_z)
"""
import os
import json
import requests
import pandas as pd
from datetime import datetime, timezone
from config import ASSET_MATRICES, REGIME_DYNAMIC_THRESHOLDS
from gatekeeper import PreTradeGatekeeper

STATE_FILE = "terminal_state.json"
HISTORY_FILE = "terminal_history.csv"


def send_telegram_alert(message):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(f"⚠️ Telegram alert hatası: {e}")


def run_background_cycle():
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC] 🔄 Arka plan kurumsal öncü tarama başladı...")

    fred_api_key = os.environ.get("FRED_API_KEY", "").strip()
    if fred_api_key:
        print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC] 🔑 FRED_API_KEY başarıyla tespit edildi ve aktifleştirildi.")
    else:
        print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC] ℹ️ FRED_API_KEY bulunamadı, piyasa ETF proxy motoru devrede.")

    state = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            pass

    prev_crisis = state.get("crisis_state", {}).get("is_active", False)
    prev_breaches = state.get("crisis_state", {}).get("consecutive_breaches", 0)
    prev_verdicts = state.get("asset_verdicts", {})

    gk = PreTradeGatekeeper(fred_api_key=fred_api_key)
    gk.crisis_active = prev_crisis
    gk.consecutive_breaches = prev_breaches
    gk.refresh_market()

    prev_map = {k: prev_verdicts.get(k, {}).get("verdict", "NÖTR (BEKLE)") for k in ASSET_MATRICES.keys()}
    if hasattr(gk, "evaluate_all_assets_harmonized"):
        verdicts = gk.evaluate_all_assets_harmonized(prev_map)
    else:
        verdicts = {k: gk.evaluate_asset_direction(k, previous_signal=prev_map[k]) for k in ASSET_MATRICES.keys()}

    comp_usd = round(float(getattr(gk, "composite_usd_risk", 0.0)), 2)
    dxy_v = round(float(getattr(gk, "dxy_velocity", 0.0)), 2)
    ndl_val = round(float(getattr(gk, "ndl_z", 0.25)), 2)
    yen_carry = round(float(getattr(gk, "yen_carry_z", 0.0)), 2)

    new_state = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "active_regime_id": getattr(gk, "active_macro_regime_id", 5),
        "active_regime_name": getattr(gk, "active_macro_regime_name", "Küresel Likidite Rallisi (Risk-On)"),
        "market_regime": getattr(gk, "market_regime", "🟢 [REJİM 5] Küresel Likidite Rallisi (Risk-On)"),
        "active_subtype": getattr(gk, "active_subtype", "Klasik Goldilocks Risk-On"),
        "dynamic_thresholds": getattr(gk, "dynamic_thresholds", REGIME_DYNAMIC_THRESHOLDS.get(5, {})),
        "macro_diagnostics": getattr(gk, "macro_diagnostics", {}),
        "composite_usd_risk": comp_usd,
        "usd_risk_label": getattr(gk, "usd_risk_label", "🟡 NÖTR / DENGELİ USD İKLİMİ"),
        "usd_risk_status": getattr(gk, "usd_risk_status", "NEUTRAL"),
        "dxy_velocity": dxy_v,
        "ndl_z": ndl_val,
        "current_vix": round(float(getattr(gk, "current_vix", 16.0)), 1),
        "stagflation_z": round(float(getattr(gk, "stagflation_z", 0.0)), 2),
        "yen_carry_z": yen_carry,
        "dfii10_z": round(float(getattr(gk, "dfii10_z", 0.45)), 2),
        "curve_label": getattr(gk, "curve_label", "DÜZ EĞRİ"),
        "crisis_state": {
            "is_active": gk.crisis_active,
            "consecutive_breaches": gk.consecutive_breaches,
            "anomaly_score": round(float(getattr(gk, "anomaly_score", 0.0)), 2),
            "vix_floor_active": bool(getattr(gk, "current_vix", 16.0) < 20.0)
        },
        "asset_verdicts": verdicts
    }

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(new_state, f, ensure_ascii=False, indent=2)

    history_row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "anomaly_score": getattr(gk, "anomaly_score", 0.0),
        "current_vix": getattr(gk, "current_vix", 16.0),
        "composite_usd_risk": comp_usd,
        "dxy_velocity": dxy_v,
        "crisis_active": gk.crisis_active,
        "market_regime": getattr(gk, "market_regime", "🟢 [REJİM 5] Küresel Likidite Rallisi (Risk-On)"),
        "active_regime_id": getattr(gk, "active_macro_regime_id", 5)
    }
    df_new = pd.DataFrame([history_row])
    if os.path.exists(HISTORY_FILE):
        df_new.to_csv(HISTORY_FILE, mode="a", header=False, index=False)
    else:
        df_new.to_csv(HISTORY_FILE, mode="w", header=True, index=False)

    if gk.crisis_active and not prev_crisis:
        msg = "🚨 <b>ACİL DURUM: SİSTEMİK KRİZ KİLİDİ DEVREYE GİRDİ!</b>\n"
        msg += f"⚠️ Anomali: <b>{getattr(gk, 'anomaly_score', 0.0):.2f}</b> (VIX: {getattr(gk, 'current_vix', 16.0):.1f})\n"
        msg += "🛑 <i>Tüm piyasalarda yeni işlem açılışları DURDURULDU!</i>"
        send_telegram_alert(msg)

    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC] ✅ Tarama başarıyla bitti. USD Risk: {comp_usd:+.2f}σ, DXY İvme: {dxy_v:+.2f}σ")


if __name__ == "__main__":
    run_background_cycle()
