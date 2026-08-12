"""
Entry point for training the precision takeoff -> hover -> land policy.

Mirrors waypoint_train.py's structure (--gui/--timesteps/--seed/--init-from/
--checkpoint-every flags, model registry integration, timestamped
archiving). Most useful pointed at a trained hover_stabilize checkpoint,
same reasoning as waypoint_nav's warm-start: PrecisionFlightGymEnv's
observation/action spaces match HoverGymEnv's exactly (see
precision_flight_gym_wrapper.py's module docstring).

PATHS NOTE (2026-08-11): hover_train.py/waypoint_train.py both source their
save paths from src/paths.py. That file wasn't available while writing
this script, so the path convention is defined locally below instead of
guessing paths.py's internals. If you want this folded into src/paths.py
to match the established pattern (precision_flight_model_path(),
PRECISION_FLIGHT_TB_LOG_DIR), paste that file and it can be done properly
in one pass -- this works correctly as-is, it just doesn't match the
existing file's home.

Usage:
    python -m src.training.precision_flight_train
    python -m src.training.precision_flight_train --gui
    python -m src.training.precision_flight_train --init-from model/model_weights/hover_stabilize_ppo_seed0.zip --timesteps 300000 --seed 0
    python -m src.training.precision_flight_train --init-from model/model_weights/precision_flight_ppo_seed0.zip --timesteps 300000 --checkpoint-every 50000
"""

import argparse
import shutil
from datetime import datetime
from pathlib import Path

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback

from src.config import ProjectConfig, PrecisionFlightTaskConfig
from src.training.gym_wrapper.precision_flight_gym_wrapper import PrecisionFlightGymEnv
from src.policies.ppo_policy import build_ppo
from src.model_registry import record_run

# See module docstring's PATHS NOTE.
_MODEL_WEIGHTS_DIR = Path("model/model_weights")
_TB_LOG_DIR = Path("tb_logs/precision_flight_logs")


def precision_flight_model_path(seed: int | None = None) -> Path:
    suffix = f"_seed{seed}" if seed is not None else ""
    return _MODEL_WEIGHTS_DIR / f"precision_flight_ppo{suffix}.zip"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gui", action="store_true", help="Render PyBullet GUI during training")
    parser.add_argument("--timesteps", type=int, default=None, help="Override total_timesteps from config")
    parser.add_argument(
        "--checkpoint-every", type=int, default=None,
        help="Save an intermediate checkpoint every N timesteps, to model/model_weights/checkpoints/. "
             "Same rationale as waypoint_train.py's flag of the same name -- recommended for any run "
             "over ~150k steps, given how easily a long run's final save can turn out worse than an "
             "intermediate one (see the waypoint task's whole 2026-08-09 history)."
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Training seed. Ignored for training when warm-starting via --init-from (still used for "
             "the save filename) -- same convention as waypoint_train.py."
    )
    parser.add_argument(
        "--init-from", type=str, default=None,
        help="Path to a .zip checkpoint to warm-start from. Most useful pointed at a trained "
             "hover_stabilize checkpoint (e.g. model/model_weights/hover_stabilize_ppo_seed0.zip)."
    )
    args = parser.parse_args()

    config = ProjectConfig(task=PrecisionFlightTaskConfig())
    if args.gui:
        config.sim.gui = True
    if args.timesteps:
        config.ppo.total_timesteps = args.timesteps

    env = PrecisionFlightGymEnv(config)

    callback = None
    if args.checkpoint_every:
        checkpoint_dir = precision_flight_model_path(args.seed).parent / "checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        name_prefix = precision_flight_model_path(args.seed).stem
        callback = CheckpointCallback(
            save_freq=args.checkpoint_every,
            save_path=str(checkpoint_dir),
            name_prefix=name_prefix,
        )
        print(f"Checkpointing every {args.checkpoint_every} steps to {checkpoint_dir}/{name_prefix}_<step>_steps.zip")

    if args.init_from:
        if args.seed is not None:
            print(f"Note: --seed {args.seed} is ignored for training when warm-starting via --init-from "
                  f"(still used for the save filename).")
        model = PPO.load(args.init_from, env=env, device="cpu", tensorboard_log=str(_TB_LOG_DIR))
        model.learn(total_timesteps=config.ppo.total_timesteps, reset_num_timesteps=False, callback=callback)
    else:
        model = build_ppo(env, config.ppo, tensorboard_log=str(_TB_LOG_DIR), seed=args.seed)
        model.learn(total_timesteps=config.ppo.total_timesteps, callback=callback)

    save_path = precision_flight_model_path(args.seed)
    model.save(str(save_path))
    print(f"\nSaved model to {save_path}")

    run_hash = record_run(
        saved_path=save_path,
        init_from=args.init_from,
        run_timesteps=config.ppo.total_timesteps,
        cumulative_timesteps=model.num_timesteps,
        seed=args.seed,
        task_config=config.task,
        ppo_config=config.ppo,
    )
    print(f"Registered in model registry: hash {run_hash[:12]}... "
          f"(cumulative_timesteps={model.num_timesteps})")

    history_dir = save_path.parent / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    run_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    history_path = history_dir / f"{save_path.stem}_{run_tag}{save_path.suffix}"
    shutil.copy(str(save_path), str(history_path))
    print(f"Archived a timestamped copy to {history_path}")

    env.close()


if __name__ == "__main__":
    main()
