# core/instruments.py
INSTRUMENT_META = {
    "USDJPY": {
        "pip_size":    0.01,
        "pip_value":   9.10,
        "spread_pips": 1.5,
        "sessions":    ["tokyo", "london", "new_york"],
    },
    "GBPJPY": {
        "pip_size":    0.01,
        "pip_value":   9.10,
        "spread_pips": 2.5,
        "sessions":    ["london", "new_york"],
    },
    "XAUUSD": {
        "pip_size":    0.10,
        "pip_value":   1.00,
        "spread_pips": 3.0,
        "sessions":    ["london", "new_york"],
    },
    "EURUSD": {
        "pip_size":    0.0001,
        "pip_value":   10.00,
        "spread_pips": 1.0,
        "sessions":    ["london", "new_york"],
    },
}

SESSION_HOURS = {
    "tokyo":    (0,  9),
    "london":   (7,  16),
    "new_york": (13, 22),
}

def get_meta(symbol: str) -> dict:
    if symbol not in INSTRUMENT_META:
        raise ValueError(f"[Instruments] '{symbol}' not in INSTRUMENT_META. Add it first.")
    return INSTRUMENT_META[symbol]