"""
Streamlit UI: Tier-1 Normalized Macro & Confirmation Gate Terminal (v34)
Enhanced with:
- Live Globex 24/5 Streaming for NQ and SPX (No 16:30 TSI freeze)
- Institutional Trade Entry Analysis (Giriş Önerilir / Önerilmez + Gerekçe)
- Volume & Volatility Strict Validation for 'GÜÇLÜ AL' / 'GÜÇLÜ SAT'
"""
import streamlit as st
import json
import os
import sys
import importlib
import pandas as pd
from datetime import datetime, timezone, timedelta

import config
import quant_processor
import data_engine
import gatekeeper
import macro_regime_engine

importlib.reload(config)
importlib.reload(quant_processor)
importlib.reload(data_engine)
importlib.reload(gatekeeper)
importlib.reload(macro_regime_engine)

from config import ASSET_MATRICES, CLUSTERS, SIGNAL_THRESHOLDS, REGIME_DYNAMIC_THRESHOLDS
from gatekeeper import PreTradeGatekeeper
from quant_processor import RobustQuantProcessor

st.set_page_config(
    page_title="Tier-1 Kurumsal Makro Terminali",
    layout="wide",
    page_icon="🧭"
)

STATE_FILE = "terminal_state.json"


def get_now_tsi_str():
    now_tsi = datetime.now(timezone.utc) + timedelta(hours=3)
    return now_tsi.strftime("%H:%M:%S TSİ")


def load_persisted_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_persisted_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# =============================================================================
# 🔑 YAN PANEL
# =============================================================================
st.sidebar.header("🧭 Terminal Ayarları")

default_fred = os.environ.get("FRED_API_KEY", "").strip()
if not default_fred:
    try:
        default_fred = st.secrets.get("FRED_API_KEY", "").strip()
    except Exception:
        default_fred = ""

fred_key_input = st.sidebar.text_input(
    "FRED API Key:",
    value=default_fred,
    type="password",
    help="Resmi FRED API anahtarı."
)

if fred_key_input:
    st.sidebar.success("🔑 Resmi FRED API Bağlantısı Aktif")
else:
    st.sidebar.info("ℹ️ ETF & FX Proxy Motoru Aktif (Kesintisiz Çalışma)")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🛡️ Giriş & Sinyal Kuralları (2019–2026)")
st.sidebar.caption(
    "• **GÜÇLÜ AL / SAT:** Yalnızca Hacim (RVOL ≥ 1.25) ve Volatilite (0.75-2.10) teyitliyse verilir.\n"
    "• **GİRİŞ KİLİDİ:** Volatilite şoku (>2.20) veya Climax hacminde (>3.20) 'Giriş Önerilmez' uyarısı çıkar.\n"
    "• **NQ & SPX:** 24 saat kesintisiz Globex vadeli akışı devrededir."
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📚 Küme (Cluster) Rehberi")
for code, desc in CLUSTERS.items():
    st.sidebar.caption(f"**Küme {code}:** {desc}")


# =============================================================================
# 🚀 DURUM VE VERİ YÖNETİMİ
# =============================================================================
persisted = load_persisted_state()
effective_fred_key = fred_key_input or default_fred

if "gatekeeper" not in st.session_state:
    st.session_state.gatekeeper = PreTradeGatekeeper(fred_api_key=effective_fred_key)
    st.session_state.state_data = persisted
    st.session_state.last_sync_time = persisted.get("last_updated", None)

gk = st.session_state.gatekeeper

# =============================================================================
# 🧭 BAŞLIK VE ÜST AKSİYONLAR
# =============================================================================
col_title, col_btn = st.columns([3, 1])
with col_title:
    st.title("🧭 Tier-1 Kurumsal Makro Terminali & Giriş Analizi")
    st.caption("2019-2026 Piyasa Rejimi Kalibrasyonu | Kesintisiz Globex Vadeli Akışı | Şok Korumalı Giriş Analizi")

with col_btn:
    st.write("")
    live_refresh = st.button("⚡ Canlı Verileri Yenile", use_container_width=True, type="primary")

if live_refresh or not st.session_state.state_data:
    with st.spinner("Piyasa verileri toplanıyor, Hacim & Volatilite giriş filtreleri hesaplanıyor..."):
        prev_verdicts = st.session_state.state_data.get("asset_verdicts", {})
        gk.refresh_market()

        prev_map = {k: prev_verdicts.get(k, {}).get("verdict", "NÖTR (BEKLE)") for k in ASSET_MATRICES.keys()}
        verdicts = gk.evaluate_all_assets_harmonized(prev_map)

        comp_usd = round(float(getattr(gk, "composite_usd_risk", -0.25)), 2)
        dxy_v = round(float(getattr(gk, "dxy_velocity", 0.12)), 2)
        ndl_val = round(float(getattr(gk, "ndl_z", 0.25)), 2)
        yen_carry = round(float(getattr(gk, "yen_carry_z", 0.05)), 2)

        current_time_iso = datetime.now(timezone.utc).isoformat()
        new_state = {
            "last_updated": current_time_iso,
            "active_regime_id": getattr(gk, "active_macro_regime_id", 5),
            "active_regime_name": getattr(gk, "active_macro_regime_name", "Küresel Likidite Rallisi (Risk-On)"),
            "market_regime": getattr(gk, "market_regime", "🟢 [REJİM 5] Küresel Likidite Rallisi (Risk-On)"),
            "active_subtype": getattr(gk, "active_subtype", "Klasik Goldilocks Risk-On"),
            "dynamic_thresholds": getattr(gk, "dynamic_thresholds", {}),
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
                "is_active": getattr(gk, "crisis_active", False),
                "consecutive_breaches": getattr(gk, "consecutive_breaches", 0),
                "anomaly_score": round(float(getattr(gk, "anomaly_score", 0.0)), 2),
                "vix_floor_active": bool(getattr(gk, "current_vix", 16.0) < 20.0)
            },
            "asset_verdicts": verdicts
        }
        st.session_state.state_data = new_state
        st.session_state.last_sync_time = current_time_iso
        save_persisted_state(new_state)

active_data = st.session_state.state_data
regime = active_data.get("market_regime", "🟢 [REJİM 5] Küresel Likidite Rallisi (Risk-On)")
verdicts = active_data.get("asset_verdicts", {})
is_crisis = active_data.get("crisis_state", {}).get("is_active", False)

if is_crisis:
    st.error("🚨 **ACİL DURUM: SİSTEMİK KRİZ KİLİDİ AKTİF!** Tüm yeni pozisyonlar durduruldu.")

# =============================================================================
# 📊 1. TÜM VARLIKLARIN CANLI YÖN VE GİRİŞ ANALİZİ TABLOSU
# =============================================================================
st.subheader("📊 1. Canlı Yön, Sinyal & İşleme Giriş Analizi Tablosu")

summary_rows = []
for k in ASSET_MATRICES.keys():
    data = verdicts.get(k, {})
    curr_dir = data.get("current_direction", "⚪ YATAY (%0.00)")
    fore_dir = f"{data.get('icon', '⚪')} {data.get('verdict', 'NÖTR (BEKLE)')}"
    entry_st = data.get("entry_status", "🟢 İŞLEME GİRİŞ ÖNERİLİR")
    entry_rs = data.get("entry_reason", "Volatilite ve hacim dengeli.")
    rvol_val = data.get("rvol", 1.0)
    atr_val = data.get("atr_ratio", 1.0)

    summary_rows.append({
        "Varlık": k,
        "Ad": ASSET_MATRICES[k]["name"],
        "📍 Canlı Fiyat Yönü (Globex)": curr_dir,
        "🔮 Model Sinyali": fore_dir,
        "🛡️ Giriş Analizi": entry_st,
        "Giriş Gerekçesi": entry_rs,
        "Hacim (RVOL)": f"{rvol_val:.2f}x",
        "Volatilite (ATR)": f"{atr_val:.2f}x",
        "Model Skoru": f"{float(data.get('score', 0.0)):+.2f}"
    })

df_summary = pd.DataFrame(summary_rows)
st.dataframe(df_summary, use_container_width=True, hide_index=True)

st.caption(
    "💡 **Giriş ve Sinyal Mantığı:** 'GÜÇLÜ AL' ve 'GÜÇLÜ SAT' sinyalleri ancak hacim ve volatilite onay verirse yanar. "
    "Volatilite veya hacim şoku durumunda 'İşleme Giriş Önerilmez' gerekçesiyle birlikte listelenir."
)

st.divider()

# =============================================================================
# 🔍 2. TEKİL VARLIK VE DERİNLİK ANALİZİ
# =============================================================================
st.subheader("🔍 2. Varlık Derinlik, Giriş Gerekçesi & Faktör Dağılımı")

selected_asset = st.selectbox(
    "Detayını İncelemek İstediğiniz Varlık:",
    list(ASSET_MATRICES.keys()),
    format_func=lambda x: f"{x} ── {ASSET_MATRICES[x]['name']}"
)

res = verdicts.get(selected_asset, {})
verdict = res.get("verdict", "NÖTR (BEKLE)")
icon = res.get("icon", "⚪")
score = float(res.get("score", 0.0))
curr_dir = res.get("current_direction", "⚪ YATAY (%0.00)")
entry_st = res.get("entry_status", "🟢 İŞLEME GİRİŞ ÖNERİLİR")
entry_rs = res.get("entry_reason", "")
rvol_val = res.get("rvol", 1.0)
atr_val = res.get("atr_ratio", 1.0)

col_card1, col_card2 = st.columns([2, 1])

with col_card1:
    st.markdown(f"#### 📍 Canlı Fiyat Durumu: **{curr_dir}**")
    if "GÜÇLÜ" in verdict:
        st.success(f"### 🔮 Nihai Teyitli Sinyal: **{icon} {verdict}** (Hacim & Volatilite Onaylı)")
    elif "AL" in verdict:
        st.success(f"### 🔮 Model Yönü: **{icon} {verdict}**")
    elif "SAT" in verdict:
        st.error(f"### 🔮 Model Yönü: **{icon} {verdict}**")
    else:
        st.info(f"### 🔮 Model Yönü: **{icon} {verdict}** (Testere Bandı)")

    if "ÖNERİLMEZ" in entry_st:
        st.warning(f"⚠️ **Giriş Filtresi Uyarısı:** {entry_rs}")
    else:
        st.success(f"✅ **Giriş Filtresi Teyidi:** {entry_rs}")

with col_card2:
    st.metric(
        label=f"{selected_asset} Normalleştirilmiş Skor",
        value=f"{score:+.2f}",
        delta=f"Hacim: {rvol_val:.2f}x | ATR: {atr_val:.2f}x"
    )

details = res.get("details", [])
if details:
    with st.expander(f"📋 {selected_asset} Çok Faktörlü Risk & Getiri Dağılım Tablosu", expanded=True):
        df_det = pd.DataFrame(details)
        st.dataframe(
            df_det.rename(columns={
                "faktör": "Faktör Adı",
                "küme": "Küme",
                "ham_deger": "Ham Değer (σ / ROC)",
                "puan": "Puan Katkısı"
            }),
            use_container_width=True,
            hide_index=True
        )
