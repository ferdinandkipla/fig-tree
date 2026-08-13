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

## 6. Consequence for the re-verification in progress

- H-001: CONFIRMED KILLED under cost model v2 (Section 3).
- The cascade-immune, patch-only methodology (Section 1, Trap 2) is now
  the validated approach for the remaining re-verification items
  (H-002 through H-006, M2) — apply the same construction (old
  `size`/`pnl_gross` from the pre-v2 commit + `total_cost()`-corrected
  `pnl`) to both real and null legs for each, rather than mixing a
  cascade-compounded real leg against a patch-only null leg again.
- Every symbol's real-strategy re-verification should get the same
  Section 2-style before/after percentile table, not just a pass/fail,
  since XAUUSD demonstrates the aggregate KILL/SURVIVE verdict can stay
  stable while a materially different — and separately interesting —
  pattern hides underneath it.
