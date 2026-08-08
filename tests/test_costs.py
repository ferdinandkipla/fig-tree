# tests/test_costs.py
#
# Known-answer validation for execution/costs.py's size-scaling fix
# (cost model v2, Commit 1/2). Per ENGINEERING_STANDARDS.md Sec 2 /
# docs/COST_MODEL_V2_PLAN.md Sec 6.

import pytest
from execution.costs import total_cost


def test_total_cost_scales_linearly_with_size():
    """The core fix: doubling size must double the cost."""
    cost_1x = total_cost("USDJPY", size=1.0)
    cost_2x = total_cost("USDJPY", size=2.0)
    assert cost_2x == pytest.approx(2 * cost_1x)


def test_total_cost_known_value_usdjpy():
    # USDJPY: spread_pips=1.5 (per core/instruments.py fixture used in
    # test_simulator.py), pip_size=0.01, pip_value=9.10, slippage=1.0
    # (default). size=0.0733 (matches test_simulator.py's Trade A).
    cost = total_cost("USDJPY", size=0.0733, slippage_pips=1.0)
    expected = (1.5 * 0.01 * 9.10 + 1.0 * 0.01 * 9.10) * 0.0733
    assert cost == pytest.approx(expected)


def test_total_cost_zero_size_is_zero_cost():
    assert total_cost("USDJPY", size=0.0) == pytest.approx(0.0)


def test_total_cost_default_slippage_matches_explicit():
    assert total_cost("USDJPY", size=1.0) == pytest.approx(
        total_cost("USDJPY", size=1.0, slippage_pips=1.0)
    )
