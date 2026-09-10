"""
Macro Event Interpretation System (v1.0)
Rule-based deterministic engine for classifying global macro regimes.
Enhanced with:
- Direct Fallback to REJIMSIZ_GECIS (No forced Risk-On hysteresis on neutral days)
- Multi-Key Fallback Mapping (Guarantees zero-loss indicator bridging from data_engine)
- Priority Rules: SHOCK_REGIMES (1, 2, 3, 4) > RISK_ON_REGIME (5) > REJIMSIZ_GECIS
- Conflict Resolution: Highest |Z| & T10YIE Breakeven Tie-Breaker
"""
import os
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from config import MACRO_EVENT_SYSTEM_SPEC, REGIME_DYNAMIC_THRESHOLDS


class MacroRegimeEngine:
    def __init__(self, fred_api_key=None, *args, **kwargs):
        self.spec = MACRO_EVENT_SYSTEM_SPEC
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
        oil_20d_z = float(macro_data.get("oil_20d_return_52w_z", macro_data.get("oil_20d_z", macro_data.get("oil_z", 0.15))))
        bdi_level_z = float(macro_data.get("bdi_level_52w_z", macro_data.get("bdi_level_z", macro_data.get("bdi_z", -0.10))))
        hy_oas_z = float(macro_data.get("hy_oas_52w_z", macro_data.get("hy_oas_z", macro_data.get("hy_z", 0.20))))
        spx_ust_corr = float(macro_data.get("spx_ust10y_60d_corr", macro_data.get("spx_ust_corr", -0.20)))
        dtwexbgs_5d_z = float(macro_data.get("dtwexbgs_5d_change_52w_z", macro_data.get("dtwexbgs_5d_z", macro_data.get("dxy_velocity_z", macro_data.get("dxy_velocity", 0.10)))))
        dtwexbgs_level_z = float(macro_data.get("dtwexbgs_level_52w_z", macro_data.get("dtwexbgs_level_z", dtwexbgs_5d_z)))
        usdjpy_1d_z = float(macro_data.get("usdjpy_1d_change_52w_z", macro_data.get("usdjpy_1d_z", macro_data.get("yen_carry_z", 0.05))))
        vix_level_z = float(macro_data.get("vix_level_52w_z", macro_data.get("vix_level_z", macro_data.get("z_vix", 0.15))))
        vix_pct = float(macro_data.get("vix_252d_percentile", 42.0))
        risk_basket_5d_z = float(macro_data.get("risk_basket_5d_return_52w_z", macro_data.get("risk_basket_5d_z", macro_data.get("risk_basket_z", 0.10))))
        dfii10_1d_z = float(macro_data.get("dfii10_1d_change_52w_z", macro_data.get("dfii10_z", 0.45)))
        t10yie_z = float(macro_data.get("t10yie_52w_z", macro_data.get("t10yie_z", 0.65)))
        dgs2_change = float(macro_data.get("dgs2_change", 0.0))
        dgs10_change = float(macro_data.get("dgs10_change", 0.0))
        hy_oas_slope = float(macro_data.get("hy_oas_10d_slope", macro_data.get("hy_oas_slope", 0.005)))
        ig_oas_z = float(macro_data.get("ig_oas_52w_z", macro_data.get("ig_oas_z", 0.15)))
        ndl_z = float(macro_data.get("ndl_52w_z", macro_data.get("ndl_z", 0.25)))
        gold_trend = str(macro_data.get("gold_trend", "FLAT_OR_FALLING")).upper()

        z_scores_dict = {
            "OIL_20D_Z": round(oil_20d_z, 2),
            "BDI_LEVEL_Z": round(bdi_level_z, 2),
            "HY_OAS_Z": round(hy_oas_z, 2),
            "SPX_UST_CORR": round(spx_ust_corr, 2),
            "DTWEXBGS_5D_Z": round(dtwexbgs_5d_z, 2),
            "DTWEXBGS_LEVEL_Z": round(dtwexbgs_level_z, 2),
            "USDJPY_1D_Z": round(usdjpy_1d_z, 2),
            "VIX_LEVEL_Z": round(vix_level_z, 2),
            "VIX_PERCENTILE": round(vix_pct, 1),
            "RISK_BASKET_5D_Z": round(risk_basket_5d_z, 2),
            "DFII10_1D_Z": round(dfii10_1d_z, 2),
            "T10YIE_Z": round(t10yie_z, 2),
            "HY_OAS_SLOPE": round(hy_oas_slope, 4),
            "IG_OAS_Z": round(ig_oas_z, 2),
            "NDL_Z": round(ndl_z, 2)
        }

        # -------------------------------------------------------------
        # 2. 5 REJİMİN AYRI AYRI DEĞERLENDİRİLMESİ
        # -------------------------------------------------------------
        triggered_regimes = {}

        # REGIME 1: Küresel Enflasyon & Stagflasyon Şoku (SHOCK)
        r1_triggers_met = (oil_20d_z > 1.5) and (bdi_level_z < -1.0)
        r1_confirmations_met = (hy_oas_z > 0.5) and (spx_ust_corr > 0.0)
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
        r2_t1 = (dtwexbgs_5d_z > 1.0)
        r2_t2 = (usdjpy_1d_z < -2.0)
        r2_t3 = (vix_level_z > 1.5)
        r2_triggers_met = (r2_t1 or r2_t2 or r2_t3)
        r2_confirmations_met = (risk_basket_5d_z < -1.5)
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
        r3_t1 = (dfii10_1d_z > 1.5)
        r3_t2 = (t10yie_z < 0.5)
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
        r4_t1 = (hy_oas_z > 2.0)
        r4_t2 = (hy_oas_slope > 0.0)
        r4_triggers_met = r4_t1 and r4_t2
        r4_confirmations_met = (ig_oas_z > 1.0)
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
        r5_c1 = (hy_oas_z < -0.5)
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

        result = {
            "version": "1.0",
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
        return result
