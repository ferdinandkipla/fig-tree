# tests/test_fdr_cells.py
#
# Known-answer validation for research/fdr_cells.py, per
# ENGINEERING_STANDARDS.md Sec 2: new statistical machinery is
# validated on cases with known answers before it adjudicates
# anything. This is the direct precedent set by the StringArray
# shuffle bug (H-004) -- run this BEFORE fdr_cells.py is trusted to
# adjudicate H-008's 5 cells.

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from research.fdr_cells import bh_adjusted_thresholds


def test_bh_textbook_example():
    """
    Canonical BH step-up worked example, 5 p-values, alpha=0.05, with
    an unambiguous partial-rejection region (a case where taking the
    largest passing rank matters, distinguishing correct step-up from
    naive per-rank comparison).

    p-values (already sorted): 0.001, 0.010, 0.020, 0.040, 0.090
    m=5, alpha=0.05
    thresholds (rank*alpha/m): 0.01, 0.02, 0.03, 0.04, 0.05
    per-rank comparison: 0.001<=0.01 T, 0.010<=0.02 T, 0.020<=0.03 T,
                         0.040<=0.04 T, 0.090<=0.05 F
    Step-up: largest k with p_(k)<=alpha*k/m is k=4 (rank 5 fails).
    Expected: ranks 1-4 significant, rank 5 (p=0.090) not -- and,
    critically, rank 4 IS significant even though it's an equality
    case (0.040<=0.040), which a strict '<' implementation would
    wrongly reject.
    """
    p_values = {
        "cell_a": 0.001,
        "cell_b": 0.010,
        "cell_c": 0.020,
        "cell_d": 0.040,
        "cell_e": 0.090,
    }
    results = bh_adjusted_thresholds(p_values, alpha=0.05)

    assert results["cell_a"].significant is True
    assert results["cell_b"].significant is True
    assert results["cell_c"].significant is True
    assert results["cell_d"].significant is True, (
        "rank-4 p=0.040 equals its own threshold exactly (4*0.05/5=0.04) "
        "-- BH's condition is <=, not <. A strict '<' implementation "
        "would silently under-reject at exactly this boundary."
    )
    assert results["cell_e"].significant is False, (
        "rank-5 p=0.090 exceeds its own threshold (0.05) and is the "
        "reason the step-up procedure stops at k=4, not k=5."
    )


def test_bh_all_null_no_false_positives():
    """
    Calibration check: p-values drawn to look like a true null (all
    large, uniformly-scattered-looking) should yield zero significant
    cells. A harness that finds a 'signal' here is broken.
    """
    p_values = {f"cell_{i}": p for i, p in enumerate(
        [0.51, 0.62, 0.33, 0.78, 0.45]
    )}
    results = bh_adjusted_thresholds(p_values, alpha=0.05)
    assert all(not r.significant for r in results.values())


def test_bh_all_significant():
    """All p-values far below threshold -> all significant."""
    p_values = {f"cell_{i}": p for i, p in enumerate(
        [0.0001, 0.0002, 0.0003, 0.0004, 0.0005]
    )}
    results = bh_adjusted_thresholds(p_values, alpha=0.05)
    assert all(r.significant for r in results.values())


def test_bh_empty_input():
    assert bh_adjusted_thresholds({}) == {}


def test_bh_single_cell_matches_uncorrected():
    """With m=1, BH threshold reduces to raw alpha -- no correction
    should be applied when there's nothing to correct against."""
    results = bh_adjusted_thresholds({"only_cell": 0.03}, alpha=0.05)
    assert results["only_cell"].bh_adjusted_threshold == 0.05
    assert results["only_cell"].significant is True
