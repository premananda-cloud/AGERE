"""
Tilt-criterion diagnostic.

Question this answers: hover_gym_wrapper.py's crash check
(max_tilt_rad, default 0.4 rad / ~23deg) truncates the instant roll or
pitch crosses the line, with NO hold-time -- unlike recovery, which
requires 60 SUSTAINED steps under threshold (recovery_hold_steps). A
policy that tilts hard for one physics step to redirect thrust and arrest
a strong kick -- exactly what a correct recovery maneuver looks like --
gets scored identically to a policy that's genuinely spinning out of
control. After three training pushes (raw continued training, then an
ent_coef/gamma fix) all plateaued at the same ~33-40% crash rate with no
improvement, this checks whether the criterion itself, not the policy, is
the actual ceiling.

Method: re-run eval with max_tilt_rad loosened well past plausible loss of
control (default 1.2 rad / ~69deg -- if a policy is still flying straight
and recovering position at THAT tilt, the original 0.4 rad line was almost
certainly cutting off recoverable maneuvers, not catching real crashes).
For every episode whose tilt trace crossed the ORIGINAL 0.4 rad line,
classify what actually happened next under the loosened bound:

  - RECOVERED_DESPITE_BREACH: tilt came back under the original threshold
    and stayed there for the rest of the episode, episode reached timeout
    (not a loosened-bound crash), and final position error is within the
    Stage 2 bar. Strong evidence the original criterion was the artifact.
  - GENUINE_LOSS_OF_CONTROL: episode still ended in a crash (out-of-bounds
    or the loosened tilt bound itself) -- the disturbance really was
    beyond what the policy could handle, independent of where the tilt
    line is drawn.
  - AMBIGUOUS: reached timeout without a further crash, but tilt never
    fully settled back under the original line, or final position error
    stayed poor -- some instability, just not a full loss of control.

Usage:
    python -m src.training.evaluate.hover_tilt_diagnostic \\
        --model model/model_weights/hover_stabilize_ppo_seed0_disturbance_3x5.zip \\
        --stage disturbance_3x5 --episodes 90 --seed 0

    # Try a different loosened bound if the default doesn't separate the
    # categories cleanly:
    python -m src.training.evaluate.hover_tilt_diagnostic ... --loosened-tilt-rad 1.57
"""

import argparse
from dataclasses import replace

import numpy as np
from stable_baselines3 import PPO

from src.config import ProjectConfig, HOVER_STAGE_PRESETS
from src.paths import hover_stabilize_model_path
from src.training.gym_wrapper.hover_gym_wrapper import HoverGymEnv
from src.training.evaluate.hover_evaluate import run_episode, STAGE_2_MAX_POSITION_ERROR


def classify(ep: dict, original_tilt_rad: float) -> tuple[str, dict]:
    trace = np.asarray(ep["tilt_trace"])
    breach_idx = np.where(trace > original_tilt_rad)[0]
    if len(breach_idx) == 0:
        return "no_breach", {"peak_tilt_rad": float(trace.max()) if len(trace) else 0.0}

    peak_tilt = float(trace.max())
    last_breach = int(breach_idx[-1])
    has_tail = last_breach < len(trace) - 1
    settled_after = has_tail and bool(np.all(trace[last_breach + 1:] <= original_tilt_rad))

    # "Crash" here means the LOOSENED run still ended in a truncation that
    # isn't a clean timeout -- out-of-bounds, or the loosened tilt bound
    # itself. If truncation_reason is None the episode never truncated
    # (shouldn't happen given HoverGymEnv always truncates via timeout at
    # worst) -- treat missing as ambiguous rather than assuming either way.
    reason = ep["truncation_reason"]
    ended_clean = reason == "timeout"
    pos_ok = ep["final_pos_error"] < STAGE_2_MAX_POSITION_ERROR

    details = {
        "peak_tilt_rad": peak_tilt,
        "peak_tilt_deg": float(np.degrees(peak_tilt)),
        "settled_after_last_breach": settled_after,
        "truncation_reason_under_loosened_bound": reason,
        "final_pos_error": ep["final_pos_error"],
    }

    if ended_clean and settled_after and pos_ok:
        return "recovered_despite_breach", details
    if not ended_clean:
        return "genuine_loss_of_control", details
    return "ambiguous", details


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default=None)
    parser.add_argument("--episodes", type=int, default=90)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--stage", type=str, default=None, choices=sorted(HOVER_STAGE_PRESETS.keys()))
    parser.add_argument(
        "--loosened-tilt-rad", type=float, default=1.2,
        help="~69 degrees. Deliberately far past anything a controlled recovery should need -- "
             "if the policy is still flying straight and converging at this tilt, the original "
             "0.4 rad crash line was almost certainly the artifact, not the policy's ceiling."
    )
    args = parser.parse_args()
    model_path = args.model or str(hover_stabilize_model_path())

    config = ProjectConfig()
    if args.stage:
        config.task = replace(config.task, **HOVER_STAGE_PRESETS[args.stage])
        print(f"Applied stage preset '{args.stage}': {HOVER_STAGE_PRESETS[args.stage]}")

    original_tilt_rad = config.task.max_tilt_rad
    print(f"Original max_tilt_rad: {original_tilt_rad:.3f} rad ({np.degrees(original_tilt_rad):.1f} deg)")
    print(f"Loosened to:           {args.loosened_tilt_rad:.3f} rad ({np.degrees(args.loosened_tilt_rad):.1f} deg) "
          f"for this diagnostic run ONLY -- not a training config change.\n")
    config.task = replace(config.task, max_tilt_rad=args.loosened_tilt_rad)

    env = HoverGymEnv(config)
    model = PPO.load(model_path, device="cpu")

    episodes = []
    for ep in range(args.episodes):
        s = args.seed if ep == 0 else None
        episodes.append(run_episode(env, model, seed=s))
    env.close()

    disturbed = [e for e in episodes if e["disturbance_fired"]]
    categories = {"no_breach": [], "recovered_despite_breach": [], "genuine_loss_of_control": [], "ambiguous": []}
    detail_by_ep = {}
    for i, ep in enumerate(disturbed):
        label, details = classify(ep, original_tilt_rad)
        categories[label].append(ep)
        detail_by_ep[i] = details

    print(f"{len(disturbed)} disturbed episodes evaluated under the loosened bound.\n")
    n_breached = len(disturbed) - len(categories["no_breach"])
    print(f"{n_breached}/{len(disturbed)} episodes crossed the ORIGINAL {original_tilt_rad:.2f} rad line "
          f"at some point (these are the ones that would have been truncated as 'crash' under the real "
          f"training/eval config):\n")

    for label in ("recovered_despite_breach", "genuine_loss_of_control", "ambiguous"):
        eps = categories[label]
        print(f"  {label}: {len(eps)}/{n_breached if n_breached else 1}")
        for ep in eps[:8]:  # cap printed detail; counts above are the real signal
            idx = disturbed.index(ep)
            d = detail_by_ep[idx]
            dist = f"{ep['disturbance_type']} L{ep['disturbance_level']} ({ep['disturbance_magnitude']:.3f})"
            print(
                f"    {dist:28s} | peak tilt {d['peak_tilt_deg']:5.1f} deg | "
                f"final pos err {d['final_pos_error']:.3f} m | "
                f"ended: {d['truncation_reason_under_loosened_bound']}"
            )
        if len(eps) > 8:
            print(f"    ... and {len(eps) - 8} more")
        print()

    print("=" * 60)
    if n_breached == 0:
        print("No episodes crossed the original tilt line at all in this sample -- can't diagnose "
              "from this run; try more episodes or a --stage/model combination known to crash.")
    else:
        recovered_frac = len(categories["recovered_despite_breach"]) / n_breached
        genuine_frac = len(categories["genuine_loss_of_control"]) / n_breached
        print(f"Of episodes that breached the original tilt line:")
        print(f"  {recovered_frac*100:.0f}% recovered cleanly once given room (criterion looks too strict)")
        print(f"  {genuine_frac*100:.0f}% were genuine loss of control regardless (criterion isn't the problem)")
        print(f"  {(1-recovered_frac-genuine_frac)*100:.0f}% ambiguous")
        print()
        if recovered_frac > 0.5:
            print("-> Majority recovered once given room. The 0.4 rad zero-hold-time crash check is "
                  "very likely conflating a legitimate hard-tilt recovery maneuver with a real crash. "
                  "Consider either raising max_tilt_rad, or (better, matching this codebase's own "
                  "recovery-hold pattern) requiring tilt to EXCEED the bound for N sustained steps "
                  "before truncating, not a single-step check.")
        elif genuine_frac > 0.5:
            print("-> Majority genuinely lost control even with room to recover. The magnitude levels "
                  "that are crashing (mostly L4-L5 kick/torque per the eval history) may really be past "
                  "this policy/task's recoverable envelope -- Hypothesis B from before, not the tilt "
                  "criterion. Worth reconsidering whether L4-L5 magnitudes belong in training at all, "
                  "vs. accepting them as an intentionally out-of-scope severe tier.")
        else:
            print("-> Mixed/ambiguous. Some episodes are criterion artifacts, some are real -- likely "
                  "both hypotheses are partially true. Worth breaking this down further by disturbance "
                  "type/level (kick vs. torque may not have the same answer).")


if __name__ == "__main__":
    main()
