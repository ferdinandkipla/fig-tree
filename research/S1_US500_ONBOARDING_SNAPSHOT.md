# S1 US500 Onboarding Snapshot

**Pulled:** 2026-08-20T10:20:48.857063+00:00, via live MT5 terminal (account 52974506, server `ICMarketsSC-Demo`, trade_mode=DEMO).

Onboarding event for US500 as the sole risk-on/off cross-asset conditioning proxy, per `research/CONDITIONAL_SEARCH_CHARTER.md` §4 item 4. DXY was surveyed the same session and disqualified for this phase (`research/CONDITIONAL_SEARCH_CHARTER.md` §4a) — only a dated futures contract exists, no continuous instrument, no roll-handling in this codebase.

## Symbol details

```
description: US SPX 500 Index
expiration_time: none reported (0) -- consistent with a non-expiring/continuous CFD, not a dated contract like DXY_U6. Still worth a periodic re-check, not a permanent guarantee.
```

## Files produced

| Timeframe | Path | Rows | Start | End | SHA-256 |
|---|---|---:|---|---|---|
| H4 | `data\storage\US500_16388.csv` | 9879 | 2019-01-02 08:00:00 | 2025-05-30 20:00:00 | `c2c85ed9c86d9d79...` |
| H1 | `data\storage\US500_16385.csv` | 37862 | 2018-12-31 21:00:00 | 2025-05-30 23:00:00 | `cb564088dc89ff41...` |

Full hashes (do not truncate when actually verifying):

```
H4: c2c85ed9c86d9d79797101519542d4445ab1f00397ed691fcb5e76a69a88eb22
H1: cb564088dc89ff41052620c7e76a24d4ee9e5d3621e9c39891868a1fac162ca6
```

## Critical caveats (read before modeling this)

1. **US500 is a broker-quoted CFD on the S&P 500 index, not the exchange-traded index itself or a futures contract.** Broker CFD pricing can differ from the underlying exchange in small ways (spread, occasional feed gaps, weekend/holiday session handling) — same category of caveat already accepted for XAUUSD/GBPJPY/etc. as broker-quoted instruments, not a new risk class for this dataset.
2. **Pulled from a DEMO account** (`ICMarketsSC-Demo`). Same caveat category as `research/S1_SWAP_RATES_SNAPSHOT.md` — verify against a live account if this ever needs to move beyond a research/backtest context.
3. **This is price/OHLC data, not a cost model.** No spread, slippage, or swap terms have been sourced or modeled for US500 here — if any hypothesis ever executes simulated trades on US500 rather than just using it as a conditioning variable for the existing 5 instruments, `core/instruments.py` and `execution/costs.py` need their own US500 entries first, with the same hard-block-on-placeholder discipline used for AUDUSD.
4. **Rollover/expiry check ran and is reported above** — confirm it says 'no expiration reported' before trusting a multi-year single-symbol series. If a future re-pull ever shows an expiration_time appearing, stop and treat it exactly like the DXY_U6 finding: check for a continuous alternative before doing anything else.
5. **This snapshot only covers price data.** It does not itself register any hypothesis, cell structure, or FDR accounting — per the charter, any mechanism memo using US500 still needs its own registration, kill criteria, and cell-level FDR extension (§5 of the charter) before adjudication.
