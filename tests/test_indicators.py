import numpy as np
import pandas as pd

from shortreport.indicators import adx, atr, bollinger_bands, macd, rsi, volume_ratio


def test_indicators_return_aligned_series():
    close = pd.Series(np.linspace(100, 140, 80))
    high = close + 2
    low = close - 2
    volume = pd.Series(np.linspace(1_000_000, 1_500_000, 80))

    rsi_series = rsi(close)
    macd_line, signal_line, hist = macd(close)
    sma, upper, lower = bollinger_bands(close)
    atr_series = atr(high, low, close)
    plus_di, minus_di, adx_series = adx(high, low, close)
    vol_ratio = volume_ratio(volume)

    assert len(rsi_series) == len(close)
    assert len(macd_line) == len(close)
    assert len(signal_line) == len(close)
    assert len(hist) == len(close)
    assert upper.iloc[-1] > sma.iloc[-1] > lower.iloc[-1]
    assert atr_series.iloc[-1] > 0
    assert plus_di.iloc[-1] >= 0
    assert minus_di.iloc[-1] >= 0
    assert adx_series.iloc[-1] >= 0
    assert vol_ratio.iloc[-1] > 0
