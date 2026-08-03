# ARCHITECTURE

**Scope:** structural description of fig-tree. For current status see
`PROJECT_STATE.md`; for standards see `ENGINEERING_STANDARDS.md`.

## 1. Design philosophy

The platform is a falsification machine, not a trading bot. Every layer
exists to make it hard to fool ourselves:

- Determinism first: identical inputs → byte-identical outputs.
- Provenance everywhere: nothing enters a conclusion without a hash
  trail.
- Null models are mandatory: no result is interpreted against zero; it
  is interpreted against a matched-frequency, drift-corrected random
  baseline.

## 2. Layers

1. **Data ingestion (S1).** Live MT5 ingestion, H4 + 1H, provenance
   logging, hash-pinned research dataset per instrument. New data
   sources are onboarded as S1-grade events (source, snapshot, hash,
   caveats), never ad-hoc fetches. **US500/DXY are not yet onboarded** —
   any Batch 2 hypothesis requiring them is blocked until an S1-grade
   onboarding event happens.
2. **Simulation core.** Signed simulator: positions carry direction
   ∈ {−1,+1}; stop/target geometry and hit detection are direction-aware;
   P&L is the unified formula (exit − entry) × direction with no
   branching. `position_size()` uses `abs(entry − stop)` and is
   direction-agnostic.
3. **Strategy protocol.** Interchangeable strategy implementations
   behind a common interface; `strategies/common.py` hosts shared
   mechanics so real and null strategies differ only in the signal.
4. **Null-model framework.** `NullRandomStrategy` with matched trade
   frequency and (post-`cef09ea`) random direction — the drift-neutral
   null. 100-seed null distributions define the noise band for every
   adjudication.
5. **Research integrity layer.** `research/experiment.py`: refuses to
   log from a dirty git tree; SHA-256 of config, inputs, outputs;
   per-run artifact copies in `research/runs/<run_id>/`; append-only
   JSONL ledger.
6. **Statistical control.** FDR ledger + `fdr_check.py` applied across
   the hypothesis registry. **Batch 2 requires a per-cell extension**
   (interaction tests multiply the comparison space) — not yet built,
   see `PROJECT_STATE.md` §5.
7. **Cost model.** Spreads per instrument (AUDUSD currently a
   placeholder — see `PROJECT_STATE.md` §3). Swap modeling NOT yet
   implemented; snapshot pinned, integration is cost model v2, not yet
   done.

## 3. Invariants that must never break

- Byte-identical reruns for identical inputs (post re-canonicalization,
  the canonical hashes include the direction column).
- Symmetric-market invariant: mirrored market + flipped direction ⇒
  identical P&L (two inversions cancel).
- Ledger append-only; git-clean before logging; no dirty-tree results.
- Schema changes require numerical-equivalence verification on shared
  columns plus explicit re-canonicalization — literal byte-identity is
  the wrong check across a legitimate schema change.

## 4. Known gaps (deliberate, documented)

- No swap costs in the cost model (v2 pending).
- No portfolio layer (H-007's correlation characterization is the only
  input gathered so far).
- No interaction-capable analysis harness yet (required for Batch 2 —
  see `RESEARCH_PROGRAM.md` §5, chartered `82a4e29`, not yet built).
