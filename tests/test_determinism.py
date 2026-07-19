# tests/test_determinism.py
#
# M1 stability test (orthogonal to tests/test_simulator.py's correctness
# test): run the REAL backtest against REAL cached data twice, and
# confirm the ledger's own output_hashes match. Consumes research
# experiment.py's ledger rather than doing an ad-hoc CSV diff — if the
# ledger is built right, this check is this short.
#
# NOTE: this test calls main.run() for all 3 symbols twice and logs
# both runs to the ledger, so it is slower than a unit test and touches
# the real data cache. It requires a clean git tree (same rule as any
# other ledger-logging run) and MetaTrader5 stubbed for import (see
# tests/test_simulator.py for the same workaround + the reason it's
# needed).

import sys
import types

if "MetaTrader5" not in sys.modules:
    _mt5_stub = types.ModuleType("MetaTrader5")
    _mt5_stub.TIMEFRAME_H4 = 16388
    sys.modules["MetaTrader5"] = _mt5_stub

import time
import pytest
import main as m
from strategies.trend_pullback.strategy import TrendPullbackStrategy
from core.config import BACKTEST, SEED
from data.loader import cache_path
from research.experiment import record, DirtyGitStateError


def _run_full_pipeline_and_log():
    """Runs the REAL backtest for all 3 symbols (regenerating trades_*.csv
    from scratch) and logs one ledger entry. Returns the ledger entry."""
    strategy = TrendPullbackStrategy()
    all_results = {}
    for symbol in ("USDJPY", "XAUUSD", "GBPJPY"):
        all_results[symbol] = m.run(symbol, export_charts=False, strategy=strategy)

    successful_symbols = [
        sym for sym, res in all_results.items()
        if res and res.get("trades") is not None and len(res["trades"]) > 0
    ]
    assert successful_symbols, "backtest produced no trades for any symbol"

    data_paths   = {s: str(cache_path(s, BACKTEST["timeframe"])) for s in successful_symbols}
    output_paths = {s: f"research/trades_{s}.csv" for s in successful_symbols}

    return record(strategy=strategy.name, symbols=successful_symbols,
                  config_snapshot=strategy.params, data_paths=data_paths,
                  output_paths=output_paths, seed=SEED)


@pytest.mark.slow
def test_real_backtest_is_deterministic_across_two_runs():
    # CRITICAL BUG FOUND IN REVIEW, FIXED HERE: an earlier version of
    # this test called m.run() (the actual backtest) ONCE, then called
    # record() TWICE against that same static, already-produced output.
    # The resulting timestamps were ~10ms apart — nowhere near enough
    # time to run a real H4 backtest over 2019-2025 for 3 instruments —
    # which proved both calls were just re-hashing identical files that
    # already existed. Identical hashes from that setup are a tautology,
    # not evidence of determinism. This is the EXACT failure class the
    # earlier "lucky" dirty-tree runs represented: a check that cannot
    # fail proves nothing.
    #
    # Fixed: the full pipeline (m.run() for all 3 symbols, regenerating
    # trades_*.csv from scratch) now runs TWICE, independently, each
    # followed by its own record() call. A wall-clock gate below asserts
    # the two runs took a realistic amount of time apart, so this test
    # cannot silently regress back into the tautological version.

    t0 = time.monotonic()
    try:
        r1 = _run_full_pipeline_and_log()
        t1 = time.monotonic()
        r2 = _run_full_pipeline_and_log()
        t2 = time.monotonic()
    except DirtyGitStateError as e:
        pytest.skip(f"Working tree not clean, cannot run ledger-based "
                    f"determinism check: {e}")
        return

    run1_duration = t1 - t0
    run2_duration = t2 - t1

    # Anti-regression gate: each full pipeline pass must take at least
    # 1 second. A tautological "log the same output twice" bug would
    # show ~0.00Xs here instead. (Real runs in this environment take
    # several seconds; 1s is a conservative floor, not a tight bound.)
    assert run1_duration > 1.0, (
        f"Run 1 completed in {run1_duration:.4f}s -- too fast to be a real "
        f"3-instrument H4 backtest. This test may have regressed into "
        f"logging pre-existing output instead of actually re-running it."
    )
    assert run2_duration > 1.0, (
        f"Run 2 completed in {run2_duration:.4f}s -- same concern as above."
    )

    assert r1["run_id"] != r2["run_id"], "sanity check: the two records must be distinct runs"
    assert r1["seed"] == r2["seed"] == SEED
    assert r1["config_hash"] == r2["config_hash"]
    assert r1["data_hashes"] == r2["data_hashes"]
    assert r1["output_hashes"] == r2["output_hashes"], (
        "Two INDEPENDENT full pipeline runs against identical code+data "
        "produced different output hashes -- this means something in the "
        "pipeline is non-deterministic (uncontrolled randomness, wall-clock "
        "dependence, unstable sort order, embedded generation timestamps, "
        "etc.) and every downstream research result is suspect until this "
        "is root-caused."
    )
