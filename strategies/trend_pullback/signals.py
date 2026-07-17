# strategies/trend_pullback/signals.py
# Revert: ADX ceiling DELETED entirely, ema_rising removed
# Reason: per-instrument ceilings = curve fitting
#         uniform ceiling = still reverse-engineered from test data
#         ema_rising = destroys sample size (290→38)
# Surviving filters: trend_up, trend_strong (ADX>20 floor), at_pullback, bullish_close

import pandas as pd
from strategies.trend_pullback.filters import (
    trend_up, trend_strong, at_pullback, bullish_close
)
from strategies.trend_pullback.params import ADX_THRESHOLD, PULLBACK_TOLERANCE


def entry_signal(df: pd.DataFrame, symbol: str = "USDJPY") -> pd.Series:
    tu = trend_up(df)
    ts = trend_strong(df, ADX_THRESHOLD)
    ap = at_pullback(df, PULLBACK_TOLERANCE)
    bc = bullish_close(df)

    print(f"[Signals] Funnel ({symbol}):")
    print(f"  trend_up           : {tu.sum():>5} bars")
    print(f"  trend_strong (>20) : {(tu & ts).sum():>5} bars")
    print(f"  at_pullback        : {(tu & ts & ap).sum():>5} bars")
    print(f"  bullish_close      : {(tu & ts & ap & bc).sum():>5} bars  ← signals")

    return (tu & ts & ap & bc).astype(int)