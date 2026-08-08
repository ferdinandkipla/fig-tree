# NO-CANDIDATE: Killed x Killed Interactions, Outside the Session Family

## Status: SURVEYED, ALL THREE PAIRS REJECTED at pre-drafting screen. No memo drafted. No hypothesis ID assigned.

Committed per the same standard as
`NO-CANDIDATE-daydow-x-volatility.md` -- a failure to construct a
defensible mechanism counts as Branch B evidence. This document makes
a STRONGER claim than that one: it is not one pairing failing its own
memo, it is the **complete enumeration of the zero-new-data killed x
killed candidate pool, exhausted**.

## 1. Scope of the survey

Per `research/CONDITIONAL_SEARCH_CHARTER.md`'s priority ordering,
zero-new-data interactions between already-killed marginals rank above
anything requiring exogenous or newly-onboarded data. The session
family (H-002, H-004) is spent -- adjudicated via H-008. Day-of-week
(H-006) is spent -- rejected via `NO-CANDIDATE-daydow-x-volatility.md`.
The remaining killed-marginal inventory is exactly three hypotheses:
H-001 (pullback depth), H-003 (time-exit value), H-005 (volatility
regime -- already used as a CONDITIONING variable in H-008/H-009, but
its own marginal finding remains available as a pairing partner). This
yields exactly three distinct pairs. All three are surveyed below;
none survives pre-drafting screening.

## 2. H-001 x H-003 (pullback depth x time-exit value)

**Mechanism sketch:** pullback-depth entries only realize value under
a specific exit-timing regime -- e.g. shallow pullbacks need to be held
longer to resolve, deep pullbacks resolve faster and get clipped by a
fixed time exit.

**Rejected: appearance-plus-kinship, STRONGER grounds than the
disqualified H-001 x trend-state pairing.** This is not merely
touching the retired `trend_pullback` strategy's entry logic (as
H-001 x trend-state did) -- it is entry-style x exit-style of the SAME
retired strategy, its two literal original parameter axes, recombined
in interaction form. Re-testing this combination is closer to a full
`trend_pullback` resurrection than the already-disqualified pairing
was. Rejected without drafting, same standard as
`CONDITIONAL_SEARCH_CHARTER.md` Sec 4a.

## 3. H-001 x H-005 (pullback depth x volatility regime)

**Mechanism sketch (best honest attempt):** shallow pullback entries
reflect genuine order-flow exhaustion only when volatility is elevated
(more participation, more information content in the move); in
low-vol grind conditions the same shallow pullback is noise.

**Counterparty argument, constructed honestly, and it fails in the
same paragraph it's built:** the nearest real counterparty story is
retail stop-placement clustering at shallow retracement levels,
creating predictable liquidity that gets swept in high-volatility
conditions. But that is a STOP-HUNTING mechanism -- it predicts
CONTINUATION through the pullback level (the sweep triggers stops,
which adds to the move), not reversion from it, which is the opposite
of what this hypothesis's own "order-flow exhaustion" framing
predicted going in. Worse, stop-hunting is an intraday microstructure
phenomenon, likely invisible at 1H for the same timescale-mismatch
reason WMR fixing was ruled out in the day-of-week survey
(`NO-CANDIDATE-daydow-x-volatility.md` Sec 2c). Constructing the
counterparty argument honestly kills the hypothesis rather than
supporting it. Rejected -- no defensible mechanism survives contact
with its own counterparty question.

## 4. H-003 x H-005 (time-exit value x volatility regime)

**Mechanism sketch:** a fixed-time exit clips positions before natural
resolution in low-vol regimes (moves take longer to develop) but is
well-matched to high-vol regimes (moves resolve faster).

**Cleanest of the three on kinship grounds -- no `trend_pullback`
entry logic involved at all. Rejected anyway: no counterparty exists
by construction.** An exit-timing x volatility interaction has no
exploited party. The counterfactual trader on the other side of a
"better" exit isn't systematically wrong about anything -- they simply
hold a different position for a different duration. This is portfolio
geometry / optimal-stopping-time structure, not a market inefficiency.
Any memo built on this would be a curve-fit of stopping rules wearing
a mechanism costume -- exactly what the charter's mechanism-memo
requirement exists to screen out BEFORE code is written, not after a
kill.

## 5. Conclusion

**The complete zero-new-data killed x killed candidate pool, outside
the session family, is exhausted.** Three pairs surveyed; three
distinct failure modes (kinship; no defensible counterparty despite an
honest attempt; no counterparty by construction); zero survive
pre-drafting screening. This is a stronger Branch B statement than
`NO-CANDIDATE-daydow-x-volatility.md`'s: that document showed one
pairing failing its own memo. This document shows **the cheap tier of
the charter's own priority order (Section 5's zero-new-data ranking)
is empty.**

## 6. Consequence for Batch 2 sequencing

Per `research/CONDITIONAL_SEARCH_CHARTER.md` Section 5's priority
order, the only remaining Batch 2 candidate tier is data-onboarding-
gated (cross-asset conditioning, per Charter Section 4a's note that
this is NOT already in the S1 dataset). That tier is itself gated on
engineering prerequisites that are ALREADY mandatory regardless of
outcome: cost model v2 (swap integration) and AUDUSD real contract
specs are required before ANY hypothesis, Batch 1 or 2, can be
ACCEPTED (`RESEARCH_PROGRAM.md` Sec 6) -- this work is not speculative
investment against an uncertain candidate, it is dead-weight debt that
must be cleared on every branch. Proposed sequence: this no-candidate
commit -> cost model v2 -> AUDUSD real specs -> survey the
data-onboarding-gated candidate tier with the same pre-drafting screen
applied here and in the day-of-week survey. If that survey also
returns empty, Batch 2 concludes early with a defensible record (2
kills, 2 no-candidates, an exhausted priority ladder at every tier
surveyed) and the continue/conclude question reopens on evidence, not
budget exhaustion.

## 7. Honesty note on the scoreboard

`research/S1_STOPPING_RULE.md`'s "8-12 budgeted" figure is a CAP, not
a quota. Nothing in the charter or the stopping rule obliges this
project to manufacture draws to fill that range. This record should
never be read as if 8-12 adjudications are owed -- the stopping rule's
actual content is the pre-committed branch logic (Branch A / Branch B
and its sub-branches), not a target count. Two kills and two
no-candidates, honestly exhausting the cheap tier, is exactly what the
charter's own discipline looks like working as designed.

## 8. Provenance

No outcome data was touched during this survey. All three rejections
are on mechanism/counterparty/kinship grounds, using only prior
findings already on record (H-001, H-003, H-005 STATUS docs;
`LESSONS_LEARNED.md`'s trend_pullback retirement) and the already-
committed day-of-week no-candidate's own reasoning as precedent for
the timescale-mismatch argument in Section 3.
