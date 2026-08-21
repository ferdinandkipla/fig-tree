# PROJECT_STATE — Single Source of Truth for Current Status

**Last updated:** 2026-08-14 · **HEAD at last update:** `a42a7aa`.
**Supersedes:** any prior PROJECT_STATE.md content stamped `3b4a84f` or
earlier that may exist in chat history or external notes — that version
was never committed to this repo and is stale relative to `82a4e29`,
`2b04b66`, `2fd20d3`, and `docs/PHASE3_CLOSURE.md`.
**Rule:** this file is updated on every milestone or adjudication commit.
If this file disagrees with any other document, this file wins; if it
disagrees with the ledger/registry, the ledger wins and this file is
stale — say so, don't quietly trust either. (This update closes a stale
window: the file sat 6 days behind HEAD, describing cost model v2 and
H-008/H-009 as blocked/pending when both were actually complete.)

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
- **Interaction-capable (per-cell) analysis harness: DONE, built and
  validated** (`research/interaction_harness.py` + `research/fdr_cells.py`,
  15 tests including a regression test for the stale-session-column bug
  caught during H-008). Unblocks all future Batch 2 interaction
  hypotheses.
- **Cost model v2 (swap integration): DONE and independently
  re-verified.** Implementation landed `e0d3637`/`4feb84c` (size-scaling
  fix + swap cost + AUDUSD hard-block). Re-verification across all 7
  cost-exposed items (M2, H-001–H-006) closed `a42a7aa` — see Section 4a
  below. Zero overall verdict flips; three sub-criterion near-misses
  documented and closed.

## 3. Data

- 5 instruments: USDJPY, XAUUSD, GBPJPY, EURUSD, AUDUSD; H4 and 1H;
  hash-pinned; MT5 provenance logged.
- **US500 and DXY are NOT yet in the S1 dataset** (S1 itself remains
  exactly the 5 instruments above), **but the availability question is
  now resolved, as of 2026-08-20:**
  - **US500: confirmed onboardable.** History from 2018-12-31
    (`research/mt5_us500_data_check.py`), covers the full TRAIN/OOS
    window with no truncation needed. Onboarding (sourcing, ingesting,
    hash-pinning, caveating, per the charter's S1-grade standard) is
    still a deliberate, separate step from this availability check —
    not yet done.
  - **DXY: confirmed DISQUALIFIED for this phase.** Only a dated
    futures CFD (`DXY_U6`, Sept 2026 expiry) exists — no continuous/
    cash instrument under any name (`research/mt5_dxy_symbol_search.py`,
    7403 symbols checked). No futures-roll handling exists anywhere in
    this codebase. Formal disqualification:
    `research/CONDITIONAL_SEARCH_CHARTER.md` §4a. US500 proceeds alone
    as the risk-on/off proxy for the cross-asset tier.
- **Caveats, verified at this commit:**
  - AUDUSD spread is still a 1.2-pip placeholder
    (`core/instruments.py`, `spread_pips: 1.2`) — **NOT replaced with
    real contract specs.** Hard-blocked (`PlaceholderInstrumentError`)
    unless explicitly overridden.
  - Swap-rate snapshot is pinned (`research/S1_SWAP_RATES_SNAPSHOT.md`,
    demo account) and **IS now integrated into the cost model**
    (`execution/costs.py`, cost model v2). The demo-account sourcing and
    unverified sign-asymmetry remain a live caveat — re-verification
    (Section 4a) surfaced a concrete, closed-arithmetic dependency of
    several XAUUSD verdict internals on this exact number, which
    **raises this item's priority**: re-sourcing the XAUUSD swap rate
    from a verified (non-demo) source now gates both the cross-asset
    conditioning candidate tier (Section 5) and any future XAUUSD-adjacent
    hypothesis, not just general data-quality hygiene.

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

## 4a. Cost model v2 re-verification (closed, `a42a7aa`)

**Staleness flag, added 2026-08-20, now compounded:** everything below
was verified against `SWAP_RATES` as pinned in the 2026-07-24 snapshot,
**and against a cost model with zero commission modeling and AUDUSD
hard-blocked entirely.** Both have since changed materially:
`SWAP_RATES` refreshed to 2026-08-20 values (formalized as permanent,
`research/S1_SWAP_RATES_SNAPSHOT_V2.md`), and **a commission term was
added for the first time** ($7/lot round-turn, the 4 FX majors) —
this is not a magnitude refresh of an existing term the way the swap
update was, it's a wholly new cost component this re-verification never
saw at all. **This re-verification has NOT been re-run against either
change.** The swap drift alone was modest and unlikely to flip anything
given the margin H-003/H-004/H-006's near-misses had; the commission
addition is a different kind of change (new fixed-per-trade cost,
independent of holding period or instrument-specific swap asymmetry)
and its effect on any of the 7 verdicts has not been reasoned through
at all, let alone tested. This section's "zero verdict flips" claim
should be read as **"zero verdict flips as of the cost model tested
against the 7/24 snapshot with no commission"** — not as current
coverage.

Full decision record: `research/registry/FINDING-xauusd-swap-sensitivity-h001.md`.

All 7 cost-exposed items reran clean against corrected costs (patch-only,
cascade-immune methodology — see that document Section 1 for why
cascade-compounded and cascade-immune legs can't be mixed). **Zero
overall verdict flips:**

| Item | Verdict | Notes |
|---|---|---|
| H-001 | KILLED (unchanged) | XAUUSD percentile shift, arithmetic closed to 0.2% residual |
| H-002 | KILLED (unchanged) | XAUUSD p 0.353→0.0000, corroborating |
| H-003 | KILLED (unchanged) | XAUUSD's own kill-criterion contribution flips sign; absorbed by USDJPY+GBPJPY |
| H-004 | KILLED (unchanged) | nominal-sig count crosses registered 4/5 bar; absorbed by dispersion gate |
| H-005 | KILLED (unchanged) | XAUUSD p 0.116→0.0000, corroborating |
| H-006 | KILLED (unchanged) | consistency sub-criterion flips; structural cost-calendar confound (Wednesday 3x rollover) found and closed |
| M2 | no-beat-null (unchanged) | strongest single-symbol shift; GBPJPY softens the other direction |

Three near-misses (H-003, H-004, H-006) where a sub-criterion flipped
under corrected costs and a second, independent gate held the line —
the pipeline's redundant-gate adjudication design is what prevented a
false survival, worth treating as load-bearing infrastructure going
forward. XAUUSD's swap term was closed-form-verified as the driver in
every case it appeared (H-001: 0.2% residual; H-003: to-the-cent; H-006:
flat, day-independent 4.4% residual matching the known spread/slip
effect) — not asserted, demonstrated.

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
- **Batch 2 progress: 2 of 8–12 CAPPED (not quota'd) adjudications
  complete (both killed), plus 2 documented no-candidates. 0
  survivors.**
  - H-008 (thin-session × high-volatility): KILLED.
  - H-009 (month-end proximity × high-volatility): KILLED.
  - No-candidate 1: day-of-week × volatility
    (`research/registry/NO-CANDIDATE-daydow-x-volatility.md`) — one
    pairing failed its own memo.
  - No-candidate 2: killed×killed survey
    (`research/registry/NO-CANDIDATE-killed-x-killed.md`) — the
    **complete** zero-new-data killed×killed candidate pool outside the
    session family (3 pairs: H-001×H-003, H-001×H-005, H-003×H-005)
    surveyed and rejected. Stronger Branch B statement than
    no-candidate 1: the entire cheap tier of the charter's priority
    order is now empty, not just one pairing.
  - **Consequence: the only remaining Batch 2 candidate tier is
    cross-asset conditioning. As of 2026-08-20, the data-availability
    question is resolved (`research/mt5_us500_data_check.py`,
    `research/mt5_dxy_symbol_search.py`): US500 confirmed onboardable
    (history from 2018-12-31), DXY confirmed DISQUALIFIED for this
    phase (dated futures contract only, no continuous instrument, no
    roll-handling in this codebase — formal record:
    `research/CONDITIONAL_SEARCH_CHARTER.md` §4a). US500 proceeds alone
    as the risk-on/off proxy. The actual onboarding event (sourcing,
    ingesting, hash-pinning, caveating US500 into `data/storage/` per
    the charter's S1-grade standard) is still a separate, not-yet-done
    step from this availability confirmation.**
  - **Swap-rate gating scope, decided explicitly (was previously stated
    as an undifferentiated AND across the whole tier — that was an
    overgeneralization on this document's part, not charter-original,
    corrected here):** XAUUSD swap-rate re-sourcing gates any
    hypothesis that actually touches XAUUSD — not the cross-asset tier
    as a blanket whole. A hypothesis restricted to non-XAUUSD
    instruments (e.g. EURUSD/AUDUSD relative value, or a US500
    conditioning variable applied only to USDJPY/GBPJPY/EURUSD/AUDUSD)
    has no dependency on the XAUUSD swap number and is not blocked by
    it. **Practical consequence: US500 onboarding can proceed, and
    non-XAUUSD cross-asset candidates can be surveyed and drafted, in
    parallel with XAUUSD swap re-sourcing rather than serially after
    it.** Any mechanism memo in this tier must state explicitly whether
    it touches XAUUSD and, if so, disclose the provenance requirement
    from `research/registry/FINDING-xauusd-swap-sensitivity-h001.md`
    Section 5.
  - **This is not speculative investment; it is dead-weight engineering
    debt that must clear either way.**
  - **Next step, agreed sequence:** ~~cost model v2 (swap
    integration)~~ **DONE, re-verified (Section 4a)** →
    **XAUUSD swap-rate re-sourcing (sequenced ahead of AUDUSD specs —
    three re-verification sections and a pre-registered falsifiable
    prediction already depend on this exact fix, vs. AUDUSD's specs
    being a generic data-quality gap with no specific finding waiting
    on it)** and **US500 data onboarding, in parallel** → AUDUSD
    real contract specs (blocks acceptance generally, not gated by
    either of the above) → survey the cross-asset conditioning tier
    with the same pre-drafting screen used for both no-candidates,
    scoped per-instrument per the decision above. If that survey also
    returns empty, Batch 2 concludes early with a defensible record (2
    kills, 2 no-candidates, exhausted priority ladder, 0 survivors) and
    continue/conclude reopens on evidence, not budget exhaustion.

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
| Cost model v2 (swap integration) | DONE (`e0d3637`/`4feb84c`), re-verified across 7 items (`a42a7aa`, Section 4a) |
| XAUUSD swap-rate re-sourcing (verified, non-demo source) | **RESOLVED AS: not achievable, reframed (2026-08-20).** IC Markets publishes no static swap table for this broker (confirmed via direct check of their own material — swap rates are stated as "Variable, check platform"). Decision: demo-sourced rates accepted as the permanent baseline, refreshed periodically, cross-checked for plausibility (not exact-value verification) against an independent broker's published numbers. Full record: `research/S1_SWAP_RATES_SNAPSHOT_V2.md`. **New follow-on debt created by this refresh: cost-model-v2 re-verification (Section 4a) was run against the now-superseded 7/24 values and has not been re-run against the 8/20 values.** |
| US500/DXY data-availability check | **DONE (2026-08-20)** — US500 confirmed onboardable (history from 2018-12-31); DXY confirmed disqualified for this phase (dated futures contract only, no roll-handling in this codebase; formal record `research/CONDITIONAL_SEARCH_CHARTER.md` §4a). |
| US500 real data ingestion (H4/1H into `data/storage/`) | **DONE (2026-08-20)** — `data/storage/US500_16388.csv` (9879 rows, 2019-01-02→2025-05-30), `data/storage/US500_16385.csv` (37862 rows, 2018-12-31→2025-05-30). Provenance: `research/S1_US500_ONBOARDING_SNAPSHOT.md`. **Hash-pinning caveat, discovered this commit:** the onboarding script's run-time SHA-256 did not match the git-stored file's hash — Windows `core.autocrlf` silently normalized line endings between the script's write and the commit. Corrected in the snapshot doc, `.gitattributes` added (`eol=lf` on csv/py/md) to prevent recurrence. **Not yet independently checked: whether the original 5 instruments' `data/storage/*.csv` (same `data.loader.fetch()` code path, committed pre-dating this discovery) have the same undetected divergence between their originally-claimed and actually-git-stored hashes.** Flagged, not resolved. |
| AUDUSD real contract specs (replace 1.2-pip placeholder) | **RESOLVED (2026-08-20).** Spread live-sampled (`research/sample_audusd_spread.py`, mean 0.075 pips, single ~2-min session — see script output for time-of-day caveat). Swap accepted under the permanent-baseline decision (`research/S1_SWAP_RATES_SNAPSHOT_V2.md`). **Commission added for the first time** — the cost model had zero commission modeling until this commit, despite the account being confirmed "Raw Spread" (IC Markets account dashboard, not inferred) where broker compensation is commission-based, not spread-markup-based. `$7.00/lot round-turn` (IC Markets' published Forex spec sheet, this account's USD currency), applied to the 4 FX majors only (`COMMISSION_APPLIES_TO` in `execution/costs.py`) — deliberately NOT applied to XAUUSD, whose metals commission is a separate, unsourced number. `PLACEHOLDER_INSTRUMENTS` is now empty. |
| USDJPY/GBPJPY/EURUSD spread_pips — never independently sourced from this account | **NEW, NOT DONE.** Surfaced by the AUDUSD fix: the old 1.2-pip AUDUSD placeholder was ~16x the actual live-sampled Raw-account spread (0.075 pips). The other 3 FX majors' `spread_pips` (1.5/2.5/1.0) read like the same category of generic, unverified estimate AUDUSD's placeholder turned out to be — never labeled as such, never checked against this account. Not assumed wrong; not assumed right either. Needs the same `sample_audusd_spread.py`-style live sampling, per instrument. |
| XAUUSD metals commission | **NEW, NOT DONE.** IC Markets' commission table sourced this session was Forex-specific; their own material notes metals commission "varies by account type" without giving the number. XAUUSD's `total_cost()` currently has $0 commission — not verified as correct, just not yet contradicted either. |
| `spread_cost`/`slip_cost` formula in `execution/costs.py` — possible unit/double-conversion issue | **NEW, NOT DONE, NOT FIXED.** Discovered while sanity-checking the AUDUSD commission fix: `spread_pips * pip_size * pip_value * size` produces a spread cost of ~$0.000075 for a 1-lot AUDUSD trade regardless of the spread_pips value used — `pip_size` appears to be applied twice (once inside the already-dollar-denominated `pip_value`, once again explicitly), making the spread/slip terms negligible under any spread number. This is pre-existing code, unchanged by any commit this session, and has been load-bearing under every hypothesis adjudicated to date (Batch 1 and 2 both) — **not touched or fixed here**, deliberately, because a change of that scope needs dedicated review, not a same-session patch stacked on everything else. Consequence, stated plainly: **commission is now the dominant FX transaction-cost term by orders of magnitude** ($7/lot vs. ~$0.0001 from spread/slip as currently formulated) — true regardless of whether this formula turns out to need fixing. |
| Interaction-capable per-cell analysis harness | DONE, built and validated (`2875bb8`, bug-fixed `f5c9cc3`) |
| `tests/test_determinism.py` mutates committed `research/` CSVs in place as a side effect | **NOT DONE** — surfaced during cost model v2 (`docs/COST_MODEL_V2_PLAN.md`). A routine `pytest` invocation regenerates `research/trades_*.csv`/`regime_*.csv`/`yearly_*.csv` in the working tree via `main.py`, producing an unexplained dirty tree after any ordinary test run — possibly the same root cause as the ledger-freeze dirty-tree warnings already tolerated elsewhere (`research/run_h008.py`/`run_h009.py`'s manifest-freeze WARNING). Fix: the determinism test should regenerate into a temp directory and compare there, not overwrite `research/` in place. This same behavior is what produced the cascade-compounded vs. cascade-immune comparison trap caught during H-001 re-verification (`research/registry/FINDING-xauusd-swap-sensitivity-h001.md` Section 1) — still logged, not fixed. |

**Consequence, stated explicitly:** Batch 2 KILL adjudications are valid
under the current cost model (placeholder/simplistic costs only make a
kill more likely, never manufacture a false survival) — cost-model-v2
re-verification (Section 4a) confirms this held exactly: zero verdict
flips across all 7 exposed items. **No Batch 2 hypothesis may be
ACCEPTED until AUDUSD real specs are in place** (cost model v2 itself is
now done); the XAUUSD swap-rate re-sourcing item is a second, related
but distinct prerequisite specifically for any XAUUSD-adjacent
hypothesis (not the cross-asset tier as a whole — US500-only
candidates are unaffected by it). Every Batch 2
registration must state the applicable caveat explicitly.

## 8. The decision on the table (as of this update)

None outstanding at the phase or hypothesis-design level. The
interaction-capable harness, cost model v2 (Sections 2, 4a), and the
US500/DXY data-availability question (Section 3, 5, 7 — US500
onboardable, DXY disqualified) are all resolved, closing the items that
previously blocked this section. **The single remaining blocker before
Batch 2 can accept anything, or before a non-XAUUSD cross-asset
candidate can be drafted, is engineering/data-sourcing, not a
decision:** AUDUSD real contract specs, XAUUSD swap-rate re-sourcing,
and the actual US500 onboarding event (ingest + hash-pin, Section 5, 7).
