# tests/test_costs.py
#
# Known-answer validation for execution/costs.py's size-scaling fix
# (cost model v2, Commit 1/2). Per ENGINEERING_STANDARDS.md Sec 2 /
# docs/COST_MODEL_V2_PLAN.md Sec 6.

import pytest
from execution.costs import total_cost


def test_total_cost_scales_linearly_with_size():
    """The core fix: doubling size must double the cost."""
    cost_1x = total_cost("USDJPY", size=1.0)
    cost_2x = total_cost("USDJPY", size=2.0)
    assert cost_2x == pytest.approx(2 * cost_1x)


def test_total_cost_known_value_usdjpy():
    # USDJPY: spread_pips=1.5 (per core/instruments.py fixture used in
    # test_simulator.py), pip_size=0.01, pip_value=9.10, slippage=1.0
    # (default). size=0.0733 (matches test_simulator.py's Trade A).
    cost = total_cost("USDJPY", size=0.0733, slippage_pips=1.0)
    expected = (1.5 * 0.01 * 9.10 + 1.0 * 0.01 * 9.10) * 0.0733
    assert cost == pytest.approx(expected)


def test_total_cost_zero_size_is_zero_cost():
    assert total_cost("USDJPY", size=0.0) == pytest.approx(0.0)


def test_total_cost_default_slippage_matches_explicit():
    assert total_cost("USDJPY", size=1.0) == pytest.approx(
        total_cost("USDJPY", size=1.0, slippage_pips=1.0)
    )


# ── Swap (cost model v2, Commit 2/2) ────────────────────────────────
# Per docs/COST_MODEL_V2_PLAN.md Sec 3's amendment: the isolated-term
# check below is the PRIMARY correctness burden for swap, cascade-immune
# by construction (each test computes swap_cost directly from a
# trade's own entry_dt/exit_dt/size/direction, touching no capital or
# compounded value at all).

from datetime import datetime
from execution.costs import swap_cost, SWAP_RATES, PLACEHOLDER_INSTRUMENTS, PlaceholderInstrumentError


def test_swap_cost_zero_when_no_rollover_crossed():
    entry = datetime(2024, 1, 10, 10, 0)
    exit_ = datetime(2024, 1, 10, 18, 0)  # same day, before 22:00 boundary
    assert swap_cost("USDJPY", size=1.0, direction=1, entry_dt=entry, exit_dt=exit_) == 0.0


def test_swap_cost_matches_hand_computation_long_one_night():
    # Tue 10:00 -> Wed 10:00: 1 rollover night, non-Wednesday boundary.
    entry = datetime(2024, 1, 9, 10, 0)
    exit_ = datetime(2024, 1, 10, 10, 0)
    size = 2.0
    result = swap_cost("USDJPY", size=size, direction=1, entry_dt=entry, exit_dt=exit_)
    # hand computation: rate=SWAP_RATES['USDJPY']['long']=8.752 (credit
    # convention in the snapshot) -> cost = -rate * size * nights
    expected = -8.752 * size * 1
    assert result == pytest.approx(expected)


def test_swap_cost_matches_hand_computation_short_across_wednesday():
    # Tue 10:00 -> Thu 10:00: crosses Tue 22:00 (x1) and Wed 22:00 (x3) = 4 nights.
    entry = datetime(2024, 1, 9, 10, 0)
    exit_ = datetime(2024, 1, 11, 10, 0)
    size = 0.5
    result = swap_cost("GBPJPY", size=size, direction=-1, entry_dt=entry, exit_dt=exit_)
    expected = -(-23.758) * size * 4  # rate = SWAP_RATES['GBPJPY']['short']
    assert result == pytest.approx(expected)


def test_swap_cost_matches_hand_computation_multi_day():
    # Mon 10:00 -> Fri 10:00: 1+1+3+1 = 6 nights.
    entry = datetime(2024, 1, 8, 10, 0)
    exit_ = datetime(2024, 1, 12, 10, 0)
    size = 1.25
    result = swap_cost("EURUSD", size=size, direction=1, entry_dt=entry, exit_dt=exit_)
    expected = -(-8.166) * size * 6
    assert result == pytest.approx(expected)


def test_zero_crossing_population_swap_is_exactly_zero():
    """Cascade-immune population check, per plan Sec 3's amendment:
    EVERY trade with zero rollover crossings must have swap_cost EXACTLY
    0.0, across a full synthetic population spanning all 5 symbols and
    both directions -- not a sample."""
    zero_crossing_pairs = [
        (datetime(2024, 1, d, 1, 0), datetime(2024, 1, d, 20, 0))
        for d in range(8, 13)  # Mon-Fri, same-day entries/exits, before 22:00
    ]
    for symbol in SWAP_RATES:
        for direction in (1, -1):
            for entry, exit_ in zero_crossing_pairs:
                result = swap_cost(symbol, size=1.0, direction=direction,
                                    entry_dt=entry, exit_dt=exit_)
                assert result == 0.0, (
                    f"{symbol} direction={direction} {entry}->{exit_}: "
                    f"expected exactly 0.0 swap for zero rollover crossings, got {result}"
                )


def test_total_cost_blocks_audusd_by_default():
    with pytest.raises(PlaceholderInstrumentError):
        total_cost("AUDUSD", size=1.0)


def test_total_cost_allows_audusd_with_explicit_flag():
    # Should not raise.
    cost = total_cost("AUDUSD", size=1.0, allow_placeholder=True)
    assert cost > 0  # spread+slip still positive even under placeholder specs


def test_total_cost_non_placeholder_symbols_unaffected_by_flag():
    assert total_cost("USDJPY", size=1.0) == pytest.approx(
        total_cost("USDJPY", size=1.0, allow_placeholder=True)
    )


def test_total_cost_includes_swap_when_dates_provided():
    entry = datetime(2024, 1, 9, 10, 0)
    exit_ = datetime(2024, 1, 10, 10, 0)  # 1 rollover night
    without_swap = total_cost("USDJPY", size=1.0)  # no dates -> swap=0
    with_swap = total_cost("USDJPY", size=1.0, direction=1, entry_dt=entry, exit_dt=exit_)
    assert with_swap != pytest.approx(without_swap)
    expected_swap = -8.752 * 1.0 * 1
    assert (with_swap - without_swap) == pytest.approx(expected_swap)
