"""
Macro Event Interpretation System (v1.0)
Module Name: macro-event-interpretation-system
Deterministic Macro Regime Classification with 52-Week Rolling Z-Score Normalization,
2-Week Hysteresis Confirmation, Strict Priority & Conflict Resolution Rules.

Implements:
- Regime 1: Küresel Enflasyon & Stagflasyon Şoku (SHOCK)
- Regime 2: Sistemik Likidite Şoku & Carry Çöküşü (SHOCK)
- Regime 3: Reel Faiz Şoku (SHOCK) (with Bear Steepener / Bear Flattener sub-types)
- Regime 4: Kredi Temerrüt Baskısı (SHOCK)
- Regime 5: Küresel Likidite Rallisi (Risk-On) (with Reflationist / Goldilocks sub-types)
- Fallback: REJIMSIZ_GECIS (retaining previous confirmed regime via hysteresis)
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, Optional
from datetime import datetime, timezone

from config import MACRO_EVENT_SYSTEM_SPEC, REGIME_DYNAMIC_THRESHOLDS


class MacroRegimeEngine:
    """
    Deterministic Macro Event Interpretation Engine (v1.0)
    Principles:
    - mutual_exclusivity: True (Only 1 active regime at any time)
    - active_regime_count: 1
    - normalization: 52_week_rolling_z_score (252 trading days)
    - hysteresis_confirmation_period_weeks: 2
    - scoring_type: deterministic
    """

    def __init__(self, fred_api_key: Optional[str] = None):
        self.fred_api_key = fred_api_key
        self.confirmed_regime_id: int = 5  # Default initialization (e.g. Risk-On baseline)
        self.candidate_regime_id: Optional[int] = None
        self.consecutive_candidate_hits: int = 0
        self.hysteresis_confirmation_weeks: int = 2
        self.last_evaluation_time: Optional[str] = None
        self.history = []

    def compute_52w_zscore(self, series: pd.Series, window: int = 252) -> float:
        """Computes 52-week (252 trading days) rolling Z-Score of the latest value."""
        if series is None or len(series) < 2:
            return 0.0
        w = min(len(series), window)
        rolling_series = series.iloc[-w:]
        mean_val = float(rolling_series.mean())
        std_val = float(rolling_series.std())
        if std_val < 1e-9:
            return 0.0
        latest_val = float(series.iloc[-1])
        z = (latest_val - mean_val) / std_val
        return float(np.clip(z, -3.5, 3.5))

    def compute_rolling_slope(self, series: pd.Series, window: int = 10) -> float:
        """Computes rolling linear regression slope over specified window."""
        if series is None or len(series) < 3:
            return 0.0
        w = min(len(series), window)
        vals = series.iloc[-w:].values
        x = np.arange(len(vals))
        slope, _ = np.polyfit(x, vals, 1)
        return float(slope)

    def compute_rolling_correlation(self, s1: pd.Series, s2: pd.Series, window: int = 60) -> float:
        """Computes 60-day rolling correlation between two return series."""
        if s1 is None or s2 is None or len(s1) < 5 or len(s2) < 5:
            return 0.0
        aligned = pd.concat([s1, s2], axis=1, join="inner").dropna()
        if len(aligned) < 5:
            return 0.0
        w = min(len(aligned), window)
        corr = aligned.iloc[-w:, 0].corr(aligned.iloc[-w:, 1])
        return 0.0 if np.isnan(corr) else float(corr)

    def compute_percentile(self, series: pd.Series, window: int = 252) -> float:
        """Computes rolling percentile rank of latest value within 252 days."""
        if series is None or len(series) < 2:
            return 50.0
        w = min(len(series), window)
        vals = series.iloc[-w:].values
        cur = vals[-1]
        pct = (np.sum(vals <= cur) / len(vals)) * 100.0
        return float(pct)

    def evaluate(self, macro_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates current macro indicators against the 5 regimes using deterministic logic,
        strict priority rules, conflict resolution, and 2-week hysteresis.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        self.last_evaluation_time = now_iso

        # Extract or calculate Z-scores from incoming macro_data
        # Indicators:
        # 1. Oil 20-day return 52w Z-score
        oil_20d_z = float(macro_data.get("oil_20d_return_52w_z", macro_data.get("oil_z", 0.0)))
        # 2. Baltic Dry Index (BDI) level 52w Z-score
        bdi_level_z = float(macro_data.get("bdi_level_52w_z", macro_data.get("bdi_z", 0.0)))
        # 3. HY OAS 52w Z-score
        hy_oas_z = float(macro_data.get("hy_oas_52w_z", macro_data.get("hy_z", 0.0)))
        # 4. SPX & UST10Y 60-day return correlation
        spx_ust_corr = float(macro_data.get("spx_ust10y_60d_corr", macro_data.get("spx_ust_corr", 0.0)))
        # 5. DTWEXBGS 5-day change 52w Z-score
        dtwexbgs_5d_z = float(macro_data.get("dtwexbgs_5d_change_52w_z", macro_data.get("dxy_velocity_z", 0.0)))
        # 6. DTWEXBGS level 52w Z-score
        dtwexbgs_level_z = float(macro_data.get("dtwexbgs_level_52w_z", dtwexbgs_5d_z))
        # 7. USD/JPY 1-day change 52w Z-score
        usdjpy_1d_z = float(macro_data.get("usdjpy_1d_change_52w_z", macro_data.get("yen_carry_z", 0.0)))
        # 8. VIX level 52w Z-score
        vix_level_z = float(macro_data.get("vix_level_52w_z", macro_data.get("z_vix", 0.0)))
        # 9. VIX 252-day percentile rank
        vix_pct = float(macro_data.get("vix_252d_percentile", 45.0))
        # 10. Risk Asset Basket (SPX + BTC) 5-day return 52w Z-score
        risk_basket_5d_z = float(macro_data.get("risk_basket_5d_return_52w_z", -0.5))
        # 11. DFII10 1-day change 52w Z-score
        dfii10_1d_z = float(macro_data.get("dfii10_1d_change_52w_z", macro_data.get("dfii10_z", 0.45)))
        # 12. T10YIE 52w Z-score
        t10yie_z = float(macro_data.get("t10yie_52w_z", macro_data.get("t10yie_z", 0.65)))
        # 13. DGS2 & DGS10 changes
        dgs2_change = float(macro_data.get("dgs2_change", 0.0))
        dgs10_change = float(macro_data.get("dgs10_change", 0.0))
        # 14. HY OAS 10-day slope
        hy_oas_slope = float(macro_data.get("hy_oas_10d_slope", 0.0))
        # 15. IG OAS level 52w Z-score
        ig_oas_z = float(macro_data.get("ig_oas_52w_z", 0.5))
        # 16. Net Dollar Liquidity (NDL) 52w Z-score
        ndl_z = float(macro_data.get("ndl_52w_z", 0.2))
        # 17. Gold trend status
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
        # EVALUATE 5 REGIMES INDIVIDUALLY
        # -------------------------------------------------------------
        triggered_regimes = {}

        # REGIME 1: Küresel Enflasyon & Stagflasyon Şoku (SHOCK)
        # Triggers (AND): Oil Z > 1.5 AND BDI Z < -1.0
        # Confirmations (AND): HY OAS Z > 0.5 AND SPX/UST Corr > 0
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
                "sub_type": "Enflasyon / Tedarik Zinciri Baskısı",
                "triggers_met": r1_triggers_met,
                "confirmations_met": r1_confirmations_met
            }

        # REGIME 2: Sistemik Likidite Şoku & Carry Çöküşü (SHOCK)
        # Triggers (OR): DTWEXBGS 5d Z > 1.0 OR USDJPY 1d Z < -2.0 OR VIX Z > 1.5
        # Confirmations (AND): Risk Basket 5d Z < -1.5
        r2_triggers_met = (dtwexbgs_5d_z > 1.0) or (usdjpy_1d_z < -2.0) or (vix_level_z > 1.5)
        r2_confirmations_met = (risk_basket_5d_z < -1.5)
        r2_active = r2_triggers_met and r2_confirmations_met
        if r2_active:
            # Main trigger indicator is the one with highest absolute z-score
            candidates = [
                ("Geniş Dolar Gücü", abs(dtwexbgs_5d_z)),
                ("JPY Carry Unwind", abs(usdjpy_1d_z)),
                ("Volatilite Şoku", abs(vix_level_z))
            ]
            best_trig_name, best_trig_z = max(candidates, key=lambda x: x[1])
            triggered_regimes[2] = {
                "id": 2,
                "name": "Sistemik Likidite Şoku & Carry Çöküşü",
                "type": "SHOCK",
                "main_trigger_z": best_trig_z,
                "main_trigger_name": best_trig_name,
                "sub_type": "Kaldıraç Azaltma & Nakde Kaçış",
                "triggers_met": r2_triggers_met,
                "confirmations_met": r2_confirmations_met
            }

        # REGIME 3: Reel Faiz Şoku (SHOCK)
        # Triggers (AND): DFII10 1d Z > 1.5 AND T10YIE Z < 0.5
        r3_triggers_met = (dfii10_1d_z > 1.5) and (t10yie_z < 0.5)
        r3_confirmations_met = True  # No explicit secondary confirmation required in schema
        r3_active = r3_triggers_met
        if r3_active:
            # Determine yield curve sub-type
            # 1. Bear Steepener (Enflasyon/Term Premium): ΔDGS2 < 0 AND ΔDGS10 > 0
            # 2. Bear Steepener (Fed Varyantı): ΔDGS2 > 0 AND ΔDGS10 > 0 AND ΔDGS10 > ΔDGS2
            # 3. Bear Flattener (Fed Sıkılaştırma Baskın): ΔDGS2 > 0 AND ΔDGS10 > 0 AND ΔDGS2 > ΔDGS10
            # 4. Bull Flattener/Steepener (Gevşeme - Tetiklemez): ΔDGS2 < 0 AND ΔDGS10 < 0
            if dgs2_change < 0 and dgs10_change > 0:
                sub_type = "Bear Steepener (Enflasyon / Term Premium)"
            elif dgs2_change > 0 and dgs10_change > 0 and dgs10_change > dgs2_change:
                sub_type = "Bear Steepener (Fed Varyantı)"
            elif dgs2_change > 0 and dgs10_change > 0 and dgs2_change > dgs10_change:
                sub_type = "Bear Flattener (Fed Sıkılaştırma Baskın)"
            elif dgs2_change < 0 and dgs10_change < 0:
                sub_type = "Bull Eğri (Gevşeme)"
            else:
                sub_type = "Bear Flattener (Genel Sıkılaşma)"

            triggered_regimes[3] = {
                "id": 3,
                "name": "Reel Faiz Şoku",
                "type": "SHOCK",
                "main_trigger_z": abs(dfii10_1d_z),
                "main_trigger_name": "Ana Tetikleyici (10Y TIPS Reel Faiz)",
                "sub_type": sub_type,
                "triggers_met": r3_triggers_met,
                "confirmations_met": r3_confirmations_met
            }

        # REGIME 4: Kredi Temerrüt Baskısı (SHOCK)
        # Triggers (AND): HY OAS Z > 2.0 AND HY OAS Slope > 0
        # Confirmations (AND): IG OAS Z > 1.0
        r4_triggers_met = (hy_oas_z > 2.0) and (hy_oas_slope > 0)
        r4_confirmations_met = (ig_oas_z > 1.0)
        r4_active = r4_triggers_met and r4_confirmations_met
        if r4_active:
            triggered_regimes[4] = {
                "id": 4,
                "name": "Kredi Temerrüt Baskısı",
                "type": "SHOCK",
                "main_trigger_z": abs(hy_oas_z),
                "main_trigger_name": "Yüksek Getirili Spread (HY OAS)",
                "sub_type": "Kredi Bulaşması & Spread Genişlemesi",
                "triggers_met": r4_triggers_met,
                "confirmations_met": r4_confirmations_met
            }

        # REGIME 5: Küresel Likidite Rallisi (Risk-On) (RISK_ON)
        # Triggers (AND): HY OAS Z < -0.5 AND -1.0 <= DTWEXBGS Z <= 0.5 AND VIX pct < 30 AND NDL Z > 0
        r5_triggers_met = (
            (hy_oas_z < -0.5) and
            (-1.0 <= dtwexbgs_level_z <= 0.5) and
            (vix_pct < 30.0) and
            (ndl_z > 0.0)
        )
        r5_confirmations_met = True
        r5_active = r5_triggers_met
        if r5_active:
            # Sub-types post-hoc:
            # - Reflasyonist Risk-On: DTWEXBGS_Z < -0.5 AND Gold_Price == RISING
            # - Klasik Goldilocks Risk-On: -1.0 <= DTWEXBGS_Z <= 0.5 AND Gold_Price == FLAT_OR_FALLING
            if dtwexbgs_level_z < -0.5 and "RIS" in gold_trend:
                sub_type = "Reflasyonist Risk-On (Zayıf Dolar + Emtia Gücü)"
            else:
                sub_type = "Klasik Goldilocks Risk-On (Dengeli Dolar + Düşük Volatilite)"

            triggered_regimes[5] = {
                "id": 5,
                "name": "Küresel Likidite Rallisi (Risk-On)",
                "type": "RISK_ON",
                "main_trigger_z": abs(ndl_z),
                "main_trigger_name": "Net Dolar Likiditesi (NDL)",
                "sub_type": sub_type,
                "triggers_met": r5_triggers_met,
                "confirmations_met": r5_confirmations_met
            }

        # -------------------------------------------------------------
        # PRIORITY RULES & CONFLICT RESOLUTION
        # -------------------------------------------------------------
        selected_candidate_id: Optional[int] = None
        conflict_explanation: str = "Doğrudan Tetiklendi"
        shock_keys = [k for k in triggered_regimes.keys() if triggered_regimes[k]["type"] == "SHOCK"]

        # Rule 1: Category Priority: SHOCK_REGIMES (1, 2, 3, 4) > RISK_ON_REGIME (5)
        if shock_keys:
            # Multiple shocks triggered?
            if len(shock_keys) == 1:
                selected_candidate_id = shock_keys[0]
                conflict_explanation = f"Tek aktif şok rejimi: Rejim {selected_candidate_id}"
            else:
                # Special conflict case: Regime 1 vs Regime 3
                if set(shock_keys) == {1, 3}:
                    if t10yie_z > 0.5:
                        selected_candidate_id = 1
                        conflict_explanation = f"Özel Kural: Rejim 1 vs Rejim 3 (T10YIE 52w_Z = {t10yie_z:+.2f} > +0.5 -> Rejim 1 Seçildi)"
                    else:
                        selected_candidate_id = 3
                        conflict_explanation = f"Özel Kural: Rejim 1 vs Rejim 3 (T10YIE 52w_Z = {t10yie_z:+.2f} <= +0.5 -> Rejim 3 Seçildi)"
                else:
                    # General conflict resolution:
                    # "IF multiple shock regimes trigger, select the regime with the highest absolute Z-score of its main trigger indicator."
                    best_shock = max(shock_keys, key=lambda k: triggered_regimes[k]["main_trigger_z"])
                    selected_candidate_id = best_shock
                    shocks_summary = ", ".join([f"R{k}: |Z|={triggered_regimes[k]['main_trigger_z']:.2f}" for k in shock_keys])
                    conflict_explanation = f"Çoklu Şok Çatışma Çözümü (En Yüksek |Z|): {shocks_summary} -> Rejim {best_shock} Seçildi"
        elif 5 in triggered_regimes:
            selected_candidate_id = 5
            conflict_explanation = "Likidite Rallisi Koşulları Karşılandı (Risk-On)"
        else:
            # Fallback Rule:
            # "IF no threshold is met THEN state = 'REJIMSIZ_GECIS' AND retain previous confirmed regime (hysteresis)."
            selected_candidate_id = None
            conflict_explanation = "Hiçbir eşik aşılmadı: REJIMSIZ_GECIS (Önceki teyitli rejim histerezis ile korunuyor)"

        # -------------------------------------------------------------
        # HYSTERESIS CONFIRMATION ENGINE (2-WEEK PERIOD)
        # -------------------------------------------------------------
        is_confirmed = False
        if selected_candidate_id is not None:
            if selected_candidate_id == self.candidate_regime_id:
                self.consecutive_candidate_hits += 1
            else:
                self.candidate_regime_id = selected_candidate_id
                self.consecutive_candidate_hits = 1

            # Check 2-week hysteresis threshold
            if self.consecutive_candidate_hits >= self.hysteresis_confirmation_weeks:
                self.confirmed_regime_id = selected_candidate_id
                is_confirmed = True
            else:
                is_confirmed = False
        else:
            # Fallback state
            self.candidate_regime_id = None
            self.consecutive_candidate_hits = 0
            is_confirmed = True  # Retains confirmed_regime_id smoothly

        # Final Active Regime Determination
        # When unconfirmed, active operational regime stays at confirmed_regime_id
        active_id = self.confirmed_regime_id if (selected_candidate_id is None or not is_confirmed) else selected_candidate_id

        # Look up regime metadata
        regime_meta = triggered_regimes.get(active_id)
        if not regime_meta:
            regime_names = {
                1: ("Küresel Enflasyon & Stagflasyon Şoku", "SHOCK", "Enflasyon Baskısı"),
                2: ("Sistemik Likidite Şoku & Carry Çöküşü", "SHOCK", "Likidite Daralması"),
                3: ("Reel Faiz Şoku", "SHOCK", "Değerleme / Getiri Şoku"),
                4: ("Kredi Temerrüt Baskısı", "SHOCK", "Spread Genişlemesi"),
                5: ("Küresel Likidite Rallisi (Risk-On)", "RISK_ON", "Klasik Goldilocks Risk-On")
            }
            name, r_type, sub = regime_names.get(active_id, ("REJIMSIZ_GECIS", "TRANSITION", "Denge"))
            regime_meta = {
                "id": active_id,
                "name": name,
                "type": r_type,
                "sub_type": sub,
                "main_trigger_name": "-",
                "main_trigger_z": 0.0
            }

        # Active Dynamic Thresholds
        active_key = active_id if active_id in REGIME_DYNAMIC_THRESHOLDS else "REJIMSIZ_GECIS"
        thresholds = REGIME_DYNAMIC_THRESHOLDS.get(active_key, REGIME_DYNAMIC_THRESHOLDS["REJIMSIZ_GECIS"])

        # Icon and label formatting
        icons = {
            1: "🛢️",
            2: "🚨",
            3: "⚡",
            4: "⚠️",
            5: "🟢",
            "REJIMSIZ_GECIS": "⚪"
        }
        reg_icon = icons.get(active_id, "⚪")
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

        self.history.append({
            "timestamp": now_iso,
            "regime_id": active_id,
            "name": regime_meta["name"]
        })

        return result
