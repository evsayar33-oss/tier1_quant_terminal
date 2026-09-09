"""
Streamlit UI: Tier-1 3-Pillar & Whipsaw-Protected Terminal (v10)
"""
import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime, timezone, timedelta
from config import ASSET_MATRICES
from gatekeeper import PreTradeGatekeeper

st.set_page_config(page_title="Tier-1 Histerezis Korumalı Terminal", layout="wide", page_icon="🧭")

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

st.title("🧭 Tier-1 Titreşimsiz Piyasa Yön Terminali")
st.caption("3 Standart Sütun (Yön + Likidite Akışı + USD Gücü) & Histerezis Ölü Bant Koruması")

col_head1, col_head2 = st.columns([3, 1])
with col_head2:
    live_refresh = st.button("⚡ Canlı Verileri Yenile", use_container_width=True)

gk = PreTradeGatekeeper()
gk.refresh_market()

# Önceki sinyalleri hafızadan alarak titreşimi süz
prev_verdicts = bg_state.get("asset_verdicts", {})
verdicts = {}
for k in ASSET_MATRICES.keys():
    prev_sig = prev_verdicts.get(k, {}).get("verdict", "NÖTR (BEKLE)")
    verdicts[k] = gk.evaluate_asset_direction(k, previous_signal=prev_sig)

regime = getattr(gk, "market_regime", "MAKRO DENGE")
vix_val = getattr(gk, "current_vix", 16.0)
stagflation_z = getattr(gk, "stagflation_z", 0.0)
yen_carry_z = getattr(gk, "yen_carry_z", 0.0)
is_event_active = getattr(gk, "is_event_active", False)
event_desc = getattr(gk, "event_desc", "Sakin Veri Dönemi")

if is_event_active:
    st.error(f"⚠️ **DİKKAT: HABER PENCERESİ!** ── `{event_desc}` saati içerisindesiniz.")

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
# 📊 2. TÜM VARLIKLARIN CANLI SİNYAL TABLOSU
# =============================================================================
st.subheader("📊 Varlıklar Canlı Sinyal Tablosu (Titreşimsiz Histerezis Modu)")

summary_rows = []
for k, data in verdicts.items():
    summary_rows.append({
        "Varlık": k,
        "Ad": ASSET_MATRICES[k]["name"],
        "Sinyal": f"{data.get('icon', '')} {data.get('verdict', 'NÖTR')}",
        "Net Skor": f"{data.get('score', 0.0):+.2f}",
        "Seans": data.get("session_status", "CANLI"),
        "Küme Durumu": data.get("cluster_agreement", "-")
    })

df_summary = pd.DataFrame(summary_rows)
st.dataframe(df_summary, use_container_width=True, hide_index=True)

st.divider()

# =============================================================================
# 🔍 3. TEKİL VARLIK DETAYI (3 SÜTUN DAĞILIMI)
# =============================================================================
st.subheader("🔍 Varlık 3 Temel Sütun & Faktör Dağılımı")

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
    st.info(f"### {icon} {selected_asset} ── {verdict} (Denge / Yönsüz Ölü Bant)")

st.caption(f"🕒 Seans: **{res.get('session_status', 'CANLI')}** | Son Canlı Tarama: **{get_now_tsi_str()}**")

details = res.get("details", [])
if details:
    with st.expander(f"📋 {selected_asset} 3 Sütun ve Faktör Puanları"):
        df_det = pd.DataFrame(details)
        st.dataframe(df_det.rename(columns={
            "faktör": "Faktör Adı",
            "küme": "Küme",
            "ham_deger": "Ham Değer",
            "puan": "Net Puan"
        }), use_container_width=True, hide_index=True)
