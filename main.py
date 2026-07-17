# main.py
from data.mt5_connector import connect, disconnect
from data.loader import fetch
from strategies.trend_pullback.strategy import prepare
from execution.simulator import Simulator
from analytics.reporting import print_report, print_portfolio_report
from analytics.charts import export_trade_charts
from analytics.equity import plot_equity
from core.config import BACKTEST


def run(symbol: str, export_charts: bool = False) -> dict:
    print(f"\n[Main] Starting: {symbol}")

    df = fetch(symbol, BACKTEST["timeframe"],
               BACKTEST["start"], BACKTEST["end"],
               use_cache=True)
    if df.empty:
        print(f"[Main] No data for {symbol}. Skipping.")
        return {}

    df_prepared = prepare(df, symbol=symbol)   # ← pass symbol
    sim         = Simulator(symbol)
    results     = sim.run(df_prepared)

    if "error" in results:
        print(f"[Main] {symbol}: {results['error']}")
        return {}

    print_report(symbol, results)

    trades = results.get("trades")
    if trades is not None and len(trades) > 0:
        plot_equity(symbol, trades)
        if export_charts:
            export_trade_charts(symbol, trades, df_prepared)

    return results

if __name__ == "__main__":
    if not connect():
        exit(1)
    try:
        all_results = {}
        all_results["USDJPY"] = run("USDJPY", export_charts=True)
        all_results["XAUUSD"] = run("XAUUSD", export_charts=True)
        all_results["GBPJPY"] = run("GBPJPY", export_charts=True)
        print_portfolio_report(all_results)
    finally:
        disconnect()