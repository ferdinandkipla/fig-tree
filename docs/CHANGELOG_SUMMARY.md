# CHANGELOG_SUMMARY — Milestone-level history

(Commit-level detail lives in git; this is the narrative index.)

- **M1** — Deterministic engine, experiment ledger (git-clean, SHA-256,
  append-only JSONL), determinism verified by independent-run hash
  identity.
- **M2** — Strategy protocol, null framework, 100-seed nulls;
  trend_pullback falsified (entries below 5th percentile of matched
  random on 3 instruments under the unsigned null).
- **S1** — MT5 live ingestion, 1H timeframe, provenance logging; dataset
  hash-pinned; later expanded to 5 instruments (EURUSD, AUDUSD added;
  AUDUSD spread placeholder caveat).
- **`7a59ffe`** — Signed simulator refactor. 12/12 tests pass;
  shared-column numerical equivalence vs canonical; new direction
  column (all +1 in long-only runs); symmetric-market fixture added
  (caught a wrong-invariant bug in the test itself).
- **`cef09ea`** — Signed drift-neutral null. M2 finding AMENDED in
  `PHASE2_FINDINGS.md`: entries are noise, not anti-predictive; drift
  was ~$5–10/trade of the old null mean.
- **H-001..H-003** — Registered, adjudicated, KILLED (pullback depth,
  H4 session, time exits). trend_pullback retirement confirmed.
- **FDR ledger + `fdr_check.py`** — Committed at 4/4 kills.
- **`S1_INTERIM_FINDING_5_KILLS.md`** — Interim finding with binding
  3-item search budget and re-evaluation commitment.
- **H-004..H-006** — KILLED (1H session: 0/5 dispersion; volatility
  regime: inconsistent sign, GBPJPY p=0.006 within seed noise;
  day-of-week: Thursday 4/5 best but 0/5 above noise). StringArray
  shuffle bug caught pre-adjudication during H-004.
- **`3b4a84f`** — H-007 STATUS: correlation characterization (mean
  |corr| 0.324; EURUSD–AUDUSD 0.552 flagged). Budget exhausted;
  continue/conclude decision required before any new registration.
- **`82a4e29`** — Conditional Search charter + stopping rule committed,
  hash-pinned, before any Batch 2 hypothesis explored. Sign-specificity
  requirement added to memo spec; FDR-by-cell accounting specified;
  cost-to-verdict priority order set; both stopping-rule branches
  (survivor / zero-survivors) pre-specified.
- **`2b04b66`** — H-008 mechanism memo committed (thin-session ×
  high-volatility interaction), before any exploratory look at the
  conditioning variable, per charter sequencing.
- **`2fd20d3`** — Compact `docs/HANDOVER.md` for session continuity;
  token correctly kept out of the repo by GitHub push protection.
- **This commit** — Full documentation package (`ARCHITECTURE.md`,
  `RESEARCH_PROGRAM.md`, `ENGINEERING_STANDARDS.md`,
  `DEVELOPMENT_WORKFLOW.md`, `ROADMAP.md`, `LESSONS_LEARNED.md`,
  `CHANGELOG_SUMMARY.md`, `AI_ONBOARDING.md`) and the explicit
  Phase 3→4 decision record (`docs/PHASE3_CLOSURE.md`) committed for
  the first time — closing the gap where this material existed only in
  chat history, unstamped against any commit.
