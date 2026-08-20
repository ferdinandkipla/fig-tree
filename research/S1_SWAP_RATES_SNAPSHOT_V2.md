# S1 Swap Rate Snapshot (v2 — supersedes the 2026-07-24 snapshot)

**Pulled:** 2026-08-20, via live MT5 terminal (account 52974506, server
`ICMarketsSC-Demo`), during the US500 onboarding session
(`research/mt5_availability_check.py`). Formal decision recorded below
on 2026-08-20: this is now the **permanent, accepted baseline**, not a
placeholder pending future re-sourcing.

## Rates (per standard lot, broker's native units)

| Symbol | swap_long | swap_short | 2026-07-24 value | drift |
|---|---:|---:|---:|---|
| USDJPY | 8.131 | -16.888 | 8.752 / -17.618 | yes |
| XAUUSD | -57.294 | 39.452 | -53.763 / 36.931 | yes, more extreme |
| GBPJPY | 11.399 | -22.900 | 12.143 / -23.758 | yes |
| EURUSD | -8.276 | 1.533 | -8.166 / 1.454 | yes |
| AUDUSD | -2.546 | -4.442 | -2.231 / -4.739 | yes |

All five drifted since the prior snapshot (expected — swap rates track
interest-rate differentials and get revised periodically by the
broker). XAUUSD's long/short asymmetry did not shrink, it became
slightly *more* pronounced.

## Decision: demo-sourced accepted as the permanent baseline (2026-08-20)

**Prior framing (2026-07-24 snapshot, `execution/costs.py`'s original
header comment) treated this as provisional, pending re-sourcing from
"a verified, non-demo source."** That framing assumed such a source
exists and simply hadn't been checked yet. It was checked this session
and **does not exist for this broker**: IC Markets' own published
material (`icmarkets.com/global/en/trading-pricing/swap-rates`, the
Forex and Commodity Product Specification Sheets) states swap rates and
spreads as "Variable" and directs traders to their own platform's
Specification window — i.e., MT5 itself is the broker's stated source
of truth, live or demo, not a separate published table. There is
nothing external to cross-check the exact number against.

Given that, the original gate ("re-source from a verified, non-demo
source") is not achievable via public sourcing and is being replaced
with a weaker but honest standard:

1. **Demo-sourced numbers are accepted as the permanent baseline**,
   refreshed periodically (this document, superseding 2026-07-24's),
   not held as a placeholder awaiting a resolution that isn't coming.
2. **Cross-checked for plausibility, not exact-value verification**,
   against two independent data points found this session:
   - A different broker (Afterprime) publishes XAUUSD swap rates of
     long −73.607 / short +30 per standard lot — a different exact
     number (different broker, different terms), but the same large,
     negative-long/positive-short asymmetry pattern seen here. This
     supports the *pattern* as a real, current gold-market/rate-
     environment feature, not an IC-Markets-demo-specific artifact.
   - IC Markets' own published material independently confirms the
     Wednesday-triple-swap convention already coded in
     `execution/rollover.py`, unprompted by this specific check —
     a small but genuine independent cross-check that this project's
     rollover assumption matches the broker's actual stated rule.
3. **The demo-vs-live distinction remains genuinely open** and is not
   resolved by anything in this document. If a live account (IC
   Markets or otherwise) ever becomes available, a same-day
   demo-vs-live comparison would be strictly better evidence than
   anything sourced here and should supersede this snapshot.

## Sign convention

Positive = credited to the account, negative = charged. XAUUSD's
asymmetry (long charged heavily, short credited) is large — see the
cross-check above for why this is treated as plausible rather than
suspicious, though "plausible" is not the same bar as "verified."

## Consequence for `research/registry/FINDING-xauusd-swap-sensitivity-h001.md`

That document's Section 4 falsifiable prediction — that the pattern
should shrink or vanish if the verified rate turns out smaller or more
symmetric — remains open and untested by this update. This snapshot
makes the number *fresher and cross-checked for plausibility*, not
*verified* in the sense that finding's gate originally asked for. The
gate itself has been reframed (see Decision above) rather than closed;
any future re-statement of that finding's Section 4 gate should point
here, not imply resolution.

## When this becomes load-bearing

Per the S1 redesign doc: swap costs only become blocking "if a
hypothesis's edge is small enough that the +50% cost stress verdict
could flip on swap." Cost model v2 (now live) already integrates these
rates into every relevant adjudication — see
`docs/PROJECT_STATE.md` §4a for the full re-verification record.
