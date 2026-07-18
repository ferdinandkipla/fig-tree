# core/config.py
from datetime import datetime
import MetaTrader5 as mt5

RESEARCH_MODE = True

BACKTEST = {
    "initial_capital": 10000,
    "start":           datetime(2019, 1, 1),
    "end":             datetime(2025, 1, 1),   # full range
    "timeframe":       mt5.TIMEFRAME_H4,
    "timeframe_label": "H4",
}

INSTRUMENTS = ["USDJPY", "XAUUSD", "GBPJPY"]

RISK = {
    "risk_per_trade":       0.01,
    "max_drawdown_halt":    0.15,
    "max_consecutive_loss": 6,
    "max_open_trades":      1,
}

COSTS = {
    "spread_pips":   2,
    "slippage_pips": 1,
    "pip_value":     10,
    "commission":    0,
}

TREND_PULLBACK = {
    "ema_fast":            50,
    "ema_slow":            200,
    "adx_period":          14,
    "adx_threshold":       20,
    #"adx_ceiling":         25.0,  # uniform, evidence-based, not instrument-specific
    "atr_period":          14,
    "stop_atr_multiplier": 1.5,
    "risk_reward":         2.0,
    "pullback_tolerance":  0.5,
}

# ── M0: Feature capture mechanism ──────────────────────────────────────
# Columns copied from the SIGNAL bar onto every trade record.
# Any column strategy.prepare() adds to the DataFrame can be declared here
# and the simulator will capture it automatically — no simulator edits
# needed to test a new entry-context hypothesis.
ENTRY_FEATURES = ["adx", "atr", "ema_distance", "trend_gap"]
