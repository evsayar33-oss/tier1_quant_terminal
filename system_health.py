"""
Sistem Sağlığı (v16.3) — sistem kendi hatasını bulur ve kalıcı olarak kaydeder
==============================================================================
Her motor döngüsünün sonunda çalışır. Sabit kontroller yapar ve sonucu iki
dosyaya yazar (ikisi de `state` dalında kalıcıdır):

* health_log.csv    — OLAY GÜNLÜĞÜ. Bir kontrol bozulduğunda "BAŞLADI",
                      düzeldiğinde "DÜZELDİ" satırı eklenir. Sorun sürdükçe her
                      saat yeni satır yazılmaz (gürültü olmaz). Böylece her
                      sohbet ve her otomatik kontrol "ne zaman ne bozuldu, ne
                      zaman düzeldi" sorusunu bu dosyadan okur.
* health_report.md  — şu anki durum: açık sorunlar ve son olaylar.

Kontroller (sabit, açıklanabilir):
* futures_live      : ES/NQ/GC/SI vadelileri seans açıkken LIVE mı
* crypto_live       : BTC/ETH LIVE mı (7/24)
* gamma_map         : NQ/SPX/BTC/ETH gama haritası dolu mu
* gex_history       : SPX GEX serisi en fazla 5 gün eski mi
* factor_coverage   : her varlıkta faktör kapsamı ≥ %70 mı
* cycle_errors      : döngüde bir modül hata verdi mi (dealer_gamma, stop, ...)
"""
from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

LOG_FILE = "health_log.csv"
REPORT_FILE = "health_report.md"
FUTURES = ("ES=F", "NQ=F", "GC=F", "SI=F")
CRYPTO = ("BTC-USD", "ETH-USD")
GAMMA_ASSETS = ("NQ", "SPX", "BTC", "ETH")
COLS = ["ts", "check", "event", "detail"]


def _futures_session_open(now: datetime) -> bool:
    """CME: Pazar 22:00 UTC → Cuma 21:00 UTC; her gün 21:00-22:00 UTC bakım (yaklaşık, yaz/kış ±1s)."""
    wd, h = now.weekday(), now.hour
    if wd == 5 or (wd == 6 and h < 23) or (wd == 4 and h >= 21):
        return False
    return h != 21


def run_checks(state: Dict[str, Any], now: Optional[datetime] = None) -> Dict[str, Dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    dq = state.get("data_quality") or {}
    out: Dict[str, Dict[str, Any]] = {}

    def res(name, ok, detail):
        out[name] = {"ok": bool(ok), "detail": detail}

    if _futures_session_open(now):
        bad = [s for s in FUTURES if (dq.get(s) or {}).get("status") != "LIVE"]
        res("futures_live", not bad, "LIVE değil: " + ", ".join(bad) if bad else "vadeliler LIVE")
    else:
        res("futures_live", True, "vadeli seansı kapalı (kontrol atlandı)")
    bad = [s for s in CRYPTO if (dq.get(s) or {}).get("status") != "LIVE"]
    res("crypto_live", not bad, "LIVE değil: " + ", ".join(bad) if bad else "kripto LIVE")

    dg = state.get("dealer_gamma") or {}
    snaps = dg.get("snapshots") or {}
    miss = [a for a in GAMMA_ASSETS if a not in snaps]
    res("gamma_map", not miss and "error" not in dg,
        (f"hata: {dg['error']}" if "error" in dg else "eksik: " + ", ".join(miss)) if (miss or "error" in dg)
        else "4 varlık dolu")

    gh = state.get("gex_history") or {}
    if not gh:
        res("gex_history", False, "GEX serisi yüklenemedi")
    else:
        res("gex_history", not gh.get("stale"), f"son tarih {gh.get('date')}" + (" (ESKİ)" if gh.get("stale") else ""))

    low = []
    for a, h in (state.get("data_health") or {}).items():
        cov = h.get("coverage")
        if cov is not None and cov < 0.70:
            low.append(f"{a} %{100 * cov:.0f}")
    res("factor_coverage", not low, "düşük kapsam: " + ", ".join(low) if low else "tüm varlıklar ≥ %70")

    errs = [f"{k}: {v.get('error')}" for k, v in (
        ("dealer_gamma", state.get("dealer_gamma") or {}),
        ("stop_calibration", state.get("stop_calibration") or {}),
        ("performance", state.get("performance") or {}),
        ("forecast_scorecard", state.get("forecast_scorecard") or {}),
        ("macro_calendar", state.get("macro_calendar") or {}),
        ("shock", state.get("shock") or {}),
        ("shock_direction", state.get("shock_direction") or {}),
        ("shadow_ledger", state.get("shadow_ledger") or {}),
        ("clone_system", state.get("clone_system") or {}),
        ("trade_scorecard", state.get("trade_scorecard") or {}),
    ) if isinstance(v, dict) and v.get("error")]
    res("cycle_errors", not errs, "; ".join(errs)[:300] if errs else "modül hatası yok")
    return out


def _open_problems(path: str) -> set:
    """Günlükteki her kontrolün son olayına bakar: son olay BAŞLADI ise sorun açık."""
    last: Dict[str, str] = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                last[row["check"]] = row["event"]
    return {k for k, v in last.items() if v == "BAŞLADI"}


def record(results: Dict[str, Dict[str, Any]], path: str = LOG_FILE, now: Optional[datetime] = None) -> List[Dict[str, str]]:
    now = now or datetime.now(timezone.utc)
    open_now = _open_problems(path)
    events = []
    for name, r in results.items():
        if not r["ok"] and name not in open_now:
            events.append({"ts": now.isoformat(timespec="minutes"), "check": name, "event": "BAŞLADI", "detail": r["detail"]})
        elif r["ok"] and name in open_now:
            events.append({"ts": now.isoformat(timespec="minutes"), "check": name, "event": "DÜZELDİ", "detail": r["detail"]})
    if events:
        new = not os.path.exists(path)
        with open(path, "a", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLS)
            if new:
                w.writeheader()
            w.writerows(events)
    return events


def write_report(results: Dict[str, Dict[str, Any]], path: str = REPORT_FILE, log: str = LOG_FILE,
                 now: Optional[datetime] = None) -> None:
    now = now or datetime.now(timezone.utc)
    bad = {k: v for k, v in results.items() if not v["ok"]}
    lines = [f"# 🩺 Sistem Sağlığı — {now:%Y-%m-%d %H:%M} UTC", "",
             ("✅ Bütün kontroller geçti." if not bad else f"⚠️ {len(bad)} açık sorun:"), ""]
    for k, v in results.items():
        lines.append(f"- {'✅' if v['ok'] else '❌'} **{k}** — {v['detail']}")
    rows = []
    if os.path.exists(log):
        with open(log, encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))[-15:]
    lines += ["", "## Son olaylar (health_log.csv)", ""]
    lines += [f"- {r['ts']} · {r['check']} · {r['event']} · {r['detail']}" for r in reversed(rows)] or ["- Kayıt yok"]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def run(state: Dict[str, Any], now: Optional[datetime] = None) -> Dict[str, Any]:
    results = run_checks(state, now)
    events = record(results, now=now)
    write_report(results, now=now)
    return {"ok": all(r["ok"] for r in results.values()), "checks": results, "new_events": events}
