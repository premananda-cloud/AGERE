"""
Entry point for training the waypoint-navigation + landing policy.

Mirrors hover_train.py's structure exactly (same flag set, same
build_ppo/Monitor note) — the only difference is which task config and
env class get wired in. See docs/code-structure.md for how environments/,
actions/, and training/ divide responsibilities.

Usage:
    python -m src.training.waypoint_train
    python -m src.training.waypoint_train --gui               # watch training live
    python -m src.training.waypoint_train --timesteps 500000  # override config
    python -m src.training.waypoint_train --seed 0            # optional, same convention as hover_train.py

Saves to model/waypoint_nav/waypoint_nav_ppo[_seed{N}].zip (see
src/paths.py) — not the working directory.

Per the demo scope in docs/status.md, the goal here is one seed with a
consistently good success rate, not the three-seed robustness hover
required — --seed is available for reproducibility but there's no
required multi-seed sweep for this task the way there was for hover
Stage 3.
"""

import argparse

from src.config import ProjectConfig, WaypointTaskConfig
from src.paths import waypoint_model_path, WAYPOINT_TB_LOG_DIR
from src.training.gym_wrapper.waypoint_gym_wrapper import WaypointGymEnv
from src.policies.ppo_policy import build_ppo


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gui", action="store_true", help="Render PyBullet GUI during training")
    parser.add_argument("--timesteps", type=int, default=None, help="Override total_timesteps from config")
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Training seed, passed to SB3's PPO (seeds torch/numpy and the env/spaces). "
             "Optional for this task — the demo scope needs one good seed, not a multi-seed sweep."
    )
    args = parser.parse_args()

    config = ProjectConfig(task=WaypointTaskConfig())
    if args.gui:
        config.sim.gui = True
    if args.timesteps:
        config.ppo.total_timesteps = args.timesteps

    env = WaypointGymEnv(config)

    # Note: build_ppo() wraps env in Monitor internally — don't double-wrap here.
    model = build_ppo(env, config.ppo, tensorboard_log=str(WAYPOINT_TB_LOG_DIR), seed=args.seed)
    model.learn(total_timesteps=config.ppo.total_timesteps)

    # Standard location: model/waypoint_nav/waypoint_nav_ppo[_seedN].zip
    # (see src/paths.py) — not the working directory.
    save_path = waypoint_model_path(args.seed)
    model.save(str(save_path))
    print(f"\nSaved model to {save_path}")

    env.close()


if __name__ == "__main__":
    main()
