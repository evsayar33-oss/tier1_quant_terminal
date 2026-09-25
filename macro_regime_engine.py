"""
Macro Event Interpretation System (v1.0)
Rule-based deterministic engine for classifying global macro regimes.
Enhanced with:
- Direct Fallback to REJIMSIZ_GECIS (No forced Risk-On hysteresis on neutral days)
- Multi-Key Source Mapping (No fabricated numeric fallback)
- Priority Rules: SHOCK_REGIMES (1, 2, 3, 4) > RISK_ON_REGIME (5) > REJIMSIZ_GECIS
- Conflict Resolution: Highest |Z| & T10YIE Breakeven Tie-Breaker
"""
import os
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from config import MACRO_EVENT_SYSTEM_SPEC, REGIME_DYNAMIC_THRESHOLDS
from adaptive_regime_thresholds import AdaptiveThresholdStore, default_store


class MacroRegimeEngine:
    def __init__(self, fred_api_key=None, *args, **kwargs):
        self.spec = MACRO_EVENT_SYSTEM_SPEC
        # Self-improving trigger calibration: every evaluate() call adds one
        # more real observation per indicator, and shock/risk-on thresholds
        # below are a shrinkage blend of the indicator's own recency-weighted
        # empirical quantile and the original literal (used as-is until
        # enough history accrues). See adaptive_regime_thresholds.py.
        self.threshold_store: AdaptiveThresholdStore = kwargs.get("threshold_store") or default_store()
        # Başlangıçta yapay ralli yerine gerçekçi olarak Nötr Denge ile başla
        self.confirmed_regime_id: Any = "REJIMSIZ_GECIS"
        self.candidate_regime_id: Optional[Any] = None
        self.consecutive_candidate_hits: int = 0
        self.hysteresis_confirmation_weeks: int = 2
        self.last_evaluation_time: Optional[str] = None
        self.fred_api_key = fred_api_key or os.environ.get("FRED_API_KEY", "").strip()

    def evaluate(self, macro_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates current macro indicators against the 5 regimes using deterministic logic,
        strict priority rules, conflict resolution, and objective regime fallback.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        self.last_evaluation_time = now_iso

        # -------------------------------------------------------------
        # 1. MAKRO VERİLERİN GÜVENLİ ÇEKİLMESİ
        # -------------------------------------------------------------
        def num(*keys):
            for key in keys:
                value = macro_data.get(key)
                try:
                    value = float(value)
                    if np.isfinite(value):
                        return value
                except (TypeError, ValueError):
                    pass
            return np.nan

        oil_20d_z = num("oil_20d_return_52w_z", "oil_20d_z", "oil_z")
        bdi_level_z = num("bdi_level_52w_z", "bdi_level_z", "bdi_z")
        hy_oas_z = num("hy_oas_52w_z", "hy_oas_z", "hy_z")
        spx_ust_corr = num("spx_ust10y_60d_corr", "spx_ust_corr")
        dtwexbgs_5d_z = num("dtwexbgs_5d_change_52w_z", "dtwexbgs_5d_z", "dxy_velocity_z")
        dtwexbgs_level_z = num("dtwexbgs_level_52w_z", "dtwexbgs_level_z", "dtwexbgs_5d_z")
        usdjpy_1d_z = num("usdjpy_1d_change_52w_z", "usdjpy_1d_z", "yen_carry_z")
        vix_level_z = num("vix_level_52w_z", "vix_level_z", "z_vix")
        vix_pct = num("vix_252d_percentile")
        risk_basket_5d_z = num("risk_basket_5d_return_52w_z", "risk_basket_5d_z", "risk_basket_z")
        dfii10_1d_z = num("dfii10_1d_change_52w_z", "dfii10_z")
        t10yie_z = num("t10yie_52w_z", "t10yie_z")
        dgs2_change = num("dgs2_change")
        dgs10_change = num("dgs10_change")
        hy_oas_slope = num("hy_oas_10d_slope", "hy_oas_slope")
        ig_oas_z = num("ig_oas_52w_z", "ig_oas_z")
        ndl_z = num("ndl_52w_z", "ndl_z")
        gold_trend = str(macro_data.get("gold_trend", "UNAVAILABLE")).upper()

        z_scores_dict = {
            "OIL_20D_Z": None if not np.isfinite(oil_20d_z) else round(oil_20d_z, 2),
            "BDI_LEVEL_Z": None if not np.isfinite(bdi_level_z) else round(bdi_level_z, 2),
            "HY_OAS_Z": None if not np.isfinite(hy_oas_z) else round(hy_oas_z, 2),
            "SPX_UST_CORR": None if not np.isfinite(spx_ust_corr) else round(spx_ust_corr, 2),
            "DTWEXBGS_5D_Z": None if not np.isfinite(dtwexbgs_5d_z) else round(dtwexbgs_5d_z, 2),
            "DTWEXBGS_LEVEL_Z": None if not np.isfinite(dtwexbgs_level_z) else round(dtwexbgs_level_z, 2),
            "USDJPY_1D_Z": None if not np.isfinite(usdjpy_1d_z) else round(usdjpy_1d_z, 2),
            "VIX_LEVEL_Z": None if not np.isfinite(vix_level_z) else round(vix_level_z, 2),
            "VIX_PERCENTILE": None if not np.isfinite(vix_pct) else round(vix_pct, 1),
            "RISK_BASKET_5D_Z": None if not np.isfinite(risk_basket_5d_z) else round(risk_basket_5d_z, 2),
            "DFII10_1D_Z": None if not np.isfinite(dfii10_1d_z) else round(dfii10_1d_z, 2),
            "T10YIE_Z": None if not np.isfinite(t10yie_z) else round(t10yie_z, 2),
            "HY_OAS_SLOPE": None if not np.isfinite(hy_oas_slope) else round(hy_oas_slope, 4),
            "IG_OAS_Z": None if not np.isfinite(ig_oas_z) else round(ig_oas_z, 2),
            "NDL_Z": None if not np.isfinite(ndl_z) else round(ndl_z, 2)
        }

        # Feed today's real, already-computed z-scores into the adaptive
        # threshold store. This is the ONLY place trigger calibration
        # learns from -- no synthetic or forward-filled values ever enter it.
        for _key, _val in z_scores_dict.items():
            self.threshold_store.update(_key, _val)

        def th(indicator_key: str, quantile: float, fallback_value: float) -> float:
            return self.threshold_store.get_threshold(indicator_key, quantile, fallback_value)

        # -------------------------------------------------------------
        # 2. 5 REJİMİN AYRI AYRI DEĞERLENDİRİLMESİ
        # -------------------------------------------------------------
        triggered_regimes = {}

        # REGIME 1: Küresel Enflasyon & Stagflasyon Şoku (SHOCK)
        # Thresholds below adapt to each indicator's own trailing
        # distribution (see th()); literals are only the cold-start prior.
        r1_triggers_met = (oil_20d_z > th("OIL_20D_Z", 0.90, 1.5)) and (bdi_level_z < th("BDI_LEVEL_Z", 0.15, -1.0))
        r1_confirmations_met = (hy_oas_z > th("HY_OAS_Z", 0.65, 0.5)) and (spx_ust_corr > 0.0)
        r1_active = r1_triggers_met and r1_confirmations_met
        if r1_active:
            triggered_regimes[1] = {
                "id": 1,
                "name": "Küresel Enflasyon & Stagflasyon Şoku",
                "type": "SHOCK",
                "main_trigger_z": abs(oil_20d_z),
                "main_trigger_name": "Petrol Şoku",
                "sub_type": "Stagflasyon Şoku (Petrol & Navlun)"
            }

        # REGIME 2: Sistemik Likidite Şoku & Carry Çöküşü (SHOCK)
        r2_t1 = (dtwexbgs_5d_z > th("DTWEXBGS_5D_Z", 0.85, 1.0))
        r2_t2 = (usdjpy_1d_z < th("USDJPY_1D_Z", 0.03, -2.0))
        r2_t3 = (vix_level_z > th("VIX_LEVEL_Z", 0.90, 1.5))
        r2_triggers_met = (r2_t1 or r2_t2 or r2_t3)
        r2_confirmations_met = (risk_basket_5d_z < th("RISK_BASKET_5D_Z", 0.08, -1.5))
        r2_active = r2_triggers_met and r2_confirmations_met
        if r2_active:
            trigger_candidates = []
            if r2_t1: trigger_candidates.append((abs(dtwexbgs_5d_z), "Geniş Dolar"))
            if r2_t2: trigger_candidates.append((abs(usdjpy_1d_z), "JPY Carry Unwind"))
            if r2_t3: trigger_candidates.append((abs(vix_level_z), "Volatilite Şoku"))
            best_r2_z, best_r2_name = max(trigger_candidates, key=lambda x: x[0])
            triggered_regimes[2] = {
                "id": 2,
                "name": "Sistemik Likidite Şoku & Carry Çöküşü",
                "type": "SHOCK",
                "main_trigger_z": best_r2_z,
                "main_trigger_name": best_r2_name,
                "sub_type": f"Likidite Çöküşü ({best_r2_name})"
            }

        # REGIME 3: Reel Faiz Şoku (SHOCK)
        r3_t1 = (dfii10_1d_z > th("DFII10_1D_Z", 0.90, 1.5))
        r3_t2 = (t10yie_z < th("T10YIE_Z", 0.60, 0.5))
        r3_triggers_met = r3_t1 and r3_t2
        if r3_triggers_met:
            if dgs2_change < 0 and dgs10_change > 0:
                sub_label = "Bear Steepener (Enflasyon/Term Premium)"
            elif dgs2_change > 0 and dgs10_change > 0 and dgs10_change > dgs2_change:
                sub_label = "Bear Steepener (Fed Varyantı)"
            elif dgs2_change > 0 and dgs10_change > 0 and dgs2_change > dgs10_change:
                sub_label = "Bear Flattener (Fed Sıkılaştırma Baskın)"
            elif dgs2_change < 0 and dgs10_change < 0:
                sub_label = "Bull Flattener/Steepener (Gevşeme - Tetiklemez)"
                r3_triggers_met = False
            else:
                sub_label = "Genel Reel Faiz Şoku"

            if r3_triggers_met:
                triggered_regimes[3] = {
                    "id": 3,
                    "name": "Reel Faiz Şoku",
                    "type": "SHOCK",
                    "main_trigger_z": abs(dfii10_1d_z),
                    "main_trigger_name": "Reel Faiz (DFII10)",
                    "sub_type": sub_label
                }

        # REGIME 4: Kredi Temerrüt Baskısı (SHOCK)
        r4_t1 = (hy_oas_z > th("HY_OAS_Z", 0.95, 2.0))
        r4_t2 = (hy_oas_slope > 0.0)
        r4_triggers_met = r4_t1 and r4_t2
        r4_confirmations_met = (ig_oas_z > th("IG_OAS_Z", 0.85, 1.0))
        r4_active = r4_triggers_met and r4_confirmations_met
        if r4_active:
            triggered_regimes[4] = {
                "id": 4,
                "name": "Kredi Temerrüt Baskısı",
                "type": "SHOCK",
                "main_trigger_z": abs(hy_oas_z),
                "main_trigger_name": "HY OAS Spread",
                "sub_type": "Kredi Temerrüt & Spread Genişlemesi"
            }

        # REGIME 5: Küresel Likidite Rallisi (Risk-On)
        r5_c1 = (hy_oas_z < th("HY_OAS_Z", 0.35, -0.5))
        r5_c2 = (-1.0 <= dtwexbgs_level_z <= 0.5)
        r5_c3 = (vix_pct < 30.0)
        r5_c4 = (ndl_z > 0.0)
        r5_triggers_met = r5_c1 and r5_c2 and r5_c3 and r5_c4
        if r5_triggers_met:
            if dtwexbgs_level_z < -0.5 and gold_trend == "RISING":
                sub_label = "Reflasyonist Risk-On (Zayıf Dolar + Değerli Maden Rallisi)"
            else:
                sub_label = "Klasik Goldilocks Risk-On (Düşük Volatilite + İstikrarlı Likidite)"
            triggered_regimes[5] = {
                "id": 5,
                "name": "Küresel Likidite Rallisi (Risk-On)",
                "type": "RISK_ON",
                "main_trigger_z": abs(ndl_z),
                "main_trigger_name": "Net Likidite",
                "sub_type": sub_label
            }

        # -------------------------------------------------------------
        # 3. ÖNCELİK KURALLARI & REJİMSİZ GEÇİŞ TAYİNİ
        # -------------------------------------------------------------
        shock_keys = [k for k in triggered_regimes.keys() if triggered_regimes[k]["type"] == "SHOCK"]
        selected_candidate_id: Optional[Any] = None
        conflict_explanation = ""

        if len(shock_keys) > 0:
            if len(shock_keys) == 1:
                selected_candidate_id = shock_keys[0]
                conflict_explanation = f"Tekil Şok Rejimi Tetiklendi: Rejim {selected_candidate_id}"
            else:
                if (1 in shock_keys) and (3 in shock_keys) and len(shock_keys) == 2:
                    if t10yie_z > 0.5:
                        selected_candidate_id = 1
                        conflict_explanation = f"Özel Kural: Rejim 1 vs Rejim 3 (T10YIE 52w_Z = {t10yie_z:+.2f} > +0.5 -> Rejim 1 Seçildi)"
                    else:
                        selected_candidate_id = 3
                        conflict_explanation = f"Özel Kural: Rejim 1 vs Rejim 3 (T10YIE 52w_Z = {t10yie_z:+.2f} <= +0.5 -> Rejim 3 Seçildi)"
                else:
                    best_shock = max(shock_keys, key=lambda k: triggered_regimes[k]["main_trigger_z"])
                    selected_candidate_id = best_shock
                    shocks_summary = ", ".join([f"R{k}: |Z|={triggered_regimes[k]['main_trigger_z']:.2f}" for k in shock_keys])
                    conflict_explanation = f"Çoklu Şok Çatışma Çözümü (En Yüksek |Z|): {shocks_summary} -> Rejim {best_shock} Seçildi"
        elif 5 in triggered_regimes:
            selected_candidate_id = 5
            conflict_explanation = "Likidite Rallisi Koşulları Karşılandı (Risk-On)"
        else:
            # HİÇBİR EŞİK AŞILMADIĞINDA DOĞRUDAN REJİMSİZ GEÇİŞ'E GEÇ
            selected_candidate_id = "REJIMSIZ_GECIS"
            conflict_explanation = "Hiçbir eşik aşılmadı: REJIMSIZ_GECIS (Makro Denge & Sıkışma Rejimi Aktif)"

        # -------------------------------------------------------------
        # 4. HİSTEREZİS & AKTİF REJİM SEÇİMİ
        # -------------------------------------------------------------
        is_confirmed = False
        if selected_candidate_id in [1, 2, 3, 4, 5]:
            if selected_candidate_id == self.candidate_regime_id:
                self.consecutive_candidate_hits += 1
            else:
                self.candidate_regime_id = selected_candidate_id
                self.consecutive_candidate_hits = 1

            if self.consecutive_candidate_hits >= self.hysteresis_confirmation_weeks:
                self.confirmed_regime_id = selected_candidate_id
                active_id = selected_candidate_id
                is_confirmed = True
            else:
                active_id = selected_candidate_id
                is_confirmed = False
        else:
            # Eşik aşılmadığında inatla eski rejimi tutma, şeffaf biçimde REJİMSİZ GEÇİŞ'i göster
            self.candidate_regime_id = None
            self.consecutive_candidate_hits = 0
            self.confirmed_regime_id = "REJIMSIZ_GECIS"
            active_id = "REJIMSIZ_GECIS"
            is_confirmed = True

        regime_meta = triggered_regimes.get(active_id)
        if not regime_meta:
            regime_names = {
                1: ("Küresel Enflasyon & Stagflasyon Şoku", "SHOCK", "Enflasyon Baskısı"),
                2: ("Sistemik Likidite Şoku & Carry Çöküşü", "SHOCK", "Likidite Daralması"),
                3: ("Reel Faiz Şoku", "SHOCK", "Değerleme / Getiri Şoku"),
                4: ("Kredi Temerrüt Baskısı", "SHOCK", "Spread Genişlemesi"),
                5: ("Küresel Likidite Rallisi (Risk-On)", "RISK_ON", "Klasik Goldilocks Risk-On"),
                "REJIMSIZ_GECIS": ("Rejimsiz Geçiş (Makro Denge / Sıkışma)", "DENGE / SIKIŞMA", "Yönsüz Piyasa & Denge Bandı")
            }
            name, r_type, sub = regime_names.get(active_id, ("Rejimsiz Geçiş / Makro Denge", "DENGE", "Yönsüz Sıkışma"))
            regime_meta = {
                "id": active_id,
                "name": name,
                "type": r_type,
                "sub_type": sub,
                "main_trigger_name": "Eşikler Nötr",
                "main_trigger_z": 0.0
            }

        active_key = active_id if active_id in REGIME_DYNAMIC_THRESHOLDS else "REJIMSIZ_GECIS"
        thresholds = REGIME_DYNAMIC_THRESHOLDS.get(active_key, REGIME_DYNAMIC_THRESHOLDS["REJIMSIZ_GECIS"])

        icons = {
            1: "🛢️",
            2: "🚨",
            3: "⚡",
            4: "⚠️",
            5: "🟢",
            "REJIMSIZ_GECIS": "⚪"
        }
        reg_icon = icons.get(active_id, "⚪")

        if active_id == "REJIMSIZ_GECIS":
            formatted_label = f"{reg_icon} [REJİMSİZ GEÇİŞ] {regime_meta['name']}"
        else:
            formatted_label = f"{reg_icon} [REJİM {active_id}] {regime_meta['name']}"

        available_count = sum(v is not None for v in z_scores_dict.values())
        result = {
            "version": "2.2",
            "data_status": "OK" if available_count >= 8 else "PARTIAL",
            "available_indicator_count": available_count,

            "module_name": "macro-event-interpretation-system",
            "timestamp": now_iso,
            "active_regime_id": active_id,
            "active_regime_name": regime_meta["name"],
            "active_regime_type": regime_meta["type"],
            "active_regime_subtype": regime_meta["sub_type"],
            "formatted_label": formatted_label,
            "is_confirmed": is_confirmed,
            "candidate_regime_id": selected_candidate_id,
            "consecutive_hits": self.consecutive_candidate_hits,
            "hysteresis_confirmation_weeks": self.hysteresis_confirmation_weeks,
            "conflict_explanation": conflict_explanation,
            "triggered_regimes": list(triggered_regimes.keys()),
            "dynamic_thresholds": thresholds,
            "indicator_z_scores": z_scores_dict,
            "raw_triggers": {
                "r1_triggers_met": r1_triggers_met,
                "r1_confirmations_met": r1_confirmations_met,
                "r2_triggers_met": r2_triggers_met,
                "r2_confirmations_met": r2_confirmations_met,
                "r3_triggers_met": r3_triggers_met,
                "r4_triggers_met": r4_triggers_met,
                "r4_confirmations_met": r4_confirmations_met,
                "r5_triggers_met": r5_triggers_met
            }
        }
        self.threshold_store.save()
        return result
