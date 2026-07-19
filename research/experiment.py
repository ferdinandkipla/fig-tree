# research/experiment.py
#
# M1 Trust Layer — the experiment ledger.
#
# Purpose: every backtest run gets stamped with enough information
# (git commit, config hash, input-data hash, output hash) that it is
# reproducible by construction, not by discipline. If a result can't be
# regenerated from its ledger entry, it doesn't count as evidence.
#
# Hard rule: record() REFUSES to log if the git working tree is dirty
# outside the excluded ledger/runs paths. A run against uncommitted
# code cannot be reproduced from a commit hash alone — logging it
# anyway would create a ledger entry that lies about what actually ran.
#
# Excluded from the dirty check: research/ledger.jsonl and
# research/runs/ themselves, since those are updated BY every run.
# Without this exclusion, run #1 would dirty the tree via its own
# logging and run #2 would then refuse to log — a self-defeating trap.

import subprocess
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT   = Path(__file__).resolve().parent.parent
LEDGER_PATH = REPO_ROOT / "research" / "ledger.jsonl"
RUNS_DIR    = REPO_ROOT / "research" / "runs"

_DIRTY_CHECK_EXCLUDES = (
    "research/ledger.jsonl",
    "research/runs/",
    # M1 fix (code-audit finding): trades_*.csv / yearly_*.csv /
    # regime_by_*.csv are "latest" convenience outputs that every
    # backtest run legitimately overwrites — same category as
    # ledger.jsonl and runs/. Excluding them from the dirty check
    # (rather than requiring them committed before every run) matches
    # how the ledger actually guarantees reproducibility: via the
    # immutable per-run copies written to research/runs/<run_id>/ by
    # record() below, not via these live/mutable files staying clean.
    "research/trades_",
    "research/yearly_",
    "research/regime_by_",
    # M2: null-model per-seed trade CSVs and summary -- same category,
    # every seeded run legitimately writes a new file here.
    "research/null_runs/",
    "research/null_distribution_summary.csv",
    "research/null_seed_results.csv",
)


class DirtyGitStateError(RuntimeError):
    """Raised when the git working tree has uncommitted changes outside
    the excluded ledger/runs paths. record() refuses to log in this
    state because the run cannot be reproduced from a commit hash."""


def _run_git(args: list) -> str:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT)] + args,
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    # NOTE: rstrip only (trailing newline), NOT strip(). A global strip()
    # would eat the leading space off the FIRST line of multi-line,
    # fixed-column output like `git status --porcelain` (" M file.py"),
    # corrupting the column alignment for exactly one line and silently
    # truncating that path. Bit us during testing — see
    # _git_dirty_paths(), which depends on this column alignment.
    return result.stdout.rstrip("\n")


def _git_commit() -> str:
    return _run_git(["rev-parse", "HEAD"])


def _git_dirty_paths() -> list:
    """Paths with uncommitted changes (staged, unstaged, or untracked),
    excluding the ledger/runs paths that every run legitimately touches."""
    status = _run_git(["status", "--porcelain"])
    dirty = []
    for line in status.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip().strip('"')
        if any(path.startswith(ex) for ex in _DIRTY_CHECK_EXCLUDES):
            continue
        dirty.append(path)
    return dirty


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_obj(obj) -> str:
    """Deterministic hash of any JSON-serializable object (sorted keys,
    non-JSON types like datetime coerced via str)."""
    blob = json.dumps(obj, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def record(
    strategy: str,
    symbols: list,
    config_snapshot: dict,
    data_paths: dict,          # {symbol: path_to_cached_csv_used}
    output_paths: dict,        # {symbol: path_to_trades_csv_produced}
    seed: int = None,
    extra: dict = None,
) -> dict:
    """
    Hash-and-log a completed backtest run.

    Raises DirtyGitStateError if the working tree has uncommitted
    changes outside research/ledger.jsonl and research/runs/ — commit
    your code before running, or the ledger entry would reference a
    commit hash that doesn't actually reflect what ran.

    Writes the entry to:
      - research/ledger.jsonl   (append-only, one line per run)
      - research/runs/<run_id>/run.json   (same entry, standalone copy)

    Returns the entry dict.
    """
    dirty = _git_dirty_paths()
    if dirty:
        raise DirtyGitStateError(
            "Refusing to log run: git working tree has uncommitted "
            f"changes outside excluded paths: {dirty}. Commit or stash "
            "these first. A ledger entry must point to a commit hash "
            "that fully reflects what actually ran."
        )

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(exist_ok=True)

    data_hashes = {sym: _sha256_file(Path(p)) for sym, p in data_paths.items()}

    # M1 fix (code-audit finding): copy each output file into this run's
    # own directory BEFORE hashing, so output_hashes reference an
    # artifact that survives the next run overwriting the live path
    # (e.g. research/trades_USDJPY.csv gets clobbered by run #2 --
    # research/runs/<run_id>/trades_USDJPY.csv does not).
    output_hashes = {}
    for sym, p in output_paths.items():
        src = Path(p)
        dst = run_dir / src.name
        shutil.copy2(src, dst)
        output_hashes[sym] = _sha256_file(dst)

    entry = {
        "run_id":          run_id,
        "timestamp_utc":   datetime.now(timezone.utc).isoformat(),
        "git_commit":      _git_commit(),
        "git_dirty":       False,   # always False here -- refused above otherwise
        "strategy":        strategy,
        "symbols":         symbols,
        "seed":            seed,
        "config_hash":     _sha256_obj(config_snapshot),
        "config_snapshot": config_snapshot,
        "data_hashes":     data_hashes,
        "output_hashes":   output_hashes,
        "extra":           extra or {},
    }

    with open(run_dir / "run.json", "w") as f:
        json.dump(entry, f, indent=2, default=str)

    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER_PATH, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")

    return entry


def last_n(n: int = 5) -> list:
    """Convenience: read the last n ledger entries."""
    if not LEDGER_PATH.exists():
        return []
    lines = [l for l in LEDGER_PATH.read_text().splitlines() if l.strip()]
    return [json.loads(l) for l in lines[-n:]]


def get(run_id: str) -> dict:
    """Fetch a single ledger entry by run_id."""
    for entry in last_n(n=10**9):
        if entry["run_id"] == run_id:
            return entry
    raise KeyError(f"run_id {run_id} not found in ledger")
