import decision_panel as D


def _v(**kw):
    v = {"learned_model_status": "NOT_PROVEN_ADVISORY", "recent_move": {"z": 0.1, "ret_pct": 0.05},
         "base_rates": {"1": {"up": 0.5625, "n": 2514}}, "vol_state": {"ratio": 0.9, "today_pct": 1.0},
         "vol_now": 0.9, "day_range": {"move": 70.0, "price": 7000.0}}
    v.update(kw)
    return v


def test_pulse_uses_volatility_not_price():
    import trade_plan as TP
    assert TP.pulse(_v())["level"] == 2
    assert TP.pulse(_v(vol_state={"ratio": 0.6, "today_pct": 0.6}, vol_now=0.5))["level"] == 1
    assert TP.pulse(_v(vol_now=2.0))["level"] == 4
    assert TP.pulse(_v(shock_active=True))["level"] == 4
    assert TP.pulse(_v(macro_next_min=45))["level"] == 4
    # fiyat yönü değişse de nabız aynı kalır
    assert TP.pulse(_v(recent_move={"z": -3.0}))["level"] == TP.pulse(_v(recent_move={"z": 3.0}))["level"]


def test_day_direction_falls_back_to_significant_base_rate():
    import day_direction as DD
    import pandas as pd
    now = pd.Timestamp("2026-10-23 15:00", tz="UTC")
    c = DD.candidates("NQ", _v(), None, {}, now, {})
    pick = DD.choose("NQ", _v(), c, {})
    assert pick["side"] == 1 and pick["strength"] == "zayıf"
    weak = _v(base_rates={"1": {"up": 0.5166, "n": 2890}})
    assert DD.choose("ETH", weak, DD.candidates("ETH", weak, None, {}, now, {}), {})["side"] == 0
    stats = {"mom4h": {"proven": True, "z": 3.0, "hit": 0.6, "n": 80, "per_asset": {"NQ": 0.6}}}
    v = _v(recent_move={"z": -1.2})
    pick = DD.choose("NQ", v, DD.candidates("NQ", v, None, {}, now, {}), stats)
    assert pick["side"] == -1 and pick["source"] == "mom4h"              # kanıtlı canlı aday önceliklidir


def test_trade_plan_full_or_none():
    import trade_plan as TP
    ctx = {"atr_1h": 10.0, "atr_1d": 60.0, "levels": {"price": 7000.0, "round_step": None, "levels": [
        {"price": 6985.0, "kind": "SWL", "label": "Salınım dibi"}, {"price": 7060.0, "kind": "PDH", "label": "Önceki gün tepesi"}]}}
    v = _v(day_direction={"side": 1, "strength": "zayıf", "why": "tarihsel eğilim", "source": "taban"})
    p = TP.plan("NQ", v, ctx, {})
    assert p["action"] == "trade" and p["side"] == 1 and p["stop"] < 7000 < p["target"] and p["rr"] >= 1.5
    assert "güven: düşük" in p["text"]
    assert TP.plan("NQ", dict(v, shock_active=True), ctx, {})["action"] == "none"
    assert TP.plan("NQ", dict(v, recent_move={"z": -2.0}), ctx, {})["action"] == "none"     # zayıf yön + ters 4 saat
    assert TP.plan("NQ", _v(day_direction={"side": 0}), ctx, {})["action"] == "none"


def test_trade_ledger_grades_stop_or_target(tmp_path):
    import numpy as np
    import pandas as pd
    import trade_plan as TP
    idx = pd.date_range("2026-10-20", periods=72, freq="h", tz="UTC")
    c = np.r_[np.full(30, 7000.0), np.linspace(7000, 7100, 42)]
    f = pd.DataFrame({"High": c + 2, "Low": c - 2, "Close": c}, index=idx)
    d = TP._load(str(tmp_path / "t.csv"))
    d.loc[0] = {"ts": idx[29].isoformat(), "asset": "NQ", "side": 1, "entry": 7000.0, "stop": 6980.0, "target": 7040.0,
                "confidence": "düşük", "source": "taban", "pulse": 0.9, "outcome": None, "r_mult": np.nan,
                "exit_ts": None, "graded": 0, "logic": "x"}
    TP.grade(d, {"NQ": f}, idx[-1])
    assert d.loc[0, "outcome"] == "hedef" and d.loc[0, "r_mult"] == 2.0
    assert TP.scorecard(d)["win"] == 1.0


def test_simple_rows_new_columns_and_closed_market():
    v = _v(trade_plan={"text": "⚪ İşlem yok — bugün için kanıtlı yön yok"}, day_direction={"side": 0, "why": "kanıtlı yön yok"},
           pulse={"text": "🟡 Normal — bugün ..."})
    r = D.simple_rows({"SPX": v}, ["SPX"])[0]
    assert set(r) == {"Varlık", "Nihai karar (işlem önerisi)", "Bugün olası yön", "Giriş riski (piyasa nabzı)",
                      "Yarın ve bu hafta", "Fikir nerede bozulur?"}
    assert r["Bugün olası yön"].startswith("⚪ NÖTR")
    closed = {"market_structure": {"session": {"phase": "Kapalı"}}}
    rc = D.simple_rows({"SPX": closed}, ["SPX"])[0]
    assert rc["Bugün olası yön"] == "⏸️ Piyasa kapalı" and rc["Giriş riski (piyasa nabzı)"] == "—"


def test_remaining_days_and_recent_move():
    import datetime as dt
    import numpy as np
    import pandas as pd
    import stop_levels as SL
    thu = dt.datetime(2026, 10, 22, tzinfo=dt.timezone.utc)
    assert D._remaining_days("SPX", thu) == 1 and D._remaining_days("BTC", thu) == 3
    b = {1: {"up": 0.53, "n": 2500}, 3: {"up": 0.52, "n": 1000}, 5: {"up": 0.6, "n": 500}}
    txt = D.simple_days({"base_rates": b}, "BTC", thu)
    assert "Hafta sonuna kadar (3 gün): %52 yükseliş (yazı-tura)" in txt and "yazı-tura" in txt
    c = pd.Series(100 * np.exp(np.cumsum(np.r_[np.random.default_rng(0).normal(0, 0.002, 200), [0.01] * 4])))
    rm = SL.recent_move(pd.DataFrame({"Close": c.values}, index=pd.date_range("2026-01-01", periods=len(c), freq="h", tz="UTC")))
    assert rm["z"] > 3 and rm["ret_pct"] > 3.9
    v = {"learned_model_status": "NOT_PROVEN_ADVISORY", "recent_move": rm}
    assert SL.evidence_short_side(v) == 1


def test_pair_consistency_and_partial_bar():
    import numpy as np
    import pandas as pd
    import stop_levels as SL
    mv = {"SPX": {"z_own": -0.9, "z": -0.9}, "NQ": {"z_own": -0.5, "z": -0.5},
          "XAU": {"z_own": 1.0, "z": 1.0}, "XAG": {"z_own": -0.9, "z": -0.9}}
    SL.pair_consistent(mv)
    assert mv["SPX"]["z"] == mv["NQ"]["z"] == -0.7 and mv["SPX"]["pair"] == "ortak"
    assert mv["XAU"]["z"] == 1.0 and mv["XAG"]["z"] == -0.9 and mv["XAU"]["pair"] == "ayrışma"
    idx = list(pd.date_range("2026-01-01", periods=100, freq="h", tz="UTC"))
    close = list(100 * np.exp(np.cumsum(np.random.default_rng(2).normal(0, 0.002, 100))))
    df = pd.DataFrame({"Close": close + [close[-1]]}, index=idx + [idx[-1] + pd.Timedelta(minutes=4)])
    rm = SL.recent_move(df)
    assert abs(rm["ret_pct"] - 100 * (close[-1] / close[-5] - 1)) < 1e-3   # 4 saat zamana göre (yarım bar pencereyi kısaltmaz)
