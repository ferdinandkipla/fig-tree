# NO-CANDIDATE: Day-of-Week (H-006) x Volatility Regime (H-005) Interaction

## Status: REJECTED at mechanism-memo stage. Not registered. No hypothesis ID assigned.

This document is committed as a first-class Branch B evidence artifact,
per `research/S1_STOPPING_RULE.md` and `research/CONDITIONAL_SEARCH_CHARTER.md`
Section 3's own standard: "if no candidate clears the mechanism bar
honestly, that's signal too, and it counts toward Branch B rather than
being forced." This is the first documented instance of the mechanism
bar rejecting a candidate before registration -- evidence the bar has
actual binding force, not just nominal existence.

## 1. The candidate as originally scoped

Interaction between two already-killed marginals: volatility regime
(H-005, killed -- direction inconsistent across instruments) and
day-of-week (H-006, killed -- Thursday best 4/5 but 0/5 exceed noise).
Proposed conditioning variable: H-005's frozen ATR terciles x H-006's
weekday partition (reused, zero new data, zero new derivation).

## 2. Named mechanisms considered, and why each fails at weekday resolution

A defensible interaction memo needs ONE named mechanism with a
counterparty story and a falsifiable sign pattern -- not a portmanteau
where any observed day pattern could be claimed post-hoc as consistent
with "some calendar effect." Three real, named candidate mechanisms
were examined, mapped against the actual conditioning variable
(day-of-week), and each fails for a distinct, disqualifying reason:

### 2a. FX option expiry (NY 10am ET cut)

**Fails: wrong cycle, and the version that would be real needs data
this project doesn't have.** The dominant cut effect in FX options is
DAILY (a 10am NY cut occurs every business day), with pinning/gamma
effects concentrated around expiry dates for large-open-interest
strikes -- not tied to a fixed weekday. There is no clean day-of-week
signature to test at all. The version of this mechanism that IS real
("is today an expiry date for a large-OI strike near current spot")
requires strike and open-interest data this project has never sourced
and is not derivable from OHLC timestamps. This isn't a data-cost
problem solvable by more derivation -- it's a data mechanism that
doesn't reduce to weekday bins under any honest operationalization.

### 2b. Month-end / quarter-end rebalancing flow

**Fails at day-of-week resolution specifically -- but see Section 4,
this is NOT a rejection of the underlying mechanism.** Month-end
rebalancing is a day-of-MONTH effect (proximity to the last business
day, or to quarter boundaries), not a day-of-week effect. It smears
across all five weekdays over a multi-year TRAIN window -- the last
business day of a given month can fall on any weekday depending on the
calendar, so H-006's weekday partition is testing a variable that has
no structural relationship to the actual proposed mechanism. Using
H-006's frozen weekday bins to test this mechanism would be
methodologically dishonest: convenient (zero new derivation) but wrong.

### 2c. WMR 4pm London fix

**Fails on timescale, not on mechanism validity.** This is the
best-evidenced of the three named mechanisms -- real documented flow
impact, real regulatory history (the 2013-14 FX fixing enforcement
actions). But the effect window is minutes around 4pm London. This
project's finest granularity is 1H bars; a bar spanning roughly
3:30pm-4:30pm London does not isolate the fix window, it dilutes a
sub-hourly effect inside 55 minutes of unrelated price action. The
mechanism is very plausibly real; it is very plausibly invisible at
the only granularity available here. Recording this as a timescale
limitation of the DATA, not a defect in the mechanism argument.

## 3. Ruling

None of the three named mechanisms survives conditioning on
day-of-week specifically. Two (expiry, month-end) fail because
day-of-week is the wrong variable for their actual cycle; the third
(WMR) fails because 1H is the wrong granularity for its actual
duration. A memo that proceeded anyway -- testing H-006's weekday bins
against volatility regime without naming which mechanism licenses the
prediction -- would be exactly the portmanteau the charter's mechanism
bar exists to prevent: a structure where any observed weekday pattern
could be retroactively attached to whichever of the three stories fit
best. That is not registered.

**This candidate, AS SCOPED (day-of-week x volatility), is a
documented no-candidate outcome.**

## 4. What this does NOT rule out

Section 2b's analysis surfaces a DIFFERENT, more defensible candidate:
month-end proximity (a calendar-distance variable, not day-of-week) x
volatility regime. This is not a rescue of the rejected candidate --
it is a distinct hypothesis with a distinct conditioning variable that
this rejection analysis happened to surface. It is tracked and
evaluated separately (see `MECHANISM-MEMO-H009.md` if it survives its
own occupancy check) specifically so this document is not quietly
retargeted into a different candidate. If a future session encounters
this file, the correct reading is: "day-of-week x volatility is
closed, permanently, for the three mechanisms examined here" -- not
"a workaround was found."

## 5. Provenance

- No reversion, return, or any outcome statistic was computed at any
  point during this analysis. The rejection is entirely on mechanism
  and calendar-cycle grounds, decided before any data beyond existing
  frozen bins (`H-005-bins.json`) and existing session/day labels was
  examined.
- Counts as 1 of the Batch 2 budget's non-adjudicating "no-candidate"
  outcomes for the purpose of tracking how thin the zero-new-data
  interaction space is turning out to be -- relevant context if a
  second no-candidate occurs (see `research/S1_STOPPING_RULE.md` on
  when remaining budget should redirect toward
  data-onboarding-gated candidates).
