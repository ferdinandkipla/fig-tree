# research/run_h005.py
#
# H-005: volatility regime. Freeze-then-verdict phase separation,
# identical discipline to research/run_h001.py -- --freeze computes
# and commits ATR-at-entry tercile edges per instrument (TRAIN only)
# and REFUSES to compute any statistic; --verdict is a separate, later
# invocation that only reads the frozen file back from disk.
#
# Zero new simulation: reads H-004's existing signed-null sweep
# (research/null_runs_h004/), which already captures atr_entry.
#
# Usage:
#   python research/run_h005.py --freeze
#   python research/run_h005.py --verdict

import sys
import json
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from research.experiment import record, DirtyGitStateError
from data.loader import cache_path
from core.config import BACKTEST

SYMBOLS      = ["USDJPY", "XAUUSD", "GBPJPY", "EURUSD", "AUDUSD"]
TRAIN_END    = "2022-01-01"
N_NULL_SEEDS = 100
N_PERMUTATIONS = 1000
RNG_SEED = 42

BINS_PATH = Path("research/registry/H-005-bins.json")
NULL_RUNS_DIR = Path("research/null_runs_h004")


def _load_pooled_train_trades(symbol: str) -> pd.DataFrame:
    frames = []
    for seed in range(N_NULL_SEEDS):
        path = NULL_RUNS_DIR / f"{symbol}_H1_seed{seed}_trades.csv"
        if not path.exists():
            continue
        df = pd.read_csv(path, parse_dates=["entry_dt"])
        df = df[df["entry_dt"] < TRAIN_END].copy()
        if df.empty:
            continue
        df["seed"] = seed
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def freeze_bins():
    """PHASE 1. Computes atr_entry tercile edges per instrument on
    TRAIN-window pooled null trades. Writes to research/registry/H-005-bins.json
    and logs a ledger entry BEFORE any tercile statistic is computed."""
    all_bins = {}
    for symbol in SYMBOLS:
        pooled = _load_pooled_train_trades(symbol)
        if len(pooled) < 90:
            print(f"[H-005] WARNING: {symbol} has only {len(pooled)} pooled TRAIN "
                  f"trades, tercile binning may be unreliable.")
        _, edges = pd.qcut(pooled["atr_entry"], q=3, retbins=True, duplicates="drop")
        all_bins[symbol] = {"edges": edges.tolist(), "n_pooled_trades": len(pooled)}
        print(f"[H-005] {symbol}: pooled n={len(pooled)}, "
              f"atr_entry tercile edges = {[round(e,5) for e in edges]}")

    BINS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(BINS_PATH, "w") as f:
        json.dump({"hypothesis": "H-005", "train_end": TRAIN_END,
                   "bins_by_symbol": all_bins}, f, indent=2)
    print(f"[H-005] Frozen bin edges written -> {BINS_PATH}")

    try:
        entry = record(
            strategy="H-005-binning", symbols=SYMBOLS,
            config_snapshot={"train_end": TRAIN_END, "bins_by_symbol": all_bins},
            data_paths={s: str(cache_path(s, BACKTEST["timeframe"])) for s in SYMBOLS},
            output_paths={s: f"research/null_runs_h004/{s}_H1_seed0_trades.csv" for s in SYMBOLS},
            extra={"purpose": "H-005_bin_freeze", "bins_path": str(BINS_PATH)},
        )
        print(f"[H-005] Bin freeze logged to ledger: {entry['run_id']}")
    except (DirtyGitStateError, FileNotFoundError) as e:
        print(f"[H-005] Ledger WARNING (bin freeze not logged): {e}")

    print("\n[H-005] Bins are now FROZEN. Do not re-run --freeze after "
          "viewing --verdict output.")


def _tercile_label(edges, i):
    return f"T{i+1} [{edges[i]:.5f}, {edges[i+1]:.5f}]"


def compute_verdict():
    """PHASE 2. Reads frozen bin edges from disk (never recomputes),
    runs the permutation test + seed-dispersion check per instrument."""
    if not BINS_PATH.exists():
        raise RuntimeError(f"{BINS_PATH} not found -- run --freeze first.")

    with open(BINS_PATH) as f:
        frozen = json.load(f)

    rng = np.random.default_rng(RNG_SEED)
    rows = []
    best_worst = {}

    for symbol in SYMBOLS:
        edges = frozen["bins_by_symbol"][symbol]["edges"]
        pooled = _load_pooled_train_trades(symbol)
        pooled["tercile"] = pd.cut(pooled["atr_entry"], bins=edges,
                                   labels=False, include_lowest=True)

        pnl = pooled["pnl"].values
        tercile_arr = np.array(pooled["tercile"].values, dtype=object)
        pooled_mean = pnl.mean()

        n_terciles = len(edges) - 1
        observed_means = {}
        for t in range(n_terciles):
            mask = tercile_arr == t
            if mask.any():
                observed_means[t] = pnl[mask].mean()
        observed_stat = max(abs(m - pooled_mean) for m in observed_means.values())

        perm_stats = np.empty(N_PERMUTATIONS)
        shuffled = tercile_arr.copy()
        for i in range(N_PERMUTATIONS):
            rng.shuffle(shuffled)
            stat = 0.0
            for t in range(n_terciles):
                mask = shuffled == t
                if mask.any():
                    stat = max(stat, abs(pnl[mask].mean() - pooled_mean))
            perm_stats[i] = stat
        p_value = float((perm_stats >= observed_stat).mean())

        dispersion = {}
        for t in range(n_terciles):
            per_seed = pooled[pooled["tercile"] == t].groupby("seed")["pnl"].mean()
            dispersion[t] = float(per_seed.std()) if len(per_seed) > 1 else float("nan")
        max_dispersion = max(d for d in dispersion.values() if not np.isnan(d))
        effect_exceeds_noise = observed_stat > max_dispersion

        best_t  = max(observed_means, key=observed_means.get)
        worst_t = min(observed_means, key=observed_means.get)
        best_worst[symbol] = (best_t, worst_t)

        print(f"\n{symbol} (pooled n={len(pooled)}, seeds={pooled['seed'].nunique()}):")
        for t in range(n_terciles):
            n = int((pooled['tercile']==t).sum())
            mean = observed_means.get(t, float('nan'))
            disp = dispersion.get(t, float('nan'))
            print(f"  {_tercile_label(edges,t):30s} n={n:6d}  expectancy={mean:7.2f}  seed-std={disp:.2f}")
        print(f"  p={p_value:.4f}  observed_stat={observed_stat:.3f}  "
              f"max_seed_dispersion={max_dispersion:.3f}  effect_exceeds_noise={effect_exceeds_noise}")
        print(f"  best=T{best_t+1}  worst=T{worst_t+1}")

        rows.append({
            "symbol": symbol, "best_tercile": best_t+1, "worst_tercile": worst_t+1,
            "p_value": round(p_value,4), "observed_stat": round(observed_stat,3),
            "max_seed_dispersion": round(max_dispersion,3),
            "effect_exceeds_noise": effect_exceeds_noise,
            "n_pooled": len(pooled),
        })

    best_terciles = set(bw[0] for bw in best_worst.values())
    n_sig_and_real = sum(1 for r in rows if r["p_value"] < 0.01 and r["effect_exceeds_noise"])
    consistent_best = len(best_terciles) == 1

    print(f"\n{'='*70}\nCONSISTENCY: best terciles = {best_terciles} (consistent: {consistent_best})")
    print(f"SIGNIFICANCE (FDR-adjusted p<0.01): {n_sig_and_real}/{len(rows)} instruments "
          f"clear BOTH the adjusted threshold AND the noise-dispersion check")

    verdict_df = pd.DataFrame(rows)
    verdict_df.to_csv("research/H-005-verdict.csv", index=False)
    survives = consistent_best and n_sig_and_real >= 4
    print(f"\nPRIMARY CLAIM {'SURVIVES this check' if survives else 'KILLED'}")
    print(f"Saved -> research/H-005-verdict.csv")
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
