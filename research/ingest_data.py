# research/ingest_data.py
#
# S1: run this LOCALLY, on the machine with a live MT5 terminal open
# and logged in. This cannot be run in a sandboxed/CI environment --
# it requires a real broker connection.
#
# What it does, per instrument/timeframe pair:
#   1. Connects to MT5, pulls the bar data (or reads cache if already
#      pulled -- fetch()'s normal behavior).
#   2. Hashes the resulting cache file (sha256).
#   3. Appends a provenance record to research/data_ingestion_log.jsonl:
#      symbol, timeframe, date range, bar count, hash, git commit,
#      pulled_at timestamp.
#   4. Refuses to log (same discipline as the run ledger) if the git
#      tree is dirty outside the allowed exclude paths -- a data
#      ingestion record must point to a commit that actually reflects
#      the code state used to pull it.
#
# Usage:
#   python research/ingest_data.py                    # default S1 matrix (see below)
#   python research/ingest_data.py --symbols EURUSD AUDUSD --timeframes H1 H4

import sys
import json
import hashlib
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import MetaTrader5 as mt5

from data.mt5_connector import connect, disconnect, get_symbol
from data.loader import fetch, cache_path
from core.config import BACKTEST

INGESTION_LOG = Path("research/data_ingestion_log.jsonl")
REPO_ROOT = Path(__file__).resolve().parent.parent

TIMEFRAME_MAP = {
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
}

# S1 default matrix, per the roadmap:
#   - 1H for the 3 existing instruments
#   - H4 + H1 for new instruments (EURUSD, AUDUSD; add an index CFD
#     manually below if your feed has one -- symbol names vary by broker)
DEFAULT_SYMBOLS_EXISTING = ["USDJPY", "XAUUSD", "GBPJPY"]
DEFAULT_SYMBOLS_NEW      = ["EURUSD", "AUDUSD"]

# Same TRAIN/OOS boundary as S0, per research/S1_DATA_SPLIT.md --
# do not change without updating that file's reasoning first.
START = BACKTEST["start"]
END   = BACKTEST["end"]


def _git_commit() -> str:
    result = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
                            capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else "UNKNOWN"


def _git_dirty_paths() -> list:
    """Same exclude-aware check as research/experiment.py, duplicated
    minimally here rather than imported, since this script must also
    run standalone without the rest of the ledger machinery available
    if MT5-only dependencies are all that's installed locally."""
    excludes = ("research/ledger.jsonl", "research/runs/",
                "research/trades_", "research/yearly_", "research/regime_by_",
                "research/null_seed_results.csv", "research/null_runs/",
                "research/null_distribution_summary.csv",
                "research/h003_runs/", "research/h003_null_arm_results.csv",
                "research/H-003-verdict.csv",
                "research/data_ingestion_log.jsonl",
                "data/storage/")  # new data files themselves get committed deliberately, see main()
    result = subprocess.run(["git", "-C", str(REPO_ROOT), "status", "--porcelain"],
                            capture_output=True, text=True)
    dirty = []
    for line in result.stdout.rstrip("\n").splitlines():
        if not line.strip():
            continue
        path = line[3:].strip().strip('"')
        if any(path.startswith(ex) for ex in excludes):
            continue
        dirty.append(path)
    return dirty


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def ingest_one(symbol: str, timeframe_label: str, timeframe_const, start, end) -> dict:
    print(f"\n{'='*60}\n{symbol} / {timeframe_label}\n{'='*60}")

    if not get_symbol(symbol):
        print(f"[Ingest] SKIPPING {symbol}: not found/visible in Market Watch. "
              f"Check the exact symbol name your broker uses (e.g. suffixes "
              f"like '.a' or '.raw' are common) and update the symbol list.")
        return {"symbol": symbol, "timeframe": timeframe_label, "status": "SKIPPED_SYMBOL_NOT_FOUND"}

    df = fetch(symbol, timeframe_const, start, end, use_cache=True)
    if df.empty:
        print(f"[Ingest] SKIPPING {symbol}/{timeframe_label}: fetch returned no data.")
        return {"symbol": symbol, "timeframe": timeframe_label, "status": "SKIPPED_NO_DATA"}

    path = cache_path(symbol, timeframe_const)
    file_hash = _sha256_file(path)

    record = {
        "symbol":          symbol,
        "timeframe":       timeframe_label,
        "start":           str(start),
        "end":             str(end),
        "n_bars":          len(df),
        "sha256":          file_hash,
        "cache_path":      str(path),
        "git_commit":      _git_commit(),
        "pulled_at_utc":   datetime.now(timezone.utc).isoformat(),
        "status":          "OK",
    }
    print(f"[Ingest] {symbol}/{timeframe_label}: {len(df)} bars, sha256={file_hash[:16]}...")
    return record


def main(symbols: list, timeframes: list, start=START, end=END, log_to_ingestion_log: bool = True):
    dirty = _git_dirty_paths()
    if dirty and log_to_ingestion_log:
        print(f"[Ingest] WARNING: git tree has uncommitted changes outside "
              f"excluded paths: {dirty}\nProceeding with the pull (data "
              f"acquisition itself doesn't need a clean tree), but the "
              f"provenance record will note git_dirty=True instead of "
              f"refusing outright -- unlike the run ledger, losing an MT5 "
              f"pull because of an unrelated dirty file is not worth it. "
              f"Commit before the NEXT step (running any hypothesis "
              f"against this data) though.")

    if not connect():
        print("[Ingest] MT5 connection failed. Ensure the terminal is open "
              "and logged in. Aborting.")
        return

    records = []
    try:
        for symbol in symbols:
            for tf_label in timeframes:
                tf_const = TIMEFRAME_MAP[tf_label]
                rec = ingest_one(symbol, tf_label, tf_const, start, end)
                rec["git_dirty_at_ingest"] = bool(dirty)
                records.append(rec)
    finally:
        disconnect()

    if log_to_ingestion_log:
        INGESTION_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(INGESTION_LOG, "a") as f:
            for rec in records:
                f.write(json.dumps(rec) + "\n")
        print(f"\n[Ingest] Appended {len(records)} records -> {INGESTION_LOG}")

    ok = [r for r in records if r["status"] == "OK"]
    skipped = [r for r in records if r["status"] != "OK"]
    print(f"\n{'='*60}\nSUMMARY: {len(ok)} OK, {len(skipped)} skipped\n{'='*60}")
    for r in skipped:
        print(f"  SKIPPED: {r['symbol']}/{r['timeframe']} -- {r['status']}")

    print("\nNEXT STEPS:")
    print("  1. Review research/data_ingestion_log.jsonl")
    print("  2. git add data/storage/<new files> research/data_ingestion_log.jsonl")
    print("  3. Commit with a message citing the sha256 hashes above --")
    print("     that commit is the timestamp/tamper-evidence proof for this data,")
    print("     same mechanism as every H-00X registration's commit hash.")
    print("  4. THEN run any hypothesis against this data, on a clean tree.")

    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="+", default=DEFAULT_SYMBOLS_EXISTING + DEFAULT_SYMBOLS_NEW)
    parser.add_argument("--timeframes", nargs="+", default=["H1"],
                       choices=list(TIMEFRAME_MAP.keys()))
    parser.add_argument("--no-log", action="store_true")
    args = parser.parse_args()
    main(args.symbols, args.timeframes, log_to_ingestion_log=not args.no_log)
