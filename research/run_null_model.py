# research/run_null_model.py
#
# M2 acceptance: builds a null distribution of expectancy/PF per
# instrument by running null_random.py across N seeds, matched to the
# real strategy's signal frequency on the same window. Each seeded run
# is its own ledger entry, per the M2 spec -- this is where the ledger
# earns its keep as more than a formality.
#
# Usage: python3 research/run_null_model.py [--n-seeds 100] [--no-ledger]

import sys
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.loader import fetch, cache_path
from strategies.common import compute_common_features, WARMUP_BARS
from strategies.trend_pullback.strategy import TrendPullbackStrategy
from strategies.null_random import NullRandomStrategy
from execution.simulator import Simulator
from core.config import BACKTEST, SEED
from research.experiment import record, DirtyGitStateError

SYMBOLS = ["USDJPY", "XAUUSD", "GBPJPY"]

_REQUIRED_COLS = ["ema_fast", "ema_slow", "adx", "atr",
                  "ema_distance", "trend_gap",
                  "stop_distance", "target_distance"]


def _prepare_common_once(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Indicators/geometry don't depend on the seed -- computing them once
    per symbol instead of once per seed is a ~100x reduction in redundant
    work (indicator computation dominated runtime in initial testing:
    140s for 3 seeds x 3 symbols, which would have been ~78 minutes for
    the full 100-seed run). Mirrors NullRandomStrategy.prepare()'s own
    common-feature step exactly -- same function, same call."""
    df = compute_common_features(raw_df)
    df = df.iloc[WARMUP_BARS:].copy()
    return df


def _resample_signal(common_df: pd.DataFrame, n_signals: int, seed: int) -> pd.DataFrame:
    """The seed-dependent part only: sample n_signals eligible bars at
    random. This is exactly NullRandomStrategy.prepare()'s sampling logic,
    factored out so it can run against an already-prepared common_df
    instead of recomputing indicators every call."""
    df = common_df.copy()
    eligible_mask = df[_REQUIRED_COLS].notna().all(axis=1)
    eligible_idx  = np.flatnonzero(eligible_mask.values)

    n = min(n_signals, len(eligible_idx))
    rng    = np.random.default_rng(seed)
    chosen = rng.choice(eligible_idx, size=n, replace=False)

    df["signal"] = 0
    df.iloc[chosen, df.columns.get_loc("signal")] = 1
    return df.dropna()


def run_one_seed(symbol: str, common_df: pd.DataFrame, n_signals: int, seed: int):
    strat    = NullRandomStrategy(n_signals=n_signals, seed=seed)
    prepared = _resample_signal(common_df, n_signals, seed)
    sim      = Simulator(symbol, entry_features=strat.entry_features)
    result   = sim.run(prepared)
    return result, strat


def summarize(results_list: list) -> dict:
    expectancies, pfs = [], []
    for r in results_list:
        if "error" in r or r.get("total_trades", 0) == 0:
            continue
        expectancies.append(r["trades"]["pnl"].mean())
        pfs.append(r["profit_factor"])
    if not expectancies:
        return {"n": 0}
    exp_arr = np.array(expectancies)
    pf_arr  = np.array(pfs)
    return {
        "n":               len(expectancies),
        "expectancy_mean": float(exp_arr.mean()),
        "expectancy_p05":  float(np.percentile(exp_arr, 5)),
        "expectancy_p95":  float(np.percentile(exp_arr, 95)),
        "pf_mean":         float(pf_arr.mean()),
        "pf_p05":          float(np.percentile(pf_arr, 5)),
        "pf_p95":          float(np.percentile(pf_arr, 95)),
    }


def real_strategy_expectancy_pf(symbol: str) -> dict:
    """The real strategy's own expectancy/PF on this window, for direct
    comparison against the null distribution summary."""
    raw_df   = fetch(symbol, BACKTEST["timeframe"], BACKTEST["start"], BACKTEST["end"], use_cache=True)
    strategy = TrendPullbackStrategy()
    prepared = strategy.prepare(raw_df.copy(), symbol=symbol)
    sim      = Simulator(symbol, entry_features=strategy.entry_features)
    result   = sim.run(prepared)
    return {
        "expectancy": float(result["trades"]["pnl"].mean()),
        "pf":         result["profit_factor"],
        "n_signals":  int(prepared["signal"].sum()),
    }


def main(n_seeds: int = 100, log_to_ledger: bool = True,
         seed_start: int = 0, seed_end: int = None,
         append_results_path: str = "research/null_seed_results.csv"):
    """
    seed_start/seed_end: run only seeds in [seed_start, seed_end) this
    call, appending per-seed results to append_results_path. Lets the
    full N-seed sweep be split across multiple invocations (each
    ~9s/run x n_symbols; a 100-seed x 3-symbol sweep is ~44 minutes,
    too long for one blocking call in this environment) without losing
    any completed work between chunks.
    """
    if seed_end is None:
        seed_end = n_seeds

    Path("research/null_runs").mkdir(parents=True, exist_ok=True)
    append_path = Path(append_results_path)
    file_exists = append_path.exists()

    for symbol in SYMBOLS:
        print(f"\n{'='*60}\n{symbol}  (seeds {seed_start}-{seed_end-1})\n{'='*60}")

        raw_df = fetch(symbol, BACKTEST["timeframe"],
                       BACKTEST["start"], BACKTEST["end"], use_cache=True)
        if raw_df.empty:
            print(f"[NullModel] No data for {symbol}, skipping.")
            continue

        real = real_strategy_expectancy_pf(symbol)
        n_signals = real["n_signals"]

        common_df = _prepare_common_once(raw_df.copy())

        if seed_start == 0:
            # Cross-check only on the first chunk -- no need to repeat
            # per chunk, it's a code-correctness check, not a data check.
            _check_strat   = NullRandomStrategy(n_signals=n_signals, seed=0)
            _via_protocol  = _check_strat.prepare(raw_df.copy(), symbol=symbol)
            _via_fast_path = _resample_signal(common_df, n_signals, seed=0)
            assert _via_protocol.equals(_via_fast_path), (
                "Fast-path optimization diverged from NullRandomStrategy.prepare()."
            )

        rows = []
        for seed in range(seed_start, seed_end):
            result, strat = run_one_seed(symbol, common_df, n_signals, seed)

            if "error" in result or result.get("total_trades", 0) == 0:
                continue

            expectancy = float(result["trades"]["pnl"].mean())
            pf = result["profit_factor"]
            rows.append({
                "symbol": symbol, "seed": seed,
                "expectancy": expectancy, "pf": pf,
                "n_signals": n_signals,
                "real_expectancy": real["expectancy"], "real_pf": real["pf"],
            })

            if log_to_ledger:
                out_path = f"research/null_runs/{symbol}_seed{seed}_trades.csv"
                result["trades"].to_csv(out_path, index=False)
                try:
                    record(
                        strategy=strat.name, symbols=[symbol],
                        config_snapshot=strat.params,
                        data_paths={symbol: str(cache_path(symbol, BACKTEST["timeframe"]))},
                        output_paths={symbol: out_path},
                        seed=seed,
                        extra={"purpose": "M2_null_distribution", "n_signals": n_signals},
                    )
                except DirtyGitStateError as e:
                    print(f"[NullModel] Ledger WARNING (seed {seed}): {e}")

        chunk_df = pd.DataFrame(rows)
        chunk_df.to_csv(append_path, mode="a", index=False, header=not file_exists)
        file_exists = True
        print(f"[NullModel] {symbol}: appended {len(rows)} seed results "
              f"(seeds {seed_start}-{seed_end-1}) to {append_path}")


def finalize_summary(results_path: str = "research/null_seed_results.csv",
                     summary_path: str = "research/null_distribution_summary.csv"):
    """Call after all chunks are done: reads the accumulated per-seed
    results and computes the final percentile summary per instrument."""
    df = pd.read_csv(results_path)
    rows = []
    for symbol, g in df.groupby("symbol"):
        exp_arr = g["expectancy"].values
        pf_arr  = g["pf"].values
        rows.append({
            "symbol":            symbol,
            "n":                 len(g),
            "expectancy_mean":   float(exp_arr.mean()),
            "expectancy_p05":    float(np.percentile(exp_arr, 5)),
            "expectancy_p95":    float(np.percentile(exp_arr, 95)),
            "pf_mean":           float(pf_arr.mean()),
            "pf_p05":            float(np.percentile(pf_arr, 5)),
            "pf_p95":            float(np.percentile(pf_arr, 95)),
            "n_signals_matched": int(g["n_signals"].iloc[0]),
            "real_expectancy":   float(g["real_expectancy"].iloc[0]),
            "real_pf":           float(g["real_pf"].iloc[0]),
        })
    summary_df = pd.DataFrame(rows)
    summary_df.to_csv(summary_path, index=False)
    print(summary_df.to_string(index=False))
    return summary_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-seeds", type=int, default=100)
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--seed-end", type=int, default=None)
    parser.add_argument("--no-ledger", action="store_true")
    parser.add_argument("--finalize", action="store_true",
                       help="Skip running seeds; just summarize accumulated results")
    args = parser.parse_args()
    if args.finalize:
        finalize_summary()
    else:
        main(n_seeds=args.n_seeds, log_to_ledger=not args.no_ledger,
             seed_start=args.seed_start, seed_end=args.seed_end)
