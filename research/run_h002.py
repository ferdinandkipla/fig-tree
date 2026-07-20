# research/run_h002.py
#
# H-002 (reframed): session structure in the null model's random long
# entries. Pure analysis on data M2 already produced -- no new
# simulation runs, no new ledger surface area, per the registration.

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SYMBOLS      = ["USDJPY", "XAUUSD", "GBPJPY"]
TRAIN_END    = "2022-01-01"
N_NULL_SEEDS = 100
N_PERMUTATIONS = 1000
SESSIONS     = ["tokyo", "london", "new_york"]
RNG_SEED     = 42  # for the permutation shuffle itself


def _load_all_train_null_trades(symbol: str) -> pd.DataFrame:
    """Pools TRAIN-window trades across all 100 null-model seeds for one
    instrument, tagging each row with its source seed (needed for the
    seed-level dispersion check)."""
    frames = []
    for seed in range(N_NULL_SEEDS):
        path = Path(f"research/null_runs/{symbol}_seed{seed}_trades.csv")
        if not path.exists():
            continue
        df = pd.read_csv(path, parse_dates=["entry_dt"])
        df = df[df["entry_dt"] < TRAIN_END].copy()
        if df.empty:
            continue
        df["seed"] = seed
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _permutation_test(df: pd.DataFrame, rng: np.random.Generator) -> dict:
    """Shuffle session labels within instrument N_PERMUTATIONS times;
    observed statistic is max|session_mean - pooled_mean|. p-value is
    the fraction of shuffles reaching >= the observed statistic."""
    pooled_mean = df["pnl"].mean()
    observed_means = df.groupby("session")["pnl"].mean()
    observed_stat = (observed_means - pooled_mean).abs().max()

    pnl_values = df["pnl"].values
    session_values = df["session"].values.copy()
    n = len(df)

    perm_stats = np.empty(N_PERMUTATIONS)
    for i in range(N_PERMUTATIONS):
        shuffled = rng.permutation(session_values)
        tmp = pd.DataFrame({"session": shuffled, "pnl": pnl_values})
        means = tmp.groupby("session")["pnl"].mean()
        perm_stats[i] = (means - pooled_mean).abs().max()

    p_value = float((perm_stats >= observed_stat).mean())
    return {
        "observed_stat": observed_stat,
        "p_value": p_value,
        "session_means": observed_means.to_dict(),
    }


def _seed_level_dispersion(df: pd.DataFrame) -> dict:
    """Per-seed, per-session expectancy -- std across the 100 seeds,
    to sanity-check the pooled permutation result against seed-to-seed
    noise (guards against the seed-pseudoreplication risk flagged in
    the registration)."""
    per_seed = df.groupby(["seed", "session"])["pnl"].mean().unstack("session")
    return {sess: per_seed[sess].std() for sess in per_seed.columns if sess in per_seed}


def main():
    rng = np.random.default_rng(RNG_SEED)
    rows = []
    session_means_by_symbol = {}

    for symbol in SYMBOLS:
        df = _load_all_train_null_trades(symbol)
        if df.empty:
            print(f"[H-002] No TRAIN null data for {symbol}, skipping.")
            continue

        bucket_n = df.groupby("session").size()
        min_bucket_n = int(bucket_n.min())

        perm_result = _permutation_test(df, rng)
        dispersion  = _seed_level_dispersion(df)

        session_means_by_symbol[symbol] = perm_result["session_means"]

        best_session  = max(perm_result["session_means"], key=perm_result["session_means"].get)
        worst_session = min(perm_result["session_means"], key=perm_result["session_means"].get)

        print(f"\n{'='*70}\n{symbol}\n{'='*70}")
        print(f"Pooled n = {len(df)} (across {df['seed'].nunique()} seeds)")
        print(f"Bucket sizes: {bucket_n.to_dict()}  (min={min_bucket_n})")
        print(f"Session means: { {k: round(v,2) for k,v in perm_result['session_means'].items()} }")
        print(f"Seed-level dispersion (std): { {k: round(v,2) for k,v in dispersion.items()} }")
        print(f"Observed stat: {perm_result['observed_stat']:.2f}  p-value: {perm_result['p_value']:.4f}")
        print(f"Best session: {best_session}  Worst session: {worst_session}")

        # Sanity flag: is the apparent effect (observed_stat) smaller
        # than seed-to-seed noise? If so, the p-value shouldn't be
        # trusted at face value, per the registration's design note 2.
        max_dispersion = max(dispersion.values()) if dispersion else float("nan")
        effect_vs_noise_flag = perm_result["observed_stat"] < max_dispersion

        rows.append({
            "symbol": symbol,
            "n_pooled": len(df),
            "min_bucket_n": min_bucket_n,
            "tokyo_mean": round(perm_result["session_means"].get("tokyo", np.nan), 3),
            "london_mean": round(perm_result["session_means"].get("london", np.nan), 3),
            "new_york_mean": round(perm_result["session_means"].get("new_york", np.nan), 3),
            "observed_stat": round(perm_result["observed_stat"], 3),
            "p_value": perm_result["p_value"],
            "best_session": best_session,
            "worst_session": worst_session,
            "max_seed_dispersion": round(max_dispersion, 3),
            "effect_smaller_than_seed_noise": effect_vs_noise_flag,
        })

    result_df = pd.DataFrame(rows)

    # Consistency check across instruments -- the binding criterion.
    best_sessions  = result_df["best_session"].tolist()
    worst_sessions = result_df["worst_session"].tolist()
    consistent_best  = len(set(best_sessions)) == 1
    consistent_worst = len(set(worst_sessions)) == 1
    any_p_above_05   = (result_df["p_value"] > 0.05).any()
    any_below_30_n   = (result_df["min_bucket_n"] < 30).any()
    any_noise_flag   = result_df["effect_smaller_than_seed_noise"].any()

    print("\n" + "="*70)
    print("H-002 VERDICT SUMMARY")
    print("="*70)
    print(result_df.to_string(index=False))
    print(f"\nConsistent best session across instruments: {consistent_best} ({best_sessions})")
    print(f"Consistent worst session across instruments: {consistent_worst} ({worst_sessions})")
    print(f"Any p-value > 0.05: {any_p_above_05}")
    print(f"Any bucket n < 30: {any_below_30_n}")
    print(f"Any instrument where effect < seed-to-seed noise: {any_noise_flag}")

    killed = any_p_above_05 or (not consistent_best) or (not consistent_worst) or any_below_30_n
    print(f"\nVERDICT: {'KILLED' if killed else 'SURVIVES (pending cost-stress check)'}")

    result_df.to_csv("research/H-002-verdict.csv", index=False)
    print("Saved -> research/H-002-verdict.csv")
    return result_df


if __name__ == "__main__":
    main()
