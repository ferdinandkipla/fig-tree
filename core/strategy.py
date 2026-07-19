# core/strategy.py
#
# M2: the Strategy protocol. Any future hypothesis (trend_pullback,
# null_random, and whatever H-001/H-002/H-003 need) implements this and
# plugs into main.py / the simulator without either needing to know the
# strategy's name or internals.
#
# Contract:
#   - prepare() adds indicators + a "signal" column (1/0) to a COPY of
#     the input df, plus "stop_distance"/"target_distance" columns
#     (price-unit distances the simulator re-anchors onto the real
#     entry price -- see execution/simulator.py _open()). Must not
#     mutate the input df.
#   - params is a config snapshot for the ledger -- whatever this
#     strategy instance actually used (not the global defaults; if a
#     strategy is instantiated with a specific seed/param override,
#     params must reflect that specific instance).
#   - entry_features is the list of prepare()-added columns the
#     simulator should capture onto every trade record (replaces the
#     old core.config.ENTRY_FEATURES global -- each strategy now owns
#     its own list, though trend_pullback and null_random currently
#     declare the same one for comparability).

from typing import Protocol, runtime_checkable
import pandas as pd


@runtime_checkable
class Strategy(Protocol):
    name: str

    def prepare(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Add indicators + a boolean/int 'signal' column, plus
        'stop_distance'/'target_distance' columns. Must not mutate df."""
        ...

    @property
    def params(self) -> dict:
        """Config snapshot for the ledger."""
        ...

    @property
    def entry_features(self) -> list:
        """Columns the simulator captures at entry (from the signal bar)."""
        ...
