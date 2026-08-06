"""
Entry point for training the waypoint-navigation + landing policy.

Mirrors hover_train.py's structure (same --gui/--timesteps/--seed flags,
same build_ppo/Monitor note), plus one addition: --init-from, to warm-
start from an existing checkpoint (most usefully, a trained
hover_stabilize checkpoint) instead of training from random init.

Why this works: WaypointGymEnv's observation_space is deliberately the
same shape as HoverGymEnv's (9 floats — see waypoint_gym_wrapper.py's
module docstring) and the action space is identical (ACTION_DIM=4 for
both tasks, from src/actions/velocity_action.py). So a hover-trained
policy network's input/output layers line up exactly with the waypoint
env, and SB3's PPO.load(path, env=env) can load it directly. What
transfers is "how to hold a position and not move too fast" — which is
most of what waypoint-following needs; what still has to be learned from
that starting point is following a *moving* target and the landing-phase
behavior specifically.

Usage:
    python -m src.training.waypoint_train
    python -m src.training.waypoint_train --gui
    python -m src.training.waypoint_train --timesteps 500000
    python -m src.training.waypoint_train --seed 0
    python -m src.training.waypoint_train --init-from model/model_weights/hover_stabilize_ppo_seed0.zip
    python -m src.training.waypoint_train --init-from model/model_weights/waypoint_nav_ppo.zip   # resume own run

Saves to model/model_weights/waypoint_nav_ppo[_seed{N}].zip (see
src/paths.py) — not the working directory.
"""

import argparse

from stable_baselines3 import PPO

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
        help="Training seed, passed to SB3's PPO. Only used for a from-scratch run "
             "(--init-from not given) — a loaded checkpoint already has its own RNG "
             "state and this is ignored, since re-seeding a warm-started model doesn't "
             "mean the same thing as seeding one from random init."
    )
    parser.add_argument(
        "--init-from", type=str, default=None,
        help="Path to a .zip checkpoint to warm-start from, instead of training from "
             "random init. Most useful pointed at a trained hover_stabilize checkpoint "
             "(e.g. model/model_weights/hover_stabilize_ppo_seed0.zip) — see module "
             "docstring for why the obs/action spaces line up. Also works pointed at a "
             "previous waypoint_nav checkpoint, to continue an interrupted/short run. "
             "PPO hyperparameters (learning_rate, ent_coef, net_arch, etc.) come from "
             "the loaded checkpoint, NOT from config.ppo, when this is set."
    )
    args = parser.parse_args()

    config = ProjectConfig(task=WaypointTaskConfig())
    if args.gui:
        config.sim.gui = True
    if args.timesteps:
        config.ppo.total_timesteps = args.timesteps

    env = WaypointGymEnv(config)

    if args.init_from:
        if args.seed is not None:
            print(f"Note: --seed {args.seed} is ignored when warm-starting via --init-from.")
        model = PPO.load(args.init_from, env=env, device="cpu", tensorboard_log=str(WAYPOINT_TB_LOG_DIR))
        # reset_num_timesteps=False: continues the TensorBoard step count and
        # PPO's internal counters from where the loaded checkpoint left off,
        # rather than restarting at step 0 and overwriting/confusing the
        # existing training curve.
        model.learn(total_timesteps=config.ppo.total_timesteps, reset_num_timesteps=False)
    else:
        # Note: build_ppo() wraps env in Monitor internally — don't double-wrap here.
        model = build_ppo(env, config.ppo, tensorboard_log=str(WAYPOINT_TB_LOG_DIR), seed=args.seed)
        model.learn(total_timesteps=config.ppo.total_timesteps)

    # Standard location: model/model_weights/waypoint_nav_ppo[_seedN].zip
    # (see src/paths.py) — not the working directory.
    save_path = waypoint_model_path(args.seed)
    model.save(str(save_path))
    print(f"\nSaved model to {save_path}")

    env.close()


if __name__ == "__main__":
    main()
