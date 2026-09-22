"""
Streamlit UI: Tier-1 Normalized Macro & Confirmation Gate Terminal (v35 / V2.2)

V2.2 ENTEGRASYONU
-----------------
- Zero Synthetic Data
- No fabricated OHLCV
- No silent critical-instrument proxy substitution
- Bounded stale cache
- Real-data quality metadata
- Live multi-horizon direction
- 1H / 2H / 4H ATR-normalized impulse
- Trend persistence
- ADX + DI directional confirmation
- Separate MODEL_DIRECTION / EXECUTION_GATE
- True RVOL with current bar excluded from baseline
- Missing volume => no fabricated RVOL
- Insufficient data => execution blocked
- No 16:30 TSI freeze
- Existing XAU/XAG architecture preserved
"""

import streamlit as st
import json
import os
import pandas as pd

from datetime import (
    datetime,
    timezone,
    timedelta,
)


# =============================================================================
# CORE MODULES
# =============================================================================

from config import (
    ASSET_MATRICES,
    CLUSTERS,
    SIGNAL_THRESHOLDS,
    REGIME_DYNAMIC_THRESHOLDS,
)

from gatekeeper import PreTradeGatekeeper
from quant_processor import RobustQuantProcessor
from stateful_adaptive_controller import StatefulAdaptiveController


# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="Tier-1 Kurumsal Makro Terminali",
    layout="wide",
    page_icon="🧭",
)


# =============================================================================
# FILES / STATE
# =============================================================================

STATE_FILE = "terminal_state.json"


def safe_float(value, default=None, digits=None):
    """Convert finite numeric values safely; preserve None/NA as unavailable."""
    try:
        if value is None or pd.isna(value):
            return default
        number = float(value)
        if not pd.notna(number) or not pd.api.types.is_number(number):
            return default
        return round(number, digits) if digits is not None else number
    except (TypeError, ValueError):
        return default


def safe_bool(value, default=False):
    return bool(value) if value is not None else default


def display_optional(value, digits=2, warmup=False):
    """Display None as a semantic unavailable/warm-up marker, never as zero."""
    if value is None:
        return "WARM-UP" if warmup else "—"
    try:
        number = float(value)
        if pd.isna(number):
            return "—"
        return f"{number:+.{digits}f}"
    except (TypeError, ValueError):
        return "—"


def format_adaptive_weight_map(weight_map):
    """Render both legacy float maps and current nested multiplier maps safely."""
    if not isinstance(weight_map, dict):
        return "—"
    parts = []
    for key, node in sorted(weight_map.items()):
        if isinstance(node, dict):
            mult = node.get("multiplier")
            if mult is None:
                continue
            try:
                parts.append(f"{key}={float(mult):.3f}")
            except (TypeError, ValueError):
                continue
        else:
            try:
                parts.append(f"{key}={float(node):.3f}")
            except (TypeError, ValueError):
                continue
    return ", ".join(parts) if parts else "—"


def get_now_tsi_str():
    """
    Current Türkiye time.
    """

    now_tsi = (
        datetime.now(timezone.utc)
        + timedelta(hours=3)
    )

    return now_tsi.strftime(
        "%H:%M:%S TSİ"
    )


def load_persisted_state():
    """
    Load previous terminal state.
    """

    if os.path.exists(
        STATE_FILE
    ):

        try:

            with open(
                STATE_FILE,
                "r",
                encoding="utf-8",
            ) as f:

                return json.load(f)

        except Exception:
            pass

    return {}


def save_persisted_state(
    state
):
    """
    Persist current terminal state.
    """

    try:

        with open(
            STATE_FILE,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                state,
                f,
                ensure_ascii=False,
                indent=2,
            )

    except Exception:
        pass


# =============================================================================
# SIDEBAR
# =============================================================================

st.sidebar.header(
    "🧭 Terminal Ayarları"
)


# =============================================================================
# FRED API
# =============================================================================

default_fred = os.environ.get(
    "FRED_API_KEY",
    "",
).strip()


if not default_fred:

    try:

        default_fred = st.secrets.get(
            "FRED_API_KEY",
            "",
        ).strip()

    except Exception:

        default_fred = ""


fred_key_input = st.sidebar.text_input(
    "FRED API Key:",
    value=default_fred,
    type="password",
    help="Resmi FRED API anahtarı.",
)


if fred_key_input:

    st.sidebar.success(
        "🔑 Resmi FRED API Bağlantısı Aktif"
    )

else:

    st.sidebar.info(
        "ℹ️ FRED anahtarı girilmedi. "
        "Gerçek piyasa verileri ayrı veri motorundan alınır."
    )


# =============================================================================
# V2.2 RULES
# =============================================================================

st.sidebar.markdown("---")

st.sidebar.markdown(
    "### 🛡️ V2.2 Veri & Giriş Kuralları"
)

st.sidebar.caption(
    "• **Sentetik OHLCV:** Kesinlikle kullanılmaz.\n"
    "• **Kritik Futures:** ES=F / NQ=F / GC=F / SI=F doğrudan gerçek veri ister.\n"
    "• **STALE veri:** İşleme girişine izin verilmez.\n"
    "• **Yetersiz veri:** İşleme girişine izin verilmez.\n"
    "• **RVOL:** Mevcut bar baseline dışında hesaplanır.\n"
    "• **Volume yoksa:** Sahte RVOL oluşturulmaz.\n"
    "• **Yön:** 1H + 2H + 4H impulse, persistence ve ADX/DI ile hesaplanır.\n"
    "• **MODEL_DIRECTION ≠ EXECUTION_GATE.**"
)


st.sidebar.markdown("---")

st.sidebar.markdown(
    "### 📚 Küme (Cluster) Rehberi"
)

for code, desc in CLUSTERS.items():

    st.sidebar.caption(
        f"**Küme {code}:** {desc}"
    )


# =============================================================================
# LOAD PERSISTED STATE
# =============================================================================

persisted = load_persisted_state()

effective_fred_key = (
    fred_key_input
    or default_fred
)


# =============================================================================
# GATEKEEPER INITIALIZATION
# =============================================================================

if (
    "gatekeeper"
    not in st.session_state
):

    st.session_state.gatekeeper = (
        PreTradeGatekeeper(
            fred_api_key=effective_fred_key
        )
    )

    st.session_state.state_data = (
        persisted
    )

    st.session_state.last_sync_time = (
        persisted.get(
            "last_updated",
            None,
        )
    )


gk = st.session_state.gatekeeper


# =============================================================================
# STATEFUL ADAPTIVE CONTROLLER
# =============================================================================

if "stateful_controller" not in st.session_state:

    st.session_state.stateful_controller = (
        StatefulAdaptiveController()
    )


stateful_controller = st.session_state.stateful_controller

def _round_or_none(value, digits=2):
    try:
        return round(float(value), digits) if value is not None and pd.notna(value) else None
    except (TypeError, ValueError):
        return None



# =============================================================================
# TITLE / ACTIONS
# =============================================================================

col_title, col_btn = st.columns(
    [3, 1]
)


with col_title:

    st.title(
        "🧭 Tier-1 Kurumsal Makro Terminali & Giriş Analizi"
    )

    st.caption(
        "2019-2026 Piyasa Rejimi Kalibrasyonu | "
        "Gerçek Globex Vadeli Akışı | "
        "V2.2 Zero Synthetic Data | "
        "Çok Ufuklu Yön & Giriş Analizi"
    )


with col_btn:

    st.write("")

    live_refresh = st.button(
        "⚡ Canlı Verileri Yenile",
        use_container_width=True,
        type="primary",
    )


# =============================================================================
# DATA REFRESH
# =============================================================================

if (
    live_refresh
    or not st.session_state.state_data
    or st.session_state.state_data.get("status") == "NOT_INITIALIZED"
    or "asset_verdicts" not in st.session_state.state_data
):

    with st.spinner(
        "Gerçek piyasa verileri toplanıyor; "
        "V2.2 yön ve giriş filtreleri hesaplanıyor..."
    ):

        try:
            prev_verdicts = (
                st.session_state.state_data.get(
                    "asset_verdicts",
                    {},
                )
            )

            # ----------------------------------------------------
            # MARKET REFRESH
            # ----------------------------------------------------

            gk.refresh_market()


            # ----------------------------------------------------
            # STATEFUL ADAPTIVE PREPARATION
            # ----------------------------------------------------

            # Reconcile pending forecasts, update persistent regime state,
            # and load the latest decayed model-memory statistics before
            # calculating this cycle's asset verdicts.
            stateful_controller.prepare_cycle(gk)


            # ----------------------------------------------------
            # PREVIOUS VERDICTS
            # ----------------------------------------------------

            prev_map = {
                k: prev_verdicts.get(
                    k,
                    {},
                ).get(
                    "verdict",
                    "NÖTR (BEKLE)",
                )
                for k in ASSET_MATRICES.keys()
            }


            # ----------------------------------------------------
            # ASSET EVALUATION
            # ----------------------------------------------------

            verdicts = (
                gk.evaluate_all_assets_harmonized(
                    prev_map
                )
            )


            # ----------------------------------------------------
            # STATEFUL ADAPTIVE FINALIZATION
            # ----------------------------------------------------

            # Replace the raw deterministic verdicts with the stateful
            # adaptive score/threshold/entry results, then persist this
            # cycle as the pending observation used by future cycles.
            verdicts, adaptive_diag = stateful_controller.finalize_cycle(
                gk,
                verdicts,
                previous_signals=prev_map,
            )

            # ----------------------------------------------------
            # PAIR COHERENCE (post-adaptive)
            # ----------------------------------------------------
            # Adaptif motorlar hem "Canlı Fiyat Yönü" hem "Model Sinyali"
            # alanlarını YENİDEN YAZDIĞI için XAU/XAG ve SPX/NQ fiyat-teyit
            # uzlaştırması burada, en son (nihai) verdict'ler üzerinde tekrar
            # uygulanır. Aksi halde bu güvenlik kontrolü sessizce kaybolur.
            verdicts = gk.reconcile_pairs_post_adaptive(verdicts)


            # ----------------------------------------------------
            # MACRO STATE
            # ----------------------------------------------------

            comp_usd = safe_float(getattr(gk, "composite_usd_risk", None), digits=2)
            dxy_v = safe_float(getattr(gk, "dxy_velocity", None), digits=2)
            ndl_val = safe_float(getattr(gk, "ndl_z", None), digits=2)
            yen_carry = safe_float(getattr(gk, "yen_carry_z", None), digits=2)


            # ----------------------------------------------------
            # DATA QUALITY SNAPSHOT
            # ----------------------------------------------------

            data_quality = getattr(
                gk.data_engine,
                "data_quality",
                {},
            )

            data_sources = getattr(
                gk.data_engine,
                "data_sources",
                {},
            )


            # ----------------------------------------------------
            # CURRENT TIME
            # ----------------------------------------------------

            current_time_iso = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )


            # ----------------------------------------------------
            # NEW STATE
            # ----------------------------------------------------

            new_state = {

                "v22_version": "2.2.1",

                "last_updated":
                    current_time_iso,

                "status":
                    "OK",

                "active_regime_id":
                    getattr(
                        gk,
                        "active_macro_regime_id",
                        "REJIMSIZ_GECIS",
                    ),

                "active_regime_name":
                    getattr(
                        gk,
                        "active_macro_regime_name",
                        "Rejimsiz Geçiş / Veri Yetersiz",
                    ),

                "market_regime":
                    getattr(
                        gk,
                        "market_regime",
                        "⚪ [REJİMSİZ] Veri Yetersiz",
                    ),

                "active_subtype":
                    getattr(
                        gk,
                        "active_subtype",
                        "VERİ YETERSİZ",
                    ),

                "dynamic_thresholds":
                    getattr(
                        gk,
                        "dynamic_thresholds",
                        {},
                    ),

                "macro_diagnostics":
                    getattr(
                        gk,
                        "macro_diagnostics",
                        {},
                    ),

                "composite_usd_risk":
                    comp_usd,

                "usd_risk_label":
                    getattr(
                        gk,
                        "usd_risk_label",
                        "⚪ VERİ YETERSİZ",
                    ),

                "usd_risk_status":
                    getattr(
                        gk,
                        "usd_risk_status",
                        "UNAVAILABLE",
                    ),

                "dxy_velocity":
                    dxy_v,

                "ndl_z":
                    ndl_val,

                "current_vix": safe_float(getattr(gk, "current_vix", None), digits=1),

                "stagflation_z": safe_float(getattr(gk, "stagflation_z", None), digits=2),

                "yen_carry_z":
                    yen_carry,

                "dfii10_z": safe_float(getattr(gk, "dfii10_z", None), digits=2),

                "curve_label":
                    getattr(
                        gk,
                        "curve_label",
                        "DÜZ EĞRİ",
                    ),

                "crisis_state": {

                    "is_active":
                        getattr(
                            gk,
                            "crisis_active",
                            False,
                        ),

                    "consecutive_breaches":
                        getattr(
                            gk,
                            "consecutive_breaches",
                            0,
                        ),

                    "anomaly_score": safe_float(getattr(gk, "anomaly_score", None), digits=2),

                    "vix_floor_active":
                        bool(
                            safe_float(getattr(gk, "current_vix", None), default=999.0) < 20.0
                        ),
                },

                "data_quality":
                    data_quality,

                "data_sources":
                    data_sources,

                "asset_verdicts":
                    verdicts,

                "stateful_adaptive":
                    adaptive_diag,
            }


            # ----------------------------------------------------
            # SAVE STATE
            # ----------------------------------------------------

            st.session_state.state_data = (
                new_state
            )

            st.session_state.last_sync_time = (
                current_time_iso
            )

            save_persisted_state(
                new_state
            )
        except Exception as refresh_error:
            # Yenileme sırasında BEKLENMEDİK bir hata oluşursa artık tüm
            # sayfa çökmüyor ve önceki (son başarılı) analiz ekranda kalıyor;
            # kullanıcı 'Yenile' butonuna bastığında analizlerin birden
            # bozulduğu / çöktüğü şikayetinin ana kaynaklarından biri buydu.
            st.error(
                "⚠️ Canlı veri yenileme sırasında bir hata oluştu; "
                "önceki başarılı analiz gösterilmeye devam ediyor. "
                f"(Teknik ayrıntı: {refresh_error})"
            )
            if not st.session_state.state_data or "asset_verdicts" not in st.session_state.state_data:
                # İlk yüklemede de hata olursa en azından boş/güvenli bir
                # durumla devam et; None ile aşağıdaki kod çökmesin.
                st.session_state.state_data = persisted or {"status": "NOT_INITIALIZED"}


# =============================================================================
# ACTIVE STATE
# =============================================================================

active_data = (
    st.session_state.state_data
)

regime = active_data.get(
    "market_regime",
    "🟢 [REJİM 5] Küresel Likidite Rallisi (Risk-On)",
)

verdicts = active_data.get(
    "asset_verdicts",
    {},
)

is_crisis = (
    active_data
    .get(
        "crisis_state",
        {},
    )
    .get(
        "is_active",
        False,
    )
)


# =============================================================================
# CRISIS BANNER
# =============================================================================

if is_crisis:

    st.error(
        "🚨 **ACİL DURUM: SİSTEMİK KRİZ KİLİDİ AKTİF!** "
        "Tüm yeni pozisyonlar durduruldu."
    )


# =============================================================================
# MARKET REGIME
# =============================================================================

st.info(
    f"🌐 **Aktif Makro Rejim:** {regime}"
)


# =============================================================================
# STATEFUL ADAPTIVE SUMMARY
# =============================================================================

stateful_diag = active_data.get(
    "stateful_adaptive",
    {},
)

if stateful_diag:

    mem_diag = stateful_diag.get("memory", {})
    regime_diag = stateful_diag.get("regime", {})

    st.subheader(
        "🧠 Stateful Adaptive Motor"
    )

    stateful_cols = st.columns(5)

    with stateful_cols[0]:
        st.metric(
            "Pending Gözlem",
            int(mem_diag.get("pending_observations", 0) or 0),
        )

    with stateful_cols[1]:
        st.metric(
            "Settled Gözlem",
            int(mem_diag.get("settled_observations", 0) or 0),
        )

    with stateful_cols[2]:
        st.metric(
            "Aktif Rejim",
            str(regime_diag.get("active_regime_id", "-")),
        )

    with stateful_cols[3]:
        st.metric(
            "Aday Rejim",
            str(regime_diag.get("candidate_regime_id", "-")),
        )

    with stateful_cols[4]:
        st.metric(
            "Adaptive Pair",
            "AKTİF" if stateful_diag.get("pair_state", {}).get("available") else "BEKLEMEDE",
        )

    st.caption(
        "Online adaptasyon geçmiş gerçekleşmelerden decayed güvenilirlik öğrenir; "
        "yön tahmini artık execution gate'den bağımsızdır. EARLY/CONFIRMED state'i, "
        "score velocity/acceleration ve 1H/4H gerçekleşmeleri birlikte kullanılır."
    )


# =============================================================================
# DATA QUALITY SUMMARY
# =============================================================================

st.subheader(
    "🛡️ V2.2 Veri Kalitesi"
)

quality_map = active_data.get(
    "data_quality",
    {},
)

quality_rows = []

for symbol, quality in (
    quality_map.items()
):

    if not isinstance(
        quality,
        dict,
    ):
        continue

    quality_rows.append(
        {
            "Sembol":
                symbol,

            "Durum":
                quality.get(
                    "status",
                    "UNAVAILABLE",
                ),

            "Kaynak":
                quality.get(
                    "source",
                    "-",
                ),

            "Kaynak Türü":
                quality.get(
                    "source_type",
                    "-",
                ),

            "Gerçek Veri":
                "✅"
                if quality.get(
                    "is_real",
                    False,
                )
                else "❌",

            "Sentetik":
                "❌"
                if not quality.get(
                    "is_synthetic",
                    False,
                )
                else "🚨",

            "Son Bar Yaşı":
                (
                    f"{safe_float(quality.get('age_seconds'), default=0.0) / 60:.1f} dk"
                    if quality.get(
                        "age_seconds"
                    )
                    is not None
                    else "-"
                ),
        }
    )


if quality_rows:

    df_quality = pd.DataFrame(
        quality_rows
    )

    st.dataframe(
        df_quality,
        use_container_width=True,
        hide_index=True,
    )

else:

    st.caption(
        "ℹ️ Henüz canlı veri kalite kaydı oluşmadı. "
        "Yenile butonuna basın."
    )


st.divider()


# =============================================================================
# 1. LIVE DIRECTION / SIGNAL / ENTRY TABLE
# =============================================================================

st.subheader(
    "📊 1. Canlı Yön, Sinyal & İşleme Giriş Analizi Tablosu"
)


summary_rows = []


for k in ASSET_MATRICES.keys():

    data = verdicts.get(
        k,
        {},
    )

    curr_dir = data.get(
        "current_direction",
        "⚪ VERİ YETERSİZ",
    )

    fore_dir = (
        f"{data.get('icon', '⚪')} "
        f"{data.get('verdict', 'NÖTR (BEKLE)')}"
    )

    entry_st = data.get(
        "entry_status",
        "🔴 İŞLEME GİRİŞ ÖNERİLMEZ",
    )

    entry_rs = data.get(
        "entry_reason",
        "Veri yeterliliği kontrol edilemedi.",
    )

    rvol_val = safe_float(data.get("rvol"), default=None)
    atr_val = safe_float(data.get("atr_ratio"), default=None)

    score_val = float(
        data.get(
            "score",
            0.0,
        )
        or 0.0
    )

    direction_stage = data.get("direction_stage", data.get("direction_state", "NEUTRAL"))
    direction_velocity = safe_float(data.get("direction_velocity"), default=None)
    direction_acceleration = safe_float(data.get("direction_acceleration"), default=None)
    direction_persistence = int(data.get("direction_persistence", 0) or 0)

    intraday_regime = data.get("intraday_regime", {}) or {}
    intraday_regime_label = intraday_regime.get("label", "—")
    if data.get("live_regime_event"):
        intraday_regime_label = f"⚠️ {intraday_regime_label} (yeni)"


    summary_rows.append(
        {

            "Varlık":
                k,

            "Ad":
                ASSET_MATRICES[k][
                    "name"
                ],

            "📍 Canlı Fiyat Yönü (1-4 Saat)":
                curr_dir,

            "Gün-içi Rejim":
                intraday_regime_label,

            "🔮 Model Sinyali (24 Saat-1 Hafta)":
                fore_dir,

            "Yön Aşaması":
                direction_stage,

            "Yön Hızı":
                (f"{direction_velocity:+.3f}/saat" if direction_velocity is not None else "—"),

            "Yön Kalıcılığı":
                str(direction_persistence),

            "🛡️ Giriş Analizi":
                entry_st,

            "Giriş Gerekçesi":
                entry_rs,

            "Hacim (RVOL)":
                (f"{rvol_val:.2f}x" if rvol_val is not None else "—"),

            "Volatilite (ATR)":
                (f"{atr_val:.2f}x" if atr_val is not None else "—"),

            "Model Skoru":
                ("VERİ YETERSİZ" if str(data.get("factor_data_status", "")).upper() == "INSUFFICIENT_DATA" else f"{score_val:+.2f}"),
        }
    )


df_summary = pd.DataFrame(
    summary_rows
)


st.dataframe(
    df_summary,
    use_container_width=True,
    hide_index=True,
)


st.caption(
    "💡 **İki Ayrı Ufuk:** 📍 *Canlı Fiyat Yönü* günün gün-içi rejimine "
    "(trend gücü + volatilite) göre kalibre edilmiş **1-4 saatlik** olası yönü; "
    "🔮 *Model Sinyali* haftalık/aylık makro rejime göre kalibre edilmiş "
    "**24 saat-1 haftalık** olası yönü gösterir. Her iki motor da kendi eşiklerini "
    "geçmiş skor dağılımından (yüzdelik dilim) dinamik olarak günceller; rejim "
    "değişimi anında (⚠️ işareti) eşikler geçici olarak genişletilerek yanlış "
    "sinyal riski azaltılır. **Stateful Direction v3.1:** Model yönü execution "
    "gate'den bağımsızdır; EARLY/CONFIRMED aşaması dynamic threshold + score "
    "velocity/acceleration + cluster persistence ile hesaplanır. İşleme giriş ise "
    "gerçek veri, veri tazeliği, ATR ve gerçek RVOL koşullarını ayrıca kontrol eder."
)


st.divider()


# =============================================================================
# 2. SINGLE ASSET DEEP ANALYSIS
# =============================================================================

st.subheader(
    "🔍 2. Varlık Derinlik, Giriş Gerekçesi & Faktör Dağılımı"
)


selected_asset = st.selectbox(
    "Detayını İncelemek İstediğiniz Varlık:",
    list(
        ASSET_MATRICES.keys()
    ),
    format_func=lambda x:
        f"{x} ── "
        f"{ASSET_MATRICES[x]['name']}",
)


res = verdicts.get(
    selected_asset,
    {},
)


verdict = res.get(
    "verdict",
    "NÖTR (BEKLE)",
)

icon = res.get(
    "icon",
    "⚪",
)

score = safe_float(res.get("score"), default=0.0)
if score is None:
    score = 0.0
score_data_status = str(res.get("factor_data_status", "")).upper()
score_display = "VERİ YETERSİZ" if score_data_status == "INSUFFICIENT_DATA" else f"{score:+.2f}"

curr_dir = res.get(
    "current_direction",
    "⚪ VERİ YETERSİZ",
)

direction_stage = res.get("direction_stage", "NEUTRAL")
direction_reason = res.get("direction_reason", "")
direction_z = safe_float(res.get("direction_score_z"), default=None)
direction_velocity = safe_float(res.get("direction_velocity"), default=None)
direction_acceleration = safe_float(res.get("direction_acceleration"), default=None)
direction_persistence = int(res.get("direction_persistence", 0) or 0)
direction_warmup = bool(res.get("direction_warmup", res.get("direction_state") == "NEUTRAL" and res.get("direction_runtime_n", 0) < 5))

entry_st = res.get(
    "entry_status",
    "🔴 İŞLEME GİRİŞ ÖNERİLMEZ",
)

entry_rs = res.get(
    "entry_reason",
    "",
)

info_cols = st.columns(5)
with info_cols[0]:
    st.metric("Yön Aşaması", direction_stage)
with info_cols[1]:
    st.metric("Score Z", display_optional(direction_z, 2, warmup=direction_z is None))
with info_cols[2]:
    st.metric("Velocity", display_optional(direction_velocity, 3, warmup=direction_velocity is None))
with info_cols[3]:
    st.metric("Acceleration", display_optional(direction_acceleration, 3, warmup=direction_acceleration is None))
with info_cols[4]:
    st.metric("Persistence", str(direction_persistence))

if direction_reason:
    st.caption(f"🧭 Yön gerekçesi (Model Sinyali, 24s-1h ufuk): {direction_reason}")

intraday_regime = res.get("intraday_regime", {}) or {}
if intraday_regime.get("label"):
    event_note = " — ⚠️ **rejim az önce değişti**, eşikler geçici genişletildi" if res.get("live_regime_event") else ""
    st.caption(
        f"🕒 Gün-içi rejim (Canlı Fiyat Yönü, 1-4s ufuk): "
        f"**{intraday_regime.get('label')}**{event_note}"
    )

rvol_val = safe_float(res.get("rvol"), default=None)
atr_val = safe_float(res.get("atr_ratio"), default=None)


# =============================================================================
# ASSET CARD
# =============================================================================

col_card1, col_card2 = st.columns(
    [2, 1]
)


with col_card1:

    st.markdown(
        f"#### 📍 Canlı Fiyat Durumu (1-4 Saat Olası Yön): **{curr_dir}**"
    )


    if (
        "GÜÇLÜ"
        in verdict
    ):

        st.success(
            f"### 🔮 Nihai Teyitli Sinyal: "
            f"**{icon} {verdict}**"
        )

    elif (
        "AL"
        in verdict
    ):

        st.success(
            f"### 🔮 Model Yönü: "
            f"**{icon} {verdict}**"
        )

    elif (
        "SAT"
        in verdict
    ):

        st.error(
            f"### 🔮 Model Yönü: "
            f"**{icon} {verdict}**"
        )

    else:

        st.info(
            f"### 🔮 Model Yönü: "
            f"**{icon} {verdict}**"
        )


    if (
        "ÖNERİLMEZ"
        in entry_st
    ):

        st.warning(
            f"⚠️ **Giriş Filtresi:** "
            f"{entry_rs}"
        )

    else:

        st.success(
            f"✅ **Giriş Filtresi:** "
            f"{entry_rs}"
        )


with col_card2:

    st.metric(
        label=(
            f"{selected_asset} "
            "Normalleştirilmiş Skor"
        ),

        value=(
            score_display
        ),

        delta=(
            f"Hacim: {(f'{rvol_val:.2f}x' if rvol_val is not None else '—')} | "
            f"ATR: {(f'{atr_val:.2f}x' if atr_val is not None else '—')}"
        ),
    )


# =============================================================================
# FACTOR DETAILS
# =============================================================================

details = res.get(
    "details",
    [],
)


if details:

    with st.expander(
        f"📋 {selected_asset} "
        "Çok Faktörlü Risk & Getiri Dağılım Tablosu",
        expanded=True,
    ):

        df_det = pd.DataFrame(
            details
        )


        st.dataframe(
            df_det.rename(
                columns={
                    "faktör":
                        "Faktör Adı",

                    "küme":
                        "Küme",

                    "ham_deger":
                        "Ham Değer (σ / ROC)",

                    "puan":
                        "Puan Katkısı",

                    "veri_durumu":
                        "Veri Durumu",

                    "veri_kaynagi":
                        "Veri Kaynağı",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    adaptive_weights = res.get("adaptive_factor_weights", {})
    adaptive_thresholds = res.get("adaptive_thresholds", {})

    if adaptive_weights:
        st.caption(
            "🧠 Adaptive factor ağırlıkları: "
            + format_adaptive_weight_map(adaptive_weights)
        )

    if adaptive_thresholds:
        numeric_thresholds = []
        for k, v in sorted(adaptive_thresholds.items()):
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                numeric_thresholds.append(f"{k}={float(v):.3f}")
        st.caption(
            "🎚️ Stateful adaptive eşikleri: "
            + (", ".join(numeric_thresholds) if numeric_thresholds else "—")
        )

    data_cov = safe_float(res.get("factor_data_coverage"), default=None)
    if data_cov is not None:
        st.caption(
            f"📐 Model veri kapsamı: {data_cov * 100:.0f}% | "
            f"durum: {res.get('factor_data_status', '—')}"
        )


# =============================================================================
# V2.2 FOOTER
# =============================================================================

st.divider()

st.caption(
    "V2.2.1 + Stateful Adaptive v3.1 | Zero Synthetic Data | "
    "Live Multi-Horizon Direction | "
    "Strict Execution Gate | "
    "Real RVOL | "
    "No 16:30 TSI Freeze"
)
