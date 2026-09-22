"""
Stateful Adaptive Controller v3.1
=================================

Adds a dedicated direction state machine on top of the existing Tier-1 factor
engine. Direction inference is explicitly separated from execution permission.

Pipeline:
    live data -> regime state -> adaptive factor score -> XAU/XAG pair
    -> dynamic direction threshold -> EARLY/CONFIRMED direction
    -> separate execution gate -> persistent outcome learning

The existing gatekeeper remains the source of raw factors, market diagnostics,
and execution-quality information. This layer does not replace those inputs.
"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

from config import ASSET_MATRICES, REGIME_DYNAMIC_THRESHOLDS
from dynamic_entry_engine import StatefulDynamicEntryEngine
from quant_processor import RobustQuantProcessor
from stateful_adaptive_model import AdaptiveScoreModel
from stateful_direction_engine import StatefulDirectionEngine
from stateful_live_direction_engine import StatefulLiveDirectionEngine
from stateful_memory_store import StatefulMemoryStore
from stateful_regime_controller import StatefulRegimeController
from xau_xag_dynamic_pair import DynamicXAU_XAGModel
from stateful_factor_quality import sanitize_factor_rows


DEFAULT_MEMORY_FILE = "stateful_adaptive_memory.json"


class StatefulAdaptiveController:
    def __init__(
        self,
        memory_file: str = DEFAULT_MEMORY_FILE,
        half_life_hours: float = 24.0 * 14.0,
    ) -> None:
        self.store = StatefulMemoryStore(memory_file, half_life_hours=half_life_hours)
        self.regime = StatefulRegimeController(self.store)
        self.model = AdaptiveScoreModel(self.store)
        self.direction = StatefulDirectionEngine(self.store)
        self.live_direction = StatefulLiveDirectionEngine(self.store)
        self.entry = StatefulDynamicEntryEngine()
        self.pair = DynamicXAU_XAGModel()
        self.prepared = False
        self.last_pair_state: Dict[str, Any] = {"available": False}
        self.last_diagnostics: Dict[str, Any] = {}

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _asset_df(grid: Dict[str, Any], asset_key: str) -> pd.DataFrame:
        matrix = ASSET_MATRICES.get(asset_key, {})
        symbol = str(matrix.get("benchmark_symbol", ""))
        candidates = [
            symbol,
            symbol.replace("^", ""),
            symbol.replace("=F", ""),
            symbol.replace("=X", ""),
        ]
        alias = {
            "SPX": ("ES=F", "ES", "SPX"),
            "NQ": ("NQ=F", "NQ", "NQ=F"),
            "XAU": ("GC=F", "GC", "XAU"),
            "XAG": ("SI=F", "SI", "XAG"),
            "HG": ("HG=F", "HG"),
        }
        candidates.extend(alias.get(asset_key, ()))
        for key in candidates:
            df = grid.get(key)
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
        return pd.DataFrame()

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        try:
            x = float(value)
            return x if np.isfinite(x) else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _extract_factor_values(asset_key: str, verdict: Dict[str, Any]) -> Dict[str, float]:
        matrix = ASSET_MATRICES.get(asset_key, {})
        rows = verdict.get("details", []) if isinstance(verdict, dict) else []
        by_name = {
            str(r.get("faktör")): r
            for r in rows
            if isinstance(r, dict)
        }
        values: Dict[str, float] = {}
        for factor in matrix.get("factors", []):
            name = str(factor.get("name"))
            fid = str(factor.get("id"))
            row = by_name.get(name)
            if not row:
                continue
            value = StatefulAdaptiveController._safe_float(row.get("ham_deger"))
            if value is not None:
                values[fid] = float(np.clip(value, -1.8, 1.8))
        return values

    @staticmethod
    def _leading_bias_for_asset(asset_key: str, gatekeeper: Any) -> float:
        """
        Kısa-ufuk (1-4 saat) canlı yön skoruna küçük bir "öncü gösterge"
        katkısı ekler: DXY hızı (dolar baskısı) ve kredi hızı (HYG/LQD
        risk iştahı). Her varlığın kendi faktör tablosunda zaten tanımlı
        olan `usd_strength` / `credit_spread` işaretleri (base_sign)
        kullanılır ki katkı yönü modelin geri kalanıyla tutarlı olsun.
        Toplam katkı küçük tutulur (StatefulLiveDirectionEngine ±0.35 ile
        sınırlar); amaç skoru domine etmek değil, teyit/reddir etmektir.
        """
        matrix = ASSET_MATRICES.get(asset_key, {})
        factors = {f.get("id"): f for f in matrix.get("factors", [])}
        bias = 0.0

        dxy_v = StatefulAdaptiveController._safe_float(getattr(gatekeeper, "dxy_velocity", None))
        if dxy_v is not None and "usd_strength" in factors:
            sign = float(factors["usd_strength"].get("base_sign", -1.0))
            bias += 0.12 * sign * float(np.clip(dxy_v, -1.8, 1.8))

        credit_v = StatefulAdaptiveController._safe_float(getattr(gatekeeper, "credit_velocity", None))
        if credit_v is not None and "credit_spread" in factors:
            sign = float(factors["credit_spread"].get("base_sign", 1.0))
            bias += 0.10 * sign * float(np.clip(credit_v, -1.8, 1.8))

        return float(np.clip(bias, -0.35, 0.35))

    def _price_frames(self, grid: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
        """Normalize asset aliases so pending observations settle correctly."""
        return {
            asset: self._asset_df(grid, asset)
            for asset in ASSET_MATRICES.keys()
        }

    def _bootstrap_from_existing_state(self) -> None:
        current = self.store.get_regime_state()
        if current.get("confirmed_regime_id") is not None:
            return
        state_path = "terminal_state.json"
        if not os.path.exists(state_path):
            return
        try:
            with open(state_path, "r", encoding="utf-8") as fh:
                state = json.load(fh)
            active_id = state.get("active_regime_id")
            if active_id is not None:
                self.store.set_regime_state({
                    "confirmed_regime_id": active_id,
                    "candidate_regime_id": None,
                    "candidate_since": None,
                    "candidate_support": 0.0,
                    "candidate_elapsed_minutes": 0.0,
                    "last_transition_at": state.get("last_updated"),
                    "last_raw_candidate": active_id,
                    "last_raw_strength_z": 0.0,
                    "last_update_at": self._now().isoformat(),
                })
        except Exception:
            return

    def prepare_cycle(self, gatekeeper: Any) -> Dict[str, Any]:
        self._bootstrap_from_existing_state()
        now = self._now()
        self.store.apply_decay(now)

        grid = getattr(gatekeeper, "grid_1h", {}) or {}
        settle = self.store.settle_pending(
            self._price_frames(grid),
            horizon_hours=(1, 4),
            now=now,
        )
        controlled = self.regime.apply_to_gatekeeper(gatekeeper)

        self.prepared = True
        self.last_diagnostics = {
            "settlement": settle,
            "regime": {
                "active_regime_id": controlled.get("active_regime_id"),
                "candidate_regime_id": controlled.get("candidate_regime_id"),
                "candidate_support": controlled.get("candidate_support"),
                "candidate_elapsed_minutes": controlled.get("candidate_elapsed_minutes"),
                "transition_reason": controlled.get("stateful_transition_reason"),
                "active_source": controlled.get("stateful_active_source"),
                "emergency_override": controlled.get("stateful_emergency_override"),
            },
        }
        return controlled

    def _adaptive_score_only(
        self,
        gatekeeper: Any,
        asset_key: str,
        verdict: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        score_model = self.model.recompute_score(
            asset_key,
            verdict.get("details", []) if isinstance(verdict, dict) else [],
        )
        return score_model, deepcopy(score_model)

    def _apply_adaptive_asset_state(
        self,
        gatekeeper: Any,
        asset_key: str,
        verdict: Dict[str, Any],
        previous_signal: str,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        regime_id = getattr(gatekeeper, "active_macro_regime_id", "REJIMSIZ_GECIS")
        market_regime = getattr(gatekeeper, "market_regime", "")
        raw_details = verdict.get("details", []) if isinstance(verdict, dict) else []

        # Sanitize legacy factor outputs: missing sources become None/MISSING,
        # genuine zeros remain numeric, and selected relative factors are
        # recomputed from the already-refreshed market grid.
        details, data_diag = sanitize_factor_rows(asset_key, raw_details, gatekeeper)
        score_model = self.model.recompute_score(asset_key, details)
        # Rebuild displayed factor contributions from the actual adaptive
        # weights used by the score model; never leave stale legacy points in
        # the UI after missing-data filtering or XAG relative-value capping.
        runtime_map = score_model.get("factor_runtime", {})
        for row in details:
            fid = str(row.get("faktor_id", ""))
            node = runtime_map.get(fid, {})
            if str(row.get("veri_durumu", "")).upper().startswith("VERİ YETERSİZ"):
                row["puan"] = None
            else:
                contrib = node.get("final_contribution")
                row["puan"] = round(float(contrib), 6) if contrib is not None else None
        direction_thresholds = self.model.dynamic_thresholds(asset_key, regime_id)

        df = self._asset_df(getattr(gatekeeper, "grid_1h", {}) or {}, asset_key)
        entry_eval = self.entry.evaluate(df, require_live=True)
        entry_allowed = bool(entry_eval.get("allowed", False))
        volume_supports = bool(entry_eval.get("volume_supports", False))
        volatility_supports = bool(entry_eval.get("volatility_supports", False))

        coverage = float(score_model.get("data_coverage", data_diag.get("coverage", 0.0)) or 0.0)
        if coverage < 0.45:
            entry_allowed = False
            entry_reason = (
                "Model veri kapsamı yetersiz (%.0f%%); yön/işlem kararı güvenli moda alındı."
                % (coverage * 100.0)
            )
        else:
            entry_reason = str(entry_eval.get("reason", ""))

        out = deepcopy(verdict)
        out.update({
            "raw_model_score": float(verdict.get("score", 0.0)) if verdict.get("score") is not None else None,
            "score": float(score_model["score"]),
            "adaptive_score": float(score_model["score"]),
            "adaptive_score_enabled": True,
            "adaptive_thresholds": direction_thresholds,
            "dynamic_thresholds": direction_thresholds,
            "adaptive_factor_weights": score_model["weight_map"],
            "adaptive_cluster_scores": score_model["cluster_scores"],
            "bull_clusters": int(score_model["bull_clusters"]),
            "bear_clusters": int(score_model["bear_clusters"]),
            "entry_allowed": entry_allowed,
            "entry_status": "🟢 İŞLEME GİRİŞ ÖNERİLİR" if entry_allowed else "🔴 İŞLEME GİRİŞ ÖNERİLMEZ",
            "entry_reason": entry_reason,
            "volume_supports": volume_supports,
            "volatility_supports": volatility_supports,
            "stateful_entry_profile": entry_eval.get("profile"),
            "market_regime": market_regime,
            "stateful_previous_signal": previous_signal,
            "details": details,
            "factor_data_coverage": coverage,
            "factor_data_status": score_model.get("data_confidence", data_diag.get("status", "UNKNOWN")),
            "factor_data_diagnostics": data_diag,
        })
        return out, score_model

    def finalize_cycle(
        self,
        gatekeeper: Any,
        verdicts: Dict[str, Dict[str, Any]],
        previous_signals: Optional[Dict[str, str]] = None,
        cycle_id: Optional[str] = None,
    ) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
        try:
            if not self.prepared:
                self.prepare_cycle(gatekeeper)

            previous_signals = previous_signals or {}
            cycle = cycle_id or self._now().isoformat()
            adaptive: Dict[str, Dict[str, Any]] = {}
            score_models: Dict[str, Dict[str, Any]] = {}

            # 1) Recompute adaptive scores and independent execution gates.
            for asset_key, verdict in verdicts.items():
                adaptive[asset_key], score_models[asset_key] = self._apply_adaptive_asset_state(
                    gatekeeper,
                    asset_key,
                    verdict,
                    previous_signals.get(asset_key, "NÖTR (BEKLE)"),
                )

            # 2) XAU/XAG relative-state reconciliation modifies score only.
            pair_state = self.pair.fit(getattr(gatekeeper, "grid_1h", {}) or {})
            self.last_pair_state = pair_state
            if "XAU" in adaptive and "XAG" in adaptive:
                xau_score = float(adaptive["XAU"].get("score", 0.0))
                xag_score = float(adaptive["XAG"].get("score", 0.0))
                xau_adj, xag_adj = self.pair.reconcile_scores(xau_score, xag_score, pair_state)
                adaptive["XAU"]["score_before_pair"] = xau_score
                adaptive["XAG"]["score_before_pair"] = xag_score
                adaptive["XAU"]["score"] = round(xau_adj, 4)
                adaptive["XAG"]["score"] = round(xag_adj, 4)
                adaptive["XAU"]["pair_state"] = deepcopy(pair_state)
                adaptive["XAG"]["pair_state"] = deepcopy(pair_state)

            # 3) Direction is resolved WITHOUT entry_allowed.
            direction_diag: Dict[str, Any] = {}
            for asset_key, out in adaptive.items():
                regime_id = getattr(gatekeeper, "active_macro_regime_id", "REJIMSIZ_GECIS")
                direction_state = self.direction.evaluate(
                    asset=asset_key,
                    regime_id=regime_id,
                    score=float(out.get("score", 0.0)),
                    bull_clusters=int(out.get("bull_clusters", 0)),
                    bear_clusters=int(out.get("bear_clusters", 0)),
                    thresholds=out.get("adaptive_thresholds", {}),
                    previous_signal=previous_signals.get(asset_key, "NÖTR (BEKLE)"),
                )

                stage = direction_state["stage"]
                direction = direction_state["direction"]
                verdict = direction_state["verdict"]
                if stage == "EARLY" and direction in ("LONG", "SHORT"):
                    forecast_label = f"{verdict} (ERKEN)"
                elif stage == "HELD" and direction in ("LONG", "SHORT"):
                    forecast_label = f"{verdict} (KORUNDU)"
                else:
                    forecast_label = verdict

                out.update({
                    "direction": direction,
                    "direction_state": stage,
                    "direction_stage": stage,
                    "direction_reason": direction_state["reason"],
                    "forecast_direction": forecast_label,
                    "verdict": verdict,
                    "icon": direction_state["icon"],
                    "color": direction_state["color"],
                    "forecast_icon": direction_state["icon"],
                    "forecast_color": direction_state["color"],
                    "direction_thresholds": direction_state["thresholds"],
                    "direction_score_z": direction_state["score_z"],
                    "direction_velocity": direction_state["velocity"],
                    "direction_acceleration": direction_state["acceleration"],
                    "direction_persistence": direction_state["persistence"],
                    "direction_warmup": bool(direction_state.get("diagnostic_warmup", False)),
                    "direction_runtime_n": direction_state["runtime_n"],
                    "direction_strong_impulse": direction_state["strong_impulse"],
                    "direction_velocity_support": direction_state["velocity_support"],
                    "direction_z_support": direction_state["z_support"],
                    # Entry never feeds back into direction.
                    "direction_execution_independent": True,
                })
                # ---------------------------------------------------------------
                # 3b) CANLI FİYAT YÖNÜ (1-4 saat, gün-içi rejime göre) — Model
                # Sinyali'nden (yukarıda, haftalık/aylık makro rejime göre)
                # tamamen bağımsız bir kısa-ufuk motoru. Aynı skor hem etiketi
                # hem gösterilen % değeri belirlediği için çelişki oluşmaz.
                # ---------------------------------------------------------------
                df_live = self._asset_df(getattr(gatekeeper, "grid_1h", {}) or {}, asset_key)
                live_score, live_meta = RobustQuantProcessor.compute_live_horizon_score(df_live)
                if live_score is None or live_meta is None:
                    out.setdefault("current_direction", "⚪ VERİ YETERSİZ")
                    out.setdefault("current_icon", "⚪")
                    out.setdefault("current_color", "gray")
                    out["live_horizon"] = "1-4 saat"
                else:
                    adx_val = out.get("adx_val", live_meta.get("adx_1h", 25.0))
                    atr_ratio = out.get("atr_ratio", 1.0)
                    regime_info = RobustQuantProcessor.classify_intraday_regime(adx_val, atr_ratio)
                    leading_bias = self._leading_bias_for_asset(asset_key, gatekeeper)
                    live_state = self.live_direction.evaluate(
                        asset=asset_key,
                        regime_label=regime_info["label"],
                        score=live_score,
                        ret_pct_1h=live_meta.get("ret_pct_1h"),
                        ret_pct_2h=live_meta.get("ret_pct_2h"),
                        leading_bias=leading_bias,
                    )
                    out.update({
                        "current_direction": live_state["current_direction"],
                        "current_icon": live_state["current_icon"],
                        "current_color": live_state["current_color"],
                        "current_roc": live_state["current_roc"],
                        "live_score": live_state["live_score"],
                        "live_tier": live_state["live_tier"],
                        "live_horizon": live_state["live_horizon"],
                        "live_regime_label": live_state["live_regime_label"],
                        "live_regime_event": live_state["live_regime_event"],
                        "live_thresholds": live_state["live_thresholds"],
                        "live_thresholds_adaptive": live_state["live_thresholds_adaptive"],
                        "intraday_regime": regime_info,
                    })

                direction_diag[asset_key] = {
                    "stage": stage,
                    "direction": direction,
                    "score": direction_state["score"],
                    "score_z": direction_state["score_z"],
                    "velocity": direction_state["velocity"],
                    "acceleration": direction_state["acceleration"],
                    "persistence": direction_state["persistence"],
                    "warmup": bool(direction_state.get("diagnostic_warmup", False)),
                    "early_threshold": direction_state["thresholds"].get("buy_early") if direction == "LONG" else abs(direction_state["thresholds"].get("sell_early", 0.0)),
                    "confirm_threshold": direction_state["thresholds"].get("buy_enter") if direction == "LONG" else abs(direction_state["thresholds"].get("sell_enter", 0.0)),
                    "entry_allowed": bool(out.get("entry_allowed", False)),
                    "execution_independent": True,
                }

            # 4) Add current observations to score distribution AFTER thresholds
            # are calculated, avoiding current-bar self-referential calibration.
            observed_at = self._now()
            for asset_key, out in adaptive.items():
                self.store.update_score_distribution(
                    asset_key,
                    getattr(gatekeeper, "active_macro_regime_id", "REJIMSIZ_GECIS"),
                    float(out.get("score", 0.0)),
                    observed_at,
                )

            # 5) Persist pending snapshots for 1h / 4h outcome learning.
            grid = getattr(gatekeeper, "grid_1h", {}) or {}
            for asset_key, verdict in adaptive.items():
                df = self._asset_df(grid, asset_key)
                if df.empty or "Close" not in df.columns:
                    continue
                try:
                    price = float(pd.to_numeric(df["Close"], errors="coerce").dropna().iloc[-1])
                except (IndexError, ValueError, TypeError):
                    continue
                if not np.isfinite(price) or price <= 0:
                    continue

                factor_values = self._extract_factor_values(asset_key, verdict)
                obs = {
                    "cycle_id": cycle,
                    "observed_at": observed_at.isoformat(),
                    "asset": asset_key,
                    "price": price,
                    "model_score_raw": float(verdict.get("raw_model_score", 0.0)),
                    "model_score_adaptive": float(verdict.get("score", 0.0)),
                    "verdict": str(verdict.get("verdict", "NÖTR (BEKLE)")),
                    "direction": str(verdict.get("direction", "NEUTRAL")),
                    "direction_stage": str(verdict.get("direction_stage", "NEUTRAL")),
                    "direction_thresholds": deepcopy(verdict.get("direction_thresholds", {})),
                    "direction_velocity": verdict.get("direction_velocity"),
                    "direction_acceleration": verdict.get("direction_acceleration"),
                    "direction_persistence": verdict.get("direction_persistence"),
                    "active_regime_id": getattr(gatekeeper, "active_macro_regime_id", "REJIMSIZ_GECIS"),
                    "candidate_regime_id": getattr(gatekeeper, "macro_diagnostics", {}).get("candidate_regime_id"),
                    "entry_allowed": bool(verdict.get("entry_allowed", False)),
                    "atr_ratio": verdict.get("atr_ratio"),
                    "rvol": verdict.get("rvol"),
                    "adaptive_thresholds": deepcopy(verdict.get("adaptive_thresholds", {})),
                    "factors": factor_values,
                    "pair_state": deepcopy(verdict.get("pair_state", {})),
                }
                self.store.add_pending_observation(obs)

            self.store.memory.setdefault("meta", {})["last_cycle_id"] = cycle
            self.store.memory.setdefault("meta", {})["direction_model_version"] = "3.1.0"
            self.store.save()

            diagnostics = {
                "version": "3.1.0",
                "cycle_id": cycle,
                "memory": self.store.diagnostics(),
                "regime": self.last_diagnostics.get("regime", {}),
                "settlement": self.last_diagnostics.get("settlement", {}),
                "pair_state": pair_state,
                "direction": direction_diag,
                "architecture": {
                    "direction_execution_separated": True,
                    "bounded_adaptation": True,
                    "velocity_acceleration": True,
                    "persistent_direction_state": True,
                    "one_hour_outcome_learning": True,
                    "four_hour_confirmation_learning": True,
                },
                "adaptive_assets": {
                    key: {
                        "raw_score": value.get("raw_model_score"),
                        "adaptive_score": value.get("score"),
                        "entry_allowed": value.get("entry_allowed"),
                        "direction_stage": value.get("direction_stage"),
                        "direction": value.get("direction"),
                        "thresholds": value.get("direction_thresholds", {}),
                    }
                    for key, value in adaptive.items()
                },
            }
            self.last_diagnostics = diagnostics
            self.prepared = False
            return adaptive, diagnostics
        finally:
            # Bir istisna oluşsa bile 'prepared' bayrağı DAİMA sıfırlanır;
            # aksi halde bir sonraki 'Canlı Verileri Yenile' tıklaması
            # prepare_cycle()'ı sessizce atlayıp eski/rejim durumunu
            # yeniden kullanır (tam olarak 'yenile -> birden bozuluyor'
            # şikayetine yol açan durumlardan biri).
            self.prepared = False
