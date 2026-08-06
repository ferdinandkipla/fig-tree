# tests/test_calendar_distance.py
#
# Known-answer validation for research/calendar_distance.py, per
# ENGINEERING_STANDARDS.md Sec 2 and this session's own warning: date
# arithmetic around month boundaries and holidays is exactly the
# quiet-join-bug genre that produced H-008's n_thin=0. Every case here
# is hand-verified against a real calendar before being asserted.

from datetime import date
from research.calendar_distance import (
    month_end_business_day,
    bars_to_month_end,
    is_near_month_end,
    is_quarter_end_month,
)


def test_month_end_business_day_when_last_day_is_a_weekday():
    # 2024-01-31 is a Wednesday.
    assert month_end_business_day(date(2024, 1, 31)) == date(2024, 1, 31)


def test_month_end_business_day_when_last_day_is_a_saturday():
    # 2024-06-30 is a Sunday -> preceding business day is Fri 2024-06-28.
    assert month_end_business_day(date(2024, 6, 30)) == date(2024, 6, 28)


def test_month_end_business_day_when_last_day_is_a_sunday():
    # 2023-12-31 is a Sunday -> preceding business day is Fri 2023-12-29.
    assert month_end_business_day(date(2023, 12, 31)) == date(2023, 12, 29)


def test_bars_to_month_end_on_month_end_itself_is_zero():
    assert bars_to_month_end(date(2024, 1, 31)) == 0  # Wed, month-end


def test_bars_to_month_end_one_business_day_before():
    # 2024-01-30 (Tue) is one business day before 2024-01-31 (Wed).
    assert bars_to_month_end(date(2024, 1, 30)) == 1


def test_bars_to_month_end_across_a_weekend():
    # 2024-06-28 (Fri) is the adjusted month-end for June 2024.
    # 2024-06-27 (Thu) is 1 business day before it.
    # 2024-06-26 (Wed) is 2 business days before it.
    assert bars_to_month_end(date(2024, 6, 28)) == 0
    assert bars_to_month_end(date(2024, 6, 27)) == 1
    assert bars_to_month_end(date(2024, 6, 26)) == 2


def test_bars_to_month_end_far_from_month_end():
    # 2024-01-02 (Tue) is far from 2024-01-31 (Wed, month-end).
    # Business days between (exclusive of start, inclusive of end):
    # Jan has 23 weekdays from the 2nd through the 31st minus the
    # start itself -- hand count: Jan 2024 weekdays are
    # 1,2,3,4,5,8,9,10,11,12,15,16,17,18,19,22,23,24,25,26,29,30,31
    # = 23 weekdays total; from the 2nd (index 2 in that list, 1-based)
    # to the 31st (index 23) is 21 steps.
    assert bars_to_month_end(date(2024, 1, 2)) == 21


def test_is_near_month_end_default_window():
    # window_business_days=1 -> bars_to_month_end in {0, 1}.
    assert is_near_month_end(date(2024, 1, 31)) is True   # 0
    assert is_near_month_end(date(2024, 1, 30)) is True   # 1
    assert is_near_month_end(date(2024, 1, 29)) is False  # 2 (Mon)


def test_is_near_month_end_across_the_june_2024_weekend_case():
    assert is_near_month_end(date(2024, 6, 28)) is True   # 0, Fri (adj)
    assert is_near_month_end(date(2024, 6, 27)) is True   # 1, Thu
    assert is_near_month_end(date(2024, 6, 26)) is False  # 2, Wed
    # The actual calendar weekend dates should not silently claim
    # "near month end" just because they're close in raw days --
    # they roll forward to Monday July 1st, which is NOT near June's
    # month-end (it's the start of a new month).
    assert is_near_month_end(date(2024, 6, 29)) is False  # Sat -> rolls to Mon Jul 1
    assert is_near_month_end(date(2024, 6, 30)) is False  # Sun -> rolls to Mon Jul 1


def test_is_quarter_end_month():
    assert is_quarter_end_month(date(2024, 3, 15)) is True
    assert is_quarter_end_month(date(2024, 6, 15)) is True
    assert is_quarter_end_month(date(2024, 9, 15)) is True
    assert is_quarter_end_month(date(2024, 12, 15)) is True
    assert is_quarter_end_month(date(2024, 1, 15)) is False
    assert is_quarter_end_month(date(2024, 7, 15)) is False


def test_leap_year_february_month_end():
    # 2024 is a leap year; Feb 2024 has 29 days, and Feb 29 2024 is a
    # Thursday (a weekday, no adjustment needed).
    assert month_end_business_day(date(2024, 2, 15)) == date(2024, 2, 29)


def test_non_leap_year_february_month_end():
    # 2023 Feb has 28 days; Feb 28 2023 is a Tuesday.
    assert month_end_business_day(date(2023, 2, 15)) == date(2023, 2, 28)
