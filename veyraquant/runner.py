from .config import AppConfig
from .data import DataClient
from .emailer import send_email
from .market import build_market_context
from .models import SymbolData
from .reporting import compose_alert_email, compose_daily_report
from .signals import analyze_symbol, assign_ranks, enforce_portfolio_heat
from .state import (
    alert_in_cooldown,
    already_sent_daily,
    mark_alert_sent,
    mark_daily_sent,
    read_state,
    write_state,
)
from .timeutils import daily_report_due, is_regular_us_market_hours, now_sydney, now_us_eastern


def run(config: AppConfig | None = None) -> int:
    config = config or AppConfig.from_env()
    now_dt = now_sydney()
    state = read_state(config.state_path)
    daily_due = config.force_daily_report or (
        daily_report_due(now_dt, config.send_hour, config.send_minute, config.send_window_minutes)
        and not already_sent_daily(state, now_dt)
    )
    alerts_due = config.entry_alerts_enabled and is_regular_us_market_hours(now_us_eastern())
    if not daily_due and not alerts_due:
        print("Daily report skipped: before send threshold or already sent today.")
        print("Entry alerts skipped: outside regular US market hours or disabled.")
        print("Nothing sent; state unchanged.")
        return 0

    client = DataClient(config)

    market_histories = {}
    for symbol in config.market_symbols:
        market_histories[symbol] = client.fetch_market_daily(symbol)
    market = build_market_context(market_histories)

    symbol_data_items = [client.fetch_symbol(symbol) for symbol in config.symbols]
    results = build_results(symbol_data_items, market, config)

    sent_any = False
    changed = False
    daily_sent, daily_changed = maybe_send_daily_report(state, now_dt, results, market, config)
    if daily_sent:
        sent_any = True
    if daily_changed:
        changed = True
    if maybe_send_entry_alerts(state, now_dt, results, config):
        sent_any = True
        changed = True

    if changed and not config.dry_run:
        write_state(config.state_path, state)
        print("State updated.")
    elif config.dry_run:
        print("DRY_RUN enabled; state unchanged.")
    elif sent_any:
        print("Send completed; state unchanged.")
    else:
        print("Nothing sent; state unchanged.")
    return 0


def build_results(symbol_data_items: list[SymbolData], market, config: AppConfig):
    results = [
        analyze_symbol(
            item.symbol,
            item.daily,
            item.intraday,
            item.fundamentals,
            item.options,
            item.news,
            market,
            config,
            item.warnings,
        )
        for item in symbol_data_items
    ]
    ranked = assign_ranks(results)
    return enforce_portfolio_heat(ranked, config.portfolio_heat_max_pct)


def maybe_send_daily_report(state, now_dt, results, market, config: AppConfig) -> tuple[bool, bool]:
    if not config.force_daily_report and not daily_report_due(
        now_dt, config.send_hour, config.send_minute, config.send_window_minutes
    ):
        print("Daily report skipped: before send threshold.")
        return False, False
    if not config.force_daily_report and already_sent_daily(state, now_dt):
        print("Daily report skipped: already sent today.")
        return False, False

    subject, body = compose_daily_report(results, market, config, now_dt)
    if config.dry_run:
        print(subject)
        print(body)
        return False, False

    send_email(config.smtp, subject, body)
    if config.force_daily_report:
        print("Daily report force-sent without updating daily state.")
        return True, False

    mark_daily_sent(state, now_dt)
    print("Daily report sent.")
    return True, True


def maybe_send_entry_alerts(state, now_dt, results, config: AppConfig) -> bool:
    if not config.entry_alerts_enabled:
        print("Entry alerts disabled.")
        return False
    if not is_regular_us_market_hours(now_us_eastern()):
        print("Entry alerts skipped: outside regular US market hours.")
        return False

    sent_any = False
    for result in results:
        if not _should_alert(result, config):
            continue
        if alert_in_cooldown(
            state, result.symbol, result.alert_kind, now_dt, config.alert_cooldown_hours
        ):
            print(f"Alert skipped due to cooldown: {result.symbol} {result.alert_kind}")
            continue

        subject, body = compose_alert_email(result, now_dt)
        if config.dry_run:
            print(subject)
            print(body)
            continue

        send_email(config.smtp, subject, body)
        mark_alert_sent(
            state,
            result.symbol,
            result.alert_kind,
            now_dt,
            {
                "score": result.score,
                "signal_hash": result.signal_hash,
                "plan": {
                    "entry_zone": result.entry_zone,
                    "stop": result.stop,
                    "targets": result.targets,
                    "position_pct": result.position_pct,
                    "max_loss_pct": result.max_loss_pct,
                },
            },
        )
        sent_any = True
        print(f"Alert sent: {result.symbol} {result.alert_kind}")

    if not sent_any:
        print("No alert sent.")
    return sent_any


def _should_alert(result, config: AppConfig) -> bool:
    if result.alert_kind in {"breakout_entry", "pullback_add"}:
        return result.score >= config.alert_score_threshold
    if result.alert_kind == "risk_reduce":
        return result.score <= 40
    return False
