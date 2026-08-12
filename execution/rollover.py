# execution/rollover.py
#
# Rollover-night counting for swap cost (cost model v2, Commit 2/2).
# Separated from execution/costs.py so the rollover-counting logic can
# be unit-tested in isolation, cascade-immune from any compounding
# concern -- it depends only on entry_dt/exit_dt, never on capital or
# any other trade.
#
# CONVENTION, stated as an explicit assumption per
# docs/COST_MODEL_V2_PLAN.md Sec 3: rollover boundary = 22:00 UTC
# (5pm NY), each calendar day a trade is held past that boundary counts
# as one rollover night, EXCEPT Wednesday which counts 3x (standard FX
# weekend-rollover triple-charge convention, covering Sat/Sun).
#
# research/S1_SWAP_RATES_SNAPSHOT.md does not state a rollover-day
# convention. FX brokers standardly triple-charge Wednesday; some
# brokers use a DIFFERENT convention for metals (e.g. Friday 3x for
# XAUUSD). Absent a stated source, this module applies the FX
# convention (Wednesday 3x) UNIFORMLY, including for XAUUSD, as an
# explicit, disclosed assumption -- NOT verified against IC Markets'
# actual metals rollover schedule. Candidate item for the swap-snapshot
# re-sourcing event mentioned in docs/COST_MODEL_V2_PLAN.md Sec 0.1,
# out of scope here.

from datetime import datetime, timedelta

ROLLOVER_HOUR_UTC = 22  # 22:00 UTC ~= 5pm NY


def count_rollover_nights(entry_dt, exit_dt) -> int:
    """
    Number of rollover-boundary (22:00 UTC) crossings in
    [entry_dt, exit_dt), with each crossing on a Wednesday counted 3x.

    entry_dt, exit_dt: pandas Timestamp or datetime, naive (assumed
    already UTC, matching this project's MT5 data convention
    throughout -- no timezone conversion performed).
    """
    entry_dt = _to_datetime(entry_dt)
    exit_dt = _to_datetime(exit_dt)
    if exit_dt <= entry_dt:
        return 0

    # First rollover boundary at or after entry_dt.
    first_boundary = entry_dt.replace(hour=ROLLOVER_HOUR_UTC, minute=0, second=0, microsecond=0)
    if first_boundary < entry_dt:
        first_boundary += timedelta(days=1)

    count = 0
    cursor = first_boundary
    while cursor < exit_dt:
        multiplier = 3 if cursor.weekday() == 2 else 1  # 2 = Wednesday
        count += multiplier
        cursor += timedelta(days=1)
    return count


def _to_datetime(x):
    if isinstance(x, datetime):
        return x
    # pandas Timestamp and string both handled by pandas if needed,
    # but avoid importing pandas here to keep this module dependency-light
    # and trivially unit-testable; callers pass datetime/Timestamp,
    # which both satisfy isinstance(x, datetime).
    raise TypeError(f"count_rollover_nights expects datetime-like input, got {type(x)}")
