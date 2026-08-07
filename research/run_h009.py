# research/run_h009.py
#
# H-009: month-end proximity x high-volatility interaction on
# reversion. Freeze-then-verdict, same structural discipline as
# run_h008.py. ATR tercile edges reused from H-005-bins.json
# unchanged. New here: the calendar-distance conditioning variable
# (research/calendar_distance.py) and the primary cell is POOLED
# across instruments (no per-instrument asymmetry predicted, unlike
# H-008), plus two non-adjudicating side computations (quarter-end
# margin, low/mid-tercile arm).
#
# Depends on research/interaction_harness.py, research/calendar_distance.py,
# both validated on synthetic known-answer data BEFORE this script is
# run -- do not run --verdict if those tests do not currently pass.
#
# Usage:
#   python research/run_h009.py --freeze
#   python research/run_h009.py --verdict

import sys
import json
import argparse
import hashlib
import types
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if "MetaTrader5" not in sys.modules:
    _mt5_stub = types.ModuleType("MetaTrader5")
    _mt5_stub.TIMEFRAME_H4 = 16388
    _mt5_stub.TIMEFRAME_H1 = 16385
    sys.modules["MetaTrader5"] = _mt5_stub

from research.experiment import record, DirtyGitStateError
from research.interaction_harness import load_h1_bars, build_cell_calendar, permutation_test, seed_dispersion
from research.calendar_distance import is_quarter_end_month, is_near_month_end
from data.loader import cache_path
from core.config import BACKTEST

SYMBOLS = ["USDJPY", "XAUUSD", "GBPJPY", "EURUSD", "AUDUSD"]
TRAIN_END = "2022-01-01"
N_NULL_SEEDS = 100
N_PERMUTATIONS = 2000
RNG_SEED = 44   # distinct from H-005 (42) and H-008 (43) -- independent draw
PRIMARY_K = 3
SECONDARY_K = 1  # descriptive only, never adjudicating
LOW_MID_UNDERCUT_FRACTION = 0.5  # per H-009.md Sec 2 / memo amendment

H005_BINS_PATH = Path("research/registry/H-005-bins.json")
MANIFEST_PATH = Path("research/registry/H-009-manifest.json")
NULL_RUNS_DIR = Path("research/null_runs_h004")


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze_manifest():
    """PHASE 1. Locks in the H-005 bins hash, window choices, and the
    low/mid-arm interpretation fraction -- BEFORE any reversion
    statistic is computed."""
    if not H005_BINS_PATH.exists():
        raise RuntimeError(f"{H005_BINS_PATH} not found -- H-005 must be frozen first.")

    manifest = {
        "hypothesis": "H-009",
        "reused_bins_from": "H-005",
        "h005_bins_sha256": _file_hash(H005_BINS_PATH),
        "train_end": TRAIN_END,
        "primary_k": PRIMARY_K,
        "secondary_k_non_adjudicating": SECONDARY_K,
        "low_mid_undercut_fraction": LOW_MID_UNDERCUT_FRACTION,
        "n_permutations": N_PERMUTATIONS,
        "rng_seed": RNG_SEED,
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"[H-009] Frozen manifest written -> {MANIFEST_PATH}")

    try:
        entry = record(
            strategy="H-009-manifest", symbols=SYMBOLS,
            config_snapshot=manifest,
            data_paths={s: str(cache_path(s, BACKTEST["timeframe"])) for s in SYMBOLS},
            output_paths={s: f"research/null_runs_h004/{s}_H1_seed0_trades.csv" for s in SYMBOLS},
            extra={"purpose": "H-009_manifest_freeze", "manifest_path": str(MANIFEST_PATH)},
        )
        print(f"[H-009] Manifest freeze logged to ledger: {entry['run_id']}")
    except (DirtyGitStateError, FileNotFoundError) as e:
        print(f"[H-009] Ledger WARNING (manifest freeze not logged): {e}")

    print("\n[H-009] Manifest is now FROZEN. Do not re-run --freeze after "
          "viewing --verdict output.")


def _load_pooled_tercile(symbol: str, edges: list, top: bool) -> pd.DataFrame:
    """top=True -> top tercile only (primary + quarter-end margin).
    top=False -> terciles 1-2 pooled (the non-adjudicating low/mid arm)."""
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
    top_idx = n_terciles - 1
    if top:
        return pooled[pooled["tercile"] == top_idx].copy()
    return pooled[pooled["tercile"] < top_idx].copy()


def compute_verdict():
    """PHASE 2. Pools top-tercile trades across ALL instruments (no
    per-instrument asymmetry predicted), computes the primary cell,
    the non-adjudicating quarter-end margin, and the non-adjudicating
    low/mid arm."""
    if not MANIFEST_PATH.exists():
        raise RuntimeError(f"{MANIFEST_PATH} not found -- run --freeze first.")
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)

    current_hash = _file_hash(H005_BINS_PATH)
    if current_hash != manifest["h005_bins_sha256"]:
        raise RuntimeError(
            "H-005-bins.json hash has changed since H-009's manifest was "
            "frozen -- refusing to proceed on drifted bin edges."
        )
    with open(H005_BINS_PATH) as f:
        h005 = json.load(f)

    rng = np.random.default_rng(manifest["rng_seed"])

    top_frames, low_mid_frames = [], []
    bars_by_symbol = {}
    for symbol in SYMBOLS:
        edges = h005["bins_by_symbol"][symbol]["edges"]
        top_frames.append(_load_pooled_tercile(symbol, edges, top=True))
        low_mid_frames.append(_load_pooled_tercile(symbol, edges, top=False))
        bars_by_symbol[symbol] = load_h1_bars(symbol)

    # Primary cell: pool top-tercile trades across ALL instruments into
    # ONE cell (mechanism predicts no instrument asymmetry). Reversion
    # is computed per-instrument (bars differ) then pooled.
    def _pooled_reversion_cell(frames_by_symbol_top, k, only_quarter_end=None):
        thin_rev, thin_seeds, home_rev, home_seeds = [], [], [], []
        for symbol, trades in zip(SYMBOLS, frames_by_symbol_top):
            if trades.empty:
                continue
            cell = build_cell_calendar(symbol, trades, bars_by_symbol[symbol], k=k)
            # build_cell_calendar already labels near-ME (thin) vs
            # ordinary (home) via clock/calendar logic -- pool across
            # symbols here.
            if only_quarter_end is not None:
                # Re-derive which near-ME rows are quarter-end vs not,
                # by re-joining entry_dt -- build_cell_calendar doesn't
                # expose this split directly, so recompute the mask on
                # the same top-tercile trades frame used to build the cell.
                me_mask = trades["entry_dt"].apply(
                    lambda dt: is_near_month_end(pd.Timestamp(dt).date())
                )
                qe_mask = trades["entry_dt"].apply(lambda dt: is_quarter_end_month(pd.Timestamp(dt).date()))
                sub = trades[me_mask & (qe_mask if only_quarter_end else ~qe_mask)]
                sub_cell = build_cell_calendar(symbol, sub, bars_by_symbol[symbol], k=k)
                thin_rev.extend(sub_cell.thin_reversion)
                thin_seeds.extend(sub_cell.thin_seeds)
            else:
                thin_rev.extend(cell.thin_reversion)
                thin_seeds.extend(cell.thin_seeds)
            home_rev.extend(cell.home_reversion)
            home_seeds.extend(cell.home_seeds)

        from research.interaction_harness import CellData
        return CellData(
            cell_id="POOLED",
            thin_reversion=np.array(thin_rev, dtype=float),
            thin_seeds=np.array(thin_seeds),
            home_reversion=np.array(home_rev, dtype=float),
            home_seeds=np.array(home_seeds),
        )

    # PRIMARY (adjudicating): pooled near-ME vs ordinary, top tercile, k=3.
    primary_cell = _pooled_reversion_cell(top_frames, PRIMARY_K)
    obs_primary, p_primary = permutation_test(primary_cell, N_PERMUTATIONS, rng)
    disp_thin = seed_dispersion(primary_cell.thin_reversion, primary_cell.thin_seeds)
    disp_home = seed_dispersion(primary_cell.home_reversion, primary_cell.home_seeds)
    max_disp = np.nanmax([disp_thin, disp_home]) if not (np.isnan(disp_thin) and np.isnan(disp_home)) else float("nan")
    n_thin, n_home = len(primary_cell.thin_reversion), len(primary_cell.home_reversion)
    sufficient_n = (n_thin >= 30) and (n_home >= 30)
    effect_exceeds_noise = (not np.isnan(max_disp)) and (not np.isnan(obs_primary)) and (abs(obs_primary) > max_disp)
    primary_significant = (p_primary is not None) and (p_primary < 0.05)

    print(f"\n{'='*70}\nPRIMARY (near-month-end x top-ATR-tercile, pooled across instruments, k={PRIMARY_K})")
    print(f"  n_near_ME={n_thin}  n_ordinary={n_home}  sufficient_n(>=30 each)={sufficient_n}")
    print(f"  observed_diff={obs_primary:.4f}  p={p_primary}")
    print(f"  seed_dispersion: near_ME={disp_thin:.4f}  ordinary={disp_home:.4f}  "
          f"effect_exceeds_max_dispersion={effect_exceeds_noise}")
    print(f"  p<0.05={primary_significant}")

    # Refutation clause 2: must revert, not persist. Reversion metric
    # is already defined as -sign(r0)*(future move); a POSITIVE
    # obs_primary (near-ME minus ordinary, both already signed-reversion)
    # consistent with reversion; check the raw sign convention here:
    # obs_primary > 0 with meaningful magnitude indicates reversion is
    # STRONGER near month-end, consistent with the mechanism. A
    # negative obs_primary would indicate continuation dominates near
    # month-end relative to ordinary bars, i.e. refutation clause 2.
    reverts_not_persists = (not np.isnan(obs_primary)) and (obs_primary > 0)
    print(f"  reverts (not persists), refutation clause 2 check: {reverts_not_persists}")

    primary_survives = sufficient_n and effect_exceeds_noise and primary_significant and reverts_not_persists
    print(f"\nPRIMARY {'SURVIVES' if primary_survives else 'KILLED'} "
          f"(kill if ANY of: insufficient n, effect within seed noise, "
          f"p>=0.05, or does not revert)")

    result = {
        "primary": {
            "n_thin": int(n_thin), "n_home": int(n_home), "sufficient_n": bool(sufficient_n),
            "observed_diff": round(float(obs_primary), 4) if not np.isnan(obs_primary) else None,
            "p_value": p_primary, "effect_exceeds_noise": bool(effect_exceeds_noise),
            "reverts_not_persists": bool(reverts_not_persists),
            "significant": bool(primary_significant), "survives": bool(primary_survives),
        }
    }

    if not primary_survives:
        print("\nPer H-009.md Sec 4: primary failed -> H-009 KILLED. The "
              "low/mid arm and quarter-end margin are reported below for "
              "completeness/transparency but CANNOT rescue this verdict "
              "(explicit asymmetry, memo amendment 140ec71).")

    # Quarter-end margin (non-adjudicating): computed regardless of
    # primary outcome, purely descriptive.
    qe_cell = _pooled_reversion_cell(top_frames, PRIMARY_K, only_quarter_end=True)
    ord_me_cell = _pooled_reversion_cell(top_frames, PRIMARY_K, only_quarter_end=False)
    obs_qe, p_qe = permutation_test(qe_cell, N_PERMUTATIONS, rng) if len(qe_cell.thin_reversion) > 0 else (float("nan"), None)
    obs_ord, p_ord = permutation_test(ord_me_cell, N_PERMUTATIONS, rng) if len(ord_me_cell.thin_reversion) > 0 else (float("nan"), None)
    print(f"\n[NON-ADJUDICATING] Quarter-end margin: quarter-end near-ME "
          f"observed_diff={obs_qe:.4f} (n={len(qe_cell.thin_reversion)}) vs. "
          f"ordinary-month near-ME observed_diff={obs_ord:.4f} "
          f"(n={len(ord_me_cell.thin_reversion)})")
    qe_stronger = (not np.isnan(obs_qe)) and (not np.isnan(obs_ord)) and (obs_qe > obs_ord)
    print(f"  Quarter-end stronger than ordinary month-end (predicted): {qe_stronger}")
    result["quarter_end_margin"] = {
        "quarter_end_diff": round(float(obs_qe), 4) if not np.isnan(obs_qe) else None,
        "ordinary_month_end_diff": round(float(obs_ord), 4) if not np.isnan(obs_ord) else None,
        "quarter_end_stronger_as_predicted": bool(qe_stronger),
    }

    # Low/mid-tercile arm (non-adjudicating), same permutation/dispersion path.
    low_mid_cell = _pooled_reversion_cell(low_mid_frames, PRIMARY_K)
    obs_lm, p_lm = permutation_test(low_mid_cell, N_PERMUTATIONS, rng)
    disp_lm_thin = seed_dispersion(low_mid_cell.thin_reversion, low_mid_cell.thin_seeds)
    disp_lm_home = seed_dispersion(low_mid_cell.home_reversion, low_mid_cell.home_seeds)
    print(f"\n[NON-ADJUDICATING] Low/mid-tercile arm: observed_diff={obs_lm:.4f} "
          f"p={p_lm}  (n_near_ME={len(low_mid_cell.thin_reversion)}, "
          f"n_ordinary={len(low_mid_cell.home_reversion)})")

    undercuts = False
    if primary_survives and not np.isnan(obs_lm) and not np.isnan(obs_primary) and obs_primary != 0:
        same_sign = (obs_lm > 0) == (obs_primary > 0)
        magnitude_ratio = abs(obs_lm) / abs(obs_primary)
        undercuts = same_sign and (magnitude_ratio >= manifest["low_mid_undercut_fraction"])
        print(f"  magnitude_ratio (low_mid/primary)={magnitude_ratio:.3f}  same_sign={same_sign}")
        print(f"  UNDERCUTS interaction reading (per H-009.md Sec 2, >=50% same-sign): {undercuts}")
    else:
        print("  Arm not evaluated for undercut (primary did not survive, or "
              "primary/arm effect is zero/NaN) -- per explicit asymmetry, "
              "this arm has no power to change a KILLED verdict.")

    result["low_mid_arm"] = {
        "observed_diff": round(float(obs_lm), 4) if not np.isnan(obs_lm) else None,
        "p_value": p_lm, "undercuts_interaction_reading": bool(undercuts),
    }

    final_verdict = "KILLED" if not primary_survives else ("SURVIVES (undercut by low/mid arm)" if undercuts else "SURVIVES")
    print(f"\n{'='*70}\nFINAL H-009 VERDICT: {final_verdict}")
    if primary_survives:
        print("Reminder (H-009.md Sec 6): even a clean SURVIVES is a "
              "KILL-only-valid adjudication under the current cost model -- "
              "NOT an acceptance. Cost model v2 + AUDUSD real specs required first.")

    with open("research/H-009-verdict.json", "w") as f:
        json.dump(result, f, indent=2)
    print("\nSaved -> research/H-009-verdict.json")
    return result


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
