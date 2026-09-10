# Power Calibration — First Cut (2026-09-09)

## Status: PARTIAL. Single-instrument detection power measured for EURUSD only. Compound cross-instrument-gate power NOT YET measured — see Section 3.

Per `research/POWER_CALIBRATION_PLAN.md`. Answers, partially, the
question nothing in this project's history has answered: can the
adjudication pipeline detect a real edge of realistic size?

## 1. Method (recap)

Known synthetic edge injected into a random 50% treatment subset of
EURUSD's pooled 100-seed TRAIN-window trades
(`research/null_runs_h004/`), in pips (`edge_pips * pip_value * size`
per trade, EURUSD `pip_value=10.00`). Detection replicates
`research/run_h005.py`'s exact two-gate method (max-group-deviation
permutation test + seed-dispersion check) — the SAME machinery real
hypotheses were adjudicated under, not a looser proxy.

## 2. Result: EURUSD, single-instrument detection curve

| Edge (pips) | Edge (bp equiv., at mean TRAIN entry price 1.14802) | Detection rate (n=20 trials each) |
|---|---|---|
| 2.00 | 1.74 | 0% |
| 2.25 | 1.96 | 0% |
| 2.50 | 2.18 | 25% |
| 2.75 | 2.40 | 60% |
| 3.00 | 2.61 | 85% |
| 5.00 | 4.36 | 100% (n=15) |
| 0.00–1.00 | 0–0.87 | 0% (n=15 each) |

**The single-instrument statistical machinery (permutation test +
seed-dispersion check) is NOT the bottleneck.** Detection crosses 50%
around ~2.6 pips (~2.3 bp) and reaches 85%+ by 3 pips (~2.6 bp). This
is well below the failure threshold the external audit proposed (">15
bp/trade to detect at 80% power" — Phase 1's stated failure condition)
— on this measurement, the single-instrument test could detect an edge
roughly 5-6x smaller than that threshold. This is a genuinely
encouraging finding, and it partially REFUTES one framing of the
audit's power-calibration concern: at least for one instrument, one
statistic, one split design, the core detection machinery works at
economically plausible magnitudes.

## 3. What this does NOT answer, and is very likely where the real story is

**The compound cross-instrument-consistency gate has not been
measured.** Real hypotheses (H-002, H-004, H-005, H-006) were not held
to a single-instrument test — they required consistency across 3-5
instruments simultaneously (direction, significance, and dispersion
all clearing on most/all of them). The external audit's sharpest
specific critique was this compound gate, not the underlying
single-instrument statistic — and this measurement has not touched it
at all. A gate requiring 5 independent ~85%-power tests to ALL pass
would compound to roughly 0.85^5 ≈ 44% even if all 5 instruments truly
carried the identical edge — and real markets don't guarantee identical
edges across instruments, so the true compound power is very likely
lower than that naive calculation. **This is the next measurement, not
a footnote — it is plausibly the entire explanation for the 100% kill
rate, and this document does not yet know either way.**

## 4. Scope limitations of this first cut (disclosed, not hidden)

- **One instrument only (EURUSD).** XAUUSD's pip_value/pip_size are
  structurally different (see `docs/COST_MODEL_V3_SPREAD_FIX.md`'s
  per-instrument table); JPY-pair dynamics differ too. A single-
  instrument curve for one FX major is a start, not a general claim
  about detection power across this project's instrument universe.
- **50/50 treatment/control split**, not the tercile-style (33/67-ish)
  or session-based splits real hypotheses actually used. Split
  fraction affects statistical power directly; this hasn't been swept.
- **`n_permutations=300`, `n_trials=15-20` per edge size** — enough to
  locate the threshold's rough location, not enough for a precise
  confidence interval on the 50%-detection point itself.
- **No swap or realistic cost drag included in the injected trades** —
  this measures detection of a PURE synthetic edge against the null,
  not detection net of the corrected cost model. Combining this with
  the in-flight cost-model re-verification is a natural next step, not
  done here.

## 5. Provenance

Zero new data. Uses `research/null_runs_h004/EURUSD_*` (already
generated, same data H-005/H-008/H-009 used). Injection mechanism
validated via known-answer tests
(`tests/test_synthetic_edge_injector.py`, 9 tests) before this curve
was computed. `load_pooled_trades()` had a real bug caught on its
first real-data run (missing `seed` column extraction from filename —
the file itself doesn't store it) — fixed, regression-tested, and this
curve was computed only after that fix, not before.
