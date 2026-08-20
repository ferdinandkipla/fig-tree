# execution/costs.py
# FIX: Instrument-aware — correct pip_size per symbol
# FIX (cost model v2, Commit 1/2): total_cost() now scales by position
# size. Previously returned a flat one-standard-lot cost regardless of
# actual trade size, while pnl_gross correctly scaled by size --
# under-costing large positions, over-costing small ones. Bug found
# during cost-model-v2 scoping, documented in
# docs/COST_MODEL_V2_PLAN.md Sec 1 and research/COST_MODEL_ERRATA.md.
# ADD (cost model v2, Commit 2/2): swap cost, wired from
# research/S1_SWAP_RATES_SNAPSHOT_V2.md (supersedes the 2026-07-24
# snapshot, refreshed 2026-08-20).
#
# DECISION (2026-08-20, research/S1_SWAP_RATES_SNAPSHOT_V2.md "Decision"
# section): these rates are now the PERMANENT accepted baseline, not a
# placeholder pending re-sourcing. IC Markets does not publish a static
# swap-rate table for this broker -- their own material states swap
# rates as "Variable, check your platform" -- so "re-source from a
# verified, non-demo source" is not achievable via public sourcing and
# has been replaced with: demo-sourced + periodically refreshed +
# cross-checked for plausibility against an independent broker's
# published numbers (see the snapshot doc for specifics). The
# demo-vs-live distinction remains genuinely open; if live-account
# access ever becomes available, that comparison would supersede this.
#
# AUDUSD hard-block: spread_pips is still a 1.2-pip PLACEHOLDER in
# core/instruments.py (IC Markets' spec sheet confirms spreads are
# "Variable" broker-wide -- no fixed number exists to source instead;
# this needs a live-sampled average from MT5, not a published lookup).
# total_cost() raises for AUDUSD unless the caller explicitly passes
# allow_placeholder=True -- kills remain computable (placeholder costs
# only make a kill MORE likely, never manufacture a false survival),
# but silent trust is refused. AUDUSD's swap rate itself is no longer
# the blocking issue (accepted under the same decision as the other 4
# instruments) -- only the spread placeholder keeps the hard block active.

from core.instruments import get_meta
from execution.rollover import count_rollover_nights

PLACEHOLDER_INSTRUMENTS = {"AUDUSD"}

# Per-standard-lot swap rates, broker's native units. Refreshed
# 2026-08-20 (see research/S1_SWAP_RATES_SNAPSHOT_V2.md for the prior
# 2026-07-24 values, drift observed, and the permanent-baseline decision).
SWAP_RATES = {
    "USDJPY": {"long": 8.131, "short": -16.888},
    "XAUUSD": {"long": -57.294, "short": 39.452},
    "GBPJPY": {"long": 11.399, "short": -22.900},
    "EURUSD": {"long": -8.276, "short": 1.533},
    "AUDUSD": {"long": -2.546, "short": -4.442},  # swap accepted; spread still placeholder, see PLACEHOLDER_INSTRUMENTS
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