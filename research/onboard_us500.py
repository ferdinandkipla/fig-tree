"""
research/onboard_us500.py

Real onboarding event for US500 as a cross-asset conditioning variable,
per research/CONDITIONAL_SEARCH_CHARTER.md Sec 4 item 4 and the
S1-grade standard used for the original 5 instruments (sourced,
ingested, hash-pinned, caveated). Follow-up to the availability check
(research/mt5_us500_data_check.py, run 2026-08-20 -- confirmed history
from 2018-12-31, no truncation needed vs. the 2019 TRAIN window start).

Run this LOCALLY with the MT5 terminal open and logged into the demo
account, same as every other real-data script in this repo.

What it does:
  1. Fetches US500 H4 and H1 bars via the EXISTING data.loader.fetch()
     path (data/mt5_connector.py + data/loader.py) -- same cache
     mechanism, same file-naming convention
     (data/storage/US500_{timeframe_code}.csv) as USDJPY/XAUUSD/GBPJPY/
     EURUSD/AUDUSD already use. Deliberately NOT a separate one-off
     fetch path, so US500 behaves identically to every other instrument
     everywhere else in the codebase (main.py, tests, etc.) once this
     runs.
  2. SHA-256 hashes both output files, using the same _sha256_file
     logic research/experiment.py already uses for the other 5
     instruments' provenance.
  3. Writes research/S1_US500_ONBOARDING_SNAPSHOT.md -- a caveat doc
     modeled directly on research/S1_SWAP_RATES_SNAPSHOT.md's format,
     including the account tier, pull timestamp, row counts, hashes,
     and the caveats that matter for this specific instrument (index
     CFD vs. cash index; broker-quoted, not exchange-quoted; contract
     rollover behavior if any -- unlike DXY_U6, confirm US500 does NOT
     roll/expire before trusting a multi-year series from a single
     symbol).

Does NOT modify core/config.py's INSTRUMENTS list, core/instruments.py's
INSTRUMENT_META, or any existing hypothesis's registration -- wiring
US500 into an actual mechanism memo is a separate, later step. This
script's job is sourcing the data and producing the provenance record
that a future memo would cite.

Usage:
    python research/onboard_us500.py
"""

import sys
import hashlib
from datetime import datetime, timezone
from pathlib import Path

try:
    import MetaTrader5 as mt5
except ImportError:
    print("MetaTrader5 package not installed.")
    sys.exit(1)

from data.mt5_connector import connect, disconnect, get_symbol
from data.loader import fetch, cache_path

SYMBOL = "US500"
TIMEFRAMES = [
    ("H4", mt5.TIMEFRAME_H4 if hasattr(mt5, "TIMEFRAME_H4") else 16388),
    ("H1", mt5.TIMEFRAME_H1 if hasattr(mt5, "TIMEFRAME_H1") else 16385),
]

CAVEAT_DOC = Path("research/S1_US500_ONBOARDING_SNAPSHOT.md")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def check_rollover_behavior(info) -> str:
    """
    US500 vs DXY_U6's dated-futures problem: confirm this symbol does
    NOT carry an expiry the way DXY_U6 does, since that would silently
    invalidate a multi-year single-symbol series the same way it did
    for DXY. Report what MT5 exposes; a name with no month/year code
    and no expiration_time is the expected "safe" pattern here, but
    state it rather than assume it.
    """
    exp = getattr(info, "expiration_time", 0)
    lines = [f"description: {info.description}"]
    if exp and exp != 0:
        exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
        lines.append(f"expiration_time: {exp_dt} -- ⚠ THIS SYMBOL EXPIRES. "
                      f"Same problem as DXY_U6 -- do not trust a single-symbol "
                      f"multi-year series without checking roll/stitch needs.")
    else:
        lines.append("expiration_time: none reported (0) -- consistent with "
                      "a non-expiring/continuous CFD, not a dated contract "
                      "like DXY_U6. Still worth a periodic re-check, not a "
                      "permanent guarantee.")
    return "\n".join(lines)


def main():
    if not connect():
        sys.exit(1)

    if not get_symbol(SYMBOL):
        print(f"{SYMBOL} not available. Aborting onboarding.")
        disconnect()
        sys.exit(1)

    info = mt5.symbol_info(SYMBOL)
    rollover_report = check_rollover_behavior(info)
    print(rollover_report)
    print()

    acc = mt5.account_info()
    results = {}

    for tf_label, tf_code in TIMEFRAMES:
        print(f"--- Fetching {SYMBOL} {tf_label} ---")
        df = fetch(SYMBOL, tf_code, use_cache=False)  # force fresh pull
        if df.empty:
            print(f"  EMPTY result for {tf_label}. Error: {mt5.last_error()}")
            continue
        path = cache_path(SYMBOL, tf_code)
        file_hash = sha256_file(path)
        results[tf_label] = {
            "path": path,
            "n_rows": len(df),
            "start": df.index.min(),
            "end": df.index.max(),
            "hash": file_hash,
            "tf_code": tf_code,
        }
        print(f"  {len(df)} rows, {df.index.min()} -> {df.index.max()}")
        print(f"  sha256: {file_hash}")
        print()

    disconnect()

    if not results:
        print("No data fetched for any timeframe. Not writing caveat doc.")
        sys.exit(1)

    write_caveat_doc(acc, info, rollover_report, results)
    print(f"\nCaveat doc written: {CAVEAT_DOC}")
    print("Review it, then commit + push both the doc and the new")
    print("data/storage/US500_*.csv files together, same as any other")
    print("provenance-bearing data commit in this repo.")


def write_caveat_doc(acc, info, rollover_report, results):
    now = datetime.now(timezone.utc).isoformat()
    lines = [
        "# S1 US500 Onboarding Snapshot",
        "",
        f"**Pulled:** {now}, via live MT5 terminal "
        f"(account {acc.login}, server `{acc.server}`, "
        f"trade_mode={'DEMO' if acc.trade_mode == 0 else 'LIVE/OTHER'}).",
        "",
        "Onboarding event for US500 as the sole risk-on/off cross-asset "
        "conditioning proxy, per "
        "`research/CONDITIONAL_SEARCH_CHARTER.md` §4 item 4. DXY was "
        "surveyed the same session and disqualified for this phase "
        "(`research/CONDITIONAL_SEARCH_CHARTER.md` §4a) — only a dated "
        "futures contract exists, no continuous instrument, no "
        "roll-handling in this codebase.",
        "",
        "## Symbol details",
        "",
        f"```\n{rollover_report}\n```",
        "",
        "## Files produced",
        "",
        "| Timeframe | Path | Rows | Start | End | SHA-256 |",
        "|---|---|---:|---|---|---|",
    ]
    for tf_label, r in results.items():
        lines.append(
            f"| {tf_label} | `{r['path']}` | {r['n_rows']} | "
            f"{r['start']} | {r['end']} | `{r['hash'][:16]}...` |"
        )
    lines += [
        "",
        "Full hashes (do not truncate when actually verifying):",
        "",
        "```",
    ]
    for tf_label, r in results.items():
        lines.append(f"{tf_label}: {r['hash']}")
    lines += [
        "```",
        "",
        "## Critical caveats (read before modeling this)",
        "",
        "1. **US500 is a broker-quoted CFD on the S&P 500 index, not the "
        "exchange-traded index itself or a futures contract.** Broker "
        "CFD pricing can differ from the underlying exchange in small "
        "ways (spread, occasional feed gaps, weekend/holiday session "
        "handling) — same category of caveat already accepted for "
        "XAUUSD/GBPJPY/etc. as broker-quoted instruments, not a new "
        "risk class for this dataset.",
        "2. **Pulled from a DEMO account** "
        f"(`{acc.server}`). Same caveat category as "
        "`research/S1_SWAP_RATES_SNAPSHOT.md` — verify against a live "
        "account if this ever needs to move beyond a research/backtest "
        "context.",
        "3. **This is price/OHLC data, not a cost model.** No spread, "
        "slippage, or swap terms have been sourced or modeled for "
        "US500 here — if any hypothesis ever executes simulated trades "
        "on US500 rather than just using it as a conditioning variable "
        "for the existing 5 instruments, `core/instruments.py` and "
        "`execution/costs.py` need their own US500 entries first, with "
        "the same hard-block-on-placeholder discipline used for "
        "AUDUSD.",
        "4. **Rollover/expiry check ran and is reported above** — "
        "confirm it says 'no expiration reported' before trusting a "
        "multi-year single-symbol series. If a future re-pull ever "
        "shows an expiration_time appearing, stop and treat it exactly "
        "like the DXY_U6 finding: check for a continuous alternative "
        "before doing anything else.",
        "5. **This snapshot only covers price data.** It does not "
        "itself register any hypothesis, cell structure, or FDR "
        "accounting — per the charter, any mechanism memo using US500 "
        "still needs its own registration, kill criteria, and "
        "cell-level FDR extension (§5 of the charter) before "
        "adjudication.",
        "",
    ]
    CAVEAT_DOC.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
