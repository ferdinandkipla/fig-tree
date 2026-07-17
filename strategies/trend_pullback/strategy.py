# strategies/trend_pullback/strategy.py
import pandas as pd
from indicators.trend import ema, adx
from indicators.volatility import atr
from strategies.trend_pullback.signals import entry_signal
from strategies.trend_pullback.params import (
    EMA_FAST, EMA_SLOW, ADX_PERIOD, ATR_PERIOD,
    STOP_ATR_MULT, RISK_REWARD
)

WARMUP_BARS = max(EMA_SLOW, ATR_PERIOD, ADX_PERIOD)


def prepare(df: pd.DataFrame, symbol: str = "USDJPY") -> pd.DataFrame:
    df = df.copy()

    df["ema_fast"] = ema(df["close"], EMA_FAST)
    df["ema_slow"] = ema(df["close"], EMA_SLOW)
    df["adx"]      = adx(df["high"], df["low"], df["close"], ADX_PERIOD)
    df["atr"]      = atr(df["high"], df["low"], df["close"], ATR_PERIOD)

    df["signal"]      = entry_signal(df, symbol=symbol)
    df["stop_loss"]   = df["close"] - (STOP_ATR_MULT * df["atr"])
    df["take_profit"] = df["close"] + (RISK_REWARD * STOP_ATR_MULT * df["atr"])

    df = df.iloc[WARMUP_BARS:].copy()
    print(f"[Strategy] Warmup stripped: {WARMUP_BARS} bars | "
          f"Remaining: {len(df)} | Signals: {df['signal'].sum()}")

    return df.dropna()