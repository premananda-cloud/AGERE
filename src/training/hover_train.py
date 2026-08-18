"""
Entry point for training the hover/stabilize policy.

AGERE is PyBullet + Gymnasium only — no PX4, no network dependency. See
docs/code-structure.md for how environments/, actions/, and training/
divide responsibilities.

Usage:
    python -m src.training.hover_train
    python -m src.training.hover_train --gui               # watch training live
    python -m src.training.hover_train --timesteps 500000  # override config
    python -m src.training.hover_train --seed 0            # for Stage 3's multi-seed requirement
    python -m src.training.hover_train --seed 0 --checkpoint-every 50000

    # Stage 1 disturbance curriculum (2026-08-16), warm-started from the
    # Stage 0 champion, per docs/planning/hover-robustness-curriculum-plan.md:
    python -m src.training.hover_train --seed 0 --stage 1a \\
        --init-from model/model_weights/hover_champion.zip \\
        --timesteps 300000 --checkpoint-every 50000

Saves to model/model_weights/hover_stabilize_ppo[_seed{N}][_{tag}].zip (see
src/paths.py's flat-directory convention) — not the working directory.
Intermediate checkpoints (if --checkpoint-every is set) save to
model/model_weights/checkpoints/, matching waypoint_train.py's convention —
added 2026-08-15, same rationale as waypoint_train.py's --checkpoint-every
(2026-08-09 devlog): "final save only" means a regression mid-run is
invisible until the whole run is over. Every save (checkpoint and final)
is logged to the model registry.
"""

import argparse
from dataclasses import replace

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback

from src.config import ProjectConfig, HOVER_STAGE_PRESETS
from src.paths import hover_stabilize_model_path, HOVER_STABILIZE_TB_LOG_DIR, MODEL_WEIGHTS_DIR
from src.training.gym_wrapper.hover_gym_wrapper import HoverGymEnv
from src.policies.ppo_policy import build_ppo
from src.model_registry import record_run

# Stage 1 sub-stage presets -- see config.py's HOVER_STAGE_PRESETS docstring.
# Kept as a module-level alias here so the rest of this file (STAGE_PRESETS[...])
# doesn't need to change; the actual dict is defined once, in config.py.
STAGE_PRESETS = HOVER_STAGE_PRESETS


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
    parser.add_argument(
        "--checkpoint-every", type=int, default=None,
        help="Save an intermediate checkpoint every N timesteps to model/model_weights/checkpoints/, "
             "matching waypoint_train.py's convention. Strongly recommended for any run -- per the "
             "2026-08-09 waypoint finding, a regression can be invisible until the whole run finishes "
             "if only the final save is ever evaluated."
    )
    parser.add_argument(
        "--init-from", type=str, default=None,
        help="Warm-start from an existing checkpoint (e.g. model/model_weights/hover_champion.zip) "
             "instead of building a fresh policy. Added 2026-08-16 for the Stage 1 disturbance "
             "curriculum, where each sub-stage continues training from the PREVIOUS sub-stage's "
             "champion rather than starting over -- without this, sub-stage progression can't work "
             "as designed (mastery from 1a wouldn't carry into 1b). NOTE: PPO.load() restores "
             "hyperparameters (gamma, ent_coef, etc.) from the checkpoint itself, not from this run's "
             "PPOConfig -- see waypoint_ppo_config()'s docstring in config.py for why this matters if "
             "you're also trying to change hyperparameters on a warm-started run."
    )
    parser.add_argument(
        "--stage", type=str, default=None, choices=sorted(STAGE_PRESETS.keys()),
        help="Apply a Stage 1 sub-stage preset (disturbance type/magnitude/recovery config) from "
             "docs/planning/hover-robustness-curriculum-plan.md. Also used as the default --tag if "
             "--tag isn't given separately."
    )
    parser.add_argument(
        "--tag", type=str, default=None,
        help="Suffix for the save path (see src/paths.py's hover_stabilize_model_path tag param), "
             "e.g. --tag 1a -> hover_stabilize_ppo_seed0_1a.zip. Defaults to --stage's value if "
             "--stage is given and --tag isn't. Prevents sub-stage runs from clobbering each other's "
             "canonical save path."
    )
    args = parser.parse_args()

    config = ProjectConfig()
    if args.gui:
        config.sim.gui = True
    if args.timesteps:
        config.ppo.total_timesteps = args.timesteps
    if args.stage:
        config.task = replace(config.task, **STAGE_PRESETS[args.stage])
        print(f"Applied stage preset '{args.stage}': {STAGE_PRESETS[args.stage]}")

    tag = args.tag or args.stage

    env = HoverGymEnv(config)

    if args.init_from:
        # Warm-start: load the existing policy, attach it to this run's env.
        # Note (see --init-from's help text): hyperparameters come from the
        # checkpoint file itself via PPO.load(), NOT from config.ppo here --
        # if you need different hyperparameters on a warm-started run, set
        # them explicitly on `model` after load, same pattern
        # waypoint_train.py already established for its gamma/ent_coef
        # override (see config.py's waypoint_ppo_config() docstring).
        model = PPO.load(args.init_from, device="cpu")
        model.set_env(env)
        if args.seed is not None:
            model.set_random_seed(args.seed)
    else:
        # Note: build_ppo() wraps env in Monitor internally — don't double-wrap here.
        model = build_ppo(env, config.ppo, tensorboard_log=str(HOVER_STABILIZE_TB_LOG_DIR), seed=args.seed)

    callback = None
    if args.checkpoint_every:
        name_prefix = f"hover_stabilize_ppo_seed{args.seed}" if args.seed is not None else "hover_stabilize_ppo"
        if tag:
            name_prefix = f"{name_prefix}_{tag}"
        checkpoint_dir = MODEL_WEIGHTS_DIR / "checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        callback = CheckpointCallback(
            save_freq=args.checkpoint_every,
            save_path=str(checkpoint_dir),
            name_prefix=name_prefix,
        )

    model.learn(total_timesteps=config.ppo.total_timesteps, callback=callback)

    # Standard location: model/model_weights/hover_stabilize_ppo[_seedN][_tag].zip
    # (see src/paths.py's flat-directory convention, tag added 2026-08-16) —
    # not the working directory. The tag keeps curriculum sub-stages from
    # clobbering each other's canonical save path.
    save_path = hover_stabilize_model_path(args.seed, tag=tag)
    model.save(str(save_path))
    print(f"\nSaved model to {save_path}")

    disturbance_meta = None
    if args.stage:
        disturbance_meta = {
            "stage": args.stage,
            "config": STAGE_PRESETS[args.stage],
        }

    h = record_run(
        task="hover",
        saved_path=save_path,
        init_from=args.init_from,
        run_timesteps=config.ppo.total_timesteps,
        # cumulative_timesteps is wrong for a warm-started run if reported as
        # just this run's timesteps -- but computing the TRUE cumulative
        # total would require reading the parent's own registry record and
        # summing, which record_run() doesn't currently do automatically.
        # Flagging rather than silently mislabeling: for a warm-started run,
        # treat this field as "this run's timesteps only" until that's fixed.
        cumulative_timesteps=config.ppo.total_timesteps,
        seed=args.seed,
        task_config=config.task,
        ppo_config=config.ppo,
        disturbance=disturbance_meta,
    )
    print(f"Logged to model registry (hash {h[:12]}...). "
          f"Query with: python -m src.model_registry describe {save_path}")
    if args.init_from:
        print(f"NOTE: cumulative_timesteps logged as this run's {config.ppo.total_timesteps} steps only, "
              f"NOT the true total including {args.init_from}'s prior training -- see record_run() call "
              f"above for why. Check the parent's own registry record if the true cumulative matters.")

    env.close()


if __name__ == "__main__":
    main()
