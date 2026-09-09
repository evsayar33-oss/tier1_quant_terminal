"""
Gatekeeper: Multi-Asset Engine with Strict Barra Risk-Parity Normalization & FRED Integration (v18)
"""
import numpy as np
import pandas as pd
from config import ASSET_MATRICES, CLUSTERS
from data_engine import ResilientDataEngine
from quant_processor import RobustQuantProcessor


class PreTradeGatekeeper:
    def __init__(self, fred_api_key=None, *args, **kwargs):
        if not fred_api_key and "fred_api_key" in kwargs:
            fred_api_key = kwargs["fred_api_key"]
        self.data_engine = ResilientDataEngine(fred_api_key=fred_api_key)
        self.processor = RobustQuantProcessor()
        self.grid_1h = {}
        self.market_regime = "MAKRO DENGE / SIKIŞMA"
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
        z_vix = self.processor.compute_z_score(vix_df["Close"]) if not vix_df.empty else 0.0

        # Anlık Hızlar
        self.dxy_velocity = self.processor.compute_usd_strength_impulse(self.grid_1h.get("DXY", pd.DataFrame()))
        self.credit_velocity = self.processor.compute_credit_intraday_velocity(
            self.grid_1h.get("HYG", pd.DataFrame()),
            self.grid_1h.get("LQD", pd.DataFrame())
        )

        # Şok İndikatörleri
        self.stagflation_z = self.processor.compute_stagflation_shock(
            self.grid_1h.get("USO", pd.DataFrame()),
            self.grid_1h.get("IYT", pd.DataFrame())
        )
        self.yen_carry_z = self.processor.compute_yen_carry_shock(self.grid_1h.get("USDJPY", pd.DataFrame()))

        # FRED Entegrasyonu
        fred_metrics = self.data_engine.fetch_fred_macro_metrics()
        self.real_yield_z = fred_metrics.get("dfii10_z", 0.45)
        self.breakeven_z = fred_metrics.get("t10yie_z", 0.65)
        self.dfii10_z = self.real_yield_z
        self.curve_label = fred_metrics.get("curve_label", "DÜZ EĞRİ")

        # Makro Rejim Tespiti
        self.market_regime = self.processor.detect_realtime_macro_regime(
            self.dxy_velocity, self.credit_velocity, self.real_yield_z,
            z_vix, self.stagflation_z, self.yen_carry_z
        )

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
            return {"verdict": "NÖTR (BEKLE)", "score": 0.0, "details": []}

        # 1. Kriz Kilidi Kontrolü
        if self.crisis_active:
            return {
                "verdict": "⛔ KRİZ KİLİDİ (BEKLE)",
                "icon": "⛔",
                "color": "red",
                "score": 0.0,
                "cluster_agreement": "Tüm Pozisyonlar Askıda",
                "session_status": "KİLİTLİ",
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

            # Dinamik Faktör Hesaplamaları
            if f_id == "asset_direction":
                symbol = matrix.get("benchmark_symbol", "SPY")
                df_ast = self.grid_1h.get(symbol, pd.DataFrame())
                vol_scale = matrix.get("vol_scale", 1.0)
                val = self.processor.compute_intraday_direction_momentum(df_ast, vol_scale=vol_scale)
            elif f_id == "crypto_taker":
                ccy = matrix.get("crypto_ccy", "BTC")
                flow = self.data_engine.fetch_crypto_taker_flow(ccy)
                # Taker oranını (1.0 civarı) logaritmik tanh filtresinden geçirerek aşırılığı törpüle
                raw_ratio = flow.get("value", 1.0)
                val = float(np.tanh(np.log(raw_ratio + 1e-6) * 2.0) * 1.5)
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
            elif f_id == "copper_gold":
                val = self.processor.compute_ratio_z(
                    self.grid_1h.get("HG=F", pd.DataFrame()),
                    self.grid_1h.get("GC=F", pd.DataFrame())
                )
            elif f_id == "gsr_velocity":
                val = self.processor.compute_gsr_velocity(
                    self.grid_1h.get("GC=F", pd.DataFrame()),
                    self.grid_1h.get("SI=F", pd.DataFrame())
                )
            elif f_id == "gold_sympathy":
                df_gc = self.grid_1h.get("GC=F", pd.DataFrame())
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
                val = self.processor.compute_z_score(vix_df["Close"]) if not vix_df.empty else 0.0
            elif f_id == "real_yield":
                val = self.real_yield_z
            elif f_id == "breakeven_infl":
                val = self.breakeven_z
            elif f_id == "safe_haven":
                vix_df = self.grid_1h.get("VIX", pd.DataFrame())
                val = self.processor.compute_z_score(vix_df["Close"]) if not vix_df.empty else 0.0
            elif f_id == "stagflation_shock":
                val = self.stagflation_z

            # Barra normalizasyonu: faktör katkısını sınırla ve topla
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

        # ⚖️ BARRA AĞIRLIKLI ORTALAMA NORMALİZASYONU
        # Ham toplamı ağırlıkların toplamına bölerek [-3.5, +3.5] aralığına ölçeklendir
        weighted_avg = weighted_sum / (total_weights + 1e-9)
        normalized_score = round(float(np.clip(weighted_avg * 1.5, -3.5, 3.5)), 2)
        final_score = round(normalized_score * session_multiplier, 2)

        # Küme Konsensüsü
        active_clusters = [c for c, sc in cluster_scores.items() if abs(sc) > 0.15]
        bull_clusters = sum(1 for c, sc in cluster_scores.items() if sc > 0.20)
        bear_clusters = sum(1 for c, sc in cluster_scores.items() if sc < -0.20)

        # Sinyal Çözümleme (Histerezis & Küme Teyidi)
        total_active_clusters = max(len(active_clusters), 2)
        verdict, color, icon = self.processor.resolve_signal_with_hysteresis(
            final_score,
            previous_signal=previous_signal,
            bull_clusters=bull_clusters,
            bear_clusters=bear_clusters,
            min_clusters=max(2, int(np.ceil(total_active_clusters * 0.45)))
        )

        return {
            "verdict": verdict,
            "icon": icon,
            "color": color,
            "score": final_score,
            "cluster_agreement": f"{bull_clusters} Boğa / {bear_clusters} Ayı Kümesi (Aktif: {len(active_clusters)})",
            "session_status": session_status,
            "details": details
        }
