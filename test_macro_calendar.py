from datetime import datetime, timezone

import numpy as np
import pandas as pd

import macro_calendar as MC


def _cal():
    days = pd.bdate_range("2025-01-01", "2026-10-30")
    ev = days[::8]
    return pd.DataFrame({"date": [d.strftime("%Y-%m-%d") for d in ev], "event": "TÜFE (CPI)", "time_et": "08:30"})


def test_measure_detects_event_volatility():
    cal = _cal()
    idx = pd.bdate_range("2025-01-01", "2026-10-22")
    rng = np.random.default_rng(3)
    r = rng.normal(0, 0.01, len(idx))
    r[idx.isin(MC.event_days(cal))] *= 2.0
    daily = pd.DataFrame({"Close": 100 * np.exp(np.cumsum(r))}, index=idx)
    m = MC.measure(daily, cal)
    assert m["proven"] and m["ratio"] > 1.5 and 1.0 < m["factor"] <= 2.5
    flat = pd.DataFrame({"Close": 100 * np.exp(np.cumsum(rng.normal(0, 0.01, len(idx))))}, index=idx)
    assert not MC.measure(flat, cal)["proven"]


def test_upcoming_today_and_note():
    cal = pd.DataFrame({"date": ["2026-11-10"], "event": ["TÜFE (CPI)"], "time_et": ["08:30"]})
    now = datetime(2026, 11, 10, 11, 0, tzinfo=timezone.utc)          # 06:00 ET
    up = MC.upcoming(cal, now)
    assert up[0]["today"] and not up[0]["passed"] and up[0]["tsi"] == "10.11 16:30"
    mc = {"today": up, "effects": {"SPX": {"proven": True, "ratio": 1.6}}}
    assert "TÜFE (CPI) 16:30 TSİ" in MC.note("SPX", mc) and "×1.6" in MC.note("SPX", mc)
    assert MC.note("SPX", {"today": []}) == ""


def test_fallback_without_key(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cal = MC.load(api_key="")
    assert (cal["event"] == "FOMC kararı").all() and cal.attrs["problems"]


def test_daily_fomc_series_rejected():
    rows = [{"date": d.strftime("%Y-%m-%d"), "event": "X", "time_et": "08:30"} for d in pd.bdate_range("2025-01-01", "2025-12-31")]
    df = pd.DataFrame(rows)
    yr = pd.to_datetime(df["date"]).dt.year
    assert df.groupby([df["event"], yr]).size().max() > MC.MAX_PER_YEAR
    cal = MC.load(api_key="")
    assert (cal["event"] == "FOMC kararı").sum() == len(MC.FOMC_DATES)
