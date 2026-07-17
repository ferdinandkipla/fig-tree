# risk/sizing.py
from core.instruments import get_meta

def position_size(capital: float, risk_pct: float,
                  entry: float, stop: float, symbol: str) -> float:
    meta         = get_meta(symbol)
    risk_amount  = capital * risk_pct
    stop_pips    = abs(entry - stop) / meta["pip_size"]
    if stop_pips == 0:
        return 0.0
    risk_per_lot = stop_pips * meta["pip_value"]
    return round(risk_amount / risk_per_lot, 4)