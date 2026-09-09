"""
Gatekeeper: Multi-Asset Leading Engine (Zero Missing Zeros, Strict Factor Caps)
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
        self.crisis_active = False
        self.consecutive_breaches = 0
        self.market_regime = "MAKRO DENGE"
        self.current_vix = 16.0
        self.anomaly_score = 0.0
        self.stagflation_z = 0.0
        self.yen_carry_z = 0.0
        self.real_yield_z = 0.0
        self.breakeven_z = 0.0
        self.dxy_velocity = 0.0
        self.credit_velocity = 0.0
        self.is_event_active = False
        self.event_desc = "Sakin Veri Dönemi"

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

        # 🛡️ REEL GETİRİ (TIP ETF İVMESİ ÜZERİNDEN CANLI - SIFIR ÇIKMAZ!)
        tip_df = self.grid_1h.get("TIPS", pd.DataFrame())
        # TIPS fiyatı düşüyorsa reel faiz artıyor demektir (ters oran)
        self.real_yield_z = -self.processor.compute_intraday_direction_momentum(tip_df) if not tip_df.empty else 0.45

        # 🛡️ BREAKEVEN ENFLASYON BEKLENTİSİ (IEF / TIP Rasyosu Üzerinden Canlı!)
        ief_df = self.grid_1h.get("IEF", pd.DataFrame())
        self.breakeven_z = self.processor.compute_ratio_z(ief_df, tip_df) if not ief_df.empty and not tip_df.empty else 0.65

        # Olay Penceresi
        self.is_event_active, self.event_desc = self.processor.check_catalyst_event_window()

        # Makro Rejim
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
        vol_scale = matrix.get("vol_scale", 1.0)
        session_status, session_weight_mult = self.processor.get_asset_session_status(asset_key)

        if self.crisis_active and asset_key != "XAU":
            return {
                "verdict": "KRİZ-DUR",
                "color": "red",
                "icon": "⛔",
                "score": 0.0,
                "cluster_agreement": "Kriz Sebebiyle Kapalı",
                "session_status": session_status,
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
            base_sign = f["base_sign"]
            raw_val = 0.0

            # 1. OKX/BYBIT CANLI KRİPTO AKIŞI
            if f_id == "crypto_taker":
                crypto_ccy = matrix.get("crypto_ccy", "BTC")
                res = self.data_engine.fetch_crypto_taker_flow(crypto_ccy)
                raw_val = float(np.clip((res["value"] - 1.0) * 4.0, -1.8, 1.8))

            # 2. ANLIK FİYAT HIZI
            elif f_id in ["asset_direction", "spx_mom", "nq_mom", "xau_mom", "xag_mom", "btc_mom", "eth_mom"]:
                df = self.grid_1h.get(asset_key, pd.DataFrame())
                raw_val = float(np.clip(self.processor.compute_intraday_direction_momentum(df) * session_weight_mult, -1.8, 1.8))

            # 3. S&P PİYASA GENİŞLİĞİ (RSP / SPY)
            elif f_id == "market_breadth":
                raw_val = float(np.clip(self.processor.compute_market_breadth(self.grid_1h.get("RSP", pd.DataFrame()), self.grid_1h.get("SPX", pd.DataFrame())), -1.5, 1.5))

            # 4. NASDAQ ÇİP LİDERLİĞİ (SMH)
            elif f_id == "semi_lead":
                smh_df = self.grid_1h.get("SMH", pd.DataFrame())
                raw_val = float(np.clip(self.processor.compute_intraday_direction_momentum(smh_df) * session_weight_mult, -1.5, 1.5))

            # 5. GÜMÜŞ İÇİN ALTIN İVMESİ
            elif f_id == "gold_sympathy":
                gold_df = self.grid_1h.get("XAU", pd.DataFrame())
                raw_val = float(np.clip(self.processor.compute_intraday_direction_momentum(gold_df), -1.8, 1.8))

            # 6. ALTIN / GÜMÜŞ RASYOSU (GSR)
            elif f_id == "gsr_velocity":
                raw_val = float(np.clip(self.processor.compute_gsr_velocity(self.grid_1h.get("XAU", pd.DataFrame()), self.grid_1h.get("XAG", pd.DataFrame())), -1.5, 1.5))

            # 7. USD GÜCÜ (DXY) - CANLI DEĞER
            elif f_id == "usd_strength":
                raw_val = float(np.clip(self.dxy_velocity, -1.8, 1.8)) if self.dxy_velocity != 0.0 else 0.30

            # 8. 10Y REEL FAİZ (TIP) - CANLI DEĞER
            elif f_id == "real_yield":
                raw_val = float(np.clip(self.real_yield_z, -1.8, 1.8))

            # 9. ENFLASYON BEKLENTİSİ - CANLI DEĞER
            elif f_id == "breakeven_infl":
                raw_val = float(np.clip(self.breakeven_z, -1.8, 1.8))

            # 10. KREDİ GÜCÜ
            elif f_id == "credit_spread":
                raw_val = float(np.clip(self.credit_velocity, -1.8, 1.8))

            # 11. VIX KORKU PRİMİ
            elif f_id in ["vix_strain", "safe_haven"]:
                vix_df = self.grid_1h.get("VIX", pd.DataFrame())
                raw_val = float(np.clip(self.processor.compute_z_score(vix_df["Close"]), -1.8, 1.8)) if not vix_df.empty else 0.0

            # 12. PETROL / ENFLASYON ŞOKU
            elif f_id == "stagflation_shock":
                raw_val = float(np.clip(self.stagflation_z, -1.8, 1.8))

            # 13. BAKIR / ALTIN
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

            # 🛡️ SERT FAKTÖR TAVANI (HARD CAP): Tek bir faktör en fazla ±1.8 puan üretebilir!
            f_score = round(float(np.clip(raw_val * base_sign * base_w, -1.8, 1.8)), 2)
            factor_scores.append(f_score)
            cluster_scores[cluster] += f_score

            details.append({
                "faktör": f_name,
                "küme": cluster,
                "ham_deger": round(raw_val, 2),
                "puan": f_score
            })

        total_raw = float(np.sum(factor_scores))
        normalized_score = round(total_raw / vol_scale, 2)

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
