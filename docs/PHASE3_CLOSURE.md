# PHASE3_CLOSURE — Decision Record: Continue/Conclude

**Committed:** 2026-08-03 · **Decision point reached at:** `3b4a84f`
**Decision executed (implicitly, via charter + memo commits):** `82a4e29`, `2b04b66`
**This document:** the explicit decision record `DEVELOPMENT_WORKFLOW.md` §4
requires — strategic decisions are committed documents, not chat artifacts
or inferred from commit archaeology.

## Decision

**Phase 3 (Batch 1, unconditional marginal search) is CLOSED — as
complete, not as terminated.** The committed 3-item re-evaluation budget
(`S1_INTERIM_FINDING_5_KILLS.md`) was fulfilled: day-of-week (H-006,
killed) and cross-instrument correlation (H-007, characterization
survival) both adjudicated, joining volatility regime (H-005, killed).
Seven hypotheses total, six kills, one non-edge characterization. Zero
integrity violations across all seven.

**The project CONTINUES into Phase 4 (Conditional Search)**, under the
charter and stopping rule committed at `82a4e29`.

## Reasoning (per the strategic review)

Batch 1 exhausted a specific, narrow hypothesis family: unconditional,
single-variable, endogenous-only effects on the most liquid, most
efficiently-priced corner of the accessible universe. A 0/7 tradable hit
rate there is real information about that family — it is not yet
evidence that no exploitable structure exists for this project at any
frequency or conditioning depth. Conditional/interaction effects are
harder to find and harder to arbitrage away; they were never tested.
Continuing is the correct next step because the untested hypothesis
space (interactions, cross-sectional conditioning, event-anchored
effects) is genuinely different from the one just exhausted, not a
retry of it.

H-007's survival as a characterization result (not an edge) is treated
as a first-class input to Phase 4, not a footnote — its correlation
structure seeds cross-instrument conditioning candidates once cross-asset
data is properly onboarded.

## What continuing required, and what was done before continuing

Per `RESEARCH_PROGRAM.md` §5, a continuation is legitimate only under a
committed charter. In order:

1. `82a4e29` — Conditional Search charter + stopping rule committed
   BEFORE any Batch 2 hypothesis was registered or explored. Adds
   sign-specificity requirement to the mechanism-memo spec, FDR-by-cell
   accounting, cost-to-verdict priority ordering (zero-new-data
   interactions first), and both stopping-rule branches pre-specified.
2. `2b04b66` — H-008 mechanism memo (thin-session x high-volatility
   interaction) committed BEFORE any exploratory look at the conditioning
   variable, per the charter's own sequencing rule.

The sequencing discipline (charter before memo, memo before look) held.

## Outstanding engineering debt at this decision point

Per `PROJECT_STATE.md` §6, four items were flagged. Status verified
directly against the repo at this commit:

| Item | Status |
|---|---|
| Re-canonicalize trade-CSV hashes (direction column) | DONE (`25db12b`) |
| Migration verifier script | DONE (`research/verify_schema_migration.py`) |
| Cost model v2 (swap integration) | **NOT DONE** |
| AUDUSD real contract specs (replace 1.2-pip placeholder) | **NOT DONE** |

**Consequence for Phase 4:** the two incomplete items are cost-model
items, not correctness-of-kill items — placeholder/simplistic costs only
ever make a kill MORE likely, never manufacture a false survival. It is
therefore acceptable to proceed with Batch 2 KILL adjudications under
the current cost model. **It is NOT acceptable to ACCEPT any Batch 2
hypothesis under the current cost model.** Every Batch 2 registration
must carry this caveat explicitly (see H-008 registration). Per
`RESEARCH_PROGRAM.md` §6, cost model v2 and real AUDUSD specs are
mandatory prerequisites before any acceptance, full stop.

## Provenance

This document formalizes a decision that was already executed in
substance by `82a4e29` and `2b04b66`; it exists so a future session does
not have to infer "continue" from commit archaeology, per
`AI_ONBOARDING.md`'s own standing instruction to prefer explicit decision
records over inferred ones.
