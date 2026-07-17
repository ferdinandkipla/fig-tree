# data/mt5_connector.py
import MetaTrader5 as mt5

def connect() -> bool:
    if not mt5.initialize():
        print(f"[MT5] Failed to initialize. Error: {mt5.last_error()}")
        print("[MT5] Ensure MT5 terminal is open and logged in.")
        return False
    acc = mt5.account_info()
    print(f"[MT5] Connected | Account: {acc.login} | Server: {acc.server}")
    print(f"[MT5] Balance: {acc.balance} {acc.currency}")
    return True

def disconnect():
    mt5.shutdown()
    print("[MT5] Disconnected.")

def get_symbol(symbol: str) -> bool:
    info = mt5.symbol_info(symbol)
    if info is None:
        print(f"[MT5] Symbol '{symbol}' not found. Check Market Watch.")
        return False
    if not info.visible:
        mt5.symbol_select(symbol, True)
    return True