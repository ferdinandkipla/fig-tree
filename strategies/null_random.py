# strategies/null_random.py
#
# M2: the null model. Identical to TrendPullbackStrategy in every respect
# (same indicators via strategies/common.py, same ATR-based stop/target
# geometry, same warmup, same entry_features, same simulator, same costs,
# same one-position constraint) EXCEPT entry selection, which is a
# matched-frequency random sample rather than the trend/pullback signal
# funnel. Differing in exactly one variable is the whole point: any
# performance gap between this and the real strategy is attributable to
# entry selection, not to some other silently-drifted difference.
#
# Direction: long-only by construction. The shared simulator only
# implements long entries (execution/simulator.py _open(): stop = entry
# - dist, target = entry + dist) -- every strategy using it inherits the
# same directional bias automatically. There is no random-direction
# option; per the M2 spec, that would answer a different question.

import numpy as np
import pandas as pd
from strategies.common import compute_common_features, WARMUP_BARS
from core.config import ENTRY_FEATURES, SEED


class NullRandomStrategy:
    name = "null_random"

    def __init__(self, n_signals: int, seed: int = None):
        """
        n_signals: the REAL strategy's signal count for this exact
            symbol/window. Must be computed by the caller as
            TrendPullbackStrategy().prepare(df, symbol)["signal"].sum()
            on the SAME df, so matched-frequency is enforced by
            construction rather than a hand-maintained number that can
            drift out of sync with the real strategy after a code change.
        seed: defaults to core.config.SEED. Pass a different int per
            run to build a null distribution -- see
            research/run_null_model.py for the N-seed driver.
        """
        self.n_signals = n_signals
        self.seed      = seed if seed is not None else SEED

    def prepare(self, df: pd.DataFrame, symbol: str = "USDJPY") -> pd.DataFrame:
        df = compute_common_features(df)
        df = df.iloc[WARMUP_BARS:].copy()

        # Eligible bars: exactly the rows TrendPullbackStrategy's
        # dropna() would keep (all indicator/geometry columns non-null).
        # Sampling only from this set means the null can't land on a bar
        # the real strategy's own pipeline would have discarded anyway.
        required_cols = ["ema_fast", "ema_slow", "adx", "atr",
                         "ema_distance", "trend_gap",
                         "stop_distance", "target_distance"]
        eligible_mask = df[required_cols].notna().all(axis=1)
        eligible_idx  = np.flatnonzero(eligible_mask.values)

        n = min(self.n_signals, len(eligible_idx))
        if n < self.n_signals:
            print(f"[NullRandom] WARNING ({symbol}): requested "
                  f"{self.n_signals} signals but only {len(eligible_idx)} "
                  f"eligible bars exist -- sampling {n} instead.")

        rng    = np.random.default_rng(self.seed)
        chosen = rng.choice(eligible_idx, size=n, replace=False)

        df["signal"] = 0
        df.iloc[chosen, df.columns.get_loc("signal")] = 1

        print(f"[NullRandom] ({symbol}, seed={self.seed}): "
              f"{n} random signals sampled from {len(eligible_idx)} eligible bars")

        return df.dropna()

    @property
    def params(self) -> dict:
        return {
            "strategy":  self.name,
            "seed":      self.seed,
            "n_signals": self.n_signals,
        }

    @property
    def entry_features(self) -> list:
        # Same list as trend_pullback -- required for the two to be
        # comparable on the same regime/feature breakdowns.
        return ENTRY_FEATURES
