# research/run_h008.py
#
# H-008: thin-session x high-volatility interaction on reversion.
# Freeze-then-verdict, same structural discipline as run_h001.py /
# run_h005.py. Unlike those, the ATR tercile edges are NOT re-derived
# here -- they are read directly from the already-frozen
# research/registry/H-005-bins.json (per H-008.md Sec 3a). What THIS
# script's --freeze phase locks in is the cell definition (which
# session counts as "thin" per instrument, from core/instruments.py --
# deterministic, not data-derived, but still written down and
# ledger-logged before --verdict runs) and a hash-check that the H-005
# bins file hasn't changed underneath this hypothesis.
#
# Depends on research/interaction_harness.py + research/fdr_cells.py,
# both validated on synthetic known-answer data
# (tests/test_interaction_harness.py, tests/test_fdr_cells.py) BEFORE
# this script is run -- do not run --verdict if those tests do not
# currently pass.
#
# Usage:
#   python research/run_h008.py --freeze
#   python research/run_h008.py --verdict

import sys
import json
import argparse
import hashlib
import types
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# MetaTrader5 requires a live terminal and cannot be imported in this
# sandboxed analysis context; data.loader's cache_path() only needs the
# module to exist enough to import, never to connect. Same stub
# pattern as tests/test_determinism.py / tests/test_simulator.py --
# not fabricating data (this script only reads real cached CSVs), only
# satisfying an unused import path.
if "MetaTrader5" not in sys.modules:
    _mt5_stub = types.ModuleType("MetaTrader5")
    _mt5_stub.TIMEFRAME_H4 = 16388
    _mt5_stub.TIMEFRAME_H1 = 16385
    sys.modules["MetaTrader5"] = _mt5_stub

from research.experiment import record, DirtyGitStateError
from research.interaction_harness import load_h1_bars, build_cell, permutation_test, seed_dispersion
from research.fdr_cells import bh_adjusted_thresholds
from core.instruments import INSTRUMENT_META
from data.loader import cache_path
from core.config import BACKTEST

SYMBOLS = ["USDJPY", "XAUUSD", "GBPJPY", "EURUSD", "AUDUSD"]
TRAIN_END = "2022-01-01"
N_NULL_SEEDS = 100
N_PERMUTATIONS = 2000
RNG_SEED = 43   # distinct from H-005's RNG_SEED=42 -- independent draw
PRIMARY_K = 3
SECONDARY_K = 1  # descriptive only, per H-008.md Sec 3b -- never adjudicating

H005_BINS_PATH = Path("research/registry/H-005-bins.json")
MANIFEST_PATH = Path("research/registry/H-008-manifest.json")
NULL_RUNS_DIR = Path("research/null_runs_h004")

# Thin session per instrument (the session where the instrument's own
# currency/market is CLOSED), derived from core/instruments.py's
# `sessions` list -- an instrument whose home session is NOT tokyo
# treats tokyo as thin. This mirrors the memo's own tokyo split
# (EURUSD/XAUUSD = thin at tokyo; USDJPY/GBPJPY/AUDUSD = home at tokyo).
THIN_SESSION = "tokyo"


def _predicted_group(symbol: str) -> str:
    return "thin_at_tokyo" if "tokyo" not in INSTRUMENT_META[symbol]["sessions"] else "home_at_tokyo"


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze_manifest():
    """PHASE 1. Locks in: (a) the H-005 bins file's hash (so any later
    drift in that file is detectable), (b) each instrument's thin/home
    group assignment, (c) the primary/secondary window choice. Writes
    to H-008-manifest.json and logs a ledger entry BEFORE any
    reversion statistic is computed."""
    if not H005_BINS_PATH.exists():
        raise RuntimeError(f"{H005_BINS_PATH} not found -- H-005 must be frozen first.")

    groups = {s: _predicted_group(s) for s in SYMBOLS}
    manifest = {
        "hypothesis": "H-008",
        "reused_bins_from": "H-005",
        "h005_bins_sha256": _file_hash(H005_BINS_PATH),
        "train_end": TRAIN_END,
        "thin_session": THIN_SESSION,
        "predicted_group_by_symbol": groups,
        "primary_k": PRIMARY_K,
        "secondary_k_non_adjudicating": SECONDARY_K,
        "n_permutations": N_PERMUTATIONS,
        "rng_seed": RNG_SEED,
    }
    print("[H-008] Predicted groups (per mechanism memo 2b04b66):")
    for s, g in groups.items():
        print(f"  {s}: {g}")

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"[H-008] Frozen manifest written -> {MANIFEST_PATH}")

    try:
        entry = record(
            strategy="H-008-manifest", symbols=SYMBOLS,
            config_snapshot=manifest,
            data_paths={s: str(cache_path(s, BACKTEST["timeframe"])) for s in SYMBOLS},
            output_paths={s: f"research/null_runs_h004/{s}_H1_seed0_trades.csv" for s in SYMBOLS},
            extra={"purpose": "H-008_manifest_freeze", "manifest_path": str(MANIFEST_PATH)},
        )
        print(f"[H-008] Manifest freeze logged to ledger: {entry['run_id']}")
    except (DirtyGitStateError, FileNotFoundError) as e:
        print(f"[H-008] Ledger WARNING (manifest freeze not logged): {e}")

    print("\n[H-008] Manifest is now FROZEN. Do not re-run --freeze after "
          "viewing --verdict output.")


def _load_pooled_top_tercile(symbol: str, edges: list) -> pd.DataFrame:
    frames = []
    for seed in range(N_NULL_SEEDS):
        path = NULL_RUNS_DIR / f"{symbol}_H1_seed{seed}_trades.csv"
        if not path.exists():
            continue
        df = pd.read_csv(path, parse_dates=["entry_dt"])
        df = df[df["entry_dt"] < TRAIN_END].copy()
        if df.empty:
            continue
        df["seed"] = seed
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    pooled = pd.concat(frames, ignore_index=True)
    pooled["tercile"] = pd.cut(pooled["atr_entry"], bins=edges, labels=False, include_lowest=True)
    n_terciles = len(edges) - 1
    top = n_terciles - 1
    return pooled[pooled["tercile"] == top].copy()


def compute_verdict():
    """PHASE 2. Reads the frozen manifest + H-005 bins (never
    recomputes them), runs the permutation test + seed-dispersion check
    per instrument-cell at both PRIMARY_K (adjudicating) and
    SECONDARY_K (descriptive only), then the 2-vs-3 group comparison."""
    if not MANIFEST_PATH.exists():
        raise RuntimeError(f"{MANIFEST_PATH} not found -- run --freeze first.")
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)

    current_hash = _file_hash(H005_BINS_PATH)
    if current_hash != manifest["h005_bins_sha256"]:
        raise RuntimeError(
            "H-005-bins.json hash has changed since H-008's manifest was "
            "frozen -- refusing to proceed on drifted bin edges. Investigate "
            "before continuing."
        )

    with open(H005_BINS_PATH) as f:
        h005 = json.load(f)

    rng = np.random.default_rng(manifest["rng_seed"])
    rows = []

    for symbol in SYMBOLS:
        edges = h005["bins_by_symbol"][symbol]["edges"]
        top_tercile_trades = _load_pooled_top_tercile(symbol, edges)
        bars = load_h1_bars(symbol)

        cell_primary = build_cell(symbol, top_tercile_trades, bars,
                                    k=manifest["primary_k"], thin_session=manifest["thin_session"])
        cell_secondary = build_cell(symbol, top_tercile_trades, bars,
                                      k=manifest["secondary_k_non_adjudicating"],
                                      thin_session=manifest["thin_session"])

        obs_primary, p_primary = permutation_test(cell_primary, N_PERMUTATIONS, rng)
        obs_secondary, p_secondary = permutation_test(cell_secondary, N_PERMUTATIONS, rng)

        disp_thin = seed_dispersion(cell_primary.thin_reversion, cell_primary.thin_seeds)
        disp_home = seed_dispersion(cell_primary.home_reversion, cell_primary.home_seeds)
        max_disp = np.nanmax([disp_thin, disp_home]) if not (np.isnan(disp_thin) and np.isnan(disp_home)) else float("nan")

        n_thin = len(cell_primary.thin_reversion)
        n_home = len(cell_primary.home_reversion)
        sufficient_n = (n_thin >= 30) and (n_home >= 30)
        effect_exceeds_noise = (not np.isnan(max_disp)) and (abs(obs_primary) > max_disp) if not np.isnan(obs_primary) else False

        print(f"\n{symbol} ({manifest['predicted_group_by_symbol'][symbol]}):")
        print(f"  n_thin(tokyo)={n_thin}  n_home={n_home}  sufficient_n(>=30 each)={sufficient_n}")
        print(f"  PRIMARY  k={manifest['primary_k']}: observed_diff={obs_primary:.4f}  p={p_primary}")
        print(f"  SECONDARY(non-adjudicating) k={manifest['secondary_k_non_adjudicating']}: "
              f"observed_diff={obs_secondary:.4f}  p={p_secondary}")
        print(f"  seed_dispersion: thin={disp_thin:.4f}  home={disp_home:.4f}  "
              f"effect_exceeds_max_dispersion={effect_exceeds_noise}")

        rows.append({
            "symbol": symbol,
            "predicted_group": manifest["predicted_group_by_symbol"][symbol],
            "n_thin": n_thin, "n_home": n_home, "sufficient_n": sufficient_n,
            "observed_diff_primary": round(obs_primary, 4) if not np.isnan(obs_primary) else None,
            "p_value_primary": p_primary,
            "observed_diff_secondary_descriptive_only": round(obs_secondary, 4) if not np.isnan(obs_secondary) else None,
            "p_value_secondary_descriptive_only": p_secondary,
            "seed_dispersion_thin": disp_thin, "seed_dispersion_home": disp_home,
            "effect_exceeds_noise": effect_exceeds_noise,
        })

    verdict_df = pd.DataFrame(rows)

    # Per-cell FDR: BH across the 5 instrument-cells' PRIMARY p-values.
    p_map = {r["symbol"]: r["p_value_primary"] for r in rows if r["p_value_primary"] is not None}
    bh_results = bh_adjusted_thresholds(p_map, alpha=0.05)
    for symbol, res in bh_results.items():
        verdict_df.loc[verdict_df["symbol"] == symbol, "bh_adjusted_threshold"] = res.bh_adjusted_threshold
        verdict_df.loc[verdict_df["symbol"] == symbol, "bh_significant"] = res.significant

    thin_group = [r for r in rows if r["predicted_group"] == "thin_at_tokyo"]
    home_group = [r for r in rows if r["predicted_group"] == "home_at_tokyo"]

    thin_group_clears = all(
        r["sufficient_n"] and r["effect_exceeds_noise"] and
        bh_results.get(r["symbol"], None) is not None and bh_results[r["symbol"]].significant
        for r in thin_group
    )

    print(f"\n{'='*70}")
    print(f"Thin-at-tokyo group (EURUSD, XAUUSD, GBPJPY -- corrected 3-vs-2 "
          f"grouping, H-008.md Sec 2 amendment) ALL clear "
          f"(n>=30 AND exceed noise AND BH-significant): {thin_group_clears}")
    print("Per H-008.md Sec 5 (amended) kill criteria: the corrected 3-vs-2 "
          "prediction requires ALL of EURUSD, XAUUSD, GBPJPY to clear -- "
          "if any fails, KILLED.")

    # Pre-registered, NON-ADJUDICATING robustness view: same comparison
    # with GBPJPY excluded (2-vs-2), per H-008.md Sec 2 amendment. GBPJPY
    # is the contested instrument (memo vs core/instruments.py); this
    # view is reported for transparency only, never substituted as the
    # adjudicating statistic.
    thin_group_ex_gbpjpy = [r for r in thin_group if r["symbol"] != "GBPJPY"]
    thin_group_clears_ex_gbpjpy = all(
        r["sufficient_n"] and r["effect_exceeds_noise"] and
        bh_results.get(r["symbol"], None) is not None and bh_results[r["symbol"]].significant
        for r in thin_group_ex_gbpjpy
    )
    print(f"\n[NON-ADJUDICATING, pre-registered robustness view]")
    print(f"Thin-at-tokyo group EXCLUDING GBPJPY (EURUSD, XAUUSD only, 2-vs-2 "
          f"vs USDJPY/AUDUSD) ALL clear: {thin_group_clears_ex_gbpjpy}")
    print("This view does not adjudicate H-008 -- reported only so GBPJPY's "
          "inclusion/exclusion cannot be chosen post-hoc to favor either verdict.")

    verdict_df.to_csv("research/H-008-verdict.csv", index=False)
    print(f"\nPRIMARY CLAIM {'SURVIVES this check' if thin_group_clears else 'KILLED'}")
    print("Reminder (H-008.md Sec 6): even if SURVIVES, this is a KILL-only-"
          "valid adjudication under the current cost model -- NOT an "
          "acceptance. Cost model v2 + AUDUSD real specs required first.")
    print("Saved -> research/H-008-verdict.csv")
    return verdict_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--verdict", action="store_true")
    args = parser.parse_args()
    if args.freeze:
        freeze_manifest()
    elif args.verdict:
        compute_verdict()
    else:
        print("Specify --freeze or --verdict.")
