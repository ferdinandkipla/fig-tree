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
# S1 UPDATE: direction can now also be randomized (signed=True), per
# the long/short redesign. This is the "drift-neutral null" -- a
# random-direction, random-timing null model converts the project's
# recurring drift confound (M2's original long-only null showed
# +$8-12/trade mean expectancy on TRAIN purely from being long during a
# long-friendly 2019-2022 window) into a controlled, measurable
# quantity instead of a caveat repeated in every writeup.
#
# Design choice: entry TIMING is drawn identically whether signed=False
# or signed=True, for the same seed -- the direction coin-flip is drawn
# from the SAME rng stream, AFTER entry selection, so turning on
# direction randomization changes exactly one variable relative to the
# existing (superseded-as-benchmark, still-historical) long-only null,
# not two at once.

import numpy as np
import pandas as pd
from strategies.common import compute_common_features, WARMUP_BARS
from core.config import ENTRY_FEATURES, SEED


class NullRandomStrategy:
    name = "null_random"

    def __init__(self, n_signals: int, seed: int = None, signed: bool = False):
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
        signed: if True, each sampled entry also gets a random direction
            (+1 long / -1 short, coin flip, same rng stream as entry
            selection). If False (default), every entry is long -- the
            original M2 null, kept as the historical/superseded
            long-only benchmark.
        """
        self.n_signals = n_signals
        self.seed      = seed if seed is not None else SEED
        self.signed    = signed

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

        # Direction: default long everywhere (only entry bars' direction
        # is ever read by the simulator, via prev_row at signal time --
        # non-entry bars' direction value is irrelevant but set for
        # column completeness/clarity).
        df["direction"] = 1
        if self.signed:
            # Drawn from the SAME rng stream, AFTER entry selection --
            # entry timing is bar-for-bar identical to signed=False for
            # the same seed; only direction is new.
            directions = rng.choice([1, -1], size=n)
            df.iloc[chosen, df.columns.get_loc("direction")] = directions

        mode_label = "signed (random direction)" if self.signed else "long-only"
        print(f"[NullRandom] ({symbol}, seed={self.seed}, {mode_label}): "
              f"{n} random signals sampled from {len(eligible_idx)} eligible bars")

        return df.dropna()

    @property
    def params(self) -> dict:
        return {
            "strategy":  self.name,
            "seed":      self.seed,
            "n_signals": self.n_signals,
            "signed":    self.signed,
        }

    @property
    def entry_features(self) -> list:
        # Same list as trend_pullback -- required for the two to be
        # comparable on the same regime/feature breakdowns.
        return ENTRY_FEATURES
