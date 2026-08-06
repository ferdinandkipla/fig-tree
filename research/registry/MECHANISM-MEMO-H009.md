# Mechanism Memo: Month-End Proximity x High-Volatility Interaction (H-009 candidate)

## Status: MEMO DRAFTED. Not yet registered -- occupancy check pending (Section 6).

Per `research/CONDITIONAL_SEARCH_CHARTER.md`'s sequencing rule: this
memo, including the full conditioning-variable definition and sign
structure, is committed BEFORE the occupancy check is run and BEFORE
any outcome (reversion) data is examined. This is a distinct hypothesis
from the rejected day-of-week x volatility candidate
(`NO-CANDIDATE-daydow-x-volatility.md`), surfaced BY that rejection's
analysis but not a rescue of it -- see that document's Section 4.

## 1. Mechanism

Month-end (and, more strongly, quarter-end) portfolio rebalancing and
fixing-adjacent flow is systematically concentrated in the last one to
two business days of the calendar month. This flow (index rebalancing,
fund NAV-driven repositioning, corporate/treasury month-end hedging
rolls) is largely informationless about future direction -- it is
executed to satisfy calendar-driven mandates, not because the
executing party has a directional view. Under normal (mid-month, mid-
volatility) conditions, market depth absorbs this flow with limited
lasting price impact. The prediction is specifically about STATE-
DEPENDENCE: when this flow coincides with an already-thin/high-
volatility state, the same flow produces a larger, more visible price
displacement that partially reverts once the flow completes -- the
same "shock absorbed poorly by insufficient depth, then corrects"
structure as H-008's mechanism, but conditioned on calendar proximity
to month-end rather than session.

**Counterparty:** the executing rebalancers/fixers themselves are the
counterparty -- systematically informationless about direction (they
trade on a calendar mandate, not a forecast), which is exactly why a
temporary, reverting impact is the predicted signature rather than a
persistent one. A persistent (non-reverting) effect would look more
like genuine information and would NOT be consistent with this
mechanism -- an important distinguishing prediction from a garden-
variety momentum story.

## 2. Why this survives where day-of-week x volatility did not

Per `NO-CANDIDATE-daydow-x-volatility.md` Section 2b: month-end flow is
a day-of-MONTH phenomenon. The rejected candidate's failure was using
the wrong conditioning variable (day-of-week) for this exact
mechanism. This candidate uses the correct variable instead: business-
days-to-month-end, a new derived column (Section 3), not H-006's
weekday partition.

**Timescale honesty (the WMR lesson applied here):** unlike the WMR
4pm-fix mechanism (rejected for being sub-hourly, invisible at 1H),
month-end/quarter-end flow is understood in the literature to persist
over hours to roughly a day around the actual month-end date, not
minutes -- this is the one candidate among the three originally
considered where the timescale question is genuinely open rather than
pre-answered against it at 1H granularity. This memo does not claim
certainty on this point; it is why an occupancy check (denominators
only) precedes registration rather than assuming power.

## 3. Conditioning variable: FROZEN definition (`research/calendar_distance.py`)

- **Business day** = Monday-Friday by calendar weekday. Holidays NOT
  modeled (stated simplification, not oversight -- see module
  docstring for full reasoning).
- **Month-end** = last calendar day of the month, adjusted backward to
  the preceding Friday if it falls on a weekend.
- **bars_to_month_end(d)** = business days from d to month-end,
  inclusive counting such that the month-end business day itself = 0.
- **Near-month-end window: `bars_to_month_end(d) <= 1`** -- the
  month-end business day and the one immediately before it. Frozen at
  this width now, not tuned after seeing occupancy counts or outcomes.
  (Widening this window later to fix a power problem would be exactly
  the collapsing-bins-after-looking escape hatch the charter's
  sign-specificity rule exists to close -- if 2 days is underpowered,
  the honest verdict is "underpowered as scoped," not "widen and
  re-check.")
- **Quarter-end month** = month in {3, 6, 9, 12}.

Full known-answer validation: `tests/test_calendar_distance.py`
(12 tests, including the June-2024 weekend-adjacent month-end case),
run and passing BEFORE this memo's occupancy check (Section 6) or any
outcome data was touched.

## 4. Volatility conditioning

Reuses H-005's frozen per-instrument TRAIN ATR terciles exactly
(`research/registry/H-005-bins.json`), top tercile vs. pooled rest --
same convention as H-008, for the same reasons (dimensional coherence,
zero new researcher degrees of freedom, comparability to the marginal
test it conditions on).

## 5. Prediction and sign structure (falsifiable, pre-committed)

- **Cell of interest:** near-month-end (bars_to_month_end <= 1) x
  top-ATR-tercile bars, pooled across all 5 instruments (this
  mechanism has no instrument-class asymmetry prediction analogous to
  H-008's thin/home split -- rebalancing flow is not specific to any
  one instrument's home session). Reversion metric: identical
  definition to H-008 Section 3c (signed reversion against the
  triggering bar's own return direction), 3-bar primary window / 1-bar
  secondary non-adjudicating, same reasoning as H-008 (flow-driven
  correction is not an instantaneous next-bar phenomenon).
- **Refutation clause 1 (interaction, not marginal):** the effect must
  be concentrated in near-month-end x high-vol cells specifically.
  If reversion appears equally across ALL volatility regimes near
  month-end (i.e., a marginal day-of-month effect with no volatility
  state-dependence), the INTERACTION claim -- the actual content of
  this mechanism -- is refuted, even if a marginal calendar effect
  exists. This mirrors H-008's own refutation-clause structure and
  guards against this quietly degrading into "H-006 but with better
  calendar bins."
- **Refutation clause 2 (persistence check):** if the near-month-end
  x high-vol effect does NOT revert (i.e., the k=3 signed effect
  continues in the SAME direction as the triggering bar rather than
  against it), that is inconsistent with an informationless-flow
  mechanism and refutes this memo's specific counterparty story, even
  if some effect exists.
- **Quarter-end margin (pre-committed, not a free parameter):** the
  flow story predicts quarter-ends (Mar/Jun/Sep/Dec) show a STRONGER
  near-month-end x high-vol effect than ordinary month-ends, since
  quarterly rebalancing mandates are larger than monthly ones. This is
  reported as a secondary, visibly-falsifiable margin -- a null result
  here (no quarter-end/month-end distinction) does not by itself kill
  the primary claim, but a REVERSED distinction (ordinary month-ends
  stronger than quarter-ends) would be a specific, disclosed
  embarrassment for the mechanism story, stated here so it can't be
  quietly dropped from the writeup later.

## 6. Occupancy check (denominators only -- no outcome data)

Per this session's power-arithmetic requirement: before registration,
count how many top-ATR-tercile bars fall in the near-month-end window
per instrument, using ONLY the conditioning variables (calendar
position, ATR tercile membership) -- zero outcome/reversion data
touched. If any instrument's near-month-end x high-vol cell has fewer
than 30 TRAIN-window events, the honest verdict is "underpowered at
this granularity, not testable," recorded as a scoping fact rather
than run anyway to harvest an ambiguous kill. See companion commit for
the occupancy check result and the resulting registration/no-candidate
decision.
