# Hover Robustness Curriculum — Planning Doc

## Status: DRAFT — not yet implemented, open for challenge

## Core thesis

The RL policy is the pilot, not a scripted fallback. Rationale: a learned
`obs → action` mapping degrades gracefully on cases adjacent to its training
distribution, and keeps functioning if disconnected from any higher-level
planner. A hand-coded control path only handles cases its author explicitly
anticipated, and a scripted state machine has no recovery mechanism if a
case falls outside what it was written for. This doc is about making that
bet justifiable — building a hover policy whose robustness is measured and
attributable to specific training decisions, not asserted.

Explicit non-goal: this doc does not argue RL-vs-classical-control in
general. It states the argument for *this* choice, once, so it can be
challenged on its own terms rather than re-litigated per stage.

## Stage 0 — Resolve the baseline (blocking, do first)

Before any curriculum work: four candidate checkpoints exist
(`hover_stabilize_ppo_seed0/1/2.zip`, `hover_stabilize_ppo.zip`). Do not
assume the unnumbered file is a seed or a duplicate — hash all four via
`model_registry`, evaluate each on the existing (undisturbed)
`hover_evaluate.py` metric, and log the result. Winner becomes "the hover
champion" and the sole Stage-0 parent for everything below. This is the
same discipline that caught the waypoint baseline silently regressing on
2026-08-11 — don't skip it because it feels obvious.

**Open question:** does `hover_evaluate.py`'s current metric (whatever it
optimizes today) actually capture "good baseline hover," or does it need a
second look before being trusted as the Stage-0 selection criterion?

## Disturbance taxonomy

Ordered most → least realistic/common for a hovering multirotor. Each needs
a concrete magnitude scale before any wrapper code is written — "realistic
ceiling" must cite a number, not an adjective.

| # | Type | Mechanism | Magnitude scale (needs real numbers) |
|---|------|-----------|---------------------------------------|
| 1 | Sustained wind | Constant-direction force, many steps | N, or equivalent steady-state tilt angle |
| 2 | Turbulent/gusting wind | Stochastic force, varying direction/magnitude over time | N mean + stddev, correlation time |
| 3 | Impulse kicks | Sudden momentary force (`apply_velocity_kick`/`apply_impulse_force`, already exists) | Δv (m/s) |
| 4 | Payload/mass shift | Sudden added mass or CG shift | % of nominal mass, offset distance |
| 5 | Thrust asymmetry | One rotor under-producing vs. command | % thrust deficit on one motor |
| 6 | Sensor noise/latency | Corrupted or delayed observation, not a physical force | stddev on position/velocity/orientation obs; latency in steps |
| 7 | Angular/spin (torque impulse) | Collision or prop-wash inducing rotation | rad/s impulse |
| 8 | Ground-effect turbulence | Landing-phase-specific turbulence near surface | altitude band + magnitude |
| 9 | Actuator dropout | Partial/full motor loss | % thrust loss, duration (transient vs. permanent) |

Note: #6 is not a force disturbance at all — it's a perception-robustness
axis. Recommend treating it as a separate track from 1–5/7–9 rather than
folding it into "degree of disturbance," since the failure mode it tests
(policy trusts bad data) is different from the failure mode force
disturbances test (policy can't compensate fast enough).

**Open item, not yet resolved:** actual numbers for the "realistically
possible degree" ceiling per type. Needs either a motor/frame spec, a
cited outdoor wind-speed distribution, or a plausible-collision estimate —
whatever is defensible, written down, and challengeable, not guessed.

## Curriculum structure

**Decision: cumulative, not strictly sequential-replace.** Original
proposal was train-to-convergence on type N, then move to type N+1. Risk:
nothing prevents a later stage from silently degrading robustness to an
earlier disturbance type, since a purely sequential curriculum stops
sampling it — the same "checkpoint quietly got worse" failure the model
registry was built to catch, one dimension up. Instead:

- Each stage adds one disturbance type to the sampling distribution; prior
  types remain present (at their previously-trained magnitude) throughout
  all later stages.
- Each stage's eval reports performance against **every disturbance type
  introduced so far**, not just the newest one. A stage that improves on
  its new type while regressing on an earlier one is a partial failure,
  not a success, and gets flagged before proceeding.
- Within a type, magnitude escalates in the same cumulative spirit: once a
  magnitude level is trained, later levels don't fully replace it in the
  sampling distribution (avoids overfitting to only the hardest case at
  the expense of the easy/common one).

**Decision: sweep-on-regression, not sweep-always.** Running N types × M
magnitude levels × K hyperparameter/policy variants at every stage is
expensive and, per 2026-08-09's finding, most single-lever tweaks don't
move outcomes — the wins were rare and structural. Default: carry forward
one config per stage. Only spend a hyperparameter/policy sweep when a
stage's eval comes back flat or regressed relative to expectation. Full
sweep is reserved for Stage 1 (establishing whether the approach works at
all) and for any stage that regresses.

## Metrics (define before training, not after)

Reuse waypoint-nav's discipline: numbers per checkpoint, logged, not just
a final-save eval or a TensorBoard curve glanced at once.

Per disturbance type, track at minimum:
- Max disturbance magnitude survived without crash
- Time-to-recover to within X cm of target after disturbance onset (X TBD)
- Steady-state position error under sustained disturbance (types 1, 2)
- Crash rate at each magnitude level
- For type 8 specifically: touchdown vertical velocity and horizontal
  drift, since this only matters during landing approach

**Open item:** the recovery-radius X and "crash" definition need concrete
values before Stage 1 starts — same category of gap as `landing_max_velocity`
already existing for the landing case.

## Registry extension

Current `model_registry.py` logs config, cumulative steps, and parent
checkpoint. Extend the `run` record schema to also capture: disturbance
type(s) active in this run's sampling distribution, magnitude range per
type, and which prior stages' distributions are included (to make the
"cumulative not replace" property auditable after the fact, not just
asserted in this doc).

## Logging discipline (per stage)

For each stage, log: which disturbance type/magnitude was added, the
hyperparameter/policy config used (and sweep results if one was run), the
eval table across all disturbance types introduced so far, and a short
theory section — why this config, why this magnitude step, what result
would falsify the approach. Same spirit as the 2026-08-09 progress-shaping
write-up: reviewed and reasoned about before commit, not just a result
dump.

## Explicitly out of scope for now (parking lot)

- Sensor-noise/latency track (#6) as a fully separate curriculum — flagged
  above, not scheduled.
- Ground-effect (#8) is landing-phase-specific and depends on landing work
  that hasn't started yet (waypoint's command-override / takeoff-land
  design from 2026-08-11 is a prerequisite, not this doc).
- Actuator dropout (#9) — highest severity, probably a "does it fail safe"
  pass/fail test rather than a "does it learn to recover" training target;
  revisit once 1–5 and 7 are solid.
- Full ROI/cost accounting for the entire sweep matrix — acknowledged this
  could be large; not worth blocking Stage 1 on estimating it precisely,
  but worth revisiting if Stage 1's sweep alone turns out to be expensive.

## Plan for next session

1. Resolve Stage 0 (hash + eval the four hover checkpoints, log winner).
2. Pin down real magnitude numbers for disturbance types 1–3 (the ones
   most likely to go first), with a cited source per number.
3. Define the concrete metric thresholds (recovery radius, crash
   definition) that Stage 1's eval will report against.
4. Decide Stage 1's disturbance type (recommend #3, impulse kicks — cheapest
   to implement, already has partial infra via `apply_velocity_kick`) and
   run the full hyperparameter/policy sweep there, since Stage 1 is where
   sweep-always is still justified.
5. Extend `model_registry.py`'s schema per the section above before Stage
   1's first run, not after — same lesson as `--checkpoint-every` arriving
   only after flying blind cost a day.
