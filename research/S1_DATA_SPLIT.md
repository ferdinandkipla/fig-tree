# S1 Data Split Declaration

**Committed:** 2026-07-19, before any S1 analysis, per S0's own charter
rule (splits/thresholds are pre-registered, not chosen after looking).

## Split boundary

**TRAIN: 2019-01-01 -> 2022-01-01**
**OOS:  2022-01-01 -> 2025-01-01 (or later, per instrument's available history)**

This is the SAME boundary used throughout S0 (H-001, H-002, H-003).
Not re-sealed for S1. Reasoning for keeping it unchanged rather than
picking a new split:

1. **Consistency across the hypothesis-family template.** H-001's
   worked-example status (see `research/registry/TEMPLATE.md`) depends
   on future hypotheses being able to compare against S0's TRAIN
   results on an apples-to-apples window. Changing the boundary now
   would break that comparability for no evidentiary gain.
2. **No S0 hypothesis ever unsealed OOS.** There is no risk of the
   TRAIN/OOS split having been "used up" by peeking -- every S0 kill
   (H-001, H-002, H-003) was decided on TRAIN alone. The boundary is as
   clean now as when it was first set.
3. **New instruments/timeframes inherit the same calendar boundary**,
   not a proportionally-equivalent one. EURUSD, AUDUSD, and any index
   CFD added in S1 use the identical 2019-01-01/2022-01-01/2025-01-01
   dates as USDJPY/XAUUSD/GBPJPY, not a recalculated split based on
   each instrument's own history length. This keeps cross-instrument
   comparisons (the consistency criterion every S0 hypothesis's kill
   criteria depended on) valid without a per-instrument correction
   factor.

## Applies to

- All new instruments added in S1 (EURUSD, AUDUSD, index CFD if
  available).
- The 1H timeframe ingestion for USDJPY/XAUUSD/GBPJPY.
- Any hypothesis registered against S1 data, unless that specific
  registration explicitly re-seals with its own stated reasoning (per
  the caution above: re-sealing requires documented justification, not
  silent drift).

## If a future registration needs a different split

Per the charter's own rule: document why in that specific registration
file, get it committed BEFORE any binning/analysis, and note the
deviation from this file's default explicitly. Silent, undocumented
split changes between hypotheses are exactly the kind of drift
pre-registration exists to prevent.
