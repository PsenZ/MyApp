from datetime import datetime, timedelta, timezone

from shortreport.state import (
    STATE_VERSION,
    alert_in_cooldown,
    mark_alert_sent,
    mark_daily_sent,
    migrate_state,
)


def test_migrate_legacy_daily_state():
    state = migrate_state({"date": "2026-03-03", "sent_at": "2026-03-03T07:33:21+11:00"})

    assert state["version"] == STATE_VERSION
    assert state["daily"]["date"] == "2026-03-03"
    assert state["alerts"] == {}


def test_alert_cooldown_by_symbol_and_kind():
    now = datetime(2026, 4, 20, 10, 0, tzinfo=timezone.utc)
    state = migrate_state({})
    mark_daily_sent(state, now)
    mark_alert_sent(state, "NVDA", "breakout_entry", now, {"score": 70})

    assert alert_in_cooldown(state, "NVDA", "breakout_entry", now + timedelta(hours=1), 12)
    assert not alert_in_cooldown(state, "MSFT", "breakout_entry", now + timedelta(hours=1), 12)
    assert not alert_in_cooldown(state, "NVDA", "breakout_entry", now + timedelta(hours=13), 12)
