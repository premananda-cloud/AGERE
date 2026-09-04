"""
Lightweight content-addressed registry for model checkpoints across tasks.

Origin (2026-08-09 incident, waypoint_nav): model/model_weights/waypoint_nav_ppo_seed0.zip
was a MUTABLE pointer -- every training run overwrote it, and nothing recorded which
cumulative-step count / config a given file actually corresponded to. "Which checkpoint got
3.00/5 waypoints reached?" could only be reconstructed after the fact from devlog prose and
mtime guessing.

Design, unchanged from the original: identify checkpoints by SHA256 content hash, not path
or filename. Every training run appends a "run" record (config, parent checkpoint, cumulative
steps) keyed by the hash of the saved .zip. Every tagged eval appends an "eval" record to the
SAME hash.

2026-08-13 change: generalized from waypoint-only to multi-task. Every record now carries a
`task` field ("waypoint_nav", "hover", etc). Eval metrics are a free-form dict instead of
hardcoded waypoint-specific fields, so hover-under-disturbance metrics (recovery time,
steady-state error, touchdown velocity...) fit the same schema without renaming or abusing
waypoint field names. Run records optionally carry a `disturbance` dict (type, magnitude
range, which prior stages' distributions are included) per the hover-robustness-curriculum
plan -- this is metadata for the disturbance curriculum, not required for simple tasks.

Old (pre-generalization) waypoint records on disk have no `task` field. `_task_of()` treats
missing-task records as "waypoint_nav" for backward compatibility -- do not rewrite old
lines to add the field; the registry is append-only by design.

Registry lives at model/model_weights/registry.jsonl -- one JSON object per line,
append-only. Never edit past lines by hand; if a correction is needed, append a new line
(query helpers use the LAST record for a given hash+kind).

CLI:
    python -m src.weight_manager.model_registry best <task> [metric]     # e.g. best hover mean_position_error (lower/higher-is-better is metric-dependent, see best_by_metric)
    python -m src.weight_manager.model_registry describe <path/to.zip>   # full history for that exact file, any task
"""
import hashlib
import json
import subprocess
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


def _registry_path() -> Path:
    # MODEL_WEIGHTS_DIR is a module-level Path constant in src/paths.py, not a
    # function -- confirmed against the actual file 2026-08-13. Importing it
    # directly (rather than deriving it from e.g. waypoint_model_path().parent,
    # the original approach) also removes the old implicit assumption that a
    # waypoint-specific path helper is the "source of truth" for a directory
    # every task shares.
    from src.paths import MODEL_WEIGHTS_DIR
    return MODEL_WEIGHTS_DIR / "registry.jsonl"


def file_hash(path: str | Path) -> str:
    """SHA256 of a checkpoint file's bytes -- this is the checkpoint's identity.
    Two files with the same hash are the same weights, regardless of filename."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=2,
        )
        return out.stdout.strip() if out.returncode == 0 else None
    except Exception:
        return None


def _task_of(record: dict) -> str:
    """Old pre-generalization records have no 'task' field -- they are all waypoint_nav
    (the only task that existed when they were written). Do not rewrite old lines to add
    this; append-only means we infer it at read time instead."""
    return record.get("task", "waypoint_nav")


def _append(record: dict) -> None:
    path = _registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    record["logged_at"] = datetime.now().isoformat(timespec="seconds")
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")


def record_run(
    *,
    task: str,
    saved_path: str | Path,
    init_from: str | Path | None,
    run_timesteps: int,
    cumulative_timesteps: int,
    seed: int | None,
    task_config: Any,
    ppo_config: Any,
    disturbance: dict | None = None,
) -> str:
    """Call right after model.save(). Returns the new file's hash.

    `disturbance`, when present, should describe what's in THIS run's sampling
    distribution, e.g.:
        {"types": ["kick"], "magnitude_range": {"kick": [0.0, 1.5]},
         "cumulative_from_stages": ["stage0_baseline"]}
    so later auditing can confirm the "cumulative, not replace" curriculum property
    actually held, rather than just asserting it in a planning doc.
    """
    h = file_hash(saved_path)
    init_from_hash = file_hash(init_from) if init_from and Path(init_from).exists() else None
    _append({
        "kind": "run",
        "task": task,
        "hash": h,
        "saved_path": str(saved_path),
        "init_from": str(init_from) if init_from else None,
        "init_from_hash": init_from_hash,
        "run_timesteps": run_timesteps,
        "cumulative_timesteps": cumulative_timesteps,
        "seed": seed,
        "task_config": asdict(task_config) if is_dataclass(task_config) else str(task_config),
        "ppo_config": asdict(ppo_config) if is_dataclass(ppo_config) else str(ppo_config),
        "disturbance": disturbance,
        "git_commit": _git_commit(),
    })
    return h


def record_eval(
    *,
    task: str,
    model_path: str | Path,
    seed: int | None,
    episodes: int,
    metrics: dict[str, float],
) -> str:
    """Call after an eval run. Returns the evaluated file's hash.

    `metrics` is free-form -- e.g. for waypoint_nav:
        {"success_rate": 0.6, "mean_waypoints_reached": 3.0, "crash_rate": 0.0,
         "mean_reward": 412.3}
    for hover-under-disturbance:
        {"crash_rate": 0.0, "mean_position_error_m": 0.08, "recovery_time_s": 1.4,
         "max_disturbance_survived": 1.2}

    If this hash has no matching 'run' record, the checkpoint's provenance is unknown
    to the registry (e.g. hand-copied, or predates the registry entirely -- true for
    every hover checkpoint as of 2026-08-13) -- this prints a warning rather than
    failing silently, since that's exactly the situation that caused the 2026-08-09
    confusion.
    """
    h = file_hash(model_path)
    known = find_run(h)
    _append({
        "kind": "eval",
        "task": task,
        "hash": h,
        "model_path": str(model_path),
        "seed": seed,
        "episodes": episodes,
        "metrics": metrics,
        "provenance_known": known is not None,
    })
    if known is None:
        print(
            f"[registry] WARNING: hash {h[:12]}... has no matching training-run record. "
            f"This file's origin (config, cumulative steps, parent checkpoint) is unknown "
            f"to the registry -- it may have been hand-copied, or predates the registry. "
            f"Eval result is still logged, but treat provenance as unverified."
        )
    return h


def _read_all() -> list[dict]:
    path = _registry_path()
    if not path.exists():
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def find_run(h: str) -> dict | None:
    matches = [r for r in _read_all() if r["kind"] == "run" and r["hash"] == h]
    return matches[-1] if matches else None


def find_evals(h: str) -> list[dict]:
    return [r for r in _read_all() if r["kind"] == "eval" and r["hash"] == h]


def best_by_metric(task: str, metric: str, higher_is_better: bool = True) -> dict | None:
    """Eval record with the best value of `metric` for a given task, plus its matching
    run record if one exists. Direct answer to 'which checkpoint actually got the best
    result' -- no reconstructing it from devlog prose and file mtimes.

    metric is looked up inside the eval's `metrics` dict for post-generalization records,
    and falls back to top-level fields for pre-generalization waypoint records.
    Set higher_is_better=False for metrics like position error or recovery time, where
    lower is better.
    """
    evals = [r for r in _read_all() if r["kind"] == "eval" and _task_of(r) == task]
    if not evals:
        return None

    def _val(r):
        if "metrics" in r and metric in r["metrics"]:
            return r["metrics"][metric]
        return r.get(metric, None)  # pre-generalization flat-field fallback

    scored = [r for r in evals if _val(r) is not None]
    if not scored:
        return None
    best = (max if higher_is_better else min)(scored, key=_val)
    best["run"] = find_run(best["hash"])
    return best


def describe(h: str) -> str:
    """Human-readable summary of everything the registry knows about a hash, across
    whatever task it belongs to."""
    run = find_run(h)
    evals = find_evals(h)
    lines = [f"hash: {h}"]
    if run:
        lines.append(
            f"  task: {_task_of(run)}"
        )
        lines.append(
            f"  from run: init_from={run['init_from']}, "
            f"cumulative_steps={run['cumulative_timesteps']}, seed={run['seed']}, "
            f"git={run['git_commit']}, saved_at={run['logged_at']}"
        )
        if run.get("disturbance"):
            lines.append(f"  disturbance: {run['disturbance']}")
    else:
        lines.append("  no matching run record (unknown provenance)")
    if evals:
        for e in evals:
            m = e.get("metrics", {k: v for k, v in e.items()
                       if k not in ("kind", "task", "hash", "model_path", "seed",
                                    "episodes", "provenance_known", "logged_at")})
            lines.append(f"  eval (seed={e['seed']}, n={e['episodes']}): {m}")
    else:
        lines.append("  no eval records yet")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3 and sys.argv[1] == "best":
        task = sys.argv[2]
        metric = sys.argv[3] if len(sys.argv) > 3 else (
            "mean_waypoints_reached" if task == "waypoint_nav" else None
        )
        if metric is None:
            print("Specify a metric: python -m src.model_registry best <task> <metric>")
            sys.exit(1)
        b = best_by_metric(task, metric)
        if b is None:
            print(f"No eval records for task={task!r} in registry yet.")
        else:
            print(f"Best {task} by {metric}:")
            print(describe(b["hash"]))
    elif len(sys.argv) >= 3 and sys.argv[1] == "describe":
        print(describe(file_hash(sys.argv[2])))
    else:
        print(
            "Usage:\n"
            "  python -m src.weight_manager.model_registry best <task> [metric]\n"
            "  python -m src.weight_manager.model_registry describe <path/to/checkpoint.zip>"
        )
