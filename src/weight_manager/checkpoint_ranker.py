"""
Rank every checkpoint in a directory by a cheap sweep, thoroughly re-evaluate
the top N, tag the registry, and archive elaborate per-checkpoint results
into results/ -- one reusable module instead of a bespoke shell pipeline per
training line.

Why this exists: select_and_package_champion.sh hardcodes CANDIDATE_LINES
(one prefix per training line) and only prints its numbers to .log files --
useful for a one-off promote, but not reusable for "just point me at a
checkpoints/ directory and tell me the best ten with the full story of why."
This module takes ANY checkpoint directory as an argument (a single line's
checkpoints/, or a directory with several lines mixed together) and:

  1. Sweeps every *.zip found there (cheap eval, --sweep-episodes) -- same
     "identical eval condition per checkpoint" principle as
     hover_checkpoint_sweep.py, which this reuses directly (eval_one_checkpoint)
     rather than re-implementing the episode loop a third time.
  2. Keeps the best --top (default 10) by --sweep-metric.
  3. Thoroughly re-evaluates each of those (--thorough-episodes), reusing
     hover_evaluate.py's own run_episode() so episode semantics can't drift
     between this tool and hover_evaluate.py.
  4. Tags every thorough eval to the model registry (model_registry.record_eval),
     same convention hover_evaluate.py and waypoint_evaluate.py use, so these
     results show up in `checkpoint_manager leaderboard/promote` too -- unless
     --no-tag is passed.
  5. Re-ranks the thoroughly-evaluated set by --metric (defaults to
     kick_crash_rate when --stage is a disturbance stage, else crash_rate --
     see select_and_package_champion.sh's header comment for why plain
     crash_rate is the wrong metric once disturbance is in play) and writes
     each into results/<dest>/rank01_<hash8>/ .. rank10_<hash8>/ with:
        manifest.json            -- hash, provenance, sweep + thorough metrics
        raw_episodes.csv          -- one row per episode (flat fields)
        raw_episodes_full.jsonl   -- one JSON object per episode, incl. traces
        summary_by_type_level.csv -- crash/recovery rate per disturbance type x level
     plus a top-level sweep_summary.csv (every checkpoint found, so it's
     visible why the other N were cut) and ranking_summary.csv/json (chart-ready).

CLI:
    python -m src.weight_manager.checkpoint_ranker <checkpoint_dir> \\
        --stage disturbance_3x5 --top 10 \\
        --sweep-episodes 60 --thorough-episodes 200 --seed 0

    python -m src.weight_manager.checkpoint_ranker model/model_weights/checkpoints \\
        --pattern "hover_stabilize_ppo_seed0_disturbance_3x5_tiltfix3_*_steps.zip" \\
        --stage disturbance_3x5 --dest results/tiltfix3_ranked

Reusable across training lines and tasks: pass whatever directory and
--pattern match the checkpoints you want compared, and --task to control
what gets tagged in the registry.
"""
import argparse
import csv
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
from stable_baselines3 import PPO

from src.config import ProjectConfig, HOVER_STAGE_PRESETS, DISTURBANCE_TYPES, DISTURBANCE_LEVELS
from src.training.evaluate.hover_checkpoint_sweep import eval_one_checkpoint, STEP_RE
from src.training.evaluate.hover_evaluate import run_episode
from src.training.gym_wrapper.hover_gym_wrapper import HoverGymEnv
from src.weight_manager import model_registry as registry


# --------------------------------------------------------------------------
# Discovery
# --------------------------------------------------------------------------
def discover_checkpoints(checkpoint_dir: str, pattern: str = "*.zip") -> list[Path]:
    """Every file matching `pattern` directly inside checkpoint_dir (not
    recursive -- a directory of one or several training lines' checkpoints,
    not a whole model_weights tree with archive/history mixed in). Sorted by
    parsed step count where the filename ends in "_<N>_steps.zip" (the
    CheckpointCallback convention), else alphabetically, so output is stable
    and readable even when several lines are mixed in one directory."""
    d = Path(checkpoint_dir)
    if not d.is_dir():
        raise FileNotFoundError(f"Not a directory: {checkpoint_dir}")
    files = sorted(d.glob(pattern))

    def sort_key(p: Path):
        m = STEP_RE.search(p.name)
        return (0, int(m.group(1))) if m else (1, p.name)

    return sorted(files, key=sort_key)


def _step_label(path: Path) -> str:
    m = STEP_RE.search(path.name)
    return f"{m.group(1)}_steps" if m else "n/a"


# --------------------------------------------------------------------------
# Thorough per-checkpoint evaluation (reuses hover_evaluate.run_episode so
# episode semantics never drift between this tool and hover_evaluate.py)
# --------------------------------------------------------------------------
def thorough_eval(model_path: Path, config: ProjectConfig, episodes: int, seed: int | None) -> list[dict]:
    env = HoverGymEnv(config)
    model = PPO.load(str(model_path), device="cpu")
    results = []
    for ep in range(episodes):
        s = seed if ep == 0 else None
        results.append(run_episode(env, model, seed=s))
    env.close()
    return results


def _overall_metrics(episodes: list[dict]) -> dict:
    return {
        "mean_position_error": float(np.mean([e["final_pos_error"] for e in episodes])),
        "crash_rate": float(np.mean([e["is_crash"] for e in episodes])),
        "mean_reward": float(np.mean([e["total_reward"] for e in episodes])),
    }


def _disturbance_breakdown(episodes: list[dict]) -> tuple[dict, list[dict]]:
    """Returns (flat_metrics, level_rows).

    flat_metrics keys match hover_evaluate.py's own naming exactly
    ("<type>_crash_rate", "<type>_recovery_rate", "<type>_mean_recovery_time_steps",
    "<type>_n_episodes") so tagging the registry with this dict plugs
    straight into checkpoint_manager.py's existing kick_crash_rate leaderboard
    convention with no translation layer.

    level_rows is the same breakdown further split by 1-5 disturbance level,
    for summary_by_type_level.csv -- something hover_evaluate.py prints to
    the console but never returns as structured data, so it's rebuilt here
    directly from the episode records rather than re-parsing printed text.
    """
    flat: dict = {}
    level_rows: list[dict] = []
    for type_name in DISTURBANCE_TYPES:
        type_eps = [e for e in episodes if e["disturbance_fired"] and e["disturbance_type"] == type_name]
        if type_eps:
            crash_rate = float(np.mean([e["is_crash"] for e in type_eps]))
            survivors = [e for e in type_eps if not e["is_crash"]]
            recovery_rate = float(np.mean([e["recovered"] for e in survivors])) if survivors else float("nan")
            recovery_times = [e["recovery_time_steps"] for e in survivors if e["recovered"]]
            mean_recovery = float(np.mean(recovery_times)) if recovery_times else float("nan")
            flat[f"{type_name}_crash_rate"] = crash_rate
            flat[f"{type_name}_recovery_rate"] = recovery_rate
            flat[f"{type_name}_mean_recovery_time_steps"] = mean_recovery
            flat[f"{type_name}_n_episodes"] = len(type_eps)

        for level in range(1, DISTURBANCE_LEVELS + 1):
            level_eps = [e for e in type_eps if e["disturbance_level"] == level]
            n = len(level_eps)
            if n == 0:
                level_rows.append({"type": type_name, "level": level, "n": 0,
                                    "crash_rate": None, "recovery_rate": None,
                                    "mean_recovery_time_steps": None})
                continue
            lc = float(np.mean([e["is_crash"] for e in level_eps]))
            l_survivors = [e for e in level_eps if not e["is_crash"]]
            lr = float(np.mean([e["recovered"] for e in l_survivors])) if l_survivors else None
            l_rec_times = [e["recovery_time_steps"] for e in l_survivors if e["recovered"]]
            lrt = float(np.mean(l_rec_times)) if l_rec_times else None
            level_rows.append({"type": type_name, "level": level, "n": n,
                                "crash_rate": lc, "recovery_rate": lr,
                                "mean_recovery_time_steps": lrt})
    return flat, level_rows


# --------------------------------------------------------------------------
# Per-checkpoint archive folder
# --------------------------------------------------------------------------
_EPISODE_CSV_FIELDS = [
    "episode_idx", "final_pos_error", "is_crash", "total_reward", "jitter_norm",
    "start_yaw_rad", "truncation_reason", "disturbance_fired", "disturbance_type",
    "disturbance_level", "disturbance_magnitude", "recovered", "recovery_time_steps",
    "wind_steady_state_error_mean",
]


def _write_checkpoint_archive(rank_dir: Path, *, rank: int, path: Path, h: str,
                               sweep_summary: dict, thorough_metrics: dict,
                               episodes: list[dict], task: str, stage: str | None,
                               sweep_episodes: int, thorough_episodes: int, seed: int | None,
                               ranking_metric: str, ranking_value: float) -> None:
    rank_dir.mkdir(parents=True, exist_ok=True)

    run_record = registry.find_run(h)
    manifest = {
        "rank": rank,
        "task": task,
        "model_path": str(path),
        "hash": h,
        "hash_short": h[:12],
        "stage": stage,
        "seed": seed,
        "sweep_episodes": sweep_episodes,
        "thorough_episodes": thorough_episodes,
        "ranking_metric": ranking_metric,
        "ranking_value": ranking_value,
        "sweep_summary": sweep_summary,
        "thorough_metrics": thorough_metrics,
        "run_record": run_record,
    }
    (rank_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))

    with open(rank_dir / "raw_episodes.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_EPISODE_CSV_FIELDS)
        writer.writeheader()
        for i, ep in enumerate(episodes):
            row = {k: ep.get(k) for k in _EPISODE_CSV_FIELDS if k != "episode_idx"}
            row["episode_idx"] = i
            writer.writerow(row)

    with open(rank_dir / "raw_episodes_full.jsonl", "w") as f:
        for i, ep in enumerate(episodes):
            f.write(json.dumps({"episode_idx": i, **ep}, default=str) + "\n")

    _, level_rows = _disturbance_breakdown(episodes)
    if level_rows:
        with open(rank_dir / "summary_by_type_level.csv", "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["type", "level", "n", "crash_rate",
                                                    "recovery_rate", "mean_recovery_time_steps"])
            writer.writeheader()
            writer.writerows(level_rows)


# --------------------------------------------------------------------------
# Main pipeline
# --------------------------------------------------------------------------
def rank_and_evaluate(
    checkpoint_dir: str,
    *,
    pattern: str = "*.zip",
    stage: str | None = None,
    sweep_episodes: int = 60,
    thorough_episodes: int = 200,
    seed: int = 0,
    top: int = 10,
    sweep_metric: str = "crash_rate",
    metric: str | None = None,
    minimize: bool = True,
    task: str = "hover",
    dest: str | None = None,
    tag_registry: bool = True,
) -> Path:
    metric = metric or ("kick_crash_rate" if stage and "disturbance" in stage else "crash_rate")

    config = ProjectConfig()
    if stage:
        config.task = replace(config.task, **HOVER_STAGE_PRESETS[stage])
        print(f"Applied stage preset '{stage}': {HOVER_STAGE_PRESETS[stage]}")

    checkpoints = discover_checkpoints(checkpoint_dir, pattern)
    if not checkpoints:
        raise SystemExit(f"No checkpoints matching {pattern!r} found in {checkpoint_dir}")

    dest_root = Path(dest) if dest else Path("results") / f"{Path(checkpoint_dir).name}_ranked"
    dest_root.mkdir(parents=True, exist_ok=True)

    # --- Step 1: cheap sweep across every checkpoint found ---------------
    print(f"\n== Sweeping {len(checkpoints)} checkpoint(s), {sweep_episodes} episodes each "
          f"(seed={seed}, identical condition per checkpoint) ==")
    sweep_rows = []
    for path in checkpoints:
        summary = eval_one_checkpoint(str(path), config, sweep_episodes, seed)
        sweep_rows.append({"path": path, "step_label": _step_label(path), "summary": summary})
        type_bits = " | ".join(f"{k.replace('_crash_rate', '')}={v*100:.0f}%"
                                for k, v in summary.items() if k.endswith("_crash_rate") and k != "crash_rate")
        print(f"  {path.name:<70} crash {summary['crash_rate']*100:5.1f}%  "
              f"pos_err {summary['mean_pos_error']:.3f} m  {type_bits}")

    with open(dest_root / "sweep_summary.csv", "w", newline="") as f:
        fieldnames = ["path", "step_label"] + sorted({k for r in sweep_rows for k in r["summary"]})
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in sweep_rows:
            writer.writerow({"path": str(r["path"]), "step_label": r["step_label"], **r["summary"]})

    def _sweep_val(r):
        return r["summary"].get(sweep_metric)

    scored = [r for r in sweep_rows if _sweep_val(r) is not None]
    dropped = len(sweep_rows) - len(scored)
    if dropped:
        print(f"\n  ({dropped} checkpoint(s) had no {sweep_metric!r} in their sweep summary -- "
              f"e.g. that disturbance type never fired at this episode count -- excluded from top-{top})")
    scored.sort(key=_sweep_val, reverse=not minimize)
    candidates = scored[:top]
    print(f"\nKept top {len(candidates)} by sweep {sweep_metric} (minimize={minimize}).")

    # --- Step 2: thorough re-evaluation of the survivors -------------------
    print(f"\n== Thorough evaluation of {len(candidates)} candidate(s), "
          f"{thorough_episodes} episodes each ==")
    thorough_results = []
    for c in candidates:
        path = c["path"]
        print(f"-- evaluating {path} --")
        episodes = thorough_eval(path, config, thorough_episodes, seed)
        overall = _overall_metrics(episodes)
        disturbance_flat, _ = _disturbance_breakdown(episodes)
        metrics = {**overall, **disturbance_flat}
        h = registry.file_hash(path)

        if tag_registry:
            registry.record_eval(task=task, model_path=path, seed=seed,
                                  episodes=thorough_episodes, metrics=metrics)

        thorough_results.append({"path": path, "hash": h, "sweep_summary": c["summary"],
                                  "metrics": metrics, "episodes": episodes})
        print(f"   crash_rate={metrics.get('crash_rate'):.3f}  "
              f"mean_position_error={metrics.get('mean_position_error'):.3f}  "
              f"{metric}={metrics.get(metric)}")

    # --- Step 3: final ranking + archive -----------------------------------
    scoreable = [r for r in thorough_results if r["metrics"].get(metric) is not None]
    unscoreable = [r for r in thorough_results if r["metrics"].get(metric) is None]
    if unscoreable:
        print(f"\nWARNING: {len(unscoreable)} thoroughly-evaluated checkpoint(s) have no "
              f"{metric!r} in their metrics (ranked last, still archived): "
              + ", ".join(str(r['path']) for r in unscoreable))
    scoreable.sort(key=lambda r: r["metrics"][metric], reverse=not minimize)
    final_order = scoreable + unscoreable

    summary_rows = []
    for i, r in enumerate(final_order, 1):
        rank_dir = dest_root / f"rank{i:02d}_{r['hash'][:8]}"
        ranking_value = r["metrics"].get(metric)
        _write_checkpoint_archive(
            rank_dir, rank=i, path=r["path"], h=r["hash"],
            sweep_summary=r["sweep_summary"], thorough_metrics=r["metrics"],
            episodes=r["episodes"], task=task, stage=stage,
            sweep_episodes=sweep_episodes, thorough_episodes=thorough_episodes, seed=seed,
            ranking_metric=metric, ranking_value=ranking_value,
        )
        row = {"rank": i, "hash_short": r["hash"][:12], "model_path": str(r["path"])}
        row.update(r["metrics"])
        summary_rows.append(row)
        print(f"  rank{i:02d}  hash={r['hash'][:12]}  {metric}={ranking_value}  -> {rank_dir}")

    fieldnames = list(summary_rows[0].keys()) if summary_rows else []
    for row in summary_rows[1:]:
        for k in row:
            if k not in fieldnames:
                fieldnames.append(k)
    with open(dest_root / "ranking_summary.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)
    (dest_root / "ranking_summary.json").write_text(json.dumps(summary_rows, indent=2, default=str))

    print(f"\nDone. Ranked {len(final_order)} checkpoint(s) by {metric} -> {dest_root}")
    print(f"Chart-ready summary: {dest_root / 'ranking_summary.csv'}")
    return dest_root


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("checkpoint_dir", help="Directory containing checkpoint .zip files (non-recursive).")
    p.add_argument("--pattern", default="*.zip", help="Glob pattern within checkpoint_dir (default: *.zip).")
    p.add_argument("--stage", default=None, choices=sorted(HOVER_STAGE_PRESETS.keys()),
                   help="Disturbance stage preset to evaluate under. Required to see any "
                        "disturbance events -- same requirement as hover_evaluate.py's --stage.")
    p.add_argument("--sweep-episodes", type=int, default=60)
    p.add_argument("--thorough-episodes", type=int, default=200)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--top", type=int, default=10)
    p.add_argument("--sweep-metric", default="crash_rate",
                   help="Metric from the cheap sweep used to pick the top-N candidates.")
    p.add_argument("--metric", default=None,
                   help="Metric used for the FINAL ranking after thorough evaluation. "
                        "Defaults to kick_crash_rate if --stage contains 'disturbance', else crash_rate.")
    p.add_argument("--maximize", dest="minimize", action="store_false",
                   help="Higher is better for both --sweep-metric and --metric (default: lower is better).")
    p.set_defaults(minimize=True)
    p.add_argument("--task", default="hover", help="Task name tagged into the model registry.")
    p.add_argument("--dest", default=None,
                   help="Defaults to results/<checkpoint_dir name>_ranked")
    p.add_argument("--no-tag", dest="tag_registry", action="store_false",
                   help="Skip logging thorough evals to the model registry.")
    p.set_defaults(tag_registry=True)
    args = p.parse_args()

    rank_and_evaluate(
        args.checkpoint_dir, pattern=args.pattern, stage=args.stage,
        sweep_episodes=args.sweep_episodes, thorough_episodes=args.thorough_episodes,
        seed=args.seed, top=args.top, sweep_metric=args.sweep_metric, metric=args.metric,
        minimize=args.minimize, task=args.task, dest=args.dest, tag_registry=args.tag_registry,
    )


if __name__ == "__main__":
    main()
