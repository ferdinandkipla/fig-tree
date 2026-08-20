"""
research/sample_audusd_spread.py

Resolves the one remaining unverified number blocking AUDUSD's
PLACEHOLDER_INSTRUMENTS status (execution/costs.py): spread_pips is
currently a 1.2-pip guess in core/instruments.py, never independently
sourced. Per this session's finding (research/S1_SWAP_RATES_SNAPSHOT_V2.md
"Decision" section), IC Markets publishes no fixed spread number for
any instrument -- their own spec sheet states spreads as "Variable."
So there's no published table to look up; the only honest source is a
live-sampled average from the actual account, same standard now applied
to swap rates.

Run this LOCALLY with MT5 open and logged in. Samples the live spread
at a fixed interval for a few minutes (spreads move constantly, so a
single instantaneous reading isn't representative -- same reasoning
that made a single swap-rate pull the "best available" rather than
"exact" standard).

Does NOT modify core/instruments.py or execution/costs.py itself --
prints the sampled average/min/max for review, and the actual edit
(replacing the 1.2-pip placeholder and deciding whether to lift the
AUDUSD hard block in PLACEHOLDER_INSTRUMENTS) happens as a separate,
deliberate step after reviewing the output.

Usage:
    python research/sample_audusd_spread.py
    (takes ~2 minutes to run -- 24 samples, 5 seconds apart, by default)
"""

import sys
import time
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import MetaTrader5 as mt5
except ImportError:
    print("MetaTrader5 package not installed.")
    sys.exit(1)

from data.mt5_connector import connect, disconnect, get_symbol

SYMBOL = "AUDUSD"
N_SAMPLES = 24
INTERVAL_SECONDS = 5


def main():
    if not connect():
        sys.exit(1)
    if not get_symbol(SYMBOL):
        print(f"{SYMBOL} not available.")
        disconnect()
        sys.exit(1)

    info = mt5.symbol_info(SYMBOL)
    point = info.point  # e.g. 0.00001 for a 5-digit AUDUSD quote
    pip_size = 0.0001    # AUDUSD pip definition, per core/instruments.py

    print(f"Sampling {SYMBOL} spread: {N_SAMPLES} samples, "
          f"{INTERVAL_SECONDS}s apart (~{N_SAMPLES * INTERVAL_SECONDS / 60:.1f} min total)")
    print(f"point={point}, treating pip_size={pip_size} per core/instruments.py convention\n")

    spreads_pips = []
    for i in range(N_SAMPLES):
        tick = mt5.symbol_info_tick(SYMBOL)
        if tick is None:
            print(f"  sample {i+1}: no tick data, skipping")
            time.sleep(INTERVAL_SECONDS)
            continue
        spread_price = tick.ask - tick.bid
        spread_pips = spread_price / pip_size
        spreads_pips.append(spread_pips)
        print(f"  sample {i+1:2d}: bid={tick.bid:.5f} ask={tick.ask:.5f} "
              f"spread={spread_pips:.2f} pips")
        time.sleep(INTERVAL_SECONDS)

    disconnect()

    if not spreads_pips:
        print("\nNo samples collected. Try again during active market hours.")
        sys.exit(1)

    print(f"\n--- Summary ({len(spreads_pips)} samples) ---")
    print(f"mean:   {mean(spreads_pips):.3f} pips")
    print(f"min:    {min(spreads_pips):.3f} pips")
    print(f"max:    {max(spreads_pips):.3f} pips")
    print(f"\nCurrent placeholder in core/instruments.py: 1.2 pips")
    print(f"\nBring this output back for review before editing")
    print(f"core/instruments.py or execution/costs.py's PLACEHOLDER_INSTRUMENTS --")
    print(f"one sampling window isn't necessarily representative of all")
    print(f"trading sessions (spreads widen around news events, session")
    print(f"opens/closes, etc.) -- worth noting what time of day/session")
    print(f"this was run during when reviewing the number.")


if __name__ == "__main__":
    main()
