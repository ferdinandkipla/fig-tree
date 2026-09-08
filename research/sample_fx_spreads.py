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

PRE-REGISTERED AGGREGATION RULE (decided here, before --summary is
ever run against real data, per review -- otherwise the rule gets
picked after seeing which one flatters the kills or the survivors):
--summary's naive "overall mean" is explicitly labeled DO NOT USE --
it weights sessions by how many times you happened to run the sampler,
not by anything real. The RECOMMENDED value instead weights each
session's sampled mean by the ACTUAL historical distribution of
simulator entry hours, computed from the pooled 100-seed
research/null_runs_h004/ sweep (see historical_entry_distribution()).
This is a data check, not an assumption: execution/simulator.py's
_in_valid_session() is confirmed (by direct inspection, not inferred)
to be hardcoded `return True` -- session gating is disabled in
research mode -- so entries fire in every hour, and the correct weight
is the real entry-hour distribution, not a "London/NY only" assumption
that doesn't hold here.

ROLLOVER WINDOW (21:00-22:00 UTC): tagged and sampled separately,
EXCLUDED from the weighted aggregate. IC Markets spreads are reported
to widen sharply in this window; one sample there would otherwise
silently dominate whichever session tag absorbed it (new_york, per
plain SESSION_HOURS). Sampling it anyway and reporting it separately
matters because execution/rollover.py's count_rollover_nights implies
positions ARE held through this window -- the finding doc should
record what spread does then, even though the current cost model
doesn't vary spread by time of day.

DEMO-VS-LIVE CAVEAT: this account is ICMarketsSC-Demo, same as the
swap-rate sourcing (research/S1_SWAP_RATES_SNAPSHOT_V2.md). Demo
spreads on raw accounts are generally close to live but not guaranteed
identical. Recorded under the same permanent-baseline decision as the
swap rates -- one disclosure, not a new gate to clear before this data
can be used.

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

from core.instruments import SESSION_HOURS, INSTRUMENT_META

SYMBOLS = ["USDJPY", "GBPJPY", "EURUSD"]
# FIX (structural note from review): read pip_size from the single
# source of truth (core.instruments.INSTRUMENT_META) instead of a
# hardcoded local copy -- a hardcoded copy is the same class of
# divergence risk as the double-pip_size bug this sampling exists to
# help fix. If INSTRUMENT_META ever changes a pip_size, this sampler
# picks it up automatically instead of silently disagreeing.
PIP_SIZES = {sym: INSTRUMENT_META[sym]["pip_size"] for sym in SYMBOLS}
N_SAMPLES = 24
INTERVAL_SECONDS = 5
LOG_PATH = Path("research/fx_spread_samples.csv")
ROLLOVER_HOUR_UTC = 21  # 21:00-22:00 UTC, per execution/rollover.py's
                         # ROLLOVER_HOUR_UTC convention -- IC Markets
                         # spreads are reported to widen 5-50x in this
                         # window. Tagged and reported SEPARATELY from
                         # "new_york" (which it would otherwise fall
                         # under, since new_york=13-22 includes hour 21)
                         # so one accidental sample here doesn't
                         # silently contaminate the new_york mean.


def current_session(dt_utc: datetime) -> str:
    """Which session(s) this UTC hour falls in, per SESSION_HOURS.
    A bar can be in multiple overlapping sessions (e.g. london+new_york);
    report all that apply, joined, so the summary can slice either way.

    ROLLOVER OVERRIDE: hour 21 (21:00-22:00 UTC) is tagged "rollover"
    instead of "new_york" (which it would otherwise be, since
    new_york=(13,22) includes hour 21) -- spreads widen sharply around
    the daily rollover, and this project's own count_rollover_nights
    (execution/rollover.py) treats 22:00 UTC as the boundary, implying
    positions ARE held through this window. The finding doc should
    record what spread does here even though the cost model doesn't
    currently use a session-conditional spread -- see the sampler's
    module docstring."""
    if dt_utc.hour == ROLLOVER_HOUR_UTC:
        return "rollover"
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


def historical_entry_distribution(symbol: str) -> dict:
    """
    PRE-REGISTERED AGGREGATION RULE (decided before --summary is ever
    run, per review): the naive "overall mean" of accumulated samples
    is biased by how many times you happened to run the sampler in
    each session -- six 24-sample runs give six tight clusters, not a
    representative distribution. The correct weight for each session
    tag is how often the SIMULATOR ACTUALLY ENTERS TRADES in that
    session -- NOT an assumption ("entries are London/NY-gated") but
    a direct data check: execution/simulator.py's _in_valid_session()
    is HARDCODED to `return True` ("disabled in research mode --
    reintroduce in Phase 3"), confirmed by inspection before writing
    this function. Entries therefore fire in ALL hours for ALL three
    instruments -- there is no session gating to weight by.

    Given that, the weight is the actual historical clock-hour
    distribution of entries, computed from the pooled 100-seed
    research/null_runs_h004/{symbol}_H1_seed*_trades.csv sweep (large
    N, already-generated, same data H-008/H-009 used) -- using the
    IDENTICAL current_session() tagging this sampler applies to its
    own live samples, so weights and samples use the same categories.
    """
    import pandas as pd
    import glob
    frames = [pd.read_csv(p, parse_dates=["entry_dt"])
              for p in glob.glob(f"research/null_runs_h004/{symbol}_H1_seed*_trades.csv")]
    if not frames:
        return {}
    pooled = pd.concat(frames, ignore_index=True)
    tags = pooled["entry_dt"].dt.hour.apply(
        lambda h: current_session(datetime(2000, 1, 1, h, tzinfo=timezone.utc))
    )
    counts = tags.value_counts()
    total = len(pooled)
    return {tag: count / total for tag, count in counts.items()}


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
    non_rollover_sessions_seen = sorted(s for s in sessions_seen if s != "rollover")
    print(f"Total samples: {len(rows)}")
    print(f"Sessions covered so far: {sessions_seen}")
    print(f"Timestamps span: {rows[0]['timestamp_utc']} to {rows[-1]['timestamp_utc']}\n")

    for sym in SYMBOLS:
        sym_rows = [r for r in rows if r["symbol"] == sym]
        if not sym_rows:
            continue
        all_spreads = [float(r["spread_pips"]) for r in sym_rows]
        print(f"--- {sym} ({len(sym_rows)} samples) ---")
        print(f"  naive overall mean (DO NOT USE -- biased by run count): "
              f"{mean(all_spreads):.3f}  min={min(all_spreads):.3f}  max={max(all_spreads):.3f}")

        per_session_mean = {}
        for session in sessions_seen:
            sess_spreads = [float(r["spread_pips"]) for r in sym_rows if r["session"] == session]
            if sess_spreads:
                per_session_mean[session] = mean(sess_spreads)
                tag = "  [EXCLUDED from weighted aggregate -- reported separately]" if session == "rollover" else ""
                print(f"  {session:20s}: n={len(sess_spreads):3d}  "
                      f"mean={mean(sess_spreads):.3f}  min={min(sess_spreads):.3f}  "
                      f"max={max(sess_spreads):.3f}{tag}")

        weights = historical_entry_distribution(sym)
        # Rollover excluded from the weighted aggregate per the
        # pre-registered rule -- renormalize remaining weights to sum
        # to 1 across non-rollover categories actually sampled so far.
        usable = {tag: w for tag, w in weights.items()
                  if tag != "rollover" and tag in per_session_mean}
        weight_sum = sum(usable.values())
        missing_coverage = [tag for tag in weights if tag != "rollover" and tag not in per_session_mean and weights[tag] > 0.01]

        if weight_sum > 0 and not missing_coverage:
            weighted_mean = sum(per_session_mean[tag] * (w / weight_sum) for tag, w in usable.items())
            print(f"  RECOMMENDED spread_pips (historical-entry-weighted, "
                  f"rollover excluded): {weighted_mean:.3f}")
        else:
            print(f"  RECOMMENDED spread_pips: NOT COMPUTABLE YET -- missing "
                  f"session coverage for: {missing_coverage or 'unknown'} "
                  f"(historical weight of missing categories is non-trivial; "
                  f"run the sampler during those hours before trusting a "
                  f"weighted mean).")

        current_placeholder = {"USDJPY": 1.5, "GBPJPY": 2.5, "EURUSD": 1.0}[sym]
        print(f"  current core/instruments.py placeholder value: {current_placeholder}")
        print()

    print("DEMO-VS-LIVE CAVEAT (carries over unchanged from the swap-rate")
    print("baseline decision, research/S1_SWAP_RATES_SNAPSHOT_V2.md): this")
    print("is the same ICMarketsSC-Demo account. Demo spreads on raw")
    print("accounts are generally close to live but not guaranteed")
    print("identical -- one disclosure under the same permanent-baseline")
    print("decision, not a new gate to clear.")
    print()
    print("Coverage check before treating a RECOMMENDED value as final: does")
    print("`sessions_seen` above include tokyo, london, new_york (and their")
    print("overlaps)? A 'NOT COMPUTABLE YET' line above means missing")
    print("coverage with non-trivial historical weight -- run the sampler")
    print("during those hours specifically.")
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
