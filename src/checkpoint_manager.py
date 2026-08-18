"""
General checkpoint manager -- task-agnostic operations on top of model_registry.py.

Why this exists: as of 2026-08-13, "which checkpoint is actually good" for any given
task should be answerable from registered numbers, not from how much time was sunk
into it. This tool exists specifically to make that decision mechanical:

    leaderboard  -- rank every evaluated checkpoint for a task by a chosen metric.
                    Nothing here knows or cares how a checkpoint was produced, how
                    much compute it cost, or how long ago. Pure numbers.
    promote      -- copy the top of the leaderboard to a canonical "champion" path.
    backfill     -- find checkpoint files with no eval record yet, run the task's
                    evaluate command against each so the leaderboard is complete.
    archive      -- move non-champion (or explicitly named) files for a task into
                    an archive folder + manifest. Never deletes.
    retire-task  -- archive EVERY checkpoint for an entire task at once. This is the
                    "we're done with this line of work, keep the numbers, drop the
                    weights" operation -- e.g. if waypoint_nav is fully superseded by
                    the hover curriculum, this is a deliberate one-line command
                    instead of a lingering decision nobody makes.

Nothing here is destructive. Archive/retire always move files, never rm them, and
always write a manifest recording what moved and why. Deleting is a separate,
manual, later step -- this tool's job is to make "should I keep this" a fast,
data-backed question, not to answer "should I permanently delete this."

TASKS below needs your actual evaluate-script CLI filled in once per task -- this
tool does not parse evaluate-script output itself; it assumes (matching the existing
waypoint_evaluate.py pattern from 2026-08-11) that the evaluate script calls
model_registry.record_eval() itself when run. If hover_evaluate.py doesn't do that
yet, add it there first (mirror whatever waypoint_evaluate.py already does) --
backfill here just invokes the command, it doesn't register results on its own.

CLI:
    python -m src.checkpoint_manager leaderboard <task> <metric> [--minimize]
    python -m src.checkpoint_manager backfill <task> [--seed N] [--episodes N]
    python -m src.checkpoint_manager promote <task> <metric> [--minimize]
    python -m src.checkpoint_manager archive <task> --keep <hash-prefix-or-champion>
    python -m src.checkpoint_manager retire-task <task>
    python -m src.checkpoint_manager restore <archive_manifest.json>
"""
import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from src import model_registry as registry
from src.paths import MODEL_WEIGHTS_DIR

# --- Fill in per task. dir: where checkpoint .zip files for this task live.
# eval_cmd: a template list; {model_path}, {seed}, {episodes} get substituted.
# Assumed (per 2026-08-11 pattern) to call record_eval(task=..., ...) itself.
#
# dir uses the real MODEL_WEIGHTS_DIR constant from src/paths.py, not a
# hardcoded "model/model_weights" string -- paths.py resolves that constant
# relative to its own file location specifically so callers don't need to
# be run from the repo root. A hardcoded relative string would silently
# break the moment this is invoked from anywhere else (confirmed against
# the actual paths.py 2026-08-13).
TASKS: dict[str, dict] = {
    "waypoint_nav": {
        "dir": MODEL_WEIGHTS_DIR,  # includes history/ and checkpoints/ subdirs, see glob below
        # File-prefix patterns that identify THIS task's checkpoints. Required because
        # MODEL_WEIGHTS_DIR is a single flat directory shared by every task (per
        # src/paths.py's deliberate design) -- without this, a glob over "dir" matches
        # every task's files indiscriminately. Confirmed the hard way on 2026-08-15:
        # `archive waypoint_nav` swept every hover checkpoint into the same archive
        # folder because this filtering didn't exist yet.
        "file_globs": ["waypoint_nav_ppo*.zip"],
        "eval_cmd": [
            "python", "-m", "src.training.evaluate.waypoint_evaluate",
            "--model", "{model_path}", "--seed", "{seed}", "--episodes", "{episodes}",
        ],
    },
    "hover": {
        "dir": MODEL_WEIGHTS_DIR,
        # Two patterns: hover_stabilize_ppo* is the training-script naming convention;
        # hover_champion.zip is what `promote` writes (f"{task}_champion.zip"). Both
        # need to be recognized as "belongs to hover" or promote's own output would be
        # orphaned from future leaderboard/archive calls on this task.
        "file_globs": ["hover_stabilize_ppo*.zip", "hover_champion.zip"],
        "eval_cmd": [
            # TODO: confirm these flags match hover_evaluate.py's actual argparse setup,
            # and confirm hover_evaluate.py calls record_eval(task="hover", ...) --
            # add that call there first if it doesn't yet.
            "python", "-m", "src.training.evaluate.hover_evaluate",
            "--model", "{model_path}", "--seed", "{seed}", "--episodes", "{episodes}",
        ],
    },
}

CHECKPOINT_SUBDIRS = ["", "history", "checkpoints"]  # "" = the directory itself


def _all_checkpoint_files(task: str) -> list[Path]:
    base = Path(TASKS[task]["dir"])
    globs = TASKS[task]["file_globs"]
    files: list[Path] = []
    for subdir in CHECKPOINT_SUBDIRS:
        d = base / subdir if subdir else base
        if not d.exists():
            continue
        for pattern in globs:
            files.extend(d.glob(pattern))
    return sorted(set(files))


def _ranked(task: str, metric: str, minimize: bool = False) -> list[tuple[dict, float, bool]]:
    """Every eval record for `task`, scored by `metric` and sorted best-first,
    each tagged with whether its file still exists on disk.

    Why this exists: the registry is append-only by design (see model_registry.py's
    docstring) -- it never forgets a record, including one for a checkpoint file
    that was later deliberately deleted (e.g. rm -rf on an archived folder). Without
    this check, best_by_metric()/promote() can silently try to act on a "ghost"
    entry -- a real file, discovered 2026-08-16: an old pre-existing hover checkpoint
    scored better than the new champion in a stale eval record, but the file itself
    had already been permanently deleted, so promote() crashed on a raw
    FileNotFoundError instead of explaining what happened.
    """
    evals = [r for r in registry._read_all() if r["kind"] == "eval" and registry._task_of(r) == task]

    def _val(r):
        if "metrics" in r and metric in r["metrics"]:
            return r["metrics"][metric]
        return r.get(metric)

    scored = [(r, _val(r), Path(r["model_path"]).exists()) for r in evals if _val(r) is not None]
    scored.sort(key=lambda triple: triple[1], reverse=not minimize)
    return scored


def leaderboard(task: str, metric: str, minimize: bool = False) -> None:
    scored = _ranked(task, metric, minimize)
    if not scored:
        print(f"No eval records with metric={metric!r} for task={task!r}.")
        return

    print(f"{'rank':<5}{'hash':<14}{metric:<20}{'file':<10}{'provenance':<12}{'model_path'}")
    for i, (r, v, exists) in enumerate(scored, 1):
        prov = "known" if r.get("provenance_known") else "UNKNOWN"
        file_status = "OK" if exists else "MISSING"
        print(f"{i:<5}{r['hash'][:12]:<14}{v:<20}{file_status:<10}{prov:<12}{r['model_path']}")
    missing = sum(1 for _, _, exists in scored if not exists)
    if missing:
        print(f"\n{missing} record(s) point to files that no longer exist on disk "
              f"(deleted after eval, registry kept the record -- this is expected, "
              f"not corruption). These are skipped by `promote`, shown here for transparency.")


def backfill(task: str, seed: int, episodes: int) -> None:
    already = {r["hash"] for r in registry._read_all()
               if r["kind"] == "eval" and registry._task_of(r) == task}
    todo = [f for f in _all_checkpoint_files(task) if registry.file_hash(f) not in already]
    if not todo:
        print(f"Nothing to backfill for task={task!r} -- every found checkpoint already has an eval record.")
        return
    cmd_template = TASKS[task]["eval_cmd"]
    for f in todo:
        cmd = [part.format(model_path=str(f), seed=seed, episodes=episodes) for part in cmd_template]
        print(f"[backfill] evaluating {f} ...")
        subprocess.run(cmd, check=True)


def promote(task: str, metric: str, minimize: bool = False, dest: str | None = None) -> None:
    scored = _ranked(task, metric, minimize)
    if not scored:
        print(f"No eval records for task={task!r} / metric={metric!r} yet.")
        return
    existing = [(r, v) for r, v, exists in scored if exists]
    ghosts_skipped = len(scored) - len(existing)
    if not existing:
        print(f"All {len(scored)} eval record(s) for task={task!r} point to files that no "
              f"longer exist on disk. Nothing to promote. Run `leaderboard {task} {metric}` "
              f"to see them.")
        return
    best, best_val = existing[0]
    src = Path(best["model_path"])
    dest_path = Path(dest) if dest else Path(TASKS[task]["dir"]) / f"{task}_champion.zip"
    shutil.copy2(src, dest_path)
    print(f"Promoted {src} (hash {best['hash'][:12]}, {metric}={best_val}) -> {dest_path}")
    print("Original left in place -- this is a copy, not a move.")
    if ghosts_skipped:
        print(f"Note: skipped {ghosts_skipped} eval record(s) that scored better but point to "
              f"deleted files -- run `leaderboard {task} {metric}` to see them.")


def archive(task: str, keep: list[str], dest_dir: str | None = None) -> None:
    """Move every checkpoint file for `task` EXCEPT those whose hash starts with
    one of the `keep` prefixes into an archive folder, with a manifest."""
    files = _all_checkpoint_files(task)
    dest = Path(dest_dir) if dest_dir else Path(TASKS[task]["dir"]) / "archive" / f"{task}-{datetime.now():%Y-%m-%d}"
    dest.mkdir(parents=True, exist_ok=True)
    manifest = {"task": task, "archived_at": datetime.now().isoformat(timespec="seconds"),
                "kept_hash_prefixes": keep, "moved": []}
    for f in files:
        h = registry.file_hash(f)
        if any(h.startswith(k) for k in keep):
            continue
        target = dest / f.name
        shutil.move(str(f), str(target))
        manifest["moved"].append({"from": str(f), "to": str(target), "hash": h})
    manifest_path = dest / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"Archived {len(manifest['moved'])} file(s) for task={task!r} -> {dest}")
    print(f"Manifest: {manifest_path}  (use `restore` to undo)")


def retire_task(task: str, dest_dir: str | None = None) -> None:
    """Archive every checkpoint for a task, full stop -- no keep list. Use when a
    task is genuinely done with, e.g. waypoint_nav superseded by the hover
    curriculum. The registry's run/eval history for the task is untouched --
    this only moves weight files, so 'what we learned' stays queryable even
    after the weights themselves are archived."""
    archive(task, keep=[], dest_dir=dest_dir)
    print(f"Task {task!r} retired: all checkpoint files archived. "
          f"Registry history (runs + evals) is preserved and still queryable via "
          f"`leaderboard {task} <metric>` -- the lessons aren't going anywhere.")


def restore(manifest_path: str) -> None:
    manifest = json.loads(Path(manifest_path).read_text())
    for entry in manifest["moved"]:
        src, dst = Path(entry["to"]), Path(entry["from"])
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
    print(f"Restored {len(manifest['moved'])} file(s) from {manifest_path}")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    lb = sub.add_parser("leaderboard")
    lb.add_argument("task", choices=TASKS.keys())
    lb.add_argument("metric")
    lb.add_argument("--minimize", action="store_true")

    bf = sub.add_parser("backfill")
    bf.add_argument("task", choices=TASKS.keys())
    bf.add_argument("--seed", type=int, default=42)
    bf.add_argument("--episodes", type=int, default=20)

    pr = sub.add_parser("promote")
    pr.add_argument("task", choices=TASKS.keys())
    pr.add_argument("metric")
    pr.add_argument("--minimize", action="store_true")
    pr.add_argument("--dest")

    ar = sub.add_parser("archive")
    ar.add_argument("task", choices=TASKS.keys())
    ar.add_argument("--keep", nargs="*", default=[], help="hash prefixes to keep in place")
    ar.add_argument("--dest-dir")

    rt = sub.add_parser("retire-task")
    rt.add_argument("task", choices=TASKS.keys())
    rt.add_argument("--dest-dir")

    rs = sub.add_parser("restore")
    rs.add_argument("manifest_path")

    args = p.parse_args()
    if args.cmd == "leaderboard":
        leaderboard(args.task, args.metric, args.minimize)
    elif args.cmd == "backfill":
        backfill(args.task, args.seed, args.episodes)
    elif args.cmd == "promote":
        promote(args.task, args.metric, args.minimize, args.dest)
    elif args.cmd == "archive":
        archive(args.task, args.keep, args.dest_dir)
    elif args.cmd == "retire-task":
        retire_task(args.task, args.dest_dir)
    elif args.cmd == "restore":
        restore(args.manifest_path)


if __name__ == "__main__":
    sys.exit(main())
