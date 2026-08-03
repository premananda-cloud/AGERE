# Stage 3 Push — Working Plan

**Purpose:** working plan for the current push toward Stage 3, per
`hover-model-plan.md` §4. Not a replacement for that doc — this is the
"how we're attacking it" companion, expected to go stale once Stage 3 is
reached or the approach changes. Living detail (actual run results) still
belongs in `training-log.md`.

## Stage 3 criteria (verbatim from hover-model-plan.md)

1. Stage 2 criteria hold across **at least 3 different random seeds**
   (rules out "got lucky once")
2. Mean position error at episode end **< 0.1 m**
3. Recovers from a **mid-episode external disturbance** (e.g. impulse
   force via PyBullet's `applyExternalForce`) within a few seconds

**Seed clarification:** "different random seeds" + "rules out got lucky
once" means *training* seeds — retrain the policy from scratch 3+ times
with different seeds and confirm each independently-trained policy clears
Stage 2 (and ideally the 0.1 m bar). Resampling eval episodes against the
one existing policy doesn't address this; it only tests eval-time luck,
not training-time luck.

## Current baseline (2026-07-31 run, single seed)

- Mean position error: 0.088 m — already under the 0.1 m bar *on average*
- Crash rate: 0%
- **But:** 2/20 episodes landed at 0.24–0.29 m, correlated with the
  worst-reward episodes (-55 to -75). A tail this size would very likely
  push a 20-episode mean over 0.1 m on a less lucky sample, or fail
  individual multi-seed runs even if the overall mean holds.

This tail is the actual risk to Stage 3, not the headline mean. It needs
to be understood before multi-seed retraining, not after — if it's a
policy weak spot rather than bad luck on start position, it'll likely
reproduce across all 3+ seeds and burn a training cycle for nothing.

## Plan, in order

### 1. Diagnose the tail (no retraining yet)
Instrument `evaluate.py` to log, per episode: the post-jitter start
position/orientation, final position error, and final reward. Re-run the
existing 20-episode eval and check whether the two tail episodes share
a start-condition signature (e.g. jitter draws near the edge of the
allowed range) or whether they look like a generic policy weak spot with
no obvious start-condition correlation.

- If start-condition correlated → likely fine, just means the eval
  seed happened to sample rare-but-valid starts; multi-seed retraining
  proceeds as planned, expect similar rare tails per seed.
- If not correlated → treat as a real policy gap. Consider whether
  more training timesteps, or a reward-weight adjustment (per
  hover-model-plan.md §5, the smoothness/survival terms may be
  competing with the position term), addresses it *before* spending
  compute on 3 full multi-seed retrains.

### 2. Fix the known cheap win first
Set `device="cpu"` in `ppo_policy.py` (per README/status.md known
issue) before the multi-seed retraining begins — no reason to pay GPU
transfer overhead 3+ times over.

### 3. Multi-seed retraining
Train 3 (or 4, for a margin of safety) separate policies with distinct
seeds, same config otherwise. For each: run the standard 20-episode
`evaluate.py` and confirm Stage 2 criteria (< 0.3 m, <10% crash) *and*
check where each lands relative to the 0.1 m Stage 3 bar. Log every run
in `training-log.md` as it completes, not batched at the end.

### 4. Disturbance-recovery eval (new capability)
Nothing in the current `evaluate.py` / `gym_wrapper.py` injects a
mid-episode disturbance. Needs:
- A way to apply an external impulse to the drone body mid-episode
  (PyBullet's `applyExternalForce`, called on the underlying `HoverAviary`
  body — likely needs a small addition to `DroneSim` in
  `environments/drone_sim.py` to expose this, since that's the layer that
  owns physics access)
- An eval mode that: runs normally to some step N, applies the impulse,
  then tracks position error over subsequent steps to determine time-to-
  reconverge
- A working definition of "recovers... within a few seconds" as a pass/
  fail threshold (e.g. position error back under some bound within X
  simulated seconds) — worth pinning down as an actual number before
  writing the check, since the plan doc leaves it qualitative

### 5. Wrap-up
Once all three criteria are met and logged, update `hover-model-plan.md`'s
checkboxes for Stage 3 and note in `training-log.md` which run(s)
demonstrated it, per that doc's own convention.

## Open questions to resolve during this push

- Is the tail a start-condition artifact or a policy gap? (Step 1 answers
  this before anything else proceeds.)
- What's the actual numeric threshold for "recovers... within a few
  seconds"? Needs a concrete number to be checkable in code.
- Do all 3+ seeds need to independently hit 0.1 m, or is it "Stage 2
  holds across seeds" + "mean position error < 0.1 m" as two separate,
  not-necessarily-per-seed-combined checks? Current reading of the plan
  doc's bullet list treats these as separate bullets, not one compound
  condition — worth confirming before treating a seed that's at 0.12 m
  as an automatic failure.
