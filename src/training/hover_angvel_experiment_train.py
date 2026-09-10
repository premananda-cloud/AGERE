"""
hover_angvel_experiment_train.py

A SEPARATE, standalone fine-tune to test whether penalizing angular
velocity in the reward reduces the tilt/oscillation seen in the smooth
takeoff/hover/landing demo -- see config.py's angular_velocity_penalty_
weight docstring for the full reasoning.

Deliberately NOT hover_train.py, and deliberately not writing to the
"hover" task in the registry:
    - Checkpoint/model filenames use prefix hover_angvel_exp_ppo_seed*,
      NOT hover_stabilize_ppo* -- checkpoint_manager.py's "hover" TASKS
      entry globs on hover_stabilize_ppo*.zip / hover_champion.zip
      specifically, so this experiment's files are invisible to hover's
      leaderboard/archive/promote commands without any extra effort.
    - model_registry.record_run()/record_eval() calls below use
      task="hover_angvel_experiment", not task="hover" -- so
      `leaderboard hover ...` and `promote hover ...` never see this
      run's eval numbers either. If this experiment succeeds and you
      want it to become the new champion candidate, that's a deliberate
      later step (re-tag, or add a real TASKS entry in
      checkpoint_manager.py), not something that happens by accident.
    - Logs to tb_logs/hover_angvel_experiment/, not tb_logs/hover_logs/.

IMPORTANT -- read before assuming --ent-coef/--gamma/etc do what you
expect: PPO.load() restores hyperparameters (gamma, ent_coef, learning
rate, ...) from the CHECKPOINT FILE ITSELF, not from any config passed
alongside it (see config.py's waypoint_ppo_config() docstring -- this
already bit the project once). Warm-starting from hover_champion.zip
means the loaded model keeps whatever hyperparameters IT was trained
with unless you explicitly override them below, which this script does
ONLY for flags you actually pass -- anything you don't pass is left as
whatever the champion already had, and this script prints those
inherited values so you can see them before training starts.

The reward function itself is now different from the champion's (this
new penalty term). That means this run's ep_rew_mean is NOT comparable
to the champion's ep_rew_mean -- different scale, different formula.
Same lesson this project has already learned about ep_rew_mean in
general: don't judge this experiment by reward curves, judge it by
hover_checkpoint_sweep.py / hover_tilt_diagnostic.py / max-tilt-observed
in sim_transfer_test_demo.py, same as every other checkpoint decision
here.

Usage:
    # Quick check, default penalty weight (0.02, see config.py):
    python -m src.training.hover_angvel_experiment_train \\
        --init-from model/model_weights/hover_champion.zip \\
        --stage disturbance_3x5 --timesteps 300000

    # Sweep the penalty weight itself across a few runs (recommended --
    # this value is an unvalidated guess, not tuned):
    python -m src.training.hover_angvel_experiment_train \\
        --init-from model/model_weights/hover_champion.zip \\
        --stage disturbance_3x5 --timesteps 300000 \\
        --angular-velocity-penalty-weight 0.01 --tag av001

    python -m src.training.hover_angvel_experiment_train \\
        --init-from model/model_weights/hover_champion.zip \\
        --stage disturbance_3x5 --timesteps 300000 \\
        --angular-velocity-penalty-weight 0.05 --tag av005
"""

import argparse
from dataclasses import replace
from pathlib import Path

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.env_util import make_vec_env

from src.config import ProjectConfig, HoverTaskConfig, HOVER_STAGE_PRESETS
from src.paths import MODEL_WEIGHTS_DIR
from src.training.gym_wrapper.hover_gym_wrapper import HoverGymEnv
from src.weight_manager import model_registry as registry

TASK_TAG = "hover_angvel_experiment"  # NOT "hover" -- see module docstring


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--init-from", type=str, required=True,
                         help="Checkpoint to warm-start from, e.g. model/model_weights/hover_champion.zip. "
                              "Required -- this script is for fine-tuning an existing policy, not training "
                              "from scratch (use hover_train.py for that).")
    parser.add_argument("--stage", type=str, default="disturbance_3x5", choices=sorted(HOVER_STAGE_PRESETS.keys()),
                         help="Same HOVER_STAGE_PRESETS hover_train.py/hover_evaluate.py use. Defaults to "
                              "disturbance_3x5 to match what the champion was actually trained/evaluated on.")
    parser.add_argument("--angular-velocity-penalty-weight", type=float, default=None,
                         help="Overrides config.py's default (0.02, itself an unvalidated starting guess) "
                              "if you want to sweep this value across runs.")
    parser.add_argument("--timesteps", type=int, default=300_000,
                         help="This is a QUICK CHECK, not a full training run -- 300k is roughly the scale "
                              "of a single fine-tuning pass on top of an already-good policy, not a from-"
                              "scratch budget.")
    parser.add_argument("--n-envs", type=int, default=4)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--checkpoint-every", type=int, default=50_000)
    parser.add_argument("--tag", type=str, default="exp1",
                         help="Suffix distinguishing this run's files from other angvel experiment runs, "
                              "e.g. --tag av005 when sweeping the penalty weight. Final filename: "
                              "hover_angvel_exp_ppo_seed<seed>_<tag>[.zip | _<N>_steps.zip]")
    # Explicit hyperparameter overrides -- None (default) means "leave whatever
    # the loaded checkpoint already has," NOT "use stable-baselines3's default."
    # See module docstring's PPO.load() warning for why this distinction matters.
    parser.add_argument("--ent-coef", type=float, default=None)
    parser.add_argument("--gamma", type=float, default=None)
    parser.add_argument("--learning-rate", type=float, default=None)
    args = parser.parse_args()

    if not Path(args.init_from).exists():
        parser.error(f"--init-from path does not exist: {args.init_from}")

    # --- Build the task config for this run -------------------------------
    task = HoverTaskConfig()
    task = replace(task, **HOVER_STAGE_PRESETS[args.stage])
    if args.angular_velocity_penalty_weight is not None:
        task = replace(task, angular_velocity_penalty_weight=args.angular_velocity_penalty_weight)
    print(f"angular_velocity_penalty_weight = {task.angular_velocity_penalty_weight} "
          f"({'CLI override' if args.angular_velocity_penalty_weight is not None else 'config.py default'})")

    config = ProjectConfig(task=task)

    # --- Vec env ------------------------------------------------------------
    env = make_vec_env(lambda: HoverGymEnv(config), n_envs=args.n_envs, seed=args.seed)

    # --- Load and warm-start -------------------------------------------------
    model = PPO.load(args.init_from, env=env, device="cpu")

    print("\nHyperparameters inherited from the loaded checkpoint (PPO.load() restores these "
          "from the .zip itself, NOT from any config passed here):")
    print(f"  gamma={model.gamma}  ent_coef={model.ent_coef}  learning_rate={model.learning_rate}")

    overrides = {}
    if args.ent_coef is not None:
        model.ent_coef = args.ent_coef
        overrides["ent_coef"] = args.ent_coef
    if args.gamma is not None:
        model.gamma = args.gamma
        overrides["gamma"] = args.gamma
    if args.learning_rate is not None:
        model.learning_rate = args.learning_rate
        overrides["learning_rate"] = args.learning_rate
    if overrides:
        print(f"Explicit overrides applied on top of the loaded model: {overrides}")
    else:
        print("No explicit hyperparameter overrides passed -- keeping the checkpoint's own values as-is.")

    checkpoint_prefix = f"hover_angvel_exp_ppo_seed{args.seed}_{args.tag}"
    checkpoint_dir = MODEL_WEIGHTS_DIR / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    callback = CheckpointCallback(
        save_freq=max(args.checkpoint_every // args.n_envs, 1),  # save_freq counts PER-ENV steps
        save_path=str(checkpoint_dir),
        name_prefix=checkpoint_prefix,
    )

    tb_log_dir = "tb_logs/hover_angvel_experiment"
    model.tensorboard_log = tb_log_dir
    print(f"\nTraining {args.timesteps} steps, tensorboard log: {tb_log_dir}\n")

    model.learn(
        total_timesteps=args.timesteps,
        callback=callback,
        reset_num_timesteps=False,  # continue the step count from the loaded checkpoint, don't restart at 0
        tb_log_name=checkpoint_prefix,
    )

    final_path = MODEL_WEIGHTS_DIR / f"{checkpoint_prefix}.zip"
    model.save(str(final_path))
    env.close()

    # --- Register the run (task="hover_angvel_experiment", NOT "hover") ----
    h = registry.record_run(
        task=TASK_TAG,
        saved_path=final_path,
        init_from=args.init_from,
        run_timesteps=args.timesteps,
        # The champion's own provenance is UNKNOWN to the registry (no
        # matching "run" record -- confirmed when it was promoted), so a
        # true cumulative step count from original training isn't
        # recoverable. This run's own step count is still accurate and is
        # what matters for comparing across angvel-experiment runs.
        cumulative_timesteps=args.timesteps,
        seed=args.seed,
        task_config=task,
        ppo_config={
            "note": "warm-started; only explicit CLI overrides shown, everything else inherited from --init-from",
            "inherited_gamma": model.gamma,
            "inherited_ent_coef": model.ent_coef,
            "inherited_learning_rate": model.learning_rate,
            "explicit_overrides": overrides,
        },
        disturbance={
            "types": list(task.disturbance_types_active),
            "note": f"stage={args.stage}, angular_velocity_penalty_weight={task.angular_velocity_penalty_weight} "
                    f"-- reward-shaping experiment, disturbance config otherwise matches the base stage preset",
        },
    )

    print(f"\nSaved: {final_path}")
    print(f"Registered under task={TASK_TAG!r}, hash={h[:12]}")
    print("\nNext steps -- do NOT compare ep_rew_mean to the champion's, the reward function itself "
          "changed. Compare actual task metrics instead:")
    print(f"  python -m src.training.evaluate.hover_checkpoint_sweep \\\n"
          f"      --prefix {checkpoint_prefix} --stage {args.stage} --episodes 60 --seed 0")
    print(f"  python -m src.training.evaluate.hover_tilt_diagnostic \\\n"
          f"      --model {final_path} --stage {args.stage} --episodes 90 --seed 0")
    print(f"  python -m src.training.demo.sim_transfer_test_demo --model {final_path}\n"
          f"      (compare Max tilt observed against the current champion's run)")


if __name__ == "__main__":
    main()
