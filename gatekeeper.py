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
from leading_indicators import compute_vol_term_structure_lead, compute_relative_vol_premium_lead, build_vol_history_frame

# Symbols that need a genuine 1D (HTF) series fetched for multi-timeframe
# confluence and/or feed the relative-value pair models above.
_DAILY_FETCH_SYMBOLS = {
    "SPX": "ES=F", "NQ": "NQ=F", "XAU": "GC=F", "XAG": "SI=F",
    "HG": "HG=F", "BTC-USD": "BTC-USD", "ETH-USD": "ETH-USD",
    # Implied-vol / tail-risk indices: their "is this unusual?" baseline
    # must come from months of DAILY history, not the few days of 1H bars
    # (see leading_indicators.build_vol_history_frame).
    "VIX": "^VIX", "VXN": "^VXN", "GVZ": "^GVZ", "VXSLV": "^VXSLV", "SKEW": "^SKEW",
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
        self.fred_metrics = {}
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
            price_series = {}
            for asset_key in ASSET_MATRICES.keys():
                # Resolve through the benchmark symbol too: BTC/ETH live in
                # the grid as "BTC-USD"/"ETH-USD", so a plain grid[asset_key]
                # lookup left their timeframe predictions pending forever.
                _sym = str(ASSET_MATRICES[asset_key].get("benchmark_symbol", asset_key))
                df = self.grid_1h.get(asset_key)
                if not isinstance(df, pd.DataFrame) or df.empty:
                    df = self.grid_1h.get(_sym.replace("^", "").replace("=X", "").replace("=F", ""), self.grid_1h.get(_sym))
                if isinstance(df, pd.DataFrame) and not df.empty and "Close" in df.columns:
                    last_close = pd.to_numeric(df["Close"], errors="coerce").dropna()
                    if not last_close.empty:
                        current_prices[asset_key] = float(last_close.iloc[-1])
                        price_series[asset_key] = last_close
            if current_prices:
                self.tf_store.settle_due_predictions(current_prices, price_series=price_series)
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
        self.fred_metrics = dict(fred)
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

    def _vol_history(self, key):
        """Daily-history + latest-intraday frame for a vol index (see
        leading_indicators.build_vol_history_frame)."""
        return build_vol_history_frame(
            self.grid_1h.get(key, pd.DataFrame()),
            self.grid_daily.get(key),
        )

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
                reference_time = last_close_series.index[-1]
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
                        reference_time=reference_time,
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
                        # v3.3: CL=F trades the same ~23h session as GC=F; USO (US
                        # hours only) was always used because key "CL" never exists.
                        self.grid_1h.get("CL=F") if not self.grid_1h.get("CL=F", pd.DataFrame()).empty
                        else self.grid_1h.get("USO", pd.DataFrame())
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
                elif f_id == "vix_term_lead":
                    # Genuinely forward-looking: the options market's OWN
                    # pricing of near-term vs 3-month risk, not price action.
                    # Shared by SPX and NQ (same broad-market vol regime).
                    val = compute_vol_term_structure_lead(
                        self.grid_1h.get("VIX", pd.DataFrame()),
                        self.grid_1h.get("VIX3M", pd.DataFrame()),
                    )
                elif f_id == "tech_vol_premium_lead":
                    # NQ-specific: is the Nasdaq-100 options market (VXN)
                    # pricing meaningfully more future risk than the broad
                    # market (VIX) right now, relative to their own normal
                    # spread? A widening premium is a tech-specific stress
                    # signal that can lead price.
                    val = compute_relative_vol_premium_lead(
                        self._vol_history("VXN"),
                        benchmark_vol_df=self._vol_history("VIX"),
                    )
                elif f_id == "gold_vol_premium_lead":
                    # GVZ (CBOE Gold ETF Volatility Index): the gold options
                    # market's own forward-looking vol pricing. A z-scored
                    # jump here can precede a large gold move rather than
                    # follow it. Also reused for XAG (silver often shares
                    # gold's implied-vol regime shifts before its own
                    # dedicated VXSLV index fully reflects it).
                    val = compute_relative_vol_premium_lead(self._vol_history("GVZ"))
                elif f_id == "silver_vol_premium_lead":
                    # VXSLV (CBOE Silver ETF Volatility Index): silver's own
                    # options-market fear gauge, distinct from gold's.
                    val = compute_relative_vol_premium_lead(self._vol_history("VXSLV"))
                elif f_id == "tail_risk_skew_lead":
                    # CBOE SKEW Index: the S&P 500 options market's pricing
                    # of tail/crash risk specifically (distinct from VIX's
                    # "how big will moves be" -- SKEW asks "how likely is a
                    # 2+ sigma crash"). Historically documented to spike
                    # ahead of major drawdowns (1987, 2010 Flash Crash, 2018,
                    # 2022) rather than merely following them. Shared by
                    # SPX and NQ (single US-equity tail-risk read).
                    val = compute_relative_vol_premium_lead(self._vol_history("SKEW"))
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

    @staticmethod
    def _relabel_live(v, score):
        """Label a live score with the asset's OWN adaptive thresholds, using the
        same tier scheme as StatefulLiveDirectionEngine (keeps label == tier)."""
        th = v.get("live_thresholds") or {}
        p50 = float(th.get("p50", 0.45)); p70 = float(th.get("p70", 0.85)); p85 = float(th.get("p85", 1.35))
        a = abs(float(score)); up = score > 0
        roc = float(v.get("current_roc") or 0.0)
        tail = " ⚠️REJİM GEÇİŞİ" if v.get("live_regime_event") else ""
        if score == 0 or a < p50:
            tier, core, icon, color = "YATAY", "YATAY / DENGELİ", "⚪", "gray"
        elif a < p70:
            tier, core = "HAFİF", ("HAFİF YUKARI" if up else "HAFİF AŞAĞI")
            icon, color = ("🟢", "palegreen") if up else ("🔴", "lightcoral")
        elif a < p85:
            tier, core = "YÖNLÜ", ("YUKARI" if up else "AŞAĞI")
            icon, color = ("🟢", "lightgreen") if up else ("🔴", "red")
        else:
            tier, core = "GÜÇLÜ", ("GÜÇLÜ YUKARI" if up else "GÜÇLÜ AŞAĞI")
            icon, color = ("🟢🟢", "darkgreen") if up else ("🔴🔴", "darkred")
        v["current_direction"] = f"{icon} {core} (son 1s %{roc:+.2f}){tail}"
        v["current_icon"], v["current_color"], v["live_tier"] = icon, color, tier
        v["live_score_pair_adjusted"] = round(float(score), 4)

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

            # --- Canlı Fiyat Yönü (1-4 saat) uzlaştırması (v3.3.4) ---
            # Eski hali: iki varlığın etiketini de çiftin ZAYIF skoruyla
            # (min |skor|), sabit 0.65/1.35 eşikleriyle ve HAFİF kademesi
            # olmayan ayrı bir formatlayıcıyla YENİDEN yazıyordu -> adaptif
            # motorun eşikleri/kademesi yok sayılıyor, NQ güçlü yükselirken
            # SPX'in zayıf skoru yüzünden ikisi de "YATAY" oluyordu (etiket ile
            # live_tier çelişiyordu). Yeni: ortak-faktör küçültmesi -- her
            # varlığın kendi adaptif canlı skoru çiftin ortalamasına doğru
            # yarı yarıya çekilir ve KENDİ dinamik eşikleriyle, canlı motorla
            # aynı etiket şemasıyla sınıflandırılır.
            if va.get("live_score") is not None and vf.get("live_score") is not None:
                la, lf = float(va["live_score"]), float(vf["live_score"])
                common = 0.5 * (la + lf)
                # Only a genuine CONTRADICTION (opposite signs) is reconciled;
                # same-direction moves keep each asset's own adaptive label.
                k = 0.5 if (la > 0) != (lf > 0) and la != 0 and lf != 0 else 0.0
                for v_, own in ((va, la), (vf, lf)):
                    adj = (1.0 - k) * own + k * common
                    self._relabel_live(v_, adj)
                    v_["pair_direction_score"] = round(adj, 3)

            # --- Model Sinyali (24 saat-1 hafta) uzlaştırması: fiyatla
            # teyit edilmemiş tek taraflı AL/SAT bastırılır. ---
            anc_verdict = str(va.get("verdict", ""))
            fol_verdict = str(vf.get("verdict", ""))
            opposite_one_sided = (
                ("AL" in fol_verdict and "AL" not in anc_verdict)
                or ("SAT" in fol_verdict and "SAT" not in anc_verdict)
            )
            if opposite_one_sided:
                # ÖNCEKİ DAVRANIŞ: follower'ın 24 saat-1 hafta model
                # verdict'i (asıl AL/SAT/BEKLE kararı) tamamen NÖTR'e
                # siliniyordu -- fiyat henüz teyit etmediği için, olası
                # gerçekten ÖNCÜ bir sinyal bile görünmeden yok ediliyordu.
                # Bu, sistemin "vizyoner/öncü" olması isteğiyle doğrudan
                # çelişiyordu: bir sinyal tam olarak faydalı olabileceği
                # anda (henüz fiyata yansımamışken) susturuluyordu.
                #
                # YENİ DAVRANIŞ: verdict/forecast_direction/skor OLDUĞU GİBİ
                # görünür kalır (kullanıcı gerçek model çağrısını görür),
                # sadece düşük-güven olarak etiketlenir. Görüntüleme ile
                # otomatik giriş birbirinden ayrılır: gerçek pozisyon açma
                # izni fiyat teyidi gelene kadar ayrıca kapatılır. Böylece
                # sinyal ne körü körüne uygulanır ne de tamamen kaybolur.
                vf["conviction"] = "DÜŞÜK (fiyat teyidi bekleniyor)"
                va["pair_model_reconciliation"] = "TEK TARAFLI - ÖNCÜ SİNYAL (fiyat teyidi bekleniyor)"
                vf["pair_model_reconciliation"] = "TEK TARAFLI - ÖNCÜ SİNYAL (fiyat teyidi bekleniyor)"
                if vf.get("entry_allowed"):
                    vf["entry_allowed"] = False
                    vf["entry_status"] = "🟡 ÖNCÜ SİNYAL (FİYAT TEYİDİ BEKLENİYOR)"
                    vf["entry_reason"] = (
                        f"{vf.get('entry_reason', '')} | Çift-fiyat teyidi henüz gelmedi "
                        f"(öncü sinyal olarak gösteriliyor, otomatik giriş bu yüzden engellendi)"
                    ).strip(" |")

        # NOT: BTC/ETH artık yukarıdaki `pair_specs` döngüsünde SPX/NQ ve
        # XAU/XAG ile AYNI, tutarlı fiyat-teyit mekanizmasından geçiyor
        # (hem Canlı Fiyat Yönü hem Model Sinyali için). Önceden burada ayrı
        # ve daha yumuşak bir "sempati" kuralı vardı; bu, yukarıdaki asıl
        # uzlaştırmayla çakışıp birbirini geçersiz kılabildiğinden kaldırıldı.
        return verdicts

    # ------------------------------------------------------------------
    # FINAL, DIRECTION-AWARE ENTRY-TIMING GATE
    # ------------------------------------------------------------------
    @staticmethod
    def _verdict_direction_sign(verdict_text):
        text = str(verdict_text or "").upper()
        has_buy = "AL" in text.replace("SAT", "")
        has_sell = "SAT" in text
        if has_buy and not has_sell:
            return 1
        if has_sell and not has_buy:
            return -1
        return 0

    @staticmethod
    def _flag_counter_trend_live_direction(v, conf):
        """Live (1-4h) direction is a fast momentum read; its STRENGTH label must
        respect the structure above it (v3.3.2, graded):
          * 4H AND 1D against  -> max HAFİF + "↩ TERS-TREND TEPKİ"
          * only 4H against    -> max YÖNLÜ (no 'GÜÇLÜ') + "(4S teyitsiz)"
          * otherwise unchanged.
        Direction and % are never changed, only the confidence tier."""
        try:
            ls = float(v.get("live_score") or 0.0)
            tfs = (conf or {}).get("timeframes", {}) or {}
            def sc(k):
                t = tfs.get(k)
                return float(t.get("score", 0.0)) if isinstance(t, dict) and t.get("available") else None
            h4, d1 = sc("MTF_4H"), sc("HTF_1D")
            v["live_counter_trend"] = False
            if ls == 0 or h4 is None:
                return
            sgn = 1.0 if ls > 0 else -1.0
            up = sgn > 0
            roc = float(v.get("current_roc") or 0.0)
            tier = str(v.get("live_tier", ""))
            if h4 * sgn < -0.20 and d1 is not None and d1 * sgn < -0.20:
                if tier in ("GÜÇLÜ", "YÖNLÜ", "HAFİF"):
                    core = "HAFİF YUKARI" if up else "HAFİF AŞAĞI"
                    v["current_direction"] = f"{'🟢' if up else '🔴'} {core} (son 1s %{roc:+.2f}) ↩ TERS-TREND TEPKİ"
                    v["current_icon"] = "🟢" if up else "🔴"
                    v["current_color"] = "palegreen" if up else "lightcoral"
                    v["live_tier"] = "HAFİF"
                    v["live_counter_trend"] = True
            elif h4 * sgn < -0.20 and tier == "GÜÇLÜ":
                core = "YUKARI" if up else "AŞAĞI"
                v["current_direction"] = f"{'🟢' if up else '🔴'} {core} (son 1s %{roc:+.2f}) · 4S teyitsiz"
                v["current_icon"] = "🟢" if up else "🔴"
                v["current_color"] = "lightgreen" if up else "red"
                v["live_tier"] = "YÖNLÜ"
        except Exception:
            pass

    def _flag_live_vs_model(self, v):
        """v3.3.3: every asset — when the 1-4h live move runs AGAINST the model
        signal (24h-1w), say so explicitly instead of letting two columns look
        contradictory. Counter-trend tag (structure) has priority."""
        try:
            d = self._verdict_direction_sign(v.get("verdict"))
            ls = float(v.get("live_score") or 0.0)
            tier = str(v.get("live_tier", ""))
            txt = str(v.get("current_direction", ""))
            v["live_vs_model"] = "ALIGNED"
            if d == 0 or ls == 0 or tier == "YATAY":
                v["live_vs_model"] = "N/A"
                return
            if (ls > 0) != (d > 0):
                v["live_vs_model"] = "OPPOSED"
                if "TERS-TREND" not in txt and "MODELE TERS" not in txt:
                    v["current_direction"] = f"{txt} ↔ MODELE TERS (kısa tepki)"
        except Exception:
            pass

    def apply_final_entry_gate(self, verdicts):
        """Must run LAST (after stateful finalize_cycle and
        reconcile_pairs_post_adaptive), in BOTH app.py and the background
        tracker, so the two always publish the same decision.

        Fixes two production defects:

        1. StatefulAdaptiveController.finalize_cycle() recomputes
           ``entry_allowed`` from ATR/RVOL only, which silently discarded
           the HTF/MTF/LTF confluence gate added to evaluate_asset_direction().
        2. That confluence gate itself was direction-blind: it asked "do the
           timeframes agree with EACH OTHER?", never "do they agree with the
           SIGNAL?". Live example: BTC verdict SAT while 1D/4H/1H were all
           bullish -> "Dinamik giriş uygun". For a future auto-trader that
           is a short straight into a confirmed up-move.

        Design (keeps the system LEADING, not reactive): the forecast
        direction is never changed here -- only the TIMING permission.
          Grade A : every available timeframe agrees with the signal
                    direction and confluence is strong -> entry allowed.
          Grade B : the fast (LTF) trigger has turned in the signal
                    direction and higher timeframes are not strongly
                    against it -> entry allowed (leading signal, price
                    trigger present).
          Grade C : the trigger has not turned yet, or the higher
                    timeframes are strongly against the call -> the call
                    stays visible as a leading signal; entry waits.
        This gate can only REMOVE entry permission, never grant it, so no
        other safety check (stale data, coverage, crisis lock, pair
        conviction) can be bypassed through it.
        """
        try:
            from config import ENTRY_TIMING_CONFIG as cfg
        except Exception:
            cfg = {}
        trig_min = float(cfg.get("ltf_trigger_min", 0.05))
        opp_max = float(cfg.get("max_opposing_confluence", 0.35))
        grade_a_min = float(cfg.get("grade_a_min_confluence", 0.35))

        for key, v in (verdicts or {}).items():
            if not isinstance(v, dict):
                continue
            d = self._verdict_direction_sign(v.get("verdict"))
            conf = v.get("timeframe_confluence") or {}
            was_allowed = bool(v.get("entry_allowed", False))

            self._flag_counter_trend_live_direction(v, conf)
            _prof = v.get("stateful_entry_profile") or {}
            if _prof.get("rvol") is not None:
                v["rvol"] = round(float(_prof["rvol"]), 2)   # v3.3.2: one RVOL on screen
            elif _prof and _prof.get("volume_known") is False:
                v["rvol"] = None                              # v3.3.6: unreliable feed -> "—", not a fake number
            if _prof.get("atr_ratio") is not None and float(v.get("atr_ratio") or 0.0) <= 0.05:
                v["atr_ratio"] = round(float(_prof["atr_ratio"]), 2)   # v3.3.3: BTC showed 0.00x
            self._flag_live_vs_model(v)

            if "NOT_PROVEN" in str(v.get("learned_model_status", "")) and "LEGACY" not in str(v.get("learned_model_status", "")):
                v["entry_allowed"] = False
                v["entry_grade"] = "-"
                v["entry_timing"] = "Örneklem dışı kanıt yok; zamanlama değerlendirilmez."
                v["entry_status"] = "⛔ GİRİŞ KAPALI (KANITSIZ SİNYAL)"
                continue

            if d == 0:
                v["entry_grade"] = "-"
                v["entry_timing"] = "Yön sinyali yok; giriş değerlendirilmez."
                v["entry_allowed"] = False
                v["entry_status"] = "⚪ YÖN SİNYALİ YOK (GİRİŞ YOK)"
                # v3.3: the ATR/RVOL text ("Dinamik giriş uygun ...") only says the
                # market is tradable; with no direction it must not read like an
                # entry recommendation (live ETH showed both at once).
                tech = str(v.get("entry_reason", "")).replace("Dinamik giriş uygun", "Piyasa koşulu işlem yapılabilir")
                v["entry_reason"] = f"Model yönü NÖTR → giriş yok. ({tech})" if tech else "Model yönü NÖTR → giriş yok."
                continue

            if not conf.get("available"):
                v["entry_grade"] = "N/A"
                v["entry_timing"] = "Zaman dilimi verisi yetersiz; zamanlama notu verilemedi."
                continue

            tfs = conf.get("timeframes", {}) or {}
            ltf = tfs.get("LTF_1H", {}) or {}
            ltf_dir = float(ltf.get("score", 0.0)) * d if ltf.get("available") else 0.0
            directional_conf = float(conf.get("confluence_score", 0.0)) * d
            avail_scores = [float(t.get("score", 0.0)) * d for t in tfs.values() if t.get("available")]
            all_with_signal = len(avail_scores) >= 2 and all(x > trig_min for x in avail_scores)

            if all_with_signal and directional_conf >= grade_a_min and ltf_dir > trig_min:
                grade = "A"
                timing = "Tüm zaman dilimleri sinyal yönünde onaylı."
            elif ltf_dir > trig_min and directional_conf > -opp_max:
                grade = "B"
                timing = "Öncü sinyal + LTF tetik sinyal yönünde döndü; üst zaman dilimleri güçlü ters değil."
            else:
                grade = "C"
                if ltf_dir <= trig_min:
                    timing = "Öncü sinyal var ama LTF tetik henüz sinyal yönüne dönmedi (zamanlama bekleniyor)."
                else:
                    timing = "Üst zaman dilimleri sinyale güçlü ters; zamanlama bekleniyor."

            v["entry_grade"] = grade
            v["entry_timing"] = timing
            v["directional_confluence"] = round(directional_conf, 4)

            # v3.3: grade A requires participation. A move on bottom-quintile
            # relative volume (same-hour comparison) is not "fully confirmed".
            prof = v.get("stateful_entry_profile") or {}
            rr = prof.get("rvol_rank")
            if grade == "A" and rr is not None and float(rr) < 0.20:
                grade = "B"
                timing = (f"Zaman dilimleri onaylı fakat hacim katılımı zayıf (RVOL P{float(rr)*100:.0f}); "
                          "A yerine B — pozisyon boyutu küçük tutulmalı.")
                v["entry_grade"] = grade
                v["entry_timing"] = timing

            if grade == "C" and was_allowed:
                v["entry_allowed"] = False
                v["entry_status"] = "🟡 ÖNCÜ SİNYAL — ZAMANLAMA BEKLENİYOR (C)"
                v["entry_reason"] = f"{v.get('entry_reason', '')} | {timing}".strip(" |")
            elif was_allowed:
                v["entry_status"] = (
                    "🟢 İŞLEME GİRİŞ ÖNERİLİR (A: tüm zaman dilimleri onaylı)" if grade == "A"
                    else "🟢 İŞLEME GİRİŞ UYGUN (B: öncü sinyal + LTF tetik)"
                )
        # v3.3.6: a blocked entry must never read like a recommendation
        for v in (verdicts or {}).values():
            if isinstance(v, dict) and not v.get("entry_allowed"):
                r = str(v.get("entry_reason", ""))
                v["entry_reason"] = r.replace("Dinamik giriş uygun", "Piyasa koşulu uygun (giriş yok)")
        return verdicts
