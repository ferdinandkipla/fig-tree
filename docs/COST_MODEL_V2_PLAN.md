# COST_MODEL_V2_PLAN

**Committed before any simulation-core code is written.** This is the
first change to simulation core since the adjudication record began
depending on it -- gets the full equivalence-check ceremony per
`ENGINEERING_STANDARDS.md`, plus the extra discipline this specific
change requires: a bug was found during scoping (Section 1), not
introduced by this plan, and its retrospective disclosure is a
deliverable in its own right (Section 4), independent of the fix.

## 0. Scope decisions (confirmed before writing this plan)

1. Swap snapshot (`research/S1_SWAP_RATES_SNAPSHOT.md`): wired
   **as-is**, its existing caveats (today-snapshot, demo-account,
   XAUUSD sign asymmetry) carried forward loudly -- named in the cost
   model's own docstring AND in `docs/PROJECT_STATE.md`, not left
   buried in the snapshot doc alone. Re-sourcing is explicitly OUT of
   scope for this change; it is a separate, dateable event with its
   own commit, so it never gets conflated with which change moved
   which number in the equivalence check.
2. AUDUSD real specs: NOT supplied by inventing a number. This plan
   writes the precise requirement (Section 5) and hard-blocks AUDUSD
   in code (`PLACEHOLDER_INSTRUMENTS`) rather than silently defaulting
   -- AUDUSD stays flagged non-acceptable until a real, dated source
   fills the requirement.
3. Size-scaling bug (Section 1): FIXED in this change, not inherited.
   Reasoning: the swap addition forces the size question open
   regardless (a swap rate is inherently per-lot), so shipping "v2"
   with one correctly-scaled term (swap) next to one knowingly-flat
   term (spread/slip) would be a documented inconsistency chosen, not
   inherited. This is a correctness bug in simulation core, a
   different category from the swap snapshot's sourcing limitation --
   it gets fixed, not caveated-and-carried-forward.

## 1. The bug (found during scoping, not introduced here)

`execution/costs.py`'s `total_cost(symbol, slippage_pips)` returns a
flat dollar cost representing ONE standard lot's spread+slippage,
regardless of the actual trade's position size. `execution/simulator.py`
`_close()` scales `pnl_gross` by `t.size` (correct) but subtracts
`total_cost(self.symbol)` unscaled (incorrect):

```python
pnl_gross = pnl_pips * meta["pip_value"] * t.size   # scales by size
pnl_net   = pnl_gross - total_cost(self.symbol)      # does NOT
```

`risk/sizing.py`'s `position_size()` returns variable lot sizes per
trade (real range observed in EURUSD H1 null trades: 0.13 to 1.43
lots, mean 0.51) -- this is not a negligible edge case. **Direction of
bias: under-costs large positions, over-costs small ones**, relative
to their true proportional cost.

## 2. Fix (Commit 1 of 2)

`total_cost()` gains a `size: float` parameter; both `spread_cost` and
`slip_cost` multiply by it. `_close()` passes `t.size`. This is a
pure scaling fix -- no swap logic in this commit.

**Expected diff (Commit 1 only):** every existing trade's net `pnl`
changes (spread/slip cost now proportional to size instead of flat).
No new cost source. Byte-identical inputs (bars, signals, entries,
exits, stops, targets) -- ONLY the cost subtraction term changes.
Equivalence check for this commit: re-run the existing test suite
(all pre-existing `pnl_gross` values must be untouched; all `pnl` net
values are EXPECTED to differ -- this is not a regression, it is the
fix).

## 3. Swap addition (Commit 2 of 2)

Adds swap cost as a separate term, applied only to trades whose
`entry_dt`/`exit_dt` span crosses ≥1 rollover boundary.

```
n_rollover_nights = count of rollover-boundary crossings in
                     [entry_dt, exit_dt), rollover boundary = 22:00 UTC
                     (5pm NY), each calendar day counted once EXCEPT
                     Wednesday counted 3x (standard FX weekend-rollover
                     triple-charge convention)
swap_cost = (swap_long if direction==1 else swap_short)
            * size * n_rollover_nights
```

Rates from `research/S1_SWAP_RATES_SNAPSHOT.md`, unchanged, its three
caveats (today-snapshot / demo-account / XAUUSD-asymmetry-unverified)
carried into this module's docstring verbatim, not summarized away.

**Wednesday-3x convention assumption, stated loudly per the same
standard as the demo-account sourcing:** the snapshot doc does not
state a rollover-day convention. FX brokers standardly triple-charge
Wednesday (to cover Sat/Sun); SOME brokers use a different convention
for metals (e.g. Friday 3x for XAUUSD). Absent a stated source, this
plan adopts the FX convention (Wednesday 3x) UNIFORMLY, including for
XAUUSD, as an explicit, disclosed assumption -- not verified against
IC Markets' actual metals rollover schedule. This is a candidate item
for the same re-sourcing event mentioned in Section 0.1, out of scope
here.

**AUDUSD hard-block:** `PLACEHOLDER_INSTRUMENTS = {"AUDUSD"}` at
module level. `total_cost()` raises if called for a placeholder
instrument UNLESS an explicit `allow_placeholder=True` is passed (kills
remain computable, per the existing "placeholder costs kill fine"
convention -- see `docs/PROJECT_STATE.md` §7) -- but the caller
receives a loud, typed signal rather than a silent number, and any
result touching AUDUSD carries a `cost_model_status: "PLACEHOLDER"`
field through to the trade record.

**Expected diff (Commit 2 only):** trades with zero rollover crossings
-- the large majority on H1 given `bars_held` tops out at 10 (~10
hours, per the `max_bars_in_trade` cap observed in the null-trade data)
-- see NO further change from Commit 1's numbers. Only trades whose
holding period spans a rollover boundary gain a nonzero swap term.
AUDUSD trades gain the `cost_model_status` field; their `pnl` numbers
are otherwise unaffected by this commit (swap/spread costs for AUDUSD
still run on the existing placeholder spread, now explicitly flagged
rather than silently trusted).

## 4. Errata note (named deliverable, independent of the fix)

A committed disclosure, either as a new `research/COST_MODEL_ERRATA.md`
or as a short addition to each affected hypothesis's STATUS section --
decided during implementation, likely the former for a single
authoritative location cross-referenced from each STATUS doc. Must
state: what the bug was, its direction of bias, which hypotheses
(M2, H-001 through H-007) ran their `pnl`-based statistics under the
mis-scaled model, which hypotheses (H-008, H-009) were NEVER exposed
(they consume raw price reversion via `research/interaction_harness.py`,
never `total_cost()` or the `pnl`/`pnl_gross` columns), and the
verified (not merely asserted) outcome of Section 5's re-check.

## 5. Past-verdict re-verification (explicit checklist, part of the equivalence work)

**Exposed (must be checked): M2, H-001, H-002, H-003, H-004, H-005,
H-006, H-007.** All six of H-001 through H-006 confirmed via direct
grep to consume the `pnl` column
(`research/run_h001.py` through `research/run_h006_verdict.py`);
H-007 (`research/run_h007_verdict.py`) and M2
(`research/run_null_model.py`) likewise confirmed.

**NOT exposed (no re-check needed, confirmed by absence): H-008,
H-009.** Neither `research/run_h008.py` nor `research/run_h009.py`
references `total_cost`, `pnl`, or `pnl_gross` anywhere -- both work
entirely from `research/interaction_harness.py`'s `compute_reversion`,
which operates on raw bar close prices, never on simulated trade P&L.

**Checklist:**
- [ ] Regenerate `pnl` under the corrected (size-scaled + swap) cost
      model for each of M2, H-001..H-007's underlying null-trade data.
- [ ] Re-run each hypothesis's own adjudication statistic (expectancy,
      permutation test, etc. -- whatever each `run_h00X.py` computed
      originally) on the corrected `pnl` values.
- [ ] Confirm every prior KILL verdict still KILLS. Expected outcome,
      stated before running (per this session's own standard for
      pre-registering expected diffs): all seven should stand,
      because none died on a cost-margin call -- they died on
      p-values and seed dispersion, categorically different from a
      cost-stress threshold. This expectation is falsifiable by the
      re-check, not assumed by it.
- [ ] If ANY verdict's conclusion would change, STOP -- this is a
      finding requiring its own decision record (same category as the
      H-008 GBPJPY grouping amendment), not a silent update.
- [ ] Record the confirmation (or, in the unlikely event of a flip,
      the finding) in the errata note from Section 4 -- "verified
      unaffected," not "believed unaffected."

## 6. Test plan

- New unit tests for `total_cost()`'s size-scaling (known-answer:
  double the size, double the spread/slip cost).
- New unit tests for the rollover-night counter (known-answer cases
  mirroring `tests/test_calendar_distance.py`'s rigor -- same-day
  trade = 0 nights, overnight non-Wednesday = 1, spanning a Wednesday
  = 3, multi-day span = sum with Wednesday multiplier applied
  correctly).
- New unit test confirming `PLACEHOLDER_INSTRUMENTS` blocks AUDUSD by
  default and only proceeds with `allow_placeholder=True`.
- Full existing suite must pass unchanged EXCEPT wherever it asserts a
  specific `pnl` value that depended on the old flat-cost bug --
  those specific assertions get updated with a comment explaining why,
  not silently changed.
- End-to-end: re-run `research/run_h001.py` (or equivalent) before/
  after and diff `pnl_gross` (must be byte-identical) vs `pnl` (must
  differ, in the direction Section 1 predicts).

## 7. Sequence

1. This plan, committed.
2. Commit 1: size-scaling fix + tests + equivalence check (Section 2).
3. Commit 2: swap addition + AUDUSD hard-block + tests (Section 3).
4. Past-verdict re-verification (Section 5's checklist), its own
   commit(s) -- likely one script + output per exposed hypothesis, or
   one consolidated re-verification report.
5. Errata note (Section 4), referencing the re-verification's
   confirmed (not assumed) outcome.
6. Only after 1-5: `docs/PROJECT_STATE.md` and `RESEARCH_PROGRAM.md`
   §6 updated to reflect cost model v2 as DONE (currently both list it
   as NOT DONE) -- and AUDUSD specifically remains flagged pending the
   Section 5-of-this-plan-referenced (renumbered: the AUDUSD
   requirement, this doc's Section on AUDUSD) real spec.
