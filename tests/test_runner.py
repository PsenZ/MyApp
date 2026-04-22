from datetime import datetime
from types import SimpleNamespace

from veyraquant.runner import maybe_send_daily_report
from veyraquant.state import mark_daily_sent, migrate_state
from veyraquant.timeutils import SYDNEY_TZ


def test_force_daily_report_sends_without_updating_daily_state(monkeypatch):
    sent = []
    monkeypatch.setattr("veyraquant.runner.compose_daily_report", lambda *args: ("subject", "body"))
    monkeypatch.setattr("veyraquant.runner.send_email", lambda smtp, subject, body: sent.append(subject))

    now_dt = datetime(2026, 4, 22, 2, 15, tzinfo=SYDNEY_TZ)
    state = migrate_state({})
    config = SimpleNamespace(
        force_daily_report=True,
        dry_run=False,
        send_hour=7,
        send_minute=30,
        send_window_minutes=30,
        smtp=object(),
    )

    did_send, changed_state = maybe_send_daily_report(state, now_dt, [], None, config)

    assert did_send
    assert not changed_state
    assert sent == ["subject"]
    assert state["daily"] == {}


def test_force_daily_report_ignores_already_sent_today(monkeypatch):
    monkeypatch.setattr("veyraquant.runner.compose_daily_report", lambda *args: ("subject", "body"))
    monkeypatch.setattr("veyraquant.runner.send_email", lambda *args: None)

    now_dt = datetime(2026, 4, 22, 8, 0, tzinfo=SYDNEY_TZ)
    state = migrate_state({})
    mark_daily_sent(state, now_dt)
    config = SimpleNamespace(
        force_daily_report=True,
        dry_run=False,
        send_hour=7,
        send_minute=30,
        send_window_minutes=30,
        smtp=object(),
    )

    did_send, changed_state = maybe_send_daily_report(state, now_dt, [], None, config)

    assert did_send
    assert not changed_state
    assert state["daily"]["date"] == "2026-04-22"
