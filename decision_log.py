"""
Karar Defteri (v16.8) — arayüzün her saat gösterdiği HER ŞEY, mantık sürümüyle
=============================================================================
Amaç: ileride "sistem o gün ne dedi, hangi mantıkla dedi, sonra ne oldu?"
sorusunu cevaplamak. Basit Özet ve detaylı Karar Özeti'nin metni, fiyat ve
mantık sürümü (config.LOGIC_VERSION) saatte bir kez yazılır. Kayıt sonradan
değişmez. Notlama tahmin karnesi (forecast_ledger) ve stop defterinde yapılır;
bu defter onların "o anki ekran görüntüsüdür".
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import pandas as pd

from system_clock import now_utc

LOG_FILE = "decision_log.csv"
MAX_ROWS = 60000


def record(verdicts: Dict[str, Dict[str, Any]], order: List[str], gex: Optional[Dict[str, Any]] = None,
           path: str = LOG_FILE, now: Any = None, logic: Optional[str] = None) -> int:
    import decision_panel as DP
    try:
        from config import LOGIC_VERSION
    except Exception:
        LOGIC_VERSION = "?"
    if logic:
        LOGIC_VERSION = logic
    ts = pd.Timestamp(now or now_utc()).floor("h").isoformat()
    old = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()
    if not old.empty and (old["ts"] == ts).any():
        return 0
    simple = {r["Varlık"]: r for r in DP.simple_rows(verdicts, order, gex)}
    detail = {r["Varlık"]: r for r in DP.build_rows(verdicts, order)}
    rows = []
    for a in order:
        v = verdicts.get(a) or {}
        price = ((v.get("market_structure") or {}).get("levels") or {}).get("price")
        row = {"ts": ts, "logic": LOGIC_VERSION, "asset": a, "price": price}
        row.update({f"basit · {k}": x for k, x in simple.get(a, {}).items() if k != "Varlık"})
        row.update({f"detay · {k}": x for k, x in detail.get(a, {}).items() if k != "Varlık"})
        rows.append(row)
    out = pd.concat([old, pd.DataFrame(rows)], ignore_index=True).tail(MAX_ROWS)
    out.to_csv(path, index=False)
    return len(rows)
