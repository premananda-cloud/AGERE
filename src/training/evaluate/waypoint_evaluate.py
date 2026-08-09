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
  - (NEW 2026-08-08) closest approach on the leg where each never-finished
    episode got stuck — see "Stuck-leg diagnosis" below

Usage:
    python -m src.training.evaluate.waypoint_evaluate
    python -m src.training.evaluate.waypoint_evaluate --model model/model_weights/waypoint_nav_ppo_seed0.zip
    python -m src.training.evaluate.waypoint_evaluate --episodes 20
    python -m src.training.evaluate.waypoint_evaluate --gui
    python -m src.training.evaluate.waypoint_evaluate --seed 42   # reproducible eval sequence
                                                                    # (matters — see note below)

NOTE ON --seed: without it, every run samples a fresh, unseeded sequence
of start conditions, same convention as hover_evaluate.py (only the first
reset is seeded; gymnasium's RNG carries forward deterministically from
there). Two eval runs of the *same* checkpoint without --seed are
different samples and can legitimately disagree — this is why the
2026-08-06 and 2026-08-07 sessions logged different "mean waypoints
reached" numbers even before the underlying checkpoint itself changed.
Pass --seed for any result you intend to compare against a later run.
"""

import argparse
from collections import Counter

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

    # Per-leg closest approach, keyed by "waypoints_reached at that step."
    # Lets us isolate the specific leg an episode got stuck on (the leg
    # index equal to its final waypoints_reached count) from earlier legs
    # it already cleared. Answers a concrete open question from
    # docs/status.md: on the leg where a never-finished episode times out,
    # did the drone ever get within waypoint_reach_radius of that target
    # (radius width isn't the bottleneck, or there's a registration bug)
    # or did it never get close at all (radius isn't the bottleneck,
    # pacing/reward is)? Caveat: this tracks closest approach to
    # whatever the *current* target is at each step, not a strictly
    # geometric per-leg segmentation — good enough to answer "close vs.
    # not close," not precise enough for finer claims.
    leg_min_error = {}

    terminated = truncated = False
    while not (terminated or truncated):
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        final_pos_error = info["position_error_norm"]
        waypoints_reached = info["waypoints_reached"]
        success = info["success"]

        leg_min_error[waypoints_reached] = min(
            leg_min_error.get(waypoints_reached, float("inf")), final_pos_error
        )

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
        "stuck_leg_min_error": leg_min_error.get(waypoints_reached),
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
        help="Seed the first reset for a reproducible eval sequence, same convention as hover_evaluate.py. "
             "See module docstring — strongly recommended for any result you'll compare against a later run."
    )
    args = parser.parse_args()
    model_path = args.model or str(waypoint_model_path())

    config = ProjectConfig(task=WaypointTaskConfig())
    if args.gui:
        config.sim.gui = True

    env = WaypointGymEnv(config)
    model = PPO.load(model_path, device="cpu")
    n_waypoints = len(env.task.waypoints)

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
    never_finished_route = []
    if failures:
        never_finished_route = [r for r in failures if r["waypoints_reached"] < n_waypoints]
        finished_but_failed_landing = [r for r in failures if r["waypoints_reached"] >= n_waypoints]
        print(f"\nFailed episodes: {len(failures)}/{args.episodes}")
        print(f"  Never finished the route:        {len(never_finished_route)}/{len(failures)}")
        print(f"  Finished route, failed landing:  {len(finished_but_failed_landing)}/{len(failures)}")
        if never_finished_route:
            reasons = [r["truncation_reason"] for r in never_finished_route if r["truncation_reason"]]
            if reasons:
                counts = Counter(reasons)
                print(f"  Route-failure reasons: {dict(counts)}")
        if finished_but_failed_landing:
            reasons = [r["truncation_reason"] for r in finished_but_failed_landing if r["truncation_reason"]]
            if reasons:
                counts = Counter(reasons)
                print(f"  Landing-failure reasons: {dict(counts)}")

    # --- Stuck-leg diagnosis (NEW 2026-08-08) ---------------------------
    # Directly answers the open reach-radius question instead of guessing:
    # for every episode that never finished the route, how close did it
    # actually get to the specific waypoint it got stuck on before timing
    # out? If episodes are routinely getting within waypoint_reach_radius
    # and still not registering, that's a bug in
    # WaypointGymEnv._advance_waypoint_if_reached(), not a tuning
    # question. If they're not getting close at all, radius width isn't
    # the bottleneck — don't touch it.
    stuck_mins = [
        r["stuck_leg_min_error"] for r in never_finished_route
        if r["stuck_leg_min_error"] is not None
    ]
    if stuck_mins:
        reach_radius = env.task.waypoint_reach_radius
        within_radius = [m for m in stuck_mins if m <= reach_radius]
        print(f"\nClosest approach on the leg each never-finished episode got stuck on:")
        print(f"  mean: {np.mean(stuck_mins):.3f} m | min: {np.min(stuck_mins):.3f} m | max: {np.max(stuck_mins):.3f} m")
        print(f"  waypoint_reach_radius: {reach_radius} m")
        print(f"  got within reach_radius but never registered as reached: {len(within_radius)}/{len(stuck_mins)}")
        if len(within_radius) == 0:
            print(
                "  -> Never actually got close on the stuck leg. Reach radius width is NOT "
                "the bottleneck here. This is consistent with the tb_logs entropy-runaway "
                "finding (train/std climbing instead of converging) — points at pacing/reward, "
                "not precision. Don't widen waypoint_reach_radius based on this data."
            )
        else:
            print(
                "  -> Some episodes got within reach_radius without the waypoint registering. "
                "Worth checking _advance_waypoint_if_reached() for a genuine bug before assuming "
                "this is a tuning question."
            )


if __name__ == "__main__":
    main()
