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

from core.instruments import SESSION_HOURS

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
    entry_dt, seed. (The pre-existing 'session' column is NOT used
    here -- see note below.)

    Splits into thin-session (tokyo, by default) vs all other sessions
    by the bar's ACTUAL CLOCK HOUR against SESSION_HOURS[thin_session],
    computes reversion_k for each retained row.

    IMPORTANT, caught during H-008's first --verdict attempt: the
    pre-existing per-trade 'session' column (execution/simulator.py's
    _active_session) only ever labels a bar with a session name drawn
    from THAT INSTRUMENT'S OWN `sessions` list in core/instruments.py.
    For an instrument whose own list excludes tokyo (EURUSD, XAUUSD,
    GBPJPY), a bar occurring during tokyo clock-hours gets session=NaN,
    NEVER session="tokyo" -- so a naive `df["session"] == "tokyo"`
    filter silently returns zero rows for exactly the three instruments
    the thin-at-tokyo mechanism is about. This is a data-join bug, not
    a market finding: it was caught by inspecting the intermediate
    n_thin=0 output before trusting any verdict, same discipline as the
    H-004 StringArray catch. Fixed here by deriving thin/home
    membership directly from entry_dt's hour-of-day against
    SESSION_HOURS[thin_session], independent of any instrument's
    official session list -- this is the correct operationalization of
    "occurred during Tokyo trading hours" for the mechanism as written,
    which is about actual clock-time liquidity depth, not which
    session label a different pipeline happened to assign.
    """
    df = pooled_top_tercile_trades.copy()
    df["reversion"] = df["entry_dt"].apply(lambda dt: compute_reversion(bars, dt, k))
    df = df.dropna(subset=["reversion"])

    start, end = SESSION_HOURS[thin_session]
    entry_hour = pd.to_datetime(df["entry_dt"]).dt.hour
    thin_mask = (entry_hour >= start) & (entry_hour < end)

    thin = df[thin_mask]
    home = df[~thin_mask]

    return CellData(
        cell_id=symbol,
        thin_reversion=thin["reversion"].to_numpy(dtype=float),
        thin_seeds=thin["seed"].to_numpy(),
        home_reversion=home["reversion"].to_numpy(dtype=float),
        home_seeds=home["seed"].to_numpy(),
    )


def build_cell_calendar(symbol: str, pooled_top_tercile_trades: pd.DataFrame,
                         bars: pd.DataFrame, k: int) -> CellData:
    """
    Calendar-conditioned counterpart to build_cell -- splits by
    near-month-end (research.calendar_distance.is_near_month_end) vs.
    the rest, instead of by session/clock-hour. Used by the H-009
    candidate (month-end proximity x high-volatility). Reuses
    compute_reversion, CellData, permutation_test, and seed_dispersion
    unchanged -- only the group-membership rule differs from
    build_cell.

    pooled_top_tercile_trades: as in build_cell -- must have columns
    entry_dt, seed.
    """
    from research.calendar_distance import is_near_month_end

    df = pooled_top_tercile_trades.copy()
    df["reversion"] = df["entry_dt"].apply(lambda dt: compute_reversion(bars, dt, k))
    df = df.dropna(subset=["reversion"])

    near_me_mask = pd.to_datetime(df["entry_dt"]).apply(lambda ts: is_near_month_end(ts.date()))

    near_me = df[near_me_mask]
    ordinary = df[~near_me_mask]

    return CellData(
        cell_id=symbol,
        thin_reversion=near_me["reversion"].to_numpy(dtype=float),
        thin_seeds=near_me["seed"].to_numpy(),
        home_reversion=ordinary["reversion"].to_numpy(dtype=float),
        home_seeds=ordinary["seed"].to_numpy(),
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
