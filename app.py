"""
Streamlit UI: Autonomous Market Direction Terminal (GÜÇLÜ AL - AL - NÖTR - SAT - GÜÇLÜ SAT)
"""
import streamlit as st
import json
import os
import pandas as pd
from config import ASSET_MATRICES
from gatekeeper import PreTradeGatekeeper

st.set_page_config(page_title="Tier-1 Quant Direction Terminal", layout="wide", page_icon="🧭")

STATE_FILE = "terminal_state.json"

def load_background_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

bg_state = load_background_state()

st.title("🧭 Tier-1 Quant Piyasa Yön Terminali")
st.caption("Makro, Kredi, Faiz ve Mikroyapı Verileriyle Otonom Yön Analizi")

col_head1, col_head2 = st.columns([3, 1])
with col_head2:
    live_refresh = st.button("⚡ Canlı Veri Yenile", use_container_width=True)

# Karar Verilerini Topla
gk = None
if live_refresh or not bg_state or "asset_verdicts" not in bg_state:
    with st.spinner("Piyasa verileri canlı taranıyor..."):
        gk = PreTradeGatekeeper()
        gk.refresh_market()
        verdicts = {k: gk.evaluate_asset_direction(k) for k in ASSET_MATRICES.keys()}
        regime = gk.market_regime
        vix_val = gk.current_vix
        crisis_active = gk.crisis_active
else:
    verdicts = bg_state["asset_verdicts"]
    regime = bg_state.get("market_regime", "NEUTRAL")
    vix_val = bg_state.get("current_vix", 15.0)
    crisis_active = bg_state.get("crisis_state", {}).get("is_active", False)

# =============================================================================
# 1. TÜM PİYASA ÖZET TABLOSU (TEK BAKIŞTA TÜM VARLIKLAR)
# =============================================================================
st.subheader("📊 Tüm Varlıklar Canlı Sinyal Tablosu")

summary_rows = []
for k, data in verdicts.items():
    summary_rows.append({
        "Varlık Kodu": k,
        "Varlık Adı": ASSET_MATRICES[k]["name"],
        "Sinyal": f"{data.get('icon', '')} {data.get('verdict', 'NÖTR')}",
        "Skor": f"{data.get('score', 0.0):+.2f}",
        "Küme Durumu": data.get("cluster_agreement", "-"),
        "Güven": f"%{data.get('confidence', 100)}"
    })

df_summary = pd.DataFrame(summary_rows)
st.dataframe(df_summary, use_container_width=True, hide_index=True)

st.divider()

# =============================================================================
# 2. TEKİL VARLIK DERİNLEMESİNE ANALİZİ
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

# BÜYÜK SİNYAL ROZETİ
if "GÜÇLÜ AL" in verdict:
    st.success(f"## {icon} {selected_asset} ── {verdict} (Güçlü Yükseliş Baskısı)")
elif "AL" in verdict:
    st.success(f"### {icon} {selected_asset} ── {verdict} (Pozitif Akış)")
elif "GÜÇLÜ SAT" in verdict:
    st.error(f"## {icon} {selected_asset} ── {verdict} (Ağır Satış Baskısı)")
elif "SAT" in verdict:
    st.error(f"### {icon} {selected_asset} ── {verdict} (Negatif Akış)")
elif "KRİZ" in verdict:
    st.error(f"### ⛔ {selected_asset} ── {verdict} (Piyasa Kilitli)")
else:
    st.info(f"### {icon} {selected_asset} ── {verdict} (Yönsüz Piyasa / İşlem Önerilmez)")

# 4 Metrik Kartı
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("📊 Analiz Net Skoru", f"{score:+.2f}")
with m2:
    st.metric("🏛️ Küme Uyumu", res.get("cluster_agreement", "-"))
with m3:
    st.metric("📈 Piyasa Rejimi", regime.replace("_", " "))
with m4:
    vix_delta = "🛡️ VIX Sakin (<20)" if vix_val < 20.0 else "⚠️ Yüksek Volatilite"
    st.metric("⚡ Anlık VIX / Anomali", f"{vix_val:.1f} / {res.get('anomaly_score', 0):.2f}", delta=vix_delta)

# Faktör Puan Detayı
details = res.get("details", [])
if details:
    with st.expander(f"📋 {selected_asset} Faktör Puan Dağılımı"):
        df_det = pd.DataFrame(details)
        st.dataframe(df_det.rename(columns={
            "faktör": "Faktör Adı",
            "küme": "Küme",
            "ham_deger": "Ham Değer (Z-Score)",
            "puan": "Ağırlıklı Puan"
        }), use_container_width=True, hide_index=True)

last_update = bg_state.get("last_updated", "Canlı Taramadan Alındı")
st.caption(f"🕒 Son Veri Güncellemesi: `{last_update}`")
