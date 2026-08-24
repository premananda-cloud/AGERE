# Hover Disturbance — 3-Type / 5-Level Scoped Design

**Status:** proposed, not yet run. Supersedes the open-ended 9-type
taxonomy and strict cumulative sub-stage curriculum (1a -> 1b -> 1c...)
in `hover-robustness-curriculum-plan.md` for the current push — that doc's
taxonomy and reasoning aren't wrong, just larger in scope than what we're
committing compute to right now.

## Scope decisions

- **Takeoff and landing are scripted, not learned**, and out of scope for
  this training push entirely. RL trains hover-only, starting and ending
  mid-air (same as the existing task). Scripted takeoff/land control may
  later be logged as demonstration trajectories (state-action pairs) if a
  future pretraining/behavior-cloning use case comes up — not built now,
  noted so the scripted controller's logging hooks aren't designed to
  preclude it later.
- **Disturbance robustness is explicitly bounded**, not treated as an
  open-ended research program: 3 types, 5 magnitude levels each, sampled
  as one event per episode. This directly avoids repeating Stage 1a's
  failure mode (a narrow single-level preset burned 300k training steps
  with zero learning signal — training-log.md Run 2026-08-16-1) by
  training across the whole scoped space in one run instead of staging
  narrow sub-presets one at a time.

## The 3 types

| Type | Mechanism | Sim method |
|---|---|---|
| Kick | Instantaneous linear velocity add | `DroneSim.apply_velocity_kick` (existing) |
| Torque | Instantaneous angular velocity add | `DroneSim.apply_torque_kick` (new) |
| Wind | Constant force, reapplied every step for a window | `DroneSim.apply_sustained_force` (new) |

Dropped from the original 9-type taxonomy: payload/mass shift, thrust
asymmetry, actuator dropout (need per-motor access the VEL/PID action
interface doesn't expose), sensor noise/latency (a perception-robustness
axis, not a force disturbance — the taxonomy doc itself recommended
treating it separately), ground-effect (landing-specific, out of scope
now that landing is scripted).

## The 5 levels

| Level | Kick (m/s) | Torque (rad/s) | Wind (N) |
|---|---|---|---|
| 1 | 0.3–0.5 | 1–2 | 0.02–0.04 |
| 2 | 0.5–0.8 | 2–4 | 0.04–0.07 |
| 3 | 0.8–1.1 | 4–6 | 0.07–0.10 |
| 4 | 1.1–1.5 | 6–9 | 0.10–0.14 |
| 5 | 1.5–2.0 | 9–13 | 0.14–0.18 |

**Validation status, honestly:**
- **Kick**: floor corrected from 1a's confirmed-too-weak 0.1–0.3 m/s.
  Still a best estimate, not yet re-validated against the champion —
  worth a quick no-training calibration eval before a full run.
- **Torque**: unvalidated placeholder. No prior data on this axis exists.
- **Wind**: unvalidated estimate, scaled against the CF2X's own hover
  thrust (~0.265N) rather than a real wind reference. The curriculum
  plan doc itself left wind's magnitude as an unresolved open item.

Don't treat this table as calibrated fact — it's a defensible starting
point built the same way the original kick levels were (grounded in a
real platform number, not a guessed adjective), but two of the three
types have zero empirical backing yet. Recommend a cheap sanity pass
(the mastery-gate metrics after a short run, or a manual eval sweep) on
torque and wind specifically before trusting the numbers the way kick's
original L3 ceiling was trusted.

## Sampling

One disturbance event per episode. Type sampled uniformly among
`task.disturbance_types_active`. **Level sampled uniformly 1–5** (not
magnitude sampled uniformly across the type's full range), so severe
levels get equal training exposure regardless of how wide their span is.
Onset step sampled in the existing `[disturbance_kick_step_min,
disturbance_kick_step_max]` window (60–150, i.e. 2–5s into an 8s
episode), same reasoning as the original Stage 1a design: early enough
to observe recovery before truncation, late enough not to be confused
with initial convergence.

## What's NOT done yet

- `hover_evaluate.py` still expects the old single-kick-type info keys
  (`kicked`/`recovered`/`recovery_time_steps`). It won't crash against
  the updated `HoverGymEnv` (`disturbance_fired` etc. are new keys it
  doesn't look for), but its disturbance report section will silently
  show zero kicked episodes — needs a matching update before evaluating
  a model trained on this design. Flagged, not fixed in this pass.
- No calibration eval has actually been run for torque or wind.
- `model_registry.py`'s run-record schema extension (type/magnitude/prior
  stages, per the original curriculum plan) hasn't been revisited for
  this simplified single-preset design — may not need it if
  "disturbance_3x5" is logged as one run tag, worth a quick check against
  the actual registry schema.
