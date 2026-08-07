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

| H-007 | cross-instrument correlation (NEW family, different evidentiary form) | commit `dd4e58f` | PREDICTION SURVIVES (not an edge finding -- see caveat in H-007.md) | mean pairwise \|corr\|=0.324 < 0.5 threshold; EURUSD-AUDUSD at 0.552 is a flagged exception | USDJPY, XAUUSD, GBPJPY, EURUSD, AUDUSD | H1, TRAIN only, direct return-correlation matrix |

**Total hypotheses adjudicated: 7. Kills: 6. Prediction survivals: 1 (H-007, a characterization result, not an edge). Sub-families: 6.**

## Batch 2 / Phase 4 (Conditional Search) -- chartered `82a4e29`

| ID | Family | Registered | Status | Cells | Notes |
|---|---|---|---|---|---|
| H-008 | thin-session x high-volatility interaction (NEW family, first Batch 2 test) | `3e8b155`, amended `b8a8794`, adjudicated this commit | **KILLED** | 5 (one per instrument, tokyo-high-vol-tercile vs rest); corrected 3-vs-2 grouping (EURUSD/XAUUSD/GBPJPY thin vs USDJPY/AUDUSD home) | Reused H-005's frozen ATR tercile edges exactly. GBPJPY's p=0.0005 dies on seed-dispersion (same pattern as H-005's GBPJPY p=0.006) -- 0/3 required cells clear all conditions. See `research/registry/H-008.md` STATUS section. |
| H-009 | month-end proximity x high-volatility interaction | `aa58168`, adjudicated this commit | **KILLED** | 1 primary (pooled across instruments); quarter-end margin and low/mid-tercile arm non-adjudicating | Unambiguous kill: p=0.8375, effect within seed noise, AND wrong sign (continuation not reversion) -- three independent kill triggers, not a borderline dispersion call. Quarter-end margin directionally correct (irrelevant to verdict). See `research/registry/H-009.md` STATUS section. |

**Total hypotheses registered across both batches: 9. Batch 1 adjudicated: 7 (6 kills, 1 characterization survival). Batch 2: 2 registered, 2 adjudicated (2 kills), plus 1 documented no-candidate. Total kills so far: 8/9 adjudicated. Batch 2 progress: 2/8-12 budgeted adjudicated, 0 survivors.**

**Note on GBPJPY (pattern, not incident):** GBPJPY has now produced
raw-significant p-values that die on the seed-to-seed dispersion check
TWICE -- H-005 (p=0.006) and H-008 (p=0.0005). Both times the effect
size was smaller than the dispersion generated purely by which random
bars a given seed happened to sample. This instrument appears prone to
generating noise that looks like signal in this pipeline more readily
than the other four. Consequence for future work: any mechanism memo
predicting an effect specifically on GBPJPY should expect the
dispersion check, not the raw p-value, to be the binding test -- and
any future GBPJPY survival of that check deserves extra scrutiny before
being taken at face value, precedent-adjusted for this instrument's
track record.

**Note on per-cell accounting:** `research/fdr_check.py` currently counts
registered hypotheses (files), not cells. The Conditional Search charter
(`research/CONDITIONAL_SEARCH_CHARTER.md`) requires FDR correction by
CELL for interaction hypotheses, since a single registration like H-008
defines multiple comparisons (5 cells). This extension is not yet built.
H-008 is registered so the sequencing (memo -> registration) is on
record, but it cannot be adjudicated until the per-cell harness exists
and is validated on a known-answer case, per `ENGINEERING_STANDARDS.md`
§2.

## RE-EVALUATION POINT REACHED (2026-07-25)

Per `research/S1_INTERIM_FINDING_5_KILLS.md`'s committed budget (test
>=3 more distinct mechanism families before any "no exploitable
structure" conclusion), all three items are now complete:
day-of-week (H-006, killed), cross-instrument correlation (H-007,
survived as characterization, not edge). Combined with H-005
(volatility, killed), that is 7 mechanism-family/market-structure
tests total, 4 originally + 3 budgeted, with ZERO edge findings and
one useful portfolio-groundwork measurement.

**This is the deliberate decision point the interim finding committed
to reaching.** Per that document's own framing: do not register
hypothesis #8 by momentum. A conscious continue/conclude decision
should be made and written down before further hypothesis work
proceeds.

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
