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

    # Parallel environments (2026-08-25): PyBullet stepping in a single
    # process is the actual bottleneck for this workload (tiny [64,64] MLP
    # -- GPU wouldn't help, see docs decision note), not GPU compute.
    # --n-envs spins up N PyBullet instances in separate processes via
    # SB3's SubprocVecEnv, each collecting rollout data in parallel:
    python -m src.training.hover_train --seed 0 --stage disturbance_3x5 \\
        --init-from model/model_weights/hover_champion.zip \\
        --timesteps 500000 --checkpoint-every 50000 --n-envs 6

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
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import SubprocVecEnv

from src.config import ProjectConfig, HOVER_STAGE_PRESETS
from src.paths import hover_stabilize_model_path, HOVER_STABILIZE_TB_LOG_DIR, MODEL_WEIGHTS_DIR
from src.training.gym_wrapper.hover_gym_wrapper import HoverGymEnv
from src.policies.ppo_policy import build_ppo
from src.model_registry import record_run

# Stage 1 sub-stage presets -- see config.py's HOVER_STAGE_PRESETS docstring.
# Kept as a module-level alias here so the rest of this file (STAGE_PRESETS[...])
# doesn't need to change; the actual dict is defined once, in config.py.
STAGE_PRESETS = HOVER_STAGE_PRESETS


def make_hover_env(config: ProjectConfig, seed: int | None, rank: int):
    """Return a zero-arg thunk that builds one Monitor-wrapped HoverGymEnv.

    Needed (rather than just passing an env instance) because
    SubprocVecEnv spawns each sub-environment in its own process and needs
    a picklable callable per env, not a shared object -- `config` (a plain
    dataclass) is picklable, so the closure over it works fine under the
    default fork start method on Linux.

    Each sub-env gets its own PyBullet client (DroneSim.__init__ calls
    HoverAviary(...), which opens its own p.connect()) once it's actually
    constructed inside its subprocess -- nothing here shares simulation
    state across ranks. `rank` offsets the seed per sub-env so parallel
    envs don't all sample identical episode start conditions.
    """

    def _init():
        env = HoverGymEnv(config)
        env = Monitor(env)
        if seed is not None:
            env.reset(seed=seed + rank)
        return env

    return _init


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
        help="Save an intermediate checkpoint every N *total* environment timesteps (summed across "
             "all --n-envs parallel envs, not per-env) to model/model_weights/checkpoints/, matching "
             "waypoint_train.py's convention. Strongly recommended for any run -- per the 2026-08-09 "
             "waypoint finding, a regression can be invisible until the whole run finishes if only "
             "the final save is ever evaluated."
    )
    parser.add_argument(
        "--n-envs", type=int, default=1,
        help="Number of parallel PyBullet environments (SB3 SubprocVecEnv), each in its own "
             "process. This is the actual speedup lever for this workload -- PyBullet stepping in "
             "a single process is the bottleneck, not GPU compute, for a network this small (see "
             "ppo_policy.py's device='cpu' and the 2026-08-25 decision note). Pick a value below "
             "your machine's core count (leave 1-2 cores free for the main process + OS); there's "
             "no benefit past your core count since PyBullet stepping is CPU-bound. Default 1 "
             "preserves the original single-process behavior exactly. Incompatible with --gui "
             "(each sub-env would try to open its own PyBullet window) -- --gui forces this to 1."
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

    if args.gui and args.n_envs > 1:
        print(f"--gui requested with --n-envs {args.n_envs}: forcing --n-envs to 1 "
              f"(each parallel sub-env would otherwise try to open its own PyBullet window).")
        args.n_envs = 1

    config = ProjectConfig()
    if args.gui:
        config.sim.gui = True
    if args.timesteps:
        config.ppo.total_timesteps = args.timesteps
    if args.stage:
        config.task = replace(config.task, **STAGE_PRESETS[args.stage])
        print(f"Applied stage preset '{args.stage}': {STAGE_PRESETS[args.stage]}")

    tag = args.tag or args.stage

    if args.n_envs > 1:
        print(f"Building {args.n_envs} parallel PyBullet environments (SubprocVecEnv)...")
        env = SubprocVecEnv([make_hover_env(config, args.seed, rank) for rank in range(args.n_envs)])
    else:
        env = HoverGymEnv(config)

    if args.init_from:
        # Warm-start: load the existing policy, attach it to this run's env.
        # Note (see --init-from's help text): hyperparameters come from the
        # checkpoint file itself via PPO.load(), NOT from config.ppo here --
        # if you need different hyperparameters on a warm-started run, set
        # them explicitly on `model` after load, same pattern
        # waypoint_train.py already established for its gamma/ent_coef
        # override (see config.py's waypoint_ppo_config() docstring).
        # set_env() auto-wraps a raw (non-Vec) env in a DummyVecEnv+Monitor
        # if needed, and leaves an already-vectorized SubprocVecEnv as-is --
        # correct either way, same as build_ppo()'s explicit check below.
        model = PPO.load(args.init_from, device="cpu")
        model.set_env(env)
        if args.seed is not None:
            model.set_random_seed(args.seed)
    else:
        # Note: build_ppo() wraps env in Monitor internally for the single-env
        # case only -- see its VecEnv check -- don't double-wrap here.
        model = build_ppo(env, config.ppo, tensorboard_log=str(HOVER_STABILIZE_TB_LOG_DIR), seed=args.seed)

    callback = None
    if args.checkpoint_every:
        name_prefix = f"hover_stabilize_ppo_seed{args.seed}" if args.seed is not None else "hover_stabilize_ppo"
        if tag:
            name_prefix = f"{name_prefix}_{tag}"
        checkpoint_dir = MODEL_WEIGHTS_DIR / "checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        # SB3's CheckpointCallback counts one _on_step() call per VECTORIZED
        # step, i.e. once per args.n_envs environment-steps collected, not
        # once per single-env step. Dividing here keeps --checkpoint-every's
        # meaning ("every N total env timesteps") identical across n_envs
        # values -- without this, checkpoints at n_envs=6 would land 6x less
        # often than the flag says, silently.
        save_freq = max(args.checkpoint_every // args.n_envs, 1)
        callback = CheckpointCallback(
            save_freq=save_freq,
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
