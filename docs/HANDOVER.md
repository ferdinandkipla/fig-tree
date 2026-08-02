# ZenithFlow — Handover (paste this whole file into a new chat to resume)

## What this is
A personal quant research platform (owner: Ferdinand "Feddy" Kiplangat).
Repo: `https://github.com/ferdinandkipla/fig-tree`, branch `main`,
latest commit as of this handover: **`2b04b66`**.

**Core identity: a refutation engine, not (yet) a trading system.**
Its proven asset is a disciplined hypothesis-testing pipeline (ledger,
null models, FDR correction). Read `research/registry/FDR_LEDGER.md`
and `research/S1_STOPPING_RULE.md` before doing anything else.

## GitHub access
```
Repo: https://github.com/ferdinandkipla/fig-tree
Clone: git clone https://<TOKEN>@github.com/ferdinandkipla/fig-tree.git
```
The access token is provided separately in chat, NOT committed here —
GitHub's own push protection correctly rejected an earlier draft of
this file for containing a live token in plaintext. Get the current
token from Feddy directly at the start of a new session; do not commit
it to any file in this repository, ever.

## Current status (verify against `git log` — don't trust this blindly)
- **Phase 2 closed**: `trend_pullback` strategy retired. Every
  component (entry timing, pullback depth, exit rule) independently
  falsified via H-001/H-002/H-003 + the null-model comparison (M2).
- **Phase 3 Batch 1 complete**: 7 hypotheses adjudicated
  (M2-revised, H-001 through H-007). **6 kills, 1 non-edge survival
  (H-007: cross-instrument correlation, mean |corr|=0.324 < 0.5 —
  useful for future portfolio construction, NOT a trading edge).**
- **Phase 3 Batch 2 ("Conditional Search") chartered, not yet executed.**
  Theory: marginal single-variable effects are spent (0/7 hit rate);
  remaining structure, if any, is conditional/cross-sectional/
  event-anchored. Charter: `research/CONDITIONAL_SEARCH_CHARTER.md`.
  Stopping rule: `research/S1_STOPPING_RULE.md` (pre-commits to
  concluding after 8-12 Batch 2 adjudications, either way).
- **First mechanism memo committed** (`research/registry/MECHANISM-MEMO-H008.md`):
  thin-session/high-volatility interaction. Predicts EURUSD/XAUUSD
  (tokyo = thin session per `core/instruments.py`) show a stronger
  effect than USDJPY/GBPJPY/AUDUSD (tokyo = home session).
  **H-008 is NOT yet formally registered** — memo exists, registration
  doesn't.

## Immediate next step
1. Register H-008 (prediction, test design, kill criteria) referencing
   the memo's commit hash. Follow `research/registry/TEMPLATE.md`.
2. Extend `research/fdr_check.py` for per-cell FDR accounting (needed
   because session × volatility-tercile creates multiple cells — the
   H-002 pseudoreplication lesson scaled up). Not yet built.
3. Run H-008 via freeze-then-verdict (same pattern as `research/run_h001.py`).

## Non-negotiable rules (violating these breaks the project's core asset)
- **OOS (2022-2025 data) has never been unsealed for anything. Keep it that way** unless a hypothesis's own pre-registered design calls for its single, one-time unsealing.
- **The seed-to-seed dispersion check is mandatory** for any pooled-seed permutation test — it has caught false-positive "significant" results in 4 of 7 hypotheses so far (H-002, H-004, H-005, H-006). Never skip it.
- **FDR-adjusted threshold, not naive 0.05**, once multiple hypotheses exist. Run `python research/fdr_check.py` before trusting any p-value.
- **No hypothesis without a pre-registered kill criteria file**, committed BEFORE any statistic is computed. The commit hash is the timestamp proof.
- **Freeze-then-verdict phase separation** for any data-derived bins (quartiles, terciles): `--freeze` commits the bins and computes nothing; `--verdict` is a separate, later call that only reads the frozen file.
- **Batch 2 requires a mechanism memo** (economic story, counterparty, prior, per-instrument sign prediction specific enough to be visibly wrong) committed BEFORE registration. See `research/CONDITIONAL_SEARCH_CHARTER.md` Section 3.
- **No unregistered "just a few more hypotheses"** once Batch 2 concludes — `research/S1_STOPPING_RULE.md` pre-commits two exact branches (daily-frequency program, or formal conclusion). Don't quietly reopen 1H/H4 testing after that without rewriting the stopping rule itself.
- **Any code change to the simulator/strategies must be verified**, not assumed — run `python -m pytest tests/ -v` (expect ~18-19 passing), and for refactors, confirm byte-identical output hashes against the real strategy; for legitimate schema changes, use `research/verify_schema_migration.py` for numerical equivalence, never skip verification.
- **MetaTrader5 is a real, live-terminal-only dependency** — cannot run in a sandboxed environment without stubbing it (`sys.modules["MetaTrader5"] = stub` before any import touches it). Real data ingestion (`research/ingest_data.py`) must run on Feddy's Windows machine with MT5 open, never fabricated/approximated.

## Known, already-diagnosed non-issues (don't re-discover these as new bugs)
- Ledger has 28 duplicate `null_random` entries (a killed timeout during M2's sweep) — confirmed non-blocking, evidentiary CSVs are unaffected.
- 32 ledger entries missing their `research/runs/` backup dir — confirmed non-blocking, all real evidentiary files are intact and hash-verified elsewhere.
- `research/PHASE2_FINDINGS.md` has a dated amendment (2026-07-24) revising the original M2 finding after the signed null model was built — read both the original and the amendment, don't treat either alone as current.

## Key file map
```
core/config.py, core/instruments.py, core/strategy.py   — config, instrument metadata, Strategy protocol
data/loader.py, data/mt5_connector.py                    — MT5 data fetch/cache
strategies/common.py, trend_pullback/, null_random.py     — shared features, retired strategy, null model
execution/simulator.py                                    — the backtest engine (signed, direction-aware)
research/experiment.py                                    — the ledger (hash, commit, refuse-if-dirty)
research/fdr_check.py                                     — live FDR/Bonferroni threshold, reads registry dir
research/verify_schema_migration.py                       — numerical-equivalence checker for schema changes
research/run_h00X*.py                                     — per-hypothesis freeze/verdict pipelines
research/registry/H-00X.md, FDR_LEDGER.md, TEMPLATE.md    — hypothesis registrations + running ledger
research/CONDITIONAL_SEARCH_CHARTER.md                    — Batch 2 theory + rules
research/S1_STOPPING_RULE.md                               — pre-committed continue/conclude branches
tests/                                                     — correctness, determinism, symmetry, migration tests
```

## One-paragraph philosophy, if a new session needs the "why"
This project spent over a year tuning a strategy before ever asking
whether it had a real edge — that mistake is why everything now runs
through pre-registration, kill criteria written before looking, and a
ledger that makes every result traceable to a commit. The project's
real, proven output so far is not a profitable strategy — it's a
demonstrated ability to find out cheaply and honestly that something
doesn't work, four mechanism families running, without ever peeking at
sealed data or quietly loosening a threshold. Protect that discipline
over any single hypothesis's outcome.
