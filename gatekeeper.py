"""
Gatekeeper: Multi-Asset Engine with Strict Barra Risk-Parity Normalization (v17)
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
        self.market_regime = "MAKRO DENGE"
        self.current_vix = 16.0
        self.stagflation_z = 0.0
        self.yen_carry_z = 0.0
        self.real_yield_z = 0.0
        self.breakeven_z = 0.0
        self.dxy_velocity = 0.0
        self.credit_velocity = 0.0

    def refresh_market(self):
        self.grid_1h = self.data_engine.fetch_global_market_grid()
        
        vix_df = self.grid_1h.get("VIX", pd.DataFrame())
        self.current_vix = float(vix_df["Close"].iloc[-1]) if not vix_df.empty else 16.0
        z_vix = self.processor.compute_z_score(vix_df["Close"]) if not vix_df.empty else 0.0

        # Anlık Göstergeler
        self.dxy_velocity = self.processor.compute_usd_strength_impulse(self.grid_1h.get("DXY", pd.DataFrame()))
        self.credit_velocity = self.processor.compute_credit_intraday_velocity(self.grid_1h.get("HYG", pd.DataFrame()), self.grid_1h.get("LQD", pd.DataFrame()))
        self.stagflation_z = self.processor.compute_stagflation_shock(self.grid_1h.get("OIL", pd.DataFrame()), self.grid_1h.get("IYT", pd.DataFrame()))
        self.yen_carry_z = self.processor.compute_yen_carry_shock(self.grid_1h.get("USDJPY", pd.DataFrame()))

        # 🛡️ 10Y REEL FAİZ VE ENFLASYON (TIP VE IEF CANLI ETF'LERİNDEN - ASLA SIFIR KALMAZ!)
        tip_df = self.grid_1h.get("TIPS", pd.DataFrame())
        self.real_yield_z = -self.processor.compute_intraday_direction_momentum(tip_df) if not tip_df.empty else 0.40

        ief_df = self.grid_1h.get("IEF", pd.DataFrame())
        self.breakeven_z = self.processor.compute_ratio_z(ief_df, tip_df) if not ief_df.empty and not tip_df.empty else 0.50

        # Makro Rejim
        self.market_regime = self.processor.detect_realtime_macro_regime(
            self.dxy_velocity, self.credit_velocity, self.real_yield_z, z_vix, self.stagflation_z, self.yen_carry_z
        )

    def evaluate_asset_direction(self, asset_key, previous_signal=None):
        if asset_key not in ASSET_MATRICES:
            return {"verdict": "HATA", "reason": "Bilinmeyen varlık"}

        matrix = ASSET_MATRICES[asset_key]
        factors = matrix["factors"]
        session_status, session_weight_mult = self.processor.get_asset_session_status(asset_key)

        factor_scores = []
        cluster_scores = {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0, "E": 0.0}
        total_weights = 0.0
        details = []

        for f in factors:
            f_id = f["id"]
            f_name = f["name"]
            cluster = f["cluster"]
            base_w = f["base_weight"]
            base_sign = f["base_sign"]
            raw_val = 0.0

            # 1. OKX / BYBIT CANLI KRİPTO AKIŞI
            if f_id == "crypto_taker":
                crypto_ccy = matrix.get("crypto_ccy", "BTC")
                res = self.data_engine.fetch_crypto_taker_flow(crypto_ccy)
                raw_val = float(np.clip((res["value"] - 1.0) * 3.5, -1.8, 1.8))

            # 2. ANLIK FİYAT HIZI (4H/24H)
            elif f_id in ["asset_direction", "xau_mom", "xag_mom", "spx_mom", "nq_mom", "btc_mom", "eth_mom"]:
                df = self.grid_1h.get(asset_key, pd.DataFrame())
                raw_val = float(np.clip(self.processor.compute_intraday_direction_momentum(df) * session_weight_mult, -1.8, 1.8))

            # 3. YARI İLETKEN (ÇİP / SMH) LİDERLİĞİ
            elif f_id == "semi_lead":
                smh_df = self.grid_1h.get("SMH", pd.DataFrame())
                raw_val = float(np.clip(self.processor.compute_intraday_direction_momentum(smh_df) * session_weight_mult, -1.6, 1.6))

            # 4. S&P PİYASA GENİŞLİĞİ (RSP / SPY)
            elif f_id == "market_breadth":
                raw_val = float(np.clip(self.processor.compute_market_breadth(self.grid_1h.get("RSP", pd.DataFrame()), self.grid_1h.get("SPX", pd.DataFrame())), -1.6, 1.6))

            # 5. ALTIN İVMESİ (GÜMÜŞÜN ÇAPASI)
            elif f_id == "gold_sympathy":
                gold_df = self.grid_1h.get("XAU", pd.DataFrame())
                raw_val = float(np.clip(self.processor.compute_intraday_direction_momentum(gold_df), -1.8, 1.8))

            # 6. USD GÜCÜ (DXY)
            elif f_id == "usd_strength":
                raw_val = float(np.clip(self.dxy_velocity, -1.8, 1.8)) if self.dxy_velocity != 0.0 else 0.35

            # 7. REEL FAİZ (TIP)
            elif f_id == "real_yield":
                raw_val = float(np.clip(self.real_yield_z, -1.8, 1.8))

            # 8. ENFLASYON BEKLENTİSİ
            elif f_id == "breakeven_infl":
                raw_val = float(np.clip(self.breakeven_z, -1.8, 1.8))

            # 9. KREDİ GÜCÜ (HYG/LQD)
            elif f_id == "credit_spread":
                raw_val = float(np.clip(self.credit_velocity, -1.8, 1.8))

            # 10. VIX KORKU PRİMİ
            elif f_id in ["vix_strain", "safe_haven"]:
                vix_df = self.grid_1h.get("VIX", pd.DataFrame())
                raw_val = float(np.clip(self.processor.compute_z_score(vix_df["Close"]), -1.8, 1.8)) if not vix_df.empty else 0.0

            # 11. PETROL / ENFLASYON ŞOKU
            elif f_id == "stagflation_shock":
                raw_val = float(np.clip(self.stagflation_z, -1.8, 1.8))

            # 12. BAKIR / ALTIN
            elif f_id == "copper_gold":
                raw_val = float(np.clip(self.processor.compute_ratio_z(self.grid_1h.get("COPPER", pd.DataFrame()), self.grid_1h.get("XAU", pd.DataFrame())), -1.5, 1.5))

            elif f_id == "eth_btc_beta":
                b_df = self.grid_1h.get("BTC", pd.DataFrame())
                e_df = self.grid_1h.get("ETH", pd.DataFrame())
                raw_val = float(np.clip(self.processor.compute_ratio_z(e_df, b_df), -1.5, 1.5))

            elif f_id == "btc_sympathy":
                b_df = self.grid_1h.get("BTC", pd.DataFrame())
                raw_val = float(np.clip(self.processor.compute_intraday_direction_momentum(b_df), -1.8, 1.8))
            else:
                raw_val = 0.0

            f_score = round(raw_val * base_sign * base_w, 2)
            factor_scores.append(f_score)
            cluster_scores[cluster] += f_score
            total_weights += base_w

            details.append({
                "faktör": f_name,
                "küme": cluster,
                "ham_deger": round(raw_val, 2),
                "puan": f_score
            })

        # ⚖️ BARRA NORMALİZASYONU: Puanlar asla ±3.5'i aşamaz!
        total_raw = float(np.sum(factor_scores))
        normalized_score = round(float(np.clip((total_raw / (total_weights + 1e-9)) * 3.0, -3.5, 3.5)), 2)

        bull_clusters = sum(1 for v in cluster_scores.values() if v > 0.3)
        bear_clusters = sum(1 for v in cluster_scores.values() if v < -0.3)

        verdict, color, icon = self.processor.resolve_signal_with_hysteresis(
            normalized_score, previous_signal, bull_clusters, bear_clusters
        )

        cluster_summary = f"{bull_clusters} Boğa / {bear_clusters} Ayı Kümesi"

        return {
            "verdict": verdict,
            "icon": icon,
            "color": color,
            "score": normalized_score,
            "cluster_agreement": cluster_summary,
            "session_status": session_status,
            "details": details
        }
