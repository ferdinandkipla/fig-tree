# tests/test_meta_test_count.py
#
# Guards against silent test-collection loss -- the exact failure mode
# this session hit: an ordinary str_replace edit clobbered a test
# function's `def` line, leaving its body as orphaned module-level
# code. It executed at import time without error and pytest reported
# a clean "N passed" -- the test simply vanished from collection
# without any red signal. A green run afterward would have been a lie.
#
# This module uses Python's ast (not a recursive pytest invocation --
# that would be slow and fragile) to count top-level `def test_*`
# functions across every tests/test_*.py file, and compares the total
# against a deliberately, manually maintained expected count.
#
# MAINTENANCE: when a real test is added or removed, EXPECTED_TEST_COUNT
# below must be updated in the SAME commit, by hand, as a deliberate
# acknowledgment of the change -- never auto-computed. The whole point
# is that a silent, accidental change in the count fails this check.

import ast
from pathlib import Path

TESTS_DIR = Path(__file__).parent

# Deliberately maintained. Update by hand when tests are genuinely
# added or removed -- see module docstring.
#
# NOTE ON PARAMETRIZED TESTS: this counts def test_* FUNCTION
# DEFINITIONS via ast, not pytest own collected-item count. A
# parametrize-decorated function with N cases is ONE function
# definition here but N separate items in pytest --collect-only.
# tests/test_schema_migration_s1_direction.py has one parametrized
# function (3 cases), so pytest --collect-only reports 48 total
# while this guards function-count arithmetic totals 46 -- expected,
# not a bug. The guards purpose is catching a function DEFINITION
# silently vanishing (e.g. a clobbered def line), which it does
# correctly regardless of parametrization.
EXPECTED_TEST_COUNT = 50  # +4 tests/test_costs.py, cost model v2 Commit 1


def _count_test_functions_in_file(path: Path) -> int:
    tree = ast.parse(path.read_text(), filename=str(path))
    count = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test_"):
                count += 1
    return count


def test_collected_test_count_matches_expected():
    total = 0
    per_file = {}
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        if path.name == "test_meta_test_count.py":
            continue  # this file's own test doesn't count itself
        n = _count_test_functions_in_file(path)
        per_file[path.name] = n
        total += n

    # +1 for this file's own test_collected_test_count_matches_expected
    total_including_self = total + 1

    assert total_including_self == EXPECTED_TEST_COUNT, (
        f"Collected test-function count is {total_including_self}, expected "
        f"{EXPECTED_TEST_COUNT}. If tests were deliberately added or removed "
        f"this commit, update EXPECTED_TEST_COUNT in "
        f"tests/test_meta_test_count.py by hand to match, as an explicit "
        f"acknowledgment. If this mismatch was NOT expected, a test may "
        f"have been silently lost (e.g. a def-line clobbered by an edit) "
        f"-- investigate per-file counts before changing the constant: "
        f"{per_file}"
    )
