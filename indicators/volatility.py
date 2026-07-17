# indicators/volatility.py
import pandas as pd
from ta.volatility import AverageTrueRange

def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    return AverageTrueRange(high, low, close, window=period).average_true_range()