# research/calendar_distance.py
#
# Derives "business days to month-end" from a bar timestamp. This is
# NEW statistical machinery (a new derived variable, not a data source)
# for the month-end x volatility candidate -- gets the full
# known-answer-test treatment before it touches occupancy counts or
# any outcome data, per ENGINEERING_STANDARDS.md Sec 2 (StringArray-bug
# precedent) and this session's own month-boundary/holiday warning:
# "date arithmetic around month boundaries and holidays is exactly the
# quiet-join-bug genre that produced n_thin=0."
#
# FROZEN CONVENTION (decided here, before any use):
# - "Business day" = Monday-Friday by calendar weekday. Bank/market
#   holidays are NOT excluded -- this project's MT5 data has its own
#   natural gaps around major holidays (Christmas/New Year) which this
#   convention does not attempt to model precisely. This is a stated
#   simplification, not an oversight: modeling exact FX market holiday
#   calendars per instrument is out of scope for a zero-new-data-source
#   candidate. Accept the resulting imprecision.
# - "Month-end" = the last CALENDAR day of the month, adjusted to the
#   preceding Friday if it falls on a Saturday or Sunday.
# - bars_to_month_end(date) = count of business days from `date`
#   (inclusive of date) to month-end (inclusive), MINUS 1. So the
#   month-end business day itself scores 0, the business day before it
#   scores 1, etc. Weekend dates are assigned the value of the next
#   business day (Monday) for bars that don't exist on weekends anyway
#   in this dataset -- included for completeness, not expected to be
#   exercised on real H1 bar data.

from datetime import date, timedelta
import calendar


def _last_calendar_day_of_month(d: date) -> date:
    last_day_num = calendar.monthrange(d.year, d.month)[1]
    return date(d.year, d.month, last_day_num)


def _adjust_to_preceding_business_day(d: date) -> date:
    while d.weekday() >= 5:  # 5=Saturday, 6=Sunday
        d -= timedelta(days=1)
    return d


def month_end_business_day(d: date) -> date:
    """The last business day (Mon-Fri) of d's month, per the frozen
    convention above (calendar month-end, adjusted backward over a
    weekend, holidays not modeled)."""
    return _adjust_to_preceding_business_day(_last_calendar_day_of_month(d))


def bars_to_month_end(d: date) -> int:
    """
    Business days from d to that month's month-end business day,
    per the frozen convention. Returns 0 on the month-end business day
    itself, 1 the business day before it, etc. Weekend dates roll
    forward to the next business day equivalent (Monday) before
    counting -- included for completeness; this dataset (FX/metals
    OHLC bars) should not actually produce weekend timestamps.
    """
    if d.weekday() >= 5:
        days_to_monday = 7 - d.weekday()
        d = d + timedelta(days=days_to_monday)

    me = month_end_business_day(d)
    if d > me:
        # d is in the business-day-adjusted weekend gap after a
        # month-end that fell on a weekend but before month rollover
        # is otherwise reached -- shouldn't occur given the rollover
        # above, defensive only.
        return 0

    count = 0
    cursor = d
    while cursor < me:
        cursor += timedelta(days=1)
        if cursor.weekday() < 5:
            count += 1
    return count


def is_near_month_end(d: date, window_business_days: int = 1) -> bool:
    """
    True if d is within `window_business_days` business days of
    month-end, inclusive (window_business_days=1 -> the month-end
    business day itself AND the one immediately before it -- i.e.
    bars_to_month_end(d) in {0, 1}). Frozen at window_business_days=1
    for the H-009 candidate -- see MECHANISM-MEMO-H009.md Sec on
    conditioning variable.
    """
    return bars_to_month_end(d) <= window_business_days


def is_quarter_end_month(d: date) -> bool:
    """True if d's month is a calendar quarter-end month (Mar/Jun/Sep/Dec)."""
    return d.month in (3, 6, 9, 12)
