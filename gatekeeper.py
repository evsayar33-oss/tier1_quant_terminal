"""
Gatekeeper: Multi-Asset Leading Macro & Institutional Confirmation Engine (Clean Imports)
"""
import numpy as np
import pandas as pd
from config import ASSET_MATRICES, CLUSTERS
from data_engine import ResilientDataEngine
from quant_processor import RobustQuantProcessor

class PreTradeGatekeeper:
    def __init__(self):
        self.data_engine = ResilientDataEngine()
        self.processor = RobustQuantProcessor()
        self.grid_1h = {}
        self.grid_daily = {}
        self.crisis_active = False
        self.consecutive_breaches = 0
        self.market_regime = "MAKRO DENGE"
        self.current_vix = 15.0
        self.anomaly_score = 0.0
        self.stagflation_z = 0.0
        self.yen_carry_z = 0.0
        self.dfii10_z = 0.0
        self.curve_label = "NÖTR EĞRİ"
        self.dxy_velocity = 0.0
        self.credit_velocity = 0.0

    def refresh_market(self):
        self.grid_1h, self.grid_daily = self.data_engine.fetch_global_market_grid()
        
        vix_df = self.grid_1h.get("VIX", pd.DataFrame())
        self.current_vix = float(vix_df["Close"].iloc[-1]) if not vix_df.empty else 15.0
        z_vix = self.processor.compute_z_score(vix_df["Close"]) if not vix_df.empty else 0.0

        # Anlık Hızlar
        self.dxy_velocity = self.processor.compute_dxy_intraday_velocity(self.grid_1h.get("DXY", pd.DataFrame()))
        self.credit_velocity = self.processor.compute_credit_intraday_velocity(self.grid_1h.get("HYG", pd.DataFrame()), self.grid_1h.get("LQD", pd.DataFrame()))
        self.stagflation_z = self.processor.compute_stagflation_shock(self.grid_1h.get("OIL", pd.DataFrame()), self.grid_1h.get("IYT", pd.DataFrame()))
        self.yen_carry_z = self.processor.compute_yen_carry_shock(self.grid_1h.get("USDJPY", pd.DataFrame()))

        # FRED Reel Getiri
        dfii10_df = self.grid_daily.get("DFII10", pd.DataFrame())
        self.dfii10_z = self.processor.compute_z_score(dfii10_df["Close"]) if not dfii10_df.empty else 0.0
        self.curve_label = "NÖTR EĞRİ"

        # Canlı Makro Rejim
        self.market_regime = self.processor.detect_realtime_macro_regime(
            self.dxy_velocity, self.credit_velocity, self.dfii10_z, z_vix, self.stagflation_z, self.yen_carry_z
        )

        if (z_vix > 2.0 and self.current_vix >= 20.0) or self.credit_velocity < -1.5:
            self.consecutive_breaches += 1
        else:
            self.consecutive_breaches = max(0, self.consecutive_breaches - 1)

        self.crisis_active, self.anomaly_score, _ = self.processor.evaluate_crisis_lock_with_hysteresis(
            self.credit_velocity, z_vix, self.dfii10_z, self.dxy_velocity, self.current_vix, self.crisis_active, self.consecutive_breaches
        )

    def evaluate_asset_direction(self, asset_key):
        if asset_key not in ASSET_MATRICES:
            return {"verdict": "HATA", "reason": "Bilinmeyen varlık"}

        matrix = ASSET_MATRICES[asset_key]
        factors = matrix["factors"]

        if self.crisis_active and asset_key != "XAU":
            return {
                "verdict": "KRİZ-DUR",
                "color": "red",
                "icon": "⛔",
                "score": 0.0,
                "cluster_agreement": "Kriz Sebebiyle Kapalı",
                "confidence": 100.0,
                "anomaly_score": round(self.anomaly_score, 2),
                "market_regime": self.market_regime,
                "current_vix": round(self.current_vix, 1),
                "details": []
            }

        factor_scores = []
        cluster_scores = {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0, "E": 0.0}
        details = []

        for f in factors:
            f_id = f["id"]
            f_name = f["name"]
            cluster = f["cluster"]
            base_w = f["base_weight"]
            raw_val = 0.0

            if f_id == "taker_ratio":
                res = self.data_engine.fetch_binance_taker_ratio(matrix.get("binance_symbol", "BTCUSDT"))
                raw_val = (res["value"] - 1.0) * 8.0
                effective_sign = 1
            elif "mom" in f_id:
                df = self.grid_1h.get(asset_key, pd.DataFrame())
                raw_val = self.processor.compute_intraday_momentum(df)
                effective_sign = 1
            elif f_id == "credit_spread":
                raw_val = self.credit_velocity
                effective_sign = 1
            elif f_id == "dxy_strain":
                raw_val = self.dxy_velocity
                effective_sign = -1
            elif f_id == "stagflation_shock":
                raw_val = self.stagflation_z
                effective_sign = 1 if asset_key in ["XAU", "XAG"] else -1
            elif f_id == "yen_carry":
                raw_val = self.yen_carry_z
                effective_sign = 1
            elif f_id in ["yield_curve", "us10y_yield", "real_yield"]:
                raw_val = self.dfii10_z
                effective_sign = -1
            elif f_id == "vix_strain":
                vix_df = self.grid_1h.get("VIX", pd.DataFrame())
                raw_val = self.processor.compute_z_score(vix_df["Close"]) if not vix_df.empty else 0.0
                effective_sign = -1
            elif f_id == "copper_gold":
                raw_val = self.processor.compute_ratio_z(self.grid_1h.get("COPPER", pd.DataFrame()), self.grid_1h.get("XAU", pd.DataFrame()))
                effective_sign = 1
            elif f_id == "safe_haven":
                vix_df = self.grid_1h.get("VIX", pd.DataFrame())
                raw_val = self.processor.compute_z_score(vix_df["Close"]) if not vix_df.empty else 0.0
                effective_sign = 1
            else:
                effective_sign = 1

            f_score = round(raw_val * effective_sign * base_w, 2)
            factor_scores.append(f_score)
            cluster_scores[cluster] += f_score

            details.append({
                "faktör": f_name,
                "küme": cluster,
                "ham_deger": round(raw_val, 2),
                "puan": f_score
            })

        total_score = float(np.sum(factor_scores))
        bull_clusters = sum(1 for v in cluster_scores.values() if v > 0.3)
        bear_clusters = sum(1 for v in cluster_scores.values() if v < -0.3)

        if total_score >= 3.0 and bull_clusters >= 3:
            verdict, color, icon = "GÜÇLÜ AL", "green", "🟢🟢"
        elif total_score >= 1.2:
            verdict, color, icon = "AL", "lightgreen", "🟢"
        elif total_score <= -3.0 and bear_clusters >= 3:
            verdict, color, icon = "GÜÇLÜ SAT", "darkred", "🔴🔴"
        elif total_score <= -1.2:
            verdict, color, icon = "SAT", "red", "🔴"
        else:
            verdict, color, icon = "NÖTR (BEKLE)", "gray", "⚪"

        cluster_summary = f"{bull_clusters} Boğa / {bear_clusters} Ayı Kümesi"

        return {
            "verdict": verdict,
            "icon": icon,
            "color": color,
            "score": round(total_score, 2),
            "cluster_agreement": cluster_summary,
            "confidence": 100.0,
            "anomaly_score": round(self.anomaly_score, 2),
            "market_regime": self.market_regime,
            "current_vix": round(self.current_vix, 1),
            "stagflation_z": round(self.stagflation_z, 2),
            "yen_carry_z": round(self.yen_carry_z, 2),
            "dfii10_z": round(self.dfii10_z, 2),
            "curve_label": self.curve_label,
            "details": details
        }
