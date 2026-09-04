"""
Evaluate a trained hover/stabilize policy against the staged criteria in
docs/hover-model-plan.md.

Runs the policy deterministically (no exploration noise) over N episodes
with randomized starts, and reports:
  - mean position error at episode end
  - crash rate (out-of-bounds or excessive tilt, NOT counting timeout as a
    crash — reaching the timeout means it survived the whole episode)
  - mean episode reward, for reference against training-log.md entries
  - IF the model/config were trained with disturbance (--stage flag): a
    per-type, per-level breakdown (crash rate, recovery rate, recovery
    time for kick/torque; steady-state error for wind), per the 3-type/
    5-level design in docs/hover-disturbance-3x5-design.md. This replaced
    the older single-kick-type "Stage 1 disturbance report" section —
    see that doc for why (Stage 1a's narrow single-level preset produced
    a null result with no way to see WHICH magnitude was too weak).

Usage:
    python -m src.training.evaluate.hover_evaluate
    python -m src.training.evaluate.hover_evaluate --model model/hover_stabilize/hover_stabilize_ppo_seed0.zip
    python -m src.training.evaluate.hover_evaluate --episodes 20
    python -m src.training.evaluate.hover_evaluate --gui   # watch the eval episodes

    # Evaluating a model trained with the 3x5 disturbance design --
    # REQUIRED --stage flag, same reason as before: without it,
    # disturbance_enabled defaults to False and you silently get a plain
    # undisturbed eval regardless of what the model was trained on.
    # More episodes than the Stage-2 default of 20 are recommended here:
    # with 3 types x 5 levels = 15 buckets, 20 episodes averages under
    # 1.5 samples/bucket. 90+ gives ~6/bucket, enough to not be pure noise.
    python -m src.training.evaluate.hover_evaluate \\
        --model model/model_weights/hover_stabilize_ppo_seed0_disturbance_3x5.zip \\
        --stage disturbance_3x5 --episodes 90

Defaults to model/hover_stabilize/hover_stabilize_ppo.zip if --model isn't
given (see src/paths.py).
"""

import argparse
from collections import defaultdict
from dataclasses import replace

import numpy as np
from stable_baselines3 import PPO

from src.config import ProjectConfig, HOVER_STAGE_PRESETS, DISTURBANCE_TYPES, DISTURBANCE_LEVELS
from src.paths import hover_stabilize_model_path
from src.training.gym_wrapper.hover_gym_wrapper import HoverGymEnv
from src.weight_manager.model_registry import record_eval

# Stage 2 criteria, per docs/hover-model-plan.md — keep these two files in
# sync if the plan changes.
STAGE_2_MAX_POSITION_ERROR = 0.3   # meters
STAGE_2_MAX_CRASH_RATE = 0.10      # fraction of episodes

# Mastery gate, per docs/hover-robustness-curriculum-plan.md — same bar
# originally defined for Stage 1a, now applied per disturbance type.
MASTERY_MAX_CRASH_RATE = 0.10
MASTERY_MIN_RECOVERY_RATE = 0.90

# Below this episode count, the per-type/per-level breakdown is too thin
# to mean much (3 types x 5 levels = 15 buckets) — a heads-up, not a hard
# stop, since a quick sanity run at 20 episodes is still a legitimate use.
RECOMMENDED_MIN_EPISODES_FOR_3X5 = 45  # ~3 samples/bucket at the low end


def run_episode(env: HoverGymEnv, model: PPO, seed=None) -> dict:
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
    tilt_trace = []  # per-step max(|roll|, |pitch|) -- obs[6]/obs[7] are
                      # already roll/pitch (see HoverGymEnv._obs_from_state),
                      # so this needs no gym-wrapper changes. Added for the
                      # tilt-criterion diagnostic (2026-08-25): checks whether
                      # "crash" (tilt truncation, zero hold-time) episodes are
                      # momentary spikes that would have self-corrected, vs.
                      # genuine sustained loss of control -- see
                      # hover_tilt_diagnostic.py.

    disturbance_fired = False
    disturbance_type = None
    disturbance_level = None
    disturbance_magnitude = None
    recovered = None
    recovery_time_steps = None
    wind_steady_state_error_mean = None

    terminated = truncated = False
    while not (terminated or truncated):
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        final_pos_error = info["position_error_norm"]
        pos_error_trace.append(final_pos_error)
        tilt_trace.append(float(max(abs(obs[6]), abs(obs[7]))))  # obs[6]=roll, obs[7]=pitch (radians)
        if info.get("disturbance_fired"):
            disturbance_fired = True
            disturbance_type = info.get("disturbance_type")
            disturbance_level = info.get("disturbance_level")
            disturbance_magnitude = info.get("disturbance_magnitude")
            recovered = info.get("recovered")
            recovery_time_steps = info.get("recovery_time_steps")
            if "wind_steady_state_error_mean" in info:
                wind_steady_state_error_mean = info["wind_steady_state_error_mean"]
        if truncated:
            is_crash = info.get("is_crash", False)
            truncation_reason = info.get("truncation_reason")

    return {
        "final_pos_error": final_pos_error,
        "is_crash": is_crash,
        "total_reward": total_reward,
        "jitter_norm": jitter_norm,
        "start_yaw_rad": start_yaw_rad,
        "pos_error_trace": pos_error_trace,
        "tilt_trace": tilt_trace,
        "truncation_reason": truncation_reason,
        "disturbance_fired": disturbance_fired,
        "disturbance_type": disturbance_type,
        "disturbance_level": disturbance_level,
        "disturbance_magnitude": disturbance_magnitude,
        "recovered": recovered,
        "recovery_time_steps": recovery_time_steps,
        "wind_steady_state_error_mean": wind_steady_state_error_mean,
    }


def _disturbance_episode_note(ep: dict) -> str:
    if not ep["disturbance_fired"]:
        return ""
    type_cfg = DISTURBANCE_TYPES[ep["disturbance_type"]]
    label = f"{ep['disturbance_type']} L{ep['disturbance_level']} ({ep['disturbance_magnitude']:.3f}{type_cfg.unit})"
    if ep["is_crash"]:
        return f" | {label}, crashed"
    if ep["disturbance_type"] == "wind" and ep["wind_steady_state_error_mean"] is not None:
        wind_note = f", steady-state err {ep['wind_steady_state_error_mean']:.3f}m"
    else:
        wind_note = ""
    if ep["recovered"]:
        return f" | {label}{wind_note}, recovered in {ep['recovery_time_steps']} steps"
    return f" | {label}{wind_note}, DID NOT recover in budget"


def _print_disturbance_report(episodes: list, n_total_episodes: int) -> dict:
    """Per-type, per-level breakdown. Returns a flat metrics dict suitable
    for record_eval() — keys prefixed by type, e.g. "kick_crash_rate".

    Design note: a bucket (type, level) can legitimately have zero samples
    at low --episodes counts, since type+level are each sampled uniformly
    per episode (1/3 * 1/5 = 1/15 chance of any specific bucket per
    episode). Buckets with zero samples are reported as "n/a", not
    silently skipped — an empty bucket is itself informative (means this
    run can't say anything about that magnitude yet).
    """
    fired = [ep for ep in episodes if ep["disturbance_fired"]]
    if not fired:
        return {}

    print(f"\nDisturbance report ({len(fired)}/{n_total_episodes} episodes had an event fire):")
    if n_total_episodes < RECOMMENDED_MIN_EPISODES_FOR_3X5:
        print(
            f"  NOTE: {n_total_episodes} episodes across 3 types x {DISTURBANCE_LEVELS} levels = "
            f"15 buckets averages under {n_total_episodes/15:.1f} samples/bucket. Per-level numbers "
            f"below are directional at this count, not statistically solid -- consider "
            f"--episodes {RECOMMENDED_MIN_EPISODES_FOR_3X5}+ for a trustworthy breakdown."
        )

    by_type = defaultdict(list)
    for ep in fired:
        by_type[ep["disturbance_type"]].append(ep)

    metrics = {}
    for type_name in DISTURBANCE_TYPES:
        type_eps = by_type.get(type_name, [])
        print(f"\n  --- {type_name} ({len(type_eps)}/{len(fired)} of fired episodes) ---")
        if not type_eps:
            print("    n/a — never sampled this run")
            continue

        crash_rate = float(np.mean([ep["is_crash"] for ep in type_eps]))
        survivors = [ep for ep in type_eps if not ep["is_crash"]]
        recovery_rate = float(np.mean([ep["recovered"] for ep in survivors])) if survivors else float("nan")
        recovery_times = [ep["recovery_time_steps"] for ep in survivors if ep["recovered"]]
        mean_recovery_time = float(np.mean(recovery_times)) if recovery_times else float("nan")

        print(f"    Crash rate:          {crash_rate*100:5.1f}%  (n={len(type_eps)})")
        print(f"    Recovery rate:       {recovery_rate*100:5.1f}%  (of {len(survivors)} non-crashed)")
        if recovery_times:
            print(f"    Mean recovery time:  {mean_recovery_time:.1f} steps ({mean_recovery_time/30:.2f}s @ 30Hz)")
        else:
            print("    Mean recovery time:  n/a (none recovered)")

        if type_name == "wind":
            steady_errors = [ep["wind_steady_state_error_mean"] for ep in type_eps
                              if ep["wind_steady_state_error_mean"] is not None]
            if steady_errors:
                print(f"    Mean steady-state error during wind window: {float(np.mean(steady_errors)):.3f} m")

        mastery = crash_rate < MASTERY_MAX_CRASH_RATE and (
            recovery_rate > MASTERY_MIN_RECOVERY_RATE if survivors else False
        )
        print(f"    [{'PASS' if mastery else 'FAIL'}] mastery gate: crash rate <10% AND recovery rate >90%")

        metrics[f"{type_name}_crash_rate"] = crash_rate
        metrics[f"{type_name}_recovery_rate"] = recovery_rate
        metrics[f"{type_name}_mean_recovery_time_steps"] = mean_recovery_time
        metrics[f"{type_name}_n_episodes"] = len(type_eps)

        # Per-level sub-breakdown, same type.
        by_level = defaultdict(list)
        for ep in type_eps:
            by_level[ep["disturbance_level"]].append(ep)
        level_line = []
        for level in range(1, DISTURBANCE_LEVELS + 1):
            level_eps = by_level.get(level, [])
            if not level_eps:
                level_line.append(f"L{level}: n/a")
                continue
            lc = float(np.mean([e["is_crash"] for e in level_eps]))
            l_survivors = [e for e in level_eps if not e["is_crash"]]
            lr = float(np.mean([e["recovered"] for e in l_survivors])) if l_survivors else float("nan")
            level_line.append(f"L{level}: n={len(level_eps)} crash={lc*100:.0f}% recover={lr*100:.0f}%")
        print("    By level: " + " | ".join(level_line))

    return metrics


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
        help="Apply a stage's disturbance config (same presets hover_train.py uses, from "
             "config.py's HOVER_STAGE_PRESETS) so evaluation matches how the model was trained. "
             "REQUIRED to see any disturbance events at all -- without --stage, "
             "disturbance_enabled defaults to False and this is a plain (undisturbed) hover eval "
             "regardless of what the model was actually trained on."
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
        if getattr(config.task, "disturbance_enabled", False) and args.episodes < RECOMMENDED_MIN_EPISODES_FOR_3X5:
            print(
                f"NOTE: --episodes {args.episodes} is below the recommended "
                f"{RECOMMENDED_MIN_EPISODES_FOR_3X5}+ for a trustworthy 3-type/5-level breakdown "
                f"(15 buckets total). Proceeding anyway -- fine for a quick sanity check.\n"
            )

    env = HoverGymEnv(config)
    model = PPO.load(model_path, device="cpu")

    episodes = []
    for ep in range(args.episodes):
        # Only the first reset needs an explicit seed — gymnasium's np_random
        # carries forward deterministically from there, so the whole sequence
        # becomes reproducible without reseeding every episode.
        seed = args.seed if ep == 0 else None
        result = run_episode(env, model, seed=seed)
        episodes.append(result)

        crash_note = f" ({result['truncation_reason']})" if result["is_crash"] else ""
        print(
            f"episode {ep+1:2d}/{args.episodes} | "
            f"final pos error: {result['final_pos_error']:.3f} m | "
            f"crash: {result['is_crash']}{crash_note} | "
            f"reward: {result['total_reward']:.1f} | "
            f"start jitter: {result['jitter_norm']:.3f} m | "
            f"start yaw jitter: {np.degrees(abs(result['start_yaw_rad'])):.1f} deg"
            f"{_disturbance_episode_note(result)}"
        )

    env.close()

    position_errors = [e["final_pos_error"] for e in episodes]
    crashes = [e["is_crash"] for e in episodes]
    rewards = [e["total_reward"] for e in episodes]
    jitter_norms = [e["jitter_norm"] for e in episodes]
    yaw_jitters = [abs(e["start_yaw_rad"]) for e in episodes]

    mean_pos_error = float(np.mean(position_errors))
    crash_rate = float(np.mean(crashes))
    mean_reward = float(np.mean(rewards))

    print("\n" + "=" * 50)
    print(f"Episodes run:          {args.episodes}")
    print(f"Mean final pos error:  {mean_pos_error:.3f} m")
    print(f"Crash rate:            {crash_rate*100:.1f}%")
    print(f"Mean episode reward:   {mean_reward:.1f}")
    print("=" * 50)

    # --- Disturbance report (3 types x 5 levels; empty dict if no events
    # fired, e.g. --stage wasn't passed or this run's config had it off) --
    disturbance_metrics = _print_disturbance_report(episodes, args.episodes)

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
              f"Query with: python -m src.weight_manager.model_registry describe {model_path}")

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
            trace = np.asarray(episodes[i]["pos_error_trace"])
            min_error = float(trace.min())
            step_of_min = int(trace.argmin())
            # Last 10% of the episode vs. its best moment — cheap way to tell
            # "never got close" (min_error itself is already high) apart from
            # "got close, then drifted back away before the episode ended".
            tail_window = trace[-max(1, len(trace) // 10):]
            drifted = min_error < args.tail_threshold * 0.6 and float(tail_window.mean()) > min_error * 1.5
            pattern = "converged then drifted" if drifted else "never converged"
            dist_note = _disturbance_episode_note(episodes[i])
            print(
                f"  episode {i+1:2d} | pos error {position_errors[i]:.3f} m | "
                f"reward {rewards[i]:.1f} | start jitter {jitter_norms[i]:.3f} m | "
                f"start yaw jitter {np.degrees(yaw_jitters[i]):.1f} deg | "
                f"best={min_error:.3f} m @ step {step_of_min}/{len(trace)} ({pattern}){dist_note}"
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
        # Disturbance-aware note: a disturbed episode landing in the tail is
        # expected and not itself a red flag -- only non-disturbed episodes
        # in the tail point at a general policy weak spot vs. disturbance
        # recovery specifically.
        n_tail_disturbed = sum(1 for i in tail_idx if episodes[i]["disturbance_fired"])
        if n_tail_disturbed:
            print(f"  ({n_tail_disturbed}/{len(tail_idx)} tail episodes had a disturbance event fire -- "
                  f"expected overlap, not necessarily a general policy weak spot)")

    pos_correlation = None
    yaw_correlation = None
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

    if tail_idx and pos_correlation is not None:
        _describe(pos_correlation, "position jitter")
    if tail_idx and yaw_correlation is not None:
        _describe(yaw_correlation, "yaw jitter")

    if tail_idx and pos_correlation is not None and yaw_correlation is not None:
        if pos_correlation < 0.4 and yaw_correlation < 0.4:
            print(
                "\nNeither start condition strongly predicts the tail. This leans toward "
                "a policy weak spot independent of start draw, rather than 'got an "
                "unusually hard start position.' Check the per-episode 'converged then "
                "drifted' vs 'never converged' tags above: the former points at a late-"
                "episode stability issue (reward/PID interaction, maybe survival_bonus "
                "vs. position_error_weight balance); the latter points at slow/incomplete "
                "convergence within the episode length, which more training timesteps "
                "might fix on its own. If most tail episodes also show a disturbance note, "
                "check the disturbance report above before concluding this is a general "
                "weak spot rather than a disturbance-recovery gap."
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
            dist_note = _disturbance_episode_note(episodes[i])
            print(
                f"  episode {i+1:2d} | reason: {episodes[i]['truncation_reason']} | "
                f"final pos error {position_errors[i]:.3f} m | "
                f"reward {rewards[i]:.1f} | start jitter {jitter_norms[i]:.3f} m | "
                f"start yaw jitter {np.degrees(yaw_jitters[i]):.1f} deg{dist_note}"
            )
        n_crash_disturbed = sum(1 for i in crash_idx if episodes[i]["disturbance_fired"])
        print(
            f"  {n_crash_disturbed}/{len(crash_idx)} crashes had a disturbance event fire. "
            "Crashes matter independently of the position-error tail — a policy that "
            "rarely-but-genuinely crashes is a different (and more serious) problem than "
            "one that just converges slowly. Worth tracking whether this reproduces on "
            "other seeds/eval runs before assuming it's a one-off."
        )


if __name__ == "__main__":
    main()
