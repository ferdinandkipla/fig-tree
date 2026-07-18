# main.py
import os
from data.mt5_connector import connect, disconnect
from data.loader import fetch, cache_path
from strategies.trend_pullback.strategy import prepare
from execution.simulator import Simulator
from analytics.reporting import print_report, print_portfolio_report
from analytics.charts import export_trade_charts
from analytics.equity import plot_equity
from core.config import BACKTEST, RISK, TREND_PULLBACK, ENTRY_FEATURES, SEED
from research.experiment import record, DirtyGitStateError


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


def _log_run_to_ledger(all_results: dict, strategy_name: str = "trend_pullback"):
    """
    M1: log this run to the experiment ledger. Opt-out via
    ZENITHFLOW_SKIP_LEDGER=1, not opt-in — every run is logged by
    default so the ledger can't silently develop gaps.

    Refuses (loudly, not silently) if the git tree is dirty outside
    research/ledger.jsonl and research/runs/ — see research/experiment.py.
    """
    if os.environ.get("ZENITHFLOW_SKIP_LEDGER"):
        print("[Ledger] Skipped (ZENITHFLOW_SKIP_LEDGER set).")
        return

    successful_symbols = [
        sym for sym, res in all_results.items()
        if res and "trades" in res and res["trades"] is not None and len(res["trades"]) > 0
    ]
    if not successful_symbols:
        print("[Ledger] No successful runs to log.")
        return

    config_snapshot = {
        "BACKTEST":        BACKTEST,
        "RISK":            RISK,
        "TREND_PULLBACK":  TREND_PULLBACK,
        "ENTRY_FEATURES":  ENTRY_FEATURES,
    }
    data_paths = {
        sym: str(cache_path(sym, BACKTEST["timeframe"]))
        for sym in successful_symbols
    }
    output_paths = {
        sym: f"research/trades_{sym}.csv"
        for sym in successful_symbols
    }

    try:
        entry = record(
            strategy=strategy_name,
            symbols=successful_symbols,
            config_snapshot=config_snapshot,
            data_paths=data_paths,
            output_paths=output_paths,
            seed=SEED,
        )
        print(f"[Ledger] Run logged: {entry['run_id']}  "
              f"(commit {entry['git_commit'][:8]}, "
              f"config_hash {entry['config_hash'][:8]})")
    except DirtyGitStateError as e:
        print(f"[Ledger] WARNING — run NOT logged: {e}")
    except FileNotFoundError as e:
        # M1 fix (code-audit finding): this used to be uncaught -- a
        # mismatch between the constructed data/output path and what
        # actually existed on disk would crash the whole run AFTER the
        # backtest completed. Now caught explicitly and reported, same
        # as the dirty-tree case, rather than raising past a completed
        # portfolio report.
        print(f"[Ledger] WARNING — run NOT logged, file missing: {e}")


if __name__ == "__main__":
    if not connect():
        exit(1)
    try:
        all_results = {}
        all_results["USDJPY"] = run("USDJPY", export_charts=True)
        all_results["XAUUSD"] = run("XAUUSD", export_charts=True)
        all_results["GBPJPY"] = run("GBPJPY", export_charts=True)
        print_portfolio_report(all_results)
        _log_run_to_ledger(all_results)
    finally:
        disconnect()
