# Interim Finding: 5 Hypotheses, 4 Mechanism Families, Zero Survivals

**Date:** 2026-07-25
**Status:** Deliberate pause before registering hypothesis #6, per the
project's own standing principle -- decide "continue vs. conclude"
branch criteria now, in writing, while no result is at stake, not
after some future result creates pressure to rationalize a choice.

---

## The scoreboard, stated plainly

| # | Hypothesis | Mechanism family | Verdict |
|---|---|---|---|
| M2 | entries vs. matched-random | entry timing (trend_pullback) | below null p05 on all 3 (later revised: inside band on 2/3 once drift-corrected) |
| H-001 | pullback depth | entry timing (trend_pullback) | KILLED |
| H-002 | session structure | session (H4, 3 instruments) | KILLED |
| H-003 | time-exit value | exit rule (trend_pullback) | KILLED |
| H-004 | session structure | session (1H, 5 instruments) | KILLED |
| H-005 | volatility regime | volatility (new family) | KILLED |

**4 distinct mechanism families tested** (entry-timing/pullback-depth,
session, exit-rule, volatility). **Not 6 independent draws** — H-002
and H-004 are the same family at different granularity, and the M2/
H-001/H-003 trio all concern the single retired `trend_pullback`
strategy. Being honest about this matters for what follows: this is
closer to 4 independent tests of the market itself than 6.

## Is this informative? Yes — but about something narrower than "no edge anywhere"

**What it does support:** no exploitable structure has been found in
entry timing, session-of-day, exit-rule design, or volatility
regime, for these 5 instruments, at H4/1H, under retail-representative
costs, within the 2019-2022 TRAIN window. That is a real, evidenced
claim, not a vague impression — each mechanism was tested with a
pre-registered, falsifiable design and killed on its own merits.

**What it does NOT support:** a conclusion that "this market has no
exploitable structure at any frequency, in any form." Four tested
mechanisms out of an unbounded hypothesis space is meaningful progress,
not exhaustive coverage. The vision-review document's own Part 8
warning applies directly here: declaring "no structure" prematurely,
without a pre-committed budget, is itself a form of the self-deception
this project exists to prevent — just in the opposite direction from
curve-fitting.

## A genuinely encouraging signal, worth stating explicitly

Three of five hypotheses (H-002, H-004, H-005) produced at least one
instrument with a raw or FDR-adjusted "significant" p-value that the
seed-to-seed dispersion check then correctly identified as noise. This
is close to the ~5% false-positive rate a well-calibrated permutation
test should produce by chance across this many (instrument x
hypothesis) comparisons — which is itself evidence the testing
methodology is behaving as designed, not evidence of a broken or
overly conservative test. A pipeline that occasionally produces
false-looking positives, and then correctly identifies and discards
them, is calibrated. A pipeline that never produces any raw signal at
all would be more worth interrogating, not less.

## The branch decision, made now

**Continue, with a stated budget, not open-ended.** Reasoning:
- 4 mechanism families is not yet a large enough sample to declare "no
  structure" with any confidence -- the base rate of how many
  reasonable mechanisms exist to test is not well pinned down, but it
  is almost certainly more than 4.
- The infrastructure cost of testing has been near-zero since M2 (H-004
  and H-005 required zero new simulation). The marginal cost argument
  that justified "kill fast, kill often" applies with equal force to
  "test broadly before concluding."
- No result has created any pressure to stop -- this is exactly the
  condition under which a stopping rule should be set, per the
  project's own repeated practice (H-001's bounded claim, the FDR
  ledger itself).

**Concrete budget, committed now:** test at least 3 more genuinely
distinct mechanism families before any formal "no exploitable
structure in this universe" conclusion is considered. Candidates
already identified and NOT yet tested:
1. Cross-instrument correlation structure (do the 5 instruments'
   random-entry outcomes co-move in a way suggesting shared risk
   factors -- also directly useful groundwork for the portfolio-null
   extension flagged as underweighted in the two-year vision review)
2. Day-of-week effects (a different temporal structure than
   session-within-day)
3. Momentum/mean-reversion at alternate horizons (distinct from the
   already-killed pullback-depth mechanism, which was specific to
   `trend_pullback`'s particular EMA-based definition)

**If all of hypotheses #6, #7, #8 also kill:** at that point (7
independent mechanism families, not just 4), write the formal
"no exploitable structure found in this universe/timeframe/cost
regime" conclusion, and pivot -- per the vision review's own framing --
to either a deliberate regime change (new frequency band, new data
types, a newly-registered search program) or treating the methodology
itself as the project's output of record. That decision does not need
to be made today; today's decision is only that we are not there yet.

**If any of #6-#8 survives:** the FDR-adjusted threshold and mandatory
dispersion check apply exactly as they did to #5 (see
`research/registry/FDR_LEDGER.md`) -- a raw significant result at that
point demands MORE scrutiny, not less, given the accumulating test
count.

## What does NOT change because of this note

- No hypothesis's verdict is revised.
- No OOS data has been examined, or will be as a result of this note.
- The retirement of `trend_pullback` (Phase 2's conclusion) stands
  independent of whether the broader market-structure search continues
  or eventually concludes negatively.
