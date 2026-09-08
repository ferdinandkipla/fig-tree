# COST_MODEL_V3_SPREAD_FIX

**The third consecutive session to find a load-bearing cost-model
defect that predates the whole adjudication record** (flat costing →
no commission → this). Recorded plainly per that observation: before
Batch 2 can produce anything that could survive, the cost model needed
a written, tested known-answer specification so this class of
discovery stops being incidental. `tests/test_cost_model_spec.py` is
that specification, going forward.

## 1. The bug

`execution/costs.py`'s `spread_cost`/`slip_cost` formula multiplied by
`pip_size` in addition to `pip_value`:

```python
spread_cost = meta["spread_pips"] * meta["pip_size"] * meta["pip_value"] * size
```

`pip_value` is already dollars-per-pip-per-standard-lot — confirmed by
its use everywhere else in this codebase:
`execution/simulator.py`: `pnl_gross = pnl_pips * pip_value * size`
`risk/sizing.py`: `risk_per_lot = stop_pips * pip_value`

Neither multiplies by `pip_size` again. The cost formula was the only
consumer of `pip_value` that did — an internal inconsistency with this
codebase's own stated convention, not merely a number that "seemed
low." For EURUSD (`pip_size=0.0001`) this made spread/slip costs
**~10,000x too small**: a correct 1-pip spread on a 1.0-lot trade costs
$10.00; the bug computed $0.001.

**Discovery:** found incidentally (`8cd2642`) while sourcing AUDUSD's
real spread — disclosed and deliberately NOT fixed inline, per the
established discipline (single-cause commits, no scope creep stacked
on an already-large change).

## 2. Confirmation

`tests/test_cost_model_spec.py`, written BEFORE the fix, confirmed
against the then-current buggy code: `test_spread_cost_hand_computed`,
`test_slip_cost_hand_computed`, and
`test_full_reference_trade_every_term_hand_computed` all failed as
expected (actual `$7.002` vs. hand-computed correct `$27.00` for the
reference EURUSD trade — commission was the only correct term).
`test_spread_slip_bug_magnitude_was_10000x` independently verifies the
10,000x claim itself against a temporarily-reintroduced buggy formula,
rather than letting that number live only in commit-message prose.

## 3. Fix

Removed the extraneous `* meta["pip_size"]` from both `spread_cost` and
`slip_cost` in `execution/costs.py`. All six spec tests pass after the
fix; the pre-existing swap/commission/rollover test suites (unaffected
by this specific term) continue to pass once their own hardcoded
expectations — which depended on Trade A/B's total cost, and therefore
cascade through the same compounding-position-sizing effect documented
for every prior cost-model change — are updated (same commit).

## 4. Consequence, stated plainly (per the closing observation)

**Every cost +50% stress test run under H-001 through H-009 stressed a
spread/slip term that was, for practical purposes, zero.** The "0.2%
residual attributed to spread/slip" noted in the H-001 re-verification
arithmetic (`research/registry/FINDING-xauusd-swap-sensitivity-h001.md`)
is corroborating evidence, not a coincidence — a near-zero spread term
would produce exactly that kind of negligible residual.

**Verdict risk assessment: low, but "verified unaffected" must be
earned again, not assumed.** The kill-asymmetry argument that applied
to every prior cost-model correction applies here too — a LARGER,
correct spread/slip cost can only make a marginal effect harder to
sustain, never easier, so a hypothesis that killed under the (near-
zero) buggy spread term should kill at least as hard under the correct
one. But this is a directional argument, not a substitute for rerunning
the actual statistic. The full seven-item re-verification (`a42a7aa`)
was already stale from the swap refresh and commission addition before
this fix; it is now three cost-model changes removed from what it
actually tested.

## 5. What this does NOT do

- **Checked, not assumed:** `pip_value` grepped across `execution/`,
  `core/`, `risk/`, `research/` before writing this fix, specifically
  to rule out the same defect in `pnl_gross`/`position_size()`. Both
  are clean:
  - `execution/simulator.py:214-215`: `pnl_pips = price_delta /
    meta["pip_size"]` (a raw price delta DIVIDED by pip_size to
    produce a genuine pip count) then `pnl_gross = pnl_pips *
    meta["pip_value"] * t.size` — exactly one pip-to-dollar
    conversion, correct.
  - `risk/sizing.py:8,11`: `stop_pips = abs(entry - stop) /
    meta["pip_size"]` (same pattern) then `risk_per_lot = stop_pips *
    meta["pip_value"]` — correct.
  - The distinguishing fact: `pnl_pips`/`stop_pips` are DERIVED from a
    raw price delta (dividing by `pip_size` is the correct, necessary
    step that converts price units into a pip count). `spread_pips`/
    `slippage_pips` are GIVEN DIRECTLY as pip-unit constants
    (`core/instruments.py`'s `1.5`, `2.5`, `1.0`, `0.075`, ...) — never
    a raw price needing conversion. Multiplying an already-pip-unit
    number by `pip_size` again was the defect; it was never present in
    the two derived-pip-count consumers. No cascading position-sizing
    inflation, no further hunting required.
- Does not touch any other consumer of `pip_value` — both confirmed
  clean above.
- Does not re-run the Batch 1/2 re-verification. That is the next,
  separate step (`docs/PROJECT_STATE.md` §4a), combining this fix with
  the still-unapplied 08-20 swap values and commission term in one
  pass, per the recommended sequencing (fold all three into a single
  re-verification rather than three separate passes).
- Does not source USDJPY/GBPJPY/EURUSD's `spread_pips` from a live
  account (still generic, unverified estimates — separate open item,
  same category AUDUSD's placeholder turned out to be).
- Does not source XAUUSD's metals commission (still $0, not verified
  correct, not yet contradicted either).

## 6. Pre-registered spread-sampling aggregation rule (decided before sampling data exists)

Per review before `research/sample_fx_spreads.py`'s `--summary` is ever
run against real accumulated data:

- **Naive overall mean across accumulated samples is explicitly
  rejected.** Six ~2-minute runs across different sessions give six
  tight clusters, not a distribution — an unweighted mean would be
  biased by how many times the sampler happened to be run in each
  session, an artifact of operator behavior, not market structure.
- **The weight is the historical distribution of actual simulator
  entry hours**, not an assumption about which sessions "should"
  matter. Checked directly, not assumed: `execution/simulator.py`'s
  `_in_valid_session()` is hardcoded `return True` — session gating is
  **disabled** in research mode (comment: "reintroduce in Phase 3").
  Entries fire in every hour for every instrument. The correct
  aggregation is therefore weighting each session's sampled mean by
  the real historical entry-hour distribution, computed from the
  pooled 100-seed `research/null_runs_h004/` sweep (large N,
  already-generated) — not a "London/NY only" assumption, which the
  data does not support here.
- **Rollover window (21:00–22:00 UTC) is sampled and reported, but
  excluded from the weighted aggregate.** IC Markets spreads are
  reported to widen sharply in this window; including it would let one
  sample silently dominate whichever session tag it would otherwise
  fall under. Reported separately because
  `execution/rollover.py`'s `count_rollover_nights` implies positions
  are genuinely held through this window — worth recording for the
  finding doc even though the cost model has no time-of-day-varying
  spread to apply it to.
- **Demo-vs-live caveat carries over unchanged** from the swap-rate
  permanent-baseline decision (`research/S1_SWAP_RATES_SNAPSHOT_V2.md`)
  — one disclosure, not a new gate.

This rule is implemented in `research/sample_fx_spreads.py`'s
`historical_entry_distribution()` and `print_summary()`, verified via
synthetic-data round-trip tests (full coverage → weighted recommendation
computed; partial coverage → explicitly refuses to compute one) before
any real sampling data existed.

