# research/run_h004_verdict.py
#
# H-004 verdict analysis: session-structure permutation test + the
# mandatory seed-to-seed dispersion check (per H-002's template), run
# against the wider dataset -- 5 instruments at 1H (primary), EURUSD/
# AUDUSD at H4 (secondary, descriptive only per the registration).

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TRAIN_END      = "2022-01-01"
N_NULL_SEEDS   = 100
N_PERMUTATIONS = 1000
SESSIONS       = ["tokyo", "london", "new_york"]
RNG_SEED       = 42

PRIMARY_1H   = ["USDJPY", "XAUUSD", "GBPJPY", "EURUSD", "AUDUSD"]
SECONDARY_H4 = ["EURUSD", "AUDUSD"]


def load_pooled_train_trades(symbol: str, timeframe: str) -> pd.DataFrame:
    frames = []
    for seed in range(N_NULL_SEEDS):
        path = Path(f"research/null_runs_h004/{symbol}_{timeframe}_seed{seed}_trades.csv")
        if not path.exists():
            continue
        df = pd.read_csv(path, parse_dates=["entry_dt"])
        df = df[df["entry_dt"] < TRAIN_END].copy()
        if df.empty:
            continue
        df["seed"] = seed
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def permutation_test(pooled: pd.DataFrame, rng: np.random.Generator):
    pnl = pooled["pnl"].values
    # BUG FOUND AND FIXED: pooled["session"].values can be a pandas
    # StringArray (extension dtype) after pd.concat of many frames, not
    # a plain numpy array. np.random.Generator.shuffle on a StringArray
    # triggers 'not guaranteed to behave correctly... may contain
    # duplicates after shuffling' -- a silent correctness risk that
    # would corrupt every p-value in this analysis. Forcing a plain
    # numpy object array explicitly before any shuffle.
    sessions = np.array(pooled["session"].values, dtype=object)
    pooled_mean = pnl.mean()

    observed_means = {s: pnl[sessions == s].mean() for s in SESSIONS if (sessions == s).any()}
    if not observed_means:
        return None, None, {}
    observed_stat = max(abs(m - pooled_mean) for m in observed_means.values())

    perm_stats = np.empty(N_PERMUTATIONS)
    shuffled = sessions.copy()
    for i in range(N_PERMUTATIONS):
        rng.shuffle(shuffled)
        stat = 0.0
        for s in SESSIONS:
            mask = shuffled == s
            if mask.any():
                stat = max(stat, abs(pnl[mask].mean() - pooled_mean))
        perm_stats[i] = stat

    p_value = float((perm_stats >= observed_stat).mean())
    return observed_stat, p_value, observed_means


def seed_level_dispersion(pooled: pd.DataFrame) -> dict:
    result = {}
    for s in SESSIONS:
        per_seed_means = pooled[pooled["session"] == s].groupby("seed")["pnl"].mean()
        result[s] = {
            "n_seeds": len(per_seed_means),
            "std_across_seeds": float(per_seed_means.std()) if len(per_seed_means) > 1 else float("nan"),
        }
    return result


def analyze(symbols: list, timeframe: str, label: str):
    rows = []
    best_worst = {}
    rng = np.random.default_rng(RNG_SEED)

    print(f"\n{'='*70}\n{label}\n{'='*70}")

    for symbol in symbols:
        pooled = load_pooled_train_trades(symbol, timeframe)
        if pooled.empty:
            print(f"  {symbol}: no TRAIN trades found, skipping.")
            continue

        session_stats = pooled.groupby("session")["pnl"].agg(["mean", "count"])
        observed_stat, p_value, observed_means = permutation_test(pooled, rng)
        if observed_stat is None:
            print(f"  {symbol}: no session data, skipping.")
            continue
        dispersion = seed_level_dispersion(pooled)

        best_session  = max(observed_means, key=observed_means.get)
        worst_session = min(observed_means, key=observed_means.get)
        best_worst[symbol] = (best_session, worst_session)

        min_n = min(int(session_stats.loc[s, "count"]) if s in session_stats.index else 0
                   for s in SESSIONS if s in observed_means)
        max_dispersion = max(d["std_across_seeds"] for d in dispersion.values()
                            if not np.isnan(d["std_across_seeds"]))
        effect_exceeds_noise = observed_stat > max_dispersion

        print(f"\n  {symbol} (n={len(pooled)}, seeds={pooled['seed'].nunique()}):")
        for s in SESSIONS:
            if s not in observed_means:
                continue
            n = int(session_stats.loc[s, "count"])
            mean = session_stats.loc[s, "mean"]
            disp = dispersion[s]["std_across_seeds"]
            print(f"    {s:10s}  n={n:6d}  expectancy={mean:7.2f}  seed-std={disp:.2f}")
        print(f"    p={p_value:.4f}  observed_stat={observed_stat:.3f}  "
              f"max_seed_dispersion={max_dispersion:.3f}  "
              f"effect_exceeds_noise={effect_exceeds_noise}")
        print(f"    best={best_session}  worst={worst_session}  min_n={min_n}")

        rows.append({
            "timeframe": timeframe, "symbol": symbol,
            "best_session": best_session, "worst_session": worst_session,
            "p_value": round(p_value, 4), "observed_stat": round(observed_stat, 3),
            "max_seed_dispersion": round(max_dispersion, 3),
            "effect_exceeds_noise": effect_exceeds_noise,
            "min_n": min_n, "n_below_30": min_n < 30,
        })

    best_sessions  = set(bw[0] for bw in best_worst.values())
    worst_sessions = set(bw[1] for bw in best_worst.values())
    consistent_best  = len(best_sessions) == 1
    consistent_worst = len(worst_sessions) == 1
    n_significant = sum(1 for r in rows if r["p_value"] < 0.05)
    n_significant_and_real = sum(1 for r in rows if r["p_value"] < 0.05 and r["effect_exceeds_noise"])

    print(f"\n  CONSISTENCY: best sessions = {best_sessions} (consistent: {consistent_best})")
    print(f"               worst sessions = {worst_sessions} (consistent: {consistent_worst})")
    print(f"  SIGNIFICANCE: {n_significant}/{len(rows)} instruments p<0.05, "
          f"{n_significant_and_real}/{len(rows)} ALSO exceed seed-dispersion noise")

    return pd.DataFrame(rows), consistent_best, n_significant_and_real, len(rows)


if __name__ == "__main__":
    primary_df, cbest, nsig_real, ntotal = analyze(PRIMARY_1H, "H1", "PRIMARY: 1H, all 5 instruments")
    secondary_df, _, _, _ = analyze(SECONDARY_H4, "H4", "SECONDARY (descriptive only): H4, EURUSD/AUDUSD")

    combined = pd.concat([primary_df, secondary_df], ignore_index=True)
    combined.to_csv("research/H-004-verdict.csv", index=False)

    print(f"\n{'='*70}\nPRIMARY CLAIM CHECK\n{'='*70}")
    print(f"Consistent best session across all 5: {cbest}")
    print(f"Instruments with p<0.05 AND effect > seed noise: {nsig_real}/{ntotal} (need >=4/5)")
    survives = cbest and nsig_real >= 4
    print(f"\nPRIMARY CLAIM {'SURVIVES this check' if survives else 'KILLED'}")
    print(f"\nSaved -> research/H-004-verdict.csv")
