# execution/costs.py
# FIX: Instrument-aware — correct pip_size per symbol

from core.instruments import get_meta

def total_cost(symbol: str, slippage_pips: float = 1.0) -> float:
    meta        = get_meta(symbol)
    spread_cost = meta["spread_pips"]  * meta["pip_size"] * meta["pip_value"]
    slip_cost   = slippage_pips        * meta["pip_size"] * meta["pip_value"]
    return spread_cost + slip_cost