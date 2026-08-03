# ROADMAP

Standing constraint: scope creep denied. M0–M4 only.

- **M0 — Foundations.** Complete.
- **M1 — Core engine, determinism, ledger.** Complete.
- **M2 — Strategy protocol, null framework, falsification of
  trend_pullback.** Complete (findings amended by signed null,
  `cef09ea`).
- **S1 — Live data ingestion, 1H, provenance.** Complete.
- **M3 — The Search (Phase 3).** CLOSED as complete. Batch 1: 7
  adjudications, 6 kills, 1 characterization. Continue/conclude decision
  made (continue) — see `docs/PHASE3_CLOSURE.md`.
- **Phase 4 — Conditional Search (Batch 2).** ACTIVE. Chartered
  `82a4e29`. Budgeted 8–12 adjudications. H-008 memo committed,
  registration pending. See `RESEARCH_PROGRAM.md` §5.
- **M4 — Only reachable via an accepted effect.** Portfolio
  construction / paper execution work is gated on `RESEARCH_PROGRAM.md`
  §6 prerequisites. H-007's correlation characterization
  (EURUSD–AUDUSD 0.552) is the only M4-relevant input collected so far.

Near-term engineering (phase-independent, do regardless of Phase 4
outcome):

1. Cost model v2: swap integration (demo-account caveat), AUDUSD real
   specs. **Blocks any acceptance, Batch 1 or 2.**
2. Interaction-capable per-cell FDR analysis harness. **Blocks H-008
   execution** (registration itself is not blocked).

Explicitly out of scope until M4 gates open: live trading, capital
allocation, AI-driven signal generation, any expansion beyond the M0–M4
plan. Any "two-year vision" narrative discussed in prior sessions is
aspiration, not roadmap; it confers no build authorization.
