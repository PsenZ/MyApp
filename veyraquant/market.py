import math

import numpy as np
import pandas as pd

from .indicators import pct_change
from .models import MarketContext


def _latest_close(daily: pd.DataFrame) -> float:
    return float(daily["Close"].iloc[-1])


def build_market_context(market_histories: dict[str, pd.DataFrame | None]) -> MarketContext:
    snapshots: dict[str, dict[str, float | str]] = {}
    score = 0.0
    reasons: list[str] = []
    risks: list[str] = []

    for symbol, daily in market_histories.items():
        if daily is None or daily.empty or len(daily) < 50:
            snapshots[symbol] = {"status": "missing"}
            risks.append(f"{symbol} 市场过滤数据不足")
            continue

        close = daily["Close"]
        sma20 = float(close.rolling(20).mean().iloc[-1])
        sma50 = float(close.rolling(50).mean().iloc[-1])
        perf20 = pct_change(close, 20)
        last = _latest_close(daily)
        snapshots[symbol] = {
            "last": last,
            "sma20": sma20,
            "sma50": sma50,
            "perf20": perf20,
        }

        if symbol == "^VIX":
            if last >= 28:
                score -= 20
                risks.append("VIX 高于 28，市场波动处于高风险区")
            elif last >= 22:
                score -= 10
                risks.append("VIX 高于 22，短线波动风险抬升")
            else:
                score += 8
                reasons.append("VIX 未进入高压区，风险偏好尚可")
            continue

        if last > sma20 > sma50:
            score += 12
            reasons.append(f"{symbol} 位于 SMA20/SMA50 上方，市场背景偏多")
        elif last < sma20 < sma50:
            score -= 12
            risks.append(f"{symbol} 跌破主要均线，市场背景偏弱")

        if not math.isnan(perf20):
            score += float(np.clip(perf20, -5, 5))

    if score >= 20:
        label = "风险偏好"
    elif score <= -15:
        label = "风险规避"
    else:
        label = "中性震荡"

    return MarketContext(
        label=label,
        score=round(score, 2),
        reasons=reasons or ["市场过滤未给出强方向，按中性处理"],
        risks=risks,
        snapshots=snapshots,
    )
