# research/fdr_check.py
#
# Small, deliberately simple tool: given the CURRENT registry size (read
# from research/registry/H-*.md files, not hand-counted), reports the
# Benjamini-Hochberg adjusted significance threshold for the NEXT
# hypothesis to be adjudicated. Run this BEFORE reading a new
# hypothesis's p-value, per research/registry/FDR_LEDGER.md's own rule
# that the correction can't be decided after seeing whether a result
# looks clean.
#
# Usage: python research/fdr_check.py [--alpha 0.05]

import argparse
import re
from pathlib import Path

REGISTRY_DIR = Path("research/registry")


def count_registered_hypotheses() -> int:
    """Counts H-XXX.md files in the registry, excluding TEMPLATE.md and
    supporting files (FDR_LEDGER.md, H-001-bins.json)."""
    pattern = re.compile(r"^H-\d+\.md$")
    return sum(1 for f in REGISTRY_DIR.glob("*.md") if pattern.match(f.name))


def bh_threshold(rank: int, n_total: int, alpha: float = 0.05) -> float:
    """Benjamini-Hochberg adjusted threshold for the hypothesis ranked
    `rank` (1-indexed, typically 1 = the new one, since prior hypotheses
    are already adjudicated and closed) out of n_total tests."""
    return alpha * rank / n_total


def main(alpha: float = 0.05):
    n_prior = count_registered_hypotheses()
    n_next = n_prior + 1

    print(f"Hypotheses already registered/adjudicated: {n_prior}")
    print(f"This will be hypothesis #{n_next} if registered now.")
    print()
    print(f"Raw alpha: {alpha}")
    print(f"BH-adjusted threshold (rank 1 of {n_next}): {bh_threshold(1, n_next, alpha):.4f}")
    print(f"Bonferroni threshold (conservative, {n_next} tests): {alpha / n_next:.4f}")
    print()
    print("REMINDER (per research/registry/FDR_LEDGER.md):")
    print("  - A raw p < 0.05 is NOT sufficient once the registry has")
    print("    accumulated multiple tests. Use the adjusted threshold above.")
    print("  - The seed-to-seed dispersion check (H-002/H-004's template)")
    print("    is mandatory regardless of which threshold the p-value clears.")
    print("  - If this hypothesis shares a mechanism family with a prior")
    print("    hypothesis (e.g. another session-structure test), apply the")
    print("    correction WITHIN that sub-family too, not just the overall count.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--alpha", type=float, default=0.05)
    args = parser.parse_args()
    main(alpha=args.alpha)
