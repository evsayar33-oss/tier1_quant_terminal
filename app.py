"""
Streamlit UI: Tier-1 Leading Macro & Cross-Asset Shock Radar Terminal
"""
import streamlit as st
import json
import os
import pandas as pd
from config import ASSET_MATRICES
from gatekeeper import PreTradeGatekeeper

st.set_page_config(page_title="Tier-1 Leading Macro Radar", layout="wide", page_icon="🧭")

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

st.title("🧭 Tier-1 Öncü Makro Şok & Piyasa Yön Terminali")
st.caption("Petrol/Ticaret Enflasyon Şoku, Yen Carry Trade ve Kredi Riskiyle Öncü Yön Analizi")

col_head1, col_head2 = st.columns([3, 1])
with col_head2:
    live_refresh = st.button("⚡ Canlı Verileri Yenile", use_container_width=True)

gk = None
if live_refresh or not bg_state or "asset_verdicts" not in bg_state:
    with st.spinner("5 Öncü Makro Radar taranıyor..."):
        gk = PreTradeGatekeeper()
        gk.refresh_market()
        verdicts = {k: gk.evaluate_asset_direction(k) for k in ASSET_MATRICES.keys()}
        regime = gk.market_regime
        vix_val = gk.current_vix
        crisis_active = gk.crisis_active
        stagflation_z = gk.stagflation_z
        yen_carry_z = gk.yen_carry_z
else:
    verdicts = bg_state["asset_verdicts"]
    regime = bg_state.get("market_regime", "MAKRO DENGE")
    vix_val = bg_state.get("current_vix", 15.0)
    crisis_active = bg_state.get("crisis_state", {}).get("is_active", False)
    stagflation_z = bg_state.get("stagflation_z", 0.0)
    yen_carry_z = bg_state.get("yen_carry_z", 0.0)

# =============================================================================
# 1. 5 ÖNCÜ MAKRO RADAR GÖSTERGESİ (BÜYÜK ÜST PANEL)
# =============================================================================
st.subheader("📡 Günün Öncü Makro İklimi & Şok Radarları")

r1, r2, r3, r4 = st.columns(4)
with r1:
    st.metric("📈 Günün Makro Rejimi", regime)
with r2:
    stag_delta = "⚠️ Enflasyon/Maliyet Şoku" if stagflation_z > 1.0 else "✅ Dengeli"
    st.metric("🛢️ Petrol / Ticaret Şoku", f"{stagflation_z:+.2f}σ", delta=stag_delta, delta_color="inverse")
with r3:
    carry_delta = "🚨 Yen Carry Tasfiyesi" if yen_carry_z < -1.2 else "✅ FX Sakin"
    st.metric("💴 USD/JPY Carry İvmesi", f"{yen_carry_z:+.2f}σ", delta=carry_delta)
with r4:
    vix_delta = "🛡️ VIX Sakin (<20)" if vix_val < 20.0 else "⚠️ Korku Primi Yüksek"
    st.metric("⚡ VIX Opsiyon Primi", f"{vix_val:.1f}", delta=vix_delta)

st.divider()

# =============================================================================
# 2. TÜM VARLIKLAR ÖZET TABLOSU
# =============================================================================
st.subheader("📊 Varlıklar İçin Öncü Yön Tablosu")

summary_rows = []
for k, data in verdicts.items():
    summary_rows.append({
        "Varlık Kodu": k,
        "Varlık Adı": ASSET_MATRICES[k]["name"],
        "Sinyal": f"{data.get('icon', '')} {data.get('verdict', 'NÖTR')}",
        "Öncü Net Skor": f"{data.get('score', 0.0):+.2f}",
        "Küme Dağılımı": data.get("cluster_agreement", "-"),
        "Veri Güveni": f"%{data.get('confidence', 100)}"
    })

df_summary = pd.DataFrame(summary_rows)
st.dataframe(df_summary, use_container_width=True, hide_index=True)

st.divider()

# =============================================================================
# 3. TEKİL VARLIK VE ÖNCÜ FAKTÖR DAĞILIMI
# =============================================================================
st.subheader("🔍 Varlık Detay Analizi & Öncü Faktörler")

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
    st.success(f"## {icon} {selected_asset} ── {verdict} (Öncü Göstergeler Yukarı İtiyor)")
elif "AL" in verdict:
    st.success(f"### {icon} {selected_asset} ── {verdict} (Pozitif Akış)")
elif "GÜÇLÜ SAT" in verdict:
    st.error(f"## {icon} {selected_asset} ── {verdict} (Öncü Şoklar Aşağı Bastırıyor)")
elif "SAT" in verdict:
    st.error(f"### {icon} {selected_asset} ── {verdict} (Negatif Baskı)")
elif "KRİZ" in verdict:
    st.error(f"### ⛔ {selected_asset} ── {verdict} (Piyasa Kilitli)")
else:
    st.info(f"### {icon} {selected_asset} ── {verdict} (Yönsüz / Denge)")

details = res.get("details", [])
if details:
    with st.expander(f"📋 {selected_asset} Öncü Faktör Puan Dağılımı"):
        df_det = pd.DataFrame(details)
        st.dataframe(df_det.rename(columns={
            "faktör": "Öncü Faktör Adı",
            "küme": "Küme",
            "ham_deger": "Ham Z-Score",
            "puan": "Ağırlıklı Net Puan"
        }), use_container_width=True, hide_index=True)

last_update = bg_state.get("last_updated", "Canlı Taramadan Alındı")
st.caption(f"🕒 Son Öncü Radar Taraması: `{last_update}`")
