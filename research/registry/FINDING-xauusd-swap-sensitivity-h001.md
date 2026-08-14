# Finding: XAUUSD H-001 percentile shift under cost model v2 — swap-driven, not depth-driven

**Status:** Logged finding, NOT a registered hypothesis. No verdict change to
H-001 (still KILLED). Gated interpretation — see Section 4.

## 1. Context: two comparison artifacts caught and controlled before this
finding could be trusted

Re-verifying H-001 under cost model v2 required recomputing `pnl` for both
the real-strategy trades and the 100-seed null distribution. Two
methodology traps surfaced during that process, both caught before being
trusted:

**Trap 1 — git-history provenance.** The committed `H-001-verdict.csv`
(commit `5eef111`) predates cost model v2 entirely — confirmed both legs
(`trades_XAUUSD.csv`, `research/null_runs/`) were internally consistent
under the OLD flat-cost model at that commit (`null_runs/` verified
byte-identical between `5eef111` and HEAD; only `trades_*.csv` changed,
via the cost-model-v2 commits). So the "old" percentiles used for
comparison were genuinely pre/pre, not contaminated by a live-`costs.py`
read against stale cached data.

**Trap 2 — cascade compounding.** `trades_XAUUSD.csv` at HEAD was
regenerated via a full simulator re-run (`tests/test_determinism.py`'s
side effect, per `docs/COST_MODEL_V2_PLAN.md`'s own documented cascade:
`position_size()` compounds off `self.capital`, so every trade after the
first cost-affected one has its `size`, `pnl_gross`, AND `pnl` shift, not
just the corrected trade). The 100-seed null distribution, by contrast,
was recomputed via an isolated per-trade patch (old `size`/`pnl_gross`
held fixed, only the cost term corrected — cascade-immune). Comparing
cascade-compounded real trades against cascade-immune null trades is not
apples-to-apples. **Controlled for** by reconstructing the real-strategy
side the same cascade-immune, patch-only way (old `size`/`pnl_gross` from
the pre-v2 commit, cost term recomputed via live `total_cost()`,
`research/patchonly_v2/trades_{symbol}.csv`) so both legs use identical,
cascade-immune methodology.

## 2. The finding, on the clean comparison

| Symbol | Bin | pct_vs_null (pre/pre, old) | pct_vs_null (post/post, patch-only both legs) |
|---|---|---|---|
| USDJPY | Q1..Q4 | 22 / 54 / 20 / 82 | 26 / 57 / 19 / 81 |
| GBPJPY | Q1..Q4 | 85 / 33 / 5 / 69 | 84 / 30 / 3 / 69 |
| XAUUSD | Q1..Q4 | 16 / 1 / 38 / 60 | **89 / 69 / 91 / 92** |

USDJPY and GBPJPY move a few points, no bin crosses a new extremity
threshold. **XAUUSD shifts hard and uniformly across all four bins**,
surviving the clean pre/pre vs. post/post (both cascade-immune)
reconstruction — this is not an artifact of either trap in Section 1.

## 3. Does this change the H-001 verdict? No.

`research/registry/H-001.md`'s kill criteria require (a) direction
consistency across instruments and (b) the best bin being the deepest
quartile (strict monotonic claim). Under corrected costs, XAUUSD's best
bin is Q4 (92, shallowest), not Q1 (89, deepest) — same failure mode as
the original verdict, via a different mechanism. **H-001 remains
KILLED.**

## 4. Interpretation — gated, not a characterization candidate

The shift is *uniform* across all four ema_distance bins, not
concentrated in the deep-pullback bins. That shape is the signature of a
flat/near-flat cost effect, not a depth-dependent one — consistent with
mechanism, not coincidence: it tracks XAUUSD's swap-rate asymmetry
(long −53.763, short +36.931 per lot, `execution/costs.py`
`SWAP_RATES`), the single largest and most asymmetric term in the entire
snapshot, sourced from a demo account and explicitly flagged in that
module's own docstring as sign-asymmetry-unverified.

**Swap footprint, quantified (closes the loop, not just consistent with
it):** across the 216 XAUUSD TRAIN trades (patch-only reconstruction,
all long, direction=1), mean rollover exposure is 1.72 nights/trade
(26.9% of trades cross zero rollover boundaries and are correctly
unaffected). Summing `execution/costs.py`'s `swap_cost()` per trade
gives a total swap cost of **+$13,322.61**. The total observed `pnl`
shift (patch-only post minus pre-v2) across the same 216 trades is
**−$13,296.37** — i.e. the swap term alone accounts for 100.2% of the
total shift, a 0.2% residual consistent with the independent, much
smaller effect of Commit 1's spread/slip size-scaling fix (mean
$0.28/trade). **The shift is explained by the swap mechanism, not merely
consistent with it** — there is no unaccounted residual raising a
separate open question.

**A "signal" whose existence is wholly contingent on the single
least-trustworthy input in the cost model is a sensitivity result, not a
characterization candidate.** No registration interest in this pattern
is warranted until the XAUUSD swap rate is re-sourced from a verifiable
(non-demo, live-account or broker-published) source. This was already an
acceptance-gate item (`docs/PROJECT_STATE.md` §7, "Outstanding
engineering debt"); this finding promotes its priority — it is now also
gating a specific, already-observed pattern, not just a generic
data-quality caveat.

**Falsifiable prediction, pre-registered here:** because the shift is
arithmetically explained by the swap term (not merely correlated with
it), this pattern makes a specific, checkable prediction about a future
event. When the XAUUSD swap rate is re-sourced from a verified source: if
the verified long/short rates are materially smaller in magnitude than
the current placeholder-quality −53.763/+36.931, or materially less
sign-asymmetric, this percentile pattern should shrink or vanish on
recompute. If it persists under a verified, materially different rate,
that would falsify the swap-mechanism explanation given here and reopen
the question of what's actually driving it.

## 5. Provenance disclosure — standing rule from H-009, applied here

TRAIN-window outcome data for XAUUSD's ema_distance × cost-model
interaction has now been observed, under corrected costs, outside any
pre-registered test. **Any future hypothesis touching XAUUSD pullback
depth, XAUUSD swap sensitivity, or XAUUSD cost-stress behavior must
disclose this observation in its mechanism memo** and carries the
weaker evidentiary starting position that follows from having seen
TRAIN data first (same standing as the H-009 wrong-sign-momentum-flow
disclosure note). This applies regardless of how much time passes or
how the hypothesis is later motivated.

## 6. Corroboration from H-002 — same signature, and a sharper implication

H-002 (session structure in the null model) was re-verified separately
(`research/H-002-verdict-v2.csv`, `research/run_h002_v2.py`) and does not
change verdict — USDJPY alone already broke the binding cross-instrument
consistency criterion in both the original and corrected runs. But
XAUUSD's own numbers move the same way as here: p-value 0.353 → 0.0000,
and the effect-vs-seed-noise flag flips from "smaller than noise" to
"larger than noise." This is not merely "the same phenomenon again" —
it is stronger evidence than a percentile shift, because a p-value
crossing from non-significant to nominally significant means that, under
corrected costs, XAUUSD's session means would have looked like a real
result had the original H-002 adjudication been run against them in
isolation. The verdict survived only because a *different* instrument
broke the binding criterion first — not because XAUUSD's own number was
safe. See Section 7 for H-003's independent confirmation of this same
capability, in a stronger form (a criterion-level sign flip, not just a
significance-threshold crossing).

## 7. Addendum — H-003: XAUUSD delta sign FLIPS (criterion-level, not overall verdict)

Unlike H-001/H-002 (percentile shifts, no verdict change of any kind),
H-003's XAUUSD **Δ(A−B) flips sign**: −4.90 (pre) → **+56.91** (post),
patch-only reconstruction of the committed `research/h003_runs/`
Arm A/B trade files (`fb5b813`, predates cost model v2, confirmed
byte-identical to HEAD). USDJPY (−3.97 → −7.52) and GBPJPY (−1.70 →
−3.54) move further negative, same direction as before — no flip.

**H-003's overall verdict does NOT change.** The registered kill
criterion ("Δ(A−B) ≤ 0 on any instrument") is independently sufficient
per instrument; USDJPY and GBPJPY still trigger it on their own. H-003
remains KILLED. But XAUUSD's individual contribution to that kill is
gone — it would no longer support the verdict standalone.

**Mechanism, arithmetically closed (not just consistent):** Arm B holds
trades far longer than Arm A by construction (time-exit disabled,
`max_bars_in_trade` 500 vs 10) — mean rollover exposure 3.33 nights/trade
(Arm B, n=83) vs 1.65 nights/trade (Arm A, n=99). Mean swap cost per
trade: −$123.91 (B) vs −$62.09 (A) — Arm B is penalized roughly double.
That per-trade differential (−$61.81, B's extra swap burden relative to
A) exactly matches the observed Δ(A−B) swing (+61.81, to the cent). This
is not a new phenomenon — it's the same XAUUSD swap-asymmetry root cause
as Sections 2–4, now expressed through differential holding-period
exposure between two arms rather than a static per-bin shift. Same gate
applies: sensitivity result, not a characterization signal, pending
swap re-sourcing.

**Sharper stakes, made explicit (from the H-002 corroboration, Section
6):** H-002's XAUUSD p-value moved from 0.353 (not nominally
significant) to 0.0000 under corrected costs — meaning had the original
H-002 adjudication run under today's cost model, XAUUSD's session means
would have looked nominally significant on their own. The verdict
survived only because the binding cross-instrument-consistency criterion
was already broken by USDJPY, not because XAUUSD's own number was safe.
H-003 now shows the same capability in a different form: the swap term
alone is large enough to flip a per-instrument kill criterion's sign.
**The swap number isn't just moving percentiles — it's capable of
manufacturing (or erasing) nominal significance and criterion-level
verdicts on its own.** This is not a reason to reopen H-003's overall
verdict (still safely killed by two other instruments), but it is the
sharpest argument yet for why registration interest in any XAUUSD
pattern must stay gated until the swap rate is re-sourced from a
verified source — a future hypothesis that happened to lean on XAUUSD
alone, without USDJPY/GBPJPY backup, would not have this safety margin.


## 8. H-004 — third confirmation, and the nominal-significance count crosses the registration's own threshold

H-004 (session structure, 1H primary across 5 instruments) reruns clean:
PRIMARY CLAIM stays KILLED, `effect_exceeds_noise` stays False for all
5 primary instruments in both pre- and post-v2 runs — the same
seed-dispersion safety mechanism that saved H-002 and H-003 saves H-004
too.

But the nominal significance count (p<0.05, before the dispersion check)
moves from **2/5 to 4/5** among the primary instruments — crossing the
registration's own stated bar ("need >=4/5") for the first stage of the
primary claim check:

| Symbol | pre p-value | post p-value |
|---|---|---|
| USDJPY | 0.012 (sig) | 0.001 (sig) |
| XAUUSD | 0.793 | **0.000 (newly sig)** |
| GBPJPY | 0.000 (sig) | 0.000 (sig) |
| EURUSD | 0.450 | 0.393 |
| AUDUSD | 0.674 | **0.019 (newly sig)** |

XAUUSD drives the largest single move, consistent with Sections 2/6/7.
AUDUSD also newly crosses significance — its swap rates (−2.231 long /
−4.739 short) are far smaller and much less asymmetric than XAUUSD's,
so a comparable-direction move here is a weaker, secondary data point,
not yet its own finding — worth watching in H-005/H-006, not yet
concluding anything about.

This is a second concrete instance (after H-003's Section 7 criterion
flip) of Section 6's warning made literal: the swap correction alone is
now capable of pushing a hypothesis's nominal significance count across
a pre-registered pass/fail threshold. H-004's overall verdict is safe
only because the dispersion check is a second, independent gate — a
hypothesis whose registration didn't include that gate would not have
this protection.

## 9. H-005 — fourth confirmation, same pattern

H-005 (volatility regime, ATR-at-entry terciles) reruns clean: overall
verdict stays KILLED, `effect_exceeds_noise` False for all 5 in both
runs. XAUUSD's p-value moves 0.116 → 0.000 (crosses p<0.01), and
`worst_tercile` moves from T2 to T1 for XAUUSD specifically (best stays
T3 in both). Instruments clearing FDR p<0.01 goes 1/5 → 2/5 (GBPJPY
alone → XAUUSD + GBPJPY). Same signature, same order of magnitude, no
independent arithmetic closure run here — the mechanism is not new
information at this point (Sections 2, 7, 9, 11), and the dispersion
gate holds the kill the same way it has for every hypothesis so far.

## 10. H-006 — day-of-week: a structural confound, not a magnitude one, self-manufactured this session

H-006 (day-of-week effects) is categorically different from Sections 6,
8, 9: it doesn't just move a p-value or a delta — it **flips a registered
kill sub-criterion from failed to passed**. Old best days: {Thursday
(4x), Friday (XAUUSD)} — not consistent. New best days: {Thursday (5x)}
— consistent, for the first time. XAUUSD's own `best_day` moves Friday
→ Thursday.

**This is the first genuine verdict-flip candidate of the
re-verification, and it required the full stop-and-decide protocol, not
an addendum line** — checked before writing anything here. Two things
had to hold:

**1. Does the overall verdict actually flip?** No. H-006's primary claim
requires `consistent_best AND n_sig_and_real >= 4` (both gates). Under
corrected costs `effect_exceeds_noise` stays False for all 5 instruments
(0/5 clear both gates, same dispersion-check gate that held H-002/H-004/
H-005) — so **H-006 stays KILLED**, independently of the consistency
flip. If the dispersion check had not held, this would be a genuine
overall verdict flip requiring registry-level reversal, not documentation.

**2. Is the flip a real pattern or a self-manufactured artifact?** This
hypothesis has a structural hazard the earlier five don't: the rollover
convention we chose and stated as an assumption (weekend-carry,
Wednesday charged 3×) is **itself day-of-week-structured**. Testing
"day-of-week effects" under a cost model whose costs vary by day of week
is not a clean test — for a large-negative-long-swap instrument
(XAUUSD, again), it's liable to manufacture a day-of-week pattern with
zero market content.

**Verified, closing arithmetic (same discipline as Sections 2, 7):**
mean swap cost by XAUUSD entry day (pooled, 100 seeds, TRAIN):

| Day | mean swap cost | mean pnl shift | residual |
|---|---:|---:|---:|
| Monday | $5.68 | −$6.01 | −$0.33 |
| Tuesday | $5.72 | −$6.11 | −$0.39 |
| Wednesday | $11.69 | −$12.06 | −$0.37 |
| Thursday | $3.23 | −$3.57 | −$0.34 |
| Friday | $13.87 | −$14.20 | −$0.34 |

The residual is small (~4.4% in aggregate) **and flat across all five
days** — it does not itself vary by day, which is what confirms it's
the same independent spread/slip size-scaling effect identified in
Section 2 (H-001), not a second, unexplained day-of-week mechanism. The
swap term alone accounts for the shift. Thursday has the lowest mean
swap cost of any weekday by a wide margin (3.23 vs. 11.7–13.9 for
Wed/Fri) — that is mechanically why Thursday becomes "best" under
corrected costs. **The consistency flip is a cost-convention artifact
interacting with the calendar, not a finding about market structure.**

**Standing methodological note (goes alongside the H-009 provenance
rule, Section 5):** any future day-of-week or calendar-proximity
hypothesis on a high-swap-asymmetry instrument must explicitly state how
it separates a real calendar effect from the rollover convention's own
day-of-week structure (Wednesday 3×, weekend carry) — e.g. by
re-running under a flat/symmetric synthetic cost model as a robustness
check, or by pre-registering the swap-adjusted null. This confound was
introduced by our own modeling choice this session, not inherited from
the data — worth stating plainly rather than treating it as an external
data-quality issue like the swap rate's demo-account sourcing (Section
4).

**H-009 exemption, reconfirmed explicitly (a reader will ask, given this
section):** H-009 (month-end proximity × volatility) was adjudicated
pre-cost-model-v2, and — per the exposure-list correction made explicit
in the prior session before this re-verification began — it never reads
or touches `pnl` in its adjudication logic (it operates on price/ATR
features only). It remains outside the cost-model-v2 exposure list on
that basis; this H-006 confound does not reopen that exemption, since
H-009's calendar variable was never passed through the cost model at
all, day-of-week-structured or otherwise.

## 11. Consequence for the re-verification in progress

- H-001, H-002: CONFIRMED KILLED under cost model v2, no verdict change,
  XAUUSD shows the swap signature (Sections 2, 6).
- H-003: CONFIRMED KILLED under cost model v2 at the overall level;
  XAUUSD's individual kill-criterion contribution flips (Section 7).
- The cascade-immune, patch-only methodology (Section 1, Trap 2) is
  validated across three hypotheses now (H-001, H-002, H-003) and is the
  required approach for the remaining items (H-004 through H-006, M2).
- **Pre/post source declared before running, per H-003's own discipline
  (this section written before H-004 begins):** for any remaining
  hypothesis whose adjudicating data isn't already sitting in a
  pre-cost-model-v2 commit the way `research/h003_runs/` was, a fresh
  script invocation under live (HEAD) `execution/costs.py` produces a
  POST-side artifact only — it cannot retroactively serve as a pre-v2
  baseline. If no pre-v2 committed artifact exists and none can be
  reconstructed via the patch-only method, the correct output is a
  disclosed limitation ("recomputed verdict confirmed under v2;
  before/after comparison not fully reconstructable"), not a silent
  single-sided pass.
- Every symbol's real-strategy re-verification gets the same before/after
  table, not just a pass/fail, even when boring — the boring USDJPY/GBPJPY
  rows are what make the XAUUSD rows interpretable (H-001 Section 2,
  H-003 Section 7).

## 12. M2 — final re-verification item, same conclusion, XAUUSD strongest yet

M2 (signed, drift-neutral null model) reruns clean using the same
patch-only methodology: `research/null_runs_signed_v2/` (300 files,
pnl recomputed via live `total_cost()`) against
`research/patchonly_v2/trades_{symbol}.csv` (the same pre-v2-commit,
patch-only real-strategy reconstruction already built for H-001 — this
file happens to span the full backtest window, not just TRAIN, which
matches what `real_strategy_expectancy_pf()` requires; confirmed by
exact match of its old mean pnl, 4.2497, to the originally committed
`real_expectancy` for XAUUSD).

**Core conclusion unchanged and, if anything, sharpened.** M2's finding
was that the real strategy does not reliably exceed the signed,
drift-neutral null (`above_p95` == False for all three instruments,
both pre- and post-v2). That holds exactly under corrected costs — no
instrument crosses into "beats null" in either direction of the
comparison:

| Symbol | pre: real vs null | post: real vs null |
|---|---|---|
| GBPJPY | below p05 (underperforms) | **within range** (softens) |
| USDJPY | within range | within range (unchanged) |
| XAUUSD | within range | **below p05 (underperforms)** |

GBPJPY's classification softens (from "clearly worse than null" to
"indistinguishable from null") but doesn't reverse direction — still
not beating null either way. XAUUSD moves the opposite way, into a
stronger underperformance classification, for the now-familiar reason:
real_expectancy collapses from +4.25 to −57.31 (real_pf 1.09 → 0.31),
closed by the identical swap arithmetic used in Section 2 — total swap
cost $13,322.61 against a total pnl shift of −$13,296.37 across the same
216 trades, 0.2% residual. No new arithmetic needed; same mechanism,
same closure, larger magnitude because M2's real-strategy dataset spans
the full 2019–2024 window rather than TRAIN-only.

**No verdict flip. This closes the cost-model-v2 re-verification.**
Final scorecard across all six exposed hypotheses plus M2:

| Item | Verdict pre-v2 | Verdict post-v2 | XAUUSD signature present |
|---|---|---|---|
| H-001 | KILLED | KILLED | Yes (Section 2) |
| H-002 | KILLED | KILLED | Yes (Section 6) |
| H-003 | KILLED | KILLED | Yes — criterion-level flip, absorbed by other 2 instruments (Section 7) |
| H-004 | KILLED | KILLED | Yes — nominal-sig count crosses threshold, absorbed by dispersion gate (Section 8) |
| H-005 | KILLED | KILLED | Yes (Section 9) |
| H-006 | KILLED | KILLED | Yes — consistency criterion flip, absorbed by dispersion gate; structural confound identified and closed (Section 10) |
| M2 | no-beat-null | no-beat-null | Yes — strongest single-symbol shift, softens GBPJPY's classification |

Zero overall verdict flips across seven items. Three near-misses
(H-003, H-004, H-006) where a sub-criterion flipped and a second,
independent gate (either a different instrument or the dispersion
check) held the line — worth registering as a general observation: this
adjudication pipeline's redundant-gate design (requiring multiple
independent criteria to jointly hold, rather than any single statistic)
is exactly what kept seven cost-model-sensitive re-verifications from
producing a single false survival. That redundancy should be treated as
load-bearing infrastructure going forward, not incidental.
