"""
Tahmin Karnesi (v16.4) — arayüzün kendi tahminlerini kaydeder ve notlar
=======================================================================
Merkez bankalarının tahmin değerlendirme ve fonların risk-modeli geri test
(backtesting) mantığı. Her tahmin, sonuç bilinmeden ÖNCE deftere yazılır;
ufuk dolunca gerçekleşen fiyatla notlanır. Sonradan değiştirilemez.

Notlanan tahminler (her varlık, saatte en fazla bir kayıt):
1. Günlük aralık (1σ): 24 saat sonra fiyat aralıkta mı?
   Ölçüt: kapsama oranı hedefi %68.3 (Kupiec tarzı kapsama testi).
   Kalibrasyon: |getiri|/σ dağılımının %68.3'lük yüzdeliği → aralık çarpanı
   (sınırlar 0.7–1.5; en az 30 bağımsız gün). Aralık bu çarpanla düzeltilir.
2. Son 4 saat eğilimi: sonraki 4 saat aynı yönde mi?
   Ölçüt: isabet oranı ve binom z (örtüşmesin diye sadece 4 saatte bir örnek).
   Kanıt: n ≥ 100 ve z ≥ 2 → "kanıtlı"; aksi halde "kanıtsız".
3. Sakin/hareketli etiketi: oynaklık oranı sonraki 24 saatlik |getiri|/normal σ
   ile sıra korelasyonu (pozitif olmalı).
4. Sonraki gün yükseliş olasılığı (taban oran): Brier skoru ve iklimsel
   (%50) tahmine göre beceri skoru (Brier Skill Score).

Bu modül gözlemcidir: yön veya giriş kararını değiştirmez. Tek geri bildirimi
aralık çarpanıdır (sınırlı ve açık ölçütlü).
"""
from __future__ import annotations

import math
import os
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from system_clock import now_utc

try:
    from config import LOGIC_VERSION as LOGIC
except Exception:
    LOGIC = "?"

LEDGER_FILE = "forecast_ledger.csv"
COLS = ["ts", "asset", "price", "sigma_pct", "lean4h", "calm_ratio", "p_up_1d",
        "ret_4h", "ret_24h", "graded_4h", "graded_24h", "logic", "pulse", "day_dir"]
TARGET_COVER = 0.6827
MIN_DAYS = 30
MIN_LEAN = 100
MAX_ROWS = 40000
STRICT_4H_SCHEMA = "NEXT_HOUR_OPEN_TO_OPEN_V1"
LABEL_4H_COLS = ["observed_at_utc", "label_4h_schema", "label_4h_start_utc",
                 "label_4h_end_utc", "label_4h_reason", "label_4h_graded_at_utc"]
COLS += LABEL_4H_COLS + ["label_4h_start_price", "label_4h_end_price"]



def _price_at(df: pd.DataFrame, t: pd.Timestamp, max_wait_h: float = 72.0) -> Optional[float]:
    idx = pd.to_datetime(df.index, utc=True)
    w = df[(idx >= t) & (idx <= t + pd.Timedelta(hours=max_wait_h))]
    if w.empty:
        return None
    return float(pd.to_numeric(w["Close"]).iloc[0])


def _utc_stamp(value):
    t = pd.Timestamp(value)
    if pd.isna(t):
        raise ValueError("timestamp missing")
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def _strict_4h_return(df, start, end):
    """Reference open to open, five exact hourly bars, never a later quote.

    The model is recorded before start. The endpoint bar must be observed
    after completion by the caller. These are market-data proxies, not fills.
    """
    if not isinstance(df, pd.DataFrame) or df.empty or "Open" not in df:
        return None
    if end != start + pd.Timedelta(hours=4):
        return None
    opens = pd.to_numeric(df["Open"], errors="coerce").copy()
    opens.index = pd.to_datetime(opens.index, utc=True, errors="coerce")
    if opens.index.has_duplicates:
        # Duplicate target timestamps have ambiguous provenance.
        opens = opens.loc[~opens.index.duplicated(keep=False)]
    required = pd.date_range(start, end, freq="h")
    values = opens.reindex(required).to_numpy(dtype=float, na_value=np.nan)
    if not np.isfinite(values).all() or (values <= 0).any():
        return None
    return float(values[0]), float(values[-1]), math.log(values[-1] / values[0])


class ForecastLedger:
    def __init__(self, path: str = LEDGER_FILE):
        self.path = path
        if os.path.exists(path):
            try:
                self.df = pd.read_csv(path)
            except Exception:
                self.df = pd.DataFrame(columns=COLS)
        else:
            self.df = pd.DataFrame(columns=COLS)
        for c in COLS:
            if c not in self.df.columns:
                self.df[c] = np.nan
        # Old ledgers retain their exact grades; new string metadata is not
        # silently coerced to float by pandas when the first new row arrives.
        for c in LABEL_4H_COLS:
            self.df[c] = self.df[c].astype(object)

    def record(self, asset: str, v: Dict[str, Any], now: Any = None, logic: str = LOGIC) -> bool:
        dr = v.get("day_range") or {}
        price = dr.get("price")
        if not price:
            return False
        observation = _utc_stamp(now or now_utc())
        ts = observation.floor("h").isoformat()
        # The hourly bucket is an id, never the exact observation time.
        # Use the strictly NEXT hourly open as a prospective reference.
        start = observation.floor("h") + pd.Timedelta(hours=1)
        end = start + pd.Timedelta(hours=4)
        if ((self.df["ts"] == ts) & (self.df["asset"] == asset)).any():
            return False
        rm = v.get("recent_move") or {}
        b1 = (v.get("base_rates") or {}).get("1") or (v.get("base_rates") or {}).get(1) or {}
        from stop_levels import evidence_short_side
        self.df.loc[len(self.df)] = {
            "ts": ts, "asset": asset, "price": float(price),
            "sigma_pct": float(dr.get("move_raw", dr["move"])) / float(price),
            "lean4h": evidence_short_side(v) if rm else np.nan,
            "calm_ratio": (v.get("vol_state") or {}).get("ratio", np.nan),
            "p_up_1d": b1.get("up", np.nan),
            "ret_4h": np.nan, "ret_24h": np.nan, "graded_4h": 0, "graded_24h": 0, "logic": logic,
            "pulse": (v.get("pulse") or {}).get("score", np.nan), "day_dir": (v.get("day_direction") or {}).get("side", np.nan),
            "observed_at_utc": observation.isoformat(), "label_4h_schema": STRICT_4H_SCHEMA,
            "label_4h_start_utc": start.isoformat(), "label_4h_end_utc": end.isoformat(),
            "label_4h_reason": "PENDING_EXACT_WINDOW",
            "label_4h_start_price": np.nan, "label_4h_end_price": np.nan,
            "label_4h_graded_at_utc": ""}
        return True

    def grade(self, frames: Dict[str, pd.DataFrame], now: Any = None) -> int:
        now = _utc_stamp(now or now_utc())
        n = 0
        strict = self.df[(self.df["graded_4h"].fillna(0) == 0) &
                         self.df["label_4h_schema"].eq(STRICT_4H_SCHEMA)]
        for i, row in strict.iterrows():
            try:
                seen = _utc_stamp(row["observed_at_utc"])
                start = _utc_stamp(row["label_4h_start_utc"])
                end = _utc_stamp(row["label_4h_end_utc"])
                if start != seen.floor("h") + pd.Timedelta(hours=1) or end != start + pd.Timedelta(hours=4):
                    raise ValueError("invalid horizon")
            except (ValueError, TypeError):
                self.df.at[i, "graded_4h"] = -1
                self.df.at[i, "label_4h_reason"] = "INVALID_WINDOW_PROVENANCE"
                continue
            # Do not read a still-forming endpoint even if the provider
            # exposes the bar early. Allow delayed publication of exact bars.
            if now < end + pd.Timedelta(hours=1):
                continue
            evidence = _strict_4h_return(frames.get(row["asset"]), start, end)
            if evidence is None:
                if now > end + pd.Timedelta(hours=96):
                    self.df.at[i, "graded_4h"] = -1
                    self.df.at[i, "label_4h_reason"] = "MISSING_EXACT_WINDOW"
                continue
            p0, p1, ret = evidence
            self.df.at[i, "ret_4h"] = ret
            self.df.at[i, "label_4h_start_price"] = p0
            self.df.at[i, "label_4h_end_price"] = p1
            self.df.at[i, "label_4h_graded_at_utc"] = now.isoformat()
            self.df.at[i, "graded_4h"] = 1
            self.df.at[i, "label_4h_reason"] = "EXACT_CONTIGUOUS_HOURLY_OPENS"
            n += 1
        # Existing 24h range calibration is a separate legacy metric; this
        # change deliberately does not alter it or the production model.
        for col, hrs in (("24h", 24),):
            todo = self.df[self.df[f"graded_{col}"].fillna(0) == 0]
            for i, row in todo.iterrows():
                t0 = pd.Timestamp(row["ts"])
                t0 = t0.tz_localize("UTC") if t0.tzinfo is None else t0
                t1 = t0 + pd.Timedelta(hours=hrs)
                if now < t1:
                    continue
                df = frames.get(row["asset"])
                if not isinstance(df, pd.DataFrame) or df.empty:
                    continue
                p1 = _price_at(df, t1)
                if p1 is None:
                    if now > t1 + pd.Timedelta(hours=96):
                        self.df.at[i, f"graded_{col}"] = -1        # veri yok: kalıcı olarak atla
                    continue
                self.df.at[i, f"ret_{col}"] = math.log(p1 / float(row["price"]))
                self.df.at[i, f"graded_{col}"] = 1
                n += 1
        return n

    def save(self) -> None:
        self.df.tail(MAX_ROWS).to_csv(self.path, index=False)

    # ------------------------------------------------------------------
    def scorecard(self, asset: str, logic: Optional[str] = LOGIC) -> Dict[str, Any]:
        """Karne SADECE verilen mantık sürümünün kayıtlarından hesaplanır (karışmasın)."""
        d = self.df[self.df["asset"] == asset].copy()
        if logic is not None:
            d = d[d["logic"].fillna("?") == logic]
        d["t"] = pd.to_datetime(d["ts"], utc=True)
        out: Dict[str, Any] = {"n_records": int(len(d)), "logic": logic}

        # 1) Aralık kapsama: günde bir bağımsız örnek (her günün ilk kaydı)
        g = d[d["graded_24h"] == 1].copy()
        g = g.sort_values("t").groupby(g["t"].dt.date).head(1)
        if len(g):
            z = (g["ret_24h"].abs() / g["sigma_pct"]).replace([np.inf, -np.inf], np.nan).dropna()
            cover = float((z <= 1.0).mean()) if len(z) else None
            k = float(np.clip(np.quantile(z, TARGET_COVER), 0.7, 1.5)) if len(z) >= MIN_DAYS else 1.0
            se = math.sqrt(TARGET_COVER * (1 - TARGET_COVER) / max(len(z), 1))
            out["range"] = {"n_days": int(len(z)), "coverage": round(cover, 3) if cover is not None else None,
                            "target": TARGET_COVER, "z": round((cover - TARGET_COVER) / se, 2) if cover is not None else None,
                            "multiplier": round(k, 3), "calibrated": len(z) >= MIN_DAYS}
            # 3) Sakin/hareketli: oran ↔ sonraki |getiri|/σ_normal (σ_normal ≈ sigma / ratio)
            c = g.dropna(subset=["calm_ratio"])
            if len(c) >= 10 and c["calm_ratio"].nunique() > 1:
                norm = c["sigma_pct"] / c["calm_ratio"].replace(0, np.nan)
                realized = (c["ret_24h"].abs() / norm).replace([np.inf, -np.inf], np.nan)
                ic = pd.Series(c["calm_ratio"].values).rank().corr(pd.Series(realized.values).rank())
                out["calm"] = {"n_days": int(len(c)), "ic": round(float(ic), 3) if ic == ic else None}
            # 4) Sonraki gün yükseliş olasılığı: Brier ve beceri skoru (iklim = 0.5)
            p = g.dropna(subset=["p_up_1d"])
            if len(p):
                y = (p["ret_24h"] > 0).astype(float)
                brier = float(((p["p_up_1d"] - y) ** 2).mean())
                out["p_up"] = {"n_days": int(len(p)), "brier": round(brier, 4),
                               "skill": round(1.0 - brier / 0.25, 4), "hit_up": round(float(y.mean()), 3)}

        # 2) Son 4 saat eğilimi: 4 saatte bir bağımsız örnek, sadece yön verilen kayıtlar
        out["lean4h_legacy_unverified"] = int(((d["graded_4h"] == 1) &
            ~d["label_4h_schema"].eq(STRICT_4H_SCHEMA)).sum())
        h = d[(d["graded_4h"] == 1) & d["label_4h_schema"].eq(STRICT_4H_SCHEMA) &
              d["label_4h_reason"].eq("EXACT_CONTIGUOUS_HOURLY_OPENS") &
              d["lean4h"].isin([-1,1]) & d["ret_4h"].notna() & d["ret_4h"].ne(0)].copy()
        h["label_start"] = pd.to_datetime(h["label_4h_start_utc"], utc=True, errors="coerce", format="mixed")
        h["label_end"] = pd.to_datetime(h["label_4h_end_utc"], utc=True, errors="coerce", format="mixed")
        h["observed"] = pd.to_datetime(h["observed_at_utc"], utc=True, errors="coerce", format="mixed")
        h = h[(h.label_start > h.observed) &
              (h.label_end == h.label_start + pd.Timedelta(hours=4))].sort_values("label_start")
        keep, last_end = [], None
        for i, r in h.iterrows():
            if last_end is None or r.label_start >= last_end:
                keep.append(i)
                last_end = r.label_end
        h = h.loc[keep]
        if len(h):
            hit = (np.sign(h["ret_4h"]) == np.sign(h["lean4h"])).astype(float)
            p_hat, n = float(hit.mean()), int(len(hit))
            zb = (p_hat - 0.5) / math.sqrt(0.25 / n)
            out["lean4h"] = {"n": n, "hit": round(p_hat, 3), "z": round(zb, 2),
                             "label_schema": STRICT_4H_SCHEMA,
                             "mean_bps": round(float((np.sign(h["lean4h"]) * h["ret_4h"]).mean()) * 1e4, 2),
                             "status": "kanıtlı" if (n >= MIN_LEAN and zb >= 2) else
                                       ("ters" if (n >= MIN_LEAN and zb <= -2) else "kanıtsız")}
        return out


def run_cycle(verdicts: Dict[str, Dict[str, Any]], frames: Dict[str, pd.DataFrame],
              path: str = LEDGER_FILE, now: Any = None, logic: str = LOGIC) -> Dict[str, Any]:
    led = ForecastLedger(path)
    led.grade(frames, now=now)
    cards: Dict[str, Any] = {}
    for a, v in verdicts.items():
        card = led.scorecard(a, logic=logic)
        cards[a] = card
        # Kalibrasyon: aralığı karnenin ölçtüğü çarpanla düzelt (yalnız ≥ 30 bağımsız gün sonra).
        dr = v.get("day_range")
        rng = card.get("range") or {}
        if dr and rng.get("calibrated"):
            dr["move_raw"] = dr["move"]
            dr["move"] = dr["move"] * float(rng["multiplier"])
            dr["calibration"] = rng["multiplier"]
        v["forecast_card"] = card
        led.record(a, v, now=now, logic=logic)
    led.save()
    return cards


def report_rows(cards: Dict[str, Any]) -> list:
    rows = []
    for a, c in (cards or {}).items():
        r, l, cm, p = c.get("range") or {}, c.get("lean4h") or {}, c.get("calm") or {}, c.get("p_up") or {}
        rows.append({
            "Varlık": a,
            "Aralık isabeti (hedef %68)": (f"%{100 * r['coverage']:.0f} · {r['n_days']} gün"
                                           + (f" · çarpan ×{r['multiplier']:.2f}" if r.get("calibrated") else " · veri birikiyor")
                                           ) if r.get("coverage") is not None else "veri birikiyor",
            "4 saat eğilim isabeti": (f"%{100 * l['hit']:.0f} · n={l['n']} · {l['status']}") if l else "veri birikiyor",
            "Sakin/hareketli doğruluğu": (f"IC {cm['ic']:+.2f} · {cm['n_days']} gün") if cm.get("ic") is not None else "veri birikiyor",
            "Yarın olasılığı (Brier beceri)": (f"{p['skill']:+.3f} · {p['n_days']} gün") if p else "veri birikiyor",
        })
    return rows


KARNE_GUIDE = """
**Tahmin Karnesi nasıl okunur?**
- Sistem her tahmini sonuç belli olmadan ÖNCE kaydeder. Süre dolunca gerçek fiyatla notlar. Kayıt sonradan değişmez.
- **Aralık isabeti:** Fiyat günlerin yaklaşık %68'inde verilen aralıkta kalmalıdır. Daha düşükse aralık dar, daha yüksekse geniştir. 30 günden sonra aralık bu sonuca göre otomatik düzeltilir.
- **4 saat eğilim isabeti:** Yalnızca tahminden sonraki ilk saat açılışından tam 4 saat sonraki açılışa kadar kesintisiz fiyat pencereleri. Eski doğrulanamayan 4s etiketleri ayrı tutulur. %50 referanstır; işlem kârı veya canlı emir kanıtı değildir.
- **Sakin/hareketli doğruluğu (IC):** Pozitif olmalıdır. "Hareketli" denen günler gerçekten büyük hareketli geçmelidir.
- **Yarın olasılığı (Brier beceri):** 0'ın üstü, "%50 yazı-tura" tahmininden iyi demektir.
"""
