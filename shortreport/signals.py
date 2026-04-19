import hashlib
import math
from typing import Optional

import numpy as np
import pandas as pd

from .config import AppConfig
from .indicators import adx, atr, bollinger_bands, macd, pct_change, rsi, volume_ratio
from .models import (
    FundamentalsData,
    MarketContext,
    NewsBundle,
    OptionsData,
    SignalResult,
    TechSnapshot,
    TradePlan,
)
from .risk import portfolio_heat_cap, position_size_pct


def tech_summary(hist: pd.DataFrame) -> TechSnapshot:
    close = hist["Close"]
    high = hist["High"]
    low = hist["Low"]
    volume = hist["Volume"]

    last = float(close.iloc[-1])
    prev = float(close.iloc[-2])
    chg = last - prev
    chg_pct = chg / prev * 100

    sma20_series = close.rolling(20).mean()
    sma50_series = close.rolling(50).mean()
    sma200_series = close.rolling(200).mean()
    rsi_series = rsi(close)
    macd_line, signal_line, hist_line = macd(close)
    bb_sma, bb_upper, bb_lower = bollinger_bands(close)
    atr14_series = atr(high, low, close)
    plus_di, minus_di, adx_series = adx(high, low, close)
    vol_ratio_series = volume_ratio(volume)

    values = {
        "last": last,
        "prev": prev,
        "chg": chg,
        "chg_pct": chg_pct,
        "sma20": float(sma20_series.iloc[-1]),
        "sma50": float(sma50_series.iloc[-1]),
        "sma200": float(sma200_series.iloc[-1]) if len(close) >= 200 else float("nan"),
        "sma20_prev": float(sma20_series.iloc[-2]),
        "sma50_prev": float(sma50_series.iloc[-2]),
        "rsi14": float(rsi_series.iloc[-1]),
        "rsi14_prev": float(rsi_series.iloc[-2]),
        "macd": float(macd_line.iloc[-1]),
        "signal": float(signal_line.iloc[-1]),
        "macd_hist": float(hist_line.iloc[-1]),
        "macd_hist_prev": float(hist_line.iloc[-2]),
        "high_20": float(close.rolling(20).max().iloc[-1]),
        "low_20": float(close.rolling(20).min().iloc[-1]),
        "high_55": float(close.rolling(55).max().iloc[-1]),
        "low_55": float(close.rolling(55).min().iloc[-1]),
        "bb_upper": float(bb_upper.iloc[-1]),
        "bb_lower": float(bb_lower.iloc[-1]),
        "bb_sma": float(bb_sma.iloc[-1]),
        "bb_width": float((bb_upper.iloc[-1] - bb_lower.iloc[-1]) / (bb_sma.iloc[-1] + 1e-9)),
        "atr14": float(atr14_series.iloc[-1]),
        "atr_pct": float(atr14_series.iloc[-1] / (last + 1e-9) * 100),
        "plus_di": float(plus_di.iloc[-1]),
        "minus_di": float(minus_di.iloc[-1]),
        "adx14": float(adx_series.iloc[-1]),
        "vol_ratio": float(vol_ratio_series.iloc[-1]),
        "perf20": pct_change(close, 20),
        "perf55": pct_change(close, 55),
    }
    return TechSnapshot(values)


def intraday_snapshot(intraday: Optional[pd.DataFrame]) -> Optional[dict[str, float]]:
    if intraday is None or intraday.empty:
        return None
    intraday = intraday.copy()
    close = intraday["Close"]
    volume = intraday["Volume"]
    latest = intraday.iloc[-1]
    prev = intraday.iloc[-2] if len(intraday) >= 2 else latest
    rolling_high = close.rolling(min(13, len(close))).max().iloc[-1]
    rolling_low = close.rolling(min(13, len(close))).min().iloc[-1]
    intraday_vol_ratio = volume.iloc[-1] / (volume.tail(min(20, len(volume))).mean() + 1e-9)
    return {
        "price": float(latest["Close"]),
        "open": float(latest["Open"]),
        "high": float(latest["High"]),
        "low": float(latest["Low"]),
        "prev_close": float(prev["Close"]),
        "chg_pct": float((latest["Close"] - prev["Close"]) / (prev["Close"] + 1e-9) * 100),
        "high_13": float(rolling_high),
        "low_13": float(rolling_low),
        "vol_ratio": float(intraday_vol_ratio),
    }


def analyze_symbol(
    symbol: str,
    daily: Optional[pd.DataFrame],
    intraday: Optional[pd.DataFrame],
    fundamentals: FundamentalsData,
    options: Optional[OptionsData],
    news: NewsBundle,
    market: MarketContext,
    config: AppConfig,
    warnings: Optional[list[str]] = None,
) -> SignalResult:
    warnings = list(warnings or [])
    if daily is None or daily.empty or len(daily) < 60:
        plan = TradePlan("等待数据恢复", "NA", "NA", 0.0, 0.0, 0.0, "无", "数据不足")
        return _result(
            rank=0,
            symbol=symbol,
            signal_type="禁止交易/等待",
            score=0,
            market_regime=market.label,
            plan=plan,
            reasons=["日线数据不足，无法生成可靠交易计划"],
            risks=warnings or ["行情数据不可用"],
            contributions={},
            alert_kind="wait",
            last_price=None,
        )

    tech = tech_summary(daily)
    intraday_data = intraday_snapshot(intraday)
    contributions, reasons, risks = score_components(
        symbol, tech, fundamentals, options, news, market, config.social_sentiment_threshold
    )
    raw_score = sum(contributions.values())
    score = int(max(0, min(100, round(raw_score))))

    signal_type, alert_kind = choose_signal_type(tech, intraday_data, score, market, config)
    plan = build_trade_plan(signal_type, tech, config)
    if plan.rr < config.min_rr and plan.position_pct > 0:
        risks.append(f"盈亏比 {plan.rr:.2f} 低于最低要求 {config.min_rr:.2f}")
        if signal_type in {"突破入场", "趋势回踩加仓"}:
            signal_type = "持有观察"
            alert_kind = "hold_watch"

    if warnings:
        risks.extend(warnings[:3])

    return _result(
        rank=0,
        symbol=symbol,
        signal_type=signal_type,
        score=score,
        market_regime=market.label,
        plan=plan,
        reasons=reasons[:8],
        risks=risks[:8],
        contributions=contributions,
        alert_kind=alert_kind,
        last_price=tech.values["last"],
        warnings=warnings,
    )


def score_components(
    symbol: str,
    tech: TechSnapshot,
    fundamentals: FundamentalsData,
    options: Optional[OptionsData],
    news: NewsBundle,
    market: MarketContext,
    social_sentiment_threshold: float = 0.15,
) -> tuple[dict[str, float], list[str], list[str]]:
    t = tech.values
    contributions: dict[str, float] = {}
    reasons: list[str] = []
    risks: list[str] = []

    trend = 0.0
    if t["last"] > t["sma20"] > t["sma50"]:
        trend += 18
        reasons.append("价格站上 SMA20 与 SMA50，短中期趋势保持多头结构")
    elif t["last"] > t["sma20"]:
        trend += 8
        reasons.append("价格高于 SMA20，但趋势强度仍需继续确认")
    else:
        trend -= 8
        risks.append("价格跌回 SMA20 下方，趋势延续性转弱")
    if not math.isnan(t["sma200"]) and t["last"] > t["sma200"]:
        trend += 8
        reasons.append("价格位于 SMA200 上方，长期趋势仍偏强")
    if t["last"] >= t["high_55"] * 0.98:
        trend += 6
        reasons.append("价格接近 55 日高点，波段趋势有延续特征")
    contributions["trend"] = trend

    momentum = 0.0
    if t["macd"] > t["signal"] and t["macd_hist"] > t["macd_hist_prev"]:
        momentum += 12
        reasons.append("MACD 位于信号线之上且柱体扩张，动能增强")
    elif t["macd"] > t["signal"]:
        momentum += 6
    else:
        momentum -= 6
        risks.append("MACD 位于信号线下方，动能偏弱")
    if 45 <= t["rsi14"] <= 68:
        momentum += 10
        reasons.append("RSI 位于健康强势区间，尚未明显过热")
    elif t["rsi14"] > 72:
        momentum -= 7
        risks.append("RSI 已进入过热区，追涨性价比下降")
    elif t["rsi14"] < 40:
        momentum -= 10
        risks.append("RSI 偏弱，说明多头承接不足")
    if t["adx14"] >= 25 and t["plus_di"] > t["minus_di"]:
        momentum += 10
        reasons.append("ADX 超过 25 且 +DI 领先，趋势具备持续性")
    contributions["momentum"] = momentum

    relative = 5.0
    spy_perf = _snapshot_perf(market, "SPY")
    qqq_perf = _snapshot_perf(market, "QQQ")
    benchmark_values = [value for value in [spy_perf, qqq_perf] if not math.isnan(value)]
    benchmark = float(np.mean(benchmark_values)) if benchmark_values else float("nan")
    if not math.isnan(t["perf20"]) and not math.isnan(benchmark):
        spread = t["perf20"] - benchmark
        relative += float(np.clip(spread, -10, 10))
        if spread >= 3:
            reasons.append(f"{symbol} 20 日表现强于 SPY/QQQ，存在相对强势")
        elif spread <= -3:
            risks.append(f"{symbol} 20 日表现弱于 SPY/QQQ，资金强度不足")
    contributions["relative_strength"] = relative

    volume = 0.0
    if t["vol_ratio"] >= 1.5:
        volume += 10
        reasons.append("成交量显著高于 20 日均量，信号确认度较高")
    elif t["vol_ratio"] >= 1.1:
        volume += 5
        reasons.append("成交量温和放大")
    elif t["vol_ratio"] < 0.7:
        volume -= 4
        risks.append("成交量低于均量，突破确认度不足")
    contributions["volume"] = volume

    vol_opt = 5.0
    if t["atr_pct"] > 6:
        vol_opt -= 6
        risks.append("ATR 占价格比例偏高，仓位需要收缩")
    if options and options.iv_mid is not None:
        if options.iv_mid >= 0.65:
            vol_opt -= 8
            risks.append("隐含波动率偏高，事件风险定价较重")
        elif options.iv_mid <= 0.4:
            vol_opt += 3
    if options and options.put_call_vol is not None:
        if options.put_call_vol >= 1.3:
            vol_opt -= 5
            risks.append("Put/Call 成交量比偏高，期权情绪谨慎")
        elif options.put_call_vol <= 0.7:
            vol_opt += 4
            reasons.append("Put/Call 成交量比偏低，期权情绪偏多")
    contributions["volatility_options"] = vol_opt

    sentiment = 0.0
    social_score = news.social_sentiment.get("score", 0.0)
    if social_score >= social_sentiment_threshold:
        sentiment += 8
        reasons.append("公开新闻/社媒标题情绪偏多")
    elif social_score <= -social_sentiment_threshold:
        sentiment -= 8
        risks.append("公开新闻/社媒标题情绪偏空")
    if news.news:
        sentiment += 2
    contributions["news_sentiment"] = sentiment

    event_risk = 0.0
    recommendation = fundamentals.recommendation_key
    if recommendation in {"buy", "strong_buy"}:
        event_risk += 4
    elif recommendation in {"sell", "underperform"}:
        event_risk -= 8
        risks.append("分析师一致预期偏弱，不支持激进加仓")
    if fundamentals.revenue_growth is not None and fundamentals.revenue_growth < 0:
        event_risk -= 4
        risks.append("收入增长为负，基本面动能需要重新确认")
    contributions["event_risk"] = event_risk

    market_score = float(np.clip(market.score, -15, 15))
    contributions["market_environment"] = market_score
    if market.label == "风险偏好":
        reasons.append("市场过滤显示风险偏好较好")
    elif market.label == "风险规避":
        risks.append("市场过滤处于风险规避状态，降低进攻性")

    base = 35.0
    contributions["base"] = base
    return contributions, reasons, risks


def choose_signal_type(
    tech: TechSnapshot,
    intraday: Optional[dict[str, float]],
    score: int,
    market: MarketContext,
    config: AppConfig,
) -> tuple[str, str]:
    t = tech.values
    breakout = t["last"] >= t["high_20"] * 0.995
    pullback_distance = abs(t["last"] - t["sma20"]) / (t["atr14"] + 1e-9)
    pullback = t["last"] > t["sma20"] and pullback_distance <= 0.9 and 42 <= t["rsi14"] <= 62
    intraday_breakout = bool(
        intraday
        and intraday["price"] >= intraday["high_13"] * 0.998
        and intraday["vol_ratio"] >= 1.15
    )

    if market.label == "风险规避" and score < config.alert_score_threshold + 5:
        return "禁止交易/等待", "wait"
    if score >= config.alert_score_threshold and (breakout or intraday_breakout):
        return "突破入场", "breakout_entry"
    if score >= config.alert_score_threshold - 5 and pullback:
        return "趋势回踩加仓", "pullback_add"
    if score >= 55:
        return "持有观察", "hold_watch"
    if score <= 40 or t["rsi14"] > 74:
        return "减仓/风险升高", "risk_reduce"
    return "禁止交易/等待", "wait"


def build_trade_plan(signal_type: str, tech: TechSnapshot, config: AppConfig) -> TradePlan:
    t = tech.values
    last = t["last"]
    atr14 = max(t["atr14"], last * 0.01)

    if signal_type == "突破入场":
        entry_low = last
        entry_high = last + 0.25 * atr14
        trigger = "日线收盘维持 20 日高点附近，盘中量比不低于 1.1"
        cancel = "收盘跌回 SMA20 下方或市场过滤转为风险规避"
    elif signal_type == "趋势回踩加仓":
        entry_low = max(0.01, t["sma20"] - 0.25 * atr14)
        entry_high = t["sma20"] + 0.25 * atr14
        trigger = "价格回踩 SMA20 附近后企稳，RSI 不跌破 42"
        cancel = "收盘跌破 SMA20 且 MACD 柱体继续走弱"
    elif signal_type == "持有观察":
        entry_low = min(last, t["sma20"])
        entry_high = last
        trigger = "已有仓位可按计划持有，新仓等待突破或回踩确认"
        cancel = "跌破 SMA20 或市场风险快速升高"
    elif signal_type == "减仓/风险升高":
        entry_low = last
        entry_high = last
        trigger = "控制风险为主，避免新增仓位"
        cancel = "重新站上 SMA20 且评分恢复到 55 以上"
    else:
        entry_low = last
        entry_high = last
        trigger = "等待更清晰的趋势、量能或市场环境确认"
        cancel = "无"

    entry_mid = (entry_low + entry_high) / 2
    stop = max(0.01, entry_mid - config.atr_stop_multiplier * atr14)
    risk_per_share = entry_mid - stop
    target1 = entry_mid + config.min_rr * risk_per_share
    target2 = entry_mid + max(config.min_rr + 1.0, 2.5) * risk_per_share
    rr = (target1 - entry_mid) / (risk_per_share + 1e-9)

    actionable = signal_type in {"突破入场", "趋势回踩加仓", "持有观察"}
    sizing = position_size_pct(
        entry_mid,
        stop,
        config.risk_per_trade_pct,
        config.max_position_pct,
        config.account_equity,
    )
    position_pct = sizing.position_pct if actionable else 0.0
    max_loss_pct = sizing.max_loss_pct if actionable else 0.0
    position_value = sizing.position_value if actionable else None

    return TradePlan(
        entry_zone=f"${entry_low:.2f} - ${entry_high:.2f}",
        stop=f"${stop:.2f}",
        targets=f"${target1:.2f} / ${target2:.2f}",
        position_pct=position_pct,
        max_loss_pct=max_loss_pct,
        rr=round(rr, 2),
        trigger=trigger,
        cancel=cancel,
        account_equity=config.account_equity,
        position_value=position_value,
    )


def assign_ranks(results: list[SignalResult]) -> list[SignalResult]:
    sorted_results = sorted(results, key=lambda item: item.score, reverse=True)
    for idx, result in enumerate(sorted_results, start=1):
        result.rank = idx
    return sorted_results


def enforce_portfolio_heat(results: list[SignalResult], max_heat_pct: float) -> list[SignalResult]:
    heat_left = max_heat_pct
    for result in results:
        if result.max_loss_pct <= 0 or result.position_pct <= 0:
            continue
        new_position, new_loss = portfolio_heat_cap(
            result.position_pct, result.max_loss_pct, max(0.0, heat_left)
        )
        if new_loss < result.max_loss_pct:
            result.risks.append("组合风险预算不足，建议仓位已按 portfolio heat 上限收缩")
            result.position_pct = new_position
            result.max_loss_pct = new_loss
            result.trade_plan.position_pct = new_position
            result.trade_plan.max_loss_pct = new_loss
            if result.trade_plan.account_equity is not None:
                result.trade_plan.position_value = result.trade_plan.account_equity * new_position / 100
        heat_left -= result.max_loss_pct
    return results


def _snapshot_perf(market: MarketContext, symbol: str) -> float:
    snapshot = market.snapshots.get(symbol, {})
    value = snapshot.get("perf20")
    try:
        return float(value)
    except Exception:
        return float("nan")


def _result(
    rank: int,
    symbol: str,
    signal_type: str,
    score: int,
    market_regime: str,
    plan: TradePlan,
    reasons: list[str],
    risks: list[str],
    contributions: dict[str, float],
    alert_kind: str,
    last_price: Optional[float],
    warnings: Optional[list[str]] = None,
) -> SignalResult:
    hash_input = f"{symbol}|{signal_type}|{score}|{plan.entry_zone}|{plan.stop}|{plan.targets}"
    signal_hash = hashlib.sha1(hash_input.encode("utf-8")).hexdigest()[:12]
    return SignalResult(
        rank=rank,
        symbol=symbol,
        signal_type=signal_type,
        score=score,
        market_regime=market_regime,
        entry_zone=plan.entry_zone,
        stop=plan.stop,
        targets=plan.targets,
        position_pct=plan.position_pct,
        max_loss_pct=plan.max_loss_pct,
        reasons=reasons,
        risks=risks,
        contributions=contributions,
        trade_plan=plan,
        alert_kind=alert_kind,
        signal_hash=signal_hash,
        last_price=last_price,
        warnings=warnings or [],
    )
