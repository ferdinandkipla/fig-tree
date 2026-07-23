# research/verify_schema_migration.py
#
# Migration verifier: whenever a schema change is legitimate (a new
# column added, e.g. 'direction' in the S1 long/short redesign), byte-
# identical file hashing is no longer the right regression check --
# but "the schema legitimately changed" must never become an excuse to
# skip verification. This script is the standing tool: it checks that
# every column shared between an OLD and NEW trade CSV is numerically
# IDENTICAL, and reports exactly which columns are new/removed.
#
# Usage:
#   python research/verify_schema_migration.py old.csv new.csv
#
# Exit code 0 if shared columns match exactly; 1 otherwise. Prints a
# clear diff summary either way.

import sys
import argparse
import pandas as pd


def verify(old_path: str, new_path: str) -> bool:
    old = pd.read_csv(old_path)
    new = pd.read_csv(new_path)

    old_cols = set(old.columns)
    new_cols = set(new.columns)
    added   = new_cols - old_cols
    removed = old_cols - new_cols
    shared  = sorted(old_cols & new_cols)

    print(f"Old: {old_path}  shape={old.shape}")
    print(f"New: {new_path}  shape={new.shape}")
    print(f"Columns added:   {sorted(added) or '(none)'}")
    print(f"Columns removed: {sorted(removed) or '(none)'}")

    if old.shape[0] != new.shape[0]:
        print(f"FAIL: row count differs ({old.shape[0]} vs {new.shape[0]}) "
              f"-- this is not a pure schema migration, trade-level "
              f"behavior changed. Investigate before treating this as "
              f"'just a schema change.'")
        return False

    old_shared = old[shared].reset_index(drop=True)
    new_shared = new[shared].reset_index(drop=True)
    identical = old_shared.equals(new_shared)

    if identical:
        print(f"PASS: all {len(shared)} shared columns are numerically identical.")
    else:
        print("FAIL: shared columns differ. Per-column diff:")
        for col in shared:
            if not old_shared[col].equals(new_shared[col]):
                mismatches = (old_shared[col] != new_shared[col]).sum()
                print(f"  {col}: {mismatches} row(s) differ")

    return identical


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("old_csv")
    parser.add_argument("new_csv")
    args = parser.parse_args()
    ok = verify(args.old_csv, args.new_csv)
    sys.exit(0 if ok else 1)
