# indicators/momentum.py
# Phase 2+ — placeholder
import pandas as pd
from ta.momentum import RSIIndicator

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    return RSIIndicator(series, window=period).rsi()