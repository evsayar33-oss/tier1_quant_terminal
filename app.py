"""
Streamlit UI: Tier-1 Normalized Macro & Confirmation Gate Terminal (v18)
"""
import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime, timezone, timedelta
from config import ASSET_MATRICES
from gatekeeper import PreTradeGatekeeper

st.set_page_config(page_title="Tier-1 Kurumsal Yön Terminali", layout="wide", page_icon="🧭")

STATE_FILE = "terminal_state.json"

def get_now_tsi_str():
    now_tsi = datetime.now(timezone.utc) + timedelta(hours=3)
    return now_tsi.strftime("%H:%M:%S TSİ")

# Yan Panel: FRED API Key Girişi (İsteğe Bağlı)
st.sidebar.header("🔑 Veri Servisleri")
fred_key_input = st.sidebar.text_input("FRED API Key (İsteğe Bağlı):", type="password", help="St. Louis Fed resmi API anahtarınız varsa buraya yapıştırabilirsiniz.")

st.title("🧭 Tier-1 Öncü Makro Şok & Piyasa Yön Terminali")
st.caption("Barra Normalizasyonlu, Çift Çekirdekli ve Histerezis Korumalı Kurumsal Risk Kapısı")

col_head1, col_head2 = st.columns([3, 1])
with col_head2:
    live_refresh = st.button("⚡ Canlı Verileri Yenile", use_container_width=True)

# Motoru Çalıştır
gk = PreTradeGatekeeper(fred_api_key=fred_key_input)
gk.refresh_market()

verdicts = {}
for k in ASSET_MATRICES.keys():
    verdicts[k] = gk.evaluate_asset_direction(k)

regime = getattr(gk, "market_regime", "MAKRO DENGE")
vix_val = getattr(gk, "current_vix", 16.0)
stagflation_z = getattr(gk, "stagflation_z", 0.0)
yen_carry_z = getattr(gk, "yen_carry_z", 0.0)

# =============================================================================
# 📡 1. GÜNÜN ÖNCÜ MAKRO RADARLARI
# =============================================================================
st.subheader("📡 Günün Öncü Makro İklimi")

r1, r2, r3, r4 = st.columns(4)
with r1:
    st.metric("📈 Aktif Makro Şok Rejimi", regime)
with r2:
    stag_delta = "⚠️ Enflasyon Şoku" if stagflation_z > 1.0 else "✅ Dengeli"
    st.metric("🛢️ Petrol / Ticaret Şoku", f"{stagflation_z:+.2f}σ", delta=stag_delta, delta_color="inverse")
with r3:
    carry_delta = "🚨 Yen Tasfiyesi" if yen_carry_z < -1.2 else "✅ FX Sakin"
    st.metric("💴 USD/JPY Carry İvmesi", f"{yen_carry_z:+.2f}σ", delta=carry_delta)
with r4:
    vix_delta = "🛡️ VIX Sakin (<20)" if vix_val < 20.0 else "⚠️ Yüksek Korku"
    st.metric("⚡ VIX Opsiyon Primi", f"{vix_val:.1f}", delta=vix_delta)

st.divider()

# =============================================================================
# 📊 2. TÜM VARLIKLARIN CANLI SİNYAL TABLOSU (NORMALİZE EDİLMİŞ)
# =============================================================================
st.subheader("📊 Varlıklar Canlı Sinyal Tablosu (Normalleştirilmiş Aralık: [-3.5, +3.5])")

summary_rows = []
for k, data in verdicts.items():
    summary_rows.append({
        "Varlık": k,
        "Ad": ASSET_MATRICES[k]["name"],
        "Sinyal": f"{data.get('icon', '')} {data.get('verdict', 'NÖTR')}",
        "Normal Skor": f"{data.get('score', 0.0):+.2f}",
        "Seans": data.get("session_status", "CANLI"),
        "Küme Durumu": data.get("cluster_agreement", "-")
    })

df_summary = pd.DataFrame(summary_rows)
st.dataframe(df_summary, use_container_width=True, hide_index=True)

st.divider()

# =============================================================================
# 🔍 3. TEKİL VARLIK VE FAKTÖR DAĞILIMI
# =============================================================================
st.subheader("🔍 Varlık Detay Analizi")

selected_asset = st.selectbox(
    "Detayını İncelemek İstediğiniz Varlık:",
    list(ASSET_MATRICES.keys()),
    format_func=lambda x: f"{x} - {ASSET_MATRICES[x]['name']}"
)

res = verdicts.get(selected_asset, {})
verdict = res.get("verdict", "NÖTR")
icon = res.get("icon", "⚪")
score = res.get("score", 0.0)

if "GÜÇLÜ AL" in verdict:
    st.success(f"## {icon} {selected_asset} ── {verdict} (Kararlı Yükseliş Akışı)")
elif "AL" in verdict:
    st.success(f"### {icon} {selected_asset} ── {verdict} (Pozitif İtici Güç)")
elif "GÜÇLÜ SAT" in verdict:
    st.error(f"## {icon} {selected_asset} ── {verdict} (Kararlı Satış Baskısı)")
elif "SAT" in verdict:
    st.error(f"### {icon} {selected_asset} ── {verdict} (Negatif Baskı)")
elif "KRİZ" in verdict:
    st.error(f"### ⛔ {selected_asset} ── {verdict} (Piyasa Kilitli)")
else:
    st.info(f"### {icon} {selected_asset} ── {verdict} (Denge / Yönsüz)")

st.caption(f"🕒 Seans: **{res.get('session_status', 'CANLI')}** | Son Canlı Tarama: **{get_now_tsi_str()}**")

details = res.get("details", [])
if details:
    with st.expander(f"📋 {selected_asset} Faktör Dağılım Tablosu"):
        df_det = pd.DataFrame(details)
        st.dataframe(df_det.rename(columns={
            "faktör": "Faktör Adı",
            "küme": "Küme",
            "ham_deger": "Ham Değer",
            "puan": "Puan (Max ±1.8)"
        }), use_container_width=True, hide_index=True)
