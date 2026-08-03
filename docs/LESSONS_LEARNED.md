# LESSONS_LEARNED — Institutional Memory (the Constitution)

This document supersedes the pre-registry "ZENITHFLOW_CONSTITUTION" PDF.
Nothing here may be violated without a committed decision record
explaining why.

## 1. Fundamental principles

1. The platform's product is trustworthy verdicts, not strategies. Six
   kills and one characterization IS the output working as designed.
2. Hypothesis before mechanics. Registration before code. Memo before
   look.
3. Null models are mandatory, matched, and drift-corrected. Judging
   returns against zero instead of a signed null once produced a wrong
   conclusion (M2's "anti-predictive entries") that stood until
   `cef09ea` corrected it.
4. Kill fast, kill often. Sunk cost is not evidence.
5. Intellectual honesty over optimism — in findings, documents, and
   status reports. Flag nuances that could mislead (schema-change hash
   example).

## 2. Statistical safeguards (never remove)

- 100-seed null distributions per adjudication.
- FDR control across the registry; individually significant p-values
  (GBPJPY p=0.006 in H-005) die when inconsistent across instruments and
  within seed noise.
- Evidence standards: ≥30 OOS trades, cross-instrument sign
  consistency, cost +50% survival.
- Pre-registered stopping rules, honored even when continuing feels
  cheap.

## 3. Mistakes never to repeat

1. **Phase 1:** trading logic before falsification infrastructure;
   instrument-specific fitted filters (ADX ceilings) mistaken for edge.
2. **Naive nulls:** unsigned nulls conflate drift with skill
   (~$5–10/trade here). Any new null model must be drift-neutral by
   construction.
3. **Wrong-invariant tests:** the symmetric-market fixture initially
   asserted negated P&L; hand-traced arithmetic showed identity. Verify
   the invariant itself before trusting a test failure in either
   direction.
4. **Unvalidated statistical plumbing:** the StringArray shuffle bug
   would have silently corrupted every H-004 p-value. Shuffle/
   permutation code is validated on known answers first, always. **This
   is the direct precedent for validating the Batch 2 interaction
   harness before it touches H-008.**
5. **Overclaiming integrity:** "zero integrity violations" means zero
   unearned trust, not zero defects. The defect list (28 dup ledger
   entries, 32 missing backups, shuffle bug, wrong FDR hash) is attached
   to the claim, not hidden behind it.
6. **Superseded narratives:** when a finding is amended (M2), hunt down
   and flag every document quoting the old version. Stale conclusions
   are a contamination vector for future sessions. **This is the same
   failure mode this doc package itself risked** — a full documentation
   set existed only in chat, unstamped against any commit, until this
   commit reconciled it against actual HEAD.

## 4. Practices worth preserving

- Building safeguards before pressure exists (FDR ledger at 4/4 kills).
- Committing interim findings with binding forward budgets.
- Honest "explicitly not done" sections in every progress update.
- Treating data onboarding as a provenance event, not a fetch.

## 5. The bottleneck doctrine

The project has transitioned from engineering-bottlenecked to
idea-and-data-bottlenecked. Compute per verdict ≈ 0 (H-005..H-007 were
~a day each). The scarce resource is a defensible economic mechanism;
the second scarcest is provenance-grade exogenous data. Consequences:

- Track registered mechanisms/month, not adjudications/month.
- Cost-to-verdict = mechanism cost + data cost + compute (≈0).
- The new dominant failure mode is motivated mechanism memos (stories
  reverse-engineered to justify testing on-hand data). Defense: memo
  committed before any exploratory look. This sequencing rule has the
  same status as the OOS seal.

## 6. Decision reasoning of record

- Long-only → signed architecture: not for shorting per se, but because
  an unsigned null cannot separate drift from skill; direction-capability
  was a statistical-validity requirement, not a feature request.
- trend_pullback retired on four independent falsifications; retirement
  survives the M2 amendment (nothing about "noise" rescues it).
- Search paused by its own pre-registered rule, not by discouragement.
  Stopping rules only mean something if honored at the moment they bind.
- Batch 1 → Batch 2 continuation (`docs/PHASE3_CLOSURE.md`): decided by
  explicit reasoning about which hypothesis family was tested (narrow,
  marginal, endogenous) versus which remains untested (conditional,
  cross-sectional, event-anchored) — not by discouragement, and not by
  momentum either.
