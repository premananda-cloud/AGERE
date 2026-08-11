"""
Lightweight content-addressed registry for waypoint_nav checkpoints.

Problem this solves (2026-08-09 incident): model/model_weights/waypoint_nav_ppo_seed0.zip
is a MUTABLE pointer -- every waypoint_train.py run overwrites it. Timestamped copies exist
under history/, but nothing recorded which cumulative-step count / config a given file
actually corresponds to, and nothing recorded eval results against a specific file. Result:
after several runs, "which checkpoint got 3.00/5 waypoints reached?" could only be
reconstructed after the fact from devlog prose and mtime guessing.

Design: identify checkpoints by SHA256 content hash, not by path or filename. Paths get
overwritten; a hash of the actual weights doesn't change. Every training run appends a
"run" record (what config produced this file, from what parent, how many cumulative steps)
keyed by the hash of the saved .zip. Every tagged eval appends an "eval" record to the SAME
hash. Querying "what got 3.00/5" becomes a registry lookup instead of forensic reconstruction.

Registry lives at model/model_weights/registry.jsonl -- one JSON object per line,
append-only. Never edit past lines by hand; if a correction is needed, append a new line
(query helpers use the LAST record for a given hash+kind).

CLI:
    python -m src.model_registry best [metric]          # default metric: mean_waypoints_reached
    python -m src.model_registry describe <path/to.zip>  # full history for that exact file
"""
import hashlib
import json
import subprocess
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


def _registry_path() -> Path:
    from src.paths import waypoint_model_path
    return Path(waypoint_model_path()).parent / "registry.jsonl"


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


def _append(record: dict) -> None:
    path = _registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    record["logged_at"] = datetime.now().isoformat(timespec="seconds")
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")


def record_run(
    *,
    saved_path: str | Path,
    init_from: str | Path | None,
    run_timesteps: int,
    cumulative_timesteps: int,
    seed: int | None,
    task_config: Any,
    ppo_config: Any,
) -> str:
    """Call right after model.save(). Returns the new file's hash."""
    h = file_hash(saved_path)
    init_from_hash = file_hash(init_from) if init_from and Path(init_from).exists() else None
    _append({
        "kind": "run",
        "hash": h,
        "saved_path": str(saved_path),
        "init_from": str(init_from) if init_from else None,
        "init_from_hash": init_from_hash,
        "run_timesteps": run_timesteps,
        "cumulative_timesteps": cumulative_timesteps,
        "seed": seed,
        "task_config": asdict(task_config) if is_dataclass(task_config) else str(task_config),
        "ppo_config": asdict(ppo_config) if is_dataclass(ppo_config) else str(ppo_config),
        "git_commit": _git_commit(),
    })
    return h


def record_eval(
    *,
    model_path: str | Path,
    seed: int | None,
    episodes: int,
    success_rate: float,
    mean_waypoints_reached: float,
    crash_rate: float,
    mean_reward: float,
) -> str:
    """Call after an eval run. Returns the evaluated file's hash. If that hash has
    no matching 'run' record, the checkpoint's provenance is unknown to the
    registry (e.g. it was hand-copied outside waypoint_train.py) -- this prints a
    warning rather than failing silently, since that's exactly the situation that
    caused the 2026-08-09 confusion."""
    h = file_hash(model_path)
    known = find_run(h)
    _append({
        "kind": "eval",
        "hash": h,
        "model_path": str(model_path),
        "seed": seed,
        "episodes": episodes,
        "success_rate": success_rate,
        "mean_waypoints_reached": mean_waypoints_reached,
        "crash_rate": crash_rate,
        "mean_reward": mean_reward,
        "provenance_known": known is not None,
    })
    if known is None:
        print(
            f"[registry] WARNING: hash {h[:12]}... has no matching training-run record. "
            f"This file's origin (config, cumulative steps, parent checkpoint) is unknown "
            f"to the registry -- it may have been hand-copied. Eval result is still logged, "
            f"but treat provenance as unverified."
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


def best_by_metric(metric: str = "mean_waypoints_reached") -> dict | None:
    """Eval record with the highest value of `metric` across the whole registry,
    plus its matching run record if one exists. Direct answer to 'which
    checkpoint actually got the best result' -- no more reconstructing it from
    devlog prose and file mtimes."""
    evals = [r for r in _read_all() if r["kind"] == "eval"]
    if not evals:
        return None
    best = max(evals, key=lambda r: r.get(metric, float("-inf")))
    best["run"] = find_run(best["hash"])
    return best


def describe(h: str) -> str:
    """Human-readable summary of everything the registry knows about a hash."""
    run = find_run(h)
    evals = find_evals(h)
    lines = [f"hash: {h}"]
    if run:
        lines.append(
            f"  from run: init_from={run['init_from']}, "
            f"cumulative_steps={run['cumulative_timesteps']}, seed={run['seed']}, "
            f"git={run['git_commit']}, saved_at={run['logged_at']}"
        )
    else:
        lines.append("  no matching run record (unknown provenance)")
    if evals:
        for e in evals:
            lines.append(
                f"  eval (seed={e['seed']}, n={e['episodes']}): "
                f"waypoints={e['mean_waypoints_reached']:.2f}, "
                f"success={e['success_rate']*100:.1f}%, crash={e['crash_rate']*100:.1f}%"
            )
    else:
        lines.append("  no eval records yet")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 2 and sys.argv[1] == "best":
        metric = sys.argv[2] if len(sys.argv) > 2 else "mean_waypoints_reached"
        b = best_by_metric(metric)
        if b is None:
            print("No eval records in registry yet.")
        else:
            print(f"Best by {metric}:")
            print(describe(b["hash"]))
    elif len(sys.argv) >= 3 and sys.argv[1] == "describe":
        print(describe(file_hash(sys.argv[2])))
    else:
        print(
            "Usage:\n"
            "  python -m src.model_registry best [metric]\n"
            "  python -m src.model_registry describe <path/to/checkpoint.zip>"
        )
