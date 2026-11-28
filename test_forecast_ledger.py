import numpy as np
import pandas as pd

import forecast_ledger as FL


def _frame(n=24 * 60, sd=0.004, seed=1):
    idx = pd.date_range("2026-01-01", periods=n, freq="h", tz="UTC")
    r = np.random.default_rng(seed).normal(0, sd, n)
    price = 100 * np.exp(np.cumsum(r))
    return pd.DataFrame({"Close": price, "Open": price}, index=idx)


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


def _verdict():
    return {"day_range":{"move":1.0,"price":100.0},
            "learned_model_status":"NOT_PROVEN_ADVISORY",
            "recent_move":{"z":1.0,"ret_pct":0.1}}


def test_strict_forward_provenance_and_no_future_bar(tmp_path):
    led=FL.ForecastLedger(str(tmp_path / "f.csv"))
    t=pd.Timestamp("2026-11-25 10:03",tz="UTC")
    led.record("BTC",_verdict(),now=t)
    start=t.floor("h")+pd.Timedelta(hours=1)
    end=start+pd.Timedelta(hours=4)
    idx=pd.date_range(start,end,freq="h")
    f=pd.DataFrame({"Open":[100.,101.,102.,103.,104.],
                    "Close":[999.]*5},index=idx)
    row=led.df.iloc[0]
    assert pd.Timestamp(row.observed_at_utc)==t
    assert pd.Timestamp(row.label_4h_start_utc)==start
    assert pd.Timestamp(row.label_4h_end_utc)==end
    led.grade({"BTC":f},now=end)  # endpoint still forming
    assert led.df.iloc[0].graded_4h==0
    led.grade({"BTC":f},now=end+pd.Timedelta(hours=1))
    row=led.df.iloc[0]
    assert row.graded_4h==1 and np.isclose(row.ret_4h,np.log(104/100))
    assert row.label_4h_start_price==100 and row.label_4h_end_price==104
    assert row.label_4h_reason=="EXACT_CONTIGUOUS_HOURLY_OPENS"
    assert led.scorecard("BTC")["lean4h"]["n"]==1


def test_missing_weekend_window_never_substitutes_next_open(tmp_path):
    led=FL.ForecastLedger(str(tmp_path/"f.csv"))
    t=pd.Timestamp("2026-11-28 10:03",tz="UTC")
    led.record("SPX",_verdict(),now=t)
    idx=pd.date_range("2026-11-29 23:00",periods=10,freq="h",tz="UTC")
    f=pd.DataFrame({"Open":100., "Close":101.},index=idx)
    led.grade({"SPX":f},now=t+pd.Timedelta(hours=100))
    assert led.df.graded_4h.iloc[0]==0
    led.grade({"SPX":f},now=t+pd.Timedelta(hours=110))
    assert led.df.graded_4h.iloc[0]==-1
    assert pd.isna(led.df.ret_4h.iloc[0])
    assert led.df.label_4h_reason.iloc[0]=="MISSING_EXACT_WINDOW"


def test_exact_start_end_with_internal_gap_is_not_valid(tmp_path):
    led=FL.ForecastLedger(str(tmp_path/"f.csv"))
    t=pd.Timestamp("2026-11-25 10:03",tz="UTC")
    led.record("NQ",_verdict(),now=t)
    idx=pd.date_range("2026-11-25 11:00",periods=5,freq="h",tz="UTC").delete(2)
    f=pd.DataFrame({"Open":100.,"Close":101.},index=idx)
    led.grade({"NQ":f},now=t+pd.Timedelta(hours=110))
    assert led.df.graded_4h.iloc[0]==-1


def test_legacy_grades_preserved_but_not_counted_as_exact(tmp_path):
    path=tmp_path/"f.csv"
    pd.DataFrame([{"ts":"2026-10-24T09:00:00+00:00","asset":"SPX",
        "price":100.,"logic":FL.LOGIC,"lean4h":1,"graded_4h":1,"ret_4h":.005,
        "graded_24h":1}]).to_csv(path,index=False)
    led=FL.ForecastLedger(str(path))
    led.grade({},now=pd.Timestamp("2026-11-28",tz="UTC"))
    assert led.df.iloc[0].ret_4h==.005 and led.df.iloc[0].graded_4h==1
    card=led.scorecard("SPX")
    assert card["lean4h_legacy_unverified"]==1 and "lean4h" not in card
