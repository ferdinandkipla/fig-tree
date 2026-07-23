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

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from research.verify_schema_migration import verify

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "s1_direction_migration"


@pytest.mark.parametrize("symbol", ["USDJPY", "XAUUSD", "GBPJPY"])
def test_direction_column_added_without_altering_existing_data(symbol):
    pre_path  = FIXTURES_DIR / f"pre_direction_trades_{symbol}.csv"
    post_path = Path(f"research/trades_{symbol}.csv")

    if not pre_path.exists():
        pytest.skip(f"Pre-migration fixture not found: {pre_path}")
    if not post_path.exists():
        pytest.skip(f"Current trades file not found: {post_path}")

    assert verify(str(pre_path), str(post_path)), (
        f"{symbol}: shared columns diverged from the frozen pre-direction "
        f"snapshot -- the S1 schema migration was supposed to ONLY add "
        f"the 'direction' column, not alter any existing trade data."
    )
