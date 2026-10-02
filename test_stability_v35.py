"""v3.5 stability tests: single writer, closed bars, smoothing, label hysteresis."""
import json
import os
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd


def test_read_only_mode_never_writes_state(tmp_path):
    from stateful_memory_store import StatefulMemoryStore
    import state_schema
    p = tmp_path / "m.json"
    os.environ["TIER1_READ_ONLY_STATE"] = "1"
    try:
        s = StatefulMemoryStore(path=p)
        s.memory["x"] = 1
        s.save()
        state_schema.atomic_write_json(str(tmp_path / "s.json"), {"a": 1})
        assert not p.exists() and not (tmp_path / "s.json").exists()
    finally:
        os.environ.pop("TIER1_READ_ONLY_STATE", None)
    s.save()
    assert p.exists()


def test_forming_hourly_bar_is_dropped(tmp_path):
    import data_engine
    from system_clock import set_frozen_now, clear_frozen_now
    idx = pd.date_range("2026-10-01 00:00", periods=9, freq="h", tz="UTC")       # last bar = 08:00
    df = pd.DataFrame({"Open": 1.0, "High": 2.0, "Low": 0.5, "Close": np.arange(1.0, 10.0), "Volume": 1.0}, index=idx)

    class _YF:
        @staticmethod
        def download(*a, **k):
            return df.copy()

    old_yf, old_dir = data_engine.yf, os.environ.get("OHLCV_HISTORY_DIR")
    data_engine.yf = _YF
    os.environ["OHLCV_HISTORY_DIR"] = str(tmp_path)
    set_frozen_now(pd.Timestamp("2026-10-01 08:20", tz="UTC"))
    try:
        eng = data_engine.ResilientDataEngine(fred_api_key="")
        _, out = eng.fetch_single_ticker_1h("TEST")
        assert pd.Timestamp(out.index[-1]) == pd.Timestamp("2026-10-01 07:00", tz="UTC")   # 08:00 still forming
        assert out.attrs["forming_bar_close"] == 9.0
        assert out.attrs["status"] == "LIVE"
    finally:
        clear_frozen_now()
        data_engine.yf = old_yf
        if old_dir is None:
            os.environ.pop("OHLCV_HISTORY_DIR", None)
        else:
            os.environ["OHLCV_HISTORY_DIR"] = old_dir


def test_live_label_has_fixed_meaning_and_hysteresis(tmp_path):
    from stateful_memory_store import StatefulMemoryStore
    from stateful_live_direction_engine import StatefulLiveDirectionEngine
    eng = StatefulLiveDirectionEngine(StatefulMemoryStore(path=tmp_path / "m.json"))
    t0 = datetime(2026, 10, 1, 8, tzinfo=timezone.utc)
    lab = "GÜÇLÜ TREND · NORMAL VOLATİLİTE"
    r = eng.evaluate("NQ", lab, -2.08, -0.3, -0.4, now=t0)
    assert r["live_tier"] == "GÜÇLÜ"                       # a -2.08 move is never "HAFİF"
    a50 = r["live_thresholds"]["p50"]
    r1 = eng.evaluate("SPX", lab, a50 * 1.15, 0.1, 0.1, now=t0)
    r2 = eng.evaluate("SPX", lab, a50 * 0.97, 0.1, 0.1, now=t0 + timedelta(hours=1))
    assert r1["live_tier"] == "HAFİF" and r2["live_tier"] == "HAFİF"   # tiny dip below boundary: no flip
    r3 = eng.evaluate("SPX", lab, a50 * 0.5, 0.1, 0.1, now=t0 + timedelta(hours=2))
    assert r3["live_tier"] == "YATAY"


def test_direction_clock_is_the_closed_bar_clock(tmp_path):
    from stateful_memory_store import StatefulMemoryStore
    from stateful_direction_engine import StatefulDirectionEngine
    th = {"buy_enter": 0.8, "buy_early": 0.55, "buy_exit": 0.3, "sell_enter": -0.8, "sell_early": -0.55,
          "sell_exit": -0.3, "strong_buy_enter": 1.7, "strong_sell_enter": -1.7, "min_clusters": 2}
    outs = []
    for minute in (20, 41):
        e = StatefulDirectionEngine(StatefulMemoryStore(path=tmp_path / f"m{minute}.json"))
        e.evaluate("SPX", 3, -0.4, 0, 3, th, now=datetime(2026, 10, 1, 7, 10, tzinfo=timezone.utc))
        outs.append(e.evaluate("SPX", 3, -0.9, 0, 3, th, now=datetime(2026, 10, 1, 8, minute, tzinfo=timezone.utc)))
    assert outs[0]["velocity"] == outs[1]["velocity"]


def test_offgrid_crypto_row_and_forming_bar_both_dropped(tmp_path):
    import data_engine
    from system_clock import set_frozen_now, clear_frozen_now
    idx = list(pd.date_range("2026-10-01 00:00", periods=9, freq="h", tz="UTC")) + [pd.Timestamp("2026-10-01 08:49", tz="UTC")]
    df = pd.DataFrame({"Open": 1.0, "High": 2.0, "Low": 0.5, "Close": np.arange(1.0, 11.0), "Volume": 1.0},
                      index=pd.DatetimeIndex(idx))

    class _YF:
        @staticmethod
        def download(*a, **k):
            return df.copy()

    old_yf, old_dir = data_engine.yf, os.environ.get("OHLCV_HISTORY_DIR")
    data_engine.yf = _YF
    os.environ["OHLCV_HISTORY_DIR"] = str(tmp_path)
    set_frozen_now(pd.Timestamp("2026-10-01 08:50", tz="UTC"))
    try:
        _, out = data_engine.ResilientDataEngine(fred_api_key="").fetch_single_ticker_1h("TESTC")
        assert pd.Timestamp(out.index[-1]) == pd.Timestamp("2026-10-01 07:00", tz="UTC")
    finally:
        clear_frozen_now()
        data_engine.yf = old_yf
        if old_dir is None:
            os.environ.pop("OHLCV_HISTORY_DIR", None)
        else:
            os.environ["OHLCV_HISTORY_DIR"] = old_dir


def test_crypto_volume_filled_from_okx():
    import data_engine
    idx = pd.date_range("2026-10-01 00:00", periods=6, freq="h", tz="UTC")
    fr = pd.DataFrame({"Open": 1.0, "High": 1.0, "Low": 1.0, "Close": 1.0, "Volume": [0, 0, 5, 0, 0, 0.0]}, index=idx)

    class _R:
        def __init__(self, d): self._d = d
        def json(self): return self._d

    calls = {"n": 0}

    def _get(url, params=None, timeout=None):
        calls["n"] += 1
        if calls["n"] > 1:
            return _R({"data": []})
        rows = [[str(int(t.timestamp() * 1000)), "1", "1", "1", "1", "1", "1", str(100.0 + i), "1"]
                for i, t in enumerate(reversed(idx))]
        return _R({"data": rows})

    old = data_engine.requests.get
    data_engine.requests.get = _get
    try:
        out = data_engine._fill_crypto_volume_from_okx(fr, "BTC-USDT")
    finally:
        data_engine.requests.get = old
    assert (out["Volume"] > 0).all() and out.attrs["volume_source"] == "OKX BTC-USDT"


def test_short_term_price_share_never_exceeds_weight():
    import inspect, stateful_adaptive_controller as C
    src = inspect.getsource(C)
    assert "_p_cap = (_wp / max(_wm, 1e-9)) * abs(_m_part)" in src
    wm, wp = 0.7, 0.3
    for mz, pz in ((0.07, 3.0), (-1.0, 3.0), (0.0, -3.0), (2.0, 0.5)):
        m = wm * mz
        p = max(-wp / wm * abs(m), min(wp / wm * abs(m), wp * pz))
        share = abs(p) / max(abs(m) + abs(p), 1e-9)
        assert share <= wp + 1e-9
