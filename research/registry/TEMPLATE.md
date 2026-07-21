# Hypothesis Registration Template

Copy this file to `research/registry/H-XXX.md` before writing any
binning/analysis code for a new hypothesis. Every section is mandatory.
The worked example (H-001, S0) follows the template.

---

## TEMPLATE

```markdown
# H-XXX: <short name>

## Prior evidence (recorded before test)
What observation motivated this hypothesis? Cite specific numbers from
prior runs, not vague impressions. If there is no prior evidence beyond
"seems plausible," say so explicitly -- don't manufacture false
grounding.

## The survivorship/pseudoreplication trap (if applicable)
Does the naive test condition on an outcome, or pool non-independent
samples? If the naive comparison is invalid for a structural reason
(selecting on survival, pooling seeded draws from the same underlying
series, etc.), name the trap before designing the real test. If no
such trap applies, state that explicitly rather than omitting the
section.

## Prediction (the falsifiable form)
State the DIRECTION and the SCOPE of the claim precisely. If the
natural claim has an unbounded tail (e.g. "deeper is always better"),
bound it to the observed range and say so -- see H-001's amendment for
the exact pattern. Vague predictions that could be satisfied by many
different results are not registrable.

## Test design
- Data window: TRAIN or OOS, and which dates. Default to
  `research/S1_DATA_SPLIT.md`'s boundary unless deviating with
  documented reason.
- Binning/grouping method, computed on TRAIN only if bins are
  data-derived (quartiles, session buckets, etc.) -- see the freeze/verdict
  phase separation pattern in `research/run_h001.py` if bins must be
  frozen before any statistic is computed.
- Null comparison: which null-model data, which seeds, Arm A or B if a
  time-exit-family test, and whether pooling seeds is used (if so, see
  the pseudoreplication template in `research/registry/H-002.md` and
  compute seed-to-seed dispersion alongside any pooled p-value).
- Metric(s), computed identically across arms/bins/instruments.

## Kill criteria (any one refutes)
List them as concrete, checkable conditions -- not "if it doesn't look
good." Include a minimum-evidence threshold (n >= 30 is S0's convention;
define exactly what counts as an "affected" or "eligible" observation
if that's ambiguous -- see H-003's precise definition when arms can
have different trade counts).

## What I will NOT do
The explicit list of moves that would constitute post-hoc rationalization:
re-binning after seeing results, selecting parameters from a descriptive
sweep, unsealing OOS, re-drawing null seeds, relabeling a result to fit
a different (unregistered) pattern.

## Provenance
Registration commit hash goes here once committed -- add it in a
follow-up commit after the initial file is pushed, per the pattern in
H-001/H-002/H-003 (the commit hash IS the timestamp proof; leave a
placeholder like `<commit-hash-pending>` until you have it, don't
compute the hash and mentally note it without writing it back).
```

---

## WORKED EXAMPLE: H-001 (S0), Annotated

The actual H-001 registration (`research/registry/H-001.md`, committed
`3d2f41af955d001c5fe56421c4c5f6209b639f81`) mapped to the template
above:

**Prior evidence** — cited exact figures: "669 trades," Fix #9's effect
on stop/target geometry, the specific commit that regenerated the
trade logs. Not "pullback strategies seem to work sometimes."

**Prediction, bounded** — the original draft claimed monotonic
expectancy "as ema_distance moves from 0 toward -3 ATR." This is
exactly the unbounded-tail problem the template warns about: it
implicitly claims the trend continues past the observed data. The
committed version bounded the claim to "the observed TRAIN-derived
quartile range" and explicitly logged what would NOT be claimed (no
extrapolation past the deepest quartile) -- this is the section to
copy verbatim into any new hypothesis with a directional/depth-style
claim.

**Kill criteria, checkable** — "best bin is not the deepest quartile"
is a condition you can check by reading one column of a table, not a
judgment call. This is why H-001 could be killed cleanly and fast: no
step in the verdict required a subjective read.

**Freeze-then-verdict phase separation** — `research/run_h001.py` has
`--freeze` (computes and commits bin edges, refuses to compute any
statistic) as a SEPARATE CLI invocation from `--verdict` (reads only
the frozen file, never recomputes bins). This structural separation
-- not just a promise in prose -- is what made "resist the temptation
to peek at OOS bins" enforceable rather than aspirational. Copy this
pattern for any hypothesis with data-derived bins.

**What actually happened** — H-001 was killed on TRAIN alone: deepest
bin was not the best bin on 2 of 3 instruments, and direction was
inconsistent across all three. Zero OOS peeking occurred; the
registration's own sequencing made that the only way to reach a
verdict.
