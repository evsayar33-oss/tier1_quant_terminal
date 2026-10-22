"""
Tarihsel Dealer Gaması (v16.2) — SqueezeMetrics günlük SPX GEX/DIX serisi
=========================================================================
Kanıt (2011-05 → 2026-10, 3.892 gün, RESEARCH_LOG #7):
* GEX yüksekken ertesi günün hareketi KÜÇÜKTÜR. |getiri|/vol, GEX
  beşte birlik dilimine göre: 1.03 / 0.88 / 0.81 / 0.71 / 0.66.
  Sıra korelasyonu −0.18; 3 dönemin 3'ünde aynı işaret (−0.20/−0.18/−0.15).
* GEX ve DIX YÖN bilgisi taşımaz: 18 kuralın hiçbiri Hep AL'ı geçmedi (#8).

Kullanım: sadece BÜYÜKLÜK. Bugünkü GEX yüzdeliği → hareket çarpanı
(o dilimin tarihsel ortalaması / genel ortalama). Stop mesafeleri ve
beklenen hareket bu çarpanla ölçeklenir. Çarpan tablosu her çalışmada
TÜM geçmişten yeniden ölçülür (kendini kalibre eder).
"""
from __future__ import annotations

import io
import math
import os
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

URL = "https://squeezemetrics.com/monitor/static/DIX.csv"
CACHE = "gex_history.csv"
APPLIES_TO = ("SPX", "NQ")          # NQ ile SPX dealer gaması yüksek korelasyonlu (aynı endeks opsiyon kompleksi)
MAX_AGE_DAYS = 5


def fetch(timeout: float = 30.0) -> Optional[pd.DataFrame]:
    try:
        import requests
        r = requests.get(URL, timeout=timeout, headers={"User-Agent": "Mozilla/5.0 tier1-quant-terminal"})
        if r.status_code != 200 or "date" not in r.text[:50]:
            return None
        return parse(r.text)
    except Exception:
        return None


def parse(text: str) -> Optional[pd.DataFrame]:
    try:
        d = pd.read_csv(io.StringIO(text), parse_dates=["date"])
        d = d.dropna(subset=["date", "price", "gex"]).sort_values("date").set_index("date")
        return d if len(d) > 300 else None
    except Exception:
        return None


def load(cache: str = CACHE) -> Optional[pd.DataFrame]:
    d = fetch()
    if d is not None:
        try:
            d.reset_index().to_csv(cache, index=False)
        except Exception:
            pass
        return d
    if os.path.exists(cache):
        try:
            return parse(open(cache, encoding="utf-8").read())
        except Exception:
            return None
    return None


def analyze(d: pd.DataFrame, now: Any = None) -> Optional[Dict[str, Any]]:
    if d is None or len(d) < 400:
        return None
    lr = np.log(d["price"])
    vol20 = lr.diff().rolling(20).std()
    g = d["gex"]
    gp = g.rolling(252, min_periods=120).apply(lambda v: (v <= v[-1]).mean(), raw=True)
    mag = ((lr.shift(-1) - lr).abs() / vol20)
    m = pd.DataFrame({"gp": gp, "mag": mag}).dropna()
    if len(m) < 300:
        return None
    q = np.minimum((m["gp"] * 5).astype(int), 4)
    overall = float(m["mag"].mean())
    table = [round(float(m["mag"][q == k].mean()) / overall, 3) for k in range(5)]
    ic = float(m["gp"].rank().corr(m["mag"].rank()))
    k = len(m) // 3
    thirds = [round(float(x["gp"].rank().corr(x["mag"].rank())), 3) for x in (m.iloc[:k], m.iloc[k:2 * k], m.iloc[2 * k:])]
    last = gp.dropna()
    if last.empty:
        return None
    today_p = float(last.iloc[-1])
    today_q = min(int(today_p * 5), 4)
    last_date = last.index[-1]
    now = pd.Timestamp(now) if now is not None else pd.Timestamp.now(tz="UTC")
    now = now.tz_convert(None) if now.tzinfo else now
    stale = (now.normalize() - pd.Timestamp(last_date).normalize()).days > MAX_AGE_DAYS
    proven = bool(all(t < 0 for t in thirds) and abs(ic) * math.sqrt(len(m)) >= 3.0)
    factor = table[today_q] if (proven and not stale) else 1.0
    return {"date": str(pd.Timestamp(last_date).date()), "gex": float(g.iloc[-1]), "dix": float(d["dix"].iloc[-1]) if "dix" in d else None,
            "gex_percentile": round(today_p, 3), "quintile": today_q + 1, "move_factor": round(float(factor), 3),
            "quintile_table": table, "ic": round(ic, 3), "ic_thirds": thirds, "n": int(len(m)),
            "proven": proven, "stale": stale,
            "note": (f"GEX 1 yıllık yüzdelik %{100 * today_p:.0f} (dilim {today_q + 1}/5): ertesi gün hareketi "
                     f"normalin ×{factor:.2f}'i beklenir" + (" (veri eski, çarpan 1.0)" if stale else ""))}


def run(cache: str = CACHE, now: Any = None) -> Optional[Dict[str, Any]]:
    return analyze(load(cache), now=now)
