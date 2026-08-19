"""
research/mt5_availability_check.py

Read-only reconnaissance script. Run this LOCALLY, where MetaTrader5
desktop terminal is installed and logged into the demo (or live) account
-- it will NOT run in this repo's CI/sandbox environments, which have no
MT5 terminal to connect to.

Does three things, in order:
  1. Confirms the MT5 Python API can connect to your running terminal.
  2. Pulls swap_long/swap_short for the 5 existing S1 instruments and
     prints them next to the currently pinned snapshot
     (research/S1_SWAP_RATES_SNAPSHOT.md / execution/costs.py
     SWAP_RATES), so you can see at a glance whether anything drifted
     since 2026-07-24, and confirms which account tier (demo/live) the
     numbers came from.
  3. Probes a list of candidate symbol names for US500 and DXY, since
     naming varies by broker and DXY is frequently not a native MT5
     symbol at all (per research/CONDITIONAL_SEARCH_CHARTER.md Sec 4
     item 4). Reports what actually exists in your Market Watch.

This script does NOT write any files, does NOT modify SWAP_RATES or any
committed snapshot, and does NOT ingest historical bars. It is a
before-you-commit-to-anything check. Once you've seen the output, the
next steps (re-sourcing the swap snapshot doc for real, or a full
US500/DXY onboarding event) are separate, deliberate scripts -- not this
one.

Usage:
    python research/mt5_availability_check.py
"""

import sys
from datetime import datetime, timezone

try:
    import MetaTrader5 as mt5
except ImportError:
    print("MetaTrader5 package not installed. Run: pip install MetaTrader5")
    print("(Windows only -- this package wraps the desktop terminal's IPC")
    print(" interface and has no meaningful use outside Windows + a")
    print(" running terminal.)")
    sys.exit(1)


# Currently pinned snapshot -- research/S1_SWAP_RATES_SNAPSHOT.md,
# execution/costs.py SWAP_RATES, pulled 2026-07-24, ICMarketsSC-Demo.
CURRENT_SNAPSHOT = {
    "USDJPY": {"long": 8.752, "short": -17.618},
    "XAUUSD": {"long": -53.763, "short": 36.931},
    "GBPJPY": {"long": 12.143, "short": -23.758},
    "EURUSD": {"long": -8.166, "short": 1.454},
    "AUDUSD": {"long": -2.231, "short": -4.739},
}

EXISTING_INSTRUMENTS = ["USDJPY", "XAUUSD", "GBPJPY", "EURUSD", "AUDUSD"]

# Candidate symbol names to probe -- broker naming for these varies a lot,
# and DXY in particular is frequently unavailable as a native MT5 symbol.
US500_CANDIDATES = ["US500", "SPX500", "US500Cash", "US500.cash", "SP500", "S&P500"]
DXY_CANDIDATES = ["DXY", "USDX", "USDIndex", "DXYcash", "DX", "USDollarIndex"]


def connect():
    if not mt5.initialize():
        print(f"initialize() FAILED, error code: {mt5.last_error()}")
        print("Check that the MT5 terminal is running and logged in.")
        sys.exit(1)
    info = mt5.account_info()
    if info is None:
        print(f"account_info() FAILED, error code: {mt5.last_error()}")
        mt5.shutdown()
        sys.exit(1)
    return info


def print_account_context(info):
    print("=" * 70)
    print("MT5 CONNECTION")
    print("=" * 70)
    print(f"Login:       {info.login}")
    print(f"Server:      {info.server}")
    print(f"Company:     {info.company}")
    print(f"Trade mode:  {'DEMO' if info.trade_mode == 0 else 'LIVE/CONTEST (check carefully)'}")
    print(f"Currency:    {info.currency}")
    print(f"Checked at:  {datetime.now(timezone.utc).isoformat()}")
    print()
    print("NOTE: 'DEMO' above does not by itself resolve the swap-rate")
    print("verification gate (research/registry/FINDING-xauusd-swap-")
    print("sensitivity-h001.md Sec 4) -- that gate wants a source you can")
    print("independently attest to, demo or live. Record which one this")
    print("was when you write up the re-sourcing.")
    print()


def check_swap_rates():
    print("=" * 70)
    print("SWAP RATE CROSS-CHECK vs. currently pinned snapshot")
    print("=" * 70)
    print(f"{'Symbol':<8} {'pinned long':>12} {'live long':>12} {'pinned short':>13} {'live short':>12} {'drift?':>8}")
    any_missing = False
    for symbol in EXISTING_INSTRUMENTS:
        info = mt5.symbol_info(symbol)
        if info is None:
            print(f"{symbol:<8} NOT FOUND in Market Watch -- add it and rerun.")
            any_missing = True
            continue
        pinned = CURRENT_SNAPSHOT[symbol]
        live_long, live_short = info.swap_long, info.swap_short
        drift = (abs(live_long - pinned["long"]) > 0.01
                 or abs(live_short - pinned["short"]) > 0.01)
        print(f"{symbol:<8} {pinned['long']:>12.3f} {live_long:>12.3f} "
              f"{pinned['short']:>13.3f} {live_short:>12.3f} "
              f"{'YES' if drift else 'no':>8}")
    print()
    if any_missing:
        print("Some symbols weren't visible -- right-click Market Watch,")
        print("'Show All' or add them individually, then rerun.")
    print("swap_mode for XAUUSD (points/currency/interest/margin-pct):",
          mt5.symbol_info("XAUUSD").swap_mode if mt5.symbol_info("XAUUSD") else "N/A")
    print()


def probe_candidates(label, candidates):
    print(f"--- {label} candidates ---")
    found = []
    for name in candidates:
        info = mt5.symbol_info(name)
        if info is not None:
            found.append(name)
            print(f"  FOUND: {name}  (bid={info.bid}, description='{info.description}')")
    if not found:
        print(f"  None of {candidates} found in Market Watch or symbol list.")
        print(f"  Try mt5.symbols_get('*') and grep for likely names manually --")
        print(f"  broker-specific naming may not match any candidate above.")
    print()
    return found


def probe_full_symbol_list_hint():
    all_symbols = mt5.symbols_get()
    print(f"Total symbols visible to this account: {len(all_symbols)}")
    print("If US500/DXY weren't found above, uncomment the block below to")
    print("dump every symbol name and grep it yourself for likely matches")
    print("(index, cash, spot, or DXY-adjacent names vary a lot by broker).")
    print()
    # for s in all_symbols:
    #     print(s.name)


def main():
    info = connect()
    print_account_context(info)
    check_swap_rates()
    us500_found = probe_candidates("US500", US500_CANDIDATES)
    dxy_found = probe_candidates("DXY", DXY_CANDIDATES)
    probe_full_symbol_list_hint()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"US500 available under: {us500_found or 'NONE FOUND'}")
    print(f"DXY   available under: {dxy_found or 'NONE FOUND (expected -- charter already flags DXY as likely unavailable)'}")
    print()
    print("Next steps depend on what printed above -- do not act on this")
    print("script's output alone. Bring it back for review before writing")
    print("either the swap-rate re-sourcing doc or a US500/DXY onboarding")
    print("script.")

    mt5.shutdown()


if __name__ == "__main__":
    main()
