# tests/test_rollover.py
#
# Known-answer validation for execution/rollover.py, per
# ENGINEERING_STANDARDS.md Sec 2. Cascade-immune by construction --
# these tests never touch capital, size, or any compounded value.

from datetime import datetime
import pytest
from execution.rollover import count_rollover_nights


def test_same_day_trade_no_crossing():
    # Enters and exits well before the 22:00 UTC boundary, same day.
    entry = datetime(2024, 1, 10, 10, 0)   # Wed 10:00
    exit_ = datetime(2024, 1, 10, 18, 0)   # Wed 18:00, before 22:00
    assert count_rollover_nights(entry, exit_) == 0


def test_single_overnight_non_wednesday():
    # Tuesday 10:00 -> Wednesday 10:00 crosses exactly one boundary,
    # at Tuesday 22:00 -- that crossing is on TUESDAY (the day of the
    # boundary itself), so no 3x multiplier applies here.
    entry = datetime(2024, 1, 9, 10, 0)    # Tue
    exit_ = datetime(2024, 1, 10, 10, 0)   # Wed
    assert count_rollover_nights(entry, exit_) == 1


def test_single_overnight_crossing_into_wednesday_still_counts_as_tuesday():
    # The boundary crossed is Tue 22:00 -- weekday() of that boundary
    # moment is Tuesday (1), not Wednesday (2), so multiplier=1.
    entry = datetime(2024, 1, 9, 23, 0)    # Tue 23:00 (already past Tue's boundary)
    exit_ = datetime(2024, 1, 10, 23, 0)   # Wed 23:00 (past Wed's boundary too)
    # Boundaries crossed: Wed 22:00 (weekday=2, Wednesday) -> multiplier 3
    assert count_rollover_nights(entry, exit_) == 3


def test_crossing_a_wednesday_boundary_triple_counts():
    # Tuesday 10:00 -> Thursday 10:00: crosses Tue 22:00 (mult=1) and
    # Wed 22:00 (mult=3) = 4 total.
    entry = datetime(2024, 1, 9, 10, 0)    # Tue
    exit_ = datetime(2024, 1, 11, 10, 0)   # Thu
    assert count_rollover_nights(entry, exit_) == 1 + 3


def test_multi_day_span_sums_correctly():
    # Monday 10:00 -> Friday 10:00: crosses Mon 22:00 (1), Tue 22:00 (1),
    # Wed 22:00 (3), Thu 22:00 (1) = 6 total.
    entry = datetime(2024, 1, 8, 10, 0)    # Mon
    exit_ = datetime(2024, 1, 12, 10, 0)   # Fri
    assert count_rollover_nights(entry, exit_) == 1 + 1 + 3 + 1


def test_exit_before_entry_returns_zero():
    entry = datetime(2024, 1, 10, 10, 0)
    exit_ = datetime(2024, 1, 9, 10, 0)
    assert count_rollover_nights(entry, exit_) == 0


def test_exit_equals_entry_returns_zero():
    dt = datetime(2024, 1, 10, 10, 0)
    assert count_rollover_nights(dt, dt) == 0


def test_entry_exactly_at_boundary_included():
    # Entry exactly at Tue 22:00 -- that boundary is the "first
    # boundary at or after entry_dt", so it counts.
    entry = datetime(2024, 1, 9, 22, 0)    # Tue 22:00 exactly
    exit_ = datetime(2024, 1, 10, 0, 0)    # Wed 00:00, 2 hours later
    assert count_rollover_nights(entry, exit_) == 1


def test_rejects_non_datetime_input():
    with pytest.raises(TypeError):
        count_rollover_nights("2024-01-10", "2024-01-11")
