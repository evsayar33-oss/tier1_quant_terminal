"""
Gatekeeper: Autonomous Market Direction Engine (Direct Buy/Sell Signals)
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
        self.grid = {}
        self.meta = {}
        self.crisis_active = False
        self.consecutive_breaches = 0
        self.market_regime = "NEUTRAL"
        self.current_vix = 15.0
        self.anomaly_score = 0.0

    def refresh_market(self):
        self.grid, self.meta = self.data_engine.fetch_global_market_grid()
        
        spx_df = self.grid.get("SPX", pd.DataFrame())
        self.market_regime = self.processor.detect_market_regime(spx_df)

        vix_df = self.grid.get("VIX", pd.DataFrame())
        self.current_vix = float(vix_df["Close"].iloc[-1]) if not vix_df.empty else 15.0

        z_vix = self.processor.compute_z_score(vix_df["Close"]) if not vix_df.empty else 0.0
        z_dxy = self.processor.compute_z_score(self.grid["DXY"]["Close"]) if not self.grid["DXY"].empty else 0.0
        z_rates = self.processor.compute_z_score(self.grid["TNX"]["Close"]) if not self.grid["TNX"].empty else 0.0
        z_credit = self.processor.compute_ratio_z(self.grid["HYG"], self.grid["LQD"])

        if (z_vix > 2.0 and self.current_vix >= 20.0) or z_credit > 1.5:
            self.consecutive_breaches += 1
        else:
            self.consecutive_breaches = max(0, self.consecutive_breaches - 1)

        self.crisis_active, self.anomaly_score, _ = self.processor.evaluate_crisis_lock_with_hysteresis(
            z_credit, z_vix, z_rates, z_dxy, self.current_vix, self.crisis_active, self.consecutive_breaches
        )

    def evaluate_asset_direction(self, asset_key):
        """
        Varlığı otonom olarak analiz eder ve doğrudan yön sinyali üretir:
        GÜÇLÜ AL, AL, NÖTR, SAT, GÜÇLÜ SAT veya KRİZ-DUR
        """
        if asset_key not in ASSET_MATRICES:
            return {"verdict": "HATA", "reason": "Bilinmeyen varlık"}

        matrix = ASSET_MATRICES[asset_key]
        factors = matrix["factors"]

        # Kriz Kilidi
        if self.crisis_active and asset_key != "XAU":
            return {
                "verdict": "KRİZ-DUR",
                "color": "red",
                "score": 0.0,
                "cluster_agreement": "Kriz Sebebiyle Kapalı",
                "confidence": 100.0,
                "anomaly_score": round(self.anomaly_score, 2),
                "market_regime": self.market_regime,
                "current_vix": round(self.current_vix, 1),
                "details": []
            }

        factor_scores = []
        cluster_scores = {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0}
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

            # 1. Ham Değerlerin Hesaplanması
            if f_id == "taker_ratio":
                res = self.data_engine.fetch_binance_taker_ratio(matrix.get("binance_symbol", "BTCUSDT"))
                # Taker oranı > 1.0 alıcı, < 1.0 satıcı
                raw_val = (res["value"] - 1.0) * 8.0
                conf = res["confidence"]
            elif "mom" in f_id:
                df = self.grid.get(asset_key, pd.DataFrame())
                raw_val = self.processor.compute_momentum_score(df)
                conf = self.meta.get(asset_key, {}).get("confidence", 1.0)
            elif "credit" in f_id:
                # HYG/LQD rasyosu artıyorsa kredi piyasası güçlüdür (Pozitif risk iştahı)
                raw_val = self.processor.compute_ratio_z(self.grid["HYG"], self.grid["LQD"])
                conf = self.meta.get("HYG", {}).get("confidence", 1.0)
            elif "vix" in f_id:
                # VIX artıyorsa hisseler için negatif (ters işaretli)
                raw_val = self.processor.compute_z_score(self.grid["VIX"]["Close"]) if not self.grid["VIX"].empty else 0.0
                conf = self.meta.get("VIX", {}).get("confidence", 1.0)
            elif "copper_gold" in f_id:
                raw_val = self.processor.compute_ratio_z(self.grid["COPPER"], self.grid["XAU"])
                conf = self.meta.get("COPPER", {}).get("confidence", 1.0)
            elif "us10y" in f_id or "rates" in f_id:
                raw_val = self.processor.compute_z_score(self.grid["TNX"]["Close"]) if not self.grid["TNX"].empty else 0.0
                conf = self.meta.get("TNX", {}).get("confidence", 1.0)
            elif "dxy" in f_id:
                raw_val = self.processor.compute_z_score(self.grid["DXY"]["Close"]) if not self.grid["DXY"].empty else 0.0
                conf = self.meta.get("DXY", {}).get("confidence", 1.0)
            elif "safe_haven" in f_id:
                raw_val = self.processor.compute_z_score(self.grid["VIX"]["Close"]) if not self.grid["VIX"].empty else 0.0
                conf = 0.9

            # Ağırlıklı Puan
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

        # Küme Teyidi (Pozitif mi, Negatif mi?)
        bull_clusters = sum(1 for v in cluster_scores.values() if v > 0.3)
        bear_clusters = sum(1 for v in cluster_scores.values() if v < -0.3)

        # 🎯 DOĞRUDAN SİNYAL ÜRETİMİ (GÜÇLÜ AL / AL / NÖTR / SAT / GÜÇLÜ SAT)
        if total_score >= 3.0 and bull_clusters >= 3:
            verdict = "GÜÇLÜ AL"
            color = "green"
            icon = "🟢🟢"
        elif total_score >= 1.2:
            verdict = "AL"
            color = "lightgreen"
            icon = "🟢"
        elif total_score <= -3.0 and bear_clusters >= 3:
            verdict = "GÜÇLÜ SAT"
            color = "darkred"
            icon = "🔴🔴"
        elif total_score <= -1.2:
            verdict = "SAT"
            color = "red"
            icon = "🔴"
        else:
            verdict = "NÖTR (BEKLE)"
            color = "gray"
            icon = "⚪"

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
            "details": details
        }
