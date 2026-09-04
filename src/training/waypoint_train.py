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

IMPORTANT — hyperparameters on a warm-started run (2026-08-08):
PPO.load() restores hyperparameters (gamma, ent_coef, learning_rate, etc.)
from the checkpoint file itself, NOT from config.ppo. That means
config.waypoint_ppo_config()'s gamma/ent_coef values (tuned specifically
to fix the entropy-runaway problem found in tb_logs analysis — see
config.py's docstring on that function) would silently have NO EFFECT on
an --init-from run unless explicitly reapplied to the loaded model after
PPO.load(). This script now does that explicitly (see the "Note:
overriding" print below) — do not remove that step, or config changes to
waypoint_ppo_config() will look like they did nothing on the next run.

Usage:
    python -m src.training.waypoint_train
    python -m src.training.waypoint_train --gui
    python -m src.training.waypoint_train --timesteps 500000
    python -m src.training.waypoint_train --seed 0
    python -m src.training.waypoint_train --init-from model/model_weights/hover_stabilize_ppo_seed0.zip
    python -m src.training.waypoint_train --init-from model/model_weights/waypoint_nav_ppo.zip   # resume own run

Saves to model/model_weights/waypoint_nav_ppo[_seed{N}].zip (see
src/paths.py) — not the working directory. Also archives a timestamped
copy under model/model_weights/history/ every run (see "Archiving" below)
so repeated/rerun/interrupted attempts against the same --seed can't
silently overwrite a previous run's result before it's been evaluated —
this happened 2026-08-06/07 (three separate runs all wrote to the same
waypoint_nav_ppo_seed0.zip; which run's weights ended up on disk could
only be reconstructed after the fact by cross-referencing tb_logs
wall-clock timestamps against the file's mtime).

IMPORTANT — ep_rew_mean is not a reliable proxy for waypoints-reached
past a point (2026-08-09): two separate 300k-step continuations from the
same 802,816-step checkpoint (one lowering velocity_penalty_weight, one
reverting it back) BOTH improved ep_rew_mean substantially (-247.6 ->
-181 to -202) while waypoints-reached on a fixed eval seed got WORSE in
both cases (3.00/5 -> 1.35-1.75/5). The dense per-step shaping reward
appears optimizable somewhat independently of the sparse, binary
waypoint-reach event past a certain point — training reward going up is
no longer sufficient evidence that the actual task is improving. This is
why --checkpoint-every exists now (see below): without periodic saves, a
run only gives you a start point and an end point, and you can't tell
whether/where along the way performance on the real metric peaked before
the shaped reward kept climbing past it.
"""

import argparse
import shutil
from datetime import datetime
from pathlib import Path

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback

from src.config import ProjectConfig, WaypointTaskConfig, waypoint_ppo_config
from src.paths import waypoint_model_path, WAYPOINT_TB_LOG_DIR
from src.training.gym_wrapper.waypoint_gym_wrapper import WaypointGymEnv
from src.policies.ppo_policy import build_ppo
from src.weight_manager.model_registry import record_run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gui", action="store_true", help="Render PyBullet GUI during training")
    parser.add_argument("--timesteps", type=int, default=None, help="Override total_timesteps from config")
    parser.add_argument(
        "--checkpoint-every", type=int, default=None,
        help="Save an intermediate checkpoint every N timesteps during this run, to "
             "model/model_weights/checkpoints/<name>_<step>_steps.zip. Added 2026-08-09 "
             "after finding that ep_rew_mean can keep climbing for hundreds of k of "
             "steps past the point where eval waypoints-reached peaks and starts "
             "declining (see module docstring's IMPORTANT note) — without this, a long "
             "run only gives you a start point and an end point, with no way to check "
             "where in between the real task metric was actually best. Recommend "
             "something like --checkpoint-every 50000 for any run over ~150k steps, "
             "then eval each saved checkpoint rather than trusting the final one by "
             "default."
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Training seed, passed to SB3's PPO. Only used for a from-scratch run "
             "(--init-from not given) — a loaded checkpoint already has its own RNG "
             "state and this is ignored for training purposes, since re-seeding a "
             "warm-started model doesn't mean the same thing as seeding one from "
             "random init. Still used for the save filename either way (see "
             "src/paths.py) so repeated --init-from runs against the same nominal "
             "seed land in the same base filename — see 'Archiving' above for why "
             "that no longer means losing earlier results."
    )
    parser.add_argument(
        "--init-from", type=str, default=None,
        help="Path to a .zip checkpoint to warm-start from, instead of training from "
             "random init. Most useful pointed at a trained hover_stabilize checkpoint "
             "(e.g. model/model_weights/hover_stabilize_ppo_seed0.zip) — see module "
             "docstring for why the obs/action spaces line up. Also works pointed at a "
             "previous waypoint_nav checkpoint, to continue an interrupted/short run. "
             "PPO hyperparameters (learning_rate, ent_coef, net_arch, etc.) come from "
             "the loaded checkpoint by default — EXCEPT gamma and ent_coef, which this "
             "script now explicitly overrides from config.waypoint_ppo_config() after "
             "load (see module docstring's IMPORTANT note)."
    )
    args = parser.parse_args()

    config = ProjectConfig(task=WaypointTaskConfig(), ppo=waypoint_ppo_config())
    if args.gui:
        config.sim.gui = True
    if args.timesteps:
        config.ppo.total_timesteps = args.timesteps

    env = WaypointGymEnv(config)

    callback = None
    if args.checkpoint_every:
        checkpoint_dir = Path(waypoint_model_path(args.seed)).parent / "checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        name_prefix = Path(waypoint_model_path(args.seed)).stem
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
        model = PPO.load(args.init_from, env=env, device="cpu", tensorboard_log=str(WAYPOINT_TB_LOG_DIR))

        # See module docstring's IMPORTANT note: PPO.load() restores the
        # checkpoint's own gamma/ent_coef, which silently defeats
        # config.waypoint_ppo_config() unless we override here explicitly.
        old_gamma, old_ent_coef = model.gamma, model.ent_coef
        model.gamma = config.ppo.gamma
        model.ent_coef = config.ppo.ent_coef
        print(
            f"Overriding warm-started model's hyperparameters: "
            f"gamma {old_gamma} -> {model.gamma}, ent_coef {old_ent_coef} -> {model.ent_coef} "
            f"(from config.waypoint_ppo_config(), not the loaded checkpoint's own values)."
        )

        # reset_num_timesteps=False: continues the TensorBoard step count and
        # PPO's internal counters from where the loaded checkpoint left off,
        # rather than restarting at step 0 and overwriting/confusing the
        # existing training curve.
        model.learn(total_timesteps=config.ppo.total_timesteps, reset_num_timesteps=False, callback=callback)
    else:
        # Note: build_ppo() wraps env in Monitor internally — don't double-wrap here.
        model = build_ppo(env, config.ppo, tensorboard_log=str(WAYPOINT_TB_LOG_DIR), seed=args.seed)
        model.learn(total_timesteps=config.ppo.total_timesteps, callback=callback)

    # Standard location: model/model_weights/waypoint_nav_ppo[_seedN].zip
    # (see src/paths.py) — not the working directory.
    save_path = Path(waypoint_model_path(args.seed))
    model.save(str(save_path))
    print(f"\nSaved model to {save_path}")

    # Registry: log this file's identity (by content hash, not path -- the
    # path above is a mutable pointer that the NEXT run will overwrite) along
    # with what produced it. This is what makes "which checkpoint got 3.00/5"
    # a lookup instead of a forensic reconstruction from devlog prose and file
    # mtimes (see 2026-08-09 incident). Tag evals against this same hash via
    # waypoint_evaluate.py to close the loop.
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

    # Archiving: always keep a timestamped copy alongside the standard
    # save path, so a rerun against the same --seed (intentional restart,
    # or an interrupted attempt run again) can never silently destroy a
    # previous run's result before anyone's looked at it. See module
    # docstring for the incident this addresses. Cheap (a few MB per run)
    # relative to the cost of losing an unevaluated checkpoint again.
    history_dir = save_path.parent / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    run_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    history_path = history_dir / f"{save_path.stem}_{run_tag}{save_path.suffix}"
    shutil.copy(str(save_path), str(history_path))
    print(f"Archived a timestamped copy to {history_path}")

    env.close()


if __name__ == "__main__":
    main()
