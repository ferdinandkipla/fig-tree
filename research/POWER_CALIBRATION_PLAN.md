# POWER_CALIBRATION_PLAN

**Purpose:** answer the question nothing in this project's history has
answered — can the adjudication pipeline detect a real effect of
realistic size, or does a 100% kill rate mean "no edge exists" and
"this machine rejects everything" are currently indistinguishable?
Per the external audit shared 2026-09-08: "the single most important
insight... run the synthetic-edge power test before anything else."

**Zero new data required.** Reuses `research/null_runs_h004/`'s
existing 100-seed matched-frequency trade sweep, already generated for
all 5 instruments.

## 1. Design

Inject a KNOWN, controlled synthetic edge into real trade timing/sizing
data (not simulated from scratch), then run the SAME detection
machinery real hypotheses were adjudicated under, and measure the
fraction of trials that correctly detect it — the power curve.

**Fidelity to the real pipeline is the whole point.** Replicates the
exact two-gate method `research/run_h005.py`'s `compute_verdict()`
uses (confirmed by direct inspection, not assumed): a max-group-
deviation permutation test (observed `max|group_mean - pooled_mean|`
vs. a shuffled-label null distribution) PLUS the seed-dispersion check
(effect must exceed per-seed group-mean std). A synthetic edge tested
under different or looser machinery than real hypotheses would answer
a different question.

**Injection unit: pips, not basis points.** The external audit's
"+3bp/trade" framing would need a notional/contract-size assumption
this project doesn't currently make anywhere (FX pip_value already
encodes contract size implicitly; XAUUSD's contract size is a separate,
unstated assumption). Using pips keeps this tool consistent with every
existing cost/edge unit in this codebase (`spread_pips`, `pip_value`,
`slippage_pips` all already work this way) instead of introducing a
new unit needing a new, undisclosed conversion. A rough bp-equivalent
is reported alongside for interpretability, computed FROM the pip
injection, not the other way around.

**Split design:** treatment/control mimics a binary conditioning
variable (the shape H-002/H-004/H-005/H-006 all tested — a tercile or
category split). Randomly assign each pooled trade to treatment/control
at a fixed fraction (default 50/50), inject the known pip edge into
treatment's `pnl` only, run the detection test, repeat across many
independent random splits AND across which seeds are sampled, at each
injected edge size, to get a detection RATE (not a single pass/fail).

**Cross-instrument-consistency power, tested separately:** per the
audit's critique that the hard cross-instrument gate may reject real
effects too aggressively, also measure: inject the SAME true edge into
ALL 5 instruments independently, and report what fraction of trials
have ALL 5 (or some threshold) individually clear detection AND agree
in sign — this is the actual power of the compound gate real
hypotheses were held to, not just the single-instrument test.

## 2. Validation before any power curve is trusted

Known-answer test: inject an edge, confirm the resulting treatment-
group mean `pnl` shifts by EXACTLY the injected amount (pips × pip_value
× each trade's own size, summed and averaged) — cascade-immune,
touches no null-distribution machinery, isolates the injection
mechanism itself from the detection statistic.

## 3. What this does NOT do

- Does not modify any existing hypothesis's verdict, registration, or
  the FDR ledger. This is a new, standalone analysis tool.
- Does not touch `execution/simulator.py`, `execution/costs.py`, or
  any simulation-core file.
- Does not claim to calibrate the CROSS-INSTRUMENT gate's power
  precisely on the first pass — the compound-gate measurement (Sec 1)
  is a first cut, reported honestly as such.

## 4. Output

A power curve per instrument (detection rate vs. injected pip edge)
and one compound-gate curve, reported as a new document
(`research/registry/POWER_CALIBRATION-2026-09.md`), not folded into
any existing hypothesis's STATUS section.
