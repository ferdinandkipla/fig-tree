# analytics/charts.py
import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def export_trade_charts(symbol: str, trades: pd.DataFrame,
                        df_ohlcv: pd.DataFrame, context_bars: int = 40):
    out_dir = f"research/charts/{symbol}"
    os.makedirs(out_dir, exist_ok=True)
    print(f"\n[Charts] Exporting {len(trades)} trade charts → {out_dir}/")

    for idx, trade in trades.iterrows():
        trade_num = idx + 1
        try:
            _plot_trade(symbol, trade, trade_num, df_ohlcv, context_bars, out_dir)
        except Exception as e:
            print(f"  [Charts] Trade {trade_num} failed: {e}")

    print(f"[Charts] Done — {len(trades)} charts saved.")


def _plot_trade(symbol, trade, trade_num, df, context_bars, out_dir):
    entry_dt = pd.Timestamp(trade["entry_dt"])
    exit_dt  = pd.Timestamp(trade["exit_dt"])

    entry_idx = df.index.searchsorted(entry_dt)
    start_idx = max(0, entry_idx - context_bars)
    end_idx   = min(len(df), entry_idx + context_bars)
    window    = df.iloc[start_idx:end_idx].copy()

    if len(window) < 5:
        return

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 7),
                                    gridspec_kw={"height_ratios": [3, 1]})

    x = range(len(window))

    ax1.plot(x, window["close"].values,    color="#AAAAAA", lw=1.0, alpha=0.7, label="Close")
    ax1.plot(x, window["ema_fast"].values, color="#F5A623", lw=1.5, label="EMA50")
    ax1.plot(x, window["ema_slow"].values, color="#4A90D9", lw=1.5, label="EMA200")

    def get_x(dt):
        return window.index.searchsorted(pd.Timestamp(dt))

    ex  = get_x(entry_dt)
    exx = get_x(exit_dt)

    ax1.axvline(ex,  color="#1D9E75", lw=1.0, ls="--", alpha=0.5)
    ax1.axvline(exx, color="#E24B4A", lw=1.0, ls="--", alpha=0.5)

    # FIX: use correct column names from trade DataFrame
    ax1.axhline(trade["entry"],       color="#1D9E75", lw=1.2, ls="--", alpha=0.8,
                label=f"Entry {trade['entry']:.4f}")
    ax1.axhline(trade["stop_loss"],   color="#E24B4A", lw=1.2, ls=":",  alpha=0.8,
                label=f"Stop  {trade['stop_loss']:.4f}")
    ax1.axhline(trade["take_profit"], color="#4A90D9", lw=1.2, ls=":",  alpha=0.8,
                label=f"Target {trade['take_profit']:.4f}")

    ax1.scatter([ex],  [trade["entry"]], color="#1D9E75", s=80, zorder=5)
    exit_color = "#1D9E75" if trade["pnl"] > 0 else "#E24B4A"
    ax1.scatter([exx], [trade["exit"]],  color=exit_color, s=80,
                marker="x", zorder=5, linewidths=2)

    result_str = f"+${trade['pnl']:.2f}" if trade["pnl"] > 0 else f"-${abs(trade['pnl']):.2f}"
    ax1.set_title(
        f"{symbol} | Trade #{trade_num:03d} | "
        f"{trade['exit_reason'].upper()} | {result_str} | "
        f"ADX: {trade.get('adx_entry', '?')} | "
        f"Session: {trade.get('session', '?')} | "
        f"Year: {trade.get('year', '?')}",
        fontsize=9, fontweight="bold"
    )
    ax1.legend(fontsize=7, loc="upper left", ncol=4)
    ax1.grid(alpha=0.15)
    ax1.set_ylabel("Price")

    if "adx" in window.columns:
        ax2.plot(x, window["adx"].values, color="#9B59B6", lw=1.2, label="ADX")
        ax2.axhline(20, color="gray", ls="--", lw=0.8, alpha=0.5)
        ax2.axhline(28, color="orange", ls="--", lw=0.8, alpha=0.7, label="ADX ceiling=28")
        ax2.axvline(ex, color="#1D9E75", lw=1.0, ls="--", alpha=0.5)
        ax2.set_ylabel("ADX")
        ax2.legend(fontsize=7)
        ax2.grid(alpha=0.15)

    plt.tight_layout()
    fname = f"{out_dir}/trade_{trade_num:03d}_{trade['exit_reason']}.png"
    plt.savefig(fname, dpi=120, bbox_inches="tight")
    plt.close()