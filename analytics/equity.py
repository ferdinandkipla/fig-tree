# analytics/equity.py
import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def plot_equity(symbol: str, trades: pd.DataFrame,
                initial_capital: float = 10000.0):

    equity = [initial_capital] + list(
        trades["pnl"].cumsum() + initial_capital
    )
    eq_s = pd.Series(equity)
    dd   = (eq_s - eq_s.cummax()) / eq_s.cummax() * 100

    GREEN = "#1D9E75"
    RED   = "#E24B4A"

    fig, axes = plt.subplots(3, 1, figsize=(14, 9),
                              gridspec_kw={"height_ratios": [3, 1, 1]})

    axes[0].plot(eq_s.values, color=GREEN, lw=2)
    axes[0].axhline(initial_capital, color="gray", ls="--", alpha=0.5)
    axes[0].fill_between(range(len(eq_s)), initial_capital, eq_s.values,
                          where=eq_s.values >= initial_capital,
                          alpha=0.15, color=GREEN)
    axes[0].fill_between(range(len(eq_s)), initial_capital, eq_s.values,
                          where=eq_s.values < initial_capital,
                          alpha=0.15, color=RED)

    final  = eq_s.iloc[-1]
    ret    = (final - initial_capital) / initial_capital * 100
    max_dd = dd.min()
    wins   = (trades["pnl"] > 0).sum()
    wr     = wins / len(trades) * 100
    pf_w   = trades[trades["pnl"] > 0]["pnl"].sum()
    pf_l   = abs(trades[trades["pnl"] <= 0]["pnl"].sum())
    pf     = pf_w / pf_l if pf_l > 0 else 999

    axes[0].set_title(
        f"ZenithFlow | {symbol} | H4 | 2019–2025  |  "
        f"Return: {ret:.1f}%  |  DD: {max_dd:.1f}%  |  "
        f"PF: {pf:.2f}  |  WR: {wr:.1f}%  |  Trades: {len(trades)}",
        fontsize=10, fontweight="bold"
    )
    axes[0].set_ylabel("Capital (USD)")
    axes[0].grid(alpha=0.2)

    axes[1].fill_between(range(len(dd)), dd.values, 0,
                          color=RED, alpha=0.6)
    axes[1].set_ylabel("Drawdown %")
    axes[1].grid(alpha=0.2)

    year_colors = {
        2019: "#4A90D9", 2020: "#E24B4A", 2021: "#1D9E75",
        2022: "#F5A623", 2023: "#9B59B6", 2024: "#1ABC9C",
    }
    bar_colors = [
        year_colors.get(int(row.get("year", 2019)), GREEN)
        if row["pnl"] > 0 else RED
        for _, row in trades.iterrows()
    ]
    axes[2].bar(range(len(trades)), trades["pnl"].values,
                color=bar_colors, alpha=0.85)
    axes[2].axhline(0, color="gray", lw=0.8)
    axes[2].set_ylabel("P&L per Trade ($)")
    axes[2].set_xlabel("Trade #")
    axes[2].grid(alpha=0.2)

    handles = [plt.Rectangle((0, 0), 1, 1, color=c, label=str(y))
               for y, c in year_colors.items()]
    axes[2].legend(handles=handles, loc="upper left",
                   fontsize=7, ncol=6, title="Year (wins)")

    plt.tight_layout()
    os.makedirs("research", exist_ok=True)
    path = f"research/equity_{symbol}.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()