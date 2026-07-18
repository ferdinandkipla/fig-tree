# tests/test_simulator.py
#
# Simulator determinism test — the M1 "insurance policy" called for in the
# Phase 2 roadmap. Feeds the simulator a fixed, hand-constructed synthetic
# bar series with known signals/ATR and asserts the exact resulting trade
# list, sizing, P&L, and equity curve.
#
# Why this matters: this is the test that would have caught the
# ema_distance/trend_gap silent-NaN bug on day one — any change to
# ENTRY_FEATURES capture, entry/stop/target logic, pessimistic-fill
# ordering, or equity-curve timing will break this test loudly instead
# of silently corrupting a research result months later.
#
# The simulator is strategy-agnostic: stop/target are re-anchored from
# stop_distance/target_distance columns (price-unit distances) rather
# than the simulator importing any strategy's specific constants. The
# synthetic bars below emulate exactly what strategy.prepare() emits.
#
# NOTE ON A REAL PORTABILITY ISSUE FOUND WHILE WRITING THIS TEST:
# core/config.py does `import MetaTrader5 as mt5` purely to reference
# mt5.TIMEFRAME_H4 as a constant. MetaTrader5 is a Windows-only package
# (it requires a running MT5 terminal) and is NOT installable on Linux/CI.
# That means the entire codebase — including this test — cannot import
# core.config on any non-Windows machine without stubbing the module out,
# as done below. This should be fixed properly in M1: replace
# `mt5.TIMEFRAME_H4` with a plain constant (e.g. a string "H4" or an int)
# so core.config has zero hard dependency on a Windows-only broker SDK.
# The stub below is a workaround for testing, not a fix for the coupling.

import sys
import types

if "MetaTrader5" not in sys.modules:
    _mt5_stub = types.ModuleType("MetaTrader5")
    _mt5_stub.TIMEFRAME_H4 = 16388  # MT5's real H4 enum value; placeholder is fine, unused by the test
    sys.modules["MetaTrader5"] = _mt5_stub

import pandas as pd
import pytest

from execution.simulator import Simulator, MAX_BARS_IN_TRADE


# ── Synthetic bar construction ──────────────────────────────────────────
# 8 hourly bars, all within the "tokyo" session window (hours 0-7, tokyo
# session = 0-9) so session assignment is unambiguous and deterministic.
#
# Bar-by-bar design (see inline comments for what each bar is FOR):
#
#  i=0  signal=1                              -> triggers entry at i=1
#  i=1  entry bar for Trade A (open=101)       -> entry=101, atr(prev)=1.0
#  i=2  no stop/target hit                     -> trade stays open
#  i=3  high=104.5 hits target(104)            -> Trade A closes: take_profit
#  i=4  signal=1                               -> triggers entry at i=5
#  i=5  entry bar for Trade B (open=104)       -> entry=104, atr(prev)=1.0
#  i=6  low=102.3 hits stop(102.5)             -> Trade B closes: stop_loss
#  i=7  trailing bar, no trade                 -> final equity point only

def _bar(o, h, l, c, atr, adx, ema_dist, trend_gap, signal, stop_atr_mult=1.5, rr=2.0):
    # stop_distance/target_distance emulate what strategy.prepare() now
    # emits (price-unit distances, strategy-agnostic contract) so the
    # simulator's _open() can re-anchor them onto the real entry price
    # without importing any strategy-specific constants.
    return dict(open=o, high=h, low=l, close=c, atr=atr, adx=adx,
                ema_distance=ema_dist, trend_gap=trend_gap, signal=signal,
                stop_distance=stop_atr_mult * atr,
                target_distance=rr * stop_atr_mult * atr)


@pytest.fixture
def synthetic_df():
    rows = [
        _bar(100.0, 101.0, 99.0,  100.5, 1.0, 25, 0.5,  1.0, 1),   # i=0
        _bar(101.0, 102.0, 100.5, 101.5, 1.0, 24, 0.4,  0.9, 0),   # i=1 (Trade A entry)
        _bar(101.5, 102.5, 101.0, 102.0, 1.0, 23, 0.3,  0.8, 0),   # i=2
        _bar(102.0, 104.5, 101.8, 104.0, 1.0, 23, 0.2,  0.7, 0),   # i=3 (Trade A exit: TP)
        _bar(104.0, 104.5, 103.5, 104.2, 1.0, 22, -0.1, 0.6, 1),   # i=4
        _bar(104.0, 104.5, 102.0, 103.0, 1.0, 22, -0.3, 0.8, 0),   # i=5 (Trade B entry)
        _bar(103.0, 103.5, 102.3, 103.0, 1.0, 21, -0.2, 0.5, 0),   # i=6 (Trade B exit: SL)
        _bar(103.0, 103.2, 102.8, 103.0, 1.0, 21, -0.2, 0.5, 0),   # i=7
    ]
    idx = pd.date_range("2024-01-01 00:00", periods=len(rows), freq="h")
    return pd.DataFrame(rows, index=idx)


@pytest.fixture
def result(synthetic_df):
    sim = Simulator(symbol="USDJPY")
    return sim.run(synthetic_df)


# ── Structural assertions ───────────────────────────────────────────────

def test_exact_trade_count(result):
    assert result["total_trades"] == 2


def test_equity_curve_length(result):
    # One equity point per bar processed (i=1..7 -> 7 points), never more,
    # never fewer, regardless of how many trades opened/closed on a bar.
    assert len(result["equity_curve"]) == 7


# ── Trade A: take-profit exit, exact numbers ────────────────────────────

def test_trade_a_entry_and_exit_prices(result):
    t = result["trades"].iloc[0]
    assert t["entry"] == pytest.approx(101.0)
    assert t["exit"] == pytest.approx(104.0)          # closes at TARGET price, not bar high
    assert t["stop_loss"] == pytest.approx(99.5)
    assert t["take_profit"] == pytest.approx(104.0)
    assert t["exit_reason"] == "take_profit"
    assert t["bars_held"] == 2                        # entry_bar=1, exit_bar=3


def test_trade_a_sizing_and_pnl(result):
    t = result["trades"].iloc[0]
    # position_size(10000, 0.01, entry=101, stop=99.5, USDJPY):
    #   risk_amount=100, stop_pips=150, risk_per_lot=150*9.10=1365
    #   size = round(100/1365, 4) = 0.0733
    assert t["size"] == pytest.approx(0.0733)
    assert t["pnl_pips"] == pytest.approx(300.0)
    # pnl_gross = 300 * 9.10 * 0.0733 = 200.109
    assert t["pnl_gross"] == pytest.approx(200.11, abs=0.01)
    # total_cost = 1.5*0.01*9.10 + 1*0.01*9.10 = 0.2275
    # pnl_net = 200.109 - 0.2275 = 199.8815 -> rounded 199.88
    assert t["pnl"] == pytest.approx(199.88, abs=0.01)


def test_trade_a_entry_features_captured(result):
    # This is the regression check for the ema_distance/trend_gap NaN bug:
    # values must come from the SIGNAL bar (i=0), not the entry bar (i=1).
    t = result["trades"].iloc[0]
    assert t["adx_entry"] == pytest.approx(25.0)
    assert t["atr_entry"] == pytest.approx(1.0)
    assert t["ema_distance"] == pytest.approx(0.5)
    assert t["trend_gap"] == pytest.approx(1.0)
    assert t["session"] == "tokyo"
    assert t["year"] == 2024
    # Explicitly guard against the original bug's symptom:
    assert pd.notna(t["ema_distance"])
    assert pd.notna(t["trend_gap"])


# ── Trade B: stop-loss exit (ambiguity + pessimistic-fill correctness) ──

def test_trade_b_entry_and_exit_prices(result):
    t = result["trades"].iloc[1]
    assert t["entry"] == pytest.approx(104.0)
    assert t["exit"] == pytest.approx(102.5)           # closes at STOP price
    assert t["stop_loss"] == pytest.approx(102.5)
    assert t["take_profit"] == pytest.approx(107.0)
    assert t["exit_reason"] == "stop_loss"
    assert t["bars_held"] == 1                         # entry_bar=5, exit_bar=6


def test_trade_b_sizing_and_pnl(result):
    t = result["trades"].iloc[1]
    # NOTE: same 150-pip stop distance as Trade A, but position_size uses
    # self.capital at open time — which has ALREADY grown from Trade A's
    # profit (10199.8815, not the original 10000). Sizing compounds.
    #   risk_amount = 10199.8815 * 0.01 = 101.998815
    #   risk_per_lot = 150 * 9.10 = 1365
    #   size = round(101.998815 / 1365, 4) = 0.0747
    assert t["size"] == pytest.approx(0.0747)
    assert t["pnl_pips"] == pytest.approx(-150.0)
    # pnl_gross = -150 * 9.10 * 0.0747 = -101.9655
    assert t["pnl_gross"] == pytest.approx(-101.97, abs=0.01)
    # pnl_net = -101.9655 - 0.2275 = -102.193 -> rounded -102.19
    assert t["pnl"] == pytest.approx(-102.19, abs=0.01)


def test_trade_b_entry_features_captured(result):
    # prev_row at entry (i=5) is bar i=4 -- the SIGNAL bar, not the entry bar.
    t = result["trades"].iloc[1]
    assert t["adx_entry"] == pytest.approx(22.0)
    assert t["atr_entry"] == pytest.approx(1.0)
    assert t["ema_distance"] == pytest.approx(-0.1)
    assert t["trend_gap"] == pytest.approx(0.6)


# ── Capital / equity-curve ordering (M0 fix #10) ────────────────────────

def test_final_capital(result):
    # 10000 + 199.8815 (Trade A) - 102.193 (Trade B, compounded sizing)
    # = 10097.6885 -> rounded 10097.69
    assert result["final_capital"] == pytest.approx(10097.69, abs=0.01)


def test_equity_reflects_close_same_bar_not_lagged(result):
    # Equity must jump on the SAME bar a trade closes, not one bar later.
    # This is the regression check for the equity-ordering fix (M0 #10):
    # previously equity was appended BEFORE trade management, lagging
    # every close by one bar.
    eq = [pt["equity"] for pt in result["equity_curve"]]
    # eq[0..6] correspond to bars i=1..7
    assert eq[0] == pytest.approx(10000.0)                    # i=1: trade just opened, no close yet
    assert eq[1] == pytest.approx(10000.0)                    # i=2: still open
    assert eq[2] == pytest.approx(10199.8815, abs=0.001)      # i=3: Trade A closes THIS bar
    assert eq[3] == pytest.approx(10199.8815, abs=0.001)      # i=4: unchanged, no trade
    assert eq[4] == pytest.approx(10199.8815, abs=0.001)      # i=5: Trade B just opened
    assert eq[5] == pytest.approx(10097.6885, abs=0.001)      # i=6: Trade B closes THIS bar
    assert eq[6] == pytest.approx(10097.6885, abs=0.001)      # i=7: unchanged, no trade


# ── Pessimistic-fill sanity check (independent of the two designed trades) ──

def test_pessimistic_fill_prefers_stop_when_both_hit_same_bar():
    # A bar where both stop AND target are technically touched must close
    # at the STOP, never the target — this is the "pessimistic fill"
    # integrity fix and must never regress silently.
    rows = [
        _bar(100.0, 101.0, 99.0, 100.5, 1.0, 25, 0.5, 1.0, 1),   # i=0 signal
        _bar(101.0, 102.0, 100.5, 101.5, 1.0, 24, 0.4, 0.9, 0),  # i=1 entry (open=101, stop=99.5, target=104)
        _bar(101.5, 110.0, 90.0, 100.0, 1.0, 23, 0.3, 0.8, 0),   # i=2 BOTH hit (low=90 <= stop, high=110 >= target)
    ]
    idx = pd.date_range("2024-01-01 00:00", periods=len(rows), freq="h")
    df = pd.DataFrame(rows, index=idx)

    sim = Simulator(symbol="USDJPY")
    result = sim.run(df)

    t = result["trades"].iloc[0]
    assert t["exit_reason"] == "stop_loss_ambiguous"
    assert t["exit"] == pytest.approx(99.5)   # stop price, NOT target price


# ── Time-exit sanity check ───────────────────────────────────────────────

def test_time_exit_fires_at_max_bars_in_trade():
    # A trade that never hits stop or target must close at MAX_BARS_IN_TRADE,
    # at the bar's close price, reason="time_exit".
    rows = [_bar(100.0, 101.0, 99.0, 100.5, 1.0, 25, 0.5, 1.0, 1)]   # i=0 signal
    # Entry bar + enough flat bars to exceed MAX_BARS_IN_TRADE without
    # touching stop (99.5) or target (104).
    for _ in range(MAX_BARS_IN_TRADE + 2):
        rows.append(_bar(101.0, 101.5, 100.8, 101.0, 1.0, 22, 0.1, 0.5, 0))

    idx = pd.date_range("2024-01-01 00:00", periods=len(rows), freq="h")
    df = pd.DataFrame(rows, index=idx)

    sim = Simulator(symbol="USDJPY")
    result = sim.run(df)

    assert result["total_trades"] == 1
    t = result["trades"].iloc[0]
    assert t["exit_reason"] == "time_exit"
    assert t["bars_held"] == MAX_BARS_IN_TRADE
