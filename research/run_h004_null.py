# research/run_h004_null.py
#
# H-004: null model sweep for the wider universe. Entry frequency is a
# FIXED 5% of eligible bars per instrument/timeframe -- NOT matched to
# trend_pullback's signal count (that strategy is retired; matching its
# frequency would silently re-import its anatomy into a market-
# structure-first test). See research/registry/H-004.md.
#
# Usage:
#   python research/run_h004_null.py --symbol USDJPY --timeframe H1 --seed-start 0 --seed-end 40
#   python research/run_h004_null.py --symbol USDJPY --timeframe H1 --finalize

import sys
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import MetaTrader5 as mt5

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.loader import fetch, cache_path
from strategies.common import compute_common_features, WARMUP_BARS
from strategies.null_random import NullRandomStrategy
from execution.simulator import Simulator
from core.config import BACKTEST
from research.experiment import record, DirtyGitStateError

TIMEFRAME_MAP = {"H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4}
ENTRY_DENSITY = 0.05   # fixed 5% of eligible bars -- see module docstring
N_SEEDS = 100

RESULTS_PATH = Path("research/null_seed_results_h004.csv")
RUNS_DIR     = Path("research/null_runs_h004")

_REQUIRED_COLS = ["ema_fast", "ema_slow", "adx", "atr",
                  "ema_distance", "trend_gap",
                  "stop_distance", "target_distance"]


def _resample_signal(common_df: pd.DataFrame, n_signals: int, seed: int) -> pd.DataFrame:
    """Same logic as strategies/null_random.py's signed sampling, factored
    out to avoid recomputing indicators every seed (same optimization as
    research/run_null_model.py)."""
    df = common_df.copy()
    eligible_mask = df[_REQUIRED_COLS].notna().all(axis=1)
    eligible_idx  = np.flatnonzero(eligible_mask.values)
    n = min(n_signals, len(eligible_idx))
    rng    = np.random.default_rng(seed)
    chosen = rng.choice(eligible_idx, size=n, replace=False)
    df["signal"] = 0
    df.iloc[chosen, df.columns.get_loc("signal")] = 1
    df["direction"] = 1
    directions = rng.choice([1, -1], size=n)
    df.iloc[chosen, df.columns.get_loc("direction")] = directions
    return df.dropna()


def run(symbol: str, timeframe_label: str, seed_start: int, seed_end: int,
       log_to_ledger: bool = True):
    timeframe_const = TIMEFRAME_MAP[timeframe_label]
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    raw_df = fetch(symbol, timeframe_const, BACKTEST["start"], BACKTEST["end"], use_cache=True)
    if raw_df.empty:
        print(f"[H-004] No data for {symbol}/{timeframe_label}, skipping.")
        return

    common_df = compute_common_features(raw_df.copy())
    common_df = common_df.iloc[WARMUP_BARS:].copy()
    eligible_mask = common_df[_REQUIRED_COLS].notna().all(axis=1)
    n_eligible = int(eligible_mask.sum())
    n_signals = round(ENTRY_DENSITY * n_eligible)

    print(f"\n{'='*60}\n{symbol} / {timeframe_label}  (seeds {seed_start}-{seed_end-1})\n"
          f"n_eligible={n_eligible}  n_signals(5%)={n_signals}\n{'='*60}")

    file_exists = RESULTS_PATH.exists()
    rows = []
    for seed in range(seed_start, seed_end):
        prepared = _resample_signal(common_df, n_signals, seed)
        strat = NullRandomStrategy(n_signals=n_signals, seed=seed, signed=True)
        sim = Simulator(symbol, entry_features=strat.entry_features)
        result = sim.run(prepared)

        if "error" in result or result.get("total_trades", 0) == 0:
            continue

        out_path = RUNS_DIR / f"{symbol}_{timeframe_label}_seed{seed}_trades.csv"
        result["trades"].to_csv(out_path, index=False)
        rows.append({"symbol": symbol, "timeframe": timeframe_label, "seed": seed,
                     "n_signals": n_signals, "n_eligible": n_eligible})

        if log_to_ledger:
            try:
                record(
                    strategy="null_random", symbols=[symbol],
                    config_snapshot={**strat.params, "timeframe": timeframe_label, "density": ENTRY_DENSITY},
                    data_paths={symbol: str(cache_path(symbol, timeframe_const))},
                    output_paths={symbol: str(out_path)},
                    seed=seed,
                    extra={"purpose": "H-004_session_wider_universe", "timeframe": timeframe_label},
                )
            except DirtyGitStateError as e:
                print(f"[H-004] Ledger WARNING (seed {seed}): {e}")

    chunk_df = pd.DataFrame(rows)
    chunk_df.to_csv(RESULTS_PATH, mode="a", index=False, header=not file_exists)
    print(f"[H-004] {symbol}/{timeframe_label}: appended {len(rows)} results")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--timeframe", required=True, choices=list(TIMEFRAME_MAP.keys()))
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--seed-end", type=int, default=N_SEEDS)
    parser.add_argument("--no-ledger", action="store_true")
    args = parser.parse_args()
    run(args.symbol, args.timeframe, args.seed_start, args.seed_end, log_to_ledger=not args.no_ledger)
