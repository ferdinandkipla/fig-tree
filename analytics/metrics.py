# analytics/metrics.py
import pandas as pd

def expectancy(trades: pd.DataFrame) -> float:
    wins   = trades[trades["pnl"] > 0]
    losses = trades[trades["pnl"] <= 0]
    wr     = len(wins) / len(trades)
    aw     = wins["pnl"].mean()   if len(wins)   > 0 else 0
    al     = losses["pnl"].mean() if len(losses) > 0 else 0
    return round(wr * aw + (1 - wr) * al, 4)

def yearly_breakdown(trades: pd.DataFrame) -> pd.DataFrame:
    df = trades.copy()
    df["year"] = pd.to_datetime(df["exit_dt"]).dt.year
    return df.groupby("year").agg(
        trades    = ("pnl", "count"),
        total_pnl = ("pnl", "sum"),
        win_rate  = ("pnl", lambda x: round((x > 0).mean() * 100, 1)),
    ).round(2)

def duration_analysis(trades: pd.DataFrame) -> dict:
    wins   = trades[trades["pnl"] > 0]
    losses = trades[trades["pnl"] <= 0]
    return {
        "avg_bars_all":    round(trades["bars_held"].mean(), 1),
        "avg_bars_wins":   round(wins["bars_held"].mean(), 1)   if len(wins)   > 0 else 0,
        "avg_bars_losses": round(losses["bars_held"].mean(), 1) if len(losses) > 0 else 0,
        "max_bars":        int(trades["bars_held"].max()),
        "time_exits":      int((trades["exit_reason"] == "time_exit").sum()),
        "ambiguous_fills": int((trades["exit_reason"] == "stop_loss_ambiguous").sum()),
    }

def exit_reason_breakdown(trades: pd.DataFrame) -> pd.DataFrame:
    return trades.groupby("exit_reason").agg(
        count     = ("pnl", "count"),
        total_pnl = ("pnl", "sum"),
        avg_pnl   = ("pnl", "mean"),
    ).round(2)