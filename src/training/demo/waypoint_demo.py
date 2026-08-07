"""
Evaluate a trained waypoint-navigation + landing policy.

Runs the policy deterministically over N episodes with randomized starts,
and reports:
  - success rate (all waypoints reached + soft landing held for the
    configured duration)
  - mean waypoints reached per episode — useful when success rate is low,
    to distinguish "never gets past waypoint 1" from "usually finishes the
    route but fails the landing specifically"
  - crash rate (out_of_bounds / tilt / hard_landing)
  - mean episode reward

Usage:
    python -m src.training.evaluate.waypoint_evaluate
    python -m src.training.evaluate.waypoint_evaluate --model model/waypoint_nav/waypoint_nav_ppo_seed0.zip
    python -m src.training.evaluate.waypoint_evaluate --episodes 20
    python -m src.training.evaluate.waypoint_evaluate --gui
"""

import argparse

import numpy as np
from stable_baselines3 import PPO

from src.config import ProjectConfig, WaypointTaskConfig
from src.paths import waypoint_model_path
from src.training.gym_wrapper.waypoint_gym_wrapper import WaypointGymEnv


def run_episode(env: WaypointGymEnv, model: PPO, seed=None):
    obs, _ = env.reset(seed=seed)

    total_reward = 0.0
    final_pos_error = None
    success = False
    is_crash = False
    truncation_reason = None
    waypoints_reached = 0

    terminated = truncated = False
    while not (terminated or truncated):
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        final_pos_error = info["position_error_norm"]
        waypoints_reached = info["waypoints_reached"]
        success = info["success"]
        if truncated:
            is_crash = info.get("is_crash", False)
            truncation_reason = info.get("truncation_reason")

    return {
        "success": success,
        "waypoints_reached": waypoints_reached,
        "is_crash": is_crash,
        "truncation_reason": truncation_reason,
        "final_pos_error": final_pos_error,
        "total_reward": total_reward,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model", type=str, default=None,
        help="Defaults to model/waypoint_nav/waypoint_nav_ppo.zip (see src/paths.py)"
    )
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--gui", action="store_true")
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Seed the first reset for a reproducible eval sequence, same convention as hover_evaluate.py."
    )
    args = parser.parse_args()
    model_path = args.model or str(waypoint_model_path())

    config = ProjectConfig(task=WaypointTaskConfig())
    if args.gui:
        config.sim.gui = True

    env = WaypointGymEnv(config)
    model = PPO.load(model_path, device="cpu")
    n_waypoints = len(env.task.waypoints)

    results = []
    for ep in range(args.episodes):
        seed = args.seed if ep == 0 else None
        result = run_episode(env, model, seed=seed)
        results.append(result)

        crash_note = f" ({result['truncation_reason']})" if result["is_crash"] else ""
        print(
            f"episode {ep+1:2d}/{args.episodes} | "
            f"success: {result['success']} | "
            f"waypoints reached: {result['waypoints_reached']}/{n_waypoints} | "
            f"crash: {result['is_crash']}{crash_note} | "
            f"final pos error: {result['final_pos_error']:.3f} m | "
            f"reward: {result['total_reward']:.1f}"
        )

    env.close()

    success_rate = float(np.mean([r["success"] for r in results]))
    crash_rate = float(np.mean([r["is_crash"] for r in results]))
    mean_waypoints = float(np.mean([r["waypoints_reached"] for r in results]))
    mean_reward = float(np.mean([r["total_reward"] for r in results]))

    print("\n" + "=" * 55)
    print(f"Episodes run:              {args.episodes}")
    print(f"Success rate:              {success_rate*100:.1f}%")
    print(f"Mean waypoints reached:    {mean_waypoints:.2f} / {n_waypoints}")
    print(f"Crash rate:                {crash_rate*100:.1f}%")
    print(f"Mean episode reward:       {mean_reward:.1f}")
    print("=" * 55)

    # --- Failure breakdown ---------------------------------------------
    # Where episodes are failing matters more than the success rate alone
    # for deciding what to iterate on next: consistently stalling early in
    # the route points at the waypoint-following reward; reaching the
    # final waypoint but failing to land points at the landing phase
    # specifically (velocity penalty weight, hold-time threshold, etc).
    failures = [r for r in results if not r["success"]]
    if failures:
        never_finished_route = [r for r in failures if r["waypoints_reached"] < n_waypoints]
        finished_but_failed_landing = [r for r in failures if r["waypoints_reached"] >= n_waypoints]
        print(f"\nFailed episodes: {len(failures)}/{args.episodes}")
        print(f"  Never finished the route:        {len(never_finished_route)}/{len(failures)}")
        print(f"  Finished route, failed landing:  {len(finished_but_failed_landing)}/{len(failures)}")
        if never_finished_route:
            reasons = [r["truncation_reason"] for r in never_finished_route if r["truncation_reason"]]
            if reasons:
                from collections import Counter
                counts = Counter(reasons)
                print(f"  Route-failure reasons: {dict(counts)}")
        if finished_but_failed_landing:
            reasons = [r["truncation_reason"] for r in finished_but_failed_landing if r["truncation_reason"]]
            if reasons:
                from collections import Counter
                counts = Counter(reasons)
                print(f"  Landing-failure reasons: {dict(counts)}")


if __name__ == "__main__":
    main()
