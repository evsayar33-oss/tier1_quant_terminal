import decision_panel as D


def test_simple_rows_plain_language():
    v = {"entry_allowed": False, "entry_reason": "Kanıt yok", "current_direction": "🔴 AŞAĞI",
         "base_rates": {1: {"up": 0.5625, "n": 2514}, 5: {"up": 0.52, "n": 502}},
         "dealer_gamma": {"regime": "NEGATİF GAMA"},
         "vol_state": {"ratio": 1.4, "today_pct": 2.0, "recent_pct": 1.6, "normal_pct": 1.43, "move_factor": 1.24},
         "stop_suggestion": {"kisa": {"stop": 100.0, "side": 1, "distance_pct": 1.2}}}
    r = D.simple_rows({"NQ": v}, ["NQ"], {"move_factor": 1.24})[0]
    assert r["Şimdi ne yapmalı?"].startswith("✋ Bekle")
    assert "Sonraki gün: %56 yükseliş (anlamlı eğilim)" in r["Yarın ve bu hafta"]
    assert r["Piyasa sakin mi?"].startswith("🌪️ Normalden hareketli — son 20 gün ±%1.6/gün, son 1 yıl ±%1.4/gün")
    assert "×1.24" in r["Piyasa sakin mi?"] and "dealer gaması negatif" in r["Piyasa sakin mi?"]
    assert "altında geçersiz" in r["Fikir nerede bozulur?"]


def test_simple_rows_closed_market():
    v = {"market_structure": {"session": {"phase": "Kapalı"}}}
    r = D.simple_rows({"SPX": v}, ["SPX"])[0]
    assert r["Şimdi ne yapmalı?"] == "⏸️ Piyasa kapalı" and r["Fikir nerede bozulur?"] == "—"


def test_today_risk_side():
    v = {"current_direction": "🔴 AŞAĞI", "verdict": "SAT", "base_rate": {"up": 0.61, "n": 502, "horizon_d": 5},
         "learned_model_status": "NOT_PROVEN_ADVISORY", "short_term_parts": {"price_z": -1.0},
         "dealer_gamma": {"regime": "NEGATİF GAMA"}, "day_range": {"move": 460.0, "price": 29000.0}}
    r = D.simple_rows({"NQ": v}, ["NQ"])[0]
    assert "28,540 – 29,460" in r["Bugün fiyat ne yapabilir?"]
    assert r["Şimdi girmek riskli mi?"].startswith("🔴")
    assert "Çelişkili" in r["Girersen hangi yön daha iyi?"]


def test_metal_divergence_is_not_invented():
    # XAU %56 / XAG %55 taban oranı istatistiksel olarak 0.5'ten farksız; kanıtsız model z'si yön vermez
    mk = lambda up, pz: {"base_rate": {"up": up, "n": 502, "horizon_d": 5}, "current_direction": "🔴 HAFİF AŞAĞI",
                         "learned_model_status": "NOT_PROVEN_ADVISORY", "short_term_parts": {"price_z": pz}}
    rows = D.simple_rows({"XAU": mk(0.5598, -0.06), "XAG": mk(0.5458, 0.21)}, ["XAU", "XAG"])
    assert rows[0]["Girersen hangi yön daha iyi?"] == rows[1]["Girersen hangi yön daha iyi?"] == "⚪ Belirgin yön yok"


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
