"""
Orchestrates the full disturbance-robustness sweep behind the lab report:
for a given checkpoint, forces every one of the 3-type x 5-level buckets
(kick/torque/wind x L1-L5) evenly -- via HoverGymEnv's existing
forced_disturbance mechanism -- runs N episodes per bucket, and dumps
everything into results/<label>/: raw per-episode data, a summary table,
auto-generated figures, and a manifest recording exactly what produced
them.

Why forced, not random, sweeping: hover_evaluate.py/hover_checkpoint_sweep.py
sample disturbance type/level/magnitude randomly per episode (matching
training distribution), so with only 15 buckets, achieving even coverage
needs a lot of episodes and you still don't control sample count per
bucket. This script forces type+level directly (magnitude still randomizes
within that level's own bound, same as training) so every bucket gets an
identical, deliberate sample size -- the right shape of data for a
"disturbance magnitude vs. effect" figure, not just an aggregate crash
rate.

Nothing about graph axes/bins is hardcoded here beyond the bucket
structure (type x level) that the curriculum itself already defines --
actual magnitudes, crash outcomes, recovery times, and tilt peaks are
whatever the sim/policy actually produced, read from
src.training.evaluate.hover_evaluate.run_episode()'s own return dict.

Usage (run from the repo root, same convention as the -m src.training...
scripts, but this one is a plain script since it lives outside src/):

    python run_report_pipeline.py \\
        --model model/model_weights/hover_stabilize_ppo_seed0_disturbance_3x5_tiltfix2.zip \\
        --stage disturbance_3x5 \\
        --episodes-per-bucket 40 \\
        --seed 0 \\
        --label tiltfix2_champion

Requires pandas + matplotlib in addition to this project's existing deps:
    pip install pandas matplotlib

Output:
    results/<label>/
        manifest.json               -- model path, git commit, args, timestamp
        raw_episodes.csv            -- one row per episode, scalar fields only
        raw_episodes_full.jsonl     -- one JSON object per episode, includes
                                        full tilt_trace/pos_error_trace, for
                                        anyone who wants to dig into a
                                        specific episode later
        summary_by_type_level.csv   -- one row per (type, level) bucket
        figures/
            crash_rate_by_level.png
            peak_tilt_vs_magnitude.png
            recovery_time_vs_magnitude.png
            wind_steady_state_error_vs_magnitude.png
"""

import argparse
import json
import subprocess
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from stable_baselines3 import PPO

from src.config import ProjectConfig, HOVER_STAGE_PRESETS, DISTURBANCE_TYPES, DISTURBANCE_LEVELS
from src.training.gym_wrapper.hover_gym_wrapper import HoverGymEnv
from src.training.evaluate.hover_evaluate import run_episode

REPO_ROOT = Path(__file__).resolve().parent
RESULTS_DIR = REPO_ROOT / "results"

# Colors kept consistent across every figure so "kick" is always the same
# color whether you're looking at the tilt plot or the recovery-time plot.
TYPE_COLORS = {"kick": "#1f77b4", "torque": "#d62728", "wind": "#2ca02c"}


def git_commit_hash() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT, stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return None


def sweep_types(config: ProjectConfig) -> list[str]:
    """Use the stage-active type list (post-preset), not the raw
    DISTURBANCE_TYPES registry -- keeps this in sync if the registry ever
    grows types that aren't in scope for the current curriculum design."""
    active = list(getattr(config.task, "disturbance_types_active", []))
    return active or list(DISTURBANCE_TYPES.keys())


def run_sweep(model_path: str, stage: str, episodes_per_bucket: int, seed: int) -> list[dict]:
    config = ProjectConfig()
    config.task = replace(config.task, **HOVER_STAGE_PRESETS[stage])
    types = sweep_types(config)
    model = PPO.load(model_path, device="cpu")

    rows = []
    for type_name in types:
        for level in range(1, DISTURBANCE_LEVELS + 1):
            env = HoverGymEnv(config, forced_disturbance={"type": type_name, "level": level})
            for ep in range(episodes_per_bucket):
                # Deterministic-but-distinct seed per bucket's first episode
                # so the 15 buckets aren't all replaying an identical start
                # jitter draw; every later episode in a bucket free-runs off
                # whatever np_random state that left behind, same pattern
                # the existing sweep/evaluate scripts use.
                s = (seed * 10_000 + level * 100 + hash(type_name) % 97) if ep == 0 else None
                result = run_episode(env, model, seed=s)
                tilt_trace = result.pop("tilt_trace")
                result.pop("pos_error_trace", None)
                result["peak_tilt_rad"] = float(np.max(tilt_trace)) if len(tilt_trace) else float("nan")
                result["peak_tilt_deg"] = float(np.degrees(result["peak_tilt_rad"]))
                result["disturbance_type_forced"] = type_name
                result["disturbance_level_forced"] = level
                result["episode_in_bucket"] = ep
                rows.append(result)
            env.close()
            n_crash = sum(r["is_crash"] for r in rows if r["disturbance_type_forced"] == type_name
                          and r["disturbance_level_forced"] == level)
            print(f"  {type_name:8s} L{level} done | {episodes_per_bucket} episodes | "
                  f"crash {n_crash}/{episodes_per_bucket}")
    return rows


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    def recovery_rate(s):
        s = s.dropna()
        return float(s.mean()) if len(s) else float("nan")

    grouped = df.groupby(["disturbance_type_forced", "disturbance_level_forced"], as_index=False)
    summary = grouped.agg(
        n=("is_crash", "size"),
        crash_rate=("is_crash", "mean"),
        recovery_rate=("recovered", recovery_rate),
        mean_recovery_time_steps=("recovery_time_steps", "mean"),
        mean_magnitude=("disturbance_magnitude", "mean"),
        min_magnitude=("disturbance_magnitude", "min"),
        max_magnitude=("disturbance_magnitude", "max"),
        mean_peak_tilt_deg=("peak_tilt_deg", "mean"),
        mean_final_pos_error=("final_pos_error", "mean"),
        mean_wind_steady_state_error=("wind_steady_state_error_mean", "mean"),
    )
    return summary.sort_values(["disturbance_type_forced", "disturbance_level_forced"]).reset_index(drop=True)


def make_figures(df: pd.DataFrame, summary: pd.DataFrame, out_dir: Path, unit_by_type: dict[str, str]):
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) crash rate by level, one line per type -- the headline robustness
    #    envelope figure.
    fig, ax = plt.subplots(figsize=(7, 5))
    for t in summary["disturbance_type_forced"].unique():
        sub = summary[summary["disturbance_type_forced"] == t].sort_values("disturbance_level_forced")
        ax.plot(sub["disturbance_level_forced"], sub["crash_rate"] * 100,
                marker="o", label=t, color=TYPE_COLORS.get(t))
    ax.set_xlabel("Disturbance level (1=weakest, 5=strongest)")
    ax.set_ylabel("Crash rate (%)")
    ax.set_title("Crash rate vs. disturbance level, by type")
    ax.set_xticks(range(1, DISTURBANCE_LEVELS + 1))
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / "crash_rate_by_level.png", dpi=150)
    plt.close(fig)

    # 2) peak tilt vs. actual sampled magnitude (the literal "force vector
    #    vs. effect" plot -- magnitude in each type's own physical unit).
    fig, ax = plt.subplots(figsize=(7, 5))
    for t in df["disturbance_type_forced"].dropna().unique():
        sub = df[df["disturbance_type_forced"] == t]
        ax.scatter(sub["disturbance_magnitude"], sub["peak_tilt_deg"],
                   s=18, alpha=0.6, label=t, color=TYPE_COLORS.get(t))
    ax.set_xlabel("Disturbance magnitude (units vary by type, see legend/labels)")
    ax.set_ylabel("Peak tilt reached (degrees)")
    ax.set_title("Peak tilt vs. disturbance magnitude, by type")
    ax.legend(title="type (" + ", ".join(f"{t}: {u}" for t, u in unit_by_type.items()) + ")")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / "peak_tilt_vs_magnitude.png", dpi=150)
    plt.close(fig)

    # 3) recovery time vs. magnitude, kick/torque only (wind's analogous
    #    metric is steady-state error, plotted separately below -- a
    #    sustained push doesn't have a single "recovery time" the same way
    #    a one-shot kick/torque impulse does).
    kt = df[df["disturbance_type_forced"].isin(["kick", "torque"]) & df["recovered"].fillna(False)]
    if len(kt):
        fig, ax = plt.subplots(figsize=(7, 5))
        for t in kt["disturbance_type_forced"].unique():
            sub = kt[kt["disturbance_type_forced"] == t]
            ax.scatter(sub["disturbance_magnitude"], sub["recovery_time_steps"],
                       s=18, alpha=0.6, label=t, color=TYPE_COLORS.get(t))
        ax.set_xlabel("Disturbance magnitude")
        ax.set_ylabel("Recovery time (control steps)")
        ax.set_title("Recovery time vs. magnitude (recovered episodes only)")
        ax.legend()
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_dir / "recovery_time_vs_magnitude.png", dpi=150)
        plt.close(fig)

    # 4) wind steady-state error vs. magnitude
    wind = df[(df["disturbance_type_forced"] == "wind") & df["wind_steady_state_error_mean"].notna()]
    if len(wind):
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.scatter(wind["disturbance_magnitude"], wind["wind_steady_state_error_mean"],
                   s=18, alpha=0.6, color=TYPE_COLORS.get("wind"))
        ax.set_xlabel(f"Wind magnitude ({unit_by_type.get('wind', '')})")
        ax.set_ylabel("Steady-state position error (m)")
        ax.set_title("Wind: steady-state error vs. magnitude")
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_dir / "wind_steady_state_error_vs_magnitude.png", dpi=150)
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", type=str, required=True,
                        help="Path to the checkpoint to sweep -- pass the champion checkpoint, "
                             "not necessarily the final save (per this project's own house rule).")
    parser.add_argument("--stage", type=str, default="disturbance_3x5", choices=sorted(HOVER_STAGE_PRESETS.keys()))
    parser.add_argument("--episodes-per-bucket", type=int, default=40,
                        help="Episodes per (type, level) bucket -- 40 x 15 buckets = 600 episodes total.")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--label", type=str, default=None,
                        help="Results subfolder name. Defaults to '<checkpoint filename>_<timestamp>' "
                             "so repeated sweeps of the same checkpoint never overwrite each other.")
    args = parser.parse_args()

    model_path = Path(args.model)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    label = args.label or f"{model_path.stem}_{timestamp}"
    out_dir = RESULTS_DIR / label
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Sweeping {args.model}")
    print(f"Stage preset: {args.stage} | episodes/bucket: {args.episodes_per_bucket} | seed: {args.seed}")
    print(f"Output: {out_dir}\n")

    rows = run_sweep(str(model_path), args.stage, args.episodes_per_bucket, args.seed)

    # Full per-episode dump, traces included -- for anyone who wants to
    # pull up one specific episode's tilt curve later without re-running.
    with open(out_dir / "raw_episodes_full.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "raw_episodes.csv", index=False)

    summary = summarize(df)
    summary.to_csv(out_dir / "summary_by_type_level.csv", index=False)

    unit_by_type = {t: DISTURBANCE_TYPES[t].unit for t in df["disturbance_type_forced"].dropna().unique()}
    make_figures(df, summary, out_dir / "figures", unit_by_type)

    manifest = {
        "model_path": str(model_path),
        "git_commit": git_commit_hash(),
        "stage": args.stage,
        "episodes_per_bucket": args.episodes_per_bucket,
        "seed": args.seed,
        "label": label,
        "generated_at_utc": timestamp,
        "n_episodes_total": len(rows),
        "units_by_type": unit_by_type,
        "files": {
            "raw_episodes_csv": "raw_episodes.csv",
            "raw_episodes_full_jsonl": "raw_episodes_full.jsonl",
            "summary_csv": "summary_by_type_level.csv",
            "figures_dir": "figures/",
        },
    }
    with open(out_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nDone. {len(rows)} episodes across {summary.shape[0]} buckets.")
    print(f"Results written to: {out_dir}")
    print("\nSummary:")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
