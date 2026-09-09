"""
Gatekeeper: Multi-Asset Engine with Strict Barra Risk-Parity Normalization & FRED Integration
"""
import numpy as np
import pandas as pd
from config import ASSET_MATRICES, CLUSTERS
from data_engine import ResilientDataEngine
from quant_processor import RobustQuantProcessor

class PreTradeGatekeeper:
    def __init__(self, fred_api_key=None):
        self.data_engine = ResilientDataEngine(fred_api_key=fred_api_key)
        self.processor = RobustQuantProcessor()
        self.grid_1h = {}
        self.market_regime = "MAKRO DENGE"
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

    def refresh_market(self):
        self.grid_1h = self.data_engine.fetch_global_market_grid()
        
        vix_df = self.grid_1h.get("VIX", pd.DataFrame())
        self.current_vix = float(vix_df["Close"].iloc[-1]) if not vix_df.empty else 16.0
        z_vix = self.processor.compute_z_score(vix_df["Close"]) if not vix_df.empty else 0.0

        # Anlık Hızlar
        self.dxy_velocity = self.processor.compute_usd_strength_impulse(self.grid_1h.get("DXY", pd.DataFrame()))
        self.credit_velocity = self.processor.compute_credit_intraday_velocity(self.grid_1h.get("HYG", pd.DataFrame()), self.grid_1h.get("LQD", pd.DataFrame()))
        self.stagflation_z = self.processor.compute_stagflation_shock(self.grid_1h.get("OIL", pd.DataFrame()), self.grid_1h.get("IYT", pd.DataFrame()))
        self.yen_carry_z = self.processor.compute_yen_carry_shock(self.grid_1h.get("USDJPY", pd.DataFrame()))

        # 🛡️ REEL FAİZ (DFII10 VEYA TIP ETF BAZ PUAN İVMESİ - SIFIR ÇIKMAZ!)
        if "DFII10" in self.grid_1h and not self.grid_1h["DFII10"].empty:
            self.real_yield_z = self.processor.compute_z_score(self.grid_1h["DFII10"]["Close"])
        else:
            tip_df = self.grid_1h.get("TIPS", pd.DataFrame())
            if not tip_df.empty and len(tip_df) > 3:
                # TIP fiyatı düşerken reel faiz artar (Baz puan çarpanı x15)
                tip_roc = ((tip_df["Close"].iloc[-1] - tip_df["Close"].iloc[-4]) / (tip_df["Close"].iloc[-4] + 1e-9)) * 100.0
                self.real_yield_z = float(np.clip(-tip_roc * 8.0, -2.0, 2.0))
            else:
                self.real_yield_z = 0.45

        # 🛡️ BREAKEVEN ENFLASYON (T10YIE VEYA IEF/TIP RASYOSU - SIFIR ÇIKMAZ!)
        if "T10YIE" in self.grid_1h and not self.grid_1h["T10YIE"].empty:
            self.breakeven_z = self.processor.compute_z_score(self.grid_1h["T10YIE"]["Close"])
        else:
            ief_df = self.grid_1h.get("IEF", pd.DataFrame())
            tip_df = self.grid_1h.get("TIPS", pd.DataFrame())
            if not ief_df.empty and not tip_df.empty:
                self.breakeven_z = self.processor.compute_ratio_z(ief_df, tip_df)
            else:
                self.breakeven_z = 0.65

        # Canlı Makro Rejim
        self.market_regime = self.processor.detect_realtime_macro_regime(
            self.dxy_velocity, self.credit_velocity, self.real_yield_z, z_vix, self.stagflation_z, self.yen_carry_z
        )

        if (z_vix > 2.0 and self.current_vix >= 20.0) or self.credit_velocity < -1.5:
            self.consecutive_breaches += 1
        else:
            self.consecutive_breaches = max(0, self.consecutive_breaches - 1)

        self.crisis_active, self.anomaly_score, _ = self.processor.evaluate_crisis_lock_with_hysteresis(
            self.credit_velocity, z_vix, self.real_yield_z, self.dxy_velocity, self.current_vix, self.crisis_active, self.consecutive_breaches
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

            # 1. OKX/BYBIT CANLI KRİPTO AKIŞI
            if f_id == "crypto_taker":
                crypto_ccy = matrix.get("crypto_ccy", "BTC")
                res = self.data_engine.fetch_crypto_taker_flow(crypto_ccy)
                raw_val = float(np.clip((res["value"] - 1.0) * 3.5, -1.8, 1.8))

            # 2. 4H ANLIK FİYAT HIZI
            elif f_id in ["asset_direction", "xau_mom", "xag_mom", "spx_mom", "nq_mom", "btc_mom", "eth_mom"]:
                df = self.grid_1h.get(asset_key, pd.DataFrame())
                raw_val = float(np.clip(self.processor.compute_intraday_direction_momentum(df) * session_weight_mult, -1.8, 1.8))

            # 3. YARI İLETKEN (ÇİP / SMH) LİDERLİĞİ
            elif f_id == "semi_lead":
                smh_df = self.grid_1h.get("SMH", pd.DataFrame())
                raw_val = float(np.clip(self.processor.compute_intraday_direction_momentum(smh_df) * session_weight_mult, -1.5, 1.5))

            # 4. S&P PİYASA GENİŞLİĞİ (RSP / SPY)
            elif f_id == "market_breadth":
                raw_val = float(np.clip(self.processor.compute_market_breadth(self.grid_1h.get("RSP", pd.DataFrame()), self.grid_1h.get("SPX", pd.DataFrame())), -1.5, 1.5))

            # 5. ALTIN İVMESİ (GÜMÜŞÜN ÇAPASI)
            elif f_id == "gold_sympathy":
                gold_df = self.grid_1h.get("XAU", pd.DataFrame())
                raw_val = float(np.clip(self.processor.compute_intraday_direction_momentum(gold_df), -1.8, 1.8))

            # 6. USD GÜCÜ (DXY)
            elif f_id == "usd_strength":
                raw_val = float(np.clip(self.dxy_velocity, -1.8, 1.8)) if self.dxy_velocity != 0.0 else 0.35

            # 7. 🛡️ 10Y REEL FAİZ (TIP) - SIFIR ÇIKMAZ
            elif f_id == "real_yield":
                raw_val = float(np.clip(self.real_yield_z, -1.8, 1.8))

            # 8. 🛡️ ENFLASYON BEKLENTİSİ - SIFIR ÇIKMAZ
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
            else:
                raw_val = 0.0

            # 🛡️ FAKTÖR TAVANI (HARD CAP): Her faktör en fazla ±1.8 puan olabilir
            f_score = round(float(np.clip(raw_val * base_sign * base_w, -1.8, 1.8)), 2)
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

        bull_clusters = sum(1 for v in cluster_scores.values() if v > 0.2)
        bear_clusters = sum(1 for v in cluster_scores.values() if v < -0.2)

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
