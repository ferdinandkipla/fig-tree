"""
research/mt5_dxy_symbol_search.py

Broad symbol-name search, replacing guesswork after
mt5_availability_check.py's candidate-name probe missed DXY_U6 -- a
dated futures-style CFD (September 2026 contract) that doesn't match
any spot/cash-style name pattern. Futures naming varies by broker
(often <ROOT>_<MonthCode><Year>, e.g. U6 = September 2026) and this
script searches for the ROOT substring instead of guessing exact names.

Also checks: does this broker offer a continuous/cash version alongside
the dated contract? That matters a lot -- a single dated futures
contract has a limited life and does NOT give 2019-2025 history on its
own. If only dated contracts exist, DXY onboarding requires either
contract-stitching (rolls, gaps -- real work, needs its own decision)
or dropping DXY in favor of US500 alone as the risk-on/off proxy.

Read-only. Usage:
    python research/mt5_dxy_symbol_search.py
"""

import sys

try:
    import MetaTrader5 as mt5
except ImportError:
    print("MetaTrader5 package not installed.")
    sys.exit(1)

SEARCH_TERMS = ["DXY", "USDX", "DOLLAR"]


def main():
    if not mt5.initialize():
        print(f"initialize() FAILED: {mt5.last_error()}")
        sys.exit(1)

    all_symbols = mt5.symbols_get()
    print(f"Total symbols visible: {len(all_symbols)}\n")

    for term in SEARCH_TERMS:
        matches = [s for s in all_symbols if term.upper() in s.name.upper()
                   or term.upper() in (s.description or "").upper()]
        print(f"--- matches for '{term}' ({len(matches)} found) ---")
        for s in matches:
            print(f"  {s.name:<20} desc='{s.description}'")
        print()

    print("For each dated futures contract found above (e.g. name ending")
    print("in a month/year code like _U6, _Z5, _H6), check its actual")
    print("history depth the same way as US500 -- a single dated contract")
    print("will NOT span back to 2019. Look specifically for a name")
    print("WITHOUT a month/year suffix, which is more likely to be a")
    print("continuous/cash equivalent if the broker offers one.")

    mt5.shutdown()


if __name__ == "__main__":
    main()
