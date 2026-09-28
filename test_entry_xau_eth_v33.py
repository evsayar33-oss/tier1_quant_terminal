"""v3.3 regression tests: RVOL blow-up, partial/seasonal RVOL, neutral entry text,
counter-trend live direction, gold sovereign residual."""
import numpy as np
import pandas as pd

from dynamic_entry_engine import StatefulDynamicEntryEngine


def _ohlcv(n=220, zero_every=None, seed=0, session=False):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2026-09-01", periods=n, freq="h", tz="UTC")
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.003, n)))
    vol = rng.uniform(800, 1200, n)
    if session:   # US hours 10x busier than Asia
        vol = vol * np.where((idx.hour >= 13) & (idx.hour <= 20), 10.0, 1.0)
    if zero_every:
        vol[::zero_every] = 0.0
        vol[1::zero_every] = 0.0
    df = pd.DataFrame({"Open": c, "High": c * 1.002, "Low": c * 0.998, "Close": c, "Volume": vol}, index=idx)
    return df


def test_rvol_never_explodes_with_zero_volume_bars():
    df = _ohlcv(zero_every=3)
    p, err = StatefulDynamicEntryEngine().profile(df, now=df.index[-1] + pd.Timedelta(hours=1))
    assert err is None
    assert p["rvol_climax"] < 100 and p["rvol_low"] > 0


def test_asian_session_bar_is_not_flagged_illiquid():
    df = _ohlcv(session=True)
    df = df[df.index.hour != 14].copy()  # keep regular structure
    last_asia = df[df.index.hour == 9].index[-1]
    d = df[df.index <= last_asia]
    p, _ = StatefulDynamicEntryEngine().profile(d, now=last_asia + pd.Timedelta(hours=1))
    assert 0.6 < p["rvol"] < 1.6          # plain 20-bar mean would give ~0.3


def test_partial_bar_is_projected_not_penalised():
    df = _ohlcv()
    df.iloc[-1, df.columns.get_loc("Volume")] = 300.0      # 18 minutes into the bar
    p, _ = StatefulDynamicEntryEngine().profile(df, now=df.index[-1] + pd.Timedelta(minutes=18))
    assert p["partial_bar_fraction"] == 0.3
    assert p["rvol"] > 0.8


def test_neutral_verdict_entry_reason_is_not_an_entry_recommendation():
    from gatekeeper import PreTradeGatekeeper as Gatekeeper
    v = {"X": {"verdict": "NÖTR (BEKLE)", "entry_allowed": True,
               "entry_reason": "Dinamik giriş uygun: ATR 1.0x", "timeframe_confluence": {}}}
    out = Gatekeeper.apply_final_entry_gate(Gatekeeper.__new__(Gatekeeper), v)["X"]
    assert out["entry_allowed"] is False
    assert "Dinamik giriş uygun" not in out["entry_reason"]


def test_counter_trend_live_bounce_is_capped():
    from gatekeeper import PreTradeGatekeeper as Gatekeeper
    tfs = {k: {"available": True, "score": s} for k, s in (("HTF_1D", -0.5), ("MTF_4H", -0.6), ("LTF_1H", -0.3))}
    v = {"verdict": "NÖTR (BEKLE)", "live_score": 1.9, "current_roc": 0.45,
         "current_direction": "🟢🟢 GÜÇLÜ YUKARI (%+0.45)"}
    Gatekeeper._flag_counter_trend_live_direction(v, {"timeframes": tfs})
    assert v["live_counter_trend"] and "GÜÇLÜ" not in v["current_direction"]


def test_gold_sovereign_is_a_residual_not_momentum():
    from quant_processor import RobustQuantProcessor as Q
    df = _ohlcv(n=300)
    df["Close"] = df["Close"].to_numpy() * np.r_[np.ones(276), np.linspace(1, 0.97, 24)]
    # gold falls exactly as much as sharply rising real yields imply -> little residual
    explained = Q.compute_gold_sovereign_decoupling(df, 2.5, pd.DataFrame())
    unexplained = Q.compute_gold_sovereign_decoupling(df, -1.0, pd.DataFrame())
    assert abs(explained) < abs(unexplained)
