import decision_panel as D


def test_simple_rows_plain_language():
    v = {"entry_allowed": False, "entry_reason": "Kanıt yok", "current_direction": "🔴 AŞAĞI",
         "base_rate": {"up": 0.61}, "dealer_gamma": {"regime": "NEGATİF GAMA"},
         "stop_suggestion": {"kisa": {"stop": 100.0, "side": 1, "distance_pct": 1.2}}}
    r = D.simple_rows({"NQ": v}, ["NQ"], {"move_factor": 1.24})[0]
    assert r["Şimdi ne yapmalı?"].startswith("✋ Bekle")
    assert "10 haftadan 6 tanesi" in r["Önümüzdeki hafta"]
    assert "%24 büyük" in r["Piyasa sakin mi?"]
    assert "altında geçersiz" in r["Fikir nerede bozulur?"]


def test_simple_rows_closed_market():
    v = {"market_structure": {"session": {"phase": "Kapalı"}}}
    r = D.simple_rows({"SPX": v}, ["SPX"])[0]
    assert r["Şimdi ne yapmalı?"] == "⏸️ Piyasa kapalı" and r["Fikir nerede bozulur?"] == "—"
