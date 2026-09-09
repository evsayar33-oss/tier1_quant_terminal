"""
Streamlit UI: 3-Second Pre-Trade Fundamental Confirmation Gate
"""
import streamlit as st
from config import ASSET_MATRICES
from gatekeeper import PreTradeGatekeeper

st.set_page_config(page_title="Tier-1 Quant Confirmation Gate", layout="wide", page_icon="🛡️")

@st.cache_resource
def get_gatekeeper():
    gk = PreTradeGatekeeper()
    gk.refresh_market()
    return gk

gatekeeper = get_gatekeeper()

# Üst Bilgi
st.title("🛡️ Tier-1 Quant Confirmation Gate")
st.caption("İşlem Öncesi Temel Analiz & Makro Doğrulama Kapısı (Day Trading Execution Shield)")

# Kontrol Paneli
col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    selected_asset = st.selectbox("İşlem Yapılacak Varlık:", list(ASSET_MATRICES.keys()), format_func=lambda x: f"{x} - {ASSET_MATRICES[x]['name']}")

with col2:
    trader_intent = st.radio("Teknik Analiz Yönün:", ["LONG", "SHORT"], horizontal=True)

with col3:
    st.write("")
    if st.button("🔄 Verileri Yenile"):
        gatekeeper.refresh_market()
        st.rerun()

st.divider()

# Onay Kapısı Çıktısı
res = gatekeeper.evaluate_asset_gate(selected_asset, trader_intent)
verdict = res["verdict"]
color = res["color"]

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
    st.metric("📊 Nihai Doğrulama Skoru", f"{res['score']:+.2f}")
with m2:
    st.metric("🏛️ Bağımsız Küme Teyidi", res["cluster_agreement"])
with m3:
    st.metric("🔒 Veri Güven / Tazelik", f"%{res['confidence']}")
with m4:
    st.metric("⚠️ Sistemik Anomali Skoru", f"{res['anomaly_score']:.2f}", delta="Kriz Kilidi" if gatekeeper.crisis_active else "Piyasa Normal", delta_color="inverse")

st.divider()

# Detaylı Katman Durumu
with st.expander("🔍 Katman Detayları ve Açıklamalar"):
    st.write(f"**Varlık:** {ASSET_MATRICES[selected_asset]['name']}")
    st.write(f"**Planlanan Yön:** {trader_intent}")
    st.write("**Aktif Kriz Durumu:**", "🚨 KİLİTLİ" if gatekeeper.crisis_active else "✅ NORMAL")
    st.write("**Küme Dağılımı:** A: Likidite | B: Faiz/Getiri | C: Kredi/Dolar | D: Mikroyapı")
    st.info("💡 Kural: Bir işleme tam güvenle girmek için en az 3 bağımsız kümenin teknik analizinle aynı yönde olması ve kriz kilidinin kapalı olması gerekir.")
