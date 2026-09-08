# tests/test_costs_known_answer.py
#
# THE known-answer specification: one fully hand-computed trade per
# instrument, every cost term, checked against total_cost()'s actual
# output. This is the artifact that would have caught all three cost
# bugs found across this project's cost-model history (flat costing,
# missing commission, doubled pip_size) -- written retroactively after
# the third, per the explicit request that follows it: "before Batch 2
# produces anything that could survive, the cost model needs a
# written, tested known-answer specification (one trade, every term
# hand-computed) so that this class of discovery stops being
# incidental."
#
# Complements tests/test_cost_model_spec.py (which focuses on isolating
# and re-deriving the pip_size bug specifically, EURUSD-only) with full
# per-instrument coverage -- every instrument's spread_pips/pip_value
# combination is different, and the doubled-pip_size bug's understatement
# factor varied by 100x-10,000x depending on pip_size's own magnitude
# (see the table below), so a single-instrument spec would not have
# demonstrated the bug's full severity.
#
# Reference trade for each instrument: size=1.0 standard lot,
# slippage_pips=1.0 (total_cost()'s default), direction=1, no
# entry_dt/exit_dt (swap=0 by construction -- isolates spread/slip/
# commission from any calendar complexity, same reasoning as
# test_cost_model_spec.py's reference trade).
#
# Per-instrument understatement under the pip_size-doubling bug
# (fixed in execution/costs.py, docs/COST_MODEL_V3_SPREAD_FIX.md),
# recorded here for the historical record:
#
#   Instrument  Intended spread/lot   Bug-era coded cost/lot   Factor
#   USDJPY      1.5 * 9.10  = $13.65  $0.1365                  100x
#   GBPJPY      2.5 * 9.10  = $22.75  $0.2275                  100x
#   XAUUSD      3.0 * 1.00  = $3.00   $0.30                    10x
#   EURUSD      1.0 * 10.00 = $10.00  $0.001                   10,000x
#   AUDUSD      0.075*10.00 = $0.75   $0.000075                10,000x

import pytest
from execution.costs import total_cost, commission_cost, COMMISSION_APPLIES_TO

REF_SIZE = 1.0
REF_SLIPPAGE_PIPS = 1.0


def _hand_compute(symbol, spread_pips, pip_value):
    spread_cost = spread_pips * pip_value * REF_SIZE
    slip_cost = REF_SLIPPAGE_PIPS * pip_value * REF_SIZE
    commission = 7.00 * REF_SIZE if symbol in COMMISSION_APPLIES_TO else 0.0
    return spread_cost, slip_cost, commission, spread_cost + slip_cost + commission


def test_usdjpy_known_answer():
    # spread_pips=1.5, pip_value=9.10 -> spread=$13.65, slip=$9.10,
    # commission=$7.00 (USDJPY in COMMISSION_APPLIES_TO) -> total $29.75
    spread, slip, commission, expected_total = _hand_compute("USDJPY", 1.5, 9.10)
    assert (spread, slip, commission) == pytest.approx((13.65, 9.10, 7.00))
    assert expected_total == pytest.approx(29.75)
    actual = total_cost("USDJPY", size=REF_SIZE, slippage_pips=REF_SLIPPAGE_PIPS)
    assert actual == pytest.approx(expected_total)


def test_gbpjpy_known_answer():
    # spread_pips=2.5, pip_value=9.10 -> spread=$22.75, slip=$9.10,
    # commission=$7.00 -> total $38.85
    spread, slip, commission, expected_total = _hand_compute("GBPJPY", 2.5, 9.10)
    assert (spread, slip, commission) == pytest.approx((22.75, 9.10, 7.00))
    assert expected_total == pytest.approx(38.85)
    actual = total_cost("GBPJPY", size=REF_SIZE, slippage_pips=REF_SLIPPAGE_PIPS)
    assert actual == pytest.approx(expected_total)


def test_xauusd_known_answer():
    # spread_pips=3.0, pip_value=1.00 -> spread=$3.00, slip=$1.00,
    # commission=$0.00 (XAUUSD NOT in COMMISSION_APPLIES_TO -- metals
    # commission still unsourced, see docs/PROJECT_STATE.md Sec 7)
    # -> total $4.00
    spread, slip, commission, expected_total = _hand_compute("XAUUSD", 3.0, 1.00)
    assert (spread, slip, commission) == pytest.approx((3.00, 1.00, 0.00))
    assert expected_total == pytest.approx(4.00)
    actual = total_cost("XAUUSD", size=REF_SIZE, slippage_pips=REF_SLIPPAGE_PIPS,
                         allow_placeholder=True)
    assert actual == pytest.approx(expected_total)


def test_eurusd_known_answer():
    # spread_pips=1.0, pip_value=10.00 -> spread=$10.00, slip=$10.00,
    # commission=$7.00 -> total $27.00
    spread, slip, commission, expected_total = _hand_compute("EURUSD", 1.0, 10.00)
    assert (spread, slip, commission) == pytest.approx((10.00, 10.00, 7.00))
    assert expected_total == pytest.approx(27.00)
    actual = total_cost("EURUSD", size=REF_SIZE, slippage_pips=REF_SLIPPAGE_PIPS)
    assert actual == pytest.approx(expected_total)


def test_audusd_known_answer():
    # spread_pips=0.075 (live-sampled 2026-08-20), pip_value=10.00 ->
    # spread=$0.75, slip=$10.00, commission=$7.00 -> total $17.75
    spread, slip, commission, expected_total = _hand_compute("AUDUSD", 0.075, 10.00)
    assert (spread, slip, commission) == pytest.approx((0.75, 10.00, 7.00))
    assert expected_total == pytest.approx(17.75)
    actual = total_cost("AUDUSD", size=REF_SIZE, slippage_pips=REF_SLIPPAGE_PIPS)
    assert actual == pytest.approx(expected_total)


def test_per_instrument_understatement_factors_under_the_fixed_bug():
    """
    Re-derives the table in this file's header docstring against a
    temporarily-reintroduced buggy formula, per instrument -- so the
    documented understatement factors (100x/100x/10x/10,000x/10,000x)
    are independently verified, not just narrated.
    """
    from core.instruments import get_meta

    cases = [
        ("USDJPY", 100),
        ("GBPJPY", 100),
        ("XAUUSD", 10),
        ("EURUSD", 10000),
        ("AUDUSD", 10000),
    ]
    for symbol, expected_factor in cases:
        meta = get_meta(symbol)
        correct = meta["spread_pips"] * meta["pip_value"] * REF_SIZE
        buggy = meta["spread_pips"] * meta["pip_size"] * meta["pip_value"] * REF_SIZE
        ratio = correct / buggy
        assert ratio == pytest.approx(expected_factor, rel=0.01), (
            f"{symbol}: expected understatement factor {expected_factor}x, got {ratio:.1f}x"
        )
