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
from dynamic_pair_model import DynamicPairModel, XAG_XAU_MODEL, NQ_SPX_MODEL, SPX_NQ_MODEL, ETH_BTC_MODEL
from timeframe_confluence import evaluate_confluence, TimeframeReliabilityStore

# Symbols that need a genuine 1D (HTF) series fetched for multi-timeframe
# confluence and/or feed the relative-value pair models above.
_DAILY_FETCH_SYMBOLS = {
    "SPX": "ES=F", "NQ": "NQ=F", "XAU": "GC=F", "XAG": "SI=F",
    "HG": "HG=F", "BTC-USD": "BTC-USD", "ETH-USD": "ETH-USD",
}

# (anchor, follower) -> the DynamicPairModel that already measures follower's
# divergence FROM anchor. Used to replace the old hand-tuned, per-pair
# (min_corr, evidence_z) literals in the pair-reconciliation steps below --
# those numbers were asymmetric across pairs (BTC/ETH's evidence_z=1.20 vs
# SPX/NQ's 1.25 and XAU/XAG's 1.35), which meant BTC/ETH divergence was
# confirmed-as-real (and therefore left unreconciled/shown to the user) far
# more easily than the other two pairs -- a structural bias, not a genuine
# crypto-specific property. Every pair now clears the SAME kind of bar: its
# own adaptive residual-z threshold (see dynamic_pair_model.py).
_RECONCILIATION_PAIR_MODELS = {
    ("SPX", "NQ"): NQ_SPX_MODEL,
    ("XAU", "XAG"): XAG_XAU_MODEL,
    ("BTC", "ETH"): ETH_BTC_MODEL,
}


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
        self.grid_daily = {}
        self.tf_store = TimeframeReliabilityStore()
        self._pair_state_cache = {}
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
        self._pair_state_cache = {}
        self.grid_daily = {}
        for alias_key, yf_symbol in _DAILY_FETCH_SYMBOLS.items():
            try:
                _, daily_df = self.data_engine.fetch_single_ticker_daily(yf_symbol)
                if isinstance(daily_df, pd.DataFrame) and not daily_df.empty:
                    self.grid_daily[alias_key] = daily_df
            except Exception:
                # Daily HTF leg is additive; its absence must never break the
                # existing 1H pipeline. evaluate_confluence() degrades to
                # resampled-1H HTF, or skips the HTF rung entirely when even
                # that has too little history -- see timeframe_confluence.py.
                pass

        # Self-improving loop, step 1: before recording any NEW timeframe
        # predictions this cycle, settle whatever predictions from earlier
        # cycles have reached their horizon, using this cycle's fresh
        # closes. This is what lets TimeframeReliabilityStore's weights
        # actually learn from live outcomes instead of sitting at their
        # prior forever.
        try:
            current_prices = {}
            for asset_key in ASSET_MATRICES.keys():
                df = self.grid_1h.get(asset_key)
                if isinstance(df, pd.DataFrame) and not df.empty and "Close" in df.columns:
                    last_close = pd.to_numeric(df["Close"], errors="coerce").dropna()
                    if not last_close.empty:
                        current_prices[asset_key] = float(last_close.iloc[-1])
            if current_prices:
                self.tf_store.settle_due_predictions(current_prices)
        except Exception:
            # Settlement is best-effort bookkeeping; it must never block a
            # market refresh.
            pass

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

    def _pair_state(self, model):
        """Fits a DynamicPairModel at most once per refresh_market() cycle
        (all three assets can call this for the same pair within one
        refresh, e.g. both legs of NQ~SPX)."""
        key = model.model if hasattr(model, "model") else id(model)
        key = f"{model.dependent}~{'+'.join(model.anchors)}"
        if key not in self._pair_state_cache:
            self._pair_state_cache[key] = model.fit(self.grid_1h)
        return self._pair_state_cache[key]

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

        # 🧭 HTF/MTF/LTF Confluence: "tüm zaman dilimleri onaylı mı?" gate.
        # Uses a real fetched daily series when available (self.grid_daily),
        # otherwise resamples the 1H grid; if even that lacks enough bars
        # for the HTF rung, the gate is skipped rather than faked (no
        # confident-looking answer from insufficient history).
        daily_key = asset_key if asset_key in self.grid_daily else clean_sym
        df_daily_htf = self.grid_daily.get(daily_key, self.grid_daily.get(symbol))
        confluence = evaluate_confluence(
            df_ast, asset_key=asset_key, regime_id=self.active_macro_regime_id,
            store=self.tf_store, df_daily=df_daily_htf,
        )
        htf_available = bool(confluence.get("timeframes", {}).get("HTF_1D", {}).get("available"))
        if entry_allowed and htf_available and not confluence.get("entry_confirmed", True):
            entry_allowed = False
            entry_reason = (
                f"{entry_reason} | HTF/LTF confluence yetersiz "
                f"(skor {confluence.get('confluence_score')}, "
                f"tüm zaman dilimleri onaylı: {confluence.get('all_aligned')})"
            )

        # Self-improving loop, step 2: record this cycle's per-timeframe
        # directional call so a future cycle's refresh_market() can grade it
        # once its horizon elapses (see settle_due_predictions above).
        try:
            last_close_series = pd.to_numeric(df_ast["Close"], errors="coerce").dropna() if "Close" in df_ast.columns else pd.Series(dtype=float)
            if not last_close_series.empty:
                reference_price = float(last_close_series.iloc[-1])
                _horizon_hours_by_tf = {"HTF_1D": 24.0, "MTF_4H": 12.0, "LTF_1H": 4.0}
                for tf_label, tf_info in confluence.get("timeframes", {}).items():
                    if not tf_info.get("available"):
                        continue
                    tf_score = float(tf_info.get("score", 0.0))
                    if abs(tf_score) <= 0.05:
                        continue  # too close to flat to call a direction
                    self.tf_store.record_prediction(
                        asset_key=asset_key,
                        regime_id=self.active_macro_regime_id,
                        timeframe=tf_label,
                        direction_sign=1 if tf_score > 0 else -1,
                        reference_price=reference_price,
                        horizon_hours=_horizon_hours_by_tf.get(tf_label, 8.0),
                    )
        except Exception:
            pass

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
        factor_failures = []

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

            try:
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
                    # Was a fixed two-regime blend (0.82/0.13/0.05 vs
                    # 0.55/0.35/0.10 at a hardcoded |z|<1.5 cutoff). Now a
                    # continuous, model-derived blend: beta comes from a
                    # recency-weighted ridge fit of XAG on XAU+HG instead of
                    # a fixed "82% gold sympathy" assumption, and the
                    # anchor/own-momentum mix shifts smoothly with how much
                    # the residual actually supports divergence.
                    df_gc = self.grid_1h.get("GC", self.grid_1h.get("GC=F", pd.DataFrame()))
                    gold_signal = self.processor.compute_intraday_direction_momentum(
                        df_gc, fast_window=2, slow_window=16, vol_scale=0.90
                    ) if not df_gc.empty else 0.0
                    silver_signal = self.processor.compute_intraday_direction_momentum(
                        df_ast, fast_window=4, slow_window=24, vol_scale=1.25
                    )
                    xag_xau_state = self._pair_state(XAG_XAU_MODEL)
                    val = DynamicPairModel.blended_anchor_signal(xag_xau_state, silver_signal, gold_signal)
                elif f_id == "gold_divergence_residual":
                    # New: dedicated divergence-only signal for XAG vs its
                    # XAU/HG-implied "fair" move. Near 0 when silver is just
                    # following gold/copper as usual; only moves away from 0
                    # when silver is genuinely decoupling -- this is the
                    # ayrışma (divergence) detector that did not exist before.
                    xag_xau_state = self._pair_state(XAG_XAU_MODEL)
                    val = DynamicPairModel.factor_signal(xag_xau_state)
                elif f_id == "btc_sympathy":
                    # Was literally BTC's own raw momentum re-used verbatim as
                    # an ETH factor (not a sympathy/anchor measure at all).
                    # Now a genuine anchor blend using the ETH~BTC pair fit.
                    df_btc = self.grid_1h.get("BTC-USD", pd.DataFrame())
                    btc_signal = self.processor.compute_intraday_direction_momentum(df_btc, vol_scale=1.8) if not df_btc.empty else 0.0
                    eth_signal = self.processor.compute_intraday_direction_momentum(df_ast, vol_scale=matrix.get("vol_scale", 1.0))
                    eth_btc_state = self._pair_state(ETH_BTC_MODEL)
                    val = DynamicPairModel.blended_anchor_signal(eth_btc_state, eth_signal, btc_signal)
                elif f_id == "eth_btc_beta":
                    # Was a raw price-ratio MAD z-score (conflates price
                    # level drift with genuine relative-value divergence).
                    # Now the regression residual z-score from a proper
                    # ETH ~ BTC beta fit -- the same divergence-detection
                    # math already proven on XAU/XAG, applied here.
                    eth_btc_state = self._pair_state(ETH_BTC_MODEL)
                    val = DynamicPairModel.factor_signal(eth_btc_state)
                elif f_id == "spx_relative_divergence":
                    # New factor (NQ only): NQ did not have ANY cross-asset
                    # divergence detector versus SPX before. Positive = NQ
                    # pulling away to the upside beyond what its usual beta
                    # to SPX would predict; negative = downside decoupling.
                    nq_spx_state = self._pair_state(NQ_SPX_MODEL)
                    val = DynamicPairModel.factor_signal(nq_spx_state)
                elif f_id == "nq_relative_divergence":
                    # Symmetric counterpart on the SPX side (separate
                    # regression: SPX ~ NQ, not just the sign-flip of the
                    # factor above -- a reverse OLS/ridge fit minimizes a
                    # different residual and is the statistically correct
                    # way to give SPX its own view of the same pair).
                    spx_nq_state = self._pair_state(SPX_NQ_MODEL)
                    val = DynamicPairModel.factor_signal(spx_nq_state)
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
            except Exception as factor_exc:
                val = None
                factor_failures.append({"faktör": factor.get("name", f_id), "id": f_id, "hata": str(factor_exc)})

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
            "details": details,
            "factor_failures": factor_failures,
            "factor_failure_count": len(factor_failures),
            "factor_total_count": len(matrix.get("factors", [])),
            "timeframe_confluence": confluence,
        }

    def _safe_evaluate_asset_direction(self, key, previous_signal):
        """
        Tek bir varlığın değerlendirmesi beklenmedik biçimde patlarsa (örn.
        canlı veri akışında geçici bir bozukluk), bu artık TÜM yenileme
        döngüsünü ve dolayısıyla ekrandaki diğer varlıkları da çökertmemeli.
        Sorunlu varlık VERİ YETERSİZ olarak işaretlenir, döngü devam eder.
        """
        try:
            return self.evaluate_asset_direction(key, previous_signal=previous_signal)
        except Exception as exc:
            return {
                "verdict": "NÖTR (BEKLE)",
                "forecast_direction": "NÖTR (BEKLE)",
                "forecast_icon": "⚪",
                "forecast_color": "gray",
                "current_direction": "⚪ VERİ YETERSİZ",
                "current_icon": "⚪",
                "current_color": "gray",
                "current_roc": 0.0,
                "icon": "⚪",
                "color": "gray",
                "score": 0.0,
                "entry_allowed": False,
                "entry_status": "🔴 İŞLEME GİRİŞ ÖNERİLMEZ",
                "entry_reason": f"Değerlendirme hatası (izole edildi): {exc}",
                "factor_data_status": "INSUFFICIENT_DATA",
                "details": [],
            }

    def _legacy_pair_stats(self, anchor_key, follower_key, bars=8):
        """Fallback correlation/spread-z pair check, used only when the
        adaptive DynamicPairModel for this pair doesn't have enough aligned
        history yet (see _pair_price_supported)."""
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
        std_1bar = float(hist.std(ddof=1)) if len(hist) >= 10 else 0.0
        std = std_1bar * (bars ** 0.5)
        spread_z = float(spread / (std + 1e-12)) if std > 1e-12 else 0.0
        anchor_1h = float(ar.iloc[-1]) if np.isfinite(ar.iloc[-1]) else 0.0
        follower_1h = float(br.iloc[-1]) if np.isfinite(br.iloc[-1]) else 0.0
        return {
            "corr": corr, "anchor_return": anchor_ret, "follower_return": follower_ret,
            "spread": spread, "spread_z": spread_z,
            "anchor_1h": anchor_1h, "follower_1h": follower_1h,
        }

    # Only used as a fallback when a pair's DynamicPairModel has insufficient
    # aligned history -- kept intentionally conservative (harder to trigger
    # than the model path) since it's a cruder same-window spread-z test.
    _LEGACY_PAIR_FALLBACK_THRESHOLDS = {
        ("SPX", "NQ"): (0.70, 1.25),
        ("XAU", "XAG"): (0.60, 1.35),
        ("BTC", "ETH"): (0.65, 1.35),  # was 1.20 -- the asymmetry this whole
        # fix removes; kept only as the (now-rare) fallback's own bar, raised
        # to match XAU/XAG rather than being the easiest pair to "confirm."
    }

    def _pair_price_supported(self, anchor_key, follower_key):
        """Single source of truth for 'is this pair's divergence real?',
        used identically by both reconciliation passes below. Prefers the
        adaptive DynamicPairModel (self-calibrated per pair, no manual
        per-asset tuning); falls back to the legacy spread-z check only when
        the model itself doesn't have enough data yet."""
        model = _RECONCILIATION_PAIR_MODELS.get((anchor_key, follower_key))
        if model is not None:
            state = self._pair_state(model)
            if state.get("available"):
                stats = {
                    "corr": state.get("corr_primary_anchor"),
                    "residual_z": state.get("residual_z"),
                    "divergence_z_used": state.get("divergence_z_used"),
                    "spread": state.get("residual"),
                    "method": "dynamic_pair_model",
                }
                return bool(state.get("divergence_supported")), stats

        stats = self._legacy_pair_stats(anchor_key, follower_key)
        if stats is None:
            return None, None
        min_corr, evidence_z = self._LEGACY_PAIR_FALLBACK_THRESHOLDS.get((anchor_key, follower_key), (0.65, 1.35))
        price_supported = (
            stats["corr"] >= min_corr
            and abs(stats["spread_z"]) >= evidence_z
            and abs(stats["spread"]) > 0
        )
        stats["method"] = "legacy_spread_z"
        return bool(price_supported), stats

    def evaluate_all_assets_harmonized(self, previous_signals=None):
        """Evaluate all assets and reconcile unsupported pair divergence from real prices."""
        previous_signals = previous_signals or {}
        verdicts = {
            key: self._safe_evaluate_asset_direction(
                key, previous_signals.get(key, "NÖTR (BEKLE)")
            )
            for key in ASSET_MATRICES.keys()
        }

        pair_specs = (("SPX", "NQ"), ("XAU", "XAG"), ("BTC", "ETH"))

        for anchor, follower in pair_specs:
            va = verdicts.get(anchor)
            vf = verdicts.get(follower)
            if not va or not vf:
                continue

            price_supported, stats = self._pair_price_supported(anchor, follower)
            if stats is None:
                va["pair_coherence"] = vf["pair_coherence"] = "FİYAT KARŞILAŞTIRMASI İÇİN VERİ YETERSİZ"
                continue

            status = (
                "GERÇEK FİYAT AYRIŞMASI TEYİTLİ"
                if price_supported
                else "AYRIŞMA FİYATLA TEYİT EDİLMEDİ"
            )
            va["pair_coherence"] = vf["pair_coherence"] = status
            va["pair_stats"] = vf["pair_stats"] = stats

            # ---------------------------------------------------------
            # NOT: Fiyat-desteksiz ayrışma durumunda canlı yön ve model
            # sinyali uzlaştırması artık burada YAPILMIYOR. Önceden burada
            # yapılıyordu; fakat stateful_adaptive_controller.finalize_cycle()
            # hem "current_direction" hem "verdict/forecast_direction"
            # alanlarını kendi adaptif motorlarıyla YENİDEN YAZIYOR, bu da bu
            # uzlaştırmayı sessizce sıfırlıyordu (canlı-yenile sonrası
            # XAU/XAG veya SPX/NQ birbiriyle çelişen sinyaller gösterebiliyordu).
            # Aynı uzlaştırma artık `reconcile_pairs_post_adaptive()` içinde,
            # adaptif motor çalıştıktan SONRA, nihai verdict/current_direction
            # üzerinde uygulanıyor (bkz. app.py çağrı sırası). BTC/ETH artık
            # burada da diğer iki çiftle AYNI (adaptif) teyit barını kullanıyor
            # -- önceden ayrı tutuluyordu ve daha kolay "teyitli" sayılıyordu.
            pass

        return verdicts

    def reconcile_pairs_post_adaptive(self, verdicts):
        """
        Fiyatla teyit edilmemiş ayrışmalarda hem "Canlı Fiyat Yönü" hem de
        "Model Sinyali" için nihai (stateful-adaptive sonrası) uzlaştırmayı
        uygular. `evaluate_all_assets_harmonized()` sadece ham/deterministik
        verdict'ler üzerinde çalışıyordu; ama stateful_adaptive_controller
        her iki alanı da adaptif motorlarla yeniden yazdığı için o erken
        uzlaştırma kayboluyordu. Bu metod app.py'de
        `stateful_controller.finalize_cycle(...)` çağrısından HEMEN SONRA
        çalıştırılmalıdır.
        """
        pair_specs = (("SPX", "NQ"), ("XAU", "XAG"), ("BTC", "ETH"))

        for anchor, follower in pair_specs:
            va = verdicts.get(anchor)
            vf = verdicts.get(follower)
            if not va or not vf:
                continue

            price_supported, stats = self._pair_price_supported(anchor, follower)
            if stats is None:
                continue
            if price_supported:
                continue

            # --- Canlı Fiyat Yönü (1-4 saat) uzlaştırması: gerçek fiyat
            # ayrışmayı doğrulamıyorsa, çift ortak bir skordan etiketlenir. ---
            qa, sa = self.processor.compute_live_horizon_score(self.grid_1h.get(anchor, pd.DataFrame()))
            qf, sf = self.processor.compute_live_horizon_score(self.grid_1h.get(follower, pd.DataFrame()))
            if qa is not None and qf is not None and sa is not None and sf is not None:
                qa_f, qf_f = float(qa), float(qf)
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

            # --- Model Sinyali (24 saat-1 hafta) uzlaştırması: fiyatla
            # teyit edilmemiş tek taraflı AL/SAT bastırılır. ---
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

        # NOT: BTC/ETH artık yukarıdaki `pair_specs` döngüsünde SPX/NQ ve
        # XAU/XAG ile AYNI, tutarlı fiyat-teyit mekanizmasından geçiyor
        # (hem Canlı Fiyat Yönü hem Model Sinyali için). Önceden burada ayrı
        # ve daha yumuşak bir "sempati" kuralı vardı; bu, yukarıdaki asıl
        # uzlaştırmayla çakışıp birbirini geçersiz kılabildiğinden kaldırıldı.
        return verdicts
