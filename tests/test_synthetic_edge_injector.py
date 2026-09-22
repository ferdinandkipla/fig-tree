# tests/test_synthetic_edge_injector.py
#
# Known-answer validation for research/synthetic_edge_injector.py, per
# ENGINEERING_STANDARDS.md Sec 2. Validates the injection mechanism in
# isolation from the detection statistic (permutation test / dispersion
# check) -- a power curve is only meaningful if the injected edge is
# exactly what it claims to be.

import numpy as np
import pandas as pd
import pytest

from research.synthetic_edge_injector import (
    inject_edge,
    max_deviation_permutation_test,
    seed_dispersion_check,
    run_single_trial,
    run_compound_trial,
)


def _synthetic_pooled(n=200, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "pnl": rng.normal(0, 10, size=n),
        "size": rng.uniform(0.1, 1.0, size=n),
        "seed": rng.integers(0, 5, size=n),
    })


def test_injection_shifts_treatment_group_by_exact_known_amount():
    """Cascade-immune: hand-compute the expected dollar shift for the
    treatment group and check it matches exactly."""
    pooled = _synthetic_pooled(n=100, seed=1)
    treatment_mask = np.array([True] * 50 + [False] * 50)
    edge_pips = 5.0
    pip_value = 10.0

    injected = inject_edge(pooled, "EURUSD", treatment_mask, edge_pips, pip_value)

    expected_shift = edge_pips * pip_value * pooled.loc[treatment_mask, "size"].values
    actual_shift = (injected.loc[treatment_mask, "pnl"].values -
                     pooled.loc[treatment_mask, "pnl"].values)
    assert actual_shift == pytest.approx(expected_shift)


def test_injection_does_not_touch_control_group():
    pooled = _synthetic_pooled(n=100, seed=2)
    treatment_mask = np.array([True] * 50 + [False] * 50)
    injected = inject_edge(pooled, "EURUSD", treatment_mask, edge_pips=7.0, pip_value=10.0)

    control_before = pooled.loc[~treatment_mask, "pnl"].values
    control_after = injected.loc[~treatment_mask, "pnl"].values
    assert control_after == pytest.approx(control_before)


def test_injection_does_not_mutate_original_dataframe():
    pooled = _synthetic_pooled(n=50, seed=3)
    original_pnl = pooled["pnl"].copy()
    treatment_mask = np.array([True] * 25 + [False] * 25)
    inject_edge(pooled, "EURUSD", treatment_mask, edge_pips=5.0, pip_value=10.0)
    assert (pooled["pnl"] == original_pnl).all()


def test_zero_edge_produces_zero_shift():
    pooled = _synthetic_pooled(n=50, seed=4)
    treatment_mask = np.array([True] * 25 + [False] * 25)
    injected = inject_edge(pooled, "EURUSD", treatment_mask, edge_pips=0.0, pip_value=10.0)
    assert (injected["pnl"] == pooled["pnl"]).all()


def test_permutation_test_detects_known_large_injected_difference():
    """Sanity check on the detection statistic itself (not the
    injection): a huge, obvious group-mean difference should produce
    p close to 0."""
    rng = np.random.default_rng(5)
    pnl = np.concatenate([rng.normal(0, 1, 500), rng.normal(100, 1, 500)])
    group = np.array([False] * 500 + [True] * 500)
    observed_stat, p_value, means = max_deviation_permutation_test(
        pnl, group, n_permutations=500, rng=np.random.default_rng(6)
    )
    assert p_value < 0.01
    assert means[True] > means[False]


def test_permutation_test_no_effect_gives_high_p_value():
    rng = np.random.default_rng(7)
    pnl = rng.normal(0, 10, 1000)  # no true group difference
    group = rng.random(1000) < 0.5
    observed_stat, p_value, _ = max_deviation_permutation_test(
        pnl, group, n_permutations=500, rng=np.random.default_rng(8)
    )
    assert p_value > 0.05  # should usually not falsely detect


def test_run_single_trial_detects_very_large_injected_edge():
    """End-to-end sanity: an enormous injected edge (should swamp any
    realistic noise floor) must be detected."""
    pooled = _synthetic_pooled(n=2000, seed=9)
    pooled["pnl"] = np.random.default_rng(10).normal(0, 5, 2000)  # tight noise
    result = run_single_trial(
        pooled, "EURUSD", edge_pips=1000.0, pip_value=10.0,
        treatment_fraction=0.5, n_permutations=200,
        rng=np.random.default_rng(11),
    )
    assert result.detected is True


def test_load_pooled_trades_produces_seed_column():
    """
    REGRESSION TEST for a bug caught on first real-data run: the actual
    research/null_runs_h004/ CSVs do NOT store a 'seed' column (unlike
    this file's synthetic test fixtures, which do) -- seed is only
    recoverable from the filename. load_pooled_trades() must extract
    it, or seed_dispersion_check() fails with a KeyError the moment
    real data is used, which is exactly what happened before this test
    was added.
    """
    from research.synthetic_edge_injector import load_pooled_trades
    import os
    if not os.path.exists("research/null_runs_h004"):
        pytest.skip("research/null_runs_h004 not present in this environment")
    pooled = load_pooled_trades("EURUSD")
    assert "seed" in pooled.columns
    assert pooled["seed"].nunique() > 1  # multiple seeds actually loaded
    assert pooled["seed"].dtype.kind in "iu"  # integer, not object/string


def test_run_single_trial_zero_edge_rarely_detects():
    """A zero injected edge should almost never pass both gates --
    run a handful of trials and confirm the detection rate is low
    (not asserting exactly zero, since false positives at alpha=0.05
    are expected at ~5% by construction)."""
    pooled = _synthetic_pooled(n=500, seed=12)
    detections = 0
    n_trials = 10
    for i in range(n_trials):
        result = run_single_trial(
            pooled, "EURUSD", edge_pips=0.0, pip_value=10.0,
            treatment_fraction=0.5, n_permutations=200,
            rng=np.random.default_rng(100 + i),
        )
        if result.detected:
            detections += 1
    assert detections <= 3  # generous bound, alpha=0.05 predicts ~0-1 of 10


# ── Compound cross-instrument-gate trial ────────────────────────────
# Per research/POWER_CALIBRATION_PLAN.md Sec 1's compound-gate design,
# replicating research/run_h005.py's EXACT combination rule (confirmed
# by direct inspection: `survives = consistent_best and
# n_sig_and_real >= 4`, p<0.01, not the single-instrument curve's
# looser p<0.05 default).

def _synthetic_pooled_by_symbol(n_symbols=5, n=300, base_seed=0):
    return {
        f"SYM{i}": _synthetic_pooled(n=n, seed=base_seed + i)
        for i in range(n_symbols)
    }


def test_compound_trial_enormous_edge_on_all_symbols_clears_everything():
    """A huge, unambiguous edge on every symbol should clear the
    individual gate on all of them and agree in direction everywhere."""
    pooled_by_symbol = _synthetic_pooled_by_symbol()
    pip_values = {sym: 10.0 for sym in pooled_by_symbol}
    rng = np.random.default_rng(42)
    result = run_compound_trial(
        pooled_by_symbol, pip_values, edge_pips=1000.0,
        treatment_fraction=0.5, n_permutations=200, rng=rng,
    )
    assert result.n_individually_clear == len(pooled_by_symbol)
    assert result.direction_consistent is True
    assert result.compound_survives is True


def test_compound_trial_zero_edge_rarely_compound_survives():
    """No true edge anywhere -- the compound standard (direction
    consistency across ALL symbols AND >=4/5 individually clearing at
    p<0.01) should almost never spuriously survive; far stricter than
    any single instrument's own false-positive rate."""
    pooled_by_symbol = _synthetic_pooled_by_symbol()
    pip_values = {sym: 10.0 for sym in pooled_by_symbol}
    survivals = 0
    for i in range(10):
        rng = np.random.default_rng(200 + i)
        result = run_compound_trial(
            pooled_by_symbol, pip_values, edge_pips=0.0,
            treatment_fraction=0.5, n_permutations=200, rng=rng,
        )
        if result.compound_survives:
            survivals += 1
    assert survivals == 0  # compound standard is strict; zero-edge should never pass it in 10 trials


def test_compound_trial_uses_stricter_alpha_than_single_instrument_default():
    """Confirms the compound trial's default alpha (0.01) is stricter
    than run_single_trial's default (0.05) -- this distinction is the
    whole point of replicating H-005's real standard rather than the
    single-instrument curve's looser threshold."""
    import inspect
    single_sig = inspect.signature(run_single_trial)
    compound_sig = inspect.signature(run_compound_trial)
    assert single_sig.parameters["alpha"].default == 0.05
    assert compound_sig.parameters["alpha"].default == 0.01
