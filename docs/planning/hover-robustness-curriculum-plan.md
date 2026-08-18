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

## Stage 0 — Resolve the baseline (DONE, 2026-08-16)

Original plan assumed picking among 4 pre-existing checkpoints. That changed
mid-execution: the 4 originals were deliberately retired (`checkpoint_manager.py
retire-task waypoint_nav` swept them in error initially — a real bug in the
task-filtering logic, since fixed — then a second, deliberate `rm -rf` on the
archive folder permanently removed them once the decision was made to train
hover from scratch instead of resuming from them). Stage 0 became: train one
fresh baseline, evaluate every intermediate checkpoint (not just the final
save), pick the real winner.

Result: `hover_stabilize_ppo_seed0`, from-scratch, 500k steps,
`--checkpoint-every 50000`. Full 11-checkpoint eval table in
`training-log.md` Run 2026-08-16-0. Champion: the **450,000-step**
checkpoint (hash `f9153039...`), not the final save — 0.020m mean position
error, 0% crash rate, beating the 501,760-step final save (0.025m, 5%
crash) on both axes simultaneously. Promoted to
`model/model_weights/hover_champion.zip` via `checkpoint_manager.py`.

Notable and still only partially understood: a crash-rate spike at
250k–350k steps (peaking 80% at 250k) that resolves by 450k, while position
error over that same window looked good (would have been missed by
position-error-only monitoring). Working theory (overcorrection via
elevated action variance) was tested and **refuted** — `train/std` was
strictly decreasing through the window, opposite of predicted. Mechanism
remains unexplained; see `theory-log.md` 2026-08-16-0/1. Not blocking —
noted because the same "good primary metric, bad secondary metric" trap is
exactly what Stage 1's eval discipline (below) exists to catch going
forward.

**Open question resolved:** `hover_evaluate.py`'s metric (position error +
crash rate, checked as separate criteria) was sufficient to select a real
champion — but only because both were checked. The crash-spike incident is
a concrete argument for continuing to gate on both, every stage, not
simplifying to one scalar later for convenience.

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

## Stage 1 — impulse kicks (design finalized 2026-08-16, not yet built)

**Type chosen: impulse kicks**, via `apply_velocity_kick()` (already exists,
confirmed kinematic-override mechanism, not physics-solver-timing-dependent
— see `drone_sim.py` docstring). Chosen over sustained/gusting wind as the
*first* stage specifically because a single discrete event is easier to
attribute a crash or recovery to than a continuous force layered on normal
control noise — isolating one clean mechanism before layering complexity,
not a claim that kicks are more important long-term than wind.

**Magnitude scale — grounded in the platform's own operating envelope.**
`drone_sim.py`'s specs (`m=0.027kg`, `max_speed_kmh=30`) match the Crazyflie
gym-pybullet-drones simulates — 30 km/h ≈ **8.3 m/s**, the platform's own
top controllable speed. Scaling disturbance against that gives a defensible,
cited ceiling instead of a guessed absolute number:

| Level | Kick magnitude | % of max speed | Rationale |
|---|---|---|---|
| 1 (mild) | 0.1–0.3 m/s | ~2–4% | Barely perceptible; sanity-checks the mechanism |
| 2 (moderate) | 0.3–0.6 m/s | ~4–7% | Realistic bump/prop-wash from a nearby object |
| 3 (severe, Stage 1 ceiling) | 0.8–1.2 m/s | ~10–15% | Plausible worst-case indoor collision; beyond this starts to look like a different failure category (structural/actuator), not "recover from a shove" |

**Timing within an episode:** one kick per episode (see sub-stage table
below for when multi-kick is introduced), landing at a **random step
between step 60–150** (2–5s into an 8s/240-step episode). Reasoning: too
early and it's indistinguishable from normal initial-convergence behavior
(the champion typically settles within the first 1–2s); too late and there's
not enough episode left to observe recovery before truncation. Randomizing
within the window (not a fixed step) prevents the policy from learning to
"brace" at a memorized timestep instead of reacting to the actual event.

**Recovery definition — anchored to existing numbers, not invented fresh.**
`hover_evaluate.py` already uses **0.2m** as `tail_threshold`, its existing
boundary for "notably worse than typical." Reusing it here (rather than a
new disconnected number) keeps Stage 1 comparable to every other hover eval
already run. Following the same non-momentary-touch principle
`landing_hold_time_sec` already uses elsewhere in the codebase: **recovered
= position error back under 0.2m within 60 steps (2s) of the kick, AND
sustained through episode end** — not just touching 0.2m once and drifting
back out.

**Mastery gate, applied identically at every sub-stage below:** crash rate
<10% (matching the existing Stage 2 hover bar) AND recovery rate >90%
within the 2s/60-step budget. One consistent bar throughout, not a new
threshold invented per sub-stage.

**Sub-stage progression — cumulative within magnitude, one new variable at
a time:**

| Sub-stage | Kicks/episode | Magnitude(s) sampled | Episode length | Purpose |
|---|---|---|---|---|
| 1a | 1 | Level 1 only | 8s (current) | Establish the mechanism works at all |
| 1b | 1 | Level 1 + 2 (cumulative, not replace) | 8s | Escalate magnitude without losing 1a competence |
| 1c | 1 | Level 1 + 2 + 3 | 8s | Full single-kick magnitude range mastered |
| 1d | 0 (sanity check, no kicks) | n/a | longer (e.g. 16s) | Isolate episode-length as a variable BEFORE adding periodicity — confirms baseline hover quality holds over a longer duration on its own |
| 1e | 2+, fixed spacing | Level 1+2+3 mix, similar magnitude within an episode | longer | Introduce repeated disturbance as its own new variable, not combined with 1d's length change |
| 1f | 2+, random spacing/magnitude | Level 1+2+3, randomized per kick | longer | Stage 1's actual finish line |

The 1c→1d split matters specifically because 1d and 1e each change exactly
one thing relative to the prior row — same discipline as the zero-cost
`--episode-len-sec` test that ruled out episode budget as waypoint nav's
bottleneck on 2026-08-09. Skipping 1d (going straight from 1c to periodic
kicks on a longer episode) would conflate "can't handle a longer episode"
with "can't handle repeated kicks" if something regresses.

**Per-trial logging** (feeds the metrics section below): kick step(s),
magnitude(s), crash (y/n), recovered within budget (y/n), and if so,
recovery time in steps — that last number is what tells whether 1a→1b→1c is
degrading gracefully or falling off a cliff, not just pass/fail per
sub-stage.

Reuse waypoint-nav's discipline: numbers per checkpoint, logged, not just
a final-save eval or a TensorBoard curve glanced at once.

Per disturbance type, track at minimum:
- Max disturbance magnitude survived without crash
- Time-to-recover to within X cm of target after disturbance onset (X TBD)
- Steady-state position error under sustained disturbance (types 1, 2)
- Crash rate at each magnitude level
- For type 8 specifically: touchdown vertical velocity and horizontal
  drift, since this only matters during landing approach

**Resolved for Stage 1 (2026-08-16):** recovery radius = 0.2m (reusing
`hover_evaluate.py`'s existing `tail_threshold`), recovery budget = 60
steps/2s sustained, not momentary. See Stage 1 section above for the full
reasoning. Types 1/2/4–9 still need their own recovery-radius/budget
definitions when their turn comes — 0.2m/2s is not assumed to transfer
automatically to a different disturbance type without re-justifying it.

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

1. ~~Resolve Stage 0~~ — done 2026-08-16, see above. Champion:
   `hover_champion.zip` (hash `f9153039...`).
2. ~~Decide Stage 1's disturbance type and magnitude~~ — done 2026-08-16,
   see Stage 1 section above.
3. Build the actual gym-wrapper changes for sub-stage 1a: kick injection
   (random step 60–150, Level-1 magnitude 0.1–0.3 m/s), recovery tracking
   (0.2m/60-step sustained), and per-trial logging as specified above.
   Not yet started — this doc was written specifically to exist before
   that code does.
4. Extend `model_registry.py`'s `run` schema for disturbance metadata (type,
   magnitude range, which prior sub-stages' distributions are included) —
   still not done, still worth doing before 1a's first training run rather
   than after, same lesson as `--checkpoint-every` arriving late cost a day
   on 2026-08-09.
5. Pin down real magnitude numbers for types 1–2 (wind) — still open,
   deferred behind Stage 1 (kicks) per the type-choice reasoning above.
6. Full hyperparameter/policy sweep at sub-stage 1a specifically (per the
   sweep-on-regression policy: Stage 1's first sub-stage is where
   sweep-always is still justified, to establish the approach works before
   defaulting to carry-forward configs).
