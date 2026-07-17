# indicators/trend.py
import pandas as pd
from ta.trend import EMAIndicator, ADXIndicator

def ema(series: pd.Series, period: int) -> pd.Series:
    return EMAIndicator(series, window=period).ema_indicator()

def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    return ADXIndicator(high, low, close, window=period).adx()