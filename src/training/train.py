"""
Entry point for training the hover/stabilize policy — active track,
running against gym-pybullet-drones (in-process PyBullet physics, no
PX4/MAVSDK/network dependency at all).

Usage:
    python -m src.training.train
    python -m src.training.train --gui               # watch training live
    python -m src.training.train --timesteps 500000  # override config
"""

import argparse

from src.config import ProjectConfig
from src.environments.pybullet.hover_env import ConfigurableHoverAviary
from src.policies.ppo_policy import build_ppo


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gui", action="store_true", help="Render PyBullet GUI during training")
    parser.add_argument("--timesteps", type=int, default=None, help="Override total_timesteps from config")
    args = parser.parse_args()

    config = ProjectConfig()
    if args.gui:
        config.pybullet_task.gui = True
    if args.timesteps:
        config.ppo.total_timesteps = args.timesteps

    env = ConfigurableHoverAviary(config.pybullet_task)

    # Note: build_ppo() wraps env in Monitor internally — don't double-wrap here.
    model = build_ppo(env, config.ppo, tensorboard_log="./tb_logs/hover")
    model.learn(total_timesteps=config.ppo.total_timesteps)
    model.save("hover_stabilize_ppo")

    env.close()


if __name__ == "__main__":
    main()
