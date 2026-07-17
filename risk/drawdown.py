# risk/drawdown.py
import pandas as pd

def max_drawdown(equity_curve: list) -> float:
    equity = pd.Series([e["equity"] for e in equity_curve])
    peak   = equity.cummax()
    dd     = (equity - peak) / peak * 100
    return round(dd.min(), 2)

def drawdown_series(equity_curve: list) -> pd.Series:
    equity = pd.Series([e["equity"] for e in equity_curve])
    peak   = equity.cummax()
    return (equity - peak) / peak * 100