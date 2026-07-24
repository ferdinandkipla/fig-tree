# ZenithFlow Phase 2 — M4 Findings Report

**Date:** 2026-07-19
**Author:** Ferdinand Kiplangat (research/analysis by Claude, per project convention)
**Status:** Phase 2 complete. `trend_pullback` retired. Scoping Phase 3 from evidence below.

---

## AMENDMENT (2026-07-24) — M2's headline finding revised by the S1 signed null

**This section does not replace the original report below — it corrects
one specific claim in it, per this project's standing discipline of
never silently rewriting a committed finding.** The original text is
preserved unchanged after this section.

**What changed:** the S1 long/short redesign built a drift-neutral
("signed") null model — random direction (long or short) per entry,
not just random timing — and ran it at full 100-seed scale
(`research/null_seed_results_signed.csv`, `null_distribution_summary_signed.csv`,
committed at `cef09ea`). Comparing it to the original long-only null
(M2, `research/null_distribution_summary.csv`) isolates how much of the
original null's mean expectancy was directional drift rather than
randomness itself:

| Symbol | Old (long-only) null mean | Signed null mean | Drift estimate | Real strategy | Inside signed band? |
|---|---|---|---|---|---|
| USDJPY | 10.17 | 1.64 | 8.53 | -4.38 | **True** |
| XAUUSD | 12.50 | 2.27 | 10.23 | 4.25 | **True** |
| GBPJPY | 8.58 | 3.38 | 5.21 | -5.29 | False (barely) |

**Most of the original null's $8–12/trade mean was directional drift**,
not an artifact of random entry timing itself — expected for FX/metals,
which (unlike equities) have no structural long-side risk premium to
harvest.

**Revision to Section 3's M2 finding below:** the original claim "real
entries land below the 5th percentile of null on all three instruments"
is **no longer accurate for USDJPY and XAUUSD** under the drift-corrected
benchmark — both now fall *inside* the signed null's band. The corrected
reading: trend_pullback's entries are statistically indistinguishable
from noise on USDJPY/XAUUSD (neither edge nor anti-edge), and GBPJPY
retains weak, not-yet-conclusive underperformance (just below p05, a
much smaller gap than the original comparison suggested).

**What this does NOT change:** H-001, H-002, and H-003's verdicts stand
unrevised — each killed a specific proposed mechanism (pullback depth,
session structure, time-exit value-add) independent of the drift
question, using TRAIN-only tests whose kill criteria don't reference
the long-only null's absolute level. Section 4's overall verdict
(`trend_pullback` retired, no component survived) also stands: a
strategy whose entries are indistinguishable from noise, whose specific
depth/session/exit mechanisms are all separately falsified, is still
not a viable strategy — the correction narrows *why* the entries look
the way they do, it doesn't rescue the strategy.

**Provenance:** signed null committed `cef09ea` (100 seeds x 3
instruments); simulator direction-capability committed `7a59ffe`;
re-canonicalization committed `25db12b`. Cross-reference:
`research/S1_DATA_SPLIT.md`, `strategies/null_random.py`.

---

## 1. Ledger Audit

**Total ledger entries: 338** (`research/ledger.jsonl`)

| Strategy | Count | Purpose breakdown |
|---|---|---|
| `trend_pullback` | 10 | 4 determinism/refactor-safety verification runs (M1 sign-off pair + M2 refactor pair), 6 H-003 Arm A/B runs |
| `null_random` | 328 | 300 clean M2 100-seed sweep entries + 28 duplicates |

### Known discrepancy #1: 28 duplicate `null_random` entries
20 USDJPY (seeds 0–19) and 8 XAUUSD (seeds 0–7), from a chunked run that
was killed by a tool timeout partway through, having already logged some
entries before dying. Flagged at the time (M2 completion message),
not hidden. **Not corrected** — the ledger is append-only by design;
rewriting history to look clean would defeat its purpose. The 100-seed
summary (`research/null_seed_results.csv`) was independently verified
to contain exactly 100 unique seeds per instrument, so the duplicates
had zero effect on any actual finding.

### Known discrepancy #2: 32 ledger entries missing a `research/runs/<run_id>/` backup directory
Found during this audit, not previously flagged. All 32 are either the
4 early `trend_pullback` verification runs or an early cluster of
`null_random` entries from July 19 ~14:12–14:13 UTC, most likely lost to
a local `rm -rf research/runs` cleanup step performed between test
iterations, whose deletion was later committed. **Confirmed
non-blocking**: every actual evidentiary file this project's verdicts
depend on — `research/trades_{symbol}.csv`, all 300 files in
`research/null_runs/`, `research/null_seed_results.csv`, and all three
H-00X verdict CSVs — is present, correctly sized, and git-tracked
independent of the `runs/` backup mechanism. No hypothesis verdict
relies on a missing `runs/` directory as its data source.

**Audit conclusion:** the ledger has cosmetic gaps, both now documented,
neither of which touches the evidentiary chain behind any verdict.

---

## 2. Cost-Per-Verdict

The declared M1/M2 charter goal was making hypothesis refutation cheap.
The actual cost trajectory:

| Milestone | Compute cost | Notes |
|---|---|---|
| M2 (null model, foundational) | ~300 simulator runs, ~44 min | One-time infrastructure cost; every hypothesis after this reused it for free |
| H-001 (pullback depth) | 2 runs (bin freeze + verdict), seconds | Pure pandas analysis on existing trade CSVs |
| H-003 (time-exit value) | 6 simulator runs, ~1 min | Killed on the real-strategy arm alone; the registered null-model sweep (~300 more runs) was skipped because the standalone kill criterion had already triggered |
| H-002 (session structure) | 0 new simulator runs | Pure analysis on M2's existing null-model trades |

**This is the actual proof the charter worked.** After the M2
investment, marginal cost per additional hypothesis dropped to near
zero specifically because hypotheses could be tested against
already-computed null-model data rather than requiring fresh
backtests. H-002 cost nothing. H-003 cost six runs and reached a
clean verdict without needing its own registered null sweep. This is
the "verdicts/month, not PF" outcome the charter asked to be measured.

---

## 3. Consolidated Findings — `trend_pullback` Family

Four independent tests, four different methods, one consistent
conclusion:

### M2 — Entries are worse than matched-frequency random

**>>> See the AMENDMENT at the top of this document (2026-07-24): this
finding was revised by the S1 signed null. USDJPY/XAUUSD no longer show
below-p05 underperformance once directional drift is controlled for.
GBPJPY's underperformance persists but is weaker than shown below. <<<**
| Symbol | Real expectancy | Null mean | Null p05 | Result |
|---|---|---|---|---|
| USDJPY | -4.38 | 10.17 | 0.13 | below p05 |
| GBPJPY | -5.29 | 8.58 | 0.30 | below p05 |
| XAUUSD | 4.25 | 12.50 | 4.18 | below p05 |

Real strategy landed below the 5th percentile of 100 matched-frequency
null draws on **all three** instruments. Not merely "no edge" —
underperforming random entries with identical exits, costs, and
constraints.

### H-001 — Pullback depth does not predict outcome (killed, TRAIN)
Quartile-binned `ema_distance` on TRAIN showed the deepest quartile
was NOT the best bin on 2 of 3 instruments (USDJPY, XAUUSD both
favored the shallowest bin instead), and direction was inconsistent
across instruments generally (GBPJPY favored the opposite extreme).
Two independent registered kill criteria triggered.

### H-003 — The time-exit rule subtracts value, doesn't add it (killed, TRAIN)
| Symbol | Arm A (current) | Arm B (exit disabled) | Δ (A−B) |
|---|---|---|---|
| USDJPY | 2.62 | 6.60 | -3.97 |
| XAUUSD | 2.33 | 7.23 | -4.90 |
| GBPJPY | -0.49 | 1.22 | -1.70 |

Removing the time exit **improved** TRAIN expectancy on all three
instruments — the opposite of the registered prediction. This also
retroactively explains why the original Phase 1 numbers
(+$56/trade time-exits vs. -$99/trade stops) were misleading: that
comparison conditioned on trade survival, exactly the trap the
registration warned against before testing.

### H-002 — No session structure, and the one "significant" result was noise (killed, TRAIN)
Best session differed across all three instruments (tokyo / new_york
/ london). p > 0.05 on 2 of 3. GBPJPY's apparently significant result
(p = 0.0000) had an effect size (3.66) smaller than seed-to-seed
sampling noise (13.81) — a textbook false positive the registration's
own dispersion check was built to catch, and did.

---

## 4. Verdict on Phase 2

**`trend_pullback` is retired.** Not one component — entries, pullback
depth as the entry mechanism, the time-exit rule, or session
conditioning — survived a pre-registered test. This is a complete,
well-evidenced falsification of the strategy's founding premise, built
via the exact mechanism Phase 2 was designed to produce: fast,
disciplined, reproducible kills rather than a slow drift toward hoping
a next parameter version would work.

**What Phase 2 actually built** (surviving into Phase 3 regardless of
`trend_pullback`'s fate):
- A hash-verified, git-tamper-evident experiment ledger
- A generic `Strategy` protocol any future hypothesis plugs into
  without simulator changes
- A validated, reusable null-model generator (matched-frequency random
  entries, same costs/exits/constraints) — the asset that made H-002
  and H-003 nearly free
- A regression-tested simulator with a real determinism guarantee
  (proven twice, at two different code states)

**Scope for Phase 3:** design the next hypothesis family from market
structure directly — not from `trend_pullback`'s anatomy, all of which
is now falsified. The reframe applied to H-002 (test the null model's
trades directly, independent of any specific entry filter) is the
template: it's cheap, and it separates "does structure exist in this
market" from "does my particular filter find it."
