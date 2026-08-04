"""
Evaluate a trained hover/stabilize policy's recovery from a mid-episode
disturbance — Stage 3 criterion 3, docs/hover-model-plan.md ("Recovers
from a mid-episode external disturbance ... within a few seconds").

The plan doc leaves "recovers ... within a few seconds" qualitative. This
script makes it checkable with two chosen defaults, both overridable —
neither is an officially confirmed number, just a reasonable starting
point:
  --recovery-threshold 0.15   (m) — "recovered" means position error is
                                     back under this value and STAYS under
                                     it for the rest of the recovery
                                     window (a single dip below threshold
                                     that bounces back out doesn't count).
                                     Chosen partway between typical
                                     undisturbed performance (~0.01-0.03 m,
                                     per the 2026-08-01/02 seed runs) and
                                     Stage 2's looser 0.3 m ceiling.
  --recovery-window-sec 3.0   — "a few seconds," read literally.

Disturbance mechanism defaults to a velocity kick (instantaneous, via
PyBullet's resetBaseVelocity) rather than the plan doc's literally-named
applyExternalForce, because a single applyExternalForce call only acts on
ONE physics substep of the next control step — PyBullet clears external
forces after every stepSimulation() call, and HoverAviary.step() runs
several such substeps internally per control step with no hook this class
can reach. See drone_sim.py's apply_impulse_force() docstring for the
full explanation. --mechanism impulse_force is available if the literal
applyExternalForce API is specifically what's wanted; be aware its
effective "kick" is much weaker than --force-magnitude alone suggests,
for that reason.

Usage:
    python -m src.training.evaluate_disturbance
    python -m src.training.evaluate_disturbance --model model/hover_stabilize/hover_stabilize_ppo_seed1.zip
    python -m src.training.evaluate_disturbance --kick-speed 2.0 --episodes 10
    python -m src.training.evaluate_disturbance --mechanism impulse_force --force-magnitude 0.3
    python -m src.training.evaluate_disturbance --gui   # watch the kick happen
"""

import argparse

import numpy as np
from stable_baselines3 import PPO

from src.config import ProjectConfig
from src.paths import hover_stabilize_model_path
from src.training.gym_wrapper import HoverGymEnv


def run_episode(
    env: HoverGymEnv,
    model: PPO,
    seed,
    disturb_fraction: float,
    mechanism: str,
    kick_speed: float,
    force_magnitude: float,
    recovery_threshold: float,
    recovery_window_sec: float,
):
    obs, _ = env.reset(seed=seed)
    ctrl_freq = env.config.sim.ctrl_freq
    max_steps = env._max_steps
    disturb_step = int(max_steps * disturb_fraction)
    window_steps = int(round(recovery_window_sec * ctrl_freq))
    window_end = min(disturb_step + window_steps, max_steps - 1)

    # Random horizontal kick direction, drawn from the env's own seeded
    # RNG (after reset()'s own jitter draws) — --seed reproduces the same
    # kick direction as well as the same start conditions.
    angle = env.np_random.uniform(0, 2 * np.pi)
    direction = np.array([np.cos(angle), np.sin(angle), 0.0])

    pos_error_trace = []
    total_reward = 0.0
    crashed = False
    truncation_reason = None
    disturbed = False

    terminated = truncated = False
    step_i = 0
    while not (terminated or truncated):
        if step_i == disturb_step and not disturbed:
            if mechanism == "velocity_kick":
                env.sim.apply_velocity_kick(direction * kick_speed)
            else:
                env.sim.apply_impulse_force(direction * force_magnitude)
            disturbed = True

        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        pos_error_trace.append(info["position_error_norm"])
        if truncated:
            crashed = info.get("is_crash", False)
            truncation_reason = info.get("truncation_reason")
        step_i += 1

    pos_error_trace = np.asarray(pos_error_trace)
    # First entry in pos_error_trace at index disturb_step is the first
    # post-kick reading, since the kick was applied before that step's
    # env.step() call.
    post_disturb = (
        pos_error_trace[disturb_step:window_end + 1]
        if disturb_step < len(pos_error_trace)
        else np.array([])
    )

    recovered = False
    recovery_time_sec = None
    if len(post_disturb) > 0:
        for j in range(len(post_disturb)):
            if np.all(post_disturb[j:] <= recovery_threshold):
                recovered = True
                recovery_time_sec = j / ctrl_freq
                break

    if crashed and disturbed:
        recovered = False

    return {
        "recovered": recovered,
        "recovery_time_sec": recovery_time_sec,
        "crashed": crashed,
        "truncation_reason": truncation_reason,
        "disturbed": disturbed,
        "disturb_step": disturb_step,
        "episode_len": len(pos_error_trace),
        "final_pos_error": float(pos_error_trace[-1]) if len(pos_error_trace) else None,
        "worst_post_disturb_error": float(post_disturb.max()) if len(post_disturb) else None,
        "total_reward": total_reward,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model", type=str, default=None,
        help="Defaults to model/hover_stabilize/hover_stabilize_ppo.zip (see src/paths.py)"
    )
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Seeds the first reset (and kick-direction draw) for reproducibility, "
             "same convention as evaluate.py."
    )
    parser.add_argument(
        "--disturb-at-fraction", type=float, default=0.5,
        help="Fraction of episode length at which to apply the disturbance (default: midpoint)."
    )
    parser.add_argument("--mechanism", choices=["velocity_kick", "impulse_force"], default="velocity_kick")
    parser.add_argument(
        "--kick-speed", type=float, default=1.0,
        help="m/s added instantaneously in a random horizontal direction (velocity_kick mechanism). "
             "Not a physically-calibrated number — a starting guess, tune and observe with --gui."
    )
    parser.add_argument(
        "--force-magnitude", type=float, default=0.3,
        help="Newtons applied in a random horizontal direction, one physics substep only "
             "(impulse_force mechanism). For reference, this drone's hover thrust is "
             "roughly its weight, ~0.265 N (m=0.027 kg, per the URDF params printed at startup)."
    )
    parser.add_argument(
        "--recovery-threshold", type=float, default=0.15,
        help="Position error (m) the episode must return to and stay under to count as 'recovered.' "
             "Not an officially specified number — see module docstring."
    )
    parser.add_argument(
        "--recovery-window-sec", type=float, default=3.0,
        help="How long after the disturbance the policy has to recover and stay recovered."
    )
    parser.add_argument("--gui", action="store_true")
    args = parser.parse_args()

    model_path = args.model or str(hover_stabilize_model_path())

    config = ProjectConfig()
    if args.gui:
        config.sim.gui = True

    env = HoverGymEnv(config)
    model = PPO.load(model_path, device="cpu")

    results = []
    for ep in range(args.episodes):
        seed = args.seed if ep == 0 else None
        result = run_episode(
            env, model, seed,
            args.disturb_at_fraction, args.mechanism,
            args.kick_speed, args.force_magnitude,
            args.recovery_threshold, args.recovery_window_sec,
        )
        results.append(result)

        if not result["disturbed"]:
            print(f"episode {ep+1:2d}/{args.episodes} | episode ended before the disturbance step (crashed early)")
            continue

        rec_note = f"{result['recovery_time_sec']:.2f}s" if result["recovered"] else "NOT RECOVERED"
        crash_note = f" | crash: {result['truncation_reason']}" if result["crashed"] else ""
        print(
            f"episode {ep+1:2d}/{args.episodes} | disturbed at step {result['disturb_step']} | "
            f"recovery: {rec_note} | worst post-disturb error: {result['worst_post_disturb_error']:.3f} m | "
            f"final error: {result['final_pos_error']:.3f} m{crash_note}"
        )

    env.close()

    n_recovered = sum(r["recovered"] for r in results)
    n_crashed = sum(r["crashed"] for r in results)
    n_undisturbed = sum(not r["disturbed"] for r in results)
    recovery_times = [r["recovery_time_sec"] for r in results if r["recovered"]]

    print("\n" + "=" * 60)
    print(f"Episodes run:                 {args.episodes}")
    print(f"Mechanism:                    {args.mechanism}")
    print(f"Disturbed at fraction:        {args.disturb_at_fraction} of episode length")
    print(f"Recovery threshold:           {args.recovery_threshold} m")
    print(f"Recovery window:              {args.recovery_window_sec} s")
    print(f"Recovered:                    {n_recovered}/{args.episodes}")
    if recovery_times:
        print(f"Mean recovery time (recovered episodes): {np.mean(recovery_times):.2f} s")
        print(f"Max recovery time (recovered episodes):  {np.max(recovery_times):.2f} s")
    print(f"Crashed:                      {n_crashed}/{args.episodes}")
    if n_undisturbed:
        print(f"Never reached disturbance step (crashed early): {n_undisturbed}/{args.episodes}")
    print("=" * 60)

    print("\nStage 3 criterion 3 (docs/hover-model-plan.md):")
    all_recovered = n_recovered == args.episodes
    print(
        f"  [{'PASS' if all_recovered else 'FAIL'}] all episodes recovered within "
        f"{args.recovery_window_sec}s (using {args.recovery_threshold} m threshold — "
        f"not an officially confirmed number, see --help / module docstring)"
    )


if __name__ == "__main__":
    main()
