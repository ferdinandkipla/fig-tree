# execution/costs.py
# FIX: Instrument-aware — correct pip_size per symbol
# FIX (cost model v2, Commit 1/2): total_cost() now scales by position
# size. Previously returned a flat one-standard-lot cost regardless of
# actual trade size, while pnl_gross correctly scaled by size --
# under-costing large positions, over-costing small ones. Bug found
# during cost-model-v2 scoping, documented in
# docs/COST_MODEL_V2_PLAN.md Sec 1 and research/COST_MODEL_ERRATA.md.

from core.instruments import get_meta

def total_cost(symbol: str, size: float, slippage_pips: float = 1.0) -> float:
    meta        = get_meta(symbol)
    spread_cost = meta["spread_pips"]  * meta["pip_size"] * meta["pip_value"] * size
    slip_cost   = slippage_pips        * meta["pip_size"] * meta["pip_value"] * size
    return spread_cost + slip_cost