"""
PARKED — SITL/PX4 transplant phase. See train.py for the active
gym-pybullet-drones training entry point.

Entry point for training the hover/stabilize policy.

Run with the sim already up (PX4 SITL + Gazebo, GPU rendering confirmed
per the 2026-07-23 session) and MAVSDK connectivity verified before
launching this — the env will hang on reset() if PX4 never connects.

Usage:
    python -m src.training.train
"""

from gymnasium.wrappers import TimeLimit

from src.config import ProjectConfig
from src.environments.hover_env import HoverStabilizeEnv
from src.policies.ppo_policy import build_ppo


def main():
    config = ProjectConfig()

    env = HoverStabilizeEnv(config)
    env = TimeLimit(env, max_episode_steps=config.task.max_episode_steps)

    model = build_ppo(env, config.ppo, tensorboard_log="./tb_logs/hover")

    model.learn(total_timesteps=config.ppo.total_timesteps)
    model.save("hover_stabilize_ppo")

    env.close()


if __name__ == "__main__":
    main()
