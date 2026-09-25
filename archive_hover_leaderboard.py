#!/usr/bin/env python3
"""
Archive the top-N leaderboard entries for a task (default: hover, metric
kick_crash_rate) into results/<task>_checkpoints_ranked/rank01 .. rankNN,
each folder holding everything the registry knows about that checkpoint.

Why this exists: select_and_package_champion.sh's Step 3 leaderboard only
prints a ranked table to the terminal / a .log file -- the moment you want
to explain "why THIS checkpoint, and not the other nine" with a chart, you
need the full per-checkpoint story (hash, provenance, every metric, the
disturbance config it trained under) sitting somewhere durable, not just
rank + one metric column. This script uses the SAME ranking function the
shell pipeline's leaderboard step uses (checkpoint_manager._ranked), so
what gets archived here is guaranteed to match what Step 3 printed -- no
risk of a second, slightly-different ranking implementation drifting from
the first.

Run from the repo root (same place select_and_package_champion.sh lives):

    python archive_hover_leaderboard.py
    python archive_hover_leaderboard.py --top 10 --metric kick_crash_rate --minimize
    python archive_hover_leaderboard.py --copy-weights   # also copy each .zip (can be large)
    python archive_hover_leaderboard.py --dry-run        # preview only, writes nothing

Output layout:
    results/hover_checkpoints_ranked/
        ranking_summary.csv         <- one row per rank, every metric as a column: chart this
        ranking_summary.json        <- same data, structured
        rank01_<hash8>/
            manifest.json           <- rank, metric value, full eval record, full run record
            describe.txt            <- human-readable registry.describe() output
            sweep_log.txt           <- copied in if a matching sweep log is found (best effort)
            eval_log.txt            <- copied in if a matching thorough-eval log is found
            tilt_diagnostic_log.txt <- copied in if this hash was the tilt-diagnostic winner
            <checkpoint>.zip        <- only with --copy-weights
        rank02_<hash8>/
            ...
"""
import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from src.paths import MODEL_WEIGHTS_DIR  # noqa: E402
from src.weight_manager import checkpoint_manager as cm  # noqa: E402
from src.weight_manager import model_registry as registry  # noqa: E402


def _find_reports_dir() -> Path | None:
    """Most recent reports/champion_selection_* directory, if any -- that's
    where select_and_package_champion.sh's per-line sweep/eval/tilt logs
    live. Best-effort only: if nothing is found, the log-copy steps below
    just skip quietly rather than failing the whole archive."""
    reports_root = REPO_ROOT / "reports"
    if not reports_root.exists():
        return None
    candidates = sorted(reports_root.glob("champion_selection_*"))
    return candidates[-1] if candidates else None


def _model_stem(model_path: str) -> str:
    return Path(model_path).stem  # e.g. "hover_stabilize_ppo_seed0_disturbance_3x5_tiltfix3_614400_steps"


def _maybe_copy_logs(reports_dir: Path | None, model_path: str, dest: Path, top_path_for_tilt: str | None) -> None:
    if reports_dir is None:
        return
    stem = _model_stem(model_path)

    # eval_<prefix>_<step>.log matches the stem exactly (see the shell
    # script's `log="$REPORT_DIR/eval_${prefix}_${step}.log"`).
    eval_log = reports_dir / f"eval_{stem}.log"
    if eval_log.exists():
        shutil.copy2(eval_log, dest / "eval_log.txt")

    # sweep_<prefix>.log is keyed by prefix only (no step) -- prefix is the
    # stem with the trailing "_<digits>_steps" chopped off.
    if stem.endswith("_steps"):
        prefix = stem.rsplit("_", 2)[0]  # drop "<digits>_steps"
        sweep_log = reports_dir / f"sweep_{prefix}.log"
        if sweep_log.exists():
            shutil.copy2(sweep_log, dest / "sweep_log.txt")

    # tilt_diagnostic.log only exists for whichever single checkpoint was
    # the *leaderboard winner* at the time that report ran (Step 4 in the
    # shell script) -- only copy it into the rank folder that's actually
    # that same checkpoint, or it'll misleadingly look like every rank got
    # its own tilt diagnostic.
    tilt_log = reports_dir / "tilt_diagnostic.log"
    if tilt_log.exists() and top_path_for_tilt is not None and str(Path(top_path_for_tilt)) == str(Path(model_path)):
        shutil.copy2(tilt_log, dest / "tilt_diagnostic_log.txt")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="hover", choices=cm.TASKS.keys())
    ap.add_argument("--metric", default="kick_crash_rate",
                    help="Same metric name select_and_package_champion.sh's Step 3 uses.")
    ap.add_argument("--minimize", action="store_true", default=True,
                    help="Default True to match Step 3 (kick_crash_rate: lower is better).")
    ap.add_argument("--no-minimize", dest="minimize", action="store_false")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--dest", default=None,
                    help="Defaults to results/<task>_checkpoints_ranked")
    ap.add_argument("--copy-weights", action="store_true",
                    help="Also copy each checkpoint .zip into its rank folder. "
                         "Off by default -- results/ elsewhere in this repo (tiltfix2_champion) "
                         "keeps analysis products only, not weights.")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    scored = cm._ranked(args.task, args.metric, args.minimize)
    if not scored:
        print(f"No eval records with metric={args.metric!r} for task={args.task!r}. "
              f"Nothing to archive -- run the sweep/eval steps first.")
        sys.exit(1)

    top_n = scored[:args.top]
    missing_files = [r["hash"][:12] for r, v, exists in top_n if not exists]

    dest_root = Path(args.dest) if args.dest else (REPO_ROOT / "results" / f"{args.task}_checkpoints_ranked")
    reports_dir = _find_reports_dir()
    # Whichever record is rank 1 here is what Step 4's tilt diagnostic was run against,
    # AS LONG AS this ranking matches the one select_and_package_champion.sh last produced.
    top_path_for_tilt = top_n[0][0]["model_path"] if top_n else None

    print(f"Task: {args.task}  Metric: {args.metric}  Minimize: {args.minimize}")
    print(f"Found {len(scored)} eval record(s), archiving top {len(top_n)}.")
    if reports_dir:
        print(f"Will try to pull matching logs from: {reports_dir}")
    else:
        print("No reports/champion_selection_* directory found -- logs will be skipped, "
              "manifest/describe.txt still written from the registry itself.")
    if missing_files:
        print(f"NOTE: {len(missing_files)} of the top {len(top_n)} point to files no longer "
              f"on disk (hash prefixes: {', '.join(missing_files)}). Still archived (metadata "
              f"only) so the story of what WAS the leader isn't lost, but --copy-weights can't "
              f"copy what isn't there.")

    if args.dry_run:
        print("\n-- DRY RUN: would create --")
        for i, (r, v, exists) in enumerate(top_n, 1):
            print(f"  rank{i:02d}_{r['hash'][:8]}  {args.metric}={v}  {r['model_path']}  "
                  f"({'OK' if exists else 'MISSING'})")
        return

    dest_root.mkdir(parents=True, exist_ok=True)
    summary_rows = []
    all_metric_keys: list[str] = []

    for i, (r, v, exists) in enumerate(top_n, 1):
        h = r["hash"]
        rank_dir = dest_root / f"rank{i:02d}_{h[:8]}"
        rank_dir.mkdir(parents=True, exist_ok=True)

        run_record = registry.find_run(h)
        all_evals_for_hash = registry.find_evals(h)

        manifest = {
            "rank": i,
            "task": args.task,
            "ranking_metric": args.metric,
            "minimize": args.minimize,
            "metric_value": v,
            "hash": h,
            "hash_short": h[:12],
            "model_path": r["model_path"],
            "file_exists_on_disk": exists,
            "provenance_known": r.get("provenance_known"),
            "eval_record_used_for_ranking": r,
            "all_eval_records_for_this_hash": all_evals_for_hash,
            "run_record": run_record,
        }
        (rank_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))
        (rank_dir / "describe.txt").write_text(registry.describe(h))

        if args.copy_weights and exists:
            shutil.copy2(r["model_path"], rank_dir / Path(r["model_path"]).name)

        _maybe_copy_logs(reports_dir, r["model_path"], rank_dir, top_path_for_tilt)

        metrics = r.get("metrics", {})
        for k in metrics:
            if k not in all_metric_keys:
                all_metric_keys.append(k)
        row = {
            "rank": i,
            "hash_short": h[:12],
            "model_path": r["model_path"],
            "file_status": "OK" if exists else "MISSING",
            "provenance_known": r.get("provenance_known"),
            "cumulative_timesteps": run_record.get("cumulative_timesteps") if run_record else None,
            "seed": r.get("seed"),
            "episodes": r.get("episodes"),
            "git_commit": run_record.get("git_commit") if run_record else None,
            args.metric + "_ranked_on": v,
        }
        row.update(metrics)
        summary_rows.append(row)

        print(f"  rank{i:02d} hash={h[:12]} {args.metric}={v} -> {rank_dir}")

    fieldnames = list(summary_rows[0].keys())
    for row in summary_rows[1:]:
        for k in row:
            if k not in fieldnames:
                fieldnames.append(k)

    with open(dest_root / "ranking_summary.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)
    (dest_root / "ranking_summary.json").write_text(json.dumps(summary_rows, indent=2, default=str))

    print(f"\nDone. {len(top_n)} checkpoint(s) archived under {dest_root}")
    print(f"Chart-ready summary: {dest_root / 'ranking_summary.csv'}")


if __name__ == "__main__":
    main()
