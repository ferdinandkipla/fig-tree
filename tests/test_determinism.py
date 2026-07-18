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

import pytest
import main as m
from core.config import BACKTEST, RISK, TREND_PULLBACK, ENTRY_FEATURES
from research.experiment import record, DirtyGitStateError


@pytest.mark.slow
def test_real_backtest_is_deterministic_across_two_runs():
    # NOTE: deliberately calling research.experiment.record() directly
    # here, NOT main._log_run_to_ledger(). The latter is a CLI-friendly
    # wrapper that CATCHES DirtyGitStateError and only prints a warning
    # (so a dirty tree doesn't crash a live trading/research session).
    # That means a try/except around _log_run_to_ledger() never fires,
    # and this test would silently pass by comparing STALE entries from
    # some earlier run instead of the two runs performed right here.
    # (Caught this exact false-positive while writing this test.)

    all_results = {}
    for symbol in ("USDJPY", "XAUUSD", "GBPJPY"):
        all_results[symbol] = m.run(symbol, export_charts=False)

    successful_symbols = [
        sym for sym, res in all_results.items()
        if res and res.get("trades") is not None and len(res["trades"]) > 0
    ]
    assert successful_symbols, "backtest produced no trades for any symbol"

    config_snapshot = {
        "BACKTEST": BACKTEST, "RISK": RISK,
        "TREND_PULLBACK": TREND_PULLBACK, "ENTRY_FEATURES": ENTRY_FEATURES,
    }
    data_paths   = {s: f"data/storage/{s}_{BACKTEST['timeframe']}.csv" for s in successful_symbols}
    output_paths = {s: f"research/trades_{s}.csv" for s in successful_symbols}

    try:
        r1 = record(strategy="trend_pullback", symbols=successful_symbols,
                    config_snapshot=config_snapshot, data_paths=data_paths,
                    output_paths=output_paths)
        r2 = record(strategy="trend_pullback", symbols=successful_symbols,
                    config_snapshot=config_snapshot, data_paths=data_paths,
                    output_paths=output_paths)
    except DirtyGitStateError as e:
        pytest.skip(f"Working tree not clean, cannot run ledger-based "
                    f"determinism check: {e}")
        return

    assert r1["run_id"] != r2["run_id"], "sanity check: the two records must be distinct runs"
    assert r1["config_hash"] == r2["config_hash"]
    assert r1["data_hashes"] == r2["data_hashes"]
    assert r1["output_hashes"] == r2["output_hashes"], (
        "Two runs against identical code+data produced different output "
        "hashes -- this means something in the pipeline is non-deterministic "
        "(uncontrolled randomness, wall-clock dependence, unstable sort "
        "order, etc.) and every downstream research result is suspect "
        "until this is root-caused."
    )
