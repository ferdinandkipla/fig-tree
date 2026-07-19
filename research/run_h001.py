# research/run_h001.py
#
# H-001: Pullback Depth Predicts Trade Outcome.
#
# Procedural discipline, enforced structurally (not just by convention):
# freeze_bins() computes TRAIN-only quartile edges and writes them to
# research/registry/H-001-bins.json + a ledger entry, and RETURNS
# NOTHING -- it cannot be chained into a stats computation in the same
# call. compute_verdict() is a SEPARATE, later invocation that only
# reads the frozen file back from disk. This makes "peek at OOS, then
# pretend the bins were frozen first" structurally awkward to do by
# accident: the two phases are different CLI subcommands, not two
# lines in one function.
#
# Usage:
#   python3 research/run_h001.py --freeze       # phase 1, run once
#   python3 research/run_h001.py --verdict       # phase 2, run after

import sys
import json
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import BACKTEST
from data.loader import cache_path
from research.experiment import record, DirtyGitStateError

SYMBOLS     = ["USDJPY", "XAUUSD", "GBPJPY"]
TRAIN_END   = "2022-01-01"   # per H-001 registration: TRAIN window 2019-2022
BINS_PATH   = Path("research/registry/H-001-bins.json")
N_NULL_SEEDS = 100


def _load_train_trades(symbol: str) -> pd.DataFrame:
    df = pd.read_csv(f"research/trades_{symbol}.csv", parse_dates=["entry_dt"])
    return df[df["entry_dt"] < TRAIN_END].copy()


def freeze_bins():
    """
    PHASE 1. Computes ema_distance quartile edges on TRAIN-only real
    strategy trades, per instrument. Writes them to
    research/registry/H-001-bins.json and logs a ledger entry BEFORE
    any bin statistic is computed. Run this once; do not re-run after
    looking at compute_verdict()'s output.
    """
    all_bins = {}
    for symbol in SYMBOLS:
        train = _load_train_trades(symbol)
        if len(train) < 4:
            print(f"[H-001] WARNING: {symbol} has only {len(train)} TRAIN trades, "
                  f"quartile binning is unreliable.")
        _, edges = pd.qcut(train["ema_distance"], q=4, retbins=True, duplicates="drop")
        all_bins[symbol] = {
            "edges": edges.tolist(),
            "n_train_trades": len(train),
        }
        print(f"[H-001] {symbol}: TRAIN n={len(train)}, "
              f"ema_distance quartile edges = {[round(e,4) for e in edges]}")

    BINS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(BINS_PATH, "w") as f:
        json.dump({
            "hypothesis": "H-001",
            "train_end": TRAIN_END,
            "bins_by_symbol": all_bins,
        }, f, indent=2)
    print(f"[H-001] Frozen bin edges written -> {BINS_PATH}")

    try:
        entry = record(
            strategy="H-001-binning", symbols=SYMBOLS,
            config_snapshot={"train_end": TRAIN_END, "bins_by_symbol": all_bins},
            data_paths={s: str(cache_path(s, BACKTEST["timeframe"])) for s in SYMBOLS},
            output_paths={s: f"research/trades_{s}.csv" for s in SYMBOLS},
            extra={"purpose": "H-001_bin_freeze", "bins_path": str(BINS_PATH)},
        )
        print(f"[H-001] Bin freeze logged to ledger: {entry['run_id']}")
    except (DirtyGitStateError, FileNotFoundError) as e:
        print(f"[H-001] Ledger WARNING (bin freeze not logged): {e}")

    print("\n[H-001] Bins are now FROZEN. Do not re-run --freeze after "
          "viewing --verdict output.")


def _bin_label(edges, i):
    return f"Q{i+1} [{edges[i]:.3f}, {edges[i+1]:.3f}]"


def compute_verdict():
    """
    PHASE 2. Reads the frozen bin edges from disk (never recomputes
    them) and produces the H-001 verdict table: per instrument, per
    bin -- n, expectancy, PF on TRAIN, and the bin's percentile against
    the null distribution (built from the same TRAIN-window null trades,
    binned with the SAME frozen edges).
    """
    if not BINS_PATH.exists():
        raise RuntimeError(f"{BINS_PATH} not found -- run --freeze first.")

    with open(BINS_PATH) as f:
        frozen = json.load(f)

    rows = []
    for symbol in SYMBOLS:
        edges = frozen["bins_by_symbol"][symbol]["edges"]
        train = _load_train_trades(symbol)
        train["bin"] = pd.cut(train["ema_distance"], bins=edges,
                              labels=False, include_lowest=True)

        # Build the null distribution: TRAIN-window null trades across
        # all 100 seeds, binned with the SAME frozen edges. For each
        # bin, compute one expectancy value per seed (mean pnl of that
        # seed's trades landing in that bin), giving a 100-point null
        # distribution per bin to rank the real bin against.
        null_bin_expectancies = {i: [] for i in range(len(edges) - 1)}
        for seed in range(N_NULL_SEEDS):
            path = Path(f"research/null_runs/{symbol}_seed{seed}_trades.csv")
            if not path.exists():
                continue
            ndf = pd.read_csv(path, parse_dates=["entry_dt"])
            ndf = ndf[ndf["entry_dt"] < TRAIN_END].copy()
            if ndf.empty:
                continue
            ndf["bin"] = pd.cut(ndf["ema_distance"], bins=edges,
                                labels=False, include_lowest=True)
            for i in null_bin_expectancies:
                bin_trades = ndf[ndf["bin"] == i]
                if len(bin_trades) > 0:
                    null_bin_expectancies[i].append(bin_trades["pnl"].mean())

        for i in range(len(edges) - 1):
            bin_trades = train[train["bin"] == i]
            n = len(bin_trades)
            if n == 0:
                expectancy, pf = float("nan"), float("nan")
            else:
                expectancy = bin_trades["pnl"].mean()
                wins   = bin_trades[bin_trades["pnl"] > 0]["pnl"].sum()
                losses = bin_trades[bin_trades["pnl"] <= 0]["pnl"].sum()
                pf = wins / abs(losses) if losses != 0 else float("inf")

            null_dist = null_bin_expectancies[i]
            if null_dist and n > 0 and not np.isnan(expectancy):
                percentile = float((np.array(null_dist) < expectancy).mean() * 100)
            else:
                percentile = float("nan")

            rows.append({
                "symbol":            symbol,
                "bin":               _bin_label(edges, i),
                "n_train":           n,
                "expectancy":        round(expectancy, 2) if n > 0 else None,
                "pf":                round(pf, 2) if n > 0 and pf != float("inf") else pf,
                "null_dist_n":       len(null_dist),
                "pct_vs_null":       round(percentile, 1) if not np.isnan(percentile) else None,
            })

    verdict_df = pd.DataFrame(rows)
    verdict_df.to_csv("research/H-001-verdict.csv", index=False)
    print("\n" + "=" * 90)
    print("H-001 VERDICT TABLE (TRAIN 2019-2022, bins frozen, read-only in this phase)")
    print("=" * 90)
    print(verdict_df.to_string(index=False))
    print(f"\nSaved -> research/H-001-verdict.csv")
    return verdict_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--verdict", action="store_true")
    args = parser.parse_args()
    if args.freeze:
        freeze_bins()
    elif args.verdict:
        compute_verdict()
    else:
        print("Specify --freeze or --verdict.")
