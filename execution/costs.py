# execution/costs.py
# FIX: Instrument-aware — correct pip_size per symbol
# FIX (cost model v2, Commit 1/2): total_cost() now scales by position
# size. Previously returned a flat one-standard-lot cost regardless of
# actual trade size, while pnl_gross correctly scaled by size --
# under-costing large positions, over-costing small ones. Bug found
# during cost-model-v2 scoping, documented in
# docs/COST_MODEL_V2_PLAN.md Sec 1 and research/COST_MODEL_ERRATA.md.
# ADD (cost model v2, Commit 2/2): swap cost, wired from
# research/S1_SWAP_RATES_SNAPSHOT.md AS-IS. That snapshot's caveats
# apply to every number this module returns for the swap term:
#   1. TODAY-SNAPSHOT, not historical -- applying 2026-07-24's rates
#      uniformly across a 2019-2025 backtest window is an approximation.
#   2. DEMO-ACCOUNT sourced (ICMarketsSC-Demo) -- may differ from live
#      account terms.
#   3. Sign convention: positive credited, negative charged. XAUUSD's
#      long/short asymmetry is large and UNVERIFIED against IC Markets'
#      published contract specs.
# Re-sourcing is explicitly OUT of scope for this module -- see
# docs/COST_MODEL_V2_PLAN.md Sec 0.1. ANY hypothesis whose acceptance
# depends on swap-sensitive cost stress must re-validate against a live
# source first, per RESEARCH_PROGRAM.md Sec 6's acceptance gate.
#
# AUDUSD hard-block: no real contract spec has been sourced for AUDUSD
# (spread_pips is still a 1.2-pip PLACEHOLDER in core/instruments.py,
# and no swap rate exists for it beyond the demo snapshot's own
# placeholder-quality numbers). total_cost() raises for AUDUSD unless
# the caller explicitly passes allow_placeholder=True -- kills remain
# computable (placeholder costs only make a kill MORE likely, never
# manufacture a false survival), but silent trust is refused.

from core.instruments import get_meta
from execution.rollover import count_rollover_nights

PLACEHOLDER_INSTRUMENTS = {"AUDUSD"}

# Per-standard-lot swap rates, broker's native units, wired as-is from
# research/S1_SWAP_RATES_SNAPSHOT.md (pulled 2026-07-24, ICMarketsSC-Demo).
SWAP_RATES = {
    "USDJPY": {"long": 8.752, "short": -17.618},
    "XAUUSD": {"long": -53.763, "short": 36.931},
    "GBPJPY": {"long": 12.143, "short": -23.758},
    "EURUSD": {"long": -8.166, "short": 1.454},
    "AUDUSD": {"long": -2.231, "short": -4.739},  # placeholder-quality, see PLACEHOLDER_INSTRUMENTS
}


class PlaceholderInstrumentError(Exception):
    """Raised when total_cost() is called for a PLACEHOLDER_INSTRUMENTS
    symbol without explicit allow_placeholder=True."""
    pass


def swap_cost(symbol: str, size: float, direction: int, entry_dt, exit_dt) -> float:
    """Swap cost in dollars for one trade. Positive = cost to the
    account (charged), matching total_cost()'s sign convention -- note
    SWAP_RATES itself uses the opposite convention (positive=credited)
    per the snapshot's own documentation, so the sign is flipped here."""
    nights = count_rollover_nights(entry_dt, exit_dt)
    if nights == 0:
        return 0.0
    rate = SWAP_RATES[symbol]["long" if direction == 1 else "short"]
    return -rate * size * nights  # flip sign: snapshot's credit(+)/charge(-) -> cost(+)/credit(-)


def total_cost(symbol: str, size: float, direction: int = 1, entry_dt=None,
                exit_dt=None, slippage_pips: float = 1.0,
                allow_placeholder: bool = False) -> float:
    if symbol in PLACEHOLDER_INSTRUMENTS and not allow_placeholder:
        raise PlaceholderInstrumentError(
            f"{symbol} has no real contract spec sourced (spread is a "
            f"placeholder, swap rate is placeholder-quality). Kills remain "
            f"valid under placeholder costs -- pass allow_placeholder=True "
            f"explicitly to proceed. No acceptance is valid for {symbol} "
            f"regardless of this flag; see RESEARCH_PROGRAM.md Sec 6."
        )
    meta        = get_meta(symbol)
    spread_cost = meta["spread_pips"]  * meta["pip_size"] * meta["pip_value"] * size
    slip_cost   = slippage_pips        * meta["pip_size"] * meta["pip_value"] * size
    swap        = 0.0
    if entry_dt is not None and exit_dt is not None:
        swap = swap_cost(symbol, size, direction, entry_dt, exit_dt)
    return spread_cost + slip_cost + swap