# execution/simulator.py
# All 6 fixes applied:
#   1. No lookahead bias    — signal bar[i], entry bar[i+1] open
#   2. Pessimistic fill     — stop before target if both hit same bar
#   3. Instrument-aware     — pip-correct costs and sizing
#   4. Trade state object   — dataclass Trade()
#   5. Regime tagging       — ADX, ATR, session, year on every trade
#   6. Time-based exit      — MAX_BARS_IN_TRADE = 10 (40hrs on H4)
#   7. Warmup in strategy   — handled upstream in strategy.prepare()

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from risk.sizing import position_size
from risk.exposure import ExposureGuard
from risk.drawdown import max_drawdown
from execution.costs import total_cost
from core.instruments import get_meta, SESSION_HOURS
from core.config import RISK, BACKTEST

MAX_BARS_IN_TRADE = 10  # H4 x 10 = ~40 hours


@dataclass
class Trade:
    symbol:     str
    entry:      float
    stop:       float
    target:     float
    size:       float
    entry_dt:   object
    entry_bar:  int
    regime:     dict = field(default_factory=dict)
    exit:        Optional[float]  = None
    exit_dt:     Optional[object] = None
    exit_reason: Optional[str]   = None
    bars_held:   Optional[int]   = None
    pnl:         Optional[float] = None


class Simulator:

    def __init__(self, symbol: str):
        self.symbol       = symbol
        self.meta         = get_meta(symbol)
        self.capital      = BACKTEST["initial_capital"]
        self.trades       = []
        self.equity_curve = []
        self.guard        = ExposureGuard(
            max_consecutive_loss = RISK["max_consecutive_loss"],
            max_open_trades      = RISK["max_open_trades"],
            max_dd_halt          = -RISK["max_drawdown_halt"] * 100,
        )
        self._trade: Optional[Trade] = None

    def run(self, df: pd.DataFrame) -> dict:
        for i in range(1, len(df)):
            row      = df.iloc[i]
            prev_row = df.iloc[i - 1]
            dt       = df.index[i]
            current_dd = self._current_dd()

            self.guard.on_bar()   # ← ADD THIS LINE

            self.equity_curve.append({"datetime": dt, "equity": self.capital})
            # ... rest unchanged
            # ── Manage open trade ──────────────────────────────
            if self._trade is not None:
                stop_hit   = row["low"]  <= self._trade.stop
                target_hit = row["high"] >= self._trade.target
                bars_held  = i - self._trade.entry_bar

                if stop_hit and target_hit:          # FIX 2: pessimistic
                    self._close(dt, self._trade.stop, "stop_loss_ambiguous", bars_held)
                elif stop_hit:
                    self._close(dt, self._trade.stop, "stop_loss", bars_held)
                elif target_hit:
                    self._close(dt, self._trade.target, "take_profit", bars_held)
                elif bars_held >= MAX_BARS_IN_TRADE:  # FIX 6: time exit
                    self._close(dt, row["close"], "time_exit", bars_held)

            # ── New entry: signal from prev bar, enter at current open ──
            if self._trade is None and prev_row.get("signal", 0) == 1:
                if self.guard.can_trade(current_dd):
                    if self._in_valid_session(dt):
                        self._open(row, prev_row, dt, i)

        return self._report()

    def _open(self, row, prev_row, dt, bar_idx: int):
        entry  = row["open"]             # FIX 1: next bar open
        stop   = prev_row["stop_loss"]
        target = prev_row["take_profit"]
        size   = position_size(          # FIX 3: pip-aware
            self.capital, RISK["risk_per_trade"],
            entry, stop, self.symbol
        )
        regime = {                       # FIX 5: regime tag
            "adx":     round(prev_row.get("adx", 0), 1),
            "atr":     round(prev_row.get("atr", 0), 5),
            "session": self._active_session(dt),
            "year":    pd.Timestamp(dt).year,
        }
        self._trade = Trade(             # FIX 4: Trade object
            symbol    = self.symbol,
            entry     = entry,
            stop      = stop,
            target    = target,
            size      = size,
            entry_dt  = dt,
            entry_bar = bar_idx,
            regime    = regime,
        )
        self.guard.on_open()

    def _close(self, dt, exit_price: float, reason: str, bars_held: int):
        t    = self._trade
        meta = self.meta

        # ── CORRECT P&L ACCOUNTING ────────────────────────────────
        # Convert price delta → pips → dollars
        # Old (buggy):  pnl = (exit - entry) * size
        # New (correct): pnl = pips * pip_value * size
        price_delta = exit_price - t.entry                    # price units
        pnl_pips    = price_delta / meta["pip_size"]          # → pips
        pnl_gross   = pnl_pips * meta["pip_value"] * t.size   # → dollars

        # Instrument-aware costs (already in dollars)
        pnl_net      = pnl_gross - total_cost(self.symbol)
        self.capital += pnl_net

        self.trades.append({
            "symbol":       t.symbol,
            "entry_dt":     t.entry_dt,
            "exit_dt":      dt,
            "entry":        round(t.entry, 5),
            "exit":         round(exit_price, 5),
            "stop_loss":    round(t.stop, 5),       # ← ADD
            "take_profit":  round(t.target, 5),     # ← ADD
            "size":         round(t.size, 4),
            "pnl_pips":     round(pnl_pips, 1),
            "pnl_gross":    round(pnl_gross, 2),
            "pnl":          round(pnl_net, 2),
            "bars_held":    bars_held,
            "exit_reason":  reason,
            "adx_entry":    t.regime.get("adx"),
            "atr_entry":    t.regime.get("atr"),
            "session":      t.regime.get("session"),
            "year":         t.regime.get("year"),
            "ema_distance": t.regime.get("ema_distance"),
            "trend_gap":    t.regime.get("trend_gap"),
        })

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
        eq   = pd.Series([e["equity"] for e in self.equity_curve])
        peak = eq.cummax().iloc[-1]
        return (eq.iloc[-1] - peak) / peak * 100 if peak > 0 else 0.0

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
            "sharpe_note":     "trade-based approx — fix in Phase 2",
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