"""
Evaluate a trained hover/stabilize policy against the staged criteria in
docs/hover-model-plan.md.

Runs the policy deterministically (no exploration noise) over N episodes
with randomized starts, and reports:
  - mean position error at episode end
  - crash rate (out-of-bounds or excessive tilt, NOT counting timeout as a
    crash — reaching the timeout means it survived the whole episode)
  - mean episode reward, for reference against training-log.md entries

Usage:
    python -m src.training.evaluate
    python -m src.training.evaluate --model hover_stabilize_ppo.zip --episodes 20
    python -m src.training.evaluate --gui   # watch the eval episodes
"""

import argparse

import numpy as np
from stable_baselines3 import PPO

from src.config import ProjectConfig
from src.training.gym_wrapper import HoverGymEnv

# Stage 2 criteria, per docs/hover-model-plan.md — keep these two files in
# sync if the plan changes.
STAGE_2_MAX_POSITION_ERROR = 0.3   # meters
STAGE_2_MAX_CRASH_RATE = 0.10      # fraction of episodes


def run_episode(env: HoverGymEnv, model: PPO):
    obs, _ = env.reset()
    total_reward = 0.0
    final_pos_error = None
    is_crash = False

    terminated = truncated = False
    while not (terminated or truncated):
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        final_pos_error = info["position_error_norm"]
        if truncated:
            is_crash = info.get("is_crash", False)

    return final_pos_error, is_crash, total_reward


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="hover_stabilize_ppo.zip")
    parser.add_argument("--episodes", type=int, default=20, help="Matches Stage 2's 20-episode spec")
    parser.add_argument("--gui", action="store_true")
    args = parser.parse_args()

    config = ProjectConfig()
    if args.gui:
        config.sim.gui = True

    env = HoverGymEnv(config)
    model = PPO.load(args.model)

    position_errors = []
    crashes = []
    rewards = []

    for ep in range(args.episodes):
        pos_error, is_crash, total_reward = run_episode(env, model)
        position_errors.append(pos_error)
        crashes.append(is_crash)
        rewards.append(total_reward)
        print(
            f"episode {ep+1:2d}/{args.episodes} | "
            f"final pos error: {pos_error:.3f} m | "
            f"crash: {is_crash} | "
            f"reward: {total_reward:.1f}"
        )

    env.close()

    mean_pos_error = float(np.mean(position_errors))
    crash_rate = float(np.mean(crashes))
    mean_reward = float(np.mean(rewards))

    print("\n" + "=" * 50)
    print(f"Episodes run:          {args.episodes}")
    print(f"Mean final pos error:  {mean_pos_error:.3f} m")
    print(f"Crash rate:            {crash_rate*100:.1f}%")
    print(f"Mean episode reward:   {mean_reward:.1f}")
    print("=" * 50)

    print("\nStage 2 criteria (docs/hover-model-plan.md):")
    pos_ok = mean_pos_error < STAGE_2_MAX_POSITION_ERROR
    crash_ok = crash_rate < STAGE_2_MAX_CRASH_RATE
    print(f"  [{'PASS' if pos_ok else 'FAIL'}] mean pos error < {STAGE_2_MAX_POSITION_ERROR} m")
    print(f"  [{'PASS' if crash_ok else 'FAIL'}] crash rate < {STAGE_2_MAX_CRASH_RATE*100:.0f}%")

    if pos_ok and crash_ok:
        print("\n-> Stage 2 (usable/viable baseline) reached.")
    else:
        print("\n-> Stage 2 not yet reached. See docs/hover-model-plan.md for what to try next.")


if __name__ == "__main__":
    main()
