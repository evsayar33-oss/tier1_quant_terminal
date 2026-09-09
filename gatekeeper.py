"""
Gatekeeper: Multi-Asset Leading Macro & Institutional Confirmation Engine
"""
import numpy as np
import pandas as pd
from config import ASSET_MATRICES, CLUSTERS, THRESHOLD_CLAMPS
from data_engine import ResilientDataEngine
from quant_processor import RobustQuantProcessor

class PreTradeGatekeeper:
    def __init__(self):
        self.data_engine = ResilientDataEngine()
        self.processor = RobustQuantProcessor()
        self.grid = {}
        self.meta = {}
        self.crisis_active = False
        self.consecutive_breaches = 0
        self.market_regime = "MAKRO DENGE"
        self.current_vix = 15.0
        self.anomaly_score = 0.0

    def refresh_market(self):
        self.grid, self.meta = self.data_engine.fetch_global_market_grid()
        
        vix_df = self.grid.get("VIX", pd.DataFrame())
        self.current_vix = float(vix_df["Close"].iloc[-1]) if not vix_df.empty else 15.0

        # Anlık Öncü Makro Değişkenler
        z_vix = self.processor.compute_z_score(vix_df["Close"]) if not vix_df.empty else 0.0
        z_dxy = self.processor.compute_z_score(self.grid["DXY"]["Close"]) if not self.grid["DXY"].empty else 0.0
        z_rates = self.processor.compute_z_score(self.grid["TNX"]["Close"]) if not self.grid["TNX"].empty else 0.0
        z_credit = self.processor.compute_ratio_z(self.grid["HYG"], self.grid["LQD"])
        z_copper_gold = self.processor.compute_ratio_z(self.grid["COPPER"], self.grid["XAU"])
        
        # 🛢️ Petrol/Taşımacılık ve 💴 Yen Carry Öncü Göstergeleri
        self.stagflation_z = self.processor.compute_stagflation_shock(self.grid["OIL"], self.grid["IYT"])
        self.yen_carry_z = self.processor.compute_yen_carry_shock(self.grid["USDJPY"])

        # 5 Boyutlu Makro Rejim Tespiti
        self.market_regime = self.processor.detect_realtime_macro_regime(
            z_dxy, z_credit, z_rates, z_copper_gold, z_vix, self.stagflation_z, self.yen_carry_z
        )

        if (z_vix > 2.0 and self.current_vix >= 20.0) or z_credit < -1.8:
            self.consecutive_breaches += 1
        else:
            self.consecutive_breaches = max(0, self.consecutive_breaches - 1)

        self.crisis_active, self.anomaly_score, _ = self.processor.evaluate_crisis_lock_with_hysteresis(
            z_credit, z_vix, z_rates, z_dxy, self.current_vix, self.crisis_active, self.consecutive_breaches
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
        active_confidence = []
        details = []

        for f in factors:
            f_id = f["id"]
            f_name = f["name"]
            cluster = f["cluster"]
            base_w = f["base_weight"]
            base_sign = f["base_sign"]
            raw_val = 0.0
            conf = 1.0

            # Öncü Gösterge Değer Atamaları
            if f_id == "taker_ratio":
                res = self.data_engine.fetch_binance_taker_ratio(matrix.get("binance_symbol", "BTCUSDT"))
                raw_val = (res["value"] - 1.0) * 8.0
                conf = res["confidence"]
            elif "mom" in f_id:
                df = self.grid.get(asset_key, pd.DataFrame())
                raw_val = self.processor.compute_momentum_score(df)
                conf = self.meta.get(asset_key, {}).get("confidence", 1.0)
            elif f_id == "credit_spread":
                raw_val = self.processor.compute_ratio_z(self.grid["HYG"], self.grid["LQD"])
                conf = self.meta.get("HYG", {}).get("confidence", 1.0)
            elif f_id == "stagflation_shock":
                raw_val = self.stagflation_z # Petrol / Taşımacılık Rasyosu Z-skoru
                conf = 1.0
            elif f_id == "yen_carry":
                raw_val = self.yen_carry_z # USD/JPY Carry İvmesi
                conf = 1.0
            elif f_id == "yield_curve":
                raw_val = self.processor.compute_ratio_z(self.grid["TNX"], self.grid["SHY"])
                conf = 1.0
            elif f_id == "vix_strain":
                raw_val = self.processor.compute_z_score(self.grid["VIX"]["Close"]) if not self.grid["VIX"].empty else 0.0
                conf = self.meta.get("VIX", {}).get("confidence", 1.0)
            elif f_id == "copper_gold":
                raw_val = self.processor.compute_ratio_z(self.grid["COPPER"], self.grid["XAU"])
                conf = self.meta.get("COPPER", {}).get("confidence", 1.0)
            elif f_id == "us10y_yield":
                raw_val = self.processor.compute_z_score(self.grid["TNX"]["Close"]) if not self.grid["TNX"].empty else 0.0
                conf = self.meta.get("TNX", {}).get("confidence", 1.0)
            elif f_id == "real_yield":
                raw_val = self.processor.compute_z_score(self.grid["TIPS"]["Close"]) if not self.grid["TIPS"].empty else 0.0
                conf = self.meta.get("TIPS", {}).get("confidence", 1.0)
            elif f_id == "dxy_strain":
                raw_val = self.processor.compute_z_score(self.grid["DXY"]["Close"]) if not self.grid["DXY"].empty else 0.0
                conf = self.meta.get("DXY", {}).get("confidence", 1.0)
            elif f_id == "mining_beta":
                raw_val = self.processor.compute_z_score(self.grid["XME"]["Close"]) if not self.grid["XME"].empty else 0.0
                conf = self.meta.get("XME", {}).get("confidence", 1.0)
            elif f_id == "safe_haven":
                raw_val = self.processor.compute_z_score(self.grid["VIX"]["Close"]) if not self.grid["VIX"].empty else 0.0
                conf = 0.9

            f_score = round(raw_val * base_sign * base_w * conf, 2)
            factor_scores.append(f_score)
            cluster_scores[cluster] += f_score
            active_confidence.append(conf)

            details.append({
                "faktör": f_name,
                "küme": cluster,
                "ham_deger": round(raw_val, 2),
                "puan": f_score
            })

        total_score = float(np.sum(factor_scores))
        avg_confidence = float(np.mean(active_confidence)) if active_confidence else 1.0

        bull_clusters = sum(1 for v in cluster_scores.values() if v > 0.3)
        bear_clusters = sum(1 for v in cluster_scores.values() if v < -0.3)

        # Karar Eşikleri
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
            "confidence": round(avg_confidence * 100, 1),
            "anomaly_score": round(self.anomaly_score, 2),
            "market_regime": self.market_regime,
            "current_vix": round(self.current_vix, 1),
            "stagflation_z": round(self.stagflation_z, 2),
            "yen_carry_z": round(self.yen_carry_z, 2),
            "details": details
        }
