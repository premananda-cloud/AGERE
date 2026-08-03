"""
Live PyBullet demo of the trained hover/stabilize policy — for showing to
other people, not for evaluation (see evaluate.py for that).

Runs continuously, looping episodes, at real-time speed so it's watchable.
Draws a green marker at the target position so viewers can see what the
drone is trying to hold station at.

On Intel integrated graphics with no dedicated GPU, this may fail to open
the GUI window or render a black screen — see demo_intel.py, which is
identical except for Mesa/OpenGL compatibility flags.

Usage:
    python -m src.training.demo
    python -m src.training.demo --model hover_stabilize_ppo.zip
    python -m src.training.demo --episodes 5   # stop after N episodes instead of looping forever
"""

import argparse
import time

from stable_baselines3 import PPO
from gym_pybullet_drones.utils.utils import sync

from src.config import ProjectConfig
from src.training.gym_wrapper import HoverGymEnv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="hover_stabilize_ppo.zip")
    parser.add_argument("--episodes", type=int, default=None, help="Loop forever if not set")
    args = parser.parse_args()

    config = ProjectConfig()
    config.sim.gui = True  # demo always shows the window, no --gui flag needed

    env = HoverGymEnv(config)
    model = PPO.load(args.model)

    timestep = 1.0 / config.sim.ctrl_freq
    episode = 0

    try:
        while args.episodes is None or episode < args.episodes:
            episode += 1
            obs, _ = env.reset()
            env.sim.draw_target_marker(config.task.target_position)

            print(f"\n--- episode {episode} ---")
            start_time = time.time()
            terminated = truncated = False
            step_i = 0

            while not (terminated or truncated):
                action, _ = model.predict(obs, deterministic=True)
                obs, reward, terminated, truncated, info = env.step(action)
                sync(step_i, start_time, timestep)  # paces to real time so it's watchable
                step_i += 1

            reason = info.get("truncation_reason", "n/a")
            print(f"episode {episode} ended: {reason} | final pos error: {info['position_error_norm']:.3f} m")

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        env.close()


if __name__ == "__main__":
    main()
