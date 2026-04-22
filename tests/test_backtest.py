import numpy as np
import pandas as pd

from veyraquant.backtest import run_backtest
from veyraquant.config import AppConfig, SmtpConfig


def make_config():
    return AppConfig(
        symbols=["NVDA"],
        market_symbols=["SPY"],
        send_hour=7,
        send_minute=30,
        send_window_minutes=10,
        state_path="state/test.json",
        cache_dir=".cache/test",
        subject_prefix="Test",
        entry_alerts_enabled=True,
        alert_cooldown_hours=12,
        alert_score_threshold=65,
        social_sentiment_threshold=0.15,
        intraday_interval="30m",
        account_equity=None,
        risk_per_trade_pct=0.5,
        max_position_pct=10,
        portfolio_heat_max_pct=3,
        atr_stop_multiplier=2,
        min_rr=1.5,
        force_daily_report=False,
        dry_run=True,
        smtp=SmtpConfig("smtp.test", 465, None, None, None, None),
    )


def test_backtest_returns_summary_without_future_data_crash():
    rows = 180
    close = 100 + np.arange(rows) * 0.25
    daily = pd.DataFrame(
        {
            "Open": close - 0.2,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": np.linspace(1_000_000, 1_800_000, rows),
        },
        index=pd.date_range("2025-01-01", periods=rows, freq="B"),
    )

    result = run_backtest("NVDA", daily, make_config())

    assert result.trades >= 0
    assert 0 <= result.win_rate <= 100
    assert result.buy_hold_pct > 0
