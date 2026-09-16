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

        weighted_avg = weighted_sum / (total_weights + 1e-9)
        final_score = round(float(np.clip(weighted_avg * 1.5, -3.5, 3.5)), 2)

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

    def evaluate_all_assets_harmonized(self, previous_signals=None):
        """Evaluate all configured assets and reconcile only unsupported model divergence."""
        previous_signals = previous_signals or {}
        verdicts={}
        for key in ASSET_MATRICES.keys():
            verdicts[key]=self.evaluate_asset_direction(key, previous_signal=previous_signals.get(key,"NÖTR (BEKLE)"))

        def pair_stats(a_key,b_key,bars=8):
            a=self.grid_1h.get(a_key,pd.DataFrame()); b=self.grid_1h.get(b_key,pd.DataFrame())
            if a is None or b is None or a.empty or b.empty: return None
            if "Close" not in a.columns or "Close" not in b.columns: return None
            ar=pd.to_numeric(a["Close"],errors="coerce").pct_change(); br=pd.to_numeric(b["Close"],errors="coerce").pct_change()
            x=pd.concat([ar.rename("a"),br.rename("b")],axis=1,join="inner").dropna()
            if len(x)<max(20,bars+2): return None
            recent=x.tail(bars); corr=float(recent["a"].corr(recent["b"])) if recent["a"].std()>0 and recent["b"].std()>0 else 0.0
            ra=float((1+recent["a"]).prod()-1); rb=float((1+recent["b"]).prod()-1); spread=rb-ra
            hist=(x["b"]-x["a"]).tail(80); z=float(spread/(hist.std(ddof=1)+1e-12)) if len(hist)>=10 else 0.0
            return {"corr":corr,"anchor_return":ra,"follower_return":rb,"spread":spread,"spread_z":z}

        for anchor,follower,min_corr,evidence_z in (("SPX","NQ",0.70,1.25),("XAU","XAG",0.60,1.35)):
            va,vf=verdicts.get(anchor),verdicts.get(follower)
            if not va or not vf: continue
            st=pair_stats(anchor,follower)
            if st is None: continue
            supported=st["corr"]>=min_corr and abs(st["spread_z"])>=evidence_z and abs(st["spread"])>0
            status="GERÇEK FİYAT AYRIŞMASI TEYİTLİ" if supported else "AYRIŞMA FİYATLA TEYİT EDİLMEDİ"
            va["pair_coherence"]=status; vf["pair_coherence"]=status; va["pair_stats"]=st; vf["pair_stats"]=st
            if not supported:
                av,fv=float(va.get("score",0)),float(vf.get("score",0))
                if abs(av-fv)>0.45:
                    avg=(av+fv)/2; shrink=0.35
                    va["score"]=round(avg+(av-avg)*shrink,2); vf["score"]=round(avg+(fv-avg)*shrink,2)
                anc_verdict=str(va.get("verdict","")); fol_verdict=str(vf.get("verdict",""))
                opposite=("AL" in fol_verdict and "AL" not in anc_verdict) or ("SAT" in fol_verdict and "SAT" not in anc_verdict)
                if opposite:
                    vf.update({"verdict":"NÖTR (FİYAT TEYİDİ YOK)","forecast_direction":"NÖTR (FİYAT TEYİDİ YOK)","forecast_icon":"⚪","forecast_color":"gray","icon":"⚪","color":"gray"})

        # Preserve broad BTC/ETH harmonization without overriding real price divergence.
        vb,ve=verdicts.get("BTC"),verdicts.get("ETH")
        if vb and ve:
            diff=abs(float(vb.get("score",0))-float(ve.get("score",0)))
            if diff<=0.60:
                if float(vb.get("score",0))<=-0.40 and float(ve.get("score",0))<=-0.40:
                    vb["verdict"]=ve["verdict"]="SAT"; vb["forecast_direction"]=ve["forecast_direction"]="SAT"
                elif float(vb.get("score",0))>=0.40 and float(ve.get("score",0))>=0.40:
                    vb["verdict"]=ve["verdict"]="AL"; vb["forecast_direction"]=ve["forecast_direction"]="AL"
        return verdicts
