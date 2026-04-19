import numpy as np
import pandas as pd

from shortreport.config import AppConfig, SmtpConfig
from shortreport.market import build_market_context
from shortreport.models import FundamentalsData, NewsBundle
from shortreport.reporting import compose_daily_report
from shortreport.signals import analyze_symbol, assign_ranks, enforce_portfolio_heat
from shortreport.timeutils import SYDNEY_TZ
from datetime import datetime


def make_config():
    return AppConfig(
        symbols=["NVDA", "MSFT"],
        market_symbols=["SPY", "QQQ", "SMH", "^VIX"],
        send_hour=7,
        send_minute=30,
        send_window_minutes=10,
        state_path="state/test.json",
        cache_dir=".cache/test",
        subject_prefix="Test 简报",
        entry_alerts_enabled=True,
        alert_cooldown_hours=12,
        alert_score_threshold=65,
        social_sentiment_threshold=0.15,
        intraday_interval="30m",
        account_equity=100_000,
        risk_per_trade_pct=0.5,
        max_position_pct=10,
        portfolio_heat_max_pct=0.6,
        atr_stop_multiplier=2,
        min_rr=1.5,
        dry_run=True,
        smtp=SmtpConfig("smtp.test", 465, None, None, None, None),
    )


def price_frame(rows=260, start=100, step=0.4):
    close = start + np.arange(rows) * step
    return pd.DataFrame(
        {
            "Open": close - 0.2,
            "High": close + 1.5,
            "Low": close - 1.5,
            "Close": close,
            "Volume": np.linspace(1_000_000, 2_000_000, rows),
        },
        index=pd.date_range("2025-01-01", periods=rows, freq="B"),
    )


def test_analyze_symbol_outputs_required_report_fields():
    config = make_config()
    daily = price_frame()
    market = build_market_context({"SPY": daily, "QQQ": daily, "SMH": daily})
    news = NewsBundle([], [], {"score": 0.3, "label": "偏多", "sample_size": 3})
    result = analyze_symbol(
        "NVDA",
        daily,
        None,
        FundamentalsData(recommendation_key="buy", revenue_growth=0.2),
        None,
        news,
        market,
        config,
    )

    assert result.symbol == "NVDA"
    assert result.score > 0
    assert result.market_regime in {"风险偏好", "中性震荡", "风险规避"}
    assert result.entry_zone
    assert result.stop
    assert result.targets
    assert result.position_pct >= 0
    assert result.max_loss_pct >= 0
    assert result.reasons
    assert "trend" in result.contributions


def test_daily_report_contains_stock_pool_and_trade_plan():
    config = make_config()
    daily = price_frame()
    market = build_market_context({"SPY": daily, "QQQ": daily, "SMH": daily})
    news = NewsBundle([], [], {"score": 0.0, "label": "中性", "sample_size": 0})
    results = [
        analyze_symbol("NVDA", daily, None, FundamentalsData(), None, news, market, config),
        analyze_symbol("MSFT", daily * 1.01, None, FundamentalsData(), None, news, market, config),
    ]
    results = enforce_portfolio_heat(assign_ranks(results), config.portfolio_heat_max_pct)

    subject, body = compose_daily_report(results, market, config, datetime(2026, 4, 20, 7, 30, tzinfo=SYDNEY_TZ))

    assert "Test 简报" in subject
    assert "股票池排序总览" in body
    assert "高优先级交易计划" in body
    assert "rank | symbol | signal_type | score" in body
    assert "position_pct" in body
