# strategies/trend_pullback/filters.py
import pandas as pd


def trend_up(df: pd.DataFrame) -> pd.Series:
    return df["ema_fast"] > df["ema_slow"]


def trend_strong(df: pd.DataFrame, threshold: float) -> pd.Series:
    return df["adx"] > threshold


def at_pullback(df: pd.DataFrame, tolerance: float) -> pd.Series:
    return df["close"] <= (df["ema_fast"] + tolerance * df["atr"])


def adx_not_overextended(df: pd.DataFrame, ceiling: float = 28.0) -> pd.Series:
    """
    ADX ceiling filter.
    Evidence: ADX 25-35 bucket loses on all 3 instruments.
    Ceiling=28 keeps the edge zone (20-25), cuts the bleed zone (25-35).
    """
    return df["adx"] <= ceiling


def bullish_close(df: pd.DataFrame) -> pd.Series:
    return df["close"] > df["open"]


def ema_rising(df: pd.DataFrame, bars: int = 3) -> pd.Series:
    return df["ema_fast"] > df["ema_fast"].shift(bars)


def not_extended(df: pd.DataFrame, atr_mult: float = 2.0) -> pd.Series:
    return abs(df["close"] - df["ema_fast"]) <= (df["atr"] * atr_mult)


def rejection_candle(df: pd.DataFrame) -> pd.Series:
    prev_dipped = df["low"].shift(1) < df["ema_fast"].shift(1)
    close_above = df["close"] > df["ema_fast"]
    bullish     = df["close"] > df["open"]
    return prev_dipped & close_above & bullish