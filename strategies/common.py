# strategies/common.py
#
# M2: shared feature/geometry computation. Both trend_pullback and
# null_random call this so they are IDENTICAL in everything except
# entry selection -- the whole point of a null model comparison is
# that it isolates that one variable. If each strategy computed its
# own ATR/stop/target independently, any future drift between them
# would confound the comparison silently.

import pandas as pd
from indicators.trend import ema, adx
from indicators.volatility import atr
from strategies.trend_pullback.params import (
    EMA_FAST, EMA_SLOW, ADX_PERIOD, ATR_PERIOD,
    STOP_ATR_MULT, RISK_REWARD
)

WARMUP_BARS = max(EMA_SLOW, ATR_PERIOD, ADX_PERIOD)


def compute_common_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds ema_fast/ema_slow/adx/atr/ema_distance/trend_gap and the
    execution-contract stop_distance/target_distance columns. Does NOT
    add 'signal' -- that's the one thing each strategy decides for
    itself. Does NOT strip warmup or dropna -- callers do that after
    adding their own signal column, so warmup-bar signal counts are
    computed consistently.

    Returns a new copy; never mutates the input.
    """
    df = df.copy()

    df["ema_fast"] = ema(df["close"], EMA_FAST)
    df["ema_slow"] = ema(df["close"], EMA_SLOW)
    df["adx"]      = adx(df["high"], df["low"], df["close"], ADX_PERIOD)
    df["atr"]      = atr(df["high"], df["low"], df["close"], ATR_PERIOD)

    df["ema_distance"] = (df["close"] - df["ema_fast"]) / df["atr"]      # pullback depth, ATR units
    df["trend_gap"]    = (df["ema_fast"] - df["ema_slow"]) / df["atr"]  # trend maturity, ATR units

    # Execution-contract columns: price-unit distances the simulator
    # re-anchors onto the real entry price. Identical formula for every
    # strategy that wants to be null-model-comparable to trend_pullback.
    df["stop_distance"]   = STOP_ATR_MULT * df["atr"]
    df["target_distance"] = RISK_REWARD * STOP_ATR_MULT * df["atr"]

    return df
