"""
Gatekeeper: Multi-Asset Engine with Macro Event Interpretation System v1.0 & Strict Barra Normalization (v24)
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

from config import ASSET_MATRICES, CLUSTERS, REGIME_DYNAMIC_THRESHOLDS
from data_engine import ResilientDataEngine
from quant_processor import RobustQuantProcessor
from macro_regime_engine import MacroRegimeEngine


class PreTradeGatekeeper:
    def __init__(self, fred_api_key=None, *args, **kwargs):
        if not fred_api_key and "fred_api_key" in kwargs:
            fred_api_key = kwargs["fred_api_key"]
        self.data_engine = ResilientDataEngine(fred_api_key=fred_api_key)
        self.processor = RobustQuantProcessor()
        self.macro_engine = MacroRegimeEngine(fred_api_key=fred_api_key)

        self.grid_1h = {}
        self.active_macro_regime_id = 5
        self.active_macro_regime_name = "Küresel Likidite Rallisi (Risk-On)"
        self.market_regime = "🟢 [REJİM 5] Küresel Likidite Rallisi (Risk-On)"
        self.active_subtype = "Klasik Goldilocks Risk-On"
        self.dynamic_thresholds = REGIME_DYNAMIC_THRESHOLDS.get(5, {})
        self.macro_diagnostics = {}

        self.current_vix = 16.0
        self.stagflation_z = 0.0
        self.yen_carry_z = 0.0
        self.real_yield_z = 0.45
        self.breakeven_z = 0.65
        self.dxy_velocity = 0.0
        self.credit_velocity = 0.0
        self.anomaly_score = 0.0
        self.crisis_active = False
        self.consecutive_breaches = 0
        self.dfii10_z = 0.45
        self.curve_label = "DÜZ EĞRİ"

    def refresh_market(self):
        self.grid_1h = self.data_engine.fetch_global_market_grid()

        vix_df = self.grid_1h.get("VIX", pd.DataFrame())
        self.current_vix = float(vix_df["Close"].iloc[-1]) if not vix_df.empty else 16.0
        z_vix = self.processor.compute_vix_stress(vix_df) if not vix_df.empty else 0.0

        # Anlık Hızlar
        self.dxy_velocity = self.processor.compute_usd_strength_impulse(self.grid_1h.get("DXY", pd.DataFrame()))
        self.credit_velocity = self.processor.compute_credit_intraday_velocity(
            self.grid_1h.get("HYG", pd.DataFrame()),
            self.grid_1h.get("LQD", pd.DataFrame())
        )

        # Şok İndikatörleri
        self.stagflation_z = self.processor.compute_stagflation_shock(
            self.grid_1h.get("USO", self.grid_1h.get("CL", pd.DataFrame())),
            self.grid_1h.get("IYT", self.grid_1h.get("BDRY", pd.DataFrame()))
        )
        self.yen_carry_z = self.processor.compute_yen_carry_shock(self.grid_1h.get("USDJPY", pd.DataFrame()))

        # FRED & Macro Engine Entegrasyonu
        fred_metrics = self.data_engine.fetch_fred_macro_metrics(market_grid=self.grid_1h)
        self.real_yield_z = fred_metrics.get("dfii10_z", 0.45)
        self.breakeven_z = fred_metrics.get("t10yie_z", 0.65)
        self.dfii10_z = self.real_yield_z
        self.curve_label = fred_metrics.get("curve_label", "DÜZ EĞRİ")

        # Macro Event Interpretation System v1.0 Değerlendirmesi
        macro_payload = {
            **fred_metrics,
            "dxy_velocity_z": self.dxy_velocity,
            "credit_velocity_z": self.credit_velocity,
            "z_vix": z_vix,
            "oil_z": self.stagflation_z,
            "yen_carry_z": self.yen_carry_z
        }
        self.macro_diagnostics = self.macro_engine.evaluate(macro_payload)
        self.active_macro_regime_id = self.macro_diagnostics["active_regime_id"]
        self.active_macro_regime_name = self.macro_diagnostics["active_regime_name"]
        self.market_regime = self.macro_diagnostics["formatted_label"]
        self.active_subtype = self.macro_diagnostics["active_regime_subtype"]
        self.dynamic_thresholds = self.macro_diagnostics["dynamic_thresholds"]

        # Kriz Kilidi Değerlendirmesi
        self.crisis_active, self.anomaly_score, _ = self.processor.evaluate_crisis_lock_with_hysteresis(
            self.credit_velocity, z_vix, self.real_yield_z, self.dxy_velocity,
            self.current_vix, self.crisis_active, self.consecutive_breaches
        )
        if self.crisis_active:
            self.consecutive_breaches += 1
        else:
            self.consecutive_breaches = 0

    def evaluate_asset_direction(self, asset_key, previous_signal="NÖTR (BEKLE)"):
        matrix = ASSET_MATRICES.get(asset_key, {})
        if not matrix:
            return {
                "verdict": "NÖTR (BEKLE)",
                "forecast_direction": "NÖTR (BEKLE)",
                "current_direction": "⚪ YATAY (%0.00)",
                "score": 0.0,
                "details": []
            }

        symbol = matrix.get("benchmark_symbol", "SPY")
        clean_sym = symbol.replace("^", "").replace("=X", "").replace("=F", "")
        df_ast = self.grid_1h.get(clean_sym, self.grid_1h.get(symbol, pd.DataFrame()))
        current_dir, current_icon, current_color, current_roc = self.processor.compute_realtime_price_action(df_ast)
        adx_val, adx_regime = self.processor.compute_adx(df_ast)

        # 1. Kriz Kilidi Kontrolü
        if self.crisis_active:
            return {
                "verdict": "⛔ KRİZ KİLİDİ (BEKLE)",
                "forecast_direction": "⛔ KRİZ KİLİDİ (BEKLE)",
                "forecast_icon": "⛔",
                "forecast_color": "red",
                "current_direction": current_dir,
                "current_icon": current_icon,
                "current_color": current_color,
                "current_roc": current_roc,
                "icon": "⛔",
                "color": "red",
                "score": 0.0,
                "cluster_agreement": "Tüm Pozisyonlar Askıda",
                "session_status": "KİLİTLİ",
                "active_regime_id": self.active_macro_regime_id,
                "active_regime_name": self.active_macro_regime_name,
                "dynamic_thresholds": self.dynamic_thresholds,
                "details": []
            }

        session_status, session_multiplier = self.processor.get_asset_session_status(asset_key)

        weighted_sum = 0.0
        total_weights = 0.0
        cluster_scores = {c: 0.0 for c in CLUSTERS.keys()}
        details = []

        for factor in matrix.get("factors", []):
            f_id = factor["id"]
            cluster = factor["cluster"]
            weight = factor["base_weight"]
            sign = factor["base_sign"]

            val = 0.0

            # Dinamik Kurumsal Risk Hesaplamaları
            if f_id == "asset_direction":
                vol_scale = matrix.get("vol_scale", 1.0)
                val = self.processor.compute_intraday_direction_momentum(df_ast, vol_scale=vol_scale)
            elif f_id == "crypto_taker":
                ccy = matrix.get("crypto_ccy", "BTC")
                flow = self.data_engine.fetch_crypto_taker_flow(ccy)
                raw_ratio = flow.get("value", 1.0)
                val = float(np.tanh(np.log(raw_ratio + 1e-6) * 2.0) * 1.5)
            elif f_id == "funding_stress":
                ccy = matrix.get("crypto_ccy", "BTC")
                fr = self.data_engine.fetch_crypto_funding_rate(ccy)
                val = self.processor.compute_crypto_funding_stress(fr.get("rate", 0.0001))
            elif f_id == "btc_dominance":
                val = self.processor.compute_ratio_z(
                    self.grid_1h.get("BTC-USD", pd.DataFrame()),
                    self.grid_1h.get("ETH-USD", pd.DataFrame())
                )
            elif f_id == "semi_lead":
                val = self.processor.compute_ratio_z(
                    self.grid_1h.get("SMH", pd.DataFrame()),
                    self.grid_1h.get("QQQ", pd.DataFrame())
                )
            elif f_id == "market_breadth":
                val = self.processor.compute_market_breadth(
                    self.grid_1h.get("RSP", pd.DataFrame()),
                    self.grid_1h.get("SPY", pd.DataFrame())
                )
            elif f_id == "duration_risk":
                val = self.processor.compute_bond_duration_risk(
                    self.grid_1h.get("TLT", pd.DataFrame()),
                    self.grid_1h.get("SHY", pd.DataFrame())
                )
            elif f_id == "banking_stress":
                val = self.processor.compute_banking_stress(
                    self.grid_1h.get("KRE", pd.DataFrame()),
                    self.grid_1h.get("SPY", pd.DataFrame())
                )
            elif f_id == "defensive_flight":
                bench_sym = "QQQ" if asset_key == "NQ" else "SPY"
                val = self.processor.compute_defensive_flight(
                    self.grid_1h.get("XLU", pd.DataFrame()),
                    self.grid_1h.get(bench_sym, pd.DataFrame())
                )
            elif f_id == "consumer_demand":
                val = self.processor.compute_consumer_confidence(
                    self.grid_1h.get("XLY", pd.DataFrame()),
                    self.grid_1h.get("XLP", pd.DataFrame())
                )
            elif f_id == "speculative_beta":
                val = self.processor.compute_ratio_z(
                    self.grid_1h.get("ARKK", pd.DataFrame()),
                    self.grid_1h.get("QQQ", pd.DataFrame())
                )
            elif f_id == "vix_term":
                val = self.processor.compute_vix_term_structure(
                    self.grid_1h.get("VIX", pd.DataFrame()),
                    self.grid_1h.get("VIX3M", pd.DataFrame())
                )
            elif f_id == "copper_gold":
                val = self.processor.compute_ratio_z(
                    self.grid_1h.get("HG", self.grid_1h.get("HG=F", pd.DataFrame())),
                    self.grid_1h.get("GC", self.grid_1h.get("GC=F", pd.DataFrame()))
                )
            elif f_id == "gsr_velocity":
                val = self.processor.compute_gsr_velocity(
                    self.grid_1h.get("GC", self.grid_1h.get("GC=F", pd.DataFrame())),
                    self.grid_1h.get("SI", self.grid_1h.get("SI=F", pd.DataFrame()))
                )
            elif f_id == "gold_oil_ratio":
                val = self.processor.compute_gold_oil_ratio(
                    self.grid_1h.get("GC", self.grid_1h.get("GC=F", pd.DataFrame())),
                    self.grid_1h.get("USO", self.grid_1h.get("CL", pd.DataFrame()))
                )
            elif f_id == "silver_copper":
                val = self.processor.compute_silver_copper_ratio(
                    self.grid_1h.get("SI", self.grid_1h.get("SI=F", pd.DataFrame())),
                    self.grid_1h.get("HG", self.grid_1h.get("HG=F", pd.DataFrame()))
                )
            elif f_id == "gold_sympathy":
                df_gc = self.grid_1h.get("GC", self.grid_1h.get("GC=F", pd.DataFrame()))
                val = self.processor.compute_intraday_direction_momentum(df_gc, vol_scale=1.0)
            elif f_id == "btc_sympathy":
                df_btc = self.grid_1h.get("BTC-USD", pd.DataFrame())
                val = self.processor.compute_intraday_direction_momentum(df_btc, vol_scale=1.8)
            elif f_id == "eth_btc_beta":
                val = self.processor.compute_ratio_z(
                    self.grid_1h.get("ETH-USD", pd.DataFrame()),
                    self.grid_1h.get("BTC-USD", pd.DataFrame())
                )
            elif f_id == "usd_strength":
                val = self.dxy_velocity
            elif f_id == "credit_spread":
                val = self.credit_velocity
            elif f_id == "vix_strain":
                vix_df = self.grid_1h.get("VIX", pd.DataFrame())
                val = self.processor.compute_vix_stress(vix_df) if not vix_df.empty else 0.0
            elif f_id == "real_yield":
                val = self.real_yield_z
            elif f_id == "breakeven_infl":
                val = self.breakeven_z
            elif f_id == "safe_haven":
                vix_df = self.grid_1h.get("VIX", pd.DataFrame())
                val = self.processor.compute_vix_stress(vix_df) if not vix_df.empty else 0.0
            elif f_id == "stagflation_shock":
                val = self.stagflation_z

            # Barra normalizasyonu
            f_score = float(np.clip(val, -1.8, 1.8)) * sign * weight
            weighted_sum += f_score
            total_weights += weight
            cluster_scores[cluster] += f_score

            details.append({
                "faktör": factor["name"],
                "küme": cluster,
                "ham_deger": round(val, 2),
                "puan": round(f_score, 2)
            })

        # Barra Ağırlıklı Ortalama
        weighted_avg = weighted_sum / (total_weights + 1e-9)
        normalized_score = round(float(np.clip(weighted_avg * 1.5, -3.5, 3.5)), 2)
        final_score = normalized_score

        # Küme Konsensüsü
        active_clusters = [c for c, sc in cluster_scores.items() if abs(sc) > 0.15]
        bull_clusters = sum(1 for c, sc in cluster_scores.items() if sc > 0.20)
        bear_clusters = sum(1 for c, sc in cluster_scores.items() if sc < -0.20)

        # 🧠 Sinyal Çözümleme (Aktif Makro Rejime ve Kalibre Edilmiş Dinamik Eşiklere Bağlı)
        total_active_clusters = max(len(active_clusters), 2)
        min_cluster_req = max(2, int(np.ceil(total_active_clusters * 0.45)))
        
        verdict, color, icon = self.processor.resolve_signal_with_hysteresis(
            final_score,
            previous_signal=previous_signal,
            bull_clusters=bull_clusters,
            bear_clusters=bear_clusters,
            min_clusters=min_cluster_req,
            market_regime=self.market_regime,
            adx_val=adx_val,
            dynamic_thresholds=self.dynamic_thresholds,
            active_regime_id=self.active_macro_regime_id
        )

        return {
            "current_direction": current_dir,
            "current_icon": current_icon,
            "current_color": current_color,
            "current_roc": current_roc,
            "forecast_direction": verdict,
            "forecast_icon": icon,
            "forecast_color": color,
            "verdict": verdict,
            "icon": icon,
            "color": color,
            "score": final_score,
            "cluster_agreement": f"{bull_clusters} Boğa / {bear_clusters} Ayı Kümesi (Aktif: {len(active_clusters)})",
            "session_status": session_status,
            "adx_val": adx_val,
            "adx_regime": adx_regime,
            "active_regime_id": self.active_macro_regime_id,
            "active_regime_name": self.active_macro_regime_name,
            "active_subtype": self.active_subtype,
            "dynamic_thresholds": self.dynamic_thresholds,
            "details": details
        }

    def evaluate_all_assets_harmonized(self, previous_signals=None):
        if previous_signals is None:
            previous_signals = {}
        verdicts = {}
        for k in ASSET_MATRICES.keys():
            prev = previous_signals.get(k, "NÖTR (BEKLE)")
            verdicts[k] = self.evaluate_asset_direction(k, previous_signal=prev)

        # İkiz Varlık Konsensüs Kontrolü
        twin_pairs = [
            ("SPX", "NQ", 0.35),
            ("XAU", "XAG", 0.35),
            ("BTC", "ETH", 0.50)
        ]
        for a1, a2, tolerance in twin_pairs:
            v1 = verdicts.get(a1)
            v2 = verdicts.get(a2)
            if not v1 or not v2:
                continue
            sc1 = float(v1.get("score", 0.0))
            sc2 = float(v2.get("score", 0.0))
            diff = abs(sc1 - sc2)

            if diff <= tolerance:
                if sc1 <= -0.40 and sc2 <= -0.40:
                    if "SAT" in v1["verdict"] or "SAT" in v2["verdict"]:
                        for v in (v1, v2):
                            if "GÜÇLÜ SAT" not in v["verdict"]:
                                v["verdict"] = "SAT"
                                v["forecast_direction"] = "SAT"
                                v["icon"] = "🔴"
                                v["forecast_icon"] = "🔴"
                                v["color"] = "red"
                elif sc1 >= 0.40 and sc2 >= 0.40:
                    if "AL" in v1["verdict"] or "AL" in v2["verdict"]:
                        for v in (v1, v2):
                            if "GÜÇLÜ AL" not in v["verdict"]:
                                v["verdict"] = "AL"
                                v["forecast_direction"] = "AL"
                                v["icon"] = "🟢"
                                v["forecast_icon"] = "🟢"
                                v["color"] = "lightgreen"

        return verdicts
