# research/fdr_cells.py
#
# Extends fdr_check.py's registry-level (one-p-value-per-hypothesis)
# correction to the per-CELL case the Conditional Search charter
# requires for interaction hypotheses. A single hypothesis like H-008
# can define multiple cells (one per instrument here); each cell's
# p-value must be corrected against the OTHER cells in the SAME
# hypothesis, not just against the count of hypotheses in the registry.
#
# This module is deliberately pure (no I/O, no data loading) so it can
# be validated on synthetic, known-answer inputs before it ever touches
# real H-008 data -- per ENGINEERING_STANDARDS.md Sec 2 / the
# StringArray-bug precedent (LESSONS_LEARNED.md Sec 3.4).

from dataclasses import dataclass


@dataclass
class CellResult:
    cell_id: str
    p_value: float
    bh_adjusted_threshold: float
    significant: bool  # p_value < bh_adjusted_threshold


def bh_adjusted_thresholds(p_values: dict, alpha: float = 0.05) -> dict:
    """
    Standard Benjamini-Hochberg step-up procedure, applied across the
    cells of ONE hypothesis (e.g. H-008's 5 instrument-cells), not
    across the whole hypothesis registry -- that is fdr_check.py's job,
    a separate and additional correction layer.

    Given {cell_id: p_value}, returns {cell_id: CellResult} where a
    cell counts as significant only if its p-value is below its own
    rank-dependent BH threshold AND every cell ranked below it (smaller
    p-value) is also below ITS threshold (the standard BH step-up
    condition -- a single small p-value surrounded by large ones does
    NOT get called significant just because of its own rank).

    m = number of cells in this hypothesis (NOT the registry size).
    """
    m = len(p_values)
    if m == 0:
        return {}

    ranked = sorted(p_values.items(), key=lambda kv: kv[1])  # ascending p
    thresholds = {}
    for rank, (cell_id, p) in enumerate(ranked, start=1):
        thresholds[cell_id] = alpha * rank / m

    # Step-up: find the largest rank k such that p_(k) <= alpha*k/m.
    # All cells ranked <= k are significant; all ranked > k are not,
    # REGARDLESS of their own individual threshold comparison.
    largest_significant_rank = 0
    for rank, (cell_id, p) in enumerate(ranked, start=1):
        if p <= thresholds[cell_id]:
            largest_significant_rank = rank

    results = {}
    for rank, (cell_id, p) in enumerate(ranked, start=1):
        results[cell_id] = CellResult(
            cell_id=cell_id,
            p_value=p,
            bh_adjusted_threshold=thresholds[cell_id],
            significant=(rank <= largest_significant_rank),
        )
    return results
