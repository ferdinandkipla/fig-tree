# strategies/trend_pullback/strategy.py
import pandas as pd
from strategies.common import compute_common_features, WARMUP_BARS
from strategies.trend_pullback.signals import entry_signal
from strategies.trend_pullback.params import (
    EMA_FAST, EMA_SLOW, ADX_PERIOD, ATR_PERIOD,
    STOP_ATR_MULT, RISK_REWARD, ADX_THRESHOLD, PULLBACK_TOLERANCE
)
from core.config import ENTRY_FEATURES


class TrendPullbackStrategy:
    """M2: Strategy-protocol implementation of the original trend-pullback
    system. Behavior is UNCHANGED from the pre-M2 module-level prepare() --
    this is a pure refactor (indicator computation moved to
    strategies/common.py, verbatim) so it must produce byte-identical
    trades_*.csv vs the M1 ledger hashes. See tests/test_determinism.py,
    which now doubles as the refactor-safety net for this claim."""

    name = "trend_pullback"

    def prepare(self, df: pd.DataFrame, symbol: str = "USDJPY") -> pd.DataFrame:
        df = compute_common_features(df)

        df["signal"]      = entry_signal(df, symbol=symbol)
        df["stop_loss"]   = df["close"] - (STOP_ATR_MULT * df["atr"])
        df["take_profit"] = df["close"] + (RISK_REWARD * STOP_ATR_MULT * df["atr"])

        df = df.iloc[WARMUP_BARS:].copy()
        print(f"[Strategy] Warmup stripped: {WARMUP_BARS} bars | "
              f"Remaining: {len(df)} | Signals: {df['signal'].sum()}")

        return df.dropna()

    @property
    def params(self) -> dict:
        return {
            "strategy":            self.name,
            "ema_fast":            EMA_FAST,
            "ema_slow":            EMA_SLOW,
            "adx_period":          ADX_PERIOD,
            "adx_threshold":       ADX_THRESHOLD,
            "atr_period":          ATR_PERIOD,
            "stop_atr_multiplier": STOP_ATR_MULT,
            "risk_reward":         RISK_REWARD,
            "pullback_tolerance":  PULLBACK_TOLERANCE,
        }

    @property
    def entry_features(self) -> list:
        return ENTRY_FEATURES


# ── Backward-compat module-level function ───────────────────────────────
# Some older call sites / notebooks may still call prepare(df, symbol=...)
# directly rather than instantiating the class. Keep it as a thin wrapper
# so nothing silently breaks; new code should use TrendPullbackStrategy().
def prepare(df: pd.DataFrame, symbol: str = "USDJPY") -> pd.DataFrame:
    return TrendPullbackStrategy().prepare(df, symbol=symbol)
