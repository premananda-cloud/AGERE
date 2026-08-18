"""
Evaluate a trained hover/stabilize policy against the staged criteria in
docs/hover-model-plan.md.

Runs the policy deterministically (no exploration noise) over N episodes
with randomized starts, and reports:
  - mean position error at episode end
  - crash rate (out-of-bounds or excessive tilt, NOT counting timeout as a
    crash — reaching the timeout means it survived the whole episode)
  - mean episode reward, for reference against training-log.md entries

Usage:
    python -m src.training.evaluate.hover_evaluate
    python -m src.training.evaluate.hover_evaluate --model model/hover_stabilize/hover_stabilize_ppo_seed0.zip
    python -m src.training.evaluate.hover_evaluate --episodes 20
    python -m src.training.evaluate.hover_evaluate --gui   # watch the eval episodes

Defaults to model/hover_stabilize/hover_stabilize_ppo.zip if --model isn't
given (see src/paths.py).
"""

import argparse
from dataclasses import replace

import numpy as np
from stable_baselines3 import PPO

from src.config import ProjectConfig, HOVER_STAGE_PRESETS
from src.paths import hover_stabilize_model_path
from src.training.gym_wrapper.hover_gym_wrapper import HoverGymEnv
from src.model_registry import record_eval

# Stage 2 criteria, per docs/hover-model-plan.md — keep these two files in
# sync if the plan changes.
STAGE_2_MAX_POSITION_ERROR = 0.3   # meters
STAGE_2_MAX_CRASH_RATE = 0.10      # fraction of episodes


def run_episode(env: HoverGymEnv, model: PPO, seed=None):
    obs, reset_info = env.reset(seed=seed)
    start_position = reset_info["start_position"]
    start_yaw_rad = reset_info["start_yaw_rad"]
    # How far this episode's start was jittered from the target — the
    # candidate explanation for the tail episodes in the 2026-07-31 run.
    jitter_norm = float(np.linalg.norm(start_position - np.asarray(env.task.target_position)))

    total_reward = 0.0
    final_pos_error = None
    is_crash = False
    truncation_reason = None
    pos_error_trace = []  # per-step, so tail episodes can be told apart:
                          # "never converged" vs. "converged then drifted"
    kicked = False
    recovered = None
    recovery_time_steps = None

    terminated = truncated = False
    while not (terminated or truncated):
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        final_pos_error = info["position_error_norm"]
        pos_error_trace.append(final_pos_error)
        if info.get("kicked"):
            kicked = True
            recovered = info.get("recovered")
            recovery_time_steps = info.get("recovery_time_steps")
        if truncated:
            is_crash = info.get("is_crash", False)
            truncation_reason = info.get("truncation_reason")

    return (final_pos_error, is_crash, total_reward, jitter_norm, start_yaw_rad, pos_error_trace,
            truncation_reason, kicked, recovered, recovery_time_steps)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model", type=str, default=None,
        help="Path to a model .zip. Defaults to model/hover_stabilize/hover_stabilize_ppo.zip "
             "(the unseeded default-run save location — see src/paths.py). Pass a full path "
             "to evaluate a specific seeded checkpoint, e.g. "
             "model/hover_stabilize/hover_stabilize_ppo_seed0.zip"
    )
    parser.add_argument("--episodes", type=int, default=20, help="Matches Stage 2's 20-episode spec")
    parser.add_argument("--gui", action="store_true")
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Seed the first reset for a reproducible eval sequence (needed to "
             "compare tail episodes across reruns, or across trained seeds later)."
    )
    parser.add_argument(
        "--tail-threshold", type=float, default=0.2,
        help="Episodes with final pos error above this are flagged as tail "
             "episodes in the summary (default 0.2 m, below the 0.3 m Stage 2 ceiling)."
    )
    parser.add_argument(
        "--stage", type=str, default=None, choices=sorted(HOVER_STAGE_PRESETS.keys()),
        help="Apply a Stage 1 sub-stage's disturbance config (same presets hover_train.py uses, "
             "from config.py's HOVER_STAGE_PRESETS) so evaluation matches how the model was "
             "trained. REQUIRED to see any kicks at all -- without --stage, disturbance_enabled "
             "defaults to False and this is a plain (undisturbed) hover eval regardless of what "
             "the model was actually trained on."
    )
    parser.add_argument(
        "--no-tag", action="store_true",
        help="Skip logging this eval to the model registry (model/model_weights/registry.jsonl). "
             "Default is to always tag, same convention as waypoint_evaluate.py. Use --no-tag for "
             "quick throwaway checks (e.g. a --gui sanity watch) you don't want cluttering the registry."
    )
    args = parser.parse_args()
    model_path = args.model or str(hover_stabilize_model_path())

    config = ProjectConfig()
    if args.gui:
        config.sim.gui = True
    if args.stage:
        config.task = replace(config.task, **HOVER_STAGE_PRESETS[args.stage])
        print(f"Applied stage preset '{args.stage}' for evaluation: {HOVER_STAGE_PRESETS[args.stage]}\n")

    env = HoverGymEnv(config)
    model = PPO.load(model_path, device="cpu")

    position_errors = []
    crashes = []
    rewards = []
    jitter_norms = []
    yaw_jitters = []
    traces = []
    reasons = []
    kicked_flags = []
    recovered_flags = []
    recovery_times = []

    for ep in range(args.episodes):
        # Only the first reset needs an explicit seed — gymnasium's np_random
        # carries forward deterministically from there, so the whole sequence
        # becomes reproducible without reseeding every episode.
        seed = args.seed if ep == 0 else None
        (pos_error, is_crash, total_reward, jitter_norm, start_yaw_rad, trace, reason,
         kicked, recovered, recovery_time) = run_episode(env, model, seed=seed)
        position_errors.append(pos_error)
        crashes.append(is_crash)
        rewards.append(total_reward)
        jitter_norms.append(jitter_norm)
        yaw_jitters.append(abs(start_yaw_rad))
        traces.append(trace)
        reasons.append(reason)
        kicked_flags.append(kicked)
        recovered_flags.append(recovered)
        recovery_times.append(recovery_time)
        crash_note = f" ({reason})" if is_crash else ""
        kick_note = ""
        if kicked:
            if is_crash:
                kick_note = " | kicked, crashed"
            elif recovered:
                kick_note = f" | kicked, recovered in {recovery_time} steps"
            else:
                kick_note = " | kicked, DID NOT recover in budget"
        print(
            f"episode {ep+1:2d}/{args.episodes} | "
            f"final pos error: {pos_error:.3f} m | "
            f"crash: {is_crash}{crash_note} | "
            f"reward: {total_reward:.1f} | "
            f"start jitter: {jitter_norm:.3f} m | "
            f"start yaw jitter: {np.degrees(abs(start_yaw_rad)):.1f} deg"
            f"{kick_note}"
        )

    env.close()

    mean_pos_error = float(np.mean(position_errors))
    crash_rate = float(np.mean(crashes))
    mean_reward = float(np.mean(rewards))

    print("\n" + "=" * 50)
    print(f"Episodes run:          {args.episodes}")
    print(f"Mean final pos error:  {mean_pos_error:.3f} m")
    print(f"Crash rate:            {crash_rate*100:.1f}%")
    print(f"Mean episode reward:   {mean_reward:.1f}")
    print("=" * 50)

    # --- Stage 1 disturbance report (only if any episode was kicked) -----
    # "kicked" requires task.disturbance_enabled to have been True during
    # this eval run's env construction, per hover_gym_wrapper.py's
    # _sample_kick_schedule(). If the model was trained WITH disturbance but
    # evaluated with a plain ProjectConfig() (disturbance_enabled=False by
    # default), this section simply won't appear -- that's a config
    # mismatch to catch by eye (no automatic warning here), not a crash.
    disturbance_metrics = {}
    n_kicked = sum(kicked_flags)
    if n_kicked > 0:
        kicked_crashes = [c for c, k in zip(crashes, kicked_flags) if k]
        kicked_crash_rate = float(np.mean(kicked_crashes))
        recovered_among_survivors = [r for r, k, c in zip(recovered_flags, kicked_flags, crashes) if k and not c]
        recovery_rate = float(np.mean(recovered_among_survivors)) if recovered_among_survivors else float("nan")
        recovery_times_valid = [t for t in recovery_times if t is not None]
        mean_recovery_time = float(np.mean(recovery_times_valid)) if recovery_times_valid else float("nan")

        print(f"\nStage 1 disturbance report ({n_kicked}/{args.episodes} episodes kicked):")
        print(f"  Crash rate among kicked episodes:     {kicked_crash_rate*100:.1f}%")
        print(f"  Recovery rate (of non-crashed kicked): {recovery_rate*100:.1f}%")
        print(f"  Mean recovery time (of recovered):     {mean_recovery_time:.1f} steps "
              f"({mean_recovery_time/30:.2f}s @ 30Hz)" if recovery_times_valid else "  Mean recovery time: n/a (none recovered)")
        mastery = kicked_crash_rate < 0.10 and recovery_rate > 0.90
        print(f"  [{'PASS' if mastery else 'FAIL'}] mastery gate: crash rate <10% AND recovery rate >90%")

        disturbance_metrics = {
            "kicked_crash_rate": kicked_crash_rate,
            "recovery_rate": recovery_rate,
            "mean_recovery_time_steps": mean_recovery_time,
        }

    if not args.no_tag:
        # 2026-08-13: hover_evaluate.py previously did not tag the registry at all --
        # every hover checkpoint's eval history lived only in devlog prose / terminal
        # scrollback. This closes that gap, same convention waypoint_evaluate.py already
        # uses. Metric names here are free-form (registry is task-agnostic as of the
        # 2026-08-13 generalization) -- keep these in sync with checkpoint_manager.py's
        # TASKS["hover"] expectations if either changes.
        h = record_eval(
            task="hover",
            model_path=model_path,
            seed=args.seed,
            episodes=args.episodes,
            metrics={
                "mean_position_error": mean_pos_error,
                "crash_rate": crash_rate,
                "mean_reward": mean_reward,
                **disturbance_metrics,
            },
        )
        print(f"Logged to model registry (hash {h[:12]}...). "
              f"Query with: python -m src.model_registry describe {model_path}")

    print("\nStage 2 criteria (docs/hover-model-plan.md):")
    pos_ok = mean_pos_error < STAGE_2_MAX_POSITION_ERROR
    crash_ok = crash_rate < STAGE_2_MAX_CRASH_RATE
    print(f"  [{'PASS' if pos_ok else 'FAIL'}] mean pos error < {STAGE_2_MAX_POSITION_ERROR} m")
    print(f"  [{'PASS' if crash_ok else 'FAIL'}] crash rate < {STAGE_2_MAX_CRASH_RATE*100:.0f}%")

    if pos_ok and crash_ok:
        print("\n-> Stage 2 (usable/viable baseline) reached.")
    else:
        print("\n-> Stage 2 not yet reached. See docs/hover-model-plan.md for what to try next.")

    # --- Tail diagnosis (Stage 3 prep) ---------------------------------
    # Question this is meant to answer: are high-error episodes explained
    # by a large start-position jitter draw, or is the policy weak in a
    # way that's independent of how far it started from target? This
    # matters before spending compute on multi-seed retraining — a
    # start-condition-driven tail will likely reproduce across all seeds
    # regardless of retraining; a policy-driven tail might not.
    tail_idx = [i for i, e in enumerate(position_errors) if e > args.tail_threshold]
    print(f"\nTail episodes (final pos error > {args.tail_threshold} m): {len(tail_idx)}/{args.episodes}")
    if tail_idx:
        for i in tail_idx:
            trace = np.asarray(traces[i])
            min_error = float(trace.min())
            step_of_min = int(trace.argmin())
            # Last 10% of the episode vs. its best moment — cheap way to tell
            # "never got close" (min_error itself is already high) apart from
            # "got close, then drifted back away before the episode ended".
            tail_window = trace[-max(1, len(trace) // 10):]
            drifted = min_error < args.tail_threshold * 0.6 and float(tail_window.mean()) > min_error * 1.5
            pattern = "converged then drifted" if drifted else "never converged"
            print(
                f"  episode {i+1:2d} | pos error {position_errors[i]:.3f} m | "
                f"reward {rewards[i]:.1f} | start jitter {jitter_norms[i]:.3f} m | "
                f"start yaw jitter {np.degrees(yaw_jitters[i]):.1f} deg | "
                f"best={min_error:.3f} m @ step {step_of_min}/{len(trace)} ({pattern})"
            )
        mean_tail_jitter = float(np.mean([jitter_norms[i] for i in tail_idx]))
        mean_other_jitter = float(np.mean([j for i, j in enumerate(jitter_norms) if i not in tail_idx])) \
            if len(tail_idx) < args.episodes else float("nan")
        mean_tail_yaw = float(np.degrees(np.mean([yaw_jitters[i] for i in tail_idx])))
        mean_other_yaw = float(np.degrees(np.mean([y for i, y in enumerate(yaw_jitters) if i not in tail_idx]))) \
            if len(tail_idx) < args.episodes else float("nan")
        print(f"  mean start jitter (tail episodes):     {mean_tail_jitter:.3f} m")
        print(f"  mean start jitter (non-tail episodes): {mean_other_jitter:.3f} m")
        print(f"  mean start yaw jitter (tail episodes):     {mean_tail_yaw:.1f} deg")
        print(f"  mean start yaw jitter (non-tail episodes): {mean_other_yaw:.1f} deg")

    if len(set(jitter_norms)) > 1 and tail_idx:
        pos_correlation = float(np.corrcoef(jitter_norms, position_errors)[0, 1])
        print(f"\nCorrelation (start jitter vs. final pos error):     {pos_correlation:+.2f}")
    if len(set(yaw_jitters)) > 1 and tail_idx:
        yaw_correlation = float(np.corrcoef(yaw_jitters, position_errors)[0, 1])
        print(f"Correlation (start yaw jitter vs. final pos error): {yaw_correlation:+.2f}")

    def _describe(corr, label):
        if corr > 0.5:
            print(f"  -> Fairly strong: {label} looks like a real driver of the tail.")
        elif corr < 0.2:
            print(f"  -> Weak/no relationship: {label} doesn't explain the tail.")
        else:
            print(f"  -> Ambiguous relationship with {label} alone.")

    if tail_idx and len(set(jitter_norms)) > 1:
        _describe(pos_correlation, "position jitter")
    if tail_idx and len(set(yaw_jitters)) > 1:
        _describe(yaw_correlation, "yaw jitter")

    if tail_idx and len(set(jitter_norms)) > 1 and len(set(yaw_jitters)) > 1:
        if pos_correlation < 0.4 and yaw_correlation < 0.4:
            print(
                "\nNeither start condition strongly predicts the tail. This leans toward "
                "a policy weak spot independent of start draw, rather than 'got an "
                "unusually hard start position.' Check the per-episode 'converged then "
                "drifted' vs 'never converged' tags above: the former points at a late-"
                "episode stability issue (reward/PID interaction, maybe survival_bonus "
                "vs. position_error_weight balance); the latter points at slow/incomplete "
                "convergence within the episode length, which more training timesteps "
                "might fix on its own."
            )

    # --- Crash report ----------------------------------------------------
    # Separate from the tail report above: a crash can happen with a final
    # position error under the tail threshold (episode was truncated by
    # tilt/out-of-bounds partway through, not by running the full episode
    # with a mediocre final value) — so this must not be gated on
    # tail_threshold or it can silently miss the more severe failure mode.
    crash_idx = [i for i, c in enumerate(crashes) if c]
    if crash_idx:
        print(f"\nCrashed episodes: {len(crash_idx)}/{args.episodes}")
        for i in crash_idx:
            print(
                f"  episode {i+1:2d} | reason: {reasons[i]} | final pos error {position_errors[i]:.3f} m | "
                f"reward {rewards[i]:.1f} | start jitter {jitter_norms[i]:.3f} m | "
                f"start yaw jitter {np.degrees(yaw_jitters[i]):.1f} deg"
            )
        print(
            "  Crashes matter independently of the position-error tail — a policy that "
            "rarely-but-genuinely crashes is a different (and more serious) problem than "
            "one that just converges slowly. Worth tracking whether this reproduces on "
            "other seeds/eval runs before assuming it's a one-off."
        )


if __name__ == "__main__":
    main()
