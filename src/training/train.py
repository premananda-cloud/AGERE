"""
Entry point for training the hover/stabilize policy.

AGERE is PyBullet + Gymnasium only — no PX4, no network dependency. See
docs/code-structure.md for how environments/, actions/, and training/
divide responsibilities.

Usage:
    python -m src.training.train
    python -m src.training.train --gui               # watch training live
    python -m src.training.train --timesteps 500000  # override config
"""

import argparse

from src.config import ProjectConfig
from src.training.gym_wrapper import HoverGymEnv
from src.policies.ppo_policy import build_ppo


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gui", action="store_true", help="Render PyBullet GUI during training")
    parser.add_argument("--timesteps", type=int, default=None, help="Override total_timesteps from config")
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Training seed, passed to SB3's PPO (seeds torch/numpy and the env/spaces). "
             "Needed for Stage 3's 'holds across 3+ seeds' requirement — run this three times "
             "with different --seed values and evaluate each saved model independently."
    )
    args = parser.parse_args()

    config = ProjectConfig()
    if args.gui:
        config.sim.gui = True
    if args.timesteps:
        config.ppo.total_timesteps = args.timesteps

    env = HoverGymEnv(config)

    # Note: build_ppo() wraps env in Monitor internally — don't double-wrap here.
    model = build_ppo(env, config.ppo, tensorboard_log="./tb_logs/hover", seed=args.seed)
    model.learn(total_timesteps=config.ppo.total_timesteps)

    # Seed-suffixed filename so multi-seed training runs (Stage 3) don't
    # clobber each other's saved model.
    save_name = f"hover_stabilize_ppo_seed{args.seed}" if args.seed is not None else "hover_stabilize_ppo"
    model.save(save_name)
    print(f"\nSaved model to {save_name}.zip")

    env.close()


if __name__ == "__main__":
    main()
