# tests/test_schema_migration_s1_direction.py
#
# Permanent regression test for the S1 long/short schema migration:
# confirms the direction column was added WITHOUT altering any
# pre-existing trade data. Uses research/verify_schema_migration.py
# (the reusable tool) against a frozen pre-migration snapshot.
#
# This does not re-verify every future schema change (each new
# migration needs its own before/after snapshot) -- it's the permanent
# record that THIS migration was clean, using the standing tool rather
# than an ad hoc one-off check.
#
# SCOPE CORRECTION (2026-08-04, cost model v2, docs/COST_MODEL_V2_PLAN.md):
# pnl, pnl_gross, and size are EXCLUDED from this comparison as of cost
# model v2's Commit 1 (size-scaling fix to execution/costs.py). These
# columns are cost-derived and legitimately change whenever the cost
# model changes -- including indirectly: pnl_gross and size for every
# trade AFTER the first one whose cost changed also shift, because
# position_size() compounds off self.capital, which now differs from
# the corrected earlier trades' pnl (same cascading effect documented
# in tests/test_simulator.py's test_trade_b_sizing_and_pnl). This is
# NOT evidence of a schema-migration defect -- it is the cost fix
# working as intended, an unrelated and later legitimate change.
#
# The migration's actual, narrower claim -- that adding the direction
# column did not alter direction, prices, timestamps, bars_held, exit
# reason, or any entry-feature column -- is unaffected by the cost fix
# and remains verified below (confirmed byte-identical across all three
# symbols before this exclusion was added, not assumed). A future
# migration that corrupts any of THOSE columns will still be caught.
# This scope correction is a deliberate, dated, disclosed change to
# what this test protects -- not a quiet loosening to turn a red test
# green.

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from research.verify_schema_migration import verify

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "s1_direction_migration"

# Cost-derived columns, excluded per the scope correction above.
COST_DERIVED_COLUMNS = {"pnl", "pnl_gross", "size"}


@pytest.mark.parametrize("symbol", ["USDJPY", "XAUUSD", "GBPJPY"])
def test_direction_column_added_without_altering_existing_data(symbol):
    pre_path  = FIXTURES_DIR / f"pre_direction_trades_{symbol}.csv"
    post_path = Path(f"research/trades_{symbol}.csv")

    if not pre_path.exists():
        pytest.skip(f"Pre-migration fixture not found: {pre_path}")
    if not post_path.exists():
        pytest.skip(f"Current trades file not found: {post_path}")

    assert verify(str(pre_path), str(post_path), exclude_columns=COST_DERIVED_COLUMNS), (
        f"{symbol}: shared non-cost-derived columns diverged from the frozen "
        f"pre-direction snapshot -- the S1 schema migration was supposed to "
        f"ONLY add the 'direction' column, not alter any existing trade data "
        f"(pnl/pnl_gross/size are excluded here -- see module docstring)."
    )
