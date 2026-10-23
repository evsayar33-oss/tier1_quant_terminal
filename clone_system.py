"""
Klon Gölge Sistem (klon-1) — sistemin TAM kopyası, yeni fikirler dahil
=====================================================================
Ekrandaki sistem (şampiyon) değişmez. Her döngüde aynı veriyle sistemin tam bir
kopyası çalışır; yeni fikirler bu kopyanın içine gerçekten entegre edilmiştir:
  * Kısa vade yönü: şampiyon "yön yok" derken SPX/NQ'da ET 11-15 arasında güçlü
    charm akışı varsa charm yönü (H13).
  * Stoplar: dayanak adaylarına önceki seansın POC / VAH / VAL seviyeleri (H15);
    gama duvarları zaten şampiyonda var (H14 ayrıca gölge defterde).
Kopya, şampiyonla AYNI modüllerden geçer (stop, aralık, tahmin karnesi, karar
defteri) ve kendi dosyalarına yazar: clone/stop_ledger.csv,
clone/forecast_ledger.csv, clone/decision_log.csv. Mantık etiketi:
"<LOGIC_VERSION>+klon1". 30 gün sonra iki sistem AYNI ölçüm koduyla notlanır.
"""
from __future__ import annotations

import copy
import os
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import pandas as pd

from system_clock import now_utc

ROOT = "clone"
ET = ZoneInfo("America/New_York")
CHARM_MIN_USD = 1e9


def logic_tag() -> str:
    try:
        from config import LOGIC_VERSION
    except Exception:
        LOGIC_VERSION = "?"
    return f"{LOGIC_VERSION}+klon1"


def build(verdicts: Dict[str, Dict[str, Any]], contexts: Dict[str, Dict[str, Any]], snaps: Dict[str, Any],
          intraday: Dict[str, Any], now: pd.Timestamp):
    import shadow_ledger as SHL
    import stop_levels as SL
    cv, cc = copy.deepcopy(verdicts), copy.deepcopy(contexts)
    et_hour = int(now.tz_convert(ET).hour)
    for a, v in cv.items():
        ctx = cc.setdefault(a, {})
        vp = SHL.volume_profile(intraday.get(a), now) if isinstance(intraday.get(a), pd.DataFrame) else None
        if vp and isinstance(ctx.get("levels"), dict):
            ctx["levels"]["levels"] = list(ctx["levels"].get("levels") or []) + [
                {"price": vp["val"], "kind": "SWL", "label": "Değer alanı dibi (VAL)"},
                {"price": vp["vah"], "kind": "SWH", "label": "Değer alanı tepesi (VAH)"},
                {"price": vp["poc"], "kind": "VWAP", "label": "POC"}]
        v.pop("clone_short_side", None)
        base = SL.evidence_short_side(v)
        charm = ((snaps or {}).get(a) or {}).get("charm_flow_1d_usd")
        if base == 0 and a in ("SPX", "NQ") and 11 <= et_hour < 15 and charm and abs(float(charm)) >= CHARM_MIN_USD:
            v["clone_short_side"] = 1 if float(charm) > 0 else -1
            v["clone_note"] = f"charm akışı {float(charm) / 1e9:+.1f} mlr $"
    return cv, cc


def run(verdicts: Dict[str, Dict[str, Any]], contexts: Dict[str, Dict[str, Any]], snaps: Dict[str, Any],
        frames: Dict[str, Any], intraday: Dict[str, Any], order: List[str], gex: Optional[Dict[str, Any]] = None,
        root: str = ROOT, now: Any = None) -> Dict[str, Any]:
    import decision_log as DL
    import forecast_ledger as FL
    import stop_levels as SL
    now = pd.Timestamp(now or now_utc())
    now = now.tz_localize("UTC") if now.tzinfo is None else now.tz_convert("UTC")
    os.makedirs(root, exist_ok=True)
    tag = logic_tag()
    cv, cc = build(verdicts, contexts, snaps, intraday, now)
    SL.run_cycle(cv, cc, snaps, frames, path=os.path.join(root, "stop_ledger.csv"), now=now)
    import day_direction as DD
    import trade_plan as TP
    DD.run_cycle(cv, frames, snaps, path=os.path.join(root, "day_direction_ledger.csv"), now=now, logic=tag, contexts=cc)
    trade = TP.run_cycle(cv, cc, snaps, frames, path=os.path.join(root, "trade_ledger.csv"), now=now, logic=tag)
    for a, v in cv.items():
        if a in cc:
            v["market_structure"] = cc[a]
    cards = FL.run_cycle(cv, frames, path=os.path.join(root, "forecast_ledger.csv"), now=now, logic=tag)
    DL.record(cv, order, gex, path=os.path.join(root, "decision_log.csv"), now=now, logic=tag)
    diff = [a for a in order if (cv.get(a) or {}).get("clone_short_side") is not None]
    return {"logic": tag, "cards": cards, "charm_override": diff, "trade": trade,
            "rows": {a: {"short": SL.evidence_short_side(cv[a]),
                         "stop_kisa": ((cv[a].get("stop_suggestion") or {}).get("kisa") or {}).get("stop")}
                     for a in order if a in cv}}
