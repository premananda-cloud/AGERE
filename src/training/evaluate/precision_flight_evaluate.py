"""
Evaluate a trained precision takeoff -> hover -> land policy.

Runs the policy deterministically over N episodes and reports:
  - success rate (completed all three phases + soft landing held for
    landing_hold_time_sec)
  - crash rate (out_of_bounds / tilt / hard_landing)
  - mean episode reward
  - hover precision: fraction of hover-phase steps spent inside
    hover_precision_radius, and mean position error during the hover
    phase specifically -- distinguishes "reaches hover but wanders" from
    "genuinely precise," which the pass/fail success flag alone can't
  - phase reached at failure -- which of takeoff/hover/landing failures
    are stuck in, same diagnostic value as waypoint_evaluate.py's
    never-finished-route breakdown

Usage:
    python -m src.training.evaluate.precision_flight_evaluate --model model/model_weights/precision_flight_ppo_seed0.zip --episodes 20 --seed 42
    python -m src.training.evaluate.precision_flight_evaluate --gui

See precision_flight_train.py's module docstring for the PATHS NOTE on
why the model path default is defined locally here rather than sourced
from src/paths.py.
"""

import argparse
from collections import Counter
from pathlib import Path

import numpy as np
from stable_baselines3 import PPO

from src.config import ProjectConfig, PrecisionFlightTaskConfig
from src.training.gym_wrapper.precision_flight_gym_wrapper import PrecisionFlightGymEnv, PHASE_HOVER
from src.model_registry import record_eval

_MODEL_WEIGHTS_DIR = Path("model/model_weights")


def _default_model_path() -> Path:
    return _MODEL_WEIGHTS_DIR / "precision_flight_ppo.zip"


def run_episode(env: PrecisionFlightGymEnv, model: PPO, seed=None):
    obs, info = env.reset(seed=seed)

    total_reward = 0.0
    final_pos_error = None
    success = False
    is_crash = False
    truncation_reason = None
    final_phase = info["phase"]

    hover_errors = []   # position error at every step spent in the hover phase

    terminated = truncated = False
    while not (terminated or truncated):
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        final_pos_error = info["position_error_norm"]
        final_phase = info["phase"]
        success = info["success"]

        if info["phase"] == PHASE_HOVER:
            hover_errors.append(final_pos_error)

        if truncated:
            is_crash = info.get("is_crash", False)
            truncation_reason = info.get("truncation_reason")

    reach_radius = env.task.hover_precision_radius
    precision_fraction = (
        float(np.mean([e < reach_radius for e in hover_errors])) if hover_errors else None
    )
    mean_hover_error = float(np.mean(hover_errors)) if hover_errors else None

    return {
        "success": success,
        "final_phase": final_phase,
        "is_crash": is_crash,
        "truncation_reason": truncation_reason,
        "final_pos_error": final_pos_error,
        "total_reward": total_reward,
        "precision_fraction": precision_fraction,
        "mean_hover_error": mean_hover_error,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default=None, help="Defaults to precision_flight_ppo.zip")
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument(
        "--no-tag", action="store_true",
        help="Skip logging this eval to the model registry -- same convention as waypoint_evaluate.py."
    )
    args = parser.parse_args()
    model_path = args.model or str(_default_model_path())

    config = ProjectConfig(task=PrecisionFlightTaskConfig())
    if args.gui:
        config.sim.gui = True

    env = PrecisionFlightGymEnv(config)
    model = PPO.load(model_path, device="cpu")

    if args.seed is None:
        print(
            "Note: no --seed given — this eval sequence is unseeded and will not "
            "reproduce exactly on a rerun. Pass --seed if you plan to compare this "
            "result against another run.\n"
        )

    results = []
    for ep in range(args.episodes):
        seed = args.seed if ep == 0 else None
        result = run_episode(env, model, seed=seed)
        results.append(result)

        crash_note = f" ({result['truncation_reason']})" if result["is_crash"] else ""
        precision_note = (
            f" | hover precision: {result['precision_fraction']*100:.0f}% in-radius, "
            f"mean err {result['mean_hover_error']:.3f}m"
            if result["precision_fraction"] is not None else " | never reached hover"
        )
        print(
            f"episode {ep+1:2d}/{args.episodes} | "
            f"success: {result['success']} | "
            f"final phase: {result['final_phase']} | "
            f"crash: {result['is_crash']}{crash_note} | "
            f"final pos error: {result['final_pos_error']:.3f} m | "
            f"reward: {result['total_reward']:.1f}"
            f"{precision_note}"
        )

    env.close()

    success_rate = float(np.mean([r["success"] for r in results]))
    crash_rate = float(np.mean([r["is_crash"] for r in results]))
    mean_reward = float(np.mean([r["total_reward"] for r in results]))
    precision_fractions = [r["precision_fraction"] for r in results if r["precision_fraction"] is not None]
    mean_precision_fraction = float(np.mean(precision_fractions)) if precision_fractions else None

    print("\n" + "=" * 55)
    print(f"Episodes run:              {args.episodes}")
    print(f"Success rate:              {success_rate*100:.1f}%")
    print(f"Crash rate:                {crash_rate*100:.1f}%")
    print(f"Mean episode reward:       {mean_reward:.1f}")
    if mean_precision_fraction is not None:
        print(f"Mean hover precision:      {mean_precision_fraction*100:.1f}% of hover-phase steps in-radius")
    print("=" * 55)

    if not args.no_tag:
        h = record_eval(
            model_path=model_path,
            seed=args.seed,
            episodes=args.episodes,
            success_rate=success_rate,
            mean_waypoints_reached=mean_precision_fraction if mean_precision_fraction is not None else 0.0,
            crash_rate=crash_rate,
            mean_reward=mean_reward,
        )
        print(f"Logged to model registry (hash {h[:12]}...). "
              f"Note: 'mean_waypoints_reached' field is repurposed here as mean hover-precision "
              f"fraction (0-1), not a waypoint count -- registry schema is shared across tasks, "
              f"not task-specific. Query with: python -m src.model_registry describe {model_path}\n")

    failures = [r for r in results if not r["success"]]
    if failures:
        print(f"Failed episodes: {len(failures)}/{args.episodes}")
        phase_counts = Counter(r["final_phase"] for r in failures)
        print(f"  Failed at phase: {dict(phase_counts)}")
        reasons = [r["truncation_reason"] for r in failures if r["truncation_reason"]]
        if reasons:
            print(f"  Failure reasons: {dict(Counter(reasons))}")


if __name__ == "__main__":
    main()
