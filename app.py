"""
Streamlit UI: Real-Time Day Trader Execution Shield (Auto-Fresh & TSİ Timezone)
"""
import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime, timezone, timedelta
from config import ASSET_MATRICES
from gatekeeper import PreTradeGatekeeper

st.set_page_config(page_title="Tier-1 Öncü Makro Radar", layout="wide", page_icon="🧭")

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

# 🛡️ 15 DAKİKALIK BAYATLIK KONTROLÜ (DAY TRADER GÜVENLİĞİ)
is_stale = False
minutes_diff = 0
if bg_state and "last_updated" in bg_state:
    try:
        last_dt = datetime.fromisoformat(bg_state["last_updated"])
        now_dt = datetime.now(timezone.utc)
        minutes_diff = int((now_dt - last_dt).total_seconds() / 60)
        if minutes_diff > 15:
            is_stale = True
    except Exception:
        is_stale = True
else:
    is_stale = True

st.title("🧭 Tier-1 Öncü Makro Şok & Piyasa Yön Terminali")
st.caption("Day Trader Koruma Zırhı — Otomatik Canlı Veri ve TSİ Zaman Damgalı")

# 🚨 EĞER VERİ 15 DAKİKADAN ESKİYSE BÜYÜK UYARI BAS
if is_stale:
    st.error(f"⚠️ **DİKKAT: Arka plan verisi {minutes_diff} dakikadır güncellenmemiş! Lütfen aşağıdaki '⚡ Canlı Verileri Yenile' butonuna basarak tazeleyin.**")

col_head1, col_head2 = st.columns([3, 1])
with col_head2:
    live_refresh = st.button("⚡ Canlı Verileri Yenile", use_container_width=True)

# Karar Motoru: Eğer canlı butonuna basıldıysa VEYA veri bayatsa CANLI ÇEK
verdicts = {}
regime = "MAKRO DENGE"
vix_val = 16.0
stagflation_z = 0.0
yen_carry_z = 0.0
crisis_active = False

if live_refresh or is_stale or not bg_state or "asset_verdicts" not in bg_state:
    with st.spinner("Piyasa verileri anlık taranıyor (Canlı Mod)..."):
        gk = PreTradeGatekeeper()
        gk.refresh_market()
        verdicts = {k: gk.evaluate_asset_direction(k) for k in ASSET_MATRICES.keys()}
        regime = getattr(gk, "market_regime", "MAKRO DENGE")
        vix_val = getattr(gk, "current_vix", 16.0)
        crisis_active = getattr(gk, "crisis_active", False)
        stagflation_z = getattr(gk, "stagflation_z", 0.0)
        yen_carry_z = getattr(gk, "yen_carry_z", 0.0)
        active_time_str = f"CANLI ({get_now_tsi_str()})"
else:
    verdicts = bg_state["asset_verdicts"]
    regime = bg_state.get("market_regime", "MAKRO DENGE")
    vix_val = bg_state.get("current_vix", 16.0)
    crisis_active = bg_state.get("crisis_state", {}).get("is_active", False)
    stagflation_z = bg_state.get("stagflation_z", 0.0)
    yen_carry_z = bg_state.get("yen_carry_z", 0.0)
    active_time_str = f"{minutes_diff} dk önce ({bg_state.get('last_updated', '')[:19]})"

# =============================================================================
# 1. 5 ÖNCÜ MAKRO RADAR GÖSTERGESİ
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
        "Küme Dağılımı": data.get("cluster_agreement", "-")
    })

df_summary = pd.DataFrame(summary_rows)
st.dataframe(df_summary, use_container_width=True, hide_index=True)

st.divider()

# =============================================================================
# 3. TEKİL VARLIK DETAY ANALİZİ
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

st.caption(f"🕒 Veri Zaman Damgası: **{active_time_str}** | Day Trader Canlı Güvenlik Modu Aktiftir.")
