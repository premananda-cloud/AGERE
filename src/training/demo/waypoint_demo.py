"""
Live PyBullet demo of the trained waypoint-navigation + landing policy --
for showing to other people, not for evaluation (see
evaluate/waypoint_evaluate.py for that, including the stuck-leg and
failure-breakdown diagnostics this script deliberately doesn't repeat).

Mirrors hover_demo.py's structure (same --model/--episodes flags, same
real-time pacing via gym_pybullet_drones' sync(), same GUI-always-on
convention). One addition: draws all five waypoints as markers up front,
color-coded by status (passed / current target / upcoming), and redraws
them whenever the policy advances to a new waypoint -- see
drone_sim.py's draw_target_marker(), which gained color/radius params on
2026-08-06 specifically for this.

Deliberately reads waypoint progress from config.task.waypoints (the
known, static route) plus the env's public info dict
(info["waypoints_reached"]) rather than reaching into
WaypointGymEnv._waypoints/_waypoint_idx. Those are private for a reason,
and this script never actually needed them -- the full route is already
public via config, and progress is already exposed via info. (The
private-attribute approach was the plan sketched in earlier devlogs;
turned out unnecessary once actually written.)

This file replaces the previous accidental duplicate of
waypoint_evaluate.py that had been sitting here unnoticed since
2026-08-06.

Usage:
    python -m src.training.demo.waypoint_demo
    python -m src.training.demo.waypoint_demo --model model/model_weights/waypoint_nav_ppo_seed0.zip
    python -m src.training.demo.waypoint_demo --episodes 3   # stop after N episodes instead of looping forever

NOTE: the color/radius kwargs passed to draw_target_marker() below assume
RGB-0-to-1 tuples, matching the most common PyBullet debug-draw
convention -- this couldn't be verified against the actual
drone_sim.py signature while writing this (file wasn't in hand). If the
first run throws a TypeError on draw_route(), check
draw_target_marker()'s real parameter types in drone_sim.py and adjust
COLOR_* below to match; the loop/pacing logic underneath doesn't depend
on getting this right.
"""

import argparse
import time

from stable_baselines3 import PPO
from gym_pybullet_drones.utils.utils import sync

from src.config import ProjectConfig, WaypointTaskConfig
from src.paths import waypoint_model_path
from src.training.gym_wrapper.waypoint_gym_wrapper import WaypointGymEnv

# RGB 0-1. RADIUS_CURRENT deliberately matches waypoint_reach_radius (0.15m)
# so the marker itself shows the viewer the actual zone the policy needs to
# enter -- useful given how much of this project's diagnosis has hinged on
# "does it get within radius or not."
COLOR_UPCOMING = (0.5, 0.5, 0.5)   # gray -- not the target yet
COLOR_CURRENT = (1.0, 1.0, 0.0)    # yellow -- what the policy is flying toward right now
COLOR_PASSED = (0.0, 1.0, 0.0)     # green -- already reached
RADIUS_UPCOMING = 0.08
RADIUS_CURRENT = 0.15
RADIUS_PASSED = 0.08


def draw_route(env: WaypointGymEnv, waypoints_reached: int):
    """(Re)draws every waypoint, color-coded by status. Called once at
    episode start and again only when waypoints_reached changes -- not
    every step, since redrawing 5 static markers 30x/second is wasteful
    and PyBullet debug items persist on their own between draws."""
    for i, wp in enumerate(env.task.waypoints):
        if i < waypoints_reached:
            color, radius = COLOR_PASSED, RADIUS_PASSED
        elif i == waypoints_reached:
            color, radius = COLOR_CURRENT, RADIUS_CURRENT
        else:
            color, radius = COLOR_UPCOMING, RADIUS_UPCOMING
        env.sim.draw_target_marker(wp, color=color, radius=radius)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model", type=str, default=None,
        help="Defaults to model/model_weights/waypoint_nav_ppo_seed0.zip (see src/paths.py)"
    )
    parser.add_argument("--episodes", type=int, default=None, help="Loop forever if not set")
    args = parser.parse_args()
    model_path = args.model or str(waypoint_model_path())

    config = ProjectConfig(task=WaypointTaskConfig())
    config.sim.gui = True  # demo always shows the window, no --gui flag needed

    env = WaypointGymEnv(config)
    model = PPO.load(model_path, device="cpu")

    timestep = 1.0 / config.sim.ctrl_freq
    episode = 0
    n_waypoints = len(env.task.waypoints)

    try:
        while args.episodes is None or episode < args.episodes:
            episode += 1
            obs, _ = env.reset()
            waypoints_reached = 0
            draw_route(env, waypoints_reached)

            print(f"\n--- episode {episode} ---")
            start_time = time.time()
            terminated = truncated = False
            step_i = 0

            while not (terminated or truncated):
                action, _ = model.predict(obs, deterministic=True)
                obs, reward, terminated, truncated, info = env.step(action)
                sync(step_i, start_time, timestep)  # paces to real time so it's watchable
                step_i += 1

                if info["waypoints_reached"] != waypoints_reached:
                    waypoints_reached = info["waypoints_reached"]
                    draw_route(env, waypoints_reached)
                    print(f"  waypoint {waypoints_reached}/{n_waypoints} reached")

            if terminated:
                outcome = "LANDED (success)" if info.get("success") else "landed, but did not register as success"
            else:
                outcome = info.get("truncation_reason", "n/a")
            print(
                f"episode {episode} ended: {outcome} | "
                f"waypoints reached: {info['waypoints_reached']}/{n_waypoints} | "
                f"final pos error: {info['position_error_norm']:.3f} m"
            )

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        env.close()


if __name__ == "__main__":
    main()
