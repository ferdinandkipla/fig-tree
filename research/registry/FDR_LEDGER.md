# FDR Ledger

Running record of every hypothesis registered and adjudicated, kept for
one purpose: **so that if/when a hypothesis survives, the decision to
accept it accounts for how many tests preceded it, not just that one
test's p-value in isolation.**

Built now, deliberately, at 4/4 kills with zero survivals -- per the
project's own standing principle (see H-001's registration and every
subsequent one): decide correction rules while no result is at stake,
not after something looks exciting.

## Why this matters even with zero survivals so far

Testing N independent hypotheses at alpha=0.05 each, if the true effect
is zero everywhere, produces an EXPECTED false-positive count of
`N * 0.05`. At N=4, that's 0.2 expected false positives -- consistent
with observing zero, and not remarkable on its own. The ledger exists
so this arithmetic is checked every time, not just when a result feels
surprising.

**This project's hypotheses are not all independent in the naive
sense** -- H-002 and H-004 both test session structure (different
granularity/universe), and both used the SAME underlying null-model
seeds. Treat closely related hypotheses (same mechanism family) as a
sub-family for correction purposes, not as fully independent draws.
See the Family column below.

## Ledger

| ID | Family | Registered | Status | Key stat | Instruments tested | Notes |
|---|---|---|---|---|---|---|
| H-001 | pullback-depth (entry anatomy) | commit `3d2f41a` | KILLED | best bin != deepest quartile on 2/3 | USDJPY, XAUUSD, GBPJPY | TRAIN only |
| H-002 | session structure | commit `3ac150f` | KILLED | p<0.05 on 1/3 (GBPJPY), but effect < seed noise | USDJPY, XAUUSD, GBPJPY | H4, long-only null |
| H-003 | exit-rule value (time-exit) | commit `0bf8102` | KILLED | (A-B) <= 0 on 3/3 (opposite of predicted direction) | USDJPY, XAUUSD, GBPJPY | TRAIN only, real-strategy Arm A/B |
| H-004 | session structure | commit `8ec8bf9` | KILLED | p<0.05 on 2/5 (USDJPY, GBPJPY), both effect < seed noise | USDJPY, XAUUSD, GBPJPY, EURUSD, AUDUSD | 1H primary + H4 secondary, signed null |
| H-005 | volatility regime (NEW family) | commit `391e6d5` | KILLED | best tercile inconsistent (T1 on 2/5, T3 on 3/5); p=0.006 on GBPJPY clears FDR threshold but effect < seed noise | USDJPY, XAUUSD, GBPJPY, EURUSD, AUDUSD | 1H, signed null, ATR-at-entry terciles; analysis-only on H-004's existing data |
| H-006 | day-of-week (NEW family) | commit `3b2e4c8` | KILLED | Thursday best on 4/5 (near-consistent, not unanimous); 0/5 clear the dispersion check | USDJPY, XAUUSD, GBPJPY, EURUSD, AUDUSD | 1H, signed null, day-of-week buckets; analysis-only on H-004's existing data |

**Total hypotheses adjudicated: 6. Survivals: 0. Sub-families: 5**
(pullback-depth: 1, session-structure: 2, exit-rule: 1, volatility-regime: 1, day-of-week: 1).

**Note on the dispersion check's track record:** 4 of 6 adjudicated
hypotheses (H-002, H-004, H-005, H-006) have had at least one instrument
clear a raw or FDR-adjusted p-value threshold that the seed-to-seed
dispersion check then correctly identified as noise, not signal. H-006
also produced the closest-to-consistent directional pattern seen yet
(Thursday best on 4/5 instruments) -- and the dispersion check still
correctly overrode it. This is the strongest empirical argument yet for
treating the dispersion check as mandatory infrastructure, not an
optional refinement, in every future pooled-seed permutation test this
registry runs.

**Search budget status (per `research/S1_INTERIM_FINDING_5_KILLS.md`):**
Budget item 2 of 3 (day-of-week) complete. One remaining before the
committed re-evaluation point: cross-instrument correlation OR
momentum/mean-reversion at alternate horizons.

## Correction rule for the NEXT hypothesis (pre-committed, not decided after seeing a result)

When hypothesis #5 (or any future hypothesis) is adjudicated:

1. **If it's a NEW mechanism family** (not session/pullback/exit-rule):
   treat it as test #5 in the overall registry. A raw p<0.05 is
   necessary but not sufficient -- report the Benjamini-Hochberg
   adjusted threshold for rank-1-of-5 (`0.05 * 1/5 = 0.01`) alongside
   the raw p-value, and require the seed-to-seed dispersion check
   (H-002/H-004's template) to also pass, regardless of family.

2. **If it's a session-structure hypothesis** (3rd in that sub-family):
   apply the SAME correction within the sub-family (2 prior tests,
   both killed) -- a 3rd session test surviving after 2 kills demands
   a materially lower p-value than 0.05, not just a numerically
   different instrument set. Consider whether a 3rd session-structure
   registration is even warranted given H-002 and H-004's convergent
   kills, versus moving to a genuinely different mechanism.

3. **Never accept a hypothesis on raw p<0.05 alone** once N>=4 in the
   registry, regardless of family. This ledger's existence is the
   enforcement mechanism -- update it BEFORE reading the next
   hypothesis's p-value, not after, so the correction can't be
   quietly skipped because a result "looks clean."

## Maintenance

Update this ledger's table immediately after every hypothesis's STATUS
is logged in its own `research/registry/H-XXX.md` file -- same commit,
or the very next one. A hypothesis is not considered closed until both
its own registry file AND this ledger reflect its final status.
