from datetime import datetime, timezone

import bot_loop


def test_next_cycle_is_90s_after_the_hour():
    t = bot_loop.next_cycle_time(datetime(2026, 10, 2, 13, 0, 30, tzinfo=timezone.utc))
    assert t == datetime(2026, 10, 2, 13, 1, 30, tzinfo=timezone.utc)
    t = bot_loop.next_cycle_time(datetime(2026, 10, 2, 13, 5, tzinfo=timezone.utc))
    assert t == datetime(2026, 10, 2, 14, 1, 30, tzinfo=timezone.utc)


def test_signal_is_tradeable_only_with_proof_and_open_gate():
    now = datetime(2026, 10, 2, 13, 2, tzinfo=timezone.utc)
    base = {"verdict": "SAT", "entry_allowed": True}
    st = {"asset_verdicts": {"SPX": dict(base, learned_model_status="NOT_PROVEN_ADVISORY"),
                             "NQ": dict(base, learned_model_status="ACTIVE"),
                             "XAU": dict(base, learned_model_status="ACTIVE", entry_allowed=False)}}
    s = bot_loop.build_signals(st, now)["assets"]
    assert s["SPX"]["tradeable"] is False and s["NQ"]["tradeable"] is True and s["XAU"]["tradeable"] is False
    assert s["NQ"]["side"] == "SHORT"


def test_proven_lab_strategy_makes_asset_tradeable():
    now = datetime(2026, 10, 7, 13, 2, tzinfo=timezone.utc)
    st = {"asset_verdicts": {"XAU": {"verdict": "NÖTR (BEKLE)", "learned_model_status": "NOT_PROVEN_ADVISORY"},
                             "BTC": {"verdict": "NÖTR (BEKLE)", "learned_model_status": "NOT_PROVEN_ADVISORY"}}}
    lab = {"XAU": {"side": "LONG", "proven": True, "sl": 1.0, "tp": 2.0},
           "BTC": {"side": "LONG", "proven": False}}
    s = bot_loop.build_signals(st, now, lab)["assets"]
    assert s["XAU"]["tradeable"] and s["XAU"]["trade_side"] == "LONG" and s["XAU"]["trade_source"] == "lab"
    assert not s["BTC"]["tradeable"] and s["BTC"]["trade_side"] == "FLAT"
    assert s["BTC"]["lab"]["side"] == "LONG"            # unproven candidate still visible (paper only)
