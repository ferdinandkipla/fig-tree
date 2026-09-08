"""
research/sample_fx_spreads.py

Live-sample spread for USDJPY, GBPJPY, EURUSD -- the three FX majors
whose spread_pips (1.5/2.5/1.0 in core/instruments.py) were never
independently sourced from this account, same category as AUDUSD's
placeholder turned out to be (docs/COST_MODEL_V3_SPREAD_FIX.md /
8cd2642's "OPEN QUESTION" note).

DIFFERENCE FROM sample_audusd_spread.py: that script sampled a single
~2-minute window and explicitly flagged the limitation in its own
output ("one sampling window isn't necessarily representative of all
trading sessions"). This script is designed to be run MULTIPLE TIMES
across different times of day/session -- each run APPENDS timestamped,
session-tagged samples to research/fx_spread_samples.csv (persistent
across runs, not overwritten) rather than reporting a single-window
summary. Real cross-session coverage requires running this several
times over a few days at different hours, not one longer sitting --
market conditions on a single day aren't representative either.

Session tagging reuses core.instruments.SESSION_HOURS (the same
tokyo/london/new_york windows used throughout the simulator), so
per-session spread behavior can be directly compared against anything
session-conditioned elsewhere in this codebase.

Run this LOCALLY with MT5 open and logged in.

Usage:
    python research/sample_fx_spreads.py            # sample + append
    python research/sample_fx_spreads.py --summary   # aggregate what's
                                                       # accumulated so far,
                                                       # no new sampling
"""

import sys
import csv
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.instruments import SESSION_HOURS

SYMBOLS = ["USDJPY", "GBPJPY", "EURUSD"]
PIP_SIZES = {"USDJPY": 0.01, "GBPJPY": 0.01, "EURUSD": 0.0001}  # per core/instruments.py
N_SAMPLES = 24
INTERVAL_SECONDS = 5
LOG_PATH = Path("research/fx_spread_samples.csv")


def current_session(dt_utc: datetime) -> str:
    """Which session(s) this UTC hour falls in, per SESSION_HOURS.
    A bar can be in multiple overlapping sessions (e.g. london+new_york);
    report all that apply, joined, so the summary can slice either way."""
    hour = dt_utc.hour
    active = [name for name, (start, end) in SESSION_HOURS.items() if start <= hour < end]
    return "+".join(active) if active else "none"


def sample_and_append():
    try:
        import MetaTrader5 as mt5
    except ImportError:
        print("MetaTrader5 package not installed.")
        sys.exit(1)

    from data.mt5_connector import connect, disconnect, get_symbol

    if not connect():
        sys.exit(1)
    for sym in SYMBOLS:
        if not get_symbol(sym):
            print(f"{sym} not available. Aborting.")
            disconnect()
            sys.exit(1)

    print(f"Sampling {SYMBOLS}: {N_SAMPLES} samples, {INTERVAL_SECONDS}s apart "
          f"(~{N_SAMPLES * INTERVAL_SECONDS / 60:.1f} min). Appending to {LOG_PATH}.\n")

    is_new_file = not LOG_PATH.exists()
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", newline="") as f:
        writer = csv.writer(f)
        if is_new_file:
            writer.writerow(["timestamp_utc", "symbol", "session", "bid", "ask", "spread_pips"])

        for i in range(N_SAMPLES):
            now = datetime.now(timezone.utc)
            session = current_session(now)
            for sym in SYMBOLS:
                tick = mt5.symbol_info_tick(sym)
                if tick is None:
                    print(f"  sample {i+1}, {sym}: no tick data, skipping")
                    continue
                spread_price = tick.ask - tick.bid
                spread_pips = spread_price / PIP_SIZES[sym]
                writer.writerow([now.isoformat(), sym, session, tick.bid, tick.ask,
                                  round(spread_pips, 4)])
                print(f"  sample {i+1:2d} [{session:20s}] {sym}: "
                      f"bid={tick.bid} ask={tick.ask} spread={spread_pips:.3f} pips")
            f.flush()
            time.sleep(INTERVAL_SECONDS)

    disconnect()
    print(f"\nAppended to {LOG_PATH}. Run with --summary to see the "
          f"accumulated aggregate, or run this script again at a "
          f"different time of day/session for more coverage before "
          f"treating any number as representative.")


def print_summary():
    if not LOG_PATH.exists():
        print(f"No samples yet -- {LOG_PATH} doesn't exist. Run without "
              f"--summary first.")
        sys.exit(1)

    rows = []
    with open(LOG_PATH) as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    if not rows:
        print("Log file exists but is empty.")
        sys.exit(1)

    sessions_seen = sorted(set(r["session"] for r in rows))
    print(f"Total samples: {len(rows)}")
    print(f"Sessions covered so far: {sessions_seen}")
    print(f"Timestamps span: {rows[0]['timestamp_utc']} to {rows[-1]['timestamp_utc']}\n")

    for sym in SYMBOLS:
        sym_rows = [r for r in rows if r["symbol"] == sym]
        if not sym_rows:
            continue
        spreads = [float(r["spread_pips"]) for r in sym_rows]
        print(f"--- {sym} ({len(sym_rows)} samples) ---")
        print(f"  overall: mean={mean(spreads):.3f}  min={min(spreads):.3f}  max={max(spreads):.3f}")
        for session in sessions_seen:
            sess_spreads = [float(r["spread_pips"]) for r in sym_rows if r["session"] == session]
            if sess_spreads:
                print(f"  {session:20s}: n={len(sess_spreads):3d}  "
                      f"mean={mean(sess_spreads):.3f}  min={min(sess_spreads):.3f}  "
                      f"max={max(sess_spreads):.3f}")
        current_placeholder = {"USDJPY": 1.5, "GBPJPY": 2.5, "EURUSD": 1.0}[sym]
        print(f"  current core/instruments.py value: {current_placeholder}")
        print()

    print("Coverage check before treating this as representative: does")
    print("`sessions_seen` above include tokyo, london, AND new_york")
    print("(or their overlaps)? If not, run this script again during the")
    print("missing session(s) before editing core/instruments.py.")
    print()
    print("Bring this output back for review before editing")
    print("core/instruments.py -- do not act on it alone.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", action="store_true",
                         help="Aggregate accumulated samples, no new sampling")
    args = parser.parse_args()
    if args.summary:
        print_summary()
    else:
        sample_and_append()
