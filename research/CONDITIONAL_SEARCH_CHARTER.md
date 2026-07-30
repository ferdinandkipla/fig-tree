# The Conditional Search — Program Charter

**Written:** 2026-07-25, before any Batch 2 hypothesis is registered,
per this project's own standing discipline: decide the rules while
nothing is at stake.

**Status of this document:** hash-pinned upon commit. Any future change
to this charter must itself be registered and justified in the ledger,
exactly like a hypothesis — see "Guarding the standards themselves"
below. This document does not get quietly renegotiated during a
drought.

---

## 1. What Batch 1 established, and why it's over

Seven hypotheses (M2, H-001 through H-007) tested **unconditional,
single-variable, endogenous** effects: entry timing, session, exit
rule, volatility regime, day-of-week, cross-instrument correlation.
Six kills, one non-edge characterization survival (H-007).

**The diagnosis, stated precisely:** marginal effects in liquid FX at
multi-hour frequencies are the hypothesis family most likely to already
be arbitraged to dust — they're the easiest to find and therefore the
easiest to crowd out. Batch 1 tested the *correct* candidates to clear
first (cheap, well-motivated, no reason to skip them), but a 0/7
tradable hit rate on exactly that family is not yet evidence "no edge
exists for you." It is evidence that no unconditional endogenous edge
survives in the most efficiently priced corner of the accessible
universe. Those are different findings, and this charter exists because
conflating them would be the single biggest strategic error available
at this decision point.

## 2. The theory Batch 2 tests

**If structure survives in this universe at these frequencies, it
survives because it is conditional, cross-sectional, or event-anchored
— hidden in interactions that marginal statistics average away.**

Every Batch 2 hypothesis must invoke one of these three mechanisms
explicitly:
- **Conditional:** an effect that only appears within a specific regime
  defined by another variable (e.g., session effect conditional on
  volatility regime — both marginals already killed individually, but
  their interaction is untested).
- **Cross-sectional:** an effect that depends on the relationship
  between instruments, not any single instrument's own statistics
  (H-007's correlation structure is the seed for this category).
- **Event-anchored:** an effect tied to a specific, structurally
  recurring event (fixing times, rollover, macro release windows) with
  a persistence argument grounded in *why* the effect isn't arbitraged
  away, not just that it's observed.

**"Because the backtest might show it" is no longer an admissible
motivation.** The free, self-enumerating hypotheses are spent. Every
candidate now requires the mechanism memo below before any code runs.

## 3. The mechanism memo — mandatory, sequenced before registration

No Batch 2 hypothesis is registered without a committed mechanism memo.
The memo must state, in this order, committed BEFORE any exploratory
look at the conditioning variable — the same freeze-before-verdict
discipline `research/run_h001.py` used for bin edges, applied one level
upstream to the mechanism itself:

1. **The economic story.** What structural or behavioral pattern is
   being claimed.
2. **The counterparty.** Who is systematically on the other side of
   this trade, and why are they structurally unable or unwilling to
   arbitrage it away (capital constraints, mandate restrictions,
   information asymmetry, transaction cost asymmetry — a real
   mechanism, not "maybe nobody noticed").
3. **The prior** (low / medium / high), with justification tied to (1)
   and (2) — not a vibe.
4. **A per-instrument, per-condition predicted SIGN PATTERN, specific
   enough to be visibly wrong.** This is the hard requirement added to
   this charter beyond the original draft: a memo is not committable if
   its mechanism is vague enough that any result could be read as
   consistent with it. If the mechanism predicts a risk-off effect, the
   memo must state in advance which instruments should show it more
   strongly and which should show it weakly or not at all (e.g., "JPY
   crosses should show this more than a USD-bloc pair, because the
   yen's safe-haven role is the mechanism's carrier") — not "the effect
   should appear, direction unspecified, consistently or however it
   shows up." A memo whose falsification condition is unclear is
   rejected at this stage, before registration, not discovered to be
   unfalsifiable after a kill fails to feel like a kill.

**Sequencing rule:** memo written and committed → THEN registration
(prediction, test design, kill criteria, per H-00X template) → THEN any
data exploration. Reversing this order — looking at the conditioning
variable's behavior before committing the memo's sign predictions — is
the exact failure mode this rule exists to prevent, and it is exactly
as serious a violation as unsealing OOS out of order.

## 4. Candidate sources, in priority order

Priority is **mechanism-cost + data-cost first, compute-cost is ≈0 and
no longer a differentiator** (see Section 6 on the bottleneck shift).

1. **H-007's correlation structure as a conditioning variable.**
   Zero new data. The correlation matrix already exists
   (`research/H-007-correlation-matrix.csv`). Candidates: does a
   session or volatility effect (both killed as marginals) appear
   conditional on the EURUSD-AUDUSD or USDJPY-GBPJPY correlation
   regime? Cheapest possible Batch 2 item — moderate mechanism-writing
   work, zero data cost, zero new compute infrastructure.
2. **Interactions between already-killed marginals.** Session ×
   volatility-regime is the natural first candidate — both marginals
   are dead individually, but a killed marginal can still matter
   conditionally. Zero new data (reuses H-004/H-005's existing null
   sweep). Moderate mechanism cost (must argue why the INTERACTION
   would survive when both marginals didn't).
3. **Published, literature-anchored structural anomalies** (fixing
   times, rollover, macro-release windows). Data cost: LOW to MODERATE
   — release-calendar data is generally free/available, but is a new
   data source requiring its own hash-pinned ingestion, not something
   already in `data/storage/`.
4. **Cross-asset conditioning** (risk-on/off axis via an index or DXY
   proxy). **FLAGGED EXPLICITLY: this is NOT already in the S1
   dataset.** The actual data ingested in S1 is exactly five
   instruments — USDJPY, XAUUSD, GBPJPY, EURUSD, AUDUSD. No index CFD
   was ever pulled (floated as optional during S1 scoping, never
   followed through), and DXY is not a standard MT5 symbol — it would
   require a proxy instrument or an entirely different data source.
   This candidate is GATED on a new, S1-grade data-onboarding event
   (sourcing, ingesting, hash-pinning, cost-caveating) before any
   mechanism memo referencing it can be committed. Do not schedule this
   as if the data already exists.

## 5. Statistical safeguards, extended for the conditional family

**FDR accounting by cell, not by registration.** Session × volatility
is dozens of cells (3 sessions × 3 volatility terciles = 9 cells,
before even multiplying by 5 instruments). The FDR ledger and
`research/fdr_check.py` must be extended to count and correct at the
cell level for any interaction hypothesis — this is the H-002
pseudoreplication lesson, scaled up. A hypothesis with 9 cells tested
per instrument is not "1 test," it's 9, for correction purposes.

**Conditional survival bar, stricter than Batch 1's:**
1. Effect present in TRAIN.
2. Sign pattern matches the memo's PRE-COMMITTED prediction per
   instrument/condition — not blanket cross-instrument consistency.
   A risk-off effect should differ in strength between a JPY cross and
   a USD-bloc pair; the memo predicts this difference in advance, and
   the verdict checks the prediction, not "did something happen
   somewhere."
3. Seed-to-seed dispersion check (from H-002 onward), applied per cell.
4. Cost +50% stress survival.
5. ≥30 OOS trades in each cell counted toward the claim.

## 6. The bottleneck has changed — track it explicitly

"Near-zero marginal cost per adjudication" was true when hypotheses
enumerated themselves and features were endogenous (compute-bound:
H-005 through H-007 each took about a day once registered). **Both
conditions just expired.** Batch 2's real cost structure:

- **Mechanism cost:** days-to-weeks of reading and reasoning per
  candidate to write a defensible memo. Cannot be parallelized or
  automated without degrading into rationalization.
- **Data cost:** cross-asset/event-anchored candidates require
  S1-grade onboarding (sourcing, hashing, ledgering, cost-caveating) —
  weeks, not a fetch call.
- **Compute cost:** ≈0, as it has been since M2.

**Scoreboard metric shifts accordingly: registered mechanisms/month,
not adjudications/month.** Adjudication is now the cheap tail of the
process, not the bottleneck. Track mechanism-memo-commit-date
separately from adjudication-date in the FDR ledger, so a future audit
of this phase sees the true bottleneck (e.g., a memo sitting committed
for two weeks awaiting data) rather than misreading adjudication itself
as slow.

**The failure mode shifts too.** When compute was the constraint, the
risk was under-testing. Now that mechanism-writing is the constraint,
the risk is **memo inflation** — plausible-sounding stories
reverse-engineered to justify testing whatever data happens to already
be on hand. Defenses: (a) the memo-freeze sequencing in Section 3, (b)
the sign-specificity requirement in Section 3, (c) the guard below.

## 7. Guarding the standards themselves

Nothing in Batch 1's machinery protects the STANDARDS from drifting
after a long drought — the FDR ledger guards the statistics, not the
definition of "survives." This charter, `research/registry/FDR_LEDGER.md`,
and any future evidence-standards document are hash-pinned upon commit.
Any change to what counts as a survival, a kill, or an admissible
mechanism must itself be registered and justified in the ledger, with
its own commit hash, before it takes effect — the same discipline
applied to every hypothesis, now applied to the rules that judge
hypotheses.

## 8. Objectives and cap

- Adjudicate 8-12 conditional/cross-sectional/event hypotheses.
- Cap: 3 open registrations at any time (unchanged from Batch 1
  practice).
- Produce, at the end, one of two documented conclusions — see
  `research/S1_STOPPING_RULE.md` for the full branch specification,
  committed alongside this charter.
