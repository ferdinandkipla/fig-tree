# analytics/reporting.py
import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from analytics.metrics import (
    expectancy, yearly_breakdown,
    duration_analysis, exit_reason_breakdown
)
from analytics.regime_analysis import full_regime_report

INST_COLORS = {
    "USDJPY": "#1D9E75", "XAUUSD": "#C9A84C",
    "GBPJPY": "#E24B4A", "EURUSD": "#4A90D9", "GBPUSD": "#9B59B6",
}
GREEN = "#1D9E75"
RED   = "#E24B4A"
SEP   = "=" * 62
SEP2  = "-" * 62


def print_report(name: str, results: dict, initial_capital: float = 10000.0):
    t = results.get("trades")

    print(f"\n{SEP}")
    print(f"  ZENITHFLOW  |  {name}  |  H4  |  2019–2025")
    print(f"{SEP}")
    print(f"  Starting Capital  : ${initial_capital:>10,.2f}")
    print(f"  Final Capital     : ${results['final_capital']:>10,.2f}")
    print(f"  Total Return      : {results['total_return_%']:>9.1f}%")
    print(f"  Max Drawdown      : {results['max_drawdown_%']:>9.1f}%")
    print(f"  Sharpe Ratio      : {results['sharpe_ratio']:>9.2f}  (trade-based approx)")
    print(f"{SEP2}")
    print(f"  Total Trades      : {results['total_trades']:>10}")
    print(f"  Win Rate          : {results['win_rate']:>9.1f}%")
    print(f"  Profit Factor     : {results['profit_factor']:>10.2f}")
    print(f"  Avg Win           : ${results['avg_win']:>10,.2f}")
    print(f"  Avg Loss          : ${results['avg_loss']:>10,.2f}")

    if t is not None and len(t) > 0:
        exp = expectancy(t)
        print(f"  Expectancy/Trade  : ${exp:>10,.2f}")
        print(f"  Avg Bars Held     : {results['avg_bars_held']:>10.1f}")

        print(f"\n  EXIT BREAKDOWN")
        print(f"  {SEP2}")
        eb = exit_reason_breakdown(t)
        print(f"  {'Reason':<22} {'Count':>6}  {'Total P&L':>12}  {'Avg P&L':>10}")
        print(f"  {'-'*22} {'-'*6}  {'-'*12}  {'-'*10}")
        for reason, row in eb.iterrows():
            print(f"  {reason:<22} {int(row['count']):>6}  "
                  f"${row['total_pnl']:>11,.2f}  ${row['avg_pnl']:>9,.2f}")

        print(f"\n  QUALITY FLAGS")
        print(f"  {SEP2}")
        print(f"  Time Exits        : {results['time_exits']:>4}  "
              f"(momentum stalled before target)")
        print(f"  Ambiguous Fills   : {results['ambiguous_fills']:>4}  "
              f"(pessimistic assumption applied)")

        print(f"\n  YEARLY BREAKDOWN")
        print(f"  {SEP2}")
        yb = yearly_breakdown(t)
        print(f"  {'Year':>6}  {'Trades':>7}  {'Total P&L':>12}  {'Win Rate':>9}")
        print(f"  {'-'*6}  {'-'*7}  {'-'*12}  {'-'*9}")
        for year, row in yb.iterrows():
            flag = " ◄ weak" if row["win_rate"] < 30 else ""
            print(f"  {year:>6}  {int(row['trades']):>7}  "
                  f"${row['total_pnl']:>11,.2f}  {row['win_rate']:>8.1f}%{flag}")

        da = duration_analysis(t)
        print(f"\n  DURATION ANALYSIS")
        print(f"  {SEP2}")
        print(f"  Avg Bars (All)    : {da['avg_bars_all']}")
        print(f"  Avg Bars (Wins)   : {da['avg_bars_wins']}")
        print(f"  Avg Bars (Losses) : {da['avg_bars_losses']}")
        print(f"  Max Bars          : {da['max_bars']}")

        # Regime analysis
        full_regime_report(t, name)

        # Save
        os.makedirs("research", exist_ok=True)
        t.to_csv(f"research/trades_{name}.csv", index=False)
        yearly_breakdown(t).to_csv(f"research/yearly_{name}.csv")

    print(f"\n{SEP}")
    print(f"  Saved → research/trades_{name}.csv")
    print(f"  Chart → research/equity_{name}.png")
    print(f"{SEP}\n")


def print_portfolio_report(all_results: dict, initial_capital: float = 10000.0):
    all_trades = []
    for name, results in all_results.items():
        t = results.get("trades")
        if t is not None and len(t) > 0:
            tc = t.copy()
            tc["instrument"] = name
            all_trades.append(tc)

    if not all_trades:
        print("No trades to report.")
        return

    combined = pd.concat(all_trades).sort_values("entry_dt").reset_index(drop=True)
    wins      = combined[combined["pnl"] > 0]
    losses    = combined[combined["pnl"] <= 0]
    pf        = (wins["pnl"].sum() / abs(losses["pnl"].sum())
                 if losses["pnl"].sum() != 0 else 999)
    total_pnl = combined["pnl"].sum()
    final_cap = initial_capital + total_pnl

    print(f"\n{'#'*62}")
    print(f"  ZENITHFLOW PORTFOLIO  |  H4  |  2019–2025")
    print(f"{'#'*62}")
    print(f"  Starting Capital  : ${initial_capital:>10,.2f}")
    print(f"  Final Capital     : ${final_cap:>10,.2f}")
    print(f"  Total Return      : {(total_pnl/initial_capital*100):>9.1f}%")
    print(f"  Total Trades      : {len(combined):>10}")
    print(f"  Win Rate          : {len(wins)/len(combined)*100:>9.1f}%")
    print(f"  Profit Factor     : {pf:>10.2f}")
    print(f"  Avg Win           : ${wins['pnl'].mean():>10,.2f}")
    print(f"  Avg Loss          : ${losses['pnl'].mean():>10,.2f}")
    print(f"  Expectancy/Trade  : ${expectancy(combined):>10,.2f}")

    print(f"\n  PER-INSTRUMENT BREAKDOWN")
    print(f"  {SEP2}")
    print(f"  {'Inst':<8} {'Trades':>7} {'WR%':>7} {'P&L':>12} "
          f"{'PF':>6} {'AvgWin':>9} {'AvgLoss':>9}")
    print(f"  {'-'*8} {'-'*7} {'-'*7} {'-'*12} "
          f"{'-'*6} {'-'*9} {'-'*9}")

    for name, results in all_results.items():
        t = results.get("trades")
        if t is None or len(t) == 0:
            print(f"  {name:<8} {'0':>7}")
            continue
        w   = t[t["pnl"] > 0]
        l   = t[t["pnl"] <= 0]
        ipf = (w["pnl"].sum() / abs(l["pnl"].sum())
               if l["pnl"].sum() != 0 else 999)
        print(f"  {name:<8} {len(t):>7} "
              f"{len(w)/len(t)*100:>6.1f}% "
              f"${t['pnl'].sum():>11,.2f} "
              f"{ipf:>6.2f} "
              f"${w['pnl'].mean():>8,.2f} "
              f"${l['pnl'].mean():>8,.2f}")

    # Portfolio chart
    _plot_portfolio(combined, all_results, initial_capital)
    print(f"\n  Chart → research/equity_portfolio.png")
    print(f"{'#'*62}\n")


def _plot_portfolio(combined, all_results, initial_capital):
    equity = [initial_capital] + list(
        combined["pnl"].cumsum() + initial_capital
    )
    eq_s = pd.Series(equity)
    dd   = (eq_s - eq_s.cummax()) / eq_s.cummax() * 100

    fig, axes = plt.subplots(3, 1, figsize=(15, 10),
                              gridspec_kw={"height_ratios": [3, 1, 1]})

    axes[0].plot(eq_s.values, color=GREEN, lw=2, label="Portfolio")
    axes[0].axhline(initial_capital, color="gray", ls="--", alpha=0.5)
    axes[0].fill_between(range(len(eq_s)), initial_capital, eq_s.values,
                          where=eq_s.values >= initial_capital,
                          alpha=0.12, color=GREEN)
    axes[0].fill_between(range(len(eq_s)), initial_capital, eq_s.values,
                          where=eq_s.values < initial_capital,
                          alpha=0.12, color=RED)

    wins   = combined[combined["pnl"] > 0]
    losses = combined[combined["pnl"] <= 0]
    pf     = (wins["pnl"].sum() / abs(losses["pnl"].sum())
              if losses["pnl"].sum() != 0 else 999)

    axes[0].set_title(
        f"ZenithFlow Portfolio | H4 | 2019–2025  |  "
        f"Trades: {len(combined)}  |  "
        f"WR: {len(wins)/len(combined)*100:.1f}%  |  "
        f"PF: {pf:.2f}  |  DD: {dd.min():.1f}%",
        fontsize=10, fontweight="bold"
    )
    axes[0].set_ylabel("Capital (USD)")
    axes[0].legend()
    axes[0].grid(alpha=0.2)

    axes[1].fill_between(range(len(dd)), dd.values, 0, color=RED, alpha=0.6)
    axes[1].set_ylabel("Drawdown %")
    axes[1].grid(alpha=0.2)

    bar_colors = [
        INST_COLORS.get(row["instrument"], GREEN) if row["pnl"] > 0 else RED
        for _, row in combined.iterrows()
    ]
    axes[2].bar(range(len(combined)), combined["pnl"].values,
                color=bar_colors, alpha=0.85)
    axes[2].axhline(0, color="gray", lw=0.8)
    axes[2].set_ylabel("P&L per Trade ($)")
    axes[2].set_xlabel("Trade #")
    axes[2].grid(alpha=0.2)

    handles = [mpatches.Patch(color=v, label=k)
               for k, v in INST_COLORS.items() if k in all_results]
    axes[2].legend(handles=handles, loc="upper left", fontsize=8, ncol=5)

    plt.tight_layout()
    os.makedirs("research", exist_ok=True)
    plt.savefig("research/equity_portfolio.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("[Portfolio] Chart saved → research/equity_portfolio.png")