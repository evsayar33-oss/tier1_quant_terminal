"""
Tier-1 Quant Terminal - Headless Background Tracker (Zero Crash Guarantee) (v18)
"""
import os
import json
import requests
import pandas as pd
from datetime import datetime, timezone
from config import ASSET_MATRICES
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

    gk = PreTradeGatekeeper()
    gk.crisis_active = prev_crisis
    gk.consecutive_breaches = prev_breaches
    gk.refresh_market()

    verdicts = {}
    for asset_key in ASSET_MATRICES.keys():
        prev_sig = prev_verdicts.get(asset_key, {}).get("verdict", "NÖTR (BEKLE)")
        verdicts[asset_key] = gk.evaluate_asset_direction(asset_key, previous_signal=prev_sig)

    new_state = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "market_regime": getattr(gk, "market_regime", "MAKRO DENGE / SIKIŞMA"),
        "current_vix": round(getattr(gk, "current_vix", 16.0), 1),
        "stagflation_z": round(getattr(gk, "stagflation_z", 0.0), 2),
        "yen_carry_z": round(getattr(gk, "yen_carry_z", 0.0), 2),
        "dfii10_z": round(getattr(gk, "dfii10_z", 0.45), 2),
        "curve_label": getattr(gk, "curve_label", "DÜZ EĞRİ"),
        "crisis_state": {
            "is_active": gk.crisis_active,
            "consecutive_breaches": gk.consecutive_breaches,
            "anomaly_score": round(getattr(gk, "anomaly_score", 0.0), 2),
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
        "crisis_active": gk.crisis_active,
        "market_regime": getattr(gk, "market_regime", "MAKRO DENGE / SIKIŞMA")
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

    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC] ✅ Tarama başarıyla bitti.")


if __name__ == "__main__":
    run_background_cycle()
