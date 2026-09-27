"""
Performance Ledger — out-of-sample, forward-only scoreboard
============================================================
Answers the one question every earlier change could not: "Does the
published signal actually predict the market?"

What it does, every background cycle:

1. RECORD  the FINAL published decision for every asset (after the
           stateful layer, pair reconciliation and the entry-timing gate):
           direction (+1 / -1 / 0), stage, entry grade (A/B/C), whether
           entry was allowed, score, regime, and the price + bar time it
           was made at.
2. SETTLE  every earlier record once its horizons (4h, 24h, 72h, 120h)
           have passed, using the price AT the horizon (as-of lookup in the
           stored 1H/1D bars, so late or skipped GitHub runs never distort
           the grade; a window with no traded bar is voided, not scored).
3. REPORT  hit-rate, average signed return, a conservative confidence bound
           and -- crucially -- the same numbers for two naive baselines
           over the SAME timestamps:
             * "Hep AL"        (always long)       -> is there real edge, or
                                                      just a rising market?
             * "Trend takibi"  (sign of the multi-timeframe price trend)
                                                  -> is the leading model
                                                      better than simply
                                                      following price?
           written to performance_report.md (readable from the GitHub app
           on a phone) and summarized into terminal_state.json.

Design rules:
* It is a pure OBSERVER. Nothing here feeds back into scores, weights or
  thresholds, so it cannot destabilize the model. It is the judge, not a
  player -- which is exactly what makes its numbers trustworthy.
* Point-in-time: a record is graded only with prices that printed after
  it was made.
* Overlap-aware statistics: records are made every cycle, so a 120h
  horizon overlaps dozens of neighbours. Hit-rates use all records, but
  the confidence bound uses a NON-overlapping subsample so it is not
  over-confident.
"""

from __future__ import annotations

import math
import os
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

from state_schema import atomic_write_json, load_versioned_json
from system_clock import now_utc

LEDGER_FILE = "performance_ledger.json"
REPORT_FILE = "performance_report.md"
SCHEMA_VERSION = "1.0.0"
HORIZONS_H = (4, 24, 72, 120)
MAX_RECORDS = 3000   # rolling window (~3-4 months at the observed Actions cadence); long history = historical replay
MIN_SAMPLES_FOR_VERDICT = 30
HEALTH_HALF_LIFE_CYCLES = 60.0


def _sign_from_verdict(verdict: Any) -> int:
    text = str(verdict or "").upper()
    has_buy = "AL" in text.replace("SAT", "")
    has_sell = "SAT" in text
    if has_buy and not has_sell:
        return 1
    if has_sell and not has_buy:
        return -1
    return 0


def _close_series(df: Any) -> Optional[pd.Series]:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty or "Close" not in df.columns:
        return None
    s = pd.to_numeric(df["Close"], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if s.empty:
        return None
    idx = pd.to_datetime(s.index, utc=True, errors="coerce")
    s = pd.Series(s.values, index=idx)
    s = s[~s.index.isna()]
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s if not s.empty else None


def wilson_lower_bound(wins: float, n: float, z: float = 1.6448536) -> float:
    """One-sided 95% lower bound of a hit-rate."""
    if n <= 0:
        return 0.0
    p = wins / n
    denom = 1.0 + z * z / n
    centre = p + z * z / (2.0 * n)
    margin = z * math.sqrt(max(p * (1.0 - p) / n + z * z / (4.0 * n * n), 0.0))
    return max(0.0, (centre - margin) / denom)


class PerformanceLedger:
    def __init__(self, path: str = LEDGER_FILE) -> None:
        self.path = path
        self.data: Dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "records": [],
            "health": {},
            "meta": {"cycles": 0},
        }
        loaded = load_versioned_json(
            path, SCHEMA_VERSION,
            validator=lambda p: isinstance(p.get("records", []), list),
        )
        if loaded:
            loaded.setdefault("records", [])
            loaded.setdefault("health", {})
            loaded.setdefault("meta", {"cycles": 0})
            self.data = loaded

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------
    def record_cycle(
        self,
        verdicts: Dict[str, Dict[str, Any]],
        grid_1h: Dict[str, Any],
        asset_frame_lookup,
        regime_id: Any,
    ) -> int:
        """``asset_frame_lookup(grid, asset_key) -> DataFrame`` resolves the
        asset's own 1H frame (same resolver the controller uses)."""
        records: List[Dict[str, Any]] = self.data.setdefault("records", [])
        last_bar_by_asset = {}
        for r in reversed(records):
            last_bar_by_asset.setdefault(r["a"], r["t"])
            if len(last_bar_by_asset) >= len(verdicts):
                break

        added = 0
        for asset, v in (verdicts or {}).items():
            if not isinstance(v, dict):
                continue
            s = _close_series(asset_frame_lookup(grid_1h, asset))
            if s is None:
                continue
            bar_time = s.index[-1].isoformat()
            if last_bar_by_asset.get(asset) == bar_time:
                continue  # same bar as last record (e.g. weekend re-run) -> not new information
            price = float(s.iloc[-1])
            if not np.isfinite(price) or price <= 0:
                continue
            conf = v.get("timeframe_confluence") or {}
            trend_sign = 0
            if conf.get("available"):
                cs = float(conf.get("confluence_score", 0.0))
                trend_sign = 1 if cs > 0.05 else (-1 if cs < -0.05 else 0)
            records.append({
                "a": asset,
                "t": bar_time,
                "rec": now_utc().isoformat(),
                "p": round(price, 6),
                "d": _sign_from_verdict(v.get("verdict")),
                "stg": str(v.get("direction_stage", "")),
                "g": str(v.get("entry_grade", "")),
                "e": bool(v.get("entry_allowed", False)),
                "sc": round(float(v.get("score", 0.0) or 0.0), 4),
                "rg": str(regime_id),
                "tr": trend_sign,
                "o": {},
            })
            added += 1

        if len(records) > MAX_RECORDS:
            del records[: len(records) - MAX_RECORDS]
        self.data.setdefault("meta", {})["cycles"] = int(self.data.get("meta", {}).get("cycles", 0)) + 1
        self.data["meta"]["last_cycle"] = now_utc().isoformat()
        return added

    # ------------------------------------------------------------------
    # Settlement
    # ------------------------------------------------------------------
    def settle(self, series_by_asset: Dict[str, Dict[str, Optional[pd.Series]]]) -> int:
        """``series_by_asset[asset] = {"1h": Series|None, "1d": Series|None}``.
        Returns number of (record, horizon) outcomes newly graded."""
        now = pd.Timestamp(now_utc())
        graded = 0
        for r in self.data.get("records", []):
            outcomes = r.setdefault("o", {})
            if len(outcomes) >= len(HORIZONS_H):
                continue
            src = series_by_asset.get(r["a"]) or {}
            t0 = pd.Timestamp(r["t"])
            if t0.tzinfo is None:
                t0 = t0.tz_localize("UTC")
            for h in HORIZONS_H:
                key = str(h)
                if key in outcomes:
                    continue
                target = t0 + pd.Timedelta(hours=h)
                if now < target:
                    continue
                px, state = self._price_at(src, t0, target)
                if state == "void":
                    outcomes[key] = None
                    continue
                if state == "pending":
                    if (now - target) > pd.Timedelta(days=10):
                        outcomes[key] = None  # data never arrived -> void
                    continue
                ret = math.log(px / float(r["p"])) if px > 0 else None
                outcomes[key] = None if ret is None or ret == 0.0 else round(ret, 6)
                graded += 1
        return graded

    @staticmethod
    def _price_at(src: Dict[str, Optional[pd.Series]], t0: pd.Timestamp, target: pd.Timestamp):
        """As-of price at ``target`` using only bars that printed after t0.
        Returns (price, "ok") | (None, "void") | (None, "pending")."""
        s1 = src.get("1h")
        if s1 is not None and not s1.empty and s1.index[0] <= t0:
            if s1.index[-1] >= target:
                window = s1[(s1.index > t0) & (s1.index <= target)]
                if window.empty:
                    return None, "void"      # market closed for the whole window
                return float(window.iloc[-1]), "ok"
            return None, "pending"
        sd = src.get("1d")
        if sd is not None and not sd.empty:
            # a daily bar is stamped with its session date; only sessions
            # that started after t0's date AND finished by target count
            finished = sd[(sd.index > t0.normalize()) & (sd.index + pd.Timedelta(hours=24) <= target)]
            if not finished.empty:
                return float(finished.iloc[-1]), "ok"
            if sd.index[-1] + pd.Timedelta(hours=24) > target:
                return None, "void"          # data covers target but no full session inside window
        return None, "pending"

    # ------------------------------------------------------------------
    # Data-health bookkeeping (decayed availability per factor)
    # ------------------------------------------------------------------
    def update_health(self, verdicts: Dict[str, Dict[str, Any]]) -> None:
        health = self.data.setdefault("health", {})
        decay = math.exp(-math.log(2.0) / HEALTH_HALF_LIFE_CYCLES)
        for asset, v in (verdicts or {}).items():
            if not isinstance(v, dict):
                continue
            for row in v.get("details", []) or []:
                name = str(row.get("faktör") or row.get("faktor") or row.get("faktor_id") or "?")
                key = f"{asset}|{name}"
                cell = health.get(key, {"n": 0.0, "ok": 0.0})
                ok = row.get("ham_deger") is not None and not str(row.get("durum", "")).upper().startswith("VERİ YETERSİZ")
                cell["n"] = float(cell["n"]) * decay + 1.0
                cell["ok"] = float(cell["ok"]) * decay + (1.0 if ok else 0.0)
                cell["last_ok"] = bool(ok)
                health[key] = cell

    def save(self) -> None:
        self.data["schema_version"] = SCHEMA_VERSION
        atomic_write_json(self.path, self.data, indent=None, sort_keys=False, separators=(",", ":"))

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------
    @staticmethod
    def _stats(rows: List[Dict[str, Any]], h: int, sign_fn) -> Dict[str, Any]:
        key = str(h)
        xs = []
        for r in rows:
            ret = (r.get("o") or {}).get(key)
            d = sign_fn(r)
            if ret is None or d == 0:
                continue
            xs.append((r["a"], pd.Timestamp(r["t"]), d * float(ret)))
        n = len(xs)
        if n == 0:
            return {"n": 0}
        wins = sum(1 for _, _, x in xs if x > 0)
        mean_bps = float(np.mean([x for _, _, x in xs])) * 1e4
        # non-overlapping subsample per asset for an honest confidence bound
        xs_sorted = sorted(xs, key=lambda z: (z[0], z[1]))
        last_t: Dict[str, pd.Timestamp] = {}
        n_ind = w_ind = 0
        for a, t, x in xs_sorted:
            if a in last_t and (t - last_t[a]) < pd.Timedelta(hours=h):
                continue
            last_t[a] = t
            n_ind += 1
            w_ind += 1 if x > 0 else 0
        hit = wins / n
        # Confidence bound: full-sample hit-rate, but only as many
        # "independent" observations as there are non-overlapping windows
        # (effective sample size) -- overlapping horizons are not new
        # evidence and must not make the bound look tighter than it is.
        return {
            "n": n,
            "hit": hit,
            "mean_bps": mean_bps,
            "n_indep": n_ind,
            "hit_lb95": wilson_lower_bound(hit * n_ind, n_ind),
        }

    def summary(self) -> Dict[str, Any]:
        rows = [r for r in self.data.get("records", []) if r.get("o")]
        out: Dict[str, Any] = {"generated_at": now_utc().isoformat(), "assets": {}, "overall": {}}
        assets = sorted({r["a"] for r in rows})
        model = lambda r: r["d"]
        always_long = lambda r: 1 if r["d"] != 0 else 0          # same timestamps as model calls
        trend = lambda r: r.get("tr", 0) if r["d"] != 0 else 0    # reactive baseline, same timestamps
        for h in HORIZONS_H:
            out["overall"][str(h)] = {
                "model": self._stats(rows, h, model),
                "always_long": self._stats(rows, h, always_long),
                "trend_follow": self._stats(rows, h, trend),
                "entry_allowed": self._stats([r for r in rows if r.get("e")], h, model),
                "grade_A": self._stats([r for r in rows if r.get("g") == "A"], h, model),
                "grade_B": self._stats([r for r in rows if r.get("g") == "B"], h, model),
                "grade_C": self._stats([r for r in rows if r.get("g") == "C"], h, model),
            }
        for a in assets:
            ra = [r for r in rows if r["a"] == a]
            out["assets"][a] = {
                str(h): {
                    "model": self._stats(ra, h, model),
                    "always_long": self._stats(ra, h, always_long),
                    "trend_follow": self._stats(ra, h, trend),
                    "entry_allowed": self._stats([r for r in ra if r.get("e")], h, model),
                }
                for h in HORIZONS_H
            }
        regimes = sorted({r.get("rg", "?") for r in rows})
        out["regimes"] = {
            rg: {str(h): self._stats([r for r in rows if r.get("rg") == rg], h, model) for h in (24, 72)}
            for rg in regimes
        }
        health = self.data.get("health", {})
        out["data_health"] = {
            k: round(v["ok"] / v["n"], 3) for k, v in health.items() if v.get("n", 0) > 0
        }
        out["records_total"] = len(self.data.get("records", []))
        out["records_graded"] = len(rows)
        out["cycles"] = int(self.data.get("meta", {}).get("cycles", 0))
        return out

    # ------------------------------------------------------------------
    # Human-readable report (Turkish)
    # ------------------------------------------------------------------
    @staticmethod
    def _fmt(st: Dict[str, Any]) -> str:
        if not st or st.get("n", 0) == 0:
            return "— (veri yok)"
        flag = "" if st.get("n_indep", 0) >= MIN_SAMPLES_FOR_VERDICT else " ⚠️az bağımsız örnek"
        return (f"%{st['hit']*100:.1f} isabet · ort {st['mean_bps']:+.0f} bps · "
                f"n={st['n']} (bağımsız {st['n_indep']}, alt sınır %{st['hit_lb95']*100:.0f}){flag}")

    @staticmethod
    def _edge_line(model: Dict[str, Any], base: Dict[str, Any], trend: Dict[str, Any]) -> str:
        if not model or model.get("n_indep", 0) < MIN_SAMPLES_FOR_VERDICT:
            return f"Karar için henüz yeterli bağımsız örnek yok (gereken: {MIN_SAMPLES_FOR_VERDICT})."
        best_base = max(
            [b.get("hit", 0.0) for b in (base, trend) if b and b.get("n", 0) > 0] or [0.5]
        )
        edge = (model["hit"] - best_base) * 100
        if model.get("hit_lb95", 0) > 0.5 and edge > 0:
            return f"✅ Kanıtlanmış avantaj: en iyi basit yöntemden {edge:+.1f} puan iyi ve alt güven sınırı %50'nin üzerinde."
        if edge > 0:
            return f"🟡 Olumlu ama henüz istatistiksel olarak kanıtlanmadı ({edge:+.1f} puan)."
        return f"🔴 Model basit yöntemlerin gerisinde ({edge:+.1f} puan) — bu varlık/ufuk için sinyal henüz güvenilir değil."

    def write_report(self, path: str = REPORT_FILE, extra_lines: Optional[Iterable[str]] = None) -> Dict[str, Any]:
        s = self.summary()
        L: List[str] = []
        L.append("# 📊 Canlı Performans Karnesi (örneklem dışı, ileriye dönük)")
        L.append("")
        L.append(f"_Son güncelleme: {s['generated_at']} · döngü: {s['cycles']} · kayıt: {s['records_total']} (notlanan: {s['records_graded']})_")
        L.append("")
        L.append("Bu sayfa sistemin **yayınladığı nihai sinyalleri** gerçekleşen fiyatla notlar. "
                 "Model bu sayfadan öğrenmez; sadece hakemdir. "
                 f"Bir satırın güvenilir olması için en az **{MIN_SAMPLES_FOR_VERDICT}** bağımsız (çakışmayan) örnek gerekir.")
        L.append("")
        L.append("**Nasıl okunur:** *isabet* = yön doğru tahmin oranı · *ort bps* = sinyal yönünde ortalama getiri "
                 "(1 bps = %0,01) · *alt sınır* = %95 güvenle gerçek isabetin en az bu kadar olduğu değer. "
                 "Model, **Hep AL** ve **Trend takibi** (fiyatın gidişine bakan reaktif yöntem) ile AYNI anlarda karşılaştırılır.")
        L.append("")
        L.append("## Genel")
        for h in HORIZONS_H:
            o = s["overall"][str(h)]
            L.append(f"### {h} saat sonrası")
            L.append(f"- **Model:** {self._fmt(o['model'])}")
            L.append(f"- Hep AL: {self._fmt(o['always_long'])}")
            L.append(f"- Trend takibi: {self._fmt(o['trend_follow'])}")
            L.append(f"- Sadece giriş izni verilenler: {self._fmt(o['entry_allowed'])}")
            L.append(f"- Zamanlama notu A: {self._fmt(o['grade_A'])}")
            L.append(f"- Zamanlama notu B: {self._fmt(o['grade_B'])}")
            L.append(f"- Zamanlama notu C: {self._fmt(o['grade_C'])}")
            L.append(f"- Sonuç: {self._edge_line(o['model'], o['always_long'], o['trend_follow'])}")
            L.append("")
        L.append("## Varlık bazında (24 saat ve 72 saat)")
        for a, per in s["assets"].items():
            L.append(f"### {a}")
            for h in (24, 72):
                o = per[str(h)]
                L.append(f"- {h}s Model: {self._fmt(o['model'])}")
                L.append(f"  - Hep AL: {self._fmt(o['always_long'])} · Trend: {self._fmt(o['trend_follow'])}")
                L.append(f"  - {self._edge_line(o['model'], o['always_long'], o['trend_follow'])}")
            L.append("")
        if s.get("regimes"):
            L.append("## Rejim bazında (Model)")
            for rg, per in s["regimes"].items():
                L.append(f"- Rejim {rg}: 24s {self._fmt(per['24'])} · 72s {self._fmt(per['72'])}")
            L.append("")
        weak = sorted((v, k) for k, v in s.get("data_health", {}).items() if v < 0.80)
        L.append("## Veri sağlığı (faktör bazında erişilebilirlik)")
        if weak:
            L.append("Aşağıdaki faktörler son döngülerin önemli kısmında **veri alamadı** ve skora katılmadı:")
            for v, k in weak[:40]:
                L.append(f"- {k}: %{v*100:.0f} erişilebilir")
        else:
            L.append("- Tüm faktörler son döngülerde %80+ oranında veri aldı. ✅")
        L.append("")
        for line in extra_lines or []:
            L.append(line)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(L) + "\n")
        return s


def _daily_frame(grid_1d: Dict[str, Any], asset_key: str):
    df = grid_1d.get(asset_key)
    if isinstance(df, pd.DataFrame) and not df.empty:
        return df
    try:
        from config import ASSET_MATRICES
        sym = str(ASSET_MATRICES.get(asset_key, {}).get("benchmark_symbol", ""))
    except Exception:
        sym = ""
    for k in (sym, sym.replace("=F", "")):
        df = grid_1d.get(k)
        if isinstance(df, pd.DataFrame) and not df.empty:
            return df
    return None


def build_series_map(gatekeeper, asset_keys: Iterable[str], asset_frame_lookup) -> Dict[str, Dict[str, Optional[pd.Series]]]:
    grid_1h = getattr(gatekeeper, "grid_1h", {}) or {}
    grid_1d = getattr(gatekeeper, "grid_daily", {}) or {}
    out = {}
    for a in asset_keys:
        out[a] = {
            "1h": _close_series(asset_frame_lookup(grid_1h, a)),
            "1d": _close_series(_daily_frame(grid_1d, a)),
        }
    return out


def run_ledger_cycle(gatekeeper, verdicts, asset_frame_lookup, extra_report_lines=None) -> Dict[str, Any]:
    """One call per background cycle: settle -> record -> health -> save -> report."""
    ledger = PerformanceLedger()
    series = build_series_map(gatekeeper, verdicts.keys(), asset_frame_lookup)
    graded = ledger.settle(series)
    added = ledger.record_cycle(
        verdicts, getattr(gatekeeper, "grid_1h", {}) or {}, asset_frame_lookup,
        getattr(gatekeeper, "active_macro_regime_id", "REJIMSIZ_GECIS"),
    )
    ledger.update_health(verdicts)
    ledger.save()
    summary = ledger.write_report(extra_lines=extra_report_lines)
    compact = {
        "graded_this_cycle": graded,
        "recorded_this_cycle": added,
        "records_total": summary["records_total"],
        "records_graded": summary["records_graded"],
        "overall_24h": summary["overall"]["24"]["model"],
        "overall_72h": summary["overall"]["72"]["model"],
    }
    return compact
