"""
Tier-1 Quant Terminal - Headless Background Tracker (Direct Signals)
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
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC] 🔄 Arka plan yön taraması başladı...")
    
    state = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            pass

    prev_crisis = state.get("crisis_state", {}).get("is_active", False)
    prev_breaches = state.get("crisis_state", {}).get("consecutive_breaches", 0)

    gk = PreTradeGatekeeper()
    gk.crisis_active = prev_crisis
    gk.consecutive_breaches = prev_breaches
    gk.refresh_market()

    verdicts = {}
    for asset_key in ASSET_MATRICES.keys():
        verdicts[asset_key] = gk.evaluate_asset_direction(asset_key)

    new_state = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "market_regime": gk.market_regime,
        "current_vix": round(gk.current_vix, 1),
        "crisis_state": {
            "is_active": gk.crisis_active,
            "consecutive_breaches": gk.consecutive_breaches,
            "anomaly_score": round(gk.anomaly_score, 2),
            "vix_floor_active": bool(gk.current_vix < 20.0)
        },
        "asset_verdicts": verdicts
    }

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(new_state, f, ensure_ascii=False, indent=2)

    history_row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "anomaly_score": gk.anomaly_score,
        "current_vix": gk.current_vix,
        "crisis_active": gk.crisis_active,
        "market_regime": gk.market_regime
    }
    df_new = pd.DataFrame([history_row])
    if os.path.exists(HISTORY_FILE):
        df_new.to_csv(HISTORY_FILE, mode="a", header=False, index=False)
    else:
        df_new.to_csv(HISTORY_FILE, mode="w", header=True, index=False)

    if gk.crisis_active and not prev_crisis:
        msg = "🚨 <b>ACİL DURUM: SİSTEMİK KRİZ KİLİDİ DEVREYE GİRDİ!</b>\n"
        msg += f"⚠️ Kredi ve Volatilite Anomalisi: <b>{gk.anomaly_score:.2f}</b> (VIX: {gk.current_vix:.1f})\n"
        msg += "🛑 <i>Tüm piyasalarda yeni işlem açılışları DURDURULDU!</i>"
        send_telegram_alert(msg)

    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC] ✅ Yön taraması tamamlandı. (Rejim: {gk.market_regime})")

if __name__ == "__main__":
    run_background_cycle()
