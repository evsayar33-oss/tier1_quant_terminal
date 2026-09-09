"""
Tier-1 Quant Terminal - Headless Background Tracker & Crisis Monitor
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
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC] 🔄 Arka plan takip döngüsü başladı...")
    
    # 1. Mevcut state'i yükle
    state = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            pass

    prev_crisis = state.get("crisis_state", {}).get("is_active", False)
    prev_breaches = state.get("crisis_state", {}).get("consecutive_breaches", 0)

    # 2. Gatekeeper'ı başlat ve verileri tazele
    gk = PreTradeGatekeeper()
    gk.crisis_active = prev_crisis
    gk.consecutive_breaches = prev_breaches
    gk.refresh_market()

    # 3. Tüm varlıklar için LONG ve SHORT onay durumlarını hesapla
    verdicts = {}
    for asset_key in ASSET_MATRICES.keys():
        eval_long = gk.evaluate_asset_gate(asset_key, "LONG")
        eval_short = gk.evaluate_asset_gate(asset_key, "SHORT")
        verdicts[asset_key] = {
            "LONG": eval_long,
            "SHORT": eval_short
        }

    # 4. State'i güncelle
    new_state = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "crisis_state": {
            "is_active": gk.crisis_active,
            "consecutive_breaches": gk.consecutive_breaches,
            "anomaly_score": round(gk.anomaly_score, 2),
            "last_crisis_trigger": datetime.now(timezone.utc).isoformat() if gk.crisis_active else state.get("crisis_state", {}).get("last_crisis_trigger")
        },
        "market_summary": {
            "anomaly_score": round(gk.anomaly_score, 2),
            "consecutive_breaches": gk.consecutive_breaches
        },
        "asset_verdicts": verdicts
    }

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(new_state, f, ensure_ascii=False, indent=2)

    # 5. Tarihsel log kaydı (terminal_history.csv)
    history_row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "anomaly_score": gk.anomaly_score,
        "crisis_active": gk.crisis_active,
        "consecutive_breaches": gk.consecutive_breaches
    }
    df_new = pd.DataFrame([history_row])
    if os.path.exists(HISTORY_FILE):
        df_new.to_csv(HISTORY_FILE, mode="a", header=False, index=False)
    else:
        df_new.to_csv(HISTORY_FILE, mode="w", header=True, index=False)

    # 6. KRİZ ALARMI: Eğer kriz durumu yeni devreye girdiyse Telegram'a ACİL bildirim at
    if gk.crisis_active and not prev_crisis:
        msg = "🚨 <b>ACİL DURUM: SİSTEMİK KRİZ KİLİDİ DEVREYE GİRDİ!</b>\n"
        msg += f"⚠️ Kredi ve Volatilite Anomalisi: <b>{gk.anomaly_score:.2f}</b>\n"
        msg += "🛑 <i>Tüm piyasalarda yeni işlem açılışları onay kapısı tarafından DURDURULDU!</i>"
        send_telegram_alert(msg)
    elif not gk.crisis_active and prev_crisis:
        msg = "✅ <b>PİYASA NORMALE DÖNDÜ: Kriz Kilidi Kaldırıldı.</b>\n"
        msg += "🟢 <i>Temel onay kapısı normal doğrulama moduna geçti.</i>"
        send_telegram_alert(msg)

    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC] ✅ State başarıyla kaydedildi. (Kriz: {gk.crisis_active})")

if __name__ == "__main__":
    run_background_cycle()
