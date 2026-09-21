"""
Stateful Macro Regime Controller
================================
Persistent confirmation / dwell-state layer placed on top of the existing
MacroRegimeEngine. It does not replace the raw macro detector; it prevents a
single transient cycle from becoming the active macro state.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import numpy as np

from config import REGIME_DYNAMIC_THRESHOLDS
from stateful_memory_store import StatefulMemoryStore


REGIME_TYPES = {
    1: "SHOCK",
    2: "SHOCK",
    3: "SHOCK",
    4: "SHOCK",
    5: "RISK_ON",
    "REJIMSIZ_GECIS": "DENGE",
}

REGIME_NAMES = {
    1: "Küresel Enflasyon & Stagflasyon Şoku",
    2: "Sistemik Likidite Şoku & Carry Çöküşü",
    3: "Reel Faiz Şoku",
    4: "Kredi Temerrüt Baskısı",
    5: "Küresel Likidite Rallisi (Risk-On)",
    "REJIMSIZ_GECIS": "Rejimsiz Geçiş / Makro Denge",
}

# Time-based confirmation deliberately replaces the old hit-count semantics.
# The values can be tightened/relaxed without changing the detector itself.
CONFIRMATION_MINUTES = {
    "SHOCK": 120,
    "RISK_ON": 720,
    "DENGE": 0,
}
MIN_DWELL_MINUTES = 90
EMERGENCY_SHOCK_Z = 3.25
CANDIDATE_DECAY_HOURS = 12.0


class StatefulRegimeController:
    def __init__(
        self,
        store: StatefulMemoryStore,
        confirmation_minutes: Optional[Dict[str, int]] = None,
    ) -> None:
        self.store = store
        self.confirmation_minutes = dict(CONFIRMATION_MINUTES)
        if confirmation_minutes:
            self.confirmation_minutes.update(confirmation_minutes)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _dt(value: Any) -> Optional[datetime]:
        if value is None:
            return None
        try:
            text = str(value).replace("Z", "+00:00")
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _candidate_key(value: Any) -> str:
        return str(value) if value is not None else "REJIMSIZ_GECIS"

    @staticmethod
    def _macro_strength(raw: Dict[str, Any]) -> float:
        z_map = raw.get("indicator_z_scores", {})
        if not isinstance(z_map, dict):
            return 0.0
        vals = []
        for value in z_map.values():
            try:
                x = float(value)
                if np.isfinite(x):
                    vals.append(abs(x))
            except (TypeError, ValueError):
                continue
        if not vals:
            return 0.0
        return float(max(vals))

    def update(self, raw_diagnostics: Dict[str, Any]) -> Dict[str, Any]:
        """Return raw diagnostics augmented with persistent active/candidate state."""
        now = self._now()
        raw = deepcopy(raw_diagnostics or {})
        state = self.store.get_regime_state()

        confirmed_id = state.get("confirmed_regime_id")
        candidate_id = state.get("candidate_regime_id")
        candidate_since = self._dt(state.get("candidate_since"))
        last_transition = self._dt(state.get("last_transition_at"))

        raw_candidate = raw.get("candidate_regime_id", raw.get("active_regime_id"))
        raw_candidate_key = self._candidate_key(raw_candidate)
        strength = self._macro_strength(raw)
        candidate_type = REGIME_TYPES.get(raw_candidate, REGIME_TYPES.get(raw_candidate_key, "DENGE"))

        # "REJIMSIZ_GECIS" means no active trigger, not "forget the prior regime".
        no_candidate = raw_candidate_key == "REJIMSIZ_GECIS"

        if no_candidate:
            candidate_id = None
            candidate_since = None
            support = 0.0
        else:
            if self._candidate_key(candidate_id) != raw_candidate_key:
                candidate_id = raw_candidate
                candidate_since = now
                support = 0.0
            else:
                previous_support = float(state.get("candidate_support", 0.0))
                elapsed_h = 0.0
                if candidate_since is not None:
                    elapsed_h = max((now - candidate_since).total_seconds() / 3600.0, 0.0)
                target = max(strength / 3.0, 0.0)
                persistence = 1.0 - np.exp(-elapsed_h / max(CANDIDATE_DECAY_HOURS, 1e-9))
                support = float(np.clip(0.55 * target + 0.45 * persistence + 0.15 * previous_support, 0.0, 1.5))

        candidate_elapsed_min = 0.0
        if candidate_since is not None:
            candidate_elapsed_min = max((now - candidate_since).total_seconds() / 60.0, 0.0)

        emergency = bool(
            not no_candidate
            and candidate_type == "SHOCK"
            and strength >= EMERGENCY_SHOCK_Z
        )

        required_minutes = int(self.confirmation_minutes.get(candidate_type, 240))
        time_confirmed = bool(candidate_since is not None and candidate_elapsed_min >= required_minutes)
        support_confirmed = support >= 0.80
        can_confirm = emergency or (time_confirmed and support_confirmed)

        current_confirmed_key = self._candidate_key(confirmed_id) if confirmed_id is not None else None
        candidate_is_same = current_confirmed_key == raw_candidate_key

        dwell_ok = True
        if last_transition is not None:
            dwell_ok = (now - last_transition).total_seconds() / 60.0 >= MIN_DWELL_MINUTES

        if not no_candidate and can_confirm and (not candidate_is_same) and dwell_ok:
            confirmed_id = raw_candidate
            last_transition = now
            transition_reason = "EMERGENCY_SHOCK" if emergency else "PERSISTENT_CONFIRMED"
        elif candidate_is_same:
            transition_reason = "ALREADY_CONFIRMED"
        elif no_candidate:
            transition_reason = "NO_NEW_TRIGGER_KEEP_CONFIRMED"
        else:
            transition_reason = "CANDIDATE_PENDING_CONFIRMATION"

        if confirmed_id is None:
            active_id = raw_candidate if not no_candidate else "REJIMSIZ_GECIS"
            active_source = "BOOTSTRAP_CANDIDATE"
            active_confirmed = False
        else:
            active_id = confirmed_id
            active_source = "PERSISTENT_CONFIRMED"
            active_confirmed = True

        active_name = REGIME_NAMES.get(active_id, raw.get("active_regime_name", "Rejimsiz Geçiş"))
        active_type = REGIME_TYPES.get(active_id, raw.get("active_regime_type", "DENGE"))
        active_thresholds = deepcopy(
            REGIME_DYNAMIC_THRESHOLDS.get(active_id, REGIME_DYNAMIC_THRESHOLDS["REJIMSIZ_GECIS"])
        )

        new_state = {
            "confirmed_regime_id": active_id,
            "candidate_regime_id": candidate_id,
            "candidate_since": candidate_since.astimezone(timezone.utc).isoformat() if candidate_since else None,
            "candidate_support": round(float(support), 6),
            "candidate_elapsed_minutes": round(candidate_elapsed_min, 2),
            "last_transition_at": last_transition.astimezone(timezone.utc).isoformat() if last_transition else None,
            "last_raw_candidate": raw_candidate,
            "last_raw_strength_z": round(float(strength), 6),
            "last_update_at": now.isoformat(),
        }
        self.store.set_regime_state(new_state)

        result = deepcopy(raw)
        result.update({
            "active_regime_id": active_id,
            "active_regime_name": active_name,
            "active_regime_type": active_type,
            "active_regime_subtype": raw.get("active_regime_subtype", REGIME_DYNAMIC_THRESHOLDS.get(active_id, {}).get("name", "DENGE")),
            "dynamic_thresholds": active_thresholds,
            "is_confirmed": bool(active_confirmed),
            "candidate_regime_id": candidate_id,
            "candidate_elapsed_minutes": round(candidate_elapsed_min, 2),
            "candidate_support": round(float(support), 4),
            "candidate_strength_z": round(float(strength), 4),
            "stateful_transition_reason": transition_reason,
            "stateful_active_source": active_source,
            "stateful_emergency_override": emergency,
            "stateful_required_confirmation_minutes": required_minutes,
            "stateful_min_dwell_minutes": MIN_DWELL_MINUTES,
        })

        if active_id == "REJIMSIZ_GECIS":
            result["formatted_label"] = "⚪ [REJİMSİZ GEÇİŞ] Rejimsiz Geçiş / Makro Denge"
        else:
            icon = {1: "🛢️", 2: "🚨", 3: "⚡", 4: "⚠️", 5: "🟢"}.get(active_id, "⚪")
            result["formatted_label"] = f"{icon} [REJİM {active_id}] {active_name}"

        return result

    def apply_to_gatekeeper(self, gatekeeper: Any) -> Dict[str, Any]:
        """Run controller from gatekeeper's latest diagnostics and patch active fields."""
        controlled = self.update(getattr(gatekeeper, "macro_diagnostics", {}) or {})
        gatekeeper.macro_diagnostics = controlled
        gatekeeper.active_macro_regime_id = controlled.get("active_regime_id", "REJIMSIZ_GECIS")
        gatekeeper.active_macro_regime_name = controlled.get("active_regime_name", "Rejimsiz Geçiş / Makro Denge")
        gatekeeper.market_regime = controlled.get("formatted_label", "⚪ [REJİMSİZ GEÇİŞ]")
        gatekeeper.active_subtype = controlled.get("active_regime_subtype", "DENGE")
        gatekeeper.dynamic_thresholds = controlled.get("dynamic_thresholds", REGIME_DYNAMIC_THRESHOLDS["REJIMSIZ_GECIS"])
        return controlled
