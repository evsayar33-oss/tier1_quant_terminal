from __future__ import annotations

import os
import tempfile

import numpy as np
import pandas as pd

import ohlcv_history as hist


def make_frame(start: str, n: int, start_price: float = 100.0) -> pd.DataFrame:
    idx = pd.date_range(start, periods=n, freq="h", tz="UTC")
    p = np.linspace(start_price, start_price + n * 0.1, n)
    return pd.DataFrame(
        {"Open": p, "High": p + 0.2, "Low": p - 0.2, "Close": p + 0.05, "Volume": np.full(n, 1000.0)},
        index=idx,
    )


def test_merge_and_dedupe():
    with tempfile.TemporaryDirectory() as td:
        os.environ["OHLCV_HISTORY_DIR"] = td
        a = make_frame("2026-09-01", 80)
        b = make_frame("2026-09-02", 80, 108.0)
        m1 = hist.merge_and_persist("ES=F", a)
        assert len(m1) == 80
        m2 = hist.merge_and_persist("ES=F", b)
        assert len(m2) == 104
        assert m2.index.is_unique
        assert len(hist.load_history("ES=F")) == 104


def test_bounded_to_200():
    with tempfile.TemporaryDirectory() as td:
        os.environ["OHLCV_HISTORY_DIR"] = td
        frame = make_frame("2026-01-01", 250)
        merged = hist.merge_and_persist("NQ=F", frame, max_bars=200)
        assert len(merged) == 200
        assert len(hist.load_history("NQ=F")) == 200


def test_missing_volume_is_not_fabricated():
    with tempfile.TemporaryDirectory() as td:
        os.environ["OHLCV_HISTORY_DIR"] = td
        frame = make_frame("2026-09-01", 75)
        frame["Volume"] = np.nan
        merged = hist.merge_and_persist("GC=F", frame)
        assert merged["Volume"].isna().all()


if __name__ == "__main__":
    test_merge_and_dedupe()
    test_bounded_to_200()
    test_missing_volume_is_not_fabricated()
    print("Persistent OHLCV history tests: PASS")
