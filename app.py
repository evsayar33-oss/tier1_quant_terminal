"""
Streamlit UI: Tier-1 Asset-Aware & Session-Protected Terminal (v9)
"""
import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime, timezone, timedelta
from config import ASSET_MATRICES
from gatekeeper import PreTradeGatekeeper

st.set_page_config(page_title="Tier-1 Varlık & Seans Korumalı Terminal", layout="wide", page_icon="🧭")

STATE_FILE = "terminal_state.json"

def get_now_tsi_str():
    now_tsi = datetime.now(timezone.utc) + timedelta(hours=3)
    return now_tsi.strftime("%H:%M:%S TSİ")

def load_background_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

bg_state = load_background_state()

st.title("🧭 Tier-1 Varlık ve Seans Korumalı Piyasa Terminali")
st.caption("Varlığa Özel İtici Güçler, Canlı Seans Saatleri ve Olay Kalkanı ile Donatılmış Kurumsal Risk Kapısı")

col_head1, col_head2 = st.columns([3, 1])
with col_head2:
    live_refresh = st.button("⚡ Canlı Verileri Yenile", use_container_width=True)

gk = PreTradeGatekeeper()
gk.refresh_market()
verdicts = {k: gk.evaluate_asset_direction(k) for k in ASSET_MATRICES.keys()}
regime = getattr(gk, "market_regime", "MAKRO DENGE")
vix_val = getattr(gk, "current_vix", 16.0)
stagflation_z = getattr(gk, "stagflation_z", 0.0)
yen_carry_z = getattr(gk, "yen_carry_z", 0.0)
is_event_active = getattr(gk, "is_event_active", False)
event_desc = getattr(gk, "event_desc", "Sakin Veri Dönemi")

# =============================================================================
# 🚨 1. KRİTİK HABER / VERİ SAATİ ALARMI
# =============================================================================
if is_event_active:
    st.error(f"⚠️ **DİKKAT: YÜKSEK VOLATİLİTE / HABER PENCERESİ!** ── `{event_desc}` saati içerisindesiniz. Anlık iğnelere ve sahte kırılımlara karşı temkinli olun!")

# =============================================================================
# 📡 2. GÜNÜN ÖNCÜ MAKRO RADARLARI
# =============================================================================
st.subheader("📡 Günün Öncü Makro İklimi")

r1, r2, r3, r4 = st.columns(4)
with r1:
    st.metric("📈 Aktif Makro Şok Rejimi", regime)
with r2:
    stag_delta = "⚠️ Enflasyon/Maliyet Şoku" if stagflation_z > 1.0 else "✅ Dengeli"
    st.metric("🛢️ Petrol / Ticaret Şoku", f"{stagflation_z:+.2f}σ", delta=stag_delta, delta_color="inverse")
with r3:
    carry_delta = "🚨 Yen Carry Tasfiyesi" if yen_carry_z < -1.2 else "✅ FX Sakin"
    st.metric("💴 USD/JPY Carry İvmesi", f"{yen_carry_z:+.2f}σ", delta=carry_delta)
with r4:
    vix_delta = "🛡️ VIX Sakin (<20)" if vix_val < 20.0 else "⚠️ Yüksek Korku"
    st.metric("⚡ VIX Opsiyon Primi", f"{vix_val:.1f}", delta=vix_delta)

st.divider()

# =============================================================================
# 📊 3. TÜM VARLIKLARIN SEANS VE YÖN TABLOSU
# =============================================================================
st.subheader("📊 Varlıklar İçin Canlı Yön ve Seans Tablosu")

summary_rows = []
for k, data in verdicts.items():
    summary_rows.append({
        "Varlık Kodu": k,
        "Varlık Adı": ASSET_MATRICES[k]["name"],
        "Sinyal": f"{data.get('icon', '')} {data.get('verdict', 'NÖTR')}",
        "Normalize Skor": f"{data.get('score', 0.0):+.2f}",
        "Seans Durumu": data.get("session_status", "CANLI"),
        "Küme Dağılımı": data.get("cluster_agreement", "-")
    })

df_summary = pd.DataFrame(summary_rows)
st.dataframe(df_summary, use_container_width=True, hide_index=True)

st.divider()

# =============================================================================
# 🔍 4. TEKİL VARLIK DERİNLEMESİNE ANALİZİ
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
session_info = res.get("session_status", "CANLI")

if "GÜÇLÜ AL" in verdict:
    st.success(f"## {icon} {selected_asset} ── {verdict} (Öncü Güçler Yukarı İtiyor)")
elif "AL" in verdict:
    st.success(f"### {icon} {selected_asset} ── {verdict} (Pozitif Akış)")
elif "GÜÇLÜ SAT" in verdict:
    st.error(f"## {icon} {selected_asset} ── {verdict} (Ağır Satış Baskısı)")
elif "SAT" in verdict:
    st.error(f"### {icon} {selected_asset} ── {verdict} (Negatif Akış)")
elif "KRİZ" in verdict:
    st.error(f"### ⛔ {selected_asset} ── {verdict} (Piyasa Kilitli)")
else:
    st.info(f"### {icon} {selected_asset} ── {verdict} (Denge / Yönsüz)")

st.caption(f"🕒 Aktif Seans: **{session_info}** | Son Tarama: **{get_now_tsi_str()}**")

details = res.get("details", [])
if details:
    with st.expander(f"📋 {selected_asset} Varlığa Özel İtici Faktörler"):
        df_det = pd.DataFrame(details)
        st.dataframe(df_det.rename(columns={
            "faktör": "İtici Faktör Adı",
            "küme": "Küme",
            "ham_deger": "Ham Değer",
            "puan": "Ağırlıklı Puan"
        }), use_container_width=True, hide_index=True)
