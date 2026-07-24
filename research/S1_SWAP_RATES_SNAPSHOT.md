# S1 Swap Rate Snapshot

**Pulled:** 2026-07-24, via live MT5 terminal (account 52974506,
server `ICMarketsSC-Demo`), per the S1 long/short redesign's Part 3
recommendation to grab swap/rollover rates in the same session as the
data pull, even though direction-aware cost modeling itself is deferred.

## Rates (per standard lot, broker's native units)

| Symbol | swap_long | swap_short |
|---|---:|---:|
| USDJPY | 8.752 | -17.618 |
| XAUUSD | -53.763 | 36.931 |
| GBPJPY | 12.143 | -23.758 |
| EURUSD | -8.166 | 1.454 |
| AUDUSD | -2.231 | -4.739 |

## Critical caveats (read before ever modeling these)

1. **This is a today-snapshot, not a historical series.** Swap rates
   drift over time (they track interest rate differentials between the
   pair's two currencies, which moved substantially across 2019-2025 --
   near-zero global rates for much of that window, then a steep
   tightening cycle from 2022). Applying today's rate uniformly across
   the entire 2019-2025 backtest window is an approximation, not a
   faithful historical reconstruction. If/when swap costs are modeled,
   this approximation must be stated explicitly in that hypothesis's
   registration, not silently assumed.

2. **Pulled from a DEMO account** (`ICMarketsSC-Demo`). Demo accounts
   can have different swap/spread terms than live accounts at the same
   broker. Verify against a live account's terms before this snapshot
   is used for anything beyond rough magnitude checks.

3. **Sign convention:** positive = credited to the account, negative =
   charged. Note XAUUSD's asymmetry is large and unusual (long charged
   heavily, short credited) -- worth double-checking against IC
   Markets' published contract specifications before trusting the
   magnitude, not just the sign, in any cost-stress test.

## When this becomes load-bearing

Per the redesign doc: swap costs only become blocking "if a
hypothesis's edge is small enough that the +50% cost stress verdict
could flip on swap." Until a signed hypothesis reaches that stage, this
file is reference material, not active cost modeling.
