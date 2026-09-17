"""Headless V2.2 tracker using exactly the same production core as Streamlit."""
import os
import json
import requests
import pandas as pd
from datetime import datetime, timezone
from config import ASSET_MATRICES
from gatekeeper import PreTradeGatekeeper

STATE_FILE="terminal_state.json"
HISTORY_FILE="terminal_history.csv"
V22_VERSION="2.2.1"

def send_telegram_alert(message):
    token=os.environ.get("TELEGRAM_TOKEN"); chat_id=os.environ.get("CHAT_ID")
    if not token or not chat_id: return
    try: requests.post("https://api.telegram.org/bot"+token+"/sendMessage",json={"chat_id":chat_id,"text":message,"parse_mode":"HTML"},timeout=10)
    except Exception as exc: print(f"Telegram alert hatası: {exc}")

def _fmt_num(value, digits=2, default="—"):
    try:
        if value is None:
            return default
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return default


def run_background_cycle():
    now=datetime.now(timezone.utc).isoformat(); fred_api_key=os.environ.get("FRED_API_KEY","").strip()
    print(f"[{now}] 🔄 V2.2 arka plan taraması başladı.")
    if fred_api_key: print(f"[{now}] 🔑 FRED_API_KEY aktif.")
    else: print(f"[{now}] ℹ️ FRED_API_KEY yok; yalnızca mevcut gerçek piyasa kaynakları kullanılıyor. Eksik macro veri UNAVAILABLE/PARTIAL.")
    state={}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE,"r",encoding="utf-8") as f: state=json.load(f)
        except Exception: pass
    prev_crisis=bool(state.get("crisis_state",{}).get("is_active",False)); prev_breaches=int(state.get("crisis_state",{}).get("consecutive_breaches",0)); prev=state.get("asset_verdicts",{})
    gk=PreTradeGatekeeper(fred_api_key=fred_api_key); gk.crisis_active=prev_crisis; gk.consecutive_breaches=prev_breaches
    gk.refresh_market(); prev_map={k:prev.get(k,{}).get("verdict","NÖTR (BEKLE)") for k in ASSET_MATRICES.keys()}; verdicts=gk.evaluate_all_assets_harmonized(prev_map)
    payload={
      "v22_version":V22_VERSION,"last_updated":now,"active_regime_id":gk.active_macro_regime_id,"active_regime_name":gk.active_macro_regime_name,
      "market_regime":gk.market_regime,"active_subtype":gk.active_subtype,"dynamic_thresholds":gk.dynamic_thresholds,"macro_diagnostics":gk.macro_diagnostics,
      "composite_usd_risk":gk.composite_usd_risk,"usd_risk_label":gk.usd_risk_label,"usd_risk_status":gk.usd_risk_status,"dxy_velocity":gk.dxy_velocity,"ndl_z":gk.ndl_z,
      "current_vix":gk.current_vix,"stagflation_z":gk.stagflation_z,"yen_carry_z":gk.yen_carry_z,"dfii10_z":gk.dfii10_z,"curve_label":gk.curve_label,
      "crisis_state":{"is_active":gk.crisis_active,"consecutive_breaches":gk.consecutive_breaches,"anomaly_score":gk.anomaly_score,"vix_floor_active":bool(gk.current_vix is not None and gk.current_vix<20)},
      "data_quality":gk.data_engine.data_quality,"data_sources":gk.data_engine.data_sources,"asset_verdicts":verdicts
    }
    with open(STATE_FILE,"w",encoding="utf-8") as f: json.dump(payload,f,ensure_ascii=False,indent=2,allow_nan=False,default=str)
    row={"timestamp":now,"anomaly_score":gk.anomaly_score,"current_vix":gk.current_vix,"composite_usd_risk":gk.composite_usd_risk,"dxy_velocity":gk.dxy_velocity,"crisis_active":gk.crisis_active,"market_regime":gk.market_regime,"active_regime_id":gk.active_macro_regime_id}
    pd.DataFrame([row]).to_csv(HISTORY_FILE,mode="a",header=not os.path.exists(HISTORY_FILE),index=False)
    if gk.crisis_active and not prev_crisis:
        send_telegram_alert("🚨 <b>ACİL DURUM: SİSTEMİK KRİZ KİLİDİ DEVREYE GİRDİ!</b>")
    print(f"[{now}] ✅ V2.2 taraması tamamlandı.")

if __name__=="__main__": run_background_cycle()
