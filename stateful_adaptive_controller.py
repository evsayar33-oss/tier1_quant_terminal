"""
Stateful Adaptive Controller
============================
Integration layer for the existing Tier-1 Quant Terminal.

Usage pattern:
    controller = StatefulAdaptiveController()
    controller.prepare_cycle(gk)                 # after gk.refresh_market()
    verdicts = gk.evaluate_all_assets_harmonized(previous_signals)
    verdicts, diagnostics = controller.finalize_cycle(
        gk, verdicts, previous_signals
    )

The original gatekeeper remains the primary data/factor engine. This layer
adds persistent regime state, dynamic score calibration, online factor
reliability, a stateful entry gate, and dynamic XAU/XAG relative-state logic.
"""

from __future__ import annotations

import os
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

from config import ASSET_MATRICES, REGIME_DYNAMIC_THRESHOLDS
from dynamic_entry_engine import StatefulDynamicEntryEngine
from stateful_adaptive_model import AdaptiveScoreModel
from stateful_memory_store import StatefulMemoryStore
from stateful_regime_controller import StatefulRegimeController
from xau_xag_dynamic_pair import DynamicXAU_XAGModel


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
            "NQ": ("NQ=F", "NQ"),
            "XAU": ("GC=F", "GC", "XAU"),
            "XAG": ("SI=F", "SI", "XAG"),
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

    def _bootstrap_from_existing_state(self) -> None:
        """Optional one-time bootstrap so existing confirmed state is not lost."""
        current = self.store.get_regime_state()
        if current.get("confirmed_regime_id") is not None:
            return
        state_path = "terminal_state.json"
        if not os.path.exists(state_path):
            return
        try:
            import json
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
        """
        Call immediately after gatekeeper.refresh_market().
        Previous pending forecasts are settled before new calibration is used.
        """
        self._bootstrap_from_existing_state()
        self.store.apply_decay(self._now())

        grid = getattr(gatekeeper, "grid_1h", {}) or {}
        settle = self.store.settle_pending(grid, horizon_hours=(1, 4, 8), now=self._now())
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

    def _apply_adaptive_asset_state(
        self,
        gatekeeper: Any,
        asset_key: str,
        verdict: Dict[str, Any],
        previous_signal: str,
    ) -> Dict[str, Any]:
        regime_id = getattr(gatekeeper, "active_macro_regime_id", "REJIMSIZ_GECIS")
        market_regime = getattr(gatekeeper, "market_regime", "")
        details = verdict.get("details", []) if isinstance(verdict, dict) else []

        score_model = self.model.recompute_score(asset_key, details)
        thresholds = self.model.dynamic_thresholds(asset_key, regime_id)

        df = self._asset_df(getattr(gatekeeper, "grid_1h", {}) or {}, asset_key)
        entry_eval = self.entry.evaluate(df, require_live=True)

        entry_allowed = bool(entry_eval.get("allowed", False))
        volume_supports = bool(entry_eval.get("volume_supports", False))
        volatility_supports = bool(entry_eval.get("volatility_supports", False))

        signal, color, icon = self.model.resolve_signal(
            score=float(score_model["score"]),
            thresholds=thresholds,
            previous_signal=previous_signal,
            bull_clusters=int(score_model["bull_clusters"]),
            bear_clusters=int(score_model["bear_clusters"]),
            entry_allowed=entry_allowed,
            volume_supports=volume_supports,
            volatility_supports=volatility_supports,
            market_regime=market_regime,
        )

        out = deepcopy(verdict)
        out.update({
            "raw_model_score": float(verdict.get("score", 0.0)),
            "score": float(score_model["score"]),
            "adaptive_score": float(score_model["score"]),
            "adaptive_score_enabled": True,
            "adaptive_thresholds": thresholds,
            "dynamic_thresholds": thresholds,
            "adaptive_factor_weights": score_model["weight_map"],
            "adaptive_cluster_scores": score_model["cluster_scores"],
            "bull_clusters": int(score_model["bull_clusters"]),
            "bear_clusters": int(score_model["bear_clusters"]),
            "entry_allowed": entry_allowed,
            "entry_status": "🟢 İŞLEME GİRİŞ ÖNERİLİR" if entry_allowed else "🔴 İŞLEME GİRİŞ ÖNERİLMEZ",
            "entry_reason": entry_eval.get("reason", ""),
            "volume_supports": volume_supports,
            "volatility_supports": volatility_supports,
            "stateful_entry_profile": entry_eval.get("profile"),
            "verdict": signal,
            "forecast_direction": signal,
            "forecast_icon": icon,
            "forecast_color": color,
            "icon": icon,
            "color": color,
            "stateful_previous_signal": previous_signal,
        })
        return out

    def finalize_cycle(
        self,
        gatekeeper: Any,
        verdicts: Dict[str, Dict[str, Any]],
        previous_signals: Optional[Dict[str, str]] = None,
        cycle_id: Optional[str] = None,
    ) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
        """Apply adaptive scoring/pair logic, then persist this cycle as pending."""
        if not self.prepared:
            self.prepare_cycle(gatekeeper)

        previous_signals = previous_signals or {}
        cycle = cycle_id or self._now().isoformat()

        adaptive: Dict[str, Dict[str, Any]] = {}
        for asset_key, verdict in verdicts.items():
            adaptive[asset_key] = self._apply_adaptive_asset_state(
                gatekeeper,
                asset_key,
                verdict,
                previous_signals.get(asset_key, "NÖTR (BEKLE)"),
            )

        pair_state = self.pair.fit(getattr(gatekeeper, "grid_1h", {}) or {})
        self.last_pair_state = pair_state

        # Apply pair reconciliation after both legs have their own adaptive score.
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

            for asset_key in ("XAU", "XAG"):
                v = adaptive[asset_key]
                s, c, i = self.model.resolve_signal(
                    score=float(v["score"]),
                    thresholds=v["adaptive_thresholds"],
                    previous_signal=previous_signals.get(asset_key, "NÖTR (BEKLE)"),
                    bull_clusters=int(v.get("bull_clusters", 0)),
                    bear_clusters=int(v.get("bear_clusters", 0)),
                    entry_allowed=bool(v.get("entry_allowed", False)),
                    volume_supports=bool(v.get("volume_supports", False)),
                    volatility_supports=bool(v.get("volatility_supports", False)),
                    market_regime=getattr(gatekeeper, "market_regime", ""),
                )
                v.update({
                    "verdict": s,
                    "forecast_direction": s,
                    "forecast_icon": i,
                    "forecast_color": c,
                    "icon": i,
                    "color": c,
                })

        # Persist current forecast only AFTER all model calculations are finished.
        grid = getattr(gatekeeper, "grid_1h", {}) or {}
        observed_at = self._now().isoformat()
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
                "observed_at": observed_at,
                "asset": asset_key,
                "price": price,
                "model_score_raw": float(verdict.get("raw_model_score", 0.0)),
                "model_score_adaptive": float(verdict.get("score", 0.0)),
                "verdict": str(verdict.get("verdict", "NÖTR (BEKLE)")),
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
        self.store.save()

        diagnostics = {
            "version": "1.0.0",
            "cycle_id": cycle,
            "memory": self.store.diagnostics(),
            "regime": self.last_diagnostics.get("regime", {}),
            "settlement": self.last_diagnostics.get("settlement", {}),
            "pair_state": pair_state,
            "adaptive_assets": {
                key: {
                    "raw_score": value.get("raw_model_score"),
                    "adaptive_score": value.get("score"),
                    "entry_allowed": value.get("entry_allowed"),
                    "thresholds": value.get("adaptive_thresholds", {}),
                }
                for key, value in adaptive.items()
            },
        }
        self.last_diagnostics = diagnostics
        self.prepared = False
        return adaptive, diagnostics
