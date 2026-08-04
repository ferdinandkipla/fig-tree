# research/interaction_harness.py
#
# The interaction-capable per-cell analysis harness required by
# CONDITIONAL_SEARCH_CHARTER.md before H-008 (or any future
# interaction hypothesis) can be adjudicated. Kept separate from
# run_h008.py so it can be imported and validated on synthetic,
# known-answer data (tests/test_interaction_harness.py) BEFORE it
# touches research/null_runs_h004/'s real data -- the StringArray-bug
# precedent (LESSONS_LEARNED.md Sec 3.4) is the reason for this split.

from pathlib import Path
from dataclasses import dataclass

import numpy as np
import pandas as pd

STORAGE_DIR = Path("data/storage")
# MT5 timeframe constants (mt5.TIMEFRAME_H1 = 16385); hardcoded here
# rather than imported from the mt5 package, which requires a live
# terminal and cannot be imported in this sandboxed analysis context
# (see AI_ONBOARDING / non-negotiable rules: stub MT5, never fabricate
# data -- these are real cached bars, not fabricated).
H1_SUFFIX = "16385"


def load_h1_bars(symbol: str) -> pd.DataFrame:
    """Loads the real, cached H1 OHLC series for `symbol` from
    data/storage/. Returns a DataFrame indexed by datetime, sorted
    ascending, with at least a 'close' column."""
    path = STORAGE_DIR / f"{symbol}_{H1_SUFFIX}.csv"
    df = pd.read_csv(path, index_col="datetime", parse_dates=True)
    return df.sort_index()


def compute_reversion(bars: pd.DataFrame, entry_dt, k: int):
    """
    reversion_k = -sign(r0) * (close[t+k] - close[t])
    where r0 = close[t] - close[t-1] (the entry bar's own close-to-close
    return, i.e. the 'shock' direction) and t is the bar at entry_dt.

    Returns None if entry_dt is not found in bars, or if t-1 or t+k
    fall outside the available series (no fabrication of edge values).
    """
    idx = bars.index
    if entry_dt not in idx:
        return None
    pos = idx.get_loc(entry_dt)
    if pos - 1 < 0 or pos + k >= len(idx):
        return None
    close = bars["close"].values
    r0 = close[pos] - close[pos - 1]
    if r0 == 0:
        return None  # undefined sign, exclude rather than fabricate a direction
    return float(-np.sign(r0) * (close[pos + k] - close[pos]))


@dataclass
class CellData:
    cell_id: str          # e.g. "EURUSD"
    thin_reversion: np.ndarray   # reversion values, tokyo-session, top ATR tercile
    thin_seeds: np.ndarray       # seed id per thin_reversion entry
    home_reversion: np.ndarray   # reversion values, non-tokyo session, top ATR tercile
    home_seeds: np.ndarray


def build_cell(symbol: str, pooled_top_tercile_trades: pd.DataFrame,
               bars: pd.DataFrame, k: int, thin_session: str = "tokyo") -> CellData:
    """
    pooled_top_tercile_trades: the pooled (across seeds), TRAIN-window,
    TOP-ATR-tercile-only null trades for `symbol` (already filtered by
    the caller using the frozen H-005 bin edges). Must have columns
    entry_dt, session, seed.

    Splits into thin-session (tokyo, by default -- per instrument this
    may be a HOME session; the caller/run_h008.py decides which
    instruments this split is meaningful for) vs all other sessions,
    computes reversion_k for each retained row.
    """
    df = pooled_top_tercile_trades.copy()
    df["reversion"] = df["entry_dt"].apply(lambda dt: compute_reversion(bars, dt, k))
    df = df.dropna(subset=["reversion"])

    thin = df[df["session"] == thin_session]
    home = df[df["session"] != thin_session]

    return CellData(
        cell_id=symbol,
        thin_reversion=thin["reversion"].to_numpy(dtype=float),
        thin_seeds=thin["seed"].to_numpy(),
        home_reversion=home["reversion"].to_numpy(dtype=float),
        home_seeds=home["seed"].to_numpy(),
    )


def permutation_test(cell: CellData, n_permutations: int, rng: np.random.Generator):
    """
    Two-sample permutation test on the difference of means
    (thin_mean - home_mean). Returns (observed_diff, p_value_two_sided).

    If either group is empty, returns (nan, nan) -- insufficient data,
    handled by the caller as its own kill-criterion category, not
    silently coerced to non-significant.
    """
    if len(cell.thin_reversion) == 0 or len(cell.home_reversion) == 0:
        return float("nan"), float("nan")

    pooled = np.concatenate([cell.thin_reversion, cell.home_reversion])
    n_thin = len(cell.thin_reversion)
    observed = cell.thin_reversion.mean() - cell.home_reversion.mean()

    perm_diffs = np.empty(n_permutations)
    idx = np.arange(len(pooled))
    for i in range(n_permutations):
        rng.shuffle(idx)
        thin_idx = idx[:n_thin]
        home_idx = idx[n_thin:]
        perm_diffs[i] = pooled[thin_idx].mean() - pooled[home_idx].mean()

    p_value = float((np.abs(perm_diffs) >= abs(observed)).mean())
    return float(observed), p_value


def seed_dispersion(reversion: np.ndarray, seeds: np.ndarray) -> float:
    """
    Seed-to-seed dispersion check (mandatory per LESSONS_LEARNED.md
    Sec 2 / the H-002/H-004/H-005 precedent): std of per-seed means.
    Returns nan if fewer than 2 seeds have data (dispersion undefined,
    not zero -- caller must treat nan as 'cannot clear this check',
    never as 'passes trivially').
    """
    if len(reversion) == 0:
        return float("nan")
    per_seed = pd.Series(reversion, index=seeds).groupby(level=0).mean()
    if len(per_seed) < 2:
        return float("nan")
    return float(per_seed.std())
