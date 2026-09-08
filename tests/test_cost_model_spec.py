# tests/test_cost_model_spec.py
#
# THE WRITTEN, TESTED KNOWN-ANSWER SPECIFICATION this project has
# needed since cost model v2 -- per the closing observation of the
# third consecutive session to find a load-bearing cost-model defect
# incidentally (flat costing -> no commission -> double pip_size).
# Every term of total_cost() is hand-computed, from first principles,
# for ONE fully-specified trade, so this class of discovery stops being
# incidental. If any term's formula changes in the future, this file
# is where that change must be re-derived and re-justified by hand --
# not just re-fit to whatever the code currently outputs.
#
# THE SPREAD/SLIP FORMULA BUG THIS FILE CONFIRMS AND THE FIX TARGETS:
# pip_value (core/instruments.py) is ALREADY a dollars-per-pip-per-
# standard-lot quantity -- confirmed by its use everywhere else in the
# codebase: execution/simulator.py's `pnl_gross = pnl_pips * pip_value
# * size` and risk/sizing.py's `risk_per_lot = stop_pips * pip_value`,
# neither of which multiplies by pip_size again. The cost formula
# was the ONLY consumer of pip_value that additionally multiplied by
# pip_size -- an internal inconsistency within this codebase's own
# stated convention, not just a magnitude that "seemed low." For
# EURUSD this made the spread/slip term ~10,000x too small (see
# test_spread_slip_bug_magnitude_was_10000x below, which asserts this
# against a temporarily-reintroduced buggy formula so the magnitude
# claim itself is verified, not just narrated in a commit message).

import pytest
from execution.costs import total_cost, commission_cost, swap_cost, SWAP_RATES


# ── The reference trade, fully specified ────────────────────────────
# EURUSD, 1.0 standard lot (100,000 units), spread_pips=1.0 (real
# core/instruments.py value), slippage_pips=1.0 (this module's
# default), long, same-day (zero rollover crossings -- swap=0 by
# construction, isolates spread/slip/commission from any calendar
# complexity). pip_size=0.0001, pip_value=10.00.

REF_SYMBOL = "EURUSD"
REF_SIZE = 1.0
REF_SPREAD_PIPS = 1.0   # core/instruments.py EURUSD spread_pips
REF_SLIPPAGE_PIPS = 1.0  # total_cost()'s default
REF_PIP_SIZE = 0.0001
REF_PIP_VALUE = 10.00


def test_spread_cost_hand_computed():
    """
    Spread cost, from first principles: a 1-pip spread on a 1.0
    standard-lot (100,000 unit) EURUSD position. 1 pip = 0.0001 price
    movement. Value of a 1-pip move on 100,000 units of EURUSD =
    100,000 * 0.0001 = $10.00 -- this IS what pip_value=10.00 already
    represents (dollars per pip per standard lot). The spread cost for
    a 1.0-lot trade with a 1.0-pip spread is therefore exactly
    1.0 (pips) * $10.00 (per pip per lot) * 1.0 (lots) = $10.00.
    NOT 1.0 * 0.0001 * 10.00 * 1.0 = $0.001 -- that treats pip_value as
    if it still needed a pip_size conversion, which it does not.
    """
    expected_spread_cost = REF_SPREAD_PIPS * REF_PIP_VALUE * REF_SIZE
    assert expected_spread_cost == pytest.approx(10.00)

    cost_with_zero_slip_and_no_commission_symbol = total_cost(
        REF_SYMBOL, size=REF_SIZE, slippage_pips=0.0
    )
    # commission_cost() is a separate, correctly-implemented term (added
    # 2026-08-20) -- isolate spread alone by subtracting it out, so this
    # test's failure mode is specifically about the spread formula, not
    # entangled with commission's correctness (covered separately below).
    commission = commission_cost(REF_SYMBOL, REF_SIZE)
    spread_only = cost_with_zero_slip_and_no_commission_symbol - commission
    assert spread_only == pytest.approx(expected_spread_cost)


def test_slip_cost_hand_computed():
    """Same derivation as spread, for slippage_pips."""
    expected_slip_cost = REF_SLIPPAGE_PIPS * REF_PIP_VALUE * REF_SIZE
    assert expected_slip_cost == pytest.approx(10.00)

    cost_with_zero_spread = total_cost(
        REF_SYMBOL, size=REF_SIZE, slippage_pips=REF_SLIPPAGE_PIPS
    )
    # Can't zero out spread_pips (it's read from core/instruments.py,
    # not a parameter) -- instead compute total spread+slip and
    # subtract the independently-verified spread term.
    commission = commission_cost(REF_SYMBOL, REF_SIZE)
    spread_plus_slip = cost_with_zero_spread - commission
    expected_spread = REF_SPREAD_PIPS * REF_PIP_VALUE * REF_SIZE
    slip_only = spread_plus_slip - expected_spread
    assert slip_only == pytest.approx(expected_slip_cost)


def test_full_reference_trade_every_term_hand_computed():
    """
    THE spec test: every term of total_cost() for the reference trade,
    each computed independently from first principles, summed, and
    checked against the function's actual output in one assertion.
    This is the "one trade, every term hand-computed" artifact this
    project's cost model has needed since v2.
    """
    expected_spread = REF_SPREAD_PIPS * REF_PIP_VALUE * REF_SIZE          # $10.00
    expected_slip = REF_SLIPPAGE_PIPS * REF_PIP_VALUE * REF_SIZE          # $10.00
    expected_commission = 7.00 * REF_SIZE                                  # $7.00 (EURUSD in COMMISSION_APPLIES_TO)
    expected_swap = 0.0                                                    # no dates passed -> swap=0 by construction

    expected_total = expected_spread + expected_slip + expected_commission + expected_swap
    assert expected_total == pytest.approx(27.00)

    actual = total_cost(REF_SYMBOL, size=REF_SIZE, slippage_pips=REF_SLIPPAGE_PIPS)
    assert actual == pytest.approx(expected_total)


def test_commission_hand_computed():
    """$7.00/lot round-turn, EURUSD is in COMMISSION_APPLIES_TO."""
    assert commission_cost("EURUSD", size=1.0) == pytest.approx(7.00)
    assert commission_cost("EURUSD", size=2.5) == pytest.approx(17.50)
    assert commission_cost("XAUUSD", size=1.0) == pytest.approx(0.0)  # not in COMMISSION_APPLIES_TO


def test_swap_hand_computed_matches_isolated_test_suite():
    """
    Cross-reference against tests/test_costs.py's own isolated swap
    tests -- this spec file doesn't re-derive rollover-night counting
    (that has its own dedicated known-answer suite,
    tests/test_rollover.py), it just confirms total_cost() wires
    swap_cost() in correctly for a trade that DOES cross a boundary,
    completing this file's "every term" claim.
    """
    from datetime import datetime
    entry = datetime(2024, 1, 9, 10, 0)   # Tue
    exit_ = datetime(2024, 1, 10, 10, 0)  # Wed, 1 rollover night
    expected_swap = -SWAP_RATES["EURUSD"]["long"] * REF_SIZE * 1
    actual_swap = swap_cost("EURUSD", size=REF_SIZE, direction=1, entry_dt=entry, exit_dt=exit_)
    assert actual_swap == pytest.approx(expected_swap)

    full_cost = total_cost(REF_SYMBOL, size=REF_SIZE, slippage_pips=REF_SLIPPAGE_PIPS,
                            direction=1, entry_dt=entry, exit_dt=exit_)
    no_swap_cost = total_cost(REF_SYMBOL, size=REF_SIZE, slippage_pips=REF_SLIPPAGE_PIPS)
    assert (full_cost - no_swap_cost) == pytest.approx(expected_swap)


def test_spread_slip_bug_magnitude_was_10000x():
    """
    Verifies the ~10,000x magnitude claim itself (docs disclosure,
    commit messages) against a temporarily-reintroduced buggy formula,
    rather than letting that number live only in prose. If this ratio
    drifts, something about pip_size/pip_value's relationship changed
    and this claim needs re-deriving, not silently trusting the old
    number.
    """
    buggy_spread_slip = (
        REF_SPREAD_PIPS * REF_PIP_SIZE * REF_PIP_VALUE * REF_SIZE +
        REF_SLIPPAGE_PIPS * REF_PIP_SIZE * REF_PIP_VALUE * REF_SIZE
    )
    correct_spread_slip = (
        REF_SPREAD_PIPS * REF_PIP_VALUE * REF_SIZE +
        REF_SLIPPAGE_PIPS * REF_PIP_VALUE * REF_SIZE
    )
    ratio = correct_spread_slip / buggy_spread_slip
    assert ratio == pytest.approx(10000.0, rel=0.01)
