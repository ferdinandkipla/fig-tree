"""
research/mt5_us500_data_check.py

Follow-up to mt5_availability_check.py. That script found "US500" in
the symbol list with bid=0.0 -- a zero bid usually just means the
symbol isn't actively streaming yet (not added to Market Watch with
live quotes), not that it lacks data. This script confirms the thing
that actually matters for backtesting: does US500 have usable
historical H4/1H bars over a range comparable to the existing S1
dataset (2019-2025)?

Read-only. Writes nothing, ingests nothing permanently -- just reports
what's available so an onboarding decision can be made with real
information instead of a guess.

Usage:
    python research/mt5_us500_data_check.py
"""

import sys
from datetime import datetime, timezone

try:
    import MetaTrader5 as mt5
except ImportError:
    print("MetaTrader5 package not installed.")
    sys.exit(1)

SYMBOL = "US500"


def main():
    if not mt5.initialize():
        print(f"initialize() FAILED: {mt5.last_error()}")
        sys.exit(1)

    # Symbol must be selected (added to Market Watch) for tick/rate data
    # to populate -- this is the likely reason bid=0.0 showed up before.
    selected = mt5.symbol_select(SYMBOL, True)
    print(f"symbol_select('{SYMBOL}', True) -> {selected}")

    info = mt5.symbol_info(SYMBOL)
    if info is None:
        print(f"{SYMBOL} still not found after select. Stopping.")
        mt5.shutdown()
        sys.exit(1)

    print(f"description: {info.description}")
    print(f"currency_base / profit / margin: "
          f"{info.currency_base} / {info.currency_profit} / {info.currency_margin}")
    print(f"digits: {info.digits}, point: {info.point}")
    print(f"trade_mode: {info.trade_mode} (0=disabled, check this isn't 0)")
    print(f"bid/ask after select: {info.bid} / {info.ask}")
    print()

    # Pull a small recent sample first (fast sanity check)
    print("--- Recent H4 bars (last 10) ---")
    recent = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H4, 0, 10)
    if recent is None or len(recent) == 0:
        print(f"No recent H4 bars returned. Error: {mt5.last_error()}")
    else:
        for bar in recent[-5:]:
            ts = datetime.fromtimestamp(bar['time'], tz=timezone.utc)
            print(f"  {ts}  O={bar['open']} H={bar['high']} L={bar['low']} C={bar['close']}")

    # Now check how far back history actually goes -- this is the real
    # question for matching the existing 2019-2025 S1 window.
    print()
    print("--- History depth check ---")
    for probe_date, label in [
        (datetime(2019, 1, 1, tzinfo=timezone.utc), "2019-01-01"),
        (datetime(2021, 1, 1, tzinfo=timezone.utc), "2021-01-01"),
        (datetime(2023, 1, 1, tzinfo=timezone.utc), "2023-01-01"),
    ]:
        bars = mt5.copy_rates_from(SYMBOL, mt5.TIMEFRAME_H4, probe_date, 5)
        if bars is None or len(bars) == 0:
            print(f"  From {label}: NO DATA (error: {mt5.last_error()})")
        else:
            first_ts = datetime.fromtimestamp(bars[0]['time'], tz=timezone.utc)
            print(f"  From {label}: data starts returning at/near {first_ts}")

    print()
    print("Compare the earliest date that returns real bars above against")
    print("the existing S1 window start (2019-01-01, core/config.py")
    print("BACKTEST['start']). If US500's history is materially shorter,")
    print("that's a real constraint on any hypothesis conditioning on it --")
    print("decide whether to truncate the whole 5-instrument comparison to")
    print("match, or treat it as a separate, shorter-window candidate.")

    mt5.shutdown()


if __name__ == "__main__":
    main()
