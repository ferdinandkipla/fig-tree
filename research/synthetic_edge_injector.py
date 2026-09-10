# research/synthetic_edge_injector.py
#
# Power calibration: can the adjudication pipeline detect a real edge
# of known size? See research/POWER_CALIBRATION_PLAN.md for the full
# design and reasoning.
#
# Reuses research/null_runs_h004/'s existing 100-seed matched-frequency
# trade sweep. Zero new data. Injection unit is PIPS (consistent with
# every other cost/edge unit already in this codebase), not basis
# points.

import glob
from dataclasses import dataclass

import numpy as np
import pandas as pd


def load_pooled_trades(symbol: str, train_end: str = "2022-01-01") -> pd.DataFrame:
    """Pooled 100-seed TRAIN-window null trades for one instrument,
    same data source as H-005/H-008/H-009."""
    frames = []
    for path in glob.glob(f"research/null_runs_h004/{symbol}_H1_seed*_trades.csv"):
        df = pd.read_csv(path, parse_dates=["entry_dt"])
        frames.append(df)
    pooled = pd.concat(frames, ignore_index=True)
    pooled = pooled[pooled["entry_dt"] < train_end].reset_index(drop=True)
    return pooled


def inject_edge(pooled: pd.DataFrame, symbol: str, treatment_mask: np.ndarray,
                 edge_pips: float, pip_value: float) -> pd.DataFrame:
    """
    Injects a KNOWN, deterministic edge of `edge_pips` into the
    treatment-masked rows' pnl, using the identical unit convention
    every cost term in this codebase already uses:
    dollar_shift = edge_pips * pip_value * size (per trade, so larger
    positions receive a proportionally larger dollar shift, matching
    how real edges would scale with position size).

    Returns a COPY with a new 'pnl' column -- never mutates the
    original pooled trades (which remain the untouched null/control
    reference for other analyses).
    """
    df = pooled.copy()
    injected_shift = np.where(treatment_mask, edge_pips * pip_value * df["size"].values, 0.0)
    df["pnl"] = df["pnl"].values + injected_shift
    df["_treatment"] = treatment_mask
    return df


def max_deviation_permutation_test(pnl: np.ndarray, group: np.ndarray,
                                    n_permutations: int, rng: np.random.Generator):
    """
    Replicates research/run_h005.py's compute_verdict() detection
    machinery exactly (confirmed by direct inspection before this
    function was written) -- max |group_mean - pooled_mean| permutation
    test. `group` is a boolean or categorical array (treatment/control
    here; tercile membership in the real hypothesis).
    """
    pooled_mean = pnl.mean()
    groups = np.unique(group)
    observed_means = {g: pnl[group == g].mean() for g in groups}
    observed_stat = max(abs(m - pooled_mean) for m in observed_means.values())

    perm_stats = np.empty(n_permutations)
    shuffled = group.copy()
    for i in range(n_permutations):
        rng.shuffle(shuffled)
        stat = 0.0
        for g in groups:
            mask = shuffled == g
            if mask.any():
                stat = max(stat, abs(pnl[mask].mean() - pooled_mean))
        perm_stats[i] = stat
    p_value = float((perm_stats >= observed_stat).mean())
    return observed_stat, p_value, observed_means


def seed_dispersion_check(df: pd.DataFrame, group_col: str, pnl_col: str = "pnl") -> tuple:
    """Same dispersion check as run_h005.py: per-seed group means' std,
    across groups, take the max as the noise floor."""
    dispersion = {}
    for g in df[group_col].unique():
        per_seed = df[df[group_col] == g].groupby("seed")[pnl_col].mean()
        dispersion[g] = float(per_seed.std()) if len(per_seed) > 1 else float("nan")
    valid = [d for d in dispersion.values() if not np.isnan(d)]
    max_dispersion = max(valid) if valid else float("nan")
    return dispersion, max_dispersion


@dataclass
class DetectionResult:
    edge_pips: float
    p_value: float
    observed_stat: float
    max_dispersion: float
    detected: bool  # p < alpha AND observed_stat > max_dispersion -- the exact dual gate


def run_single_trial(pooled: pd.DataFrame, symbol: str, edge_pips: float, pip_value: float,
                      treatment_fraction: float, n_permutations: int,
                      rng: np.random.Generator, alpha: float = 0.05) -> DetectionResult:
    n = len(pooled)
    treatment_mask = rng.random(n) < treatment_fraction
    injected = inject_edge(pooled, symbol, treatment_mask, edge_pips, pip_value)

    pnl = injected["pnl"].values
    group = injected["_treatment"].values
    observed_stat, p_value, _ = max_deviation_permutation_test(pnl, group, n_permutations, rng)
    _, max_dispersion = seed_dispersion_check(injected, "_treatment")

    detected = bool((p_value < alpha) and (not np.isnan(max_dispersion)) and (observed_stat > max_dispersion))
    return DetectionResult(edge_pips=edge_pips, p_value=p_value, observed_stat=observed_stat,
                            max_dispersion=max_dispersion, detected=detected)
