# PROJECT_STATE — Single Source of Truth for Current Status

**Last updated:** 2026-08-03 · **HEAD at last update:** to be filled with
this commit's own hash (see provenance note at bottom).
**Supersedes:** any prior PROJECT_STATE.md content stamped `3b4a84f` or
earlier that may exist in chat history or external notes — that version
was never committed to this repo and is stale relative to `82a4e29`,
`2b04b66`, `2fd20d3`, and `docs/PHASE3_CLOSURE.md`.
**Rule:** this file is updated on every milestone or adjudication commit.
If this file disagrees with any other document, this file wins; if it
disagrees with the ledger/registry, the ledger wins and this file is
stale — say so, don't quietly trust either.

## 1. Phase

**Phase 3 (Batch 1, unconditional marginal search): CLOSED, as complete.**
**Phase 4 (Conditional Search, Batch 2): OPEN, chartered, in progress.**

See `docs/PHASE3_CLOSURE.md` for the explicit decision record. Charter:
`research/CONDITIONAL_SEARCH_CHARTER.md`. Stopping rule:
`research/S1_STOPPING_RULE.md`.

## 2. Infrastructure (all validated)

- Deterministic backtest engine; determinism verified via independent runs
  (byte-identical output hashes).
- Experiment ledger: git-clean requirement, SHA-256 of config/input/output,
  per-run artifact copies, append-only JSONL.
- Strategy protocol with interchangeable implementations.
- Signed (long/short) simulator: signed positions, direction-aware
  stop/target geometry and hit detection, unified P&L
  (exit − entry) × direction. All pre-refactor tests pass; numerical
  equivalence on shared columns verified against canonical values.
- Signed drift-neutral null model (NullRandomStrategy, random direction).
- Symmetric-market fixture (invariant: mirrored short has IDENTICAL P&L to
  original long — two inversions cancel).
- O(n²) performance correction verified numerically identical.
- FDR ledger + `fdr_check.py`, hash-pinned alongside the charter at
  `82a4e29`; any future change to survival/kill criteria must itself be
  registered in the ledger before it takes effect.
- Migration verification framework: `research/verify_schema_migration.py`
  — **DONE**, confirmed present at this commit.
- Trade-CSV hash re-canonicalization post direction-column schema change:
  **DONE** (`25db12b`).
- **Interaction-capable (per-cell) analysis harness: NOT YET BUILT.**
  Required before H-008 (or any interaction hypothesis) can be adjudicated
  — charter requirement, `research/CONDITIONAL_SEARCH_CHARTER.md`. Must be
  validated on a known-answer case before touching real data, per the
  StringArray-shuffle-bug lesson (`LESSONS_LEARNED.md` if/when committed;
  see H-004 STATUS for the precedent).

## 3. Data

- 5 instruments: USDJPY, XAUUSD, GBPJPY, EURUSD, AUDUSD; H4 and 1H;
  hash-pinned; MT5 provenance logged.
- **US500 and DXY are NOT in the S1 dataset.** (Prior chat-only notes
  incorrectly implied a risk-on/off cross-asset axis already existed in
  S1 — it does not. Any cross-asset conditioning candidate is gated on a
  proper S1-grade data onboarding event: sourced, snapshotted,
  hash-pinned, caveated, per the charter.)
- **Caveats, verified at this commit:**
  - AUDUSD spread is still a 1.2-pip placeholder
    (`core/instruments.py`, `spread_pips: 1.2`) — **NOT replaced with
    real contract specs.**
  - Swap-rate snapshot is pinned (`research/S1_SWAP_RATES_SNAPSHOT.md`,
    demo account) but **NOT integrated into the cost model** — zero
    references to swap in `execution/`.

## 4. Findings of record (Batch 1, closed)

- trend_pullback: FALSIFIED (four independent tests). Retired.
- M2 (amended by `cef09ea`): under the drift-corrected signed null,
  entries are indistinguishable from noise on USDJPY/XAUUSD; GBPJPY
  weakly negative. The earlier "entries are anti-predictive" narrative is
  SUPERSEDED — quote only the amended `PHASE2_FINDINGS.md`.
- H-001 pullback depth — KILLED.
- H-002 session structure (H4) — KILLED.
- H-003 time-exit value — KILLED.
- H-004 session structure (1H) — KILLED.
- H-005 volatility regime — KILLED.
- H-006 day-of-week — KILLED.
- H-007 cross-instrument correlation — SURVIVES as characterization only
  (mean pairwise |corr| 0.324 < 0.5; EURUSD–AUDUSD 0.552 flagged as a
  Phase 4 conditioning-variable candidate, not an edge).
- **Conclusion of record:** unconditional single-variable marginal effects
  are exhausted on this 5-instrument universe at H4/1H. This does NOT
  imply no exploitable structure exists at any frequency or conditioning
  depth — see `docs/PHASE3_CLOSURE.md`'s reasoning section.

## 5. Phase 4 status (Batch 2, in progress)

- `research/CONDITIONAL_SEARCH_CHARTER.md` + `research/S1_STOPPING_RULE.md`
  committed `82a4e29`, before any Batch 2 hypothesis was explored.
- **H-008 (thin-session × high-volatility interaction): KILLED.** Full
  lifecycle complete: mechanism memo (`2b04b66`) → registration
  (`3e8b155`) → GBPJPY group-assignment amendment (`b8a8794`,
  corrected 2-vs-3 to 3-vs-2 per `core/instruments.py`'s actual session
  metadata) → interaction harness built + validated (`2875bb8`) →
  harness bug caught and fixed (`f5c9cc3`, build_cell was filtering on
  a stale session column that structurally could never say "tokyo" for
  EURUSD/XAUUSD/GBPJPY) → adjudicated KILLED. GBPJPY's primary p=0.0005
  dies on the mandatory seed-dispersion check, same pattern as H-005's
  GBPJPY p=0.006. Zero of the three required cells (EURUSD, XAUUSD,
  GBPJPY) clear all conditions; the non-adjudicating GBPJPY-excluded
  robustness view also fails independently. See
  `research/registry/H-008.md` STATUS section,
  `research/H-008-verdict.csv` for full detail.
- Interaction-capable per-cell FDR analysis harness
  (`research/interaction_harness.py` + `research/fdr_cells.py`):
  **built and validated** (`tests/test_interaction_harness.py`,
  `tests/test_fdr_cells.py`, 15 tests, including a regression test for
  the stale-session-column bug). This unblocks all future Batch 2
  interaction hypotheses, not just H-008.
- **Batch 2 progress: 2 of 8–12 budgeted adjudications complete (both
  killed), plus 1 documented no-candidate
  (day-of-week × volatility, rejected at mechanism-memo stage before
  registration). 0 survivors.**
  - H-008 (thin-session × high-volatility): KILLED. Full lifecycle in
    `research/registry/H-008.md`.
  - H-009 (month-end proximity × high-volatility): KILLED. Unambiguous
    -- p=0.8375, within seed noise, and wrong sign (continuation, not
    reversion). Surfaced by the day-of-week no-candidate's own
    analysis, not a rescue of it. New calendar-distance derived
    variable (`research/calendar_distance.py`) built and validated
    (12 known-answer tests) along the way -- reusable for any future
    calendar-anchored candidate. Full lifecycle:
    `research/registry/MECHANISM-MEMO-H009.md` (memo, amended once at
    pre-freeze review to add a non-adjudicating low/mid-tercile arm
    closing a design gap between a refutation clause and what the
    analysis actually tested) → `research/registry/H-009.md`
    (registration + STATUS).
  - Next candidate per the charter's cost-to-verdict priority order:
    a killed×killed interaction (per the charter's own reasoning,
    testing whether "marginals exhausted, interactions might not be"
    holds outside the session family). H-001 × trend-state is
    DISQUALIFIED (`research/CONDITIONAL_SEARCH_CHARTER.md` §4a,
    trend_pullback resurrection risk) -- not a candidate.

## 6. Integrity record (precise claim)

Zero integrity violations, defined as: zero instances of trusting a
result that had not earned trust — no post-hoc promotion, no OOS peek, no
quiet re-test. This is NOT a zero-defect claim. Defects caught before
being trusted: 28 duplicate ledger entries (killed timeout, non-blocking),
32 missing backup directories (non-blocking, evidentiary files intact),
StringArray shuffle bug (H-004, caught pre-adjudication), wrong commit
hash in FDR ledger first draft. The catch record is evidence the
verification layer works; report it, never hide it.

## 7. Outstanding engineering debt

| Item | Status |
|---|---|
| Re-canonicalize trade-CSV hashes (direction column) | DONE (`25db12b`) |
| Migration verifier script | DONE (`research/verify_schema_migration.py`) |
| Cost model v2 (swap integration) | **NOT DONE** |
| AUDUSD real contract specs (replace 1.2-pip placeholder) | **NOT DONE** |
| Interaction-capable per-cell analysis harness | **NOT DONE** — blocks H-008 execution |

**Consequence, stated explicitly:** Batch 2 KILL adjudications are valid
under the current cost model (placeholder/simplistic costs only make a
kill more likely, never manufacture a false survival). **No Batch 2
hypothesis may be ACCEPTED until cost model v2 and real AUDUSD specs are
in place.** Every Batch 2 registration must state this caveat explicitly.

## 8. The decision on the table (as of this update)

None outstanding at the phase or hypothesis-design level. Both tactical
decisions (ATR tercile method, reversion window) are resolved and frozen
in `research/registry/H-008.md`. **The single remaining blocker before
any H-008 statistic can be computed is engineering, not a decision:**
build the interaction-capable per-cell FDR harness, validate it on a
known-answer case, then run H-008 via freeze-then-verdict.
