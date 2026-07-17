# analytics/regime_analysis.py
import os
import pandas as pd


def by_session(trades: pd.DataFrame) -> pd.DataFrame:
    return _breakdown(trades, "session")


def by_year(trades: pd.DataFrame) -> pd.DataFrame:
    return _breakdown(trades, "year")


def by_exit(trades: pd.DataFrame) -> pd.DataFrame:
    return _breakdown(trades, "exit_reason")


def by_adx_bucket(trades: pd.DataFrame) -> pd.DataFrame:
    df = trades.copy()
    df["adx_bucket"] = pd.cut(
        df["adx_entry"],
        bins  = [0, 20, 25, 35, 100],
        labels= ["<20 weak", "20-25 marginal", "25-35 strong", ">35 very strong"]
    )
    return _breakdown(df, "adx_bucket")


def by_atr_regime(trades: pd.DataFrame) -> pd.DataFrame:
    df = trades.copy()
    low  = df["atr_entry"].quantile(0.33)
    high = df["atr_entry"].quantile(0.67)

    def label(v):
        if v <= low:  return "low_vol"
        if v <= high: return "med_vol"
        return "high_vol"

    df["atr_regime"] = df["atr_entry"].apply(label)
    return _breakdown(df, "atr_regime")


def _breakdown(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    results = []
    for name, group in df.groupby(group_col):
        wins   = group[group["pnl"] > 0]
        losses = group[group["pnl"] <= 0]
        pf     = (wins["pnl"].sum() / abs(losses["pnl"].sum())
                  if losses["pnl"].sum() != 0 else 999)
        results.append({
            group_col:   name,
            "trades":    len(group),
            "win_rate":  round(len(wins) / len(group) * 100, 1),
            "total_pnl": round(group["pnl"].sum(), 2),
            "avg_pnl":   round(group["pnl"].mean(), 2),
            "avg_win":   round(wins["pnl"].mean(), 2)   if len(wins)   > 0 else 0,
            "avg_loss":  round(losses["pnl"].mean(), 2) if len(losses) > 0 else 0,
            "pf":        round(pf, 2),
        })
    df_out = pd.DataFrame(results).set_index(group_col)
    return df_out.sort_values("total_pnl", ascending=False)


def full_regime_report(trades: pd.DataFrame, symbol: str):
    sep  = "=" * 62
    sep2 = "-" * 62

    print(f"\n{sep}")
    print(f"  REGIME ANALYSIS  |  {symbol}")
    print(f"{sep}")

    sections = [
        ("BY SESSION",    by_session(trades)),
        ("BY ADX BUCKET", by_adx_bucket(trades)),
        ("BY ATR REGIME", by_atr_regime(trades)),
        ("BY YEAR",       by_year(trades)),
        ("BY EXIT TYPE",  by_exit(trades)),
    ]

    for title, df in sections:
        print(f"\n  {title}")
        print(f"  {sep2}")
        if df.empty:
            print("  No data.")
            continue
        print(f"  {df.index.name or 'group':<18} "
              f"{'trades':>7} {'wr%':>6} {'total_pnl':>11} "
              f"{'avg_pnl':>9} {'pf':>6}")
        print(f"  {'-'*18} {'-'*7} {'-'*6} {'-'*11} {'-'*9} {'-'*6}")
        for name, row in df.iterrows():
            flag = " ◄" if row["win_rate"] < 30 or row["pf"] < 0.8 else ""
            print(f"  {str(name):<18} "
                  f"{int(row['trades']):>7} "
                  f"{row['win_rate']:>5.1f}% "
                  f"${row['total_pnl']:>10,.2f} "
                  f"${row['avg_pnl']:>8,.2f} "
                  f"{row['pf']:>6.2f}{flag}")

    os.makedirs("research", exist_ok=True)
    for title, df in sections:
        fname = title.lower().replace(" ", "_")
        df.to_csv(f"research/regime_{fname}_{symbol}.csv")

    print(f"\n  Saved → research/regime_*_{symbol}.csv")
    print(f"{sep}\n")