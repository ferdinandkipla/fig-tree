# research/run_h006_verdict.py
#
# H-006: day-of-week effects. Categorical grouping (like H-002/H-004's
# sessions), no freeze/verdict separation needed. Zero new simulation --
# pure analysis on H-004's existing signed-null sweep.

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SYMBOLS        = ["USDJPY", "XAUUSD", "GBPJPY", "EURUSD", "AUDUSD"]
TRAIN_END      = "2022-01-01"
N_NULL_SEEDS   = 100
N_PERMUTATIONS = 1000
RNG_SEED       = 42
DAYS           = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

NULL_RUNS_DIR = Path("research/null_runs_h004")


def load_pooled_train_trades(symbol: str) -> pd.DataFrame:
    frames = []
    for seed in range(N_NULL_SEEDS):
        path = NULL_RUNS_DIR / f"{symbol}_H1_seed{seed}_trades.csv"
        if not path.exists():
            continue
        df = pd.read_csv(path, parse_dates=["entry_dt"])
        df = df[df["entry_dt"] < TRAIN_END].copy()
        if df.empty:
            continue
        df["day_of_week"] = df["entry_dt"].dt.day_name()
        df["seed"] = seed
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def permutation_test(pooled: pd.DataFrame, rng: np.random.Generator):
    pnl = pooled["pnl"].values
    days = np.array(pooled["day_of_week"].values, dtype=object)
    pooled_mean = pnl.mean()

    observed_means = {d: pnl[days == d].mean() for d in DAYS if (days == d).any()}
    if not observed_means:
        return None, None, {}
    observed_stat = max(abs(m - pooled_mean) for m in observed_means.values())

    perm_stats = np.empty(N_PERMUTATIONS)
    shuffled = days.copy()
    for i in range(N_PERMUTATIONS):
        rng.shuffle(shuffled)
        stat = 0.0
        for d in DAYS:
            mask = shuffled == d
            if mask.any():
                stat = max(stat, abs(pnl[mask].mean() - pooled_mean))
        perm_stats[i] = stat

    p_value = float((perm_stats >= observed_stat).mean())
    return observed_stat, p_value, observed_means


def seed_level_dispersion(pooled: pd.DataFrame) -> dict:
    result = {}
    for d in DAYS:
        per_seed = pooled[pooled["day_of_week"] == d].groupby("seed")["pnl"].mean()
        result[d] = float(per_seed.std()) if len(per_seed) > 1 else float("nan")
    return result


def main():
    rng = np.random.default_rng(RNG_SEED)
    rows = []
    best_worst = {}

    for symbol in SYMBOLS:
        pooled = load_pooled_train_trades(symbol)
        if pooled.empty:
            print(f"{symbol}: no TRAIN trades, skipping.")
            continue

        day_stats = pooled.groupby("day_of_week")["pnl"].agg(["mean", "count"])
        observed_stat, p_value, observed_means = permutation_test(pooled, rng)
        if observed_stat is None:
            continue
        dispersion = seed_level_dispersion(pooled)
        max_dispersion = max(d for d in dispersion.values() if not np.isnan(d))
        effect_exceeds_noise = observed_stat > max_dispersion

        best_day  = max(observed_means, key=observed_means.get)
        worst_day = min(observed_means, key=observed_means.get)
        best_worst[symbol] = (best_day, worst_day)

        min_n = min(int(day_stats.loc[d, "count"]) for d in DAYS if d in observed_means)

        print(f"\n{symbol} (pooled n={len(pooled)}, seeds={pooled['seed'].nunique()}):")
        for d in DAYS:
            if d not in observed_means:
                continue
            n = int(day_stats.loc[d, "count"])
            mean = day_stats.loc[d, "mean"]
            disp = dispersion[d]
            print(f"  {d:10s}  n={n:6d}  expectancy={mean:7.2f}  seed-std={disp:.2f}")
        print(f"  p={p_value:.4f}  observed_stat={observed_stat:.3f}  "
              f"max_seed_dispersion={max_dispersion:.3f}  effect_exceeds_noise={effect_exceeds_noise}")
        print(f"  best={best_day}  worst={worst_day}  min_n={min_n}")

        rows.append({
            "symbol": symbol, "best_day": best_day, "worst_day": worst_day,
            "p_value": round(p_value, 4), "observed_stat": round(observed_stat, 3),
            "max_seed_dispersion": round(max_dispersion, 3),
            "effect_exceeds_noise": effect_exceeds_noise,
            "min_n": min_n, "n_below_30": min_n < 30,
        })

    best_days = set(bw[0] for bw in best_worst.values())
    consistent_best = len(best_days) == 1
    FDR_THRESHOLD = 0.0083
    n_sig_and_real = sum(1 for r in rows if r["p_value"] < FDR_THRESHOLD and r["effect_exceeds_noise"])

    print(f"\n{'='*70}\nCONSISTENCY: best days = {best_days} (consistent: {consistent_best})")
    print(f"SIGNIFICANCE (FDR-adjusted p<{FDR_THRESHOLD}): {n_sig_and_real}/{len(rows)} "
          f"instruments clear BOTH the adjusted threshold AND the dispersion check")

    verdict_df = pd.DataFrame(rows)
    verdict_df.to_csv("research/H-006-verdict.csv", index=False)
    survives = consistent_best and n_sig_and_real >= 4
    print(f"\nPRIMARY CLAIM {'SURVIVES this check' if survives else 'KILLED'}")
    print(f"Saved -> research/H-006-verdict.csv")
    return verdict_df


if __name__ == "__main__":
    main()
