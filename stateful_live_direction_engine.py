"""
Stateful Live Direction Engine
==============================
"Canlı Fiyat Yönü" (1-4 saat ufuk) için bağımsız, gün-içi rejime duyarlı ve
kendi kendini kalibre eden motor.

Neden ayrı bir motor?
----------------------
`StatefulDirectionEngine` (bkz. stateful_direction_engine.py) "Model
Sinyali"ni (24 saat-1 hafta ufuk) hesaplar ve haftalık histerezisli MAKRO
rejime (`active_macro_regime_id`) göre kalibre olur. Canlı Fiyat Yönü ise
tanım gereği ÇOK DAHA KISA bir ufku (1-4 saat) yansıtmalı ve GÜN İÇİ
(intraday trend/volatilite) rejimine göre kalibre olmalı. İkisini aynı
motorda karıştırmak, tam olarak kullanıcının şikayet ettiği duruma yol
açıyordu: kısa vadeli "canlı" etiket, yavaş hareket eden haftalık rejim
eşikleriyle karışıyor ve gösterilen % ile etiket birbiriyle çelişebiliyordu.

Bu motor üç şeyi garanti eder:
1. Etiket ve gösterilen % HER ZAMAN aynı skordan türetilir (çelişki yok).
2. Eşikler sabit sayılar değildir; her varlığın KENDİ gün-içi rejimindeki
   son skor dağılımının (p50/p70/p85) yüzdelik dilimlerinden türetilir ve
   yeni veriyle birlikte kendini günceller (dinamik / kendini geliştiren).
3. Gün-içi rejim değiştiğinde ("rejim olayı") bunu açıkça işaretler ve
   geçiş anındaki yanlış sinyal riskini azaltmak için eşikleri geçici
   olarak genişletir (daha az güvenle, daha az yanlış pozitif).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

import numpy as np

from stateful_memory_store import StatefulMemoryStore

LIVE_REGIME_PREFIX = "LIVE::"
BOOTSTRAP_P50 = 0.45
BOOTSTRAP_P70 = 0.85
BOOTSTRAP_P85 = 1.35
MIN_HISTORY_FOR_ADAPTIVE = 8.0
EVENT_WIDEN_FACTOR = 1.25  # rejim yeni değiştiyse eşikleri %25 genişlet


class StatefulLiveDirectionEngine:
    """Canlı (1-4 saat) fiyat yönü: gün-içi rejim + dinamik yüzdelik eşik + rejim-olay tespiti."""

    def __init__(self, store: StatefulMemoryStore) -> None:
        self.store = store

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _finite(value: Any, default: float = 0.0) -> float:
        try:
            x = float(value)
            return x if np.isfinite(x) else default
        except (TypeError, ValueError):
            return default

    def evaluate(
        self,
        asset: str,
        regime_label: str,
        score: float,
        ret_pct_1h: float,
        ret_pct_2h: float,
        leading_bias: float = 0.0,
        now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        current = now or self._now()
        score = float(np.clip(self._finite(score), -4.0, 4.0))
        leading_bias = float(np.clip(self._finite(leading_bias), -0.35, 0.35))
        adjusted_score = float(np.clip(score + leading_bias, -4.0, 4.0))

        # --- Rejim olayı (gün-içi rejim değişimi) tespiti ---
        prev = self.store.get_intraday_regime(asset)
        prev_label = str(prev.get("label")) if prev else None
        regime_event = bool(prev_label) and prev_label != regime_label
        self.store.set_intraday_regime(asset, regime_label, now=current)

        # --- Bu varlık + bu gün-içi rejim için dinamik (kendi kendini
        # güncelleyen) yüzdelik eşikler. Yeterli tarihçe yoksa güvenli bir
        # başlangıç (bootstrap) eşiği kullanılır. ---
        dist_key = f"{LIVE_REGIME_PREFIX}{regime_label}"
        snapshot = self.store.score_distribution_snapshot(asset, dist_key)
        n = float(snapshot.get("n", 0.0))
        if n >= MIN_HISTORY_FOR_ADAPTIVE:
            p50 = max(float(snapshot.get("abs_score_p50", BOOTSTRAP_P50)), 0.10)
            p70 = max(float(snapshot.get("abs_score_p70", BOOTSTRAP_P70)), p50 + 0.05)
            p85 = max(float(snapshot.get("abs_score_p85", BOOTSTRAP_P85)), p70 + 0.05)
            adaptive = True
        else:
            p50, p70, p85 = BOOTSTRAP_P50, BOOTSTRAP_P70, BOOTSTRAP_P85
            adaptive = False

        # Rejim yeni değiştiyse: geçiş anındaki gürültü/yanlış sinyal
        # riskini azaltmak için eşikleri geçici olarak genişlet.
        if regime_event:
            p50 *= EVENT_WIDEN_FACTOR
            p70 *= EVENT_WIDEN_FACTOR
            p85 *= EVENT_WIDEN_FACTOR

        abs_score = abs(adjusted_score)
        sign = 1 if adjusted_score > 0 else (-1 if adjusted_score < 0 else 0)

        if sign == 0 or abs_score < p50:
            tier = "YATAY"
        elif abs_score < p70:
            tier = "HAFİF"
        elif abs_score < p85:
            tier = "YÖNLÜ"
        else:
            tier = "GÜÇLÜ"

        if tier == "YATAY":
            label_core, icon, color = "YATAY / DENGELİ", "⚪", "gray"
        elif sign > 0:
            if tier == "GÜÇLÜ":
                label_core, icon, color = "GÜÇLÜ YUKARI", "🟢🟢", "darkgreen"
            elif tier == "YÖNLÜ":
                label_core, icon, color = "YUKARI", "🟢", "lightgreen"
            else:
                label_core, icon, color = "HAFİF YUKARI", "🟢", "palegreen"
        else:
            if tier == "GÜÇLÜ":
                label_core, icon, color = "GÜÇLÜ AŞAĞI", "🔴🔴", "darkred"
            elif tier == "YÖNLÜ":
                label_core, icon, color = "AŞAĞI", "🔴", "red"
            else:
                label_core, icon, color = "HAFİF AŞAĞI", "🔴", "lightcoral"

        display_pct = float(ret_pct_1h if ret_pct_1h is not None else 0.0)
        event_tag = " ⚠️REJİM GEÇİŞİ" if regime_event else ""
        label = f"{icon} {label_core} (%{display_pct:+.2f}){event_tag}"

        # Skoru sınıflandırma SONRASI dağılıma ekle (kendi kendini geçerli
        # verinin dışına referans vermesin diye — bkz. finalize_cycle'daki
        # aynı desen).
        self.store.update_score_distribution(asset, dist_key, adjusted_score, current)

        return {
            "current_direction": label,
            "current_icon": icon,
            "current_color": color,
            "current_roc": round(display_pct, 3),
            "live_score": round(adjusted_score, 4),
            "live_score_raw": round(score, 4),
            "live_leading_bias": round(leading_bias, 4),
            "live_tier": tier,
            "live_horizon": "1-4 saat",
            "live_regime_label": regime_label,
            "live_regime_event": regime_event,
            "live_thresholds": {"p50": round(p50, 4), "p70": round(p70, 4), "p85": round(p85, 4)},
            "live_thresholds_adaptive": adaptive,
            "live_history_n": round(n, 2),
            "ret_pct_1h": round(self._finite(ret_pct_1h), 4),
            "ret_pct_2h": round(self._finite(ret_pct_2h), 4),
        }
