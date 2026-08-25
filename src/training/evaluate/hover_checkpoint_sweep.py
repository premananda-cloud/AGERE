"""
Sweep-evaluate a series of checkpoints from ONE training run (e.g. the
50k-step increments CheckpointCallback already saves) under an IDENTICAL
eval condition -- same seed, same episode count, same --stage -- so
results are directly comparable across checkpoints rather than confounded
by different random disturbance draws landing on easier/harder episodes.

Answers "is this run still learning, or has it plateaued" with actual
task-performance numbers, rather than inferring it from train/std or
approx_kl in the training printout -- those describe how much the POLICY
UPDATE moved, not whether the policy is actually getting better at the
task. A std that's still climbing (as seen in the 2026-08-25 run) is
ambiguous by itself: could mean "still learning, needs more steps" or
"stuck oscillating." This resolves that ambiguity by measuring the thing
that actually matters -- crash rate and position error, per checkpoint.

Reuses hover_evaluate.py's run_episode() rather than duplicating episode
logic -- if that function's behavior changes, this sweep stays in sync
automatically.

Usage:
    # Auto-discover every hover_stabilize_ppo_seed0_disturbance_3x5_*_steps.zip
    # checkpoint in the default checkpoints dir, evaluate each with 60
    # episodes under the disturbance_3x5 stage, same seed for every one:
    python -m src.training.evaluate.hover_checkpoint_sweep \\
        --prefix hover_stabilize_ppo_seed0_disturbance_3x5 \\
        --stage disturbance_3x5 --episodes 60 --seed 0

    # Narrower episode count for a quick look; widen for a trustworthy
    # verdict once you're deciding whether to commit to more training.
"""

import argparse
import glob
import os
import re
from dataclasses import replace

import numpy as np
from stable_baselines3 import PPO

from src.config import ProjectConfig, HOVER_STAGE_PRESETS
from src.paths import MODEL_WEIGHTS_DIR
from src.training.gym_wrapper.hover_gym_wrapper import HoverGymEnv
from src.training.evaluate.hover_evaluate import run_episode

STEP_RE = re.compile(r"_(\d+)_steps\.zip$")

# How many trailing checkpoints define "recent" for the plateau check, and
# how much crash-rate improvement (previous window mean minus recent
# window mean) counts as "still meaningfully improving" rather than noise.
# 3 checkpoints = 150k steps at this run's --checkpoint-every 50000: enough
# to smooth over single-checkpoint noise without needing the whole run.
TREND_WINDOW = 3
PLATEAU_THRESHOLD = 0.03  # 3 percentage points of crash rate


def discover_checkpoints(checkpoint_dir: str, prefix: str) -> list[str]:
    pattern = os.path.join(checkpoint_dir, f"{prefix}_*_steps.zip")
    paths = glob.glob(pattern)
    with_steps = [(p, int(m.group(1))) for p in paths if (m := STEP_RE.search(p))]
    with_steps.sort(key=lambda x: x[1])
    return with_steps


def eval_one_checkpoint(model_path: str, config: ProjectConfig, episodes: int, seed: int | None) -> dict:
    env = HoverGymEnv(config)
    model = PPO.load(model_path, device="cpu")

    crashes = []
    pos_errors = []
    type_crashes: dict[str, list[bool]] = {}

    for ep in range(episodes):
        s = seed if ep == 0 else None
        result = run_episode(env, model, seed=s)
        crashes.append(result["is_crash"])
        pos_errors.append(result["final_pos_error"])
        if result["disturbance_fired"]:
            type_crashes.setdefault(result["disturbance_type"], []).append(result["is_crash"])

    env.close()

    summary = {
        "crash_rate": float(np.mean(crashes)),
        "mean_pos_error": float(np.mean(pos_errors)),
    }
    for t, cs in type_crashes.items():
        summary[f"{t}_crash_rate"] = float(np.mean(cs))
        summary[f"{t}_n"] = len(cs)
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--checkpoint-dir", type=str, default=None,
        help="Defaults to model/model_weights/checkpoints (see src/paths.py's MODEL_WEIGHTS_DIR)."
    )
    parser.add_argument(
        "--prefix", type=str, required=True,
        help="Checkpoint filename prefix to sweep, e.g. hover_stabilize_ppo_seed0_disturbance_3x5 "
             "(matches <prefix>_<N>_steps.zip, the CheckpointCallback naming convention)."
    )
    parser.add_argument("--episodes", type=int, default=60, help="Episodes per checkpoint, same count for every one.")
    parser.add_argument(
        "--seed", type=int, default=0,
        help="Same seed reused for EVERY checkpoint's first reset -- this is what makes the sweep "
             "apples-to-apples (identical start/disturbance draw sequence per checkpoint) rather than "
             "each checkpoint getting luckier or unluckier random episodes."
    )
    parser.add_argument(
        "--stage", type=str, default=None, choices=sorted(HOVER_STAGE_PRESETS.keys()),
        help="Same as hover_evaluate.py's --stage -- REQUIRED to see disturbance episodes at all."
    )
    args = parser.parse_args()

    checkpoint_dir = args.checkpoint_dir or str(MODEL_WEIGHTS_DIR / "checkpoints")
    checkpoints = discover_checkpoints(checkpoint_dir, args.prefix)
    if not checkpoints:
        print(f"No checkpoints matching {args.prefix}_*_steps.zip found in {checkpoint_dir}")
        return

    config = ProjectConfig()
    if args.stage:
        config.task = replace(config.task, **HOVER_STAGE_PRESETS[args.stage])
        print(f"Applied stage preset '{args.stage}': {HOVER_STAGE_PRESETS[args.stage]}")
    print(f"Sweeping {len(checkpoints)} checkpoints, {args.episodes} episodes each, seed={args.seed} "
          f"(identical eval condition per checkpoint)\n")

    rows = []
    for path, step in checkpoints:
        summary = eval_one_checkpoint(path, config, args.episodes, args.seed)
        rows.append((step, summary))
        type_bits = " | ".join(
            f"{k.replace('_crash_rate', '')}={v*100:.0f}%"
            for k, v in summary.items() if k.endswith("_crash_rate") and k != "crash_rate"
        )
        print(f"{step:>7} steps | crash {summary['crash_rate']*100:5.1f}% | "
              f"pos_err {summary['mean_pos_error']:.3f} m | {type_bits}")

    print("\n" + "=" * 60)
    if len(rows) < 2 * TREND_WINDOW:
        print(f"Only {len(rows)} checkpoints available -- need at least {2*TREND_WINDOW} for a "
              f"trend verdict (comparing two {TREND_WINDOW}-checkpoint windows). Read the table above "
              f"by eye instead.")
        return

    recent = [r[1]["crash_rate"] for r in rows[-TREND_WINDOW:]]
    previous = [r[1]["crash_rate"] for r in rows[-2 * TREND_WINDOW:-TREND_WINDOW]]
    recent_mean = float(np.mean(recent))
    previous_mean = float(np.mean(previous))
    improvement = previous_mean - recent_mean  # positive = crash rate went down = improving

    recent_steps = f"{rows[-TREND_WINDOW][0]}-{rows[-1][0]}"
    previous_steps = f"{rows[-2*TREND_WINDOW][0]}-{rows[-TREND_WINDOW-1][0]}"
    print(f"Trailing window:  steps {recent_steps} -> mean crash rate {recent_mean*100:.1f}%")
    print(f"Prior window:     steps {previous_steps} -> mean crash rate {previous_mean*100:.1f}%")
    print(f"Improvement:      {improvement*100:+.1f} percentage points "
          f"(threshold for 'still learning': >{PLATEAU_THRESHOLD*100:.0f}pp)")

    if improvement > PLATEAU_THRESHOLD:
        print(
            "\n-> STILL IMPROVING. Crash rate dropped meaningfully in the most recent window vs the "
            "one before it. More training steps at current settings look like a reasonable next move "
            "-- continue with --init-from this run's final checkpoint."
        )
    else:
        print(
            "\n-> PLATEAUED (or noisy/flat). No meaningful crash-rate improvement between the two most "
            "recent windows at current settings. More steps alone are unlikely to help much from here "
            "-- worth pausing to reconsider rather than continuing to spend compute (candidates: the "
            "ent_coef/std issue flagged earlier, curriculum restructuring, or a larger eval to confirm "
            "this reading before deciding)."
        )


if __name__ == "__main__":
    main()
