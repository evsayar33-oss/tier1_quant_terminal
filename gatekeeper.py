"""
Gatekeeper: Layer 1-2-3 Fusion & Pre-Trade Decision Gate
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

    def refresh_market(self):
        """Piyasa gridini ve kriz durumunu yeniler."""
        self.grid, self.meta = self.data_engine.fetch_global_market_grid()
        
        # Katman 2 Kriz Göstergeleri
        z_vix = self.processor.compute_z_score(self.grid["VIX"]["Close"]) if not self.grid["VIX"].empty else 0.0
        z_dxy = self.processor.compute_z_score(self.grid["DXY"]["Close"]) if not self.grid["DXY"].empty else 0.0
        z_rates = self.processor.compute_z_score(self.grid["TNX"]["Close"]) if not self.grid["TNX"].empty else 0.0
        z_credit = self.processor.compute_ratio_z(self.grid["HYG"], self.grid["LQD"])
        
        if z_vix > 2.0 or z_credit > 1.5:
            self.consecutive_breaches += 1
        else:
            self.consecutive_breaches = max(0, self.consecutive_breaches - 1)

        self.crisis_active, self.anomaly_score = self.processor.evaluate_crisis_lock_with_hysteresis(
            z_credit, z_vix, z_rates, z_dxy, self.crisis_active, self.consecutive_breaches
        )

    def evaluate_asset_gate(self, asset_key, trader_intent="LONG"):
        """
        Trader'ın Long/Short kurgusunu temel ve makro verilerle doğrular.
        Çıktı: ONAYLA, ZAYIF ONAY, ONAYLAMA veya KRİZ-DUR
        """
        if asset_key not in ASSET_MATRICES:
            return {"status": "HATA", "reason": "Bilinmeyen varlık"}

        matrix = ASSET_MATRICES[asset_key]
        factors = matrix["factors"]
        
        # Kriz Kontrolü (Altın İstisnası Hariç)
        if self.crisis_active:
            if asset_key == "XAU":
                safe_haven_active = True # Altın krizde korunma talebi görebilir
            else:
                return {
                    "verdict": "KRİZ-DUR",
                    "color": "red",
                    "cluster_agreement": "0/4",
                    "score": 0.0,
                    "reason": f"Kredi & Volatilite Kriz Kilidi Devrede (Anomali: {self.anomaly_score:.2f})"
                }

        factor_scores = []
        cluster_directions = {"A": [], "B": [], "C": [], "D": []}
        active_confidence = []

        for f in factors:
            f_id = f["id"]
            cluster = f["cluster"]
            base_w = f["base_weight"]
            base_sign = f["base_sign"]
            
            # Değer Hesaplama
            if f_id == "taker_ratio":
                res = self.data_engine.fetch_binance_taker_ratio(matrix.get("binance_symbol", "BTCUSDT"))
                val = (res["value"] - 1.0) * 10.0 # Normalize z-benzeri skor
                conf = res["confidence"]
            elif "mom" in f_id:
                df = self.grid.get(asset_key, pd.DataFrame())
                val = self.processor.compute_z_score(df["Close"]) if not df.empty else 0.0
                conf = self.meta.get(asset_key, {}).get("confidence", 1.0)
            elif "credit" in f_id:
                val = self.processor.compute_ratio_z(self.grid["HYG"], self.grid["LQD"])
                conf = self.meta.get("HYG", {}).get("confidence", 1.0)
            elif "vix" in f_id:
                val = self.processor.compute_z_score(self.grid["VIX"]["Close"]) if not self.grid["VIX"].empty else 0.0
                conf = self.meta.get("VIX", {}).get("confidence", 1.0)
            elif "copper_gold" in f_id:
                val = self.processor.compute_ratio_z(self.grid["COPPER"], self.grid["XAU"])
                conf = self.meta.get("COPPER", {}).get("confidence", 1.0)
            else:
                val = 0.0
                conf = 0.8

            # Gecikmeli Kayan Korelasyon İşareti (Sıfır Look-Ahead Bias)
            asset_df = self.grid.get(asset_key, pd.DataFrame())
            if not asset_df.empty and len(asset_df) > 65:
                derived_sign, is_neutral = self.processor.compute_lagged_rolling_correlation(
                    asset_df["Close"], asset_df["Close"], window=60, lag=3
                )
                effective_sign = derived_sign * base_sign if not is_neutral else 0.0
            else:
                effective_sign = base_sign

            # Efektif Ağırlık = Taban Ağırlık * Güven Çarpanı
            effective_weight = base_w * conf
            f_score = val * effective_sign * effective_weight
            factor_scores.append(f_score)
            active_confidence.append(conf)

            # Küme Yön Teyidi
            if f_score > 0.3:
                cluster_directions[cluster].append(1)
            elif f_score < -0.3:
                cluster_directions[cluster].append(-1)
            else:
                cluster_directions[cluster].append(0)

        total_score = float(np.sum(factor_scores))
        avg_confidence = float(np.mean(active_confidence))

        # 4 Bağımsız Kümenin Kaçı Trader ile Aynı Yönde?
        desired_dir = 1 if trader_intent == "LONG" else -1
        agreeing_clusters = 0
        for cl_key, dirs in cluster_directions.items():
            if len(dirs) > 0:
                cluster_net = np.sum(dirs)
                if (desired_dir == 1 and cluster_net > 0) or (desired_dir == -1 and cluster_net < 0):
                    agreeing_clusters += 1

        cluster_str = f"{agreeing_clusters}/4 Küme Uyumlu"

        # Persentil Eşik Kurgusu (Sentetik Kayan Dağılım)
        long_threshold = 2.5
        short_threshold = -2.5

        # NİHAİ 4 DURUMLU KARAR MOTORU
        if trader_intent == "LONG":
            if total_score >= long_threshold and agreeing_clusters >= 3:
                verdict = "ONAYLA"
                color = "green"
            elif total_score > 0 and agreeing_clusters >= 2:
                verdict = "ZAYIF ONAY"
                color = "yellow"
            else:
                verdict = "ONAYLAMA"
                color = "orange"
        else: # SHORT
            if total_score <= short_threshold and agreeing_clusters >= 3:
                verdict = "ONAYLA"
                color = "green"
            elif total_score < 0 and agreeing_clusters >= 2:
                verdict = "ZAYIF ONAY"
                color = "yellow"
            else:
                verdict = "ONAYLAMA"
                color = "orange"

        return {
            "verdict": verdict,
            "color": color,
            "score": round(total_score, 2),
            "cluster_agreement": cluster_str,
            "confidence": round(avg_confidence * 100, 1),
            "trader_intent": trader_intent,
            "anomaly_score": round(self.anomaly_score, 2)
        }
