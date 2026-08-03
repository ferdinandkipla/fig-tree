# DEVELOPMENT_WORKFLOW

## 1. Commit conventions

- Small, single-purpose commits; message states what changed and what
  was verified (e.g., "signed simulator: direction-aware geometry;
  12/12 tests pass; shared-column numerical equivalence vs canonical").
- Research commits reference the hypothesis ID (H-00x) and verdict
  where applicable. STATUS commits close adjudications explicitly.
- Never commit results from a dirty tree — the ledger enforces this;
  don't fight it.

## 2. Progress update format

Updates follow the established style: (a) what was done, with commit
hash; (b) how it was verified, specifically; (c) what was explicitly
NOT done, flagged honestly; (d) nuances that could mislead a future
reader (e.g., the expected hash change from a legitimate schema
change).

## 3. Experiment documentation style

Per hypothesis: registration doc (hypothesis, prediction, test,
criteria) → ledger-logged runs → STATUS/adjudication doc with verdict,
numbers, and FDR ledger entry. Interim findings that change strategy
(e.g., `S1_INTERIM_FINDING_5_KILLS.md`) are committed as standalone
documents with explicit forward commitments (budgets, stopping rules)
that later work treats as binding.

## 4. Decision records

Strategic decisions (phase closures, continue/conclude, charter
adoption) are committed documents, not chat artifacts. The repo must be
able to reconstruct WHY without any conversation history. See
`docs/PHASE3_CLOSURE.md` for the current worked example of this rule
being followed.

## 5. Repository organization

- `research/` — ledger, `runs/<run_id>/` artifacts, registration and
  STATUS docs.
- `strategies/` — protocol implementations + `common.py` shared
  mechanics.
- `execution/` — `costs.py` and simulation core.
- `docs/` — this documentation set.
- Data snapshots hash-pinned with provenance logs.

## 6. Definition of done

Code is complete when: tests pass, equivalence verified,
ledger-compatible, documented per §2–§3, and `PROJECT_STATE.md` updated
if the state changed.
