"""v15.1 — market structure, vanna/charm, Deribit, suggested stop + its ledger, decision panel."""
import math
import os
import tempfile
from datetime import date

import numpy as np
import pandas as pd

import dealer_gamma as DG
import decision_panel as DP
import market_structure as MS
import stop_levels as SL


# ---------------------------------------------------------------------------
# calendar / session
# ---------------------------------------------------------------------------
def test_opex_and_vix_expiry_rules():
    assert MS.third_friday(2026, 10) == date(2026, 10, 16)
    assert MS.third_friday(2026, 11) == date(2026, 11, 20)
    assert MS.vix_expiry(2026, 10) == date(2026, 10, 21)          # 30 days before Nov 20, a Wednesday
    assert MS.vix_expiry(2026, 10).weekday() == 2
    cal = MS.options_calendar("2026-10-14T15:00:00Z")
    assert cal["next_opex"] == "2026-10-16" and cal["opex_week"] and not cal["quarterly_opex"]
    after = MS.options_calendar("2026-10-19T15:00:00Z")
    assert after["days_after_opex"] == 3 and after["next_opex"] == "2026-11-20"
    assert MS.options_calendar("2026-12-14T15:00:00Z")["quarterly_opex"]


def test_session_phases_in_new_york_time():
    assert MS.session_phase("2026-10-14T13:45:00Z", "NQ")["phase"].startswith("ABD açılış")   # 09:45 ET
    assert MS.session_phase("2026-10-14T19:00:00Z", "NQ")["phase"] == "ABD kapanış saatleri"  # 15:00 ET
    assert MS.session_phase("2026-10-14T02:00:00Z", "NQ")["phase"] == "Asya seansı"           # 22:00 ET
    assert MS.session_phase("2026-10-17T15:00:00Z", "NQ")["phase"] == "Kapalı"                # Saturday
    assert MS.session_phase("2026-10-17T15:00:00Z", "BTC")["phase"] == "Hafta sonu"
    # CME day starts 18:00 ET
    assert MS.trading_day("2026-10-14T22:30:00Z", "NQ") == date(2026, 10, 15)
    assert MS.trading_day("2026-10-14T22:30:00Z", "BTC") == date(2026, 10, 14)


# ---------------------------------------------------------------------------
# levels / sweep
# ---------------------------------------------------------------------------
def _frame(start, opens, highs, lows, closes, freq="h"):
    idx = pd.date_range(start, periods=len(closes), freq=freq, tz="UTC")
    return pd.DataFrame({"Open": opens, "High": highs, "Low": lows, "Close": closes,
                         "Volume": [100.0] * len(closes)}, index=idx)


def _two_days():
    # 2026-10-13 22:00Z (18:00 ET) -> trading day 10-14 ; 24 bars, then day 10-15
    n = 48
    c = np.r_[np.linspace(100, 104, 24), np.linspace(103, 102, 24)]
    h, l = c + 0.5, c - 0.5
    h[10], l[5] = 110.0, 95.0                 # previous day extremes
    return _frame("2026-10-13T22:00:00Z", c, h, l, c)


def test_previous_day_high_low_follow_cme_trading_day():
    d = _two_days()
    lv = MS.liquidity_levels(d, "NQ", now=d.index[-1])
    kinds = {x["kind"]: x["price"] for x in lv["levels"]}
    assert kinds["PDH"] == 110.0 and kinds["PDL"] == 95.0
    assert "VWAP" in kinds and lv["round_step"] > 0


def test_sweep_needs_wick_through_from_inside_and_close_back():
    levels = {"levels": [{"price": 100.0, "kind": "PDL", "label": "Önceki gün dibi"},
                         {"price": 110.0, "kind": "PDH", "label": "Önceki gün tepesi"}]}
    bull = _frame("2026-10-14T14:00:00Z", [101, 101], [101.5, 101.8], [100.6, 99.2], [101, 101.4])
    ev = MS.detect_sweep(bull, levels)
    assert ev["direction"] == 1 and ev["kind"] == "PDL" and ev["bars_ago"] == 0
    bear = _frame("2026-10-14T14:00:00Z", [109, 109], [109.5, 110.9], [108.5, 108.6], [109, 109.1])
    assert MS.detect_sweep(bear, levels)["direction"] == -1
    # A plain breakdown (closes below the level) is NOT a sweep
    brk = _frame("2026-10-14T14:00:00Z", [101, 100.5], [101.2, 100.6], [100.4, 98.0], [100.6, 98.2])
    assert MS.detect_sweep(brk, levels) is None


def test_cta_trigger_and_vol_control_direction():
    idx = pd.date_range("2025-01-01", periods=300, freq="B", tz="UTC")
    up = pd.DataFrame({"High": 0, "Low": 0, "Close": np.exp(np.linspace(0, 0.3, 300))}, index=idx)
    up["High"], up["Low"] = up["Close"] * 1.01, up["Close"] * 0.99
    m = MS.cta_model(up)
    assert m["position"] > 0.5 and m["nearest_trigger_below"]["level"] < up["Close"].iloc[-1]
    rng = np.random.default_rng(3)
    r = np.r_[rng.normal(0, 0.02, 250), rng.normal(0, 0.004, 50)]       # vol collapses
    calm = pd.DataFrame({"Close": 100 * np.exp(np.cumsum(r))}, index=idx)
    calm["High"], calm["Low"] = calm["Close"] * 1.001, calm["Close"] * 0.999
    vc = MS.vol_control_model(calm)
    assert vc["leverage_change_5d"] > 0 and vc["flow"] == "mekanik ALIM"


# ---------------------------------------------------------------------------
# vanna / charm / deribit
# ---------------------------------------------------------------------------
def _bs_delta(S, K, T, v, r=0.04):
    from scipy.stats import norm
    return norm.cdf((math.log(S / K) + (r + 0.5 * v * v) * T) / (v * math.sqrt(T)))


def test_vanna_and_charm_match_finite_differences():
    S, K, T, v = 100.0, 95.0, 20 / 365, 0.3
    fd_vanna = (_bs_delta(S, K, T, v + 1e-4) - _bs_delta(S, K, T, v - 1e-4)) / 2e-4
    assert abs(float(DG.bs_vanna(S, K, T, v)) - fd_vanna) < 1e-5
    dt = 1e-5
    fd_charm = (_bs_delta(S, K, T - dt, v) - _bs_delta(S, K, T, v)) / dt     # time passing
    assert abs(float(DG.bs_charm(S, K, T, v)) - fd_charm) < 1e-3


def test_vanna_flow_sign_dealers_short_otm_puts_buy_when_iv_falls():
    spot = 6000.0
    exp = pd.Timestamp("2026-10-14") + pd.Timedelta(days=20)
    ch = pd.DataFrame([{"root": "SPX", "expiry": exp, "type": "P", "strike": 5700.0, "iv": 0.25, "oi": 50000.0}])
    m = DG.build_gamma_map([(ch, spot)], spot, now=pd.Timestamp("2026-10-14T15:00:00Z"))
    assert m["vanna_flow_iv_down_1pt_usd"] > 0          # the "vanna rally"
    assert "ALIR" in m["interpretation"]["vanna_charm"]


def test_deribit_payload_parses_and_maps_to_spot_futures():
    payload = {"result": [
        {"instrument_name": "BTC-16OCT26-100000-C", "open_interest": 500, "mark_iv": 45.0, "underlying_price": 101000},
        {"instrument_name": "BTC-6NOV26-90000-P", "open_interest": 800, "mark_iv": 55.0, "underlying_price": 101200},
        {"instrument_name": "BTC-PERPETUAL", "open_interest": 1},
    ]}
    ch, spot = DG.parse_deribit_payload(payload)
    assert len(ch) == 2 and spot == 101100.0 and set(ch["mult"]) == {1.0}
    assert ch["expiry_utc"].iloc[0] == pd.Timestamp("2026-10-16T08:00:00Z")
    m = DG.snapshot_asset("BTC", 101300.0, now=pd.Timestamp("2026-10-14T15:00:00Z"),
                          fetch_deribit=lambda c: (ch, spot), fetch_cboe=lambda s: (None, None),
                          fetch_yf=lambda s: (None, None))
    assert m["source"] == "Deribit" and m["call_wall"] is not None
    assert abs(m["expected_move_1d"] - 101300 * 0.45 / math.sqrt(365)) < 1e-6 * 101300


# ---------------------------------------------------------------------------
# suggested stop
# ---------------------------------------------------------------------------
LEVELS = {"price": 100.0, "round_step": 5.0, "levels": [
    {"price": 98.2, "kind": "SWL", "label": "Salınım dibi"},
    {"price": 96.0, "kind": "PDL", "label": "Önceki gün dibi"},
    {"price": 101.6, "kind": "SWH", "label": "Salınım tepesi"},
]}


def test_stop_goes_beyond_nearest_structure_with_hunt_buffer():
    s = SL.suggest_stop(+1, "kisa", 100.0, atr_1h=1.0, levels=LEVELS)
    assert s["anchor"]["kind"] == "SWL" and abs(s["stop"] - (98.2 - 0.25)) < 1e-9
    assert s["distance"] > 1.8 and "likidite avı" in s["basis"]
    short = SL.suggest_stop(-1, "kisa", 100.0, atr_1h=1.0, levels=LEVELS)
    assert short["anchor"]["kind"] == "SWH" and short["stop"] > 101.6


def test_stop_avoids_round_numbers_and_widens_in_negative_gamma():
    lv = {"price": 100.0, "round_step": 5.0, "levels": [{"price": 95.1, "kind": "PDL", "label": "Önceki gün dibi"}]}
    s = SL.suggest_stop(+1, "kisa", 100.0, atr_1h=2.0, levels=lv)
    assert s["stop"] < 95.0 - 0.29                        # pushed beyond the 95 round number
    pos = SL.suggest_stop(+1, "kisa", 100.0, atr_1h=1.0, levels=LEVELS, gamma={"regime": "POZİTİF GAMA"})
    neg = SL.suggest_stop(+1, "kisa", 100.0, atr_1h=1.0, levels=LEVELS, gamma={"regime": "NEGATİF GAMA"})
    assert neg["stop"] < pos["stop"] and neg["negative_gamma"]


def test_stop_falls_back_to_volatility_and_uses_daily_unit_for_long_horizon():
    s = SL.suggest_stop(+1, "kisa", 100.0, atr_1h=0.1, levels={"price": 100.0, "levels": []})
    assert s["anchor"] is None and abs(s["stop"] - 99.85) < 1e-9
    u = SL.suggest_stop(+1, "uzun", 100.0, atr_1h=0.5, em_1d=2.0, levels=LEVELS)
    assert u["unit"].startswith("günlük beklenen") and u["anchor"]["kind"] == "SWL"
    assert SL.suggest_stop(0, "kisa", 100.0, atr_1h=1.0) is None


def test_stop_ledger_widens_buffer_when_stops_get_hunted():
    with tempfile.TemporaryDirectory() as d:
        led = SL.StopLedger(os.path.join(d, "s.csv"))
        t0 = pd.Timestamp("2026-06-01T00:00:00Z")
        bars = []
        for i in range(40):                                   # 40 independent 4h windows
            ts = t0 + pd.Timedelta(hours=4 * i)
            led.record("NQ", {"horizon": "kisa", "side": 1, "price": 100.0, "stop": 99.0}, now=ts)
            # each window: dips to 98.9 (stop hit) then closes at 101 (direction right) -> hunted
            bars += [(ts + pd.Timedelta(hours=k + 1), 99.5, 100.2, 98.9 if k == 0 else 99.5, 101.0 if k == 3 else 99.8)
                     for k in range(4)]
        f = pd.DataFrame(bars, columns=["t", "Open", "High", "Low", "Close"]).set_index("t")
        assert led.grade({"NQ": f}, now=t0 + pd.Timedelta(days=10)) == 40
        st = led.stats("kisa")
        assert st["hunted_rate"] == 1.0 and st["buffer_mult"] == 2.0 and st["verdict"] == "KALİBRE"
        assert not led.record("NQ", {"horizon": "kisa", "side": 1, "price": 1, "stop": 0}, now=t0)   # dedupe


# ---------------------------------------------------------------------------
# decision panel
# ---------------------------------------------------------------------------
def test_decision_panel_rows():
    v = {"NQ": {"current_direction": "🟢 YUKARI (%+0.31)", "verdict": "SAT",
                "learned_model_status": "NOT_PROVEN_ADVISORY", "entry_allowed": False,
                "entry_reason": "⛔ Kanıt yok (örneklem dışı t=0.4 < 2.0) → giriş kapalı.", "entry_grade": "C",
                "stop_suggestion": {"kisa": {"stop": 24810.0, "side": 1, "distance_pct": 0.42, "atr_1h_mult": 1.1,
                                             "label": "Kısa vade (1-4 saat)", "basis": "x"}, "uzun": None},
                "market_structure": {"levels": {"price": 24914.0}}},
         "SPX": {"current_direction": "⚪ YATAY / DENGELİ (%+0.01)", "verdict": "NÖTR (BEKLE)"}}
    rows = {r["Varlık"]: r for r in DP.build_rows(v, ["NQ", "SPX"])}
    nq = rows["NQ"]
    assert nq["Kısa vade (1-4 saat)"] == "🟢 YUKARI" and nq["Uzun vade (24 saat-1 hafta)"] == "🔴 SAT · kanıtsız"
    assert nq["Giriş"] == "⛔ Önerilmez · model kanıtı yok (t < 2)"
    assert nq["Stop · kısa vade"] == "24,810 (-0.42% · 1.1×ATR)" and nq["Stop · uzun vade"] == "—"
    assert rows["SPX"]["Giriş"].startswith("⚪ Yön yok")
    v["NQ"]["entry_allowed"] = True
    assert DP.entry_label(v["NQ"]) == "✅ Giriş önerilir"
