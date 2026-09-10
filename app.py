"""
Streamlit UI: Tier-1 Normalized Macro & Confirmation Gate Terminal (v19)
"""
import streamlit as st
import json
import os
import sys
import importlib
import pandas as pd
from datetime import datetime, timezone, timedelta

# Streamlit Cloud üzerinde modül önbellek çakışmalarını önlemek için dinamik reload
import config
import quant_processor
import data_engine
import gatekeeper

importlib.reload(config)
importlib.reload(quant_processor)
importlib.reload(data_engine)
importlib.reload(gatekeeper)

from config import ASSET_MATRICES, CLUSTERS, SIGNAL_THRESHOLDS
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
# 🔑 YAN PANEL (AYARLAR VE VERİ DURUMU)
# =============================================================================
st.sidebar.header("🧭 Terminal Ayarları")
fred_key_input = st.sidebar.text_input(
    "FRED API Key (İsteğe Bağlı):",
    type="password",
    help="St. Louis Fed resmi API anahtarınız varsa buraya ekleyebilirsiniz. Boş bırakılırsa ETF proxy'leri (TIP/IEF) kullanılır."
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📚 Küme (Cluster) Rehberi")
for code, desc in CLUSTERS.items():
    st.sidebar.caption(f"**Küme {code}:** {desc}")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🛡️ Sinyal Eşikleri")
st.sidebar.caption(f"🟢 **GÜÇLÜ AL:** ≥ +{SIGNAL_THRESHOLDS['strong_buy_enter']} (Onay: +{SIGNAL_THRESHOLDS['strong_buy_exit']})")
st.sidebar.caption(f"🟢 **AL:** ≥ +{SIGNAL_THRESHOLDS['buy_enter']} (Ölü Bant: +{SIGNAL_THRESHOLDS['buy_exit']})")
st.sidebar.caption(f"🔴 **SAT:** ≤ {SIGNAL_THRESHOLDS['sell_enter']} (Ölü Bant: {SIGNAL_THRESHOLDS['sell_exit']})")
st.sidebar.caption(f"🔴 **GÜÇLÜ SAT:** ≤ {SIGNAL_THRESHOLDS['strong_sell_enter']} (Onay: {SIGNAL_THRESHOLDS['strong_sell_exit']})")


# =============================================================================
# 🚀 DURUM VE VERİ YÖNETİMİ (SESSION STATE - CRASH PROOF)
# =============================================================================
persisted = load_persisted_state()

def create_gatekeeper_safe(api_key=None):
    try:
        return PreTradeGatekeeper(fred_api_key=api_key)
    except TypeError:
        try:
            gk_fallback = PreTradeGatekeeper()
            if hasattr(gk_fallback, "data_engine") and hasattr(gk_fallback.data_engine, "fred_api_key"):
                gk_fallback.data_engine.fred_api_key = api_key
            return gk_fallback
        except Exception:
            return PreTradeGatekeeper()

if "gatekeeper" not in st.session_state:
    st.session_state.gatekeeper = create_gatekeeper_safe(fred_key_input)
    st.session_state.state_data = persisted
    st.session_state.last_sync_time = persisted.get("last_updated", None)

gk = st.session_state.gatekeeper
if fred_key_input and hasattr(gk, "data_engine"):
    gk.data_engine.fred_api_key = fred_key_input


# =============================================================================
# 🧭 BAŞLIK VE ÜST AKSİYONLAR
# =============================================================================
col_title, col_btn = st.columns([3, 1])
with col_title:
    st.title("🧭 Tier-1 Öncü Makro Şok & Piyasa Yön Terminali")
    st.caption("Barra Normalizasyonlu, Volatilite Ölçekli & Histerezis Korumalı Gün İçi Risk Kapısı")

with col_btn:
    st.write("")
    live_refresh = st.button("⚡ Canlı Verileri Yenile", use_container_width=True, type="primary")


# Canlı yenileme tetiklendiğinde veya ilk kurulumda veri yoksa
if live_refresh or not st.session_state.state_data:
    with st.spinner("Piyasa verileri toplanıyor ve Barra risk modelleri hesaplanıyor..."):
        prev_verdicts = st.session_state.state_data.get("asset_verdicts", {})
        gk.refresh_market()

        prev_map = {k: prev_verdicts.get(k, {}).get("verdict", "NÖTR (BEKLE)") for k in ASSET_MATRICES.keys()}
        if hasattr(gk, "evaluate_all_assets_harmonized"):
            verdicts = gk.evaluate_all_assets_harmonized(prev_map)
        else:
            verdicts = {k: gk.evaluate_asset_direction(k, previous_signal=prev_map[k]) for k in ASSET_MATRICES.keys()}

        current_time_iso = datetime.now(timezone.utc).isoformat()
        new_state = {
            "last_updated": current_time_iso,
            "market_regime": getattr(gk, "market_regime", "MAKRO DENGE / SIKIŞMA"),
            "current_vix": round(getattr(gk, "current_vix", 16.0), 1),
            "stagflation_z": round(getattr(gk, "stagflation_z", 0.0), 2),
            "yen_carry_z": round(getattr(gk, "yen_carry_z", 0.0), 2),
            "dfii10_z": round(getattr(gk, "dfii10_z", 0.45), 2),
            "curve_label": getattr(gk, "curve_label", "DÜZ EĞRİ"),
            "crisis_state": {
                "is_active": getattr(gk, "crisis_active", False),
                "consecutive_breaches": getattr(gk, "consecutive_breaches", 0),
                "anomaly_score": round(getattr(gk, "anomaly_score", 0.0), 2),
                "vix_floor_active": bool(getattr(gk, "current_vix", 16.0) < 20.0)
            },
            "asset_verdicts": verdicts
        }
        st.session_state.state_data = new_state
        st.session_state.last_sync_time = current_time_iso
        save_persisted_state(new_state)


# Aktif Durum Değişkenleri
active_data = st.session_state.state_data
regime = active_data.get("market_regime", "MAKRO DENGE / SIKIŞMA")
vix_val = float(active_data.get("current_vix", 16.0))
stagflation_z = float(active_data.get("stagflation_z", 0.0))
yen_carry_z = float(active_data.get("yen_carry_z", 0.0))
crisis_info = active_data.get("crisis_state", {})
is_crisis = crisis_info.get("is_active", False)
verdicts = active_data.get("asset_verdicts", {})

# Haber / Katalizör Penceresi Kontrolü
is_catalyst, catalyst_desc = RobustQuantProcessor.check_catalyst_event_window()

# =============================================================================
# 🚨 UYARI VE GÜVENLİK BİLDİRİMLERİ
# =============================================================================
if is_crisis:
    st.error(
        f"🚨 **ACİL DURUM: SİSTEMİK KRİZ KİLİDİ AKTİF!** (Anomali: `{crisis_info.get('anomaly_score', 0.0):.2f}`, VIX: `{vix_val:.1f}`)\n\n"
        "Kredi spreadleri veya volatilite kriz eşiklerini aştı. Tüm varlıklarda yeni işlem açılışları askıya alındı!"
    )

if is_catalyst:
    st.warning(f"⚠️ **KRİTİK HABER PENCERESİ:** Şu anda `{catalyst_desc}` zaman dilimindesiniz. Ani volatilite sıçramalarına dikkat ediniz.")


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
st.subheader("📊 6 Varlık Canlı Yön Tablosu (Barra Normalleştirilmiş: [-3.5, +3.5])")

summary_rows = []
for k in ASSET_MATRICES.keys():
    data = verdicts.get(k, {})
    curr_dir = data.get("current_direction")
    if not curr_dir:
        details = data.get("details", [])
        f_dir = next((d for d in details if "Fiyat Hızı" in d.get("faktör", "") or "Fiyat İvmesi" in d.get("faktör", "")), None)
        if f_dir:
            ham = float(f_dir.get("ham_deger", 0.0))
            if ham >= 0.35:
                curr_dir = f"🟢 YUKARI (%{ham:+.2f})"
            elif ham <= -0.35:
                curr_dir = f"🔴 AŞAĞI (%{ham:+.2f})"
            else:
                curr_dir = f"⚪ YATAY / NÖTR (%{ham:+.2f})"
        else:
            curr_dir = "⚪ YATAY / NÖTR (%0.00)"

    fore_dir = f"{data.get('icon', '⚪')} {data.get('verdict', 'NÖTR (BEKLE)')}"

    summary_rows.append({
        "Varlık": k,
        "Ad": ASSET_MATRICES[k]["name"],
        "📍 Şu Anki Yön (Canlı Fiyat)": curr_dir,
        "🔮 Olası Gelecek Yön (Model)": fore_dir,
        "Model Skoru": f"{float(data.get('score', 0.0)):+.2f}",
        "Seans Durumu": data.get("session_status", "CANLI"),
        "Küme Onayı": data.get("cluster_agreement", "-")
    })

df_summary = pd.DataFrame(summary_rows)
st.dataframe(df_summary, use_container_width=True, hide_index=True)

st.caption(
    "💡 **Çift Ufuk Kılavuzu:** **📍 Şu Anki Yön**, grafikte anlık gördüğünüz 4 saatlik fiyat hareketidir. "
    "**🔮 Olası Gelecek Yön**, kurumsal likidite, fonlama, tahvil getirileri ve makro faktörlerin önümüzdeki seans/saatler için öngördüğü istatistiksel baskıdır."
)

st.divider()


# =============================================================================
# 🔍 3. TEKİL VARLIK VE FAKTÖR DAĞILIMI
# =============================================================================
st.subheader("🔍 Varlık Derinlik ve Faktör Analizi")

selected_asset = st.selectbox(
    "Detayını İncelemek İstediğiniz Varlık:",
    list(ASSET_MATRICES.keys()),
    format_func=lambda x: f"{x} ── {ASSET_MATRICES[x]['name']}"
)

res = verdicts.get(selected_asset, {})
verdict = res.get("verdict", "NÖTR (BEKLE)")
icon = res.get("icon", "⚪")
score = float(res.get("score", 0.0))

# Varlık Sinyal Kartı
col_card1, col_card2 = st.columns([2, 1])
with col_card1:
    curr_dir = res.get("current_direction")
    if not curr_dir:
        details = res.get("details", [])
        f_dir = next((d for d in details if "Fiyat Hızı" in d.get("faktör", "") or "Fiyat İvmesi" in d.get("faktör", "")), None)
        if f_dir:
            ham = float(f_dir.get("ham_deger", 0.0))
            curr_dir = f"🟢 YUKARI (%{ham:+.2f})" if ham >= 0.35 else (f"🔴 AŞAĞI (%{ham:+.2f})" if ham <= -0.35 else f"⚪ YATAY / NÖTR (%{ham:+.2f})")
        else:
            curr_dir = "⚪ YATAY / NÖTR (%0.00)"

    st.markdown(f"#### 📍 Şu Anki Fiyat Durumu: **{curr_dir}**")
    if "GÜÇLÜ AL" in verdict:
        st.success(f"### 🔮 Olası Gelecek Yön (Öncü Model): **{icon} {verdict}** (Kararlı Kurumsal Alış Akışı)")
    elif "AL" in verdict:
        st.success(f"### 🔮 Olası Gelecek Yön (Öncü Model): **{icon} {verdict}** (Pozitif İtici Güç)")
    elif "GÜÇLÜ SAT" in verdict:
        st.error(f"### 🔮 Olası Gelecek Yön (Öncü Model): **{icon} {verdict}** (Kararlı Satış Baskısı)")
    elif "SAT" in verdict:
        st.error(f"### 🔮 Olası Gelecek Yön (Öncü Model): **{icon} {verdict}** (Negatif Makro Baskı)")
    elif "KRİZ" in verdict:
        st.error(f"### ⛔ Olası Gelecek Yön (Öncü Model): **{icon} {verdict}** (Piyasa Kilitli)")
    else:
        st.info(f"### 🔮 Olası Gelecek Yön (Öncü Model): **{icon} {verdict}** (Denge / Yönsüz Ölü Bant)")

with col_card2:
    st.metric(
        label=f"{selected_asset} Normalleştirilmiş Skor",
        value=f"{score:+.2f}",
        delta=f"Volatilite Çarpanı: x{ASSET_MATRICES[selected_asset].get('vol_scale', 1.0)}"
    )

adx_val = res.get('adx_val', 22.0)
adx_regime = res.get('adx_regime', 'DENGELİ')
st.caption(
    f"🕒 Seans: **{res.get('session_status', 'CANLI')}** | "
    f"🎯 Trend Gücü: **ADX {adx_val} ({adx_regime})** | "
    f"Küme Uyumu: **{res.get('cluster_agreement', '-')}** | "
    f"Son Tarama: **{get_now_tsi_str()}**"
)

# Faktör Dağılım Tablosu
details = res.get("details", [])
if details:
    with st.expander(f"📋 {selected_asset} Faktör Dağılım Tablosu ({len(details)} Faktör)", expanded=True):
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
