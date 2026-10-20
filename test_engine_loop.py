from datetime import datetime, timezone

import engine_loop


def test_next_cycle_is_90s_after_the_hour():
    t = engine_loop.next_cycle_time(datetime(2026, 10, 2, 13, 0, 30, tzinfo=timezone.utc))
    assert t == datetime(2026, 10, 2, 13, 1, 30, tzinfo=timezone.utc)
    t = engine_loop.next_cycle_time(datetime(2026, 10, 2, 13, 5, tzinfo=timezone.utc))
    assert t == datetime(2026, 10, 2, 14, 1, 30, tzinfo=timezone.utc)


def test_engine_has_no_trading_layer():
    import importlib.util
    assert not hasattr(engine_loop, "build_signals") and not hasattr(engine_loop, "paper_broker")
    for mod in ("paper_broker", "strategy_lab", "bot_loop"):
        assert importlib.util.find_spec(mod) is None


def test_recent_cycle_guard(tmp_path):
    import json
    p = tmp_path / "s.json"
    now = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
    p.write_text(json.dumps({"last_success": "2026-10-20T11:30:00+00:00"}))
    assert engine_loop.recent_cycle(45, str(p), now)
    assert not engine_loop.recent_cycle(20, str(p), now)
    assert not engine_loop.recent_cycle(0, str(p), now)
    assert not engine_loop.recent_cycle(45, str(tmp_path / "missing.json"), now)
