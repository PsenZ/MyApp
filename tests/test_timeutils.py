from datetime import datetime

from veyraquant.timeutils import SYDNEY_TZ, daily_report_due


def test_daily_report_due_before_threshold_is_false():
    now_dt = datetime(2026, 4, 22, 6, 59, tzinfo=SYDNEY_TZ)

    assert not daily_report_due(now_dt, 7, 30, 30)


def test_daily_report_due_after_threshold_is_true_all_day():
    early_dt = datetime(2026, 4, 22, 7, 0, tzinfo=SYDNEY_TZ)
    later_dt = datetime(2026, 4, 22, 21, 15, tzinfo=SYDNEY_TZ)

    assert daily_report_due(early_dt, 7, 30, 30)
    assert daily_report_due(later_dt, 7, 30, 30)
