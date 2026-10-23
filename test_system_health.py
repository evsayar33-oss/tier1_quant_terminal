"""v16.3 — the system logs a problem once when it starts and once when it is fixed."""
import os
from datetime import datetime, timezone

import system_health as SH

OPEN = datetime(2026, 10, 21, 14, 0, tzinfo=timezone.utc)      # Wednesday, futures open


def _state(**kw):
    s = {"data_quality": {k: {"status": "LIVE"} for k in SH.FUTURES + SH.CRYPTO},
         "dealer_gamma": {"snapshots": {a: {} for a in SH.GAMMA_ASSETS}},
         "gex_history": {"date": "2026-10-20", "stale": False},
         "data_health": {"NQ": {"coverage": 0.9}}}
    s.update(kw)
    return s


def test_healthy_state_passes_and_logs_nothing(tmp_path):
    os.chdir(tmp_path)
    r = SH.run(_state(), now=OPEN)
    assert r["ok"] and r["new_events"] == [] and not os.path.exists(SH.LOG_FILE)
    assert "Bütün kontroller geçti" in open(SH.REPORT_FILE, encoding="utf-8").read()


def test_problem_logged_once_then_fixed(tmp_path):
    os.chdir(tmp_path)
    bad = _state(dealer_gamma={"snapshots": {"NQ": {}}})
    e1 = SH.run(bad, now=OPEN)["new_events"]
    e2 = SH.run(bad, now=OPEN)["new_events"]                 # still broken -> no new row
    e3 = SH.run(_state(), now=OPEN)["new_events"]            # fixed
    assert [e["event"] for e in e1] == ["BAŞLADI"] and e2 == [] and [e["event"] for e in e3] == ["DÜZELDİ"]
    rows = open(SH.LOG_FILE, encoding="utf-8").read().strip().splitlines()
    assert len(rows) == 3 and "gamma_map" in rows[1]


def test_futures_check_skipped_on_weekend(tmp_path):
    os.chdir(tmp_path)
    weekend = datetime(2026, 10, 24, 12, 0, tzinfo=timezone.utc)
    st = _state(data_quality={k: {"status": "STALE"} for k in SH.FUTURES} | {k: {"status": "LIVE"} for k in SH.CRYPTO})
    assert SH.run_checks(st, weekend)["futures_live"]["ok"]
    assert not SH.run_checks(st, OPEN)["futures_live"]["ok"]


def test_module_errors_and_stale_gex_are_problems(tmp_path):
    os.chdir(tmp_path)
    r = SH.run_checks(_state(stop_calibration={"error": "boom"}, gex_history={"date": "x", "stale": True}), OPEN)
    assert not r["cycle_errors"]["ok"] and "boom" in r["cycle_errors"]["detail"]
    assert not r["gex_history"]["ok"]
