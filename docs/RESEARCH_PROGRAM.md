# RESEARCH_PROGRAM

**Scope:** research philosophy, evidence standards, hypothesis registry
summary, and the terms for any future search. Status lives in
`PROJECT_STATE.md`; this file changes rarely, `PROJECT_STATE.md` changes
often.

## 1. Philosophy

- Hypothesis before mechanics. No code is written for an unregistered
  idea.
- Kill fast, kill often. A clean kill is a successful outcome and is
  documented with the same care as an acceptance.
- Pre-registration is binding: hypothesis, prediction (direction and
  instrument pattern), test, and adjudication criteria are committed
  before results are seen.
- Null models are mandatory and must be matched (frequency) and
  drift-corrected (signed). Results are judged against the null band,
  not against zero.

## 2. Minimum evidence standards (unchanged, mandatory)

An effect is accepted only if ALL hold:
1. ≥ 30 out-of-sample trades.
2. Effect direction consistent across instruments (or, for conditional
   effects, consistent with the mechanism's own predicted per-instrument
   pattern — see §5).
3. Survives a cost +50% stress test.

Plus FDR control across the registry (by hypothesis in Batch 1; by cell
in Batch 2 — see §5), and, for Batch 2 onward, a committed mechanism memo
predating exploratory analysis.

## 3. Registry summary — Batch 1 (CLOSED)

| ID | Hypothesis | Verdict |
|---|---|---|
| M2 | Entry timing vs random | No edge after drift correction (amended: noise, not anti-predictive) |
| H-001 | Pullback depth | KILLED |
| H-002 | Session structure (H4) | KILLED |
| H-003 | Time-exit value | KILLED |
| H-004 | Session structure (1H) | KILLED |
| H-005 | Volatility regime | KILLED |
| H-006 | Day-of-week | KILLED |
| H-007 | Cross-instrument correlation | Characterization only (no edge claim) |

**Interpretation:** unconditional single-variable marginal effects are
exhausted on this 5-instrument universe at H4/1H. Total adjudicated: 7.
Kills: 6. Characterization survivals: 1. Sub-families tested: 6.

## 4. Why Batch 1 concluded, and why Batch 2 is legitimate

The stopping rule pre-registered in `research/S1_INTERIM_FINDING_5_KILLS.md`
committed to a 3-item budget and a deliberate re-evaluation, reached at
`3b4a84f`. That re-evaluation is now resolved: **continue**, into a
Conditional Search, per the explicit decision record in
`docs/PHASE3_CLOSURE.md`. The reasoning, briefly: Batch 1 tested the
hypothesis family most likely to be arbitraged to nothing — marginal,
endogenous, single-variable effects on the most liquid instruments at the
most-studied timeframes. A 0/7 tradable hit rate there is real
information about THAT family; it is not evidence against conditional,
cross-sectional, or event-anchored structure, which was never tested.

Registering hypothesis #8 (or any Batch 2 candidate) on momentum alone
remains prohibited. Every Batch 2 candidate requires the mechanism memo
and charter compliance below.

## 5. Conditional Search charter — requirements (Batch 2, ACTIVE)

Full charter: `research/CONDITIONAL_SEARCH_CHARTER.md`, committed
`82a4e29`, hash-pinned alongside the stopping rule
(`research/S1_STOPPING_RULE.md`). Summary:

- **Mechanism memo per hypothesis** — economic story, counterparty (who
  is systematically wrong and why they can't arbitrage it away), prior
  (low/medium/high, justified), and a **sign-specificity requirement**:
  a per-instrument, per-condition sign prediction specific enough to be
  visibly wrong. Committed BEFORE any exploratory look at the
  conditioning variable. This closes the motivated-memo gap — a memo
  that could absorb any result as confirming evidence fails this bar.
- **Interaction-capable analysis harness**, built and validated on a
  known-answer case BEFORE it touches real data (StringArray-bug
  precedent), required before first Batch 2 registration is adjudicated.
  Status: **not yet built** — see `PROJECT_STATE.md` §2/§5.
- **FDR-by-cell accounting.** Interaction tests multiply the comparison
  space (session × volatility is dozens of cells); the ledger counts
  cells, not registrations, and null distributions are evaluated per
  cell. Extension of `research/fdr_check.py`, not yet built (see
  `PROJECT_STATE.md` §5, item under "Immediate next step" in the
  handover).
- **Cost-to-verdict priority order:** mechanism cost + data cost +
  compute (≈0). Zero-new-data interactions (session × volatility;
  interactions between already-killed marginals) outrank anything
  requiring exogenous feeds. Cross-asset conditioning is explicitly
  gated on a proper S1-grade data onboarding event — **US500 and DXY are
  NOT currently in the S1 dataset**, correcting an earlier chat-only
  assumption that they were.
- **Cap:** 3 open registrations at any time, as in Batch 1.
- **New stopping rule** (`research/S1_STOPPING_RULE.md`): Batch 2 is
  budgeted at 8–12 adjudications, with two pre-committed branches:
  - **Branch A (survivor):** single OOS unseal, cost model v2 required
    in parallel, pre-registered live kill criteria ("H-Live"), one
    quarter of paper trading as the first live test, then five hard
    criteria (all, no exceptions) before real capital.
  - **Branch B (zero survivors):** the Search at 1H/H4 in this universe
    concluded as a first-class negative result, equal rank with any
    acceptance. Two pre-specified sub-branches decided now: B1 (daily-
    frequency program, the pre-specified default — cost disadvantage
    shrinks at daily frequency while the discipline advantage carries
    over) or B2 (conclusion of the trading objective as a legitimate
    successful outcome). An unregistered "Batch 3 of just a few more
    ideas" is explicitly forbidden by name.

## 6. Acceptance prerequisites (any future accepted effect, Batch 1 or 2)

Before ANY acceptance: cost model v2 (swap integration) complete, AUDUSD
real contract specs in place, re-canonicalized hashes (already done),
and the full evidence standards of §2. Current status of these
prerequisites: `PROJECT_STATE.md` §7. **As of this writing, cost model
v2 and AUDUSD specs are NOT done — no acceptance is possible yet
regardless of any Batch 2 result.**
