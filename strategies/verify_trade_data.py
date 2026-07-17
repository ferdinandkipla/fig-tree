# research/verify_trade_data.py
# Phase 2A — Step 1: confirm we have what we need BEFORE analysis
# Run from project root: python research/verify_trade_data.py

import pandas as pd
from pathlib import Path

# --- locate the trade files Phase 1 produced -------------------
SEARCH_DIRS = [Path("."), Path("data/storage"), Path("research"),
               Path("output"), Path("results")]

found = []
for d in SEARCH_DIRS:
    if d.exists():
        found.extend(sorted(d.glob("trades_*.csv")))

print("=" * 62)
print("  PHASE 2A · STEP 1 — TRADE DATA VERIFICATION")
print("=" * 62)

if not found:
    print("\n[!] No trades_*.csv files found in the usual places.")
    print("    Searched:", [str(x) for x in SEARCH_DIRS])
    print("    → Tell me where Phase 1 wrote its trade logs,")
    print("      or whether we need to re-run the backtest to")
    print("      regenerate them.")
else:
    print(f"\n[OK] Found {len(found)} trade file(s):")
    for f in found:
        print(f"     • {f}")

    # what Path A REQUIRES to compute pullback depth
    REQUIRED = ["entry_price", "instrument", "pnl"]
    DEPTH_NEEDS = ["ema20", "ema", "atr", "atr_entry",
                   "ema20_at_entry", "atr_at_entry", "entry_time"]

    for f in found:
        print("\n" + "-" * 62)
        print(f"  FILE: {f.name}")
        print("-" * 62)
        df = pd.read_csv(f)
        print(f"  rows (trades) : {len(df)}")
        print(f"  columns       : {list(df.columns)}")

        have_req   = [c for c in REQUIRED    if c in df.columns]
        miss_req   = [c for c in REQUIRED    if c not in df.columns]
        have_depth = [c for c in DEPTH_NEEDS if c in df.columns]

        print(f"\n  required present : {have_req}")
        if miss_req:
            print(f"  required MISSING : {miss_req}  ◄ problem")
        print(f"  depth-related    : {have_depth if have_depth else 'NONE ◄ must patch simulator'}")

print("\n" + "=" * 62)
print("  Paste this entire output back. We decide next step")
print("  based on what columns actually exist. Nothing assumed.")
print("=" * 62)