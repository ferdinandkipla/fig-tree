# execution/simulator.py
# All fixes applied:
#   1. No lookahead bias    — signal bar[i], entry bar[i+1] open
#   2. Pessimistic fill     — stop before target if both hit same bar
#   3. Instrument-aware     — pip-correct costs and sizing
#   4. Trade state object   — dataclass Trade()
#   5. Regime tagging       — ADX, ATR, session, year on every trade
#   6. Time-based exit      — MAX_BARS_IN_TRADE = 10 (40hrs on H4)
#   7. Warmup in strategy   — handled upstream in strategy.prepare()
#
# M0 fixes (research-integrity review):
#   8. Generic ENTRY_FEATURES capture — regime dict no longer hardcodes
#      which columns get recorded; any column added in strategy.prepare()
#      and declared in core.config.ENTRY_FEATURES is captured automatically.
#      Fixes the silent ema_distance/trend_gap NaN bug (schema promised
#      columns the producer never populated).
#   9. Stop/target recomputed from the ACTUAL entry price (row["open"]),
#      not the previous bar's close-based stop_loss/take_profit. Previously
#      a gap between prev_row's close and the next bar's open silently
#      skewed realized R:R away from the configured ratio.
#  10. Equity curve now appended AFTER trade management for the bar,
#      so each equity point reflects capital net of any close on that
#      bar rather than lagging it by one bar.

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from risk.sizing import position_size
from risk.exposure import ExposureGuard
from risk.drawdown import max_drawdown
from execution.costs import total_cost
from core.instruments import get_meta, SESSION_HOURS
from core.config import RISK, BACKTEST, ENTRY_FEATURES

MAX_BARS_IN_TRADE = 10  # H4 x 10 = ~40 hours

# Feature names that keep their legacy "<name>_entry" column name in the
# trade record, preserving backward compatibility with research/walkforward.py
# which expects adx_entry / atr_entry specifically.
_LEGACY_ENTRY_SUFFIX = ("adx", "atr")


@dataclass
class Trade:
    symbol:     str
    entry:      float
    stop:       float
    target:     float
    size:       float
    entry_dt:   object
    entry_bar:  int
    direction:  int = 1   # +1 = long, -1 = short. Default preserves old long-only behavior.
    regime:     dict = field(default_factory=dict)
    exit:        Optional[float]  = None
    exit_dt:     Optional[object] = None
    exit_reason: Optional[str]   = None
    bars_held:   Optional[int]   = None
    pnl:         Optional[float] = None


class Simulator:

    def __init__(self, symbol: str, entry_features: list = None, max_bars_in_trade: int = None):
        self.symbol       = symbol
        self.meta         = get_meta(symbol)
        self.capital      = BACKTEST["initial_capital"]
        self.trades       = []
        self.equity_curve = []
        self._running_peak = None
        self.guard        = ExposureGuard(
            max_consecutive_loss = RISK["max_consecutive_loss"],
            max_open_trades      = RISK["max_open_trades"],
            max_dd_halt          = -RISK["max_drawdown_halt"] * 100,
        )
        self._trade: Optional[Trade] = None
        # M2: entry_features now comes from the Strategy instance
        # (strategy.entry_features) via the caller, not a hardcoded
        # import -- the simulator has zero strategy-name knowledge.
        # Defaults to the core.config global for backward compatibility
        # with any caller that hasn't been updated to pass it explicitly.
        self.entry_features = entry_features if entry_features is not None else ENTRY_FEATURES
        # H-003: configurable per-instance so Arm A (default 10) vs Arm B
        # (500, functionally "no time exit") can run side-by-side without
        # a global mutation racing between them.
        self.max_bars_in_trade = max_bars_in_trade if max_bars_in_trade is not None else MAX_BARS_IN_TRADE

    def run(self, df: pd.DataFrame) -> dict:
        for i in range(1, len(df)):
            row      = df.iloc[i]
            prev_row = df.iloc[i - 1]
            dt       = df.index[i]

            self.guard.on_bar()

            # ── Manage open trade (may close this bar) ─────────────
            if self._trade is not None:
                # Direction-aware hit detection (S1 long/short redesign).
                # Long: stop below entry, target above -- price falling
                # hits stop, rising hits target (unchanged from before).
                # Short: stop above entry, target below -- mirrored.
                if self._trade.direction == 1:
                    stop_hit   = row["low"]  <= self._trade.stop
                    target_hit = row["high"] >= self._trade.target
                else:
                    stop_hit   = row["high"] >= self._trade.stop
                    target_hit = row["low"]  <= self._trade.target
                bars_held  = i - self._trade.entry_bar

                if stop_hit and target_hit:          # FIX 2: pessimistic
                    self._close(dt, self._trade.stop, "stop_loss_ambiguous", bars_held)
                elif stop_hit:
                    self._close(dt, self._trade.stop, "stop_loss", bars_held)
                elif target_hit:
                    self._close(dt, self._trade.target, "take_profit", bars_held)
                elif bars_held >= self.max_bars_in_trade:  # FIX 6: time exit
                    self._close(dt, row["close"], "time_exit", bars_held)

            # ── M0 FIX 10: mark equity AFTER any close this bar ─────
            current_dd = self._current_dd()
            self.equity_curve.append({"datetime": dt, "equity": self.capital})
            # Guardrail #4 infra fix (S1 prep): O(1) running peak instead
            # of rebuilding a full pandas Series + cummax() every bar
            # (was O(n^2) total -- flagged in the original code audit,
            # confirmed to actually bite at scale: a 4x bar-count
            # synthetic proxy showed a 10.28x slowdown, not ~4x, before
            # this fix). Updated here, right after each append, so
            # _current_dd() always sees the peak through the most
            # recently appended point -- semantics unchanged, verified
            # byte-identical trade output vs pre-fix hashes.
            self._running_peak = self.capital if self._running_peak is None else max(self._running_peak, self.capital)

            # ── New entry: signal from prev bar, enter at current open ──
            if self._trade is None and prev_row.get("signal", 0) == 1:
                if self.guard.can_trade(current_dd):
                    if self._in_valid_session(dt):
                        self._open(row, prev_row, dt, i)

        return self._report()

    def _open(self, row, prev_row, dt, bar_idx: int):
        entry = row["open"]                # FIX 1: next bar open

        # S1 long/short redesign: direction comes from the strategy's
        # "direction" column (+1 long, -1 short), defaulting to +1 (long)
        # if the column is absent -- this is what keeps every existing
        # long-only strategy (trend_pullback, null_random) byte-identical
        # to their pre-redesign canonical hashes without any change to
        # those strategy files.
        direction = int(prev_row.get("direction", 1))

        # M0 FIX 9 (revised): stop/target derived from the ACTUAL entry
        # price, not prev_row's close-based stop_loss/take_profit.
        #
        # CODE AUDIT FIX: originally this imported STOP_ATR_MULT/RISK_REWARD
        # directly from strategies.trend_pullback.params — a coupling
        # violation that made the simulator depend on one specific
        # strategy, pre-empting the M2 Strategy protocol. Fixed: the
        # strategy now emits stop_distance/target_distance columns (price
        # units, computed from its own params in prepare()), and the
        # simulator only re-anchors those distances onto the real entry
        # price. The simulator no longer knows or cares which strategy
        # produced them.
        stop_dist   = prev_row["stop_distance"]
        target_dist = prev_row["target_distance"]
        if direction == 1:
            stop   = entry - stop_dist
            target = entry + target_dist
        else:  # direction == -1: geometry mirrors around entry
            stop   = entry + stop_dist
            target = entry - target_dist

        size   = position_size(          # FIX 3: pip-aware; abs(entry-stop)
            self.capital, RISK["risk_per_trade"],   # already direction-agnostic,
            entry, stop, self.symbol                # verified before this change
        )

        # M0 FIX 8: generic entry-feature capture. Any column declared
        # in core.config.ENTRY_FEATURES is pulled from the signal bar
        # (prev_row) automatically — no simulator edit needed to add a
        # new research feature.
        regime = {
            "session": self._active_session(dt),
            "year":    pd.Timestamp(dt).year,
        }
        for feat in self.entry_features:
            val = prev_row.get(feat)
            regime[feat] = round(float(val), 5) if pd.notna(val) else None

        self._trade = Trade(             # FIX 4: Trade object
            symbol    = self.symbol,
            entry     = entry,
            stop      = stop,
            target    = target,
            size      = size,
            entry_dt  = dt,
            entry_bar = bar_idx,
            direction = direction,
            regime    = regime,
        )
        self.guard.on_open()

    def _close(self, dt, exit_price: float, reason: str, bars_held: int):
        t    = self._trade
        meta = self.meta

        # ── CORRECT P&L ACCOUNTING ────────────────────────────────
        # Convert price delta → pips → dollars. Direction-aware (S1
        # redesign): for longs (direction=1), unchanged from before --
        # profit when exit > entry. For shorts (direction=-1), profit
        # when exit < entry, i.e. price_delta flips sign. Multiplying
        # by t.direction handles both uniformly without an if/else here.
        price_delta = (exit_price - t.entry) * t.direction    # price units
        pnl_pips    = price_delta / meta["pip_size"]          # → pips
        pnl_gross   = pnl_pips * meta["pip_value"] * t.size   # → dollars

        # Instrument-aware costs (already in dollars)
        pnl_net      = pnl_gross - total_cost(self.symbol)
        self.capital += pnl_net

        trade_record = {
            "symbol":       t.symbol,
            "direction":    t.direction,
            "entry_dt":     t.entry_dt,
            "exit_dt":      dt,
            "entry":        round(t.entry, 5),
            "exit":         round(exit_price, 5),
            "stop_loss":    round(t.stop, 5),
            "take_profit":  round(t.target, 5),
            "size":         round(t.size, 4),
            "pnl_pips":     round(pnl_pips, 1),
            "pnl_gross":    round(pnl_gross, 2),
            "pnl":          round(pnl_net, 2),
            "bars_held":    bars_held,
            "exit_reason":  reason,
        }

        # M0 FIX 8 (cont.): generic capture, with legacy column-name
        # preservation for adx/atr so research/walkforward.py (which
        # expects adx_entry / atr_entry) keeps working unchanged.
        for feat in self.entry_features:
            key = f"{feat}_entry" if feat in _LEGACY_ENTRY_SUFFIX else feat
            trade_record[key] = t.regime.get(feat)

        trade_record["session"] = t.regime.get("session")
        trade_record["year"]    = t.regime.get("year")

        self.trades.append(trade_record)

        self.guard.on_win() if pnl_net > 0 else self.guard.on_loss()
        self._trade = None

    def _in_valid_session(self, dt) -> bool:
        return True  # disabled in research mode — reintroduce in Phase 3

    def _active_session(self, dt) -> Optional[str]:
        hour     = pd.Timestamp(dt).hour
        sessions = self.meta.get("sessions", [])
        for s in sessions:
            start, end = SESSION_HOURS[s]
            if start <= hour < end:
                return s
        return None

    def _current_dd(self) -> float:
        if len(self.equity_curve) < 2:
            return 0.0
        last_equity = self.equity_curve[-1]["equity"]
        peak = self._running_peak
        return (last_equity - peak) / peak * 100 if peak > 0 else 0.0

    def _report(self) -> dict:
        if not self.trades:
            return {"error": "No trades executed. Check signal logic or session filter."}

        df_t   = pd.DataFrame(self.trades)
        wins   = df_t[df_t["pnl"] > 0]
        losses = df_t[df_t["pnl"] <= 0]

        pf = (wins["pnl"].sum() / abs(losses["pnl"].sum())
              if losses["pnl"].sum() != 0 else 999)

        returns = df_t["pnl"] / BACKTEST["initial_capital"]
        sharpe  = (returns.mean() / returns.std() * np.sqrt(252)
                   if returns.std() > 0 else 0)

        return {
            "total_trades":    len(df_t),
            "win_rate":        round(len(wins) / len(df_t) * 100, 2),
            "profit_factor":   round(pf, 2),
            "total_return_%":  round((self.capital - BACKTEST["initial_capital"])
                                     / BACKTEST["initial_capital"] * 100, 2),
            "max_drawdown_%":  max_drawdown(self.equity_curve),
            "sharpe_ratio":    round(sharpe, 2),
            "sharpe_note":     "trade-based approx — fix in Phase 2 M1",
            "avg_win":         round(wins["pnl"].mean(), 2)   if len(wins)   > 0 else 0,
            "avg_loss":        round(losses["pnl"].mean(), 2) if len(losses) > 0 else 0,
            "avg_bars_held":   round(df_t["bars_held"].mean(), 1),
            "max_bars_held":   int(df_t["bars_held"].max()),
            "time_exits":      int((df_t["exit_reason"] == "time_exit").sum()),
            "ambiguous_fills": int((df_t["exit_reason"] == "stop_loss_ambiguous").sum()),
            "final_capital":   round(self.capital, 2),
            "trades":          df_t,
            "equity_curve":    self.equity_curve,
        }
