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

from system_clock import now_utc
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import numpy as np

from stateful_memory_store import StatefulMemoryStore

LIVE_REGIME_PREFIX = "SHORT::"   # v3.6: forecast score lives on a new scale -> fresh distributions
BOOTSTRAP_P50 = 0.45
BOOTSTRAP_P70 = 0.85
BOOTSTRAP_P85 = 1.35
MIN_HISTORY_FOR_ADAPTIVE = 8.0
EVENT_WIDEN_FACTOR = 1.25  # rejim yeni değiştiyse eşikleri %25 genişlet (yaşla söner)
EVENT_DECAY_HOURS = 2.0    # v3.3.5: genişletme 2 saatte doğrusal olarak sıfıra iner
SHRINK_K = 12.0            # v3.3.5: rejim kovası güveni w = n/(n+K)
MIN_TIER_RATIO = 1.15
ANCHOR_THRESHOLDS = (0.60, 1.00, 1.50)   # v3.5: fixed meaning of HAFİF / YÖNLÜ / GÜÇLÜ (score units)
TIER_HYSTERESIS = 0.10                   # v3.5: enter +10% above, leave 10% below a boundary      # v3.3.5: kademeler arası asgari oran (p70>=1.15*p50 ...)


class StatefulLiveDirectionEngine:
    """Canlı (1-4 saat) fiyat yönü: gün-içi rejim + dinamik yüzdelik eşik + rejim-olay tespiti."""

    def __init__(self, store: StatefulMemoryStore) -> None:
        self.store = store

    @staticmethod
    def _now() -> datetime:
        return now_utc()

    @staticmethod
    def _finite(value: Any, default: float = 0.0) -> float:
        try:
            x = float(value)
            return x if np.isfinite(x) else default
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _significant_change(old: str, new: str) -> bool:
        """v3.3.6: a regime EVENT (warning + threshold widening) needs a real
        break: trend jumps two steps (YATAY <-> GÜÇLÜ) or the volatility state
        changes. Adjacent trend steps (ADX crossing 20 or 22) are routine and
        were flagging a 'regime transition' on ordinary drifts."""
        order = {"YATAY / TESTERE": 0, "GELİŞEN TREND": 1, "GÜÇLÜ TREND": 2}
        try:
            ot, ov = old.split(" · ", 1)
            nt, nv = new.split(" · ", 1)
        except ValueError:
            return True
        if ov != nv:
            return True
        return abs(order.get(ot, 1) - order.get(nt, 1)) >= 2

    def _abs_scores(self, asset: str, key: Optional[str]):
        node = (self.store.memory.get("score_distribution", {}) or {}).get(str(asset), {}) or {}
        out = []
        for k, st in node.items():
            if not str(k).startswith(LIVE_REGIME_PREFIX):
                continue
            if key is not None and k != key:
                continue
            out.extend(float(x) for x in (st.get("abs_scores") or []) if np.isfinite(float(x)))
        return out

    @staticmethod
    def _quantiles(vals):
        if not vals:
            return (0.0, 0.0, 0.0), 0
        arr = np.asarray(vals[-512:], dtype=float)
        return tuple(float(np.quantile(arr, q)) for q in (0.50, 0.70, 0.85)), int(len(arr))

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

        # --- Rejim olayı (v3.3.5) ---
        # Eskisi: etiket son YAZIMDAN beri değiştiyse "olay" -> 3-6 saatlik
        # arka plan aralığında ve histerezissiz etiketlerde döngülerin %40'ında
        # tetikleniyor, eşikleri sabit x1.25 genişletip yönü YATAY'a itiyordu.
        # Yeni: olay = etiketin YENİ başlaması; etkisi yaşla doğrusal söner
        # (EVENT_DECAY_HOURS sonra sıfır). Etiket histerezisli (quant_processor).
        prev = self.store.get_intraday_regime(asset)
        prev_label = str(prev.get("label")) if prev else None
        self.store.set_intraday_regime(asset, regime_label, now=current)
        node = self.store.get_intraday_regime(asset) or {}
        since = node.get("since")
        try:
            since_dt = datetime.fromisoformat(str(since).replace("Z", "+00:00"))
            if since_dt.tzinfo is None:
                since_dt = since_dt.replace(tzinfo=timezone.utc)
            age_h = max((current - since_dt).total_seconds() / 3600.0, 0.0)
        except Exception:
            age_h = 0.0 if (prev_label and prev_label != regime_label) else EVENT_DECAY_HOURS
        fresh = max(0.0, 1.0 - age_h / EVENT_DECAY_HOURS)
        # Only a RECORDED change counts (legacy entries without 'changed_from'
        # carry a meaningless 'since' = last write time).
        _from = str(node.get("changed_from") or "")
        # A switch from/to "VOLATİLİTE BİLİNMİYOR" is a DATA change, not a market one.
        regime_event = (bool(_from) and fresh > 0.0 and "BİLİNMİYOR" not in _from
                        and "BİLİNMİYOR" not in regime_label
                        and self._significant_change(_from, regime_label))
        if not regime_event:
            fresh = 0.0
        widen = 1.0 + (EVENT_WIDEN_FACTOR - 1.0) * fresh

        # --- Eşikler (v3.3.5): ampirik-Bayes küçültmesi ---
        # Eskisi: 12 (trend x volatilite) kovasının HER BİRİ ayrı; çoğunda n<8
        # -> sabit bootstrap. Aynı çiftte SPX bootstrap, NQ adaptif eşikle
        # etiketleniyordu; kova değişince eşik sıçrıyordu; n~10'da p70~p85.
        # Yeni: rejim kovası, varlığın TÜM canlı skor havuzuna doğru
        # w = n_r / (n_r + SHRINK_K) ile çekilir; havuz da azsa bootstrap'a.
        dist_key = f"{LIVE_REGIME_PREFIX}{regime_label}"
        reg_q, n_r = self._quantiles(self._abs_scores(asset, dist_key))
        pool_q, n_p = self._quantiles(self._abs_scores(asset, None))
        boot = (BOOTSTRAP_P50, BOOTSTRAP_P70, BOOTSTRAP_P85)
        wp = min(n_p / MIN_HISTORY_FOR_ADAPTIVE, 1.0)
        base = tuple(wp * pool_q[i] + (1.0 - wp) * boot[i] for i in range(3)) if n_p else boot
        known_vol = "BİLİNMİYOR" not in regime_label
        wr = (n_r / (n_r + SHRINK_K)) if (n_r and known_vol) else 0.0
        q = [wr * reg_q[i] + (1.0 - wr) * base[i] for i in range(3)] if n_r else list(base)
        # v3.5: the learned quantiles may only fine-tune a FIXED-meaning
        # anchor (+-20%). Pure self-referential percentiles from 10-20 points
        # moved with every observation (same score -0.88 labelled AŞAĞI, then
        # HAFİF AŞAĞI one run later) and made "GÜÇLÜ" mean "top 15% of THIS
        # asset's last few days" (NQ -2.08 was shown as HAFİF).
        a50, a70, a85 = ANCHOR_THRESHOLDS
        p50 = float(np.clip(max(q[0], 0.10), a50 * 0.8, a50 * 1.25))
        p70 = float(np.clip(max(q[1], p50 * MIN_TIER_RATIO), a70 * 0.8, a70 * 1.25))
        p85 = float(np.clip(max(q[2], p70 * MIN_TIER_RATIO), a85 * 0.8, a85 * 1.25))
        p70 = max(p70, p50 * MIN_TIER_RATIO)
        p85 = max(p85, p70 * MIN_TIER_RATIO)
        p50, p70, p85 = p50 * widen, p70 * widen, p85 * widen
        adaptive = n_p >= MIN_HISTORY_FOR_ADAPTIVE
        n = float(n_r)

        abs_score = abs(adjusted_score)
        sign = 1 if adjusted_score > 0 else (-1 if adjusted_score < 0 else 0)
        order = ("YATAY", "HAFİF", "YÖNLÜ", "GÜÇLÜ")

        def _tier(scale: float) -> int:
            if sign == 0 or abs_score < p50 * scale:
                return 0
            if abs_score < p70 * scale:
                return 1
            if abs_score < p85 * scale:
                return 2
            return 3

        # v3.5 HYSTERESIS: a tier is entered 10% above its boundary and left
        # 10% below it, so a score sitting on a boundary cannot flip the
        # label on every refresh / every bar.
        prev_t = (self.store.memory.get("live_tier_state", {}) or {}).get(str(asset), {})
        up, down = _tier(1.0 + TIER_HYSTERESIS), _tier(1.0 - TIER_HYSTERESIS)
        p_idx = int(prev_t.get("tier", -1)) if prev_t else -1
        p_sign = int(prev_t.get("sign", 0)) if prev_t else 0
        if p_idx < 0 or regime_event:
            t_idx = _tier(1.0)
        elif p_idx == 0 or p_sign == sign:
            if up > p_idx:
                t_idx = up
            elif down < p_idx:
                t_idx = down
            else:
                t_idx = p_idx
        else:                                     # direction reversal needs a clear crossing
            t_idx = up
        tier = order[t_idx]
        self.store.memory.setdefault("live_tier_state", {})[str(asset)] = {
            "tier": int(t_idx), "sign": int(sign if t_idx > 0 else 0)}

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
        label = f"{icon} {label_core} (son 1s %{display_pct:+.2f}){event_tag}"

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
            "live_regime_age_h": round(age_h, 2),
            "live_pool_n": int(n_p),
            "ret_pct_1h": round(self._finite(ret_pct_1h), 4),
            "ret_pct_2h": round(self._finite(ret_pct_2h), 4),
        }
