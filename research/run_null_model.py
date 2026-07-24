# research/run_null_model.py
#
# M2 acceptance: builds a null distribution of expectancy/PF per
# instrument by running null_random.py across N seeds, matched to the
# real strategy's signal frequency on the same window. Each seeded run
# is its own ledger entry, per the M2 spec -- this is where the ledger
# earns its keep as more than a formality.
#
# S1 UPDATE: --signed builds the drift-neutral null (random direction
# per entry, per the long/short redesign) instead of the original
# long-only null. Signed results write to SEPARATE files
# (null_seed_results_signed.csv, null_runs_signed/) so the original
# long-only null distributions are preserved as historical evidence,
# not overwritten -- they're superseded as the benchmark, not deleted.
#
# Usage: python3 research/run_null_model.py [--n-seeds 100] [--signed] [--no-ledger]

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
    per symbol instead of once per seed is a large reduction in redundant
    work. Mirrors NullRandomStrategy.prepare()'s own common-feature step
    exactly -- same function, same call."""
    df = compute_common_features(raw_df)
    df = df.iloc[WARMUP_BARS:].copy()
    return df


def _resample_signal(common_df: pd.DataFrame, n_signals: int, seed: int,
                     signed: bool = False) -> pd.DataFrame:
    """The seed-dependent part only: sample n_signals eligible bars at
    random, optionally with random direction. This is exactly
    NullRandomStrategy.prepare()'s sampling logic, factored out so it
    can run against an already-prepared common_df instead of
    recomputing indicators every call.

    S1: when signed=True, direction is drawn from the SAME rng stream,
    AFTER entry selection -- entries are bar-for-bar identical to
    signed=False for the same seed; only direction changes."""
    df = common_df.copy()
    eligible_mask = df[_REQUIRED_COLS].notna().all(axis=1)
    eligible_idx  = np.flatnonzero(eligible_mask.values)

    n = min(n_signals, len(eligible_idx))
    rng    = np.random.default_rng(seed)
    chosen = rng.choice(eligible_idx, size=n, replace=False)

    df["signal"] = 0
    df.iloc[chosen, df.columns.get_loc("signal")] = 1

    df["direction"] = 1
    if signed:
        directions = rng.choice([1, -1], size=n)
        df.iloc[chosen, df.columns.get_loc("direction")] = directions

    return df.dropna()


def run_one_seed(symbol: str, common_df: pd.DataFrame, n_signals: int, seed: int,
                 signed: bool = False):
    strat    = NullRandomStrategy(n_signals=n_signals, seed=seed, signed=signed)
    prepared = _resample_signal(common_df, n_signals, seed, signed=signed)
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
         signed: bool = False,
         append_results_path: str = None):
    """
    seed_start/seed_end: run only seeds in [seed_start, seed_end) this
    call, appending per-seed results to append_results_path. Lets the
    full N-seed sweep be split across multiple invocations without
    losing any completed work between chunks.
    """
    if seed_end is None:
        seed_end = n_seeds

    if append_results_path is None:
        append_results_path = ("research/null_seed_results_signed.csv" if signed
                               else "research/null_seed_results.csv")
    null_runs_dir = Path("research/null_runs_signed" if signed else "research/null_runs")
    null_runs_dir.mkdir(parents=True, exist_ok=True)

    append_path = Path(append_results_path)
    file_exists = append_path.exists()

    for symbol in SYMBOLS:
        print(f"\n{'='*60}\n{symbol}  (seeds {seed_start}-{seed_end-1}, signed={signed})\n{'='*60}")

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
            _check_strat   = NullRandomStrategy(n_signals=n_signals, seed=0, signed=signed)
            _via_protocol  = _check_strat.prepare(raw_df.copy(), symbol=symbol)
            _via_fast_path = _resample_signal(common_df, n_signals, seed=0, signed=signed)
            assert _via_protocol.equals(_via_fast_path), (
                "Fast-path optimization diverged from NullRandomStrategy.prepare()."
            )

        rows = []
        for seed in range(seed_start, seed_end):
            result, strat = run_one_seed(symbol, common_df, n_signals, seed, signed=signed)

            if "error" in result or result.get("total_trades", 0) == 0:
                continue

            expectancy = float(result["trades"]["pnl"].mean())
            pf = result["profit_factor"]
            rows.append({
                "symbol": symbol, "seed": seed,
                "expectancy": expectancy, "pf": pf,
                "n_signals": n_signals, "signed": signed,
                "real_expectancy": real["expectancy"], "real_pf": real["pf"],
            })

            if log_to_ledger:
                out_path = str(null_runs_dir / f"{symbol}_seed{seed}_trades.csv")
                result["trades"].to_csv(out_path, index=False)
                try:
                    record(
                        strategy=strat.name, symbols=[symbol],
                        config_snapshot=strat.params,
                        data_paths={symbol: str(cache_path(symbol, BACKTEST["timeframe"]))},
                        output_paths={symbol: out_path},
                        seed=seed,
                        extra={"purpose": "S1_signed_null_distribution" if signed else "M2_null_distribution",
                              "n_signals": n_signals, "signed": signed},
                    )
                except DirtyGitStateError as e:
                    print(f"[NullModel] Ledger WARNING (seed {seed}): {e}")

        chunk_df = pd.DataFrame(rows)
        chunk_df.to_csv(append_path, mode="a", index=False, header=not file_exists)
        file_exists = True
        print(f"[NullModel] {symbol}: appended {len(rows)} seed results "
              f"(seeds {seed_start}-{seed_end-1}) to {append_path}")


def finalize_summary(results_path: str = None, summary_path: str = None, signed: bool = False):
    """Call after all chunks are done: reads the accumulated per-seed
    results and computes the final percentile summary per instrument."""
    if results_path is None:
        results_path = ("research/null_seed_results_signed.csv" if signed
                        else "research/null_seed_results.csv")
    if summary_path is None:
        summary_path = ("research/null_distribution_summary_signed.csv" if signed
                        else "research/null_distribution_summary.csv")

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
    parser.add_argument("--signed", action="store_true")
    parser.add_argument("--no-ledger", action="store_true")
    parser.add_argument("--finalize", action="store_true",
                       help="Skip running seeds; just summarize accumulated results")
    args = parser.parse_args()
    if args.finalize:
        finalize_summary(signed=args.signed)
    else:
        main(n_seeds=args.n_seeds, log_to_ledger=not args.no_ledger,
             seed_start=args.seed_start, seed_end=args.seed_end, signed=args.signed)
