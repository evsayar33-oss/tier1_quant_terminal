"""
Makro Veri Takvimi (v16.5) — ABD veri günleri ve oynaklık etkisi
================================================================
Kaynak: FRED "release dates" (geçmiş ve İLAN EDİLMİŞ gelecek tarihler).
Olaylar: TÜFE (CPI), Tarım Dışı İstihdam (NFP), ÜFE (PPI), GSYH, PCE,
Perakende Satışlar, FOMC kararı.

Kendini ölçer: her döngüde, varlığın günlük verisinde olay günlerinin
hareket büyüklüğü (|getiri| / önceki 20 günün σ'sı) normal günlerle
karşılaştırılır. Etki SADECE kanıtlıysa (t ≥ 3, n ≥ 20) olay günü için
hareket çarpanı uygulanır (sınır 1.0–2.5). Kanıt yoksa takvim yalnız
bilgi olarak gösterilir.

Kendini denetler: FRED'deki yayın adı beklenenle uyuşmazsa veya gelecek
FOMC tarihi kalmazsa sağlık kontrolü bunu bir sorun olarak kaydeder.
"""
from __future__ import annotations

import math
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ET = ZoneInfo("America/New_York")
TR = ZoneInfo("Europe/Istanbul")
CACHE = "macro_calendar.csv"
# ad: (FRED release_id, adda aranacak metin, ET saati)
EVENTS = {
    "TÜFE (CPI)": (10, "consumer price index", "08:30"),
    "İstihdam (NFP)": (50, "employment situation", "08:30"),
    "ÜFE (PPI)": (46, "producer price index", "08:30"),
    "GSYH": (53, "gross domestic product", "08:30"),
    "PCE": (54, "personal income", "08:30"),
    "Perakende Satışlar": (9, "retail", "08:30"),
    "FOMC kararı": (101, "fomc", "14:00"),
}
# FRED erişilemezse son çare: Fed'in ilan ettiği 2026 FOMC karar günleri.
FOMC_FALLBACK = ["2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17",
                 "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09"]
T_REQ, MIN_N = 3.0, 20


def fetch(api_key: str, timeout: float = 20.0) -> Optional[pd.DataFrame]:
    import requests
    rows, problems = [], []
    base = "https://api.stlouisfed.org/fred"
    for name, (rid, must, hhmm) in EVENTS.items():
        try:
            meta = requests.get(f"{base}/release", params={"release_id": rid, "api_key": api_key, "file_type": "json"},
                                timeout=timeout).json()
            rname = ((meta.get("releases") or [{}])[0].get("name") or "")
            if must not in rname.lower():
                problems.append(f"{name}: FRED adı beklenmedik ({rname!r})")
                continue
            js = requests.get(f"{base}/release/dates", params={
                "release_id": rid, "api_key": api_key, "file_type": "json", "realtime_start": "2015-01-01",
                "realtime_end": "9999-12-31", "include_release_dates_with_no_data": "true", "limit": 10000},
                timeout=timeout).json()
            for d in js.get("release_dates") or []:
                rows.append({"date": d["date"], "event": name, "time_et": hhmm})
        except Exception as exc:
            problems.append(f"{name}: {exc}")
    if not rows:
        return None
    df = pd.DataFrame(rows).drop_duplicates()
    df.attrs["problems"] = problems
    return df


def load(api_key: Optional[str] = None, cache: str = CACHE) -> pd.DataFrame:
    key = api_key if api_key is not None else os.environ.get("FRED_API_KEY", "").strip()
    df, problems = None, []
    if key:
        df = fetch(key)
        if df is not None:
            problems = df.attrs.get("problems", [])
            try:
                df.to_csv(cache, index=False)
            except Exception:
                pass
    if df is None and os.path.exists(cache):
        try:
            df = pd.read_csv(cache)
        except Exception:
            df = None
    if df is None:
        problems.append("FRED takvimi alınamadı; sadece FOMC yedek listesi")
        df = pd.DataFrame({"date": FOMC_FALLBACK, "event": "FOMC kararı", "time_et": "14:00"})
    df.attrs["problems"] = problems
    return df


def event_days(cal: pd.DataFrame) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(pd.to_datetime(cal["date"]).dt.normalize().unique())


def measure(daily: Any, cal: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """Olay günü hareket büyüklüğü / normal gün. Ölçek: önceki 20 günün medyan-tabanlı σ'sı."""
    try:
        c = pd.to_numeric(daily["Close"], errors="coerce").dropna()
        c.index = pd.to_datetime(c.index, utc=True).tz_convert(None).normalize()
        c = c[~c.index.duplicated(keep="last")]
        r = np.log(c / c.shift(1))
        sig = r.abs().rolling(20, min_periods=15).median().shift(1) / 0.6745
        m = (r.abs() / sig).dropna()
        if len(m) < 120:
            return None
        ev = m.index.isin(event_days(cal))
        a, b = m[ev], m[~ev]
        if len(a) < 5:
            return None
        t = (a.mean() - b.mean()) / math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
        ratio = float(a.mean() / b.mean())
        proven = bool(t >= T_REQ and len(a) >= MIN_N)
        return {"ratio": round(ratio, 3), "t": round(float(t), 2), "n_event": int(len(a)), "n_normal": int(len(b)),
                "proven": proven, "factor": round(float(np.clip(ratio, 1.0, 2.5)), 3) if proven else 1.0}
    except Exception:
        return None


def upcoming(cal: pd.DataFrame, now: Optional[datetime] = None, days: int = 7) -> List[Dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    out = []
    for _, row in cal.iterrows():
        d = pd.Timestamp(row["date"]).date()
        hh, mm = map(int, str(row.get("time_et") or "08:30").split(":"))
        t = datetime(d.year, d.month, d.day, hh, mm, tzinfo=ET)
        if now - timedelta(hours=6) <= t <= now + timedelta(days=days):
            out.append({"event": row["event"], "et": t.isoformat(), "tsi": t.astimezone(TR).strftime("%d.%m %H:%M"),
                        "today": t.astimezone(ET).date() == now.astimezone(ET).date(), "passed": t <= now})
    return sorted(out, key=lambda x: x["et"])


def run(daily: Dict[str, Any], now: Optional[datetime] = None, api_key: Optional[str] = None) -> Dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    cal = load(api_key)
    problems = list(cal.attrs.get("problems", []))
    fomc_future = [d for d in cal[cal["event"] == "FOMC kararı"]["date"] if pd.Timestamp(d).date() >= now.date()]
    if not fomc_future:
        problems.append("Gelecek FOMC tarihi yok (takvim güncellenmeli)")
    effects = {a: measure(df, cal) for a, df in (daily or {}).items()}
    up = upcoming(cal, now)
    today = [e for e in up if e["today"]]
    return {"upcoming": up, "today": today, "effects": effects, "problems": problems,
            "n_dates": int(len(cal)), "error": "; ".join(problems) if problems else None}


def note(asset: str, mc: Dict[str, Any]) -> str:
    """Basit Özet için kısa uyarı: bugün olay varsa saat ve ölçülen etki."""
    today = (mc or {}).get("today") or []
    if not today:
        return ""
    eff = ((mc or {}).get("effects") or {}).get(asset) or {}
    names = ", ".join(f"{e['event']} {e['tsi'][-5:]} TSİ" + (" (açıklandı)" if e["passed"] else "") for e in today)
    tag = f" · bu günlerde hareket ×{eff['ratio']:.1f} (kanıtlı)" if eff.get("proven") else ""
    return f" · ⚠️ Bugün veri: {names}{tag}"
