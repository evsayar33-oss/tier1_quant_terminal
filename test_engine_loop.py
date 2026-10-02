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
