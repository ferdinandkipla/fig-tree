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
# AUDUSD hard-block: RESOLVED 2026-08-20, see the ADD COMMISSION block
# below for the full story (spread live-sampled, commission sourced,
# swap accepted). PLACEHOLDER_INSTRUMENTS is now empty. That fix
# surfaced a larger, NOT-yet-resolved question about whether
# USDJPY/GBPJPY/EURUSD's spread_pips were ever sourced from this
# account either -- see the "OPEN QUESTION" comment below
# COMMISSION_PER_LOT_USD.

from core.instruments import get_meta
from execution.rollover import count_rollover_nights

# AUDUSD RESOLVED (2026-08-20): spread live-sampled
# (research/sample_audusd_spread.py, 0.075 pips mean), swap accepted
# under the permanent-baseline decision (S1_SWAP_RATES_SNAPSHOT_V2.md),
# commission sourced (see COMMISSION_PER_LOT_USD above). All three cost
# components are now sourced to the same standard as the other 4 FX
# majors -- hard block lifted, AUDUSD removed from
# PLACEHOLDER_INSTRUMENTS.
#
# OPEN QUESTION SURFACED BY THIS FIX, NOT RESOLVED HERE: AUDUSD's old
# 1.2-pip placeholder was ~16x the actual live-sampled Raw-account
# spread (0.075 pips). USDJPY/GBPJPY/EURUSD's spread_pips (1.5/2.5/1.0)
# were never independently sourced from this account either -- they
# read like generic standard-account-style estimates, the same category
# of unverified number AUDUSD's placeholder turned out to be. If they
# have the same problem, the missing-commission fix above and an
# overstated-spread problem could be partially offsetting for those 3
# pairs, or could not be, instrument by instrument -- not assumed
# either way. XAUUSD's commission is also still unsourced (Forex-only
# spec sheet doesn't cover metals). Flagged as a new, larger debt item.
PLACEHOLDER_INSTRUMENTS = set()

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


# COMMISSION (added 2026-08-20): confirmed missing entirely from this
# module until now -- account 52974506 is explicitly a "Raw Spread"
# account (confirmed via IC Markets' own account dashboard, not
# inferred), meaning broker compensation comes through a separate
# per-lot commission, not spread markup. A live-sampled AUDUSD spread
# check this session came back at ~0.075 pips mean (vs. the 1.2-pip
# placeholder) -- correct for a raw account, but using it alone would
# have badly under-costed every trade by omitting commission entirely.
#
# Source: IC Markets' Forex Product Specification Sheet
# (cdn.icmarkets.com/uploads/FSA/Forex-Product-Specificiation-Sheet.pdf),
# "Commission (RawSpread): $7USD, $7AUD, 5GBP, 5.50EUR, 9SGD, 650JPY,
# 6.60CHF, 9NZD, 7CAD, 54.25HKD per lot round turn" -- a flat per-lot
# fee keyed by ACCOUNT currency, not by instrument traded. This
# account's currency is USD, so $7.00/lot round-turn applies uniformly
# across all FX pairs on this account.
#
# SCOPE, DELIBERATELY LIMITED: applied to the 4 FX majors only
# (USDJPY, GBPJPY, EURUSD, AUDUSD). NOT applied to XAUUSD -- that spec
# sheet was Forex-specific; metals commission may differ and has not
# been sourced (IC Markets' own material notes "commissions in Forex
# and Precious Metals... rates vary by account type" without giving
# the metals number). Applying the FX rate to XAUUSD without evidence
# would repeat exactly the mistake this fix is correcting. Flagged as
# a distinct open item, not assumed equal to FX's rate.
COMMISSION_PER_LOT_USD = 7.00
COMMISSION_APPLIES_TO = {"USDJPY", "GBPJPY", "EURUSD", "AUDUSD"}


def commission_cost(symbol: str, size: float) -> float:
    """Round-turn commission in dollars for one trade, this account's
    currency (USD) only. Returns 0.0 for instruments not in
    COMMISSION_APPLIES_TO (currently: XAUUSD, pending metals-specific
    sourcing -- see module header)."""
    if symbol not in COMMISSION_APPLIES_TO:
        return 0.0
    return COMMISSION_PER_LOT_USD * size


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
    # FIX (confirmed via tests/test_cost_model_spec.py, hand-computed
    # against pip_value's own documented units): pip_value is ALREADY
    # dollars-per-pip-per-standard-lot -- confirmed by its use
    # everywhere else in this codebase (execution/simulator.py's
    # `pnl_gross = pnl_pips * pip_value * size`, risk/sizing.py's
    # `risk_per_lot = stop_pips * pip_value`), neither of which
    # multiplies by pip_size again. This formula previously did,
    # making spread/slip ~10,000x too small for EURUSD (1 correct pip
    # of spread = $10/lot; the bug computed $0.001/lot). Found while
    # sourcing AUDUSD's real spec (8cd2642), confirmed and fixed here.
    # Every prior hypothesis's cost +50% stress test ran against this
    # near-zero spread/slip term -- see docs/COST_MODEL_V3_SPREAD_FIX.md
    # for the re-verification this requires.
    spread_cost = meta["spread_pips"]  * meta["pip_value"] * size
    slip_cost   = slippage_pips        * meta["pip_value"] * size
    commission  = commission_cost(symbol, size)
    swap        = 0.0
    if entry_dt is not None and exit_dt is not None:
        swap = swap_cost(symbol, size, direction, entry_dt, exit_dt)
    return spread_cost + slip_cost + commission + swap