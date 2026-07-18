# data/loader.py
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
from pathlib import Path
from data.mt5_connector import get_symbol

CACHE_DIR = Path("data/storage")


def cache_path(symbol: str, timeframe) -> Path:
    """
    Single source of truth for the cache filename pattern. Used by both
    fetch() below and research/experiment.py's ledger (via main.py) so
    the two can never silently diverge — a path built in two places
    was exactly the kind of duplication the ledger exists to prevent.
    """
    return CACHE_DIR / f"{symbol}_{timeframe}.csv"


def fetch(symbol: str, timeframe, start: datetime = None, end: datetime = None,
          use_cache: bool = True) -> pd.DataFrame:

    # Cache key = symbol + timeframe only (full history always cached)
    cache_file = cache_path(symbol, timeframe)

    if use_cache and cache_file.exists():
        print(f"[Loader] Cache hit: {cache_file.name}")
        df = pd.read_csv(cache_file, index_col="datetime", parse_dates=True)
    else:
        print(f"[Loader] Fetching {symbol} from MT5...")
        if not get_symbol(symbol):
            return pd.DataFrame()

        full_start = datetime(2019, 1, 1)
        full_end   = datetime(2025, 6, 1)
        rates = mt5.copy_rates_range(symbol, timeframe, full_start, full_end)

        if rates is None or len(rates) == 0:
            print(f"[Loader] No data. Error: {mt5.last_error()}")
            return pd.DataFrame()

        df = pd.DataFrame(rates)
        df["datetime"] = pd.to_datetime(df["time"], unit="s")
        df.set_index("datetime", inplace=True)
        df = df[["open", "high", "low", "close", "tick_volume"]].rename(
            columns={"tick_volume": "volume"}
        )
        df.dropna(inplace=True)

        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(cache_file)
        print(f"[Loader] {len(df)} bars cached → {cache_file.name}")

    # Walk-forward date slicing (works on cache AND live fetch)
    if start is not None:
        df = df[df.index >= pd.Timestamp(start)]
    if end is not None:
        df = df[df.index <  pd.Timestamp(end)]

    print(f"[Loader] {len(df)} bars | "
          f"{pd.Timestamp(start).date() if start else 'start'} → "
          f"{pd.Timestamp(end).date() if end else 'end'}")
    return df