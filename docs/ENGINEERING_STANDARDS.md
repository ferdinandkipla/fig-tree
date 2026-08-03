# ENGINEERING_STANDARDS

Mandatory. Work not meeting these standards is incomplete regardless of
whether it "runs."

## 1. Determinism

- Identical inputs must produce byte-identical outputs.
- Any change touching the output path requires an equivalence check:
  byte-identity when the schema is unchanged; numerical equivalence on
  all shared columns + explicit re-canonicalization when the schema
  changed.
- Seeds are explicit and logged. "It looks the same" is not
  verification.

## 2. Verification before trust

- Every result passes through the experiment ledger: git-clean tree,
  SHA-256 of config/inputs/outputs, per-run artifact copy, append-only
  log.
- Tests must be able to fail. When a test disagrees with the code, trace
  the arithmetic by hand before deciding which is wrong (precedent: the
  symmetric-market fixture — the test was wrong, the simulator was
  right).
- New statistical machinery is validated on cases with known answers
  before it adjudicates anything (precedent: the StringArray shuffle bug
  caught before H-004's p-values were trusted). **This applies directly
  to the Batch 2 interaction harness before it touches H-008 data.**

## 3. Defect handling

- Defects are logged, fixed, and reported — never silently patched.
- The integrity claim of this project is "zero instances of trusting an
  unearned result," NOT "zero bugs." Maintaining the first claim requires
  honesty about the second. The defect catch-list is evidence, not
  embarrassment (see `PROJECT_STATE.md` §6).

## 4. Testing expectations

- Full test suite passes before any commit that touches simulation,
  costs, ledger, or statistics.
- Refactors of the simulation core require: all pre-existing tests
  unchanged and passing + end-to-end numerical equivalence on a real
  strategy run.
- Property-style fixtures (e.g., symmetric-market) are preferred over
  point checks for core invariants.

## 5. Scope discipline

- Scope creep is denied. M0–M4 roadmap only (`ROADMAP.md`).
- No trading, no live execution, no capital allocation work until the
  research program has an accepted effect meeting `RESEARCH_PROGRAM.md`
  §2 and §6. Currently there is none.
