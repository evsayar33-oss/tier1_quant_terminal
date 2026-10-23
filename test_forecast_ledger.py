import numpy as np
import pandas as pd

import forecast_ledger as FL


def _frame(n=24 * 60, sd=0.004, seed=1):
    idx = pd.date_range("2026-01-01", periods=n, freq="h", tz="UTC")
    r = np.random.default_rng(seed).normal(0, sd, n)
    return pd.DataFrame({"Close": 100 * np.exp(np.cumsum(r))}, index=idx)


def test_record_grade_and_calibrate(tmp_path):
    df = _frame()
    path = str(tmp_path / "f.csv")
    sigma_true = 0.004 * np.sqrt(24)
    for i in range(24 * 50, 0, -6):          # 50 gün, 6 saatte bir döngü
        t = df.index[-1 - i]
        sub = df[df.index <= t]
        p = float(sub["Close"].iloc[-1])
        v = {"day_range": {"move": p * sigma_true * 0.5, "price": p},   # bilerek %50 dar aralık
             "recent_move": {"z": 1.0, "ret_pct": 0.1}, "learned_model_status": "NOT_PROVEN_ADVISORY",
             "vol_state": {"ratio": 1.0}, "base_rates": {"1": {"up": 0.55}}}
        FL.run_cycle({"X": v}, {"X": df}, path=path, now=t)
    card = FL.ForecastLedger(path).scorecard("X")
    r = card["range"]
    assert r["n_days"] >= 30 and r["coverage"] < 0.5          # dar aralık yakalandı
    assert r["calibrated"] and r["multiplier"] >= 1.4          # çarpan genişletiyor (sınır 1.5)
    assert card["lean4h"]["status"] in ("kanıtsız", "kanıtlı", "ters") and card["p_up"]["n_days"] >= 30
    # Kalibrasyon bir sonraki döngüde aralığa uygulanır
    v = {"day_range": {"move": 1.0, "price": 100.0}}
    FL.run_cycle({"X": v}, {"X": df}, path=path, now=df.index[-1])
    assert v["day_range"]["move"] > 1.39 and v["day_range"]["move_raw"] == 1.0
    assert FL.report_rows({"X": card})[0]["Aralık isabeti (hedef %68)"].startswith("%")


def test_no_double_record_same_hour(tmp_path):
    led = FL.ForecastLedger(str(tmp_path / "f.csv"))
    v = {"day_range": {"move": 1.0, "price": 100.0}}
    t = pd.Timestamp("2026-03-02 10:20", tz="UTC")
    assert led.record("X", v, now=t) and not led.record("X", v, now=t + pd.Timedelta(minutes=30))
