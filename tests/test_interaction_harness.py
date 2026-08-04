# tests/test_interaction_harness.py
#
# Known-answer validation for research/interaction_harness.py, per
# ENGINEERING_STANDARDS.md Sec 2 and the StringArray-bug precedent
# (LESSONS_LEARNED.md Sec 3.4): validated on synthetic data with a
# KNOWN engineered effect and a KNOWN true-null before it is trusted
# to adjudicate H-008's real cells.

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from research.interaction_harness import (
    compute_reversion, build_cell, permutation_test, seed_dispersion,
)


def _make_bars(n=200, seed=0):
    """Synthetic H1 bar series: random-walk close prices, hourly."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=n, freq="h")
    steps = rng.normal(0, 1.0, size=n)
    close = 100 + np.cumsum(steps)
    return pd.DataFrame({"close": close}, index=idx)


def test_compute_reversion_known_shock_and_full_reversion():
    """
    Hand-constructed bars where the answer is known exactly:
    bar t-1 close=100, bar t close=105 (r0=+5, an up-shock),
    bar t+1 close=103, bar t+3 close=100.
    reversion_1 = -sign(+5)*(103-105) = -1*(-2) = +2 (partial reversion)
    reversion_3 = -sign(+5)*(100-105) = -1*(-5) = +5 (full reversion)
    """
    idx = pd.date_range("2020-01-01", periods=6, freq="h")
    closes = [100, 100, 105, 103, 104, 100]
    #          t-2  t-1   t   t+1  t+2  t+3
    bars = pd.DataFrame({"close": closes}, index=idx)
    entry_dt = idx[2]  # the shock bar

    assert compute_reversion(bars, entry_dt, k=1) == pytest.approx(2.0)
    assert compute_reversion(bars, entry_dt, k=3) == pytest.approx(5.0)


def test_compute_reversion_continuation_gives_negative_value():
    """Shock continues in the same direction -> negative 'reversion'
    (i.e. correctly signed as anti-reversion/continuation)."""
    idx = pd.date_range("2020-01-01", periods=4, freq="h")
    closes = [100, 100, 105, 110]  # up-shock, then continues up
    bars = pd.DataFrame({"close": closes}, index=idx)
    entry_dt = idx[2]
    # r0=+5, reversion_1 = -1*(110-105) = -5 (continuation, not reversion)
    assert compute_reversion(bars, entry_dt, k=1) == pytest.approx(-5.0)


def test_compute_reversion_out_of_range_returns_none():
    idx = pd.date_range("2020-01-01", periods=3, freq="h")
    bars = pd.DataFrame({"close": [100, 101, 102]}, index=idx)
    assert compute_reversion(bars, idx[0], k=1) is None   # no t-1
    assert compute_reversion(bars, idx[2], k=1) is None   # no t+1
    assert compute_reversion(bars, idx[1] + pd.Timedelta("100h"), k=1) is None  # missing dt


def test_engineered_effect_recovered_by_permutation_test():
    """
    THE core known-answer case: build a synthetic cell where thin-
    session reversion is engineered to be strongly positive
    (mean +3.0, small noise) and home-session reversion is engineered
    to be centered at 0 (small noise). The harness must recover a
    large observed difference and a p-value indicating significance.
    A harness that fails to detect this cannot be trusted on H-008.
    """
    rng = np.random.default_rng(42)
    n_thin, n_home = 60, 60
    thin_reversion = rng.normal(3.0, 1.0, size=n_thin)
    home_reversion = rng.normal(0.0, 1.0, size=n_home)

    from research.interaction_harness import CellData
    cell = CellData(
        cell_id="SYNTH",
        thin_reversion=thin_reversion,
        thin_seeds=np.arange(n_thin) % 10,   # 10 pseudo-seeds
        home_reversion=home_reversion,
        home_seeds=np.arange(n_home) % 10,
    )
    observed, p_value = permutation_test(cell, n_permutations=2000,
                                          rng=np.random.default_rng(1))
    assert observed == pytest.approx(3.0, abs=0.6)
    assert p_value < 0.01, (
        f"engineered effect (thin mean=3.0 vs home mean=0.0, n=60 each) "
        f"was not detected as significant (p={p_value}) -- harness is "
        f"not sensitive enough to trust on real H-008 data."
    )


def test_true_null_recovered_by_permutation_test():
    """
    Calibration control: BOTH groups drawn from the SAME distribution
    (no engineered effect). The harness must NOT report significance
    here -- a harness that finds 'signal' in a true null is exactly
    the false-acceptance failure mode LESSONS_LEARNED.md Sec 3.5 warns
    against, now at the harness-validation stage instead of the
    adjudication stage.
    """
    rng = np.random.default_rng(7)
    n = 60
    thin_reversion = rng.normal(0.0, 1.0, size=n)
    home_reversion = rng.normal(0.0, 1.0, size=n)

    from research.interaction_harness import CellData
    cell = CellData(
        cell_id="SYNTH_NULL",
        thin_reversion=thin_reversion,
        thin_seeds=np.arange(n) % 10,
        home_reversion=home_reversion,
        home_seeds=np.arange(n) % 10,
    )
    observed, p_value = permutation_test(cell, n_permutations=2000,
                                          rng=np.random.default_rng(2))
    assert p_value > 0.05, (
        f"true-null synthetic data (both groups drawn from identical "
        f"distributions) produced p={p_value} < 0.05 -- either an "
        f"unlucky draw or a miscalibrated test statistic; investigate "
        f"before trusting this harness on real data."
    )


def test_permutation_test_empty_group_returns_nan_not_zero():
    """An empty group must surface as 'cannot test', never silently
    coerced into a spuriously confident result."""
    from research.interaction_harness import CellData
    cell = CellData(
        cell_id="EMPTY_HOME",
        thin_reversion=np.array([1.0, 2.0, 3.0]),
        thin_seeds=np.array([0, 1, 2]),
        home_reversion=np.array([]),
        home_seeds=np.array([]),
    )
    observed, p_value = permutation_test(cell, n_permutations=100,
                                          rng=np.random.default_rng(0))
    assert np.isnan(observed) and np.isnan(p_value)


def test_seed_dispersion_known_values():
    """Hand-computed: 3 seeds, per-seed means 1.0, 2.0, 3.0 ->
    population std of [1,2,3] with ddof=1 (pandas default) = 1.0."""
    reversion = np.array([1.0, 1.0, 2.0, 2.0, 3.0, 3.0])
    seeds = np.array([0, 0, 1, 1, 2, 2])
    result = seed_dispersion(reversion, seeds)
    assert result == pytest.approx(1.0)


def test_seed_dispersion_single_seed_returns_nan():
    """Cannot compute a std across seeds when only one seed has data --
    must be nan, not 0.0 (which would wrongly read as 'zero noise')."""
    reversion = np.array([1.0, 2.0, 3.0])
    seeds = np.array([0, 0, 0])
    assert np.isnan(seed_dispersion(reversion, seeds))


def test_build_cell_thin_home_split_is_correct():
    """End-to-end on synthetic bars + synthetic trades: verify the
    thin/home split lands the right rows in the right bucket and that
    reversion values match hand computation."""
    bars = _make_bars(n=20, seed=1)
    idx = bars.index

    trades = pd.DataFrame({
        "entry_dt": [idx[5], idx[10], idx[15]],
        "session": ["tokyo", "london", "tokyo"],
        "seed": [0, 0, 1],
    })

    cell = build_cell("SYNTH", trades, bars, k=1, thin_session="tokyo")
    assert len(cell.thin_reversion) == 2   # idx[5], idx[15]
    assert len(cell.home_reversion) == 1   # idx[10]

    expected_5 = compute_reversion(bars, idx[5], 1)
    expected_15 = compute_reversion(bars, idx[15], 1)
    assert set(cell.thin_reversion) == {expected_5, expected_15}
