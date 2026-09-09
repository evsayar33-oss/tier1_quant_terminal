"""
Gatekeeper: Layer 1-2-3 Fusion & Pre-Trade Decision Gate (Reinforced v4)
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
        self.market_regime = "NEUTRAL"
        self.current_vix = 15.0

    def refresh_market(self):
        """Tüm makro gridi, VIX tabanını ve piyasa rejimini yeniler."""
        self.grid, self.meta = self.data_engine.fetch_global_market_grid()
        
        # 1. Piyasa Rejimi Tespiti (Boğa mı, Ayı mı?)
        spx_df = self.grid.get("SPX", pd.DataFrame())
        self.market_regime = self.processor.detect_market_regime(spx_df)

        # 2. Mutlak VIX Seviyesi
        vix_df = self.grid.get("VIX", pd.DataFrame())
        self.current_vix = float(vix_df["Close"].iloc[-1]) if not vix_df.empty else 15.0

        # Katman 2 Göstergeleri
        z_vix = self.processor.compute_z_score(vix_df["Close"]) if not vix_df.empty else 0.0
        z_dxy = self.processor.compute_z_score(self.grid["DXY"]["Close"]) if not self.grid["DXY"].empty else 0.0
        z_rates = self.processor.compute_z_score(self.grid["TNX"]["Close"]) if not self.grid["TNX"].empty else 0.0
        z_credit = self.processor.compute_ratio_z(self.grid["HYG"], self.grid["LQD"])
        
        if (z_vix > 2.0 and self.current_vix >= 20.0) or z_credit > 1.5:
            self.consecutive_breaches += 1
        else:
            self.consecutive_breaches = max(0, self.consecutive_breaches - 1)

        # Hysteresis + VIX Mutlak Taban Kriz Kilidi
        self.crisis_active, self.anomaly_score, self.is_vix_high = self.processor.evaluate_crisis_lock_with_hysteresis(
            z_credit, z_vix, z_rates, z_dxy, self.current_vix, self.crisis_active, self.consecutive_breaches
        )

    def evaluate_asset_gate(self, asset_key, trader_intent="LONG"):
        if asset_key not in ASSET_MATRICES:
            return {"verdict": "HATA", "reason": "Bilinmeyen varlık"}

        matrix = ASSET_MATRICES[asset_key]
        factors = matrix["factors"]
        
        # Kriz Kilidi Kontrolü
        if self.crisis_active:
            if asset_key == "XAU":
                pass # Altın güvenli liman olarak istisnaya tabi olabilir
            else:
                return {
                    "verdict": "KRİZ-DUR",
                    "color": "red",
                    "cluster_agreement": "0/4",
                    "score": 0.0,
                    "reason": f"Sistemik Kriz Kilidi Devrede! (VIX: {self.current_vix:.1f} | Anomali: {self.anomaly_score:.2f})"
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
                val = (res["value"] - 1.0) * 10.0
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

            # Gecikmeli Kayan Korelasyon (Sıfır Look-Ahead Bias)
            asset_df = self.grid.get(asset_key, pd.DataFrame())
            if not asset_df.empty and len(asset_df) > 65:
                derived_sign, is_neutral = self.processor.compute_lagged_rolling_correlation(
                    asset_df["Close"], asset_df["Close"], window=60, lag=3
                )
                effective_sign = derived_sign * base_sign if not is_neutral else 0.0
            else:
                effective_sign = base_sign

            # Rejim Koşullu Dinamik Ağırlık
            dynamic_w = self.processor.compute_frequency_matched_weight(
                base_w, hit_rate=0.60, regime=self.market_regime, cluster=cluster
            )
            effective_weight = dynamic_w * conf

            f_score = val * effective_sign * effective_weight
            factor_scores.append(f_score)
            active_confidence.append(conf)

            # Küme Yönü
            if f_score > 0.3: cluster_directions[cluster].append(1)
            elif f_score < -0.3: cluster_directions[cluster].append(-1)
            else: cluster_directions[cluster].append(0)

        total_score = float(np.sum(factor_scores))
        avg_confidence = float(np.mean(active_confidence))

        # 4 Bağımsız Küme Teyidi
        desired_dir = 1 if trader_intent == "LONG" else -1
        agreeing_clusters = 0
        for cl_key, dirs in cluster_directions.items():
            if len(dirs) > 0:
                cluster_net = np.sum(dirs)
                if (desired_dir == 1 and cluster_net > 0) or (desired_dir == -1 and cluster_net < 0):
                    agreeing_clusters += 1

        cluster_str = f"{agreeing_clusters}/4 Küme Uyumlu"

        # 🛡️ DİNAMİK EŞİK TABANI (CLAMP):
        # Piyasanın uyuduğu günlerde persentil düşse bile asgari mutlak skor aranır!
        min_long_thresh = THRESHOLD_CLAMPS["min_long_score"]
        max_short_thresh = THRESHOLD_CLAMPS["max_short_score"]

        # NİHAİ 4 DURUMLU KARAR
        if trader_intent == "LONG":
            if total_score >= min_long_thresh and agreeing_clusters >= 3:
                verdict = "ONAYLA"
                color = "green"
            elif total_score > 0.5 and agreeing_clusters >= 2:
                verdict = "ZAYIF ONAY"
                color = "yellow"
            else:
                verdict = "ONAYLAMA"
                color = "orange"
        else: # SHORT
            if total_score <= max_short_thresh and agreeing_clusters >= 3:
                verdict = "ONAYLA"
                color = "green"
            elif total_score < -0.5 and agreeing_clusters >= 2:
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
            "anomaly_score": round(self.anomaly_score, 2),
            "market_regime": self.market_regime,
            "current_vix": round(self.current_vix, 1)
        }
