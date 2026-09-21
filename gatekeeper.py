"""
Gatekeeper: Multi-Asset Engine with 3-Pillar USD Risk, Live Entry Quality Gating & Macro Interpretation (v35)
"""
import os
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

from config import ASSET_MATRICES, CLUSTERS, REGIME_DYNAMIC_THRESHOLDS

try:
    from config import ENTRY_FILTER_CONFIG
except ImportError:
    try:
        from config import ENTRY_GATES_CONFIG as ENTRY_FILTER_CONFIG
    except ImportError:
        ENTRY_FILTER_CONFIG = {
            "vol_shock_high": 2.20,
            "vol_shock_low": 0.65,
            "rvol_strong_min": 1.25,
            "rvol_climax_shock": 3.20,
            "rvol_illiquid": 0.50,
            "mad_z_threshold": 1.96
        }
ENTRY_GATES_CONFIG = ENTRY_FILTER_CONFIG

from data_engine import ResilientDataEngine
from quant_processor import RobustQuantProcessor
from macro_regime_engine import MacroRegimeEngine


class PreTradeGatekeeper:
    def __init__(self, fred_api_key=None, *args, **kwargs):
        if not fred_api_key:
            fred_api_key = kwargs.get("fred_api_key")
        if not fred_api_key:
            fred_api_key = os.environ.get("FRED_API_KEY", "").strip()
        if not fred_api_key:
            try:
                import streamlit as st
                fred_api_key = st.secrets.get("FRED_API_KEY", "").strip()
            except Exception:
                pass
        self.fred_api_key = fred_api_key or ""
        self.data_engine = ResilientDataEngine(fred_api_key=self.fred_api_key)
        self.processor = RobustQuantProcessor()
        self.macro_engine = MacroRegimeEngine(fred_api_key=self.fred_api_key)
        self.grid_1h = {}
        self.active_macro_regime_id = "REJIMSIZ_GECIS"
        self.active_macro_regime_name = "Rejimsiz Geçiş / Veri Yetersiz"
        self.market_regime = "⚪ [REJİMSİZ] Veri Yetersiz"
        self.active_subtype = "VERİ YETERSİZ"
        self.dynamic_thresholds = REGIME_DYNAMIC_THRESHOLDS.get("REJIMSIZ_GECIS", {})
        self.macro_diagnostics = {}
        self.composite_usd_risk = None; self.usd_risk_label = "⚪ VERİ YETERSİZ"; self.usd_risk_status = "UNAVAILABLE"
        self.dxy_velocity = None; self.ndl_z = None; self.current_vix = None; self.stagflation_z = None; self.yen_carry_z = None
        self.real_yield_z = None; self.breakeven_z = None; self.credit_velocity = None; self.anomaly_score = None
        self.crisis_active=False; self.consecutive_breaches=0; self.dfii10_z=None; self.curve_label="VERİ YETERSİZ"

    def refresh_market(self):
        self.grid_1h = self.data_engine.fetch_global_market_grid()
        def has(key, minimum=5):
            df=self.grid_1h.get(key,pd.DataFrame()); return isinstance(df,pd.DataFrame) and len(df)>=minimum
        vix_df=self.grid_1h.get("VIX",pd.DataFrame()); self.current_vix=float(vix_df["Close"].iloc[-1]) if has("VIX",1) else None
        z_vix=self.processor.compute_vix_stress(vix_df) if has("VIX",5) else None
        dxy=self.grid_1h.get("DXY",pd.DataFrame()); self.dxy_velocity=self.processor.compute_usd_strength_impulse(dxy) if has("DXY",5) else None
        hyg,lqd=self.grid_1h.get("HYG",pd.DataFrame()),self.grid_1h.get("LQD",pd.DataFrame()); self.credit_velocity=self.processor.compute_credit_intraday_velocity(hyg,lqd) if has("HYG",5) and has("LQD",5) else None
        oil,transport=self.grid_1h.get("CL=F",pd.DataFrame()),self.grid_1h.get("IYT",pd.DataFrame()); self.stagflation_z=self.processor.compute_stagflation_shock(oil,transport) if has("CL=F",5) and has("IYT",5) else None
        uj=self.grid_1h.get("USDJPY=X",pd.DataFrame()); self.yen_carry_z=self.processor.compute_yen_carry_shock(uj) if has("USDJPY=X",5) else None
        fred=self.data_engine.fetch_fred_macro_metrics(self.grid_1h)
        self.real_yield_z=fred.get("dfii10_z"); self.breakeven_z=fred.get("t10yie_z"); self.dfii10_z=self.real_yield_z; self.curve_label=fred.get("curve_label","VERİ YETERSİZ"); self.ndl_z=fred.get("ndl_z")
        if all(x is not None for x in (self.dxy_velocity,self.ndl_z,self.yen_carry_z)):
            self.composite_usd_risk,self.usd_risk_label,self.usd_risk_status=self.processor.compute_composite_usd_risk(self.dxy_velocity,self.ndl_z,self.yen_carry_z)
        else:
            self.composite_usd_risk,self.usd_risk_label,self.usd_risk_status=None,"⚪ VERİ YETERSİZ","UNAVAILABLE"
        payload=dict(fred)
        for key,val in (("dxy_velocity_z",self.dxy_velocity),("credit_velocity_z",self.credit_velocity),("z_vix",z_vix),("oil_z",self.stagflation_z),("yen_carry_z",self.yen_carry_z)):
            if val is not None: payload[key]=val
        self.macro_diagnostics=self.macro_engine.evaluate(payload)
        self.active_macro_regime_id=self.macro_diagnostics["active_regime_id"]; self.active_macro_regime_name=self.macro_diagnostics["active_regime_name"]; self.market_regime=self.macro_diagnostics["formatted_label"]; self.active_subtype=self.macro_diagnostics["active_regime_subtype"]; self.dynamic_thresholds=self.macro_diagnostics["dynamic_thresholds"]
        if all(x is not None for x in (self.credit_velocity,z_vix,self.real_yield_z,self.dxy_velocity,self.current_vix)):
            self.crisis_active,self.anomaly_score,_=self.processor.evaluate_crisis_lock_with_hysteresis(self.credit_velocity,z_vix,self.real_yield_z,self.dxy_velocity,self.current_vix,self.crisis_active,self.consecutive_breaches)
            self.consecutive_breaches=self.consecutive_breaches+1 if self.crisis_active else 0
        else:
            self.crisis_active=False; self.anomaly_score=None; self.consecutive_breaches=0

    def evaluate_asset_direction(self, asset_key, previous_signal="NÖTR (BEKLE)"):
        matrix = ASSET_MATRICES.get(asset_key, {})
        if not matrix:
            return {
                "verdict": "NÖTR (BEKLE)",
                "forecast_direction": "NÖTR (BEKLE)",
                "current_direction": "⚪ YATAY (%0.00)",
                "score": 0.0,
                "entry_allowed": True,
                "entry_reason": "Veri yok",
                "details": []
            }

        symbol = matrix.get("benchmark_symbol", "ES=F")
        clean_sym = symbol.replace("^", "").replace("=X", "").replace("=F", "")
        df_ast = self.grid_1h.get(clean_sym, self.grid_1h.get(symbol, pd.DataFrame()))

        # 🎯 Doğru Yön Analizi (Eşikler gerçekçi)
        current_dir, current_icon, current_color, current_roc = self.processor.compute_realtime_price_action(
            df_ast, vol_scale=matrix.get("vol_scale", 1.0), asset_key=asset_key
        )
        adx_val, adx_regime = self.processor.compute_adx(df_ast)

        # 🚀 Dinamik Giriş Analizi (ATR ve RVOL canlı hesaplanır)
        entry_allowed, entry_reason, atr_ratio, rvol = self.processor.evaluate_trade_entry_gate(
            df_ast, asset_key=asset_key
        )

        volume_supports = rvol >= ENTRY_FILTER_CONFIG.get("rvol_strong_min", 1.25)
        volatility_supports = (ENTRY_FILTER_CONFIG.get("vol_shock_low", 0.65) <= atr_ratio <= ENTRY_FILTER_CONFIG.get("vol_shock_high", 2.20))

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
                "entry_allowed": False,
                "entry_reason": "Sistemik Kriz Kilidi Devrede: Yeni pozisyon açılamaz!",
                "entry_status": "🔴 İŞLEME GİRİŞ ÖNERİLMEZ",
                "volume_supports": False,
                "volatility_supports": False,
                "rvol": round(rvol, 2),
                "atr_ratio": round(atr_ratio, 2),
                "cluster_agreement": "Tüm Pozisyonlar Askıda",
                "session_status": "KİLİTLİ",
                "details": []
            }

        session_status, _ = self.processor.get_asset_session_status(asset_key)

        weighted_sum = 0.0
        total_weights = 0.0
        cluster_scores = {c: 0.0 for c in CLUSTERS.keys()}
        details = []

        ccy = matrix.get("crypto_ccy", "BTC")
        crypto_flow = None
        crypto_fr = None

        for factor in matrix.get("factors", []):
            f_id = factor["id"]
            cluster = factor["cluster"]
            weight = factor["base_weight"]
            sign = factor["base_sign"]

            val = 0.0

            required_missing = {
                "equity_duration_drag": self.real_yield_z is None,
                "gold_sovereign_decoupling": self.real_yield_z is None,
                "usd_strength": self.dxy_velocity is None,
                "net_dollar_liquidity": self.ndl_z is None,
                "usd_jpy_carry": self.yen_carry_z is None,
                "credit_spread": self.credit_velocity is None,
                "real_yield": self.real_yield_z is None,
                "breakeven_infl": self.breakeven_z is None,
                "stagflation_shock": self.stagflation_z is None,
            }
            if required_missing.get(f_id, False):
                details.append({
                    "faktör": factor["name"], "küme": cluster,
                    "ham_deger": None, "puan": None,
                    "durum": "GEREKLİ GERÇEK GİRDİ YOK"
                })
                continue

            if f_id == "asset_direction":
                vol_scale = matrix.get("vol_scale", 1.0)
                if asset_key == "XAU":
                    val = self.processor.compute_intraday_direction_momentum(
                        df_ast, fast_window=2, slow_window=16, vol_scale=0.90
                    )
                elif asset_key == "XAG":
                    val = self.processor.compute_intraday_direction_momentum(
                        df_ast, fast_window=4, slow_window=24, vol_scale=1.25
                    )
                else:
                    val = self.processor.compute_intraday_direction_momentum(
                        df_ast, vol_scale=vol_scale
                    )
            elif f_id == "gold_macro_lead":
                val = self.processor.compute_gold_macro_lead(
                    df_ast,
                    self.grid_1h.get("DXY", pd.DataFrame()),
                    self.grid_1h.get("TLT", pd.DataFrame()),
                    self.grid_1h.get("USDJPY", pd.DataFrame())
                )
            elif f_id == "crypto_taker":
                if crypto_flow is None:
                    crypto_flow = self.data_engine.fetch_crypto_taker_flow(ccy)
                raw_ratio = crypto_flow.get("value") if isinstance(crypto_flow, dict) else None
                if raw_ratio is None:
                    val = None
                    continue
                val = float(np.tanh(np.log(raw_ratio + 1e-6) * 2.0) * 1.5)
            elif f_id == "funding_stress":
                if crypto_fr is None:
                    crypto_fr = self.data_engine.fetch_crypto_funding_rate(ccy)
                rate = crypto_fr.get("rate") if isinstance(crypto_fr, dict) else None
                val = self.processor.compute_crypto_funding_stress(rate) if rate is not None else None
            elif f_id == "stablecoin_usd_impulse":
                if crypto_flow is None:
                    crypto_flow = self.data_engine.fetch_crypto_taker_flow(ccy)
                if crypto_fr is None:
                    crypto_fr = self.data_engine.fetch_crypto_funding_rate(ccy)
                flow_value = crypto_flow.get("value") if isinstance(crypto_flow, dict) else None
                funding_value = crypto_fr.get("rate") if isinstance(crypto_fr, dict) else None
                if flow_value is None or funding_value is None or self.ndl_z is None:
                    val = None
                else:
                    val = self.processor.compute_crypto_stablecoin_usd_impulse(
                        flow_value, funding_value, self.ndl_z
                    )
            elif f_id == "liquidation_squeeze_risk":
                if crypto_fr is None:
                    crypto_fr = self.data_engine.fetch_crypto_funding_rate(ccy)
                rate = crypto_fr.get("rate") if isinstance(crypto_fr, dict) else None
                val = self.processor.compute_liquidation_squeeze_risk(rate, df_ast) if rate is not None else None
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
            elif f_id == "tech_breadth_dispersion":
                val = self.processor.compute_tech_breadth_dispersion(
                    self.grid_1h.get("SMH", pd.DataFrame()),
                    self.grid_1h.get("ARKK", pd.DataFrame()),
                    self.grid_1h.get("QQQ", pd.DataFrame())
                )
            elif f_id == "equity_duration_drag":
                val = self.processor.compute_equity_duration_drag(df_ast, self.real_yield_z)
            elif f_id == "gold_sovereign_decoupling":
                val = self.processor.compute_gold_sovereign_decoupling(
                    df_ast, self.real_yield_z, self.grid_1h.get("DXY", pd.DataFrame())
                )
            elif f_id == "silver_monetary_catchup":
                val = self.processor.compute_silver_monetary_catchup(
                    df_ast,
                    self.grid_1h.get("GC", self.grid_1h.get("GC=F", pd.DataFrame())),
                    self.grid_1h.get("HG", self.grid_1h.get("HG=F", pd.DataFrame()))
                )
            elif f_id == "eth_staking_utility_drift":
                val = self.processor.compute_eth_staking_utility_drift(
                    df_ast, self.grid_1h.get("BTC-USD", pd.DataFrame())
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
                df_hg = self.grid_1h.get("HG", self.grid_1h.get("HG=F", pd.DataFrame()))
                val = self.processor.compute_silver_gold_anchor(
                    df_ast, df_gc, df_hg
                )
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
            elif f_id == "net_dollar_liquidity":
                val = float(np.clip(self.ndl_z, -2.0, 2.0)) if self.ndl_z is not None else None
            elif f_id == "usd_jpy_carry":
                val = self.yen_carry_z
            elif f_id == "credit_spread":
                val = self.credit_velocity
            elif f_id == "vix_strain":
                vix_df = self.grid_1h.get("VIX", pd.DataFrame())
                val = self.processor.compute_vix_stress(vix_df) if not vix_df.empty else None
            elif f_id == "real_yield":
                val = self.real_yield_z
            elif f_id == "breakeven_infl":
                val = self.breakeven_z
            elif f_id == "safe_haven":
                vix_df = self.grid_1h.get("VIX", pd.DataFrame())
                val = self.processor.compute_vix_stress(vix_df) if not vix_df.empty else None
            elif f_id == "stagflation_shock":
                val = self.stagflation_z

            if val is None or not np.isfinite(float(val)):
                details.append({
                    "faktör": factor["name"], "küme": cluster,
                    "ham_deger": None, "puan": None,
                    "durum": "VERİ YETERSİZ / KATKI DIŞI"
                })
                continue
            f_score = float(np.clip(float(val), -1.8, 1.8)) * sign * weight
            weighted_sum += f_score
            total_weights += weight
            cluster_scores[cluster] += f_score
            details.append({
                "faktör": factor["name"], "küme": cluster,
                "ham_deger": round(float(val), 2), "puan": round(f_score, 2)
            })

        # XAU-ONLY DYNAMIC SILVER PEER EVIDENCE
        # ---------------------------------------------------------------
        # This is part of XAU's model score, not a post-hoc verdict override.
        # It uses only real GC=F/SI=F price history plus XAG's existing
        # continuous model score. No fixed price-gap trigger is used.
        xau_silver_peer = None
        peer_adjustment = 0.0
        if asset_key == "XAU":
            try:
                xag_df = self.grid_1h.get("XAG", self.grid_1h.get("SI=F", pd.DataFrame()))
                xag_score, _ = self.processor.compute_direction_score(xag_df) if isinstance(xag_df, pd.DataFrame) and not xag_df.empty else (None, None)
                xau_silver_peer = self._dynamic_xau_silver_peer_adjustment(
                    df_ast, xag_df, xag_score
                )
            except Exception:
                xau_silver_peer = None

            if xau_silver_peer is not None:
                peer_adjustment = float(xau_silver_peer["adjustment"])

        weighted_avg = weighted_sum / (total_weights + 1e-9)
        final_score = round(float(np.clip(weighted_avg * 1.5 + peer_adjustment, -3.5, 3.5)), 2)

        if asset_key == "XAU" and xau_silver_peer is not None:
            details.append({
                "faktör": "🥈 Gümüş Dinamik Eş-Hareket Teyidi",
                "küme": "E",
                "ham_deger": round(float(xau_silver_peer["peer_signal"]), 2),
                "puan": round(float(peer_adjustment), 2),
                "durum": "GERÇEK GC=F/SI=F İSTATİSTİKSEL İLİŞKİ",
                "lag_hours": int(xau_silver_peer["lag_hours"]),
                "corr": round(float(xau_silver_peer["corr"]), 3),
                "r2": round(float(xau_silver_peer["r2"]), 3),
                "beta": round(float(xau_silver_peer["beta"]), 4),
                "confidence": round(float(xau_silver_peer["confidence"]), 3),
            })

        active_clusters = [c for c, sc in cluster_scores.items() if abs(sc) > 0.15]
        bull_clusters = sum(1 for c, sc in cluster_scores.items() if sc > 0.20)
        bear_clusters = sum(1 for c, sc in cluster_scores.items() if sc < -0.20)

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
            active_regime_id=self.active_macro_regime_id,
            entry_allowed=entry_allowed,
            volume_supports=volume_supports,
            volatility_supports=volatility_supports
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
            "entry_allowed": entry_allowed,
            "entry_status": "🟢 İŞLEME GİRİŞ ÖNERİLİR" if entry_allowed else "🔴 İŞLEME GİRİŞ ÖNERİLMEZ",
            "entry_reason": entry_reason,
            "volume_supports": volume_supports,
            "volatility_supports": volatility_supports,
            "rvol": round(rvol, 2),
            "atr_ratio": round(atr_ratio, 2),
            "cluster_agreement": f"{bull_clusters} Boğa / {bear_clusters} Ayı Kümesi (Aktif: {len(active_clusters)})",
            "session_status": session_status,
            "adx_val": adx_val,
            "adx_regime": adx_regime,
            "active_regime_id": self.active_macro_regime_id,
            "active_regime_name": self.active_macro_regime_name,
            "active_subtype": self.active_subtype,
            "dynamic_thresholds": self.dynamic_thresholds,
            "composite_usd_risk": self.composite_usd_risk,
            "usd_risk_label": self.usd_risk_label,
            "details": details
        }

    @staticmethod
    def _dynamic_xau_silver_peer_adjustment(xau_df, xag_df, xag_score):
        """
        XAU-only continuous peer evidence from real GC=F and SI=F data.

        It learns the strongest positive contemporaneous/forward relationship
        between SI=F and GC=F over the observed return history, estimates a
        rolling beta, measures fit/stability, and converts the existing XAG
        model score into a bounded confidence-weighted XAU score adjustment.

        It never copies the XAG verdict and never modifies XAG or any other
        asset. Missing/weak relationship => adjustment tends to zero.
        """
        if xag_score is None:
            return None
        if not isinstance(xau_df, pd.DataFrame) or not isinstance(xag_df, pd.DataFrame):
            return None
        if xau_df.empty or xag_df.empty:
            return None
        if "Close" not in xau_df.columns or "Close" not in xag_df.columns:
            return None

        au = pd.to_numeric(xau_df["Close"], errors="coerce")
        ag = pd.to_numeric(xag_df["Close"], errors="coerce")
        aligned = pd.concat([au.rename("gold"), ag.rename("silver")], axis=1, join="inner").dropna()
        aligned = aligned.tail(150)
        if len(aligned) < 50:
            return None

        returns = aligned.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
        if len(returns) < 45:
            return None

        # Search only for relationships that allow XAG to be a same/earlier
        # observation relative to XAU. The lag is learned from data.
        candidates = []
        for lag in range(0, 4):
            sample = pd.concat(
                [returns["silver"].shift(lag).rename("silver"), returns["gold"].rename("gold")],
                axis=1,
            ).dropna()
            if len(sample) < 35:
                continue
            corr = float(sample["silver"].corr(sample["gold"]))
            if not np.isfinite(corr) or corr <= 0:
                continue
            n = len(sample)
            t_stat = corr * np.sqrt(max(n - 2, 1) / max(1.0 - corr * corr, 1e-12))
            # Slight preference to stable relationship rather than a single
            # accidental maximum correlation.
            mid = max(15, len(sample) // 2)
            c1 = float(sample.iloc[:mid]["silver"].corr(sample.iloc[:mid]["gold"]))
            c2 = float(sample.iloc[-mid:]["silver"].corr(sample.iloc[-mid:]["gold"]))
            stability = float(np.clip(np.nanmean([max(c1, 0.0), max(c2, 0.0)]), 0.0, 1.0))
            rank = t_stat * (0.70 + 0.30 * stability)
            candidates.append((rank, corr, lag, sample, stability))

        if not candidates:
            return None

        _, corr, lag, sample, stability = max(candidates, key=lambda item: item[0])
        fit = sample.iloc[:-1]
        if len(fit) < 30:
            return None

        xs = fit["silver"].to_numpy(dtype=float)
        ys = fit["gold"].to_numpy(dtype=float)
        x_mean = float(np.mean(xs))
        y_mean = float(np.mean(ys))
        x_centered = xs - x_mean
        y_centered = ys - y_mean
        denom = float(np.sum(x_centered * x_centered))
        if denom <= 1e-14:
            return None

        beta = float(np.sum(x_centered * y_centered) / denom)
        if not np.isfinite(beta) or beta <= 0:
            return None

        intercept = y_mean - beta * x_mean
        pred = intercept + beta * xs
        ss_res = float(np.sum((ys - pred) ** 2))
        ss_tot = float(np.sum((ys - y_mean) ** 2))
        r2 = float(np.clip(1.0 - ss_res / (ss_tot + 1e-12), 0.0, 1.0))

        n = len(fit)
        t_stat = corr * np.sqrt(max(n - 2, 1) / max(1.0 - corr * corr, 1e-12))
        sig_conf = float(np.clip((t_stat - 1.0) / 3.0, 0.0, 1.0))
        fit_conf = float(np.sqrt(r2))
        sample_conf = float(np.clip(n / 80.0, 0.0, 1.0))
        confidence = float(np.clip(sig_conf * fit_conf * stability * sample_conf, 0.0, 1.0))
        if confidence <= 0.05:
            return None

        # XAG's existing model score is used continuously rather than as AL/SAT.
        peer_model = float(np.clip(np.tanh(float(xag_score) / 1.25) * 1.8, -1.8, 1.8))

        # Add an independent real-price component from SI=F's recent 4H move.
        ag_ret = returns["silver"]
        current_4h = ag_ret.tail(min(4, len(ag_ret)))
        current_impulse = float((1.0 + current_4h).prod() - 1.0)
        hist_impulses = []
        for i in range(4, len(ag_ret)):
            w = ag_ret.iloc[i - 4:i]
            hist_impulses.append(float((1.0 + w).prod() - 1.0))
        if len(hist_impulses) >= 20:
            arr = np.asarray(hist_impulses, dtype=float)
            med = float(np.median(arr))
            mad_scale = float(np.median(np.abs(arr - med)) * 1.4826)
            if not np.isfinite(mad_scale) or mad_scale <= 1e-12:
                mad_scale = float(np.std(arr))
            price_signal = float(np.clip((current_impulse - med) / (mad_scale + 1e-12), -1.8, 1.8)) if mad_scale > 0 else 0.0
        else:
            price_signal = 0.0

        peer_signal = float(np.clip(0.70 * peer_model + 0.30 * price_signal, -1.8, 1.8))

        # If XAU's own score is strongly opposite, reduce the transfer smoothly
        # instead of forcing XAU to follow silver.
        xau_existing_score = None
        # The caller intentionally does not pass the XAU score into this helper,
        # so no extra decision gate is created here. The relationship confidence
        # itself is the limiter.

        adjustment = float(np.clip(peer_signal * confidence * 0.95, -0.95, 0.95))

        return {
            "adjustment": adjustment,
            "peer_signal": peer_signal,
            "corr": corr,
            "r2": r2,
            "beta": beta,
            "confidence": confidence,
            "lag_hours": lag,
        }

    def evaluate_all_assets_harmonized(self, previous_signals=None):
        """Evaluate all assets and reconcile unsupported pair divergence from real prices."""
        previous_signals = previous_signals or {}
        verdicts = {
            key: self.evaluate_asset_direction(
                key, previous_signal=previous_signals.get(key, "NÖTR (BEKLE)")
            )
            for key in ASSET_MATRICES.keys()
        }

        pair_specs = (
            ("SPX", "NQ", 0.70, 1.25),
            ("XAU", "XAG", 0.60, 1.35),
        )

        def pair_stats(anchor_key, follower_key, bars=8):
            a = self.grid_1h.get(anchor_key, pd.DataFrame())
            b = self.grid_1h.get(follower_key, pd.DataFrame())
            if not isinstance(a, pd.DataFrame) or not isinstance(b, pd.DataFrame) or a.empty or b.empty:
                return None
            if "Close" not in a.columns or "Close" not in b.columns:
                return None

            ar = pd.to_numeric(a["Close"], errors="coerce").pct_change()
            br = pd.to_numeric(b["Close"], errors="coerce").pct_change()
            x = pd.concat([ar.rename("a"), br.rename("b")], axis=1, join="inner").dropna()
            if len(x) < max(24, bars + 5):
                return None

            recent = x.tail(bars)
            corr = float(recent["a"].corr(recent["b"])) if recent["a"].std() > 0 and recent["b"].std() > 0 else 0.0
            anchor_ret = float((1.0 + recent["a"]).prod() - 1.0)
            follower_ret = float((1.0 + recent["b"]).prod() - 1.0)
            spread = follower_ret - anchor_ret

            spread_series = (x["b"] - x["a"]).dropna()
            hist = spread_series.tail(min(120, len(spread_series)))
            std = float(hist.std(ddof=1)) if len(hist) >= 10 else 0.0
            spread_z = float(spread / (std + 1e-12)) if std > 1e-12 else 0.0

            # 1H signs are useful for display coherence but not enough to prove divergence.
            anchor_1h = float(ar.iloc[-1]) if np.isfinite(ar.iloc[-1]) else 0.0
            follower_1h = float(br.iloc[-1]) if np.isfinite(br.iloc[-1]) else 0.0
            return {
                "corr": corr,
                "anchor_return": anchor_ret,
                "follower_return": follower_ret,
                "spread": spread,
                "spread_z": spread_z,
                "anchor_1h": anchor_1h,
                "follower_1h": follower_1h,
            }

        for anchor, follower, min_corr, evidence_z in pair_specs:
            va = verdicts.get(anchor)
            vf = verdicts.get(follower)
            if not va or not vf:
                continue

            stats = pair_stats(anchor, follower)
            if stats is None:
                va["pair_coherence"] = vf["pair_coherence"] = "FİYAT KARŞILAŞTIRMASI İÇİN VERİ YETERSİZ"
                continue

            price_supported = (
                stats["corr"] >= min_corr
                and abs(stats["spread_z"]) >= evidence_z
                and abs(stats["spread"]) > 0
            )

            status = (
                "GERÇEK FİYAT AYRIŞMASI TEYİTLİ"
                if price_supported
                else "AYRIŞMA FİYATLA TEYİT EDİLMEDİ"
            )
            va["pair_coherence"] = vf["pair_coherence"] = status
            va["pair_stats"] = vf["pair_stats"] = stats

            # ---------------------------------------------------------
            # CURRENT DIRECTION COHERENCE
            # ---------------------------------------------------------
            # XAU/XAG and SPX/NQ should not show opposite/noisy short-term
            # directions when the real price series move together. If real
            # divergence is not statistically supported, classify both from
            # the pair-average model-direction score while retaining each
            # asset's actual ROC in the label.
            if not price_supported:
                qa, sa = self.processor.compute_direction_score(
                    self.grid_1h.get(anchor, pd.DataFrame())
                )
                qf, sf = self.processor.compute_direction_score(
                    self.grid_1h.get(follower, pd.DataFrame())
                )

                if qa is not None and qf is not None and sa is not None and sf is not None:
                    qa_f = float(qa)
                    qf_f = float(qf)
                    # When both legs agree in sign, the weaker leg caps the
                    # common direction. One outlier therefore cannot force
                    # the pair into a directional label. Opposite signs use
                    # the mean, naturally moving the pair toward neutral
                    # unless the real price spread is independently supported.
                    if qa_f == 0.0 or qf_f == 0.0:
                        pair_score = 0.0
                    elif np.sign(qa_f) == np.sign(qf_f):
                        pair_score = float(np.sign(qa_f) * min(abs(qa_f), abs(qf_f)))
                    else:
                        pair_score = 0.50 * qa_f + 0.50 * qf_f

                    va["current_direction"], va["current_icon"], va["current_color"], _ = self.processor.format_direction_score(
                        pair_score, sa["roc_1h"]
                    )
                    vf["current_direction"], vf["current_icon"], vf["current_color"], _ = self.processor.format_direction_score(
                        pair_score, sf["roc_1h"]
                    )

                    va["pair_direction_score"] = round(pair_score, 3)
                    vf["pair_direction_score"] = round(pair_score, 3)

                # Unsupported one-sided model signal gets neutralized.
                anc_verdict = str(va.get("verdict", ""))
                fol_verdict = str(vf.get("verdict", ""))
                opposite_one_sided = (
                    ("AL" in fol_verdict and "AL" not in anc_verdict)
                    or ("SAT" in fol_verdict and "SAT" not in anc_verdict)
                )
                if opposite_one_sided:
                    vf.update({
                        "verdict": "NÖTR (FİYAT TEYİDİ YOK)",
                        "forecast_direction": "NÖTR (FİYAT TEYİDİ YOK)",
                        "forecast_icon": "⚪",
                        "forecast_color": "gray",
                        "icon": "⚪",
                        "color": "gray",
                    })

                    va["pair_model_reconciliation"] = "TEK TARAFLI MODEL SİNYALİ BASTIRILDI"
                    vf["pair_model_reconciliation"] = "TEK TARAFLI MODEL SİNYALİ BASTIRILDI"

        # BTC/ETH broad sympathy is kept intentionally soft; genuine divergence
        # is not overwritten here.
        vb, ve = verdicts.get("BTC"), verdicts.get("ETH")
        if vb and ve:
            diff = abs(float(vb.get("score", 0.0)) - float(ve.get("score", 0.0)))
            if diff <= 0.60:
                if float(vb.get("score", 0.0)) <= -0.40 and float(ve.get("score", 0.0)) <= -0.40:
                    vb["verdict"] = ve["verdict"] = "SAT"
                    vb["forecast_direction"] = ve["forecast_direction"] = "SAT"
                elif float(vb.get("score", 0.0)) >= 0.40 and float(ve.get("score", 0.0)) >= 0.40:
                    vb["verdict"] = ve["verdict"] = "AL"
                    vb["forecast_direction"] = ve["forecast_direction"] = "AL"

        return verdicts
