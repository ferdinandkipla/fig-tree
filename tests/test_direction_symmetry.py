# tests/test_direction_symmetry.py
#
# S1 long/short redesign — the new regression fixture the design doc
# specified: a mirrored price series, traded in the OPPOSITE direction,
# must reproduce the original trade's outcome exactly (same timing,
# same exit reason, IDENTICAL gross P&L -- not negated). Reasoning:
# mirroring the price series inverts up<->down; flipping direction
# (long->short) also inverts directional exposure. Two inversions
# cancel out. This is the correct symmetry invariant -- confirmed by
# hand-tracing the arithmetic (see the comment at the assertion) after
# an earlier draft of this test got the sign backwards and failed
# against a simulator that was actually correct.
#
# Construction: take the synthetic bars from tests/test_simulator.py's
# Trade A scenario (a real, already-verified long trade), build a
# PRICE-MIRRORED version of the same bars (mirror around the entry
# price so relative moves invert), run a SHORT position through it,
# and confirm the resulting trade matches the original long trade
# exactly: same stop/target distances, same bars_held, exit_reason,
# size, and gross P&L (gross of costs -- see note at the assertion).

import sys
import types

if "MetaTrader5" not in sys.modules:
    _mt5_stub = types.ModuleType("MetaTrader5")
    _mt5_stub.TIMEFRAME_H4 = 16388
    sys.modules["MetaTrader5"] = _mt5_stub

import pandas as pd
import pytest

from execution.simulator import Simulator


def _bar(o, h, l, c, atr, adx, ema_dist, trend_gap, signal, direction=1,
        stop_atr_mult=1.5, rr=2.0):
    return dict(open=o, high=h, low=l, close=c, atr=atr, adx=adx,
                ema_distance=ema_dist, trend_gap=trend_gap, signal=signal,
                direction=direction,
                stop_distance=stop_atr_mult * atr,
                target_distance=rr * stop_atr_mult * atr)


def _mirror_price(p: float, pivot: float) -> float:
    """Reflect a price around a pivot point: mirror(p) = pivot - (p - pivot)."""
    return pivot - (p - pivot)


@pytest.fixture
def long_bars():
    """Trade A from tests/test_simulator.py: take-profit long, entry=101,
    stop=99.5, target=104, exit at target, bars_held=2."""
    rows = [
        _bar(100.0, 101.0, 99.0,  100.5, 1.0, 25, 0.5, 1.0, 1, direction=1),   # i=0 signal
        _bar(101.0, 102.0, 100.5, 101.5, 1.0, 24, 0.4, 0.9, 0, direction=1),   # i=1 entry (open=101)
        _bar(101.5, 102.5, 101.0, 102.0, 1.0, 23, 0.3, 0.8, 0, direction=1),   # i=2
        _bar(102.0, 104.5, 101.8, 104.0, 1.0, 23, 0.2, 0.7, 0, direction=1),   # i=3 exit: TP
    ]
    idx = pd.date_range("2024-01-01 00:00", periods=len(rows), freq="h")
    return pd.DataFrame(rows, index=idx)


@pytest.fixture
def mirrored_short_bars(long_bars):
    """Mirror every OHLC price around the long fixture's entry price
    (101.0), and flip signal bar's direction to -1. A price series
    mirrored around the entry point, traded short, must produce the
    exact inverse of the long trade on the un-mirrored series."""
    pivot = 101.0  # the long fixture's entry price
    df = long_bars.copy()
    for col in ("open", "high", "low", "close"):
        df[col] = df[col].apply(lambda p: _mirror_price(p, pivot))
    # Mirroring swaps which side is "high" and "low" for a bar (e.g. a
    # bar whose original high was above open, after reflection has its
    # mirrored high BELOW the mirrored open) -- re-sort high/low per row
    # so they remain valid OHLC (high >= low) after reflection.
    df["high"], df["low"] = df[["high", "low"]].max(axis=1), df[["high", "low"]].min(axis=1)
    df["direction"] = -1
    return df


def test_short_on_mirrored_market_reproduces_long_on_original(long_bars, mirrored_short_bars):
    sim_long  = Simulator(symbol="USDJPY")
    sim_short = Simulator(symbol="USDJPY")

    result_long  = sim_long.run(long_bars)
    result_short = sim_short.run(mirrored_short_bars)

    assert result_long["total_trades"] == 1
    assert result_short["total_trades"] == 1

    t_long  = result_long["trades"].iloc[0]
    t_short = result_short["trades"].iloc[0]

    # Structural symmetry: same timing, same exit reason, same size
    # (stop distance is identical in both, since mirroring preserves
    # distances from the pivot).
    assert t_short["bars_held"]   == t_long["bars_held"]
    assert t_short["exit_reason"] == t_long["exit_reason"]
    assert t_short["direction"]   == -1
    assert t_long["direction"]    == 1
    assert t_short["size"] == pytest.approx(t_long["size"], abs=0.0001)

    # P&L symmetry: gross P&L must be IDENTICAL (same sign), not negated.
    # Reasoning: mirroring the price series inverts up<->down; flipping
    # direction (long->short) ALSO inverts directional exposure. Two
    # inversions cancel out. Concretely: the long profits 104-101=+3
    # when price rises to target on the original series; the short
    # profits 101-98=+3 when price falls to the mirrored target on the
    # mirrored series. Both +3. (An earlier draft of this test asserted
    # the negation here -- caught by running it and tracing the
    # arithmetic by hand before "fixing" the simulator for a bug that
    # was actually in the test's own expectation.)
    #
    # Gross P&L (not net) is compared deliberately: spread/slippage
    # costs in execution/costs.py today are a fixed dollar charge per
    # trade, not a direction-dependent swap rate -- direction-aware
    # swap cost modeling is explicitly out of scope until real swap
    # data is ingested (see Part 3 of the redesign doc).
    assert t_short["pnl_gross"] == pytest.approx(t_long["pnl_gross"], abs=0.01)
    assert t_short["pnl_pips"]  == pytest.approx(t_long["pnl_pips"], abs=0.1)


def test_short_stop_and_target_geometry_mirrors_long(long_bars, mirrored_short_bars):
    """Explicit geometry check: for the short, stop must be ABOVE entry
    and target BELOW -- the literal mirror of the long fixture's
    stop=99.5 (below entry=101) and target=104 (above entry=101)."""
    sim_short = Simulator(symbol="USDJPY")
    result = sim_short.run(mirrored_short_bars)
    t = result["trades"].iloc[0]

    assert t["stop_loss"] > t["entry"], "short stop must be ABOVE entry"
    assert t["take_profit"] < t["entry"], "short target must be BELOW entry"


def test_long_only_default_direction_is_backward_compatible():
    """A dataframe with NO 'direction' column at all must default to
    long (direction=1) -- this is what keeps every pre-S1 strategy
    (trend_pullback as it existed before this change, any old test
    fixture) byte-identical without modification."""
    rows = [
        dict(open=100.0, high=101.0, low=99.0,  close=100.5, atr=1.0, adx=25,
            ema_distance=0.5, trend_gap=1.0, signal=1,
            stop_distance=1.5, target_distance=3.0),   # no "direction" key at all
        dict(open=101.0, high=102.0, low=100.5, close=101.5, atr=1.0, adx=24,
            ema_distance=0.4, trend_gap=0.9, signal=0,
            stop_distance=1.5, target_distance=3.0),
        dict(open=101.5, high=104.5, low=101.0, close=104.0, atr=1.0, adx=23,
            ema_distance=0.3, trend_gap=0.8, signal=0,
            stop_distance=1.5, target_distance=3.0),
    ]
    idx = pd.date_range("2024-01-01 00:00", periods=len(rows), freq="h")
    df = pd.DataFrame(rows, index=idx)

    sim = Simulator(symbol="USDJPY")
    result = sim.run(df)
    t = result["trades"].iloc[0]
    assert t["direction"] == 1
    assert t["stop_loss"] < t["entry"]
    assert t["take_profit"] > t["entry"]
