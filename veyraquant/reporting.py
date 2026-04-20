from datetime import datetime

from .config import AppConfig
from .models import MarketContext, SignalResult


def format_money(value) -> str:
    if value is None:
        return "NA"
    try:
        value = float(value)
    except Exception:
        return "NA"
    if abs(value) >= 1e12:
        return f"{value / 1e12:.2f}T"
    if abs(value) >= 1e9:
        return f"{value / 1e9:.2f}B"
    if abs(value) >= 1e6:
        return f"{value / 1e6:.2f}M"
    return f"{value:.2f}"


def compose_daily_report(
    results: list[SignalResult],
    market: MarketContext,
    config: AppConfig,
    now_dt: datetime,
) -> tuple[str, str]:
    subject = f"{config.subject_prefix} - {now_dt.strftime('%Y-%m-%d')}"
    lines: list[str] = [
        f"VeyraQuant 股票池量化简报 ({now_dt.strftime('%Y-%m-%d %H:%M')} Sydney)",
        "",
        "[市场过滤]",
        f"市场状态: {market.label} (score {market.score:+.1f})",
        *[f"- {reason}" for reason in market.reasons[:4]],
    ]
    if market.risks:
        lines.extend(["", "[市场风险]", *[f"- {risk}" for risk in market.risks[:4]]])

    lines.extend(["", "[股票池排序总览]"])
    lines.extend(
        [
            "rank | symbol | signal_type | score | market_regime | entry_zone | stop | targets | position_pct | max_loss_pct",
        ]
    )
    for result in results:
        lines.append(
            f"{result.rank} | {result.symbol} | {result.signal_type} | {result.score} | "
            f"{result.market_regime} | {result.entry_zone} | {result.stop} | {result.targets} | "
            f"{result.position_pct:.2f}% | {result.max_loss_pct:.2f}%"
        )

    lines.extend(["", "[高优先级交易计划]"])
    high_priority = [item for item in results if item.score >= 55 or item.signal_type != "禁止交易/等待"]
    if not high_priority:
        lines.append("当前没有达到观察阈值的标的，等待趋势、量能或市场环境改善。")
    for result in high_priority:
        lines.extend(_result_block(result))

    warnings = [warning for result in results for warning in result.warnings]
    if warnings:
        lines.extend(["", "[数据降级提示]", *[f"- {warning}" for warning in warnings[:8]]])

    lines.extend(
        [
            "",
            "[说明]",
            "本系统不接券商 API，不生成真实订单。所有仓位与交易计划仅供人工决策参考。",
            "仓位比例按账户百分比计算；未设置 ACCOUNT_EQUITY 时不输出具体金额。",
        ]
    )
    return subject, "\n".join(lines)


def compose_alert_email(result: SignalResult, now_dt: datetime) -> tuple[str, str]:
    subject = f"{result.symbol} {result.signal_type} - score {result.score}"
    lines = [
        f"{result.symbol} 机会/风险提醒 ({now_dt.strftime('%Y-%m-%d %H:%M')} Sydney)",
        "",
        f"rank: {result.rank}",
        f"symbol: {result.symbol}",
        f"signal_type: {result.signal_type}",
        f"score: {result.score}",
        f"market_regime: {result.market_regime}",
        f"entry_zone: {result.entry_zone}",
        f"stop: {result.stop}",
        f"targets: {result.targets}",
        f"position_pct: {result.position_pct:.2f}%",
        f"max_loss_pct: {result.max_loss_pct:.2f}%",
        f"trigger: {result.trade_plan.trigger}",
        f"cancel: {result.trade_plan.cancel}",
    ]
    if result.trade_plan.position_value is not None:
        lines.append(f"position_value: ${result.trade_plan.position_value:,.2f}")

    lines.extend(["", "[分项评分]"])
    lines.extend(f"- {key}: {value:+.1f}" for key, value in result.contributions.items())
    lines.extend(["", "[reasons]", *[f"- {line}" for line in result.reasons]])
    lines.extend(["", "[risks]", *[f"- {line}" for line in result.risks or ["无主要新增风险"]]])
    lines.extend(["", "提示: 该提醒用于辅助分批入场、加仓或风险控制，不代表必须立即执行。"])
    return subject, "\n".join(lines)


def _result_block(result: SignalResult) -> list[str]:
    lines = [
        "",
        f"## {result.rank}. {result.symbol} - {result.signal_type} ({result.score}/100)",
        f"rank: {result.rank}",
        f"symbol: {result.symbol}",
        f"signal_type: {result.signal_type}",
        f"score: {result.score}",
        f"market_regime: {result.market_regime}",
        f"entry_zone: {result.entry_zone}",
        f"stop: {result.stop}",
        f"targets: {result.targets}",
        f"position_pct: {result.position_pct:.2f}%",
        f"max_loss_pct: {result.max_loss_pct:.2f}%",
        f"trigger: {result.trade_plan.trigger}",
        f"cancel: {result.trade_plan.cancel}",
    ]
    if result.trade_plan.position_value is not None:
        lines.append(f"position_value: ${result.trade_plan.position_value:,.2f}")
    lines.extend(["reasons:", *[f"- {reason}" for reason in result.reasons[:5]]])
    lines.extend(["risks:", *[f"- {risk}" for risk in (result.risks[:5] or ["无主要新增风险"])]])
    return lines
