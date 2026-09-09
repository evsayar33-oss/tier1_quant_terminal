"""
Streamlit UI: 3-Second Pre-Trade Confirmation Gate (Memory-Connected)
"""
import streamlit as st
import json
import os
from config import ASSET_MATRICES
from gatekeeper import PreTradeGatekeeper

st.set_page_config(page_title="Tier-1 Quant Confirmation Gate", layout="wide", page_icon="🛡️")

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

st.title("🛡️ Tier-1 Quant Confirmation Gate")
st.caption("İşlem Öncesi Temel Analiz & Makro Doğrulama Kapısı (Arka Plan Hafıza Bağlantılı)")

# Kontrol Paneli
col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    selected_asset = st.selectbox(
        "İşlem Yapılacak Varlık:",
        list(ASSET_MATRICES.keys()),
        format_func=lambda x: f"{x} - {ASSET_MATRICES[x]['name']}"
    )

with col2:
    trader_intent = st.radio("Teknik Analiz Yönün:", ["LONG", "SHORT"], horizontal=True)

with col3:
    st.write("")
    live_refresh = st.button("⚡ Canlı Veri Yenile")

st.divider()

# Karar Motoru: Arka planda hazır hesaplanmış veri var mı?
res = None
if not live_refresh and bg_state and "asset_verdicts" in bg_state:
    asset_data = bg_state["asset_verdicts"].get(selected_asset, {})
    res = asset_data.get(trader_intent)

# Eğer canlı yenileme tıklandıysa veya state henüz boşsa canlı hesapla
if res is None or live_refresh:
    with st.spinner("Piyasa verileri canlı taranıyor..."):
        gk = PreTradeGatekeeper()
        gk.refresh_market()
        res = gk.evaluate_asset_gate(selected_asset, trader_intent)
        crisis_active = gk.crisis_active
else:
    crisis_active = bg_state.get("crisis_state", {}).get("is_active", False)

verdict = res["verdict"]

# 3 SANİYELİK BÜYÜK KARAR ROZETİ
if verdict == "ONAYLA":
    st.success(f"### 🟢 {verdict} — Temel & Makro Akış {trader_intent} Yönünü Destekliyor!")
elif verdict == "ZAYIF ONAY":
    st.warning(f"### 🟡 {verdict} — Yön Uyumlu Ancak Güven/Küme Sınırda (Pozisyon Boyutunu Düşürün)")
elif verdict == "ONAYLAMA":
    st.error(f"### 🟠 {verdict} — Temel Analiz Teknik Kurgunuzla Çelişiyor (İşleme Girmeyin)")
else: # KRİZ-DUR
    st.error(f"### ⛔ {verdict} — KREDİ & VOLATİLİTE KRİZİ! Piyasada Tüm İşlemler Durduruldu!")

st.write("")

# 4 Temel Metrik Kartı
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("📊 Doğrulama Skoru", f"{res['score']:+.2f}")
with m2:
    st.metric("🏛️ Bağımsız Küme Teyidi", res["cluster_agreement"])
with m3:
    st.metric("🔒 Veri Güven Oranı", f"%{res['confidence']}")
with m4:
    st.metric(
        "⚠️ Sistemik Anomali",
        f"{res['anomaly_score']:.2f}",
        delta="🚨 Kriz Devrede" if crisis_active else "✅ Normal",
        delta_color="inverse"
    )

st.divider()

# Alt Bilgi / Zaman Damgası
last_update = bg_state.get("last_updated", "Canlı Taramadan Alındı")
st.caption(f"🕒 Son Arka Plan Denetimi: `{last_update}` | Arka planda 7/24 hafıza takibi aktiftir.")
