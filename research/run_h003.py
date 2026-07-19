# research/run_h003.py
#
# H-003: time-exit asymmetry. Two-arm counterfactual: Arm A = current
# config (MAX_BARS_IN_TRADE=10), Arm B = time-exit effectively disabled
# (MAX_BARS_IN_TRADE=500, per the registration's implementation note).
# Both arms run against the IDENTICAL prepared signal dataframe -- only
# the exit rule differs.
#
# Cost note: real-strategy A/B is cheap (6 runs total). The null-model
# A/B is expensive -- but Arm A for the null is EXACTLY what M2 already
# computed and saved to research/null_runs/{symbol}_seed{n}_trades.csv
# (same seeds, same n_signals, same MAX_BARS_IN_TRADE=10 default) --
# re-simulating it would be pure waste. Only Arm B (500) needs fresh
# simulation: 100 seeds x 3 symbols = 300 runs, same order of cost as
# the M2 sweep, run in chunks for the same reason (tool-call timeouts).
#
# Usage:
#   python3 research/run_h003.py --real                          # both arms, real strategy, all 3 symbols
#   python3 research/run_h003.py --null-arm-b --seed-start 0 --seed-end 5   # chunked null Arm B
#   python3 research/run_h003.py --verdict                        # combine everything into H-003-verdict.csv

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

SYMBOLS      = ["USDJPY", "XAUUSD", "GBPJPY"]
TRAIN_END    = "2022-01-01"
ARM_A_BARS   = 10    # current shipped config
ARM_B_BARS   = 500   # "time exit disabled" per registration's implementation note
N_NULL_SEEDS = 100

H003_RUNS_DIR = Path("research/h003_runs")
NULL_ARM_B_RESULTS = Path("research/h003_null_arm_results.csv")

_REQUIRED_COLS = ["ema_fast", "ema_slow", "adx", "atr",
                  "ema_distance", "trend_gap",
                  "stop_distance", "target_distance"]


def _resample_signal(common_df: pd.DataFrame, n_signals: int, seed: int) -> pd.DataFrame:
    """Identical to run_null_model.py's helper -- must produce the SAME
    entries as M2's saved null_runs CSVs for the same seed, since Arm A
    for the null model is being REUSED from M2, not re-simulated."""
    df = common_df.copy()
    eligible_mask = df[_REQUIRED_COLS].notna().all(axis=1)
    eligible_idx  = np.flatnonzero(eligible_mask.values)
    n = min(n_signals, len(eligible_idx))
    rng    = np.random.default_rng(seed)
    chosen = rng.choice(eligible_idx, size=n, replace=False)
    df["signal"] = 0
    df.iloc[chosen, df.columns.get_loc("signal")] = 1
    return df.dropna()


def _train_only(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["entry_dt"] = pd.to_datetime(d["entry_dt"])
    return d[d["entry_dt"] < TRAIN_END]


def _expectancy_pf(trades: pd.DataFrame) -> dict:
    if len(trades) == 0:
        return {"n": 0, "expectancy": float("nan"), "pf": float("nan")}
    wins   = trades[trades["pnl"] > 0]["pnl"].sum()
    losses = trades[trades["pnl"] <= 0]["pnl"].sum()
    pf = wins / abs(losses) if losses != 0 else float("inf")
    return {"n": len(trades), "expectancy": trades["pnl"].mean(), "pf": pf}


def run_real_strategy_arms():
    """Cheap: 6 total simulator runs (2 arms x 3 symbols). Real strategy
    only -- the expensive part is the null model's Arm B (separate function)."""
    H003_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    rows = []

    for symbol in SYMBOLS:
        raw_df = fetch(symbol, BACKTEST["timeframe"], BACKTEST["start"], BACKTEST["end"], use_cache=True)
        strategy = TrendPullbackStrategy()
        prepared = strategy.prepare(raw_df.copy(), symbol=symbol)  # SAME entries for both arms

        arm_results = {}
        for arm_name, max_bars in [("A", ARM_A_BARS), ("B", ARM_B_BARS)]:
            sim = Simulator(symbol, entry_features=strategy.entry_features, max_bars_in_trade=max_bars)
            result = sim.run(prepared.copy())
            out_path = H003_RUNS_DIR / f"{symbol}_real_arm{arm_name}_trades.csv"
            result["trades"].to_csv(out_path, index=False)
            arm_results[arm_name] = result

            try:
                record(
                    strategy="trend_pullback", symbols=[symbol],
                    config_snapshot={**strategy.params, "max_bars_in_trade": max_bars, "arm": arm_name},
                    data_paths={symbol: str(cache_path(symbol, BACKTEST["timeframe"]))},
                    output_paths={symbol: str(out_path)},
                    extra={"purpose": "H-003_real_strategy_arm", "arm": arm_name},
                )
            except (DirtyGitStateError, FileNotFoundError) as e:
                print(f"[H-003] Ledger WARNING ({symbol} Arm {arm_name}): {e}")

        train_a = _train_only(arm_results["A"]["trades"])
        train_b = _train_only(arm_results["B"]["trades"])

        stats_a = _expectancy_pf(train_a)
        stats_b = _expectancy_pf(train_b)

        # "Affected trades" per the registration's precise definition:
        # Arm A TRAIN trades with exit_reason==time_exit, PLUS Arm A
        # TRAIN trades whose entry_dt has no match in Arm B's TRAIN list
        # (entries Arm A's faster turnover took that Arm B's longer-held
        # positions blocked).
        n_time_exits = int((train_a["exit_reason"] == "time_exit").sum())
        b_entry_dts  = set(train_b["entry_dt"])
        n_a_only     = int((~train_a["entry_dt"].isin(b_entry_dts)).sum())
        affected     = n_time_exits + n_a_only

        delta_expectancy = stats_a["expectancy"] - stats_b["expectancy"]
        delta_pf         = (stats_a["pf"] - stats_b["pf"]) if np.isfinite(stats_a["pf"]) and np.isfinite(stats_b["pf"]) else float("nan")

        rows.append({
            "symbol": symbol,
            "arm_a_n": stats_a["n"], "arm_a_expectancy": round(stats_a["expectancy"], 2), "arm_a_pf": round(stats_a["pf"], 2),
            "arm_b_n": stats_b["n"], "arm_b_expectancy": round(stats_b["expectancy"], 2), "arm_b_pf": round(stats_b["pf"], 2),
            "delta_expectancy_A_minus_B": round(delta_expectancy, 2),
            "delta_pf_A_minus_B": round(delta_pf, 2) if not np.isnan(delta_pf) else None,
            "n_time_exits_arm_a": n_time_exits,
            "n_a_only_entries": n_a_only,
            "affected_trades": affected,
        })
        print(f"[H-003] {symbol}: Arm A expectancy={stats_a['expectancy']:.2f} (n={stats_a['n']}), "
              f"Arm B expectancy={stats_b['expectancy']:.2f} (n={stats_b['n']}), "
              f"delta(A-B)={delta_expectancy:.2f}, affected_trades={affected}")

    real_df = pd.DataFrame(rows)
    real_df.to_csv("research/h003_real_arm_results.csv", index=False)
    print(f"\nSaved -> research/h003_real_arm_results.csv")
    print(real_df.to_string(index=False))
    return real_df


def run_null_arm_b(seed_start: int = 0, seed_end: int = N_NULL_SEEDS, log_to_ledger: bool = True):
    """Fresh simulation, Arm B only (max_bars=500) -- Arm A is reused
    from M2's already-saved research/null_runs/ CSVs, not re-run here."""
    H003_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    file_exists = NULL_ARM_B_RESULTS.exists()

    for symbol in SYMBOLS:
        raw_df = fetch(symbol, BACKTEST["timeframe"], BACKTEST["start"], BACKTEST["end"], use_cache=True)

        # n_signals must match M2's original matched-frequency count --
        # read it back from one of M2's saved null trade files' sibling
        # ledger entry would be ideal, but simplest reliable source: the
        # real strategy's own full-window signal count (same value M2 used).
        real_prepared = TrendPullbackStrategy().prepare(raw_df.copy(), symbol=symbol)
        n_signals = int(real_prepared["signal"].sum())

        common_df = compute_common_features(raw_df.copy())
        common_df = common_df.iloc[WARMUP_BARS:].copy()

        rows = []
        for seed in range(seed_start, seed_end):
            prepared = _resample_signal(common_df, n_signals, seed)
            sim = Simulator(symbol, entry_features=NullRandomStrategy(n_signals, seed).entry_features,
                            max_bars_in_trade=ARM_B_BARS)
            result = sim.run(prepared)

            if "error" in result or result.get("total_trades", 0) == 0:
                continue

            train_b = _train_only(result["trades"])
            stats_b = _expectancy_pf(train_b)
            rows.append({"symbol": symbol, "seed": seed,
                        "arm_b_expectancy": stats_b["expectancy"], "arm_b_pf": stats_b["pf"],
                        "arm_b_n": stats_b["n"]})

            if log_to_ledger:
                out_path = H003_RUNS_DIR / f"{symbol}_null_seed{seed}_armB_trades.csv"
                result["trades"].to_csv(out_path, index=False)
                try:
                    record(
                        strategy="null_random", symbols=[symbol],
                        config_snapshot={"seed": seed, "n_signals": n_signals, "max_bars_in_trade": ARM_B_BARS, "arm": "B"},
                        data_paths={symbol: str(cache_path(symbol, BACKTEST["timeframe"]))},
                        output_paths={symbol: str(out_path)},
                        seed=seed,
                        extra={"purpose": "H-003_null_arm_B", "n_signals": n_signals},
                    )
                except (DirtyGitStateError, FileNotFoundError) as e:
                    print(f"[H-003] Ledger WARNING ({symbol} seed {seed}): {e}")

        chunk_df = pd.DataFrame(rows)
        chunk_df.to_csv(NULL_ARM_B_RESULTS, mode="a", index=False, header=not file_exists)
        file_exists = True
        print(f"[H-003] {symbol}: appended {len(rows)} null Arm-B results (seeds {seed_start}-{seed_end-1})")


def compute_verdict():
    """Combines real-strategy A/B results with the null Arm-A (from M2)
    vs Arm-B (from run_null_arm_b) comparison into the final H-003
    verdict table, per instrument."""
    real_df = pd.read_csv("research/h003_real_arm_results.csv")
    null_b_df = pd.read_csv(NULL_ARM_B_RESULTS)

    rows = []
    for symbol in SYMBOLS:
        real_row = real_df[real_df["symbol"] == symbol].iloc[0]

        # Null Arm A: reuse M2's saved trades, filtered to TRAIN.
        null_a_expectancies = []
        for seed in range(N_NULL_SEEDS):
            path = Path(f"research/null_runs/{symbol}_seed{seed}_trades.csv")
            if not path.exists():
                continue
            df = pd.read_csv(path)
            train = _train_only(df)
            if len(train) > 0:
                null_a_expectancies.append(train["pnl"].mean())

        null_b_rows = null_b_df[null_b_df["symbol"] == symbol]
        null_b_expectancies = null_b_rows.set_index("seed")["arm_b_expectancy"].to_dict()

        deltas = []
        for seed, exp_b in null_b_expectancies.items():
            # match seed-for-seed against null Arm A (same seed's own A vs its own B)
            path = Path(f"research/null_runs/{symbol}_seed{seed}_trades.csv")
            if not path.exists():
                continue
            df = pd.read_csv(path)
            train_a = _train_only(df)
            if len(train_a) == 0:
                continue
            exp_a = train_a["pnl"].mean()
            deltas.append(exp_a - exp_b)

        deltas = np.array(deltas)
        real_delta = real_row["delta_expectancy_A_minus_B"]
        pct_vs_null = float((deltas < real_delta).mean() * 100) if len(deltas) > 0 else float("nan")
        null_delta_p95 = float(np.percentile(deltas, 95)) if len(deltas) > 0 else float("nan")

        rows.append({
            "symbol": symbol,
            "real_delta_A_minus_B": real_delta,
            "affected_trades": real_row["affected_trades"],
            "null_delta_n": len(deltas),
            "null_delta_mean": round(float(deltas.mean()), 2) if len(deltas) > 0 else None,
            "null_delta_p95": round(null_delta_p95, 2) if len(deltas) > 0 else None,
            "real_delta_pct_vs_null": round(pct_vs_null, 1) if not np.isnan(pct_vs_null) else None,
            "real_delta_exceeds_null_p95": bool(real_delta > null_delta_p95) if len(deltas) > 0 else None,
        })

    verdict_df = pd.DataFrame(rows)
    verdict_df.to_csv("research/H-003-verdict.csv", index=False)
    print("\n" + "=" * 90)
    print("H-003 VERDICT TABLE")
    print("=" * 90)
    print(verdict_df.to_string(index=False))
    print(f"\nSaved -> research/H-003-verdict.csv")
    return verdict_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--real", action="store_true")
    parser.add_argument("--null-arm-b", action="store_true")
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--seed-end", type=int, default=N_NULL_SEEDS)
    parser.add_argument("--verdict", action="store_true")
    parser.add_argument("--no-ledger", action="store_true")
    args = parser.parse_args()

    if args.real:
        run_real_strategy_arms()
    elif args.null_arm_b:
        run_null_arm_b(args.seed_start, args.seed_end, log_to_ledger=not args.no_ledger)
    elif args.verdict:
        compute_verdict()
    else:
        print("Specify --real, --null-arm-b, or --verdict.")
