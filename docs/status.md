# AGERE Project — Status / Context Handoff

**Purpose of this file:** give a new LLM chat (or another person) full
context on this project in one read, without needing the prior
conversation history. If you're an LLM reading this cold: this is a
real, ongoing project with real training runs already completed — treat
stated results as ground truth, not as something to re-derive from
scratch.

## What this project is

Reinforcement learning for a multirotor drone, part of a larger project
called **Agere** / **Backseat Driver**. **Status as of 2026-08-16, updated
from a stale 2026-08-09-vintage description below — read this block first,
the "Task 2" section further down is now historical, not current.**

- **Task 1, hover/stabilize:** was "complete and paused" as of 2026-08-06.
  **No longer paused — this is the current active task**, now expanded
  into a hover-robustness disturbance curriculum. See
  `docs/planning/hover-robustness-curriculum-plan.md` and
  `docs/research/theory-log.md`.
- **Task 2, waypoint navigation + landing:** was "current focus" as of
  2026-08-09. **Retired 2026-08-16** — judged stuck at a hard local
  optimum (802,816-step checkpoint, 3.00/5 waypoints, four independent
  fixes all failed to beat it — full detail in the "Task 2" section
  below, kept as historical record). Checkpoint files deliberately
  deleted from disk; all eval/training history preserved permanently in
  `model/model_weights/registry.jsonl` (`task=waypoint_nav`), queryable
  via `python -m src.weight_manager.checkpoint_manager leaderboard waypoint_nav
  mean_waypoints_reached` even though the weights themselves are gone.

**New tooling since 2026-08-13**, not reflected anywhere below except
here: `src/model_registry.py` (content-hash-addressed, append-only,
multi-task) and `src/checkpoint_manager.py` (leaderboard/backfill/
promote/archive/retire-task CLI built on top of it) now exist and are the
standard way to pick a "champion" checkpoint for any task — see their own
docstrings, not reproduced here.

Full system architecture (unchanged, still the long-term target) is in
`docs/architecture/Architecture.md` — PX4 flight stack + ROS 2 / uXRCE-DDS.
That document describes the eventual deployed system, not what this repo
currently builds.

## The two-repo split (critical context)

- **`AGERE`** (this repo) — model building only. **PyBullet + Gymnasium
  only. No PX4, no MAVSDK, no network dependency, at all.** This is where
  the RL policy gets trained and iterated on.
- **`AGERE_sims`** — a separate repo. PX4 + Gazebo SITL lives here
  exclusively. This is where a trained model eventually gets plugged in
  and tested against the real flight stack.

**Why:** early sessions tried training directly against PX4 SITL +
Gazebo + MAVSDK. This turned into extensive networking/infra debugging
that had nothing to do with learning RL or building the model. Decision:
fully decouple model development from flight-stack integration. See
`docs/devlog/2026_07_30.md` for the full reasoning.

**Note on sim-to-real (added 2026-08-08):** training observations
(`pos_error`, `velocity`, `roll/pitch/yaw_error`) are a state
representation, not a sensor reading — in PyBullet they come straight
from ground-truth physics; in real deployment the same 9-dim vector
would come from a state estimator (PX4's EKF fusing IMU + GPS/optical
flow/mocap). The policy only ever sees whatever produces that vector, so
this should transfer without retraining as long as the real estimator's
frame/units match. What training here does NOT cover: estimator noise,
latency, or drift, since sim state is noiseless and instantaneous — a
policy that's only seen clean state can be more sensitive to real
estimator noise than expected. That gap is `AGERE_sims`'/Stage 4's
problem, not something to solve here, but worth knowing about ahead of
time rather than being surprised by it at that stage.

## Simulation framework

Training runs against
[`gym-pybullet-drones`](https://github.com/learnsyslab/gym-pybullet-drones)
— in-process PyBullet physics, no network, no SITL. Built on top of their
`HoverAviary` class as the physics engine (via composition, not
inheritance — see code structure below). Key facts about this dependency
(established by reading its source): `ActionType.VEL` = direction vector
+ speed magnitude, PID-controlled internally, **no yaw-rate control**;
`ObservationType.KIN` = 12-dim kinematic state; `BaseAviary._housekeeping()`
reads `INIT_XYZS`/`INIT_RPYS` fresh on every `reset()`, which is how
per-episode start randomization is implemented for both tasks.

## Code structure (`src/`)

Full rationale in `docs/code-structure.md`. **Diagram below is
2026-08-09-vintage and incomplete as of 2026-08-16** — additions since
then, not reflected in the tree below:
- `src/model_registry.py` — content-hash-addressed, multi-task, append-only
- `src/checkpoint_manager.py` — leaderboard/backfill/promote/archive CLI
- `config.py` gained `HoverTaskConfig.disturbance_*`/`recovery_*` fields
  and a module-level `HOVER_STAGE_PRESETS` dict (Stage 1 sub-stage configs,
  shared between `hover_train.py` and `hover_evaluate.py`)
- `paths.py`'s `hover_stabilize_model_path()` gained an optional `tag`
  param so curriculum sub-stage checkpoints don't clobber the canonical
  path
- `hover_train.py` gained `--init-from`, `--stage`, `--tag`,
  `--checkpoint-every` (previously had none of these)
- `hover_gym_wrapper.py` gained kick-injection + recovery-tracking state
- `hover_evaluate.py` gained `--stage` and a disturbance-recovery report
- A short-lived `PrecisionFlightTaskConfig` + its train/eval/wrapper files
  (added 2026-08-11) were built, trained against, then judged not worth
  keeping and fully removed 2026-08-16 — not reflected below since they no
  longer exist; mentioned only so their absence isn't mysterious if
  anything still references them

```
src/
├── config.py                       SimConfig, HoverTaskConfig,
│                                    WaypointTaskConfig, PPOConfig,
│                                    waypoint_ppo_config() [NEW 2026-08-08],
│                                    ProjectConfig (task: Hover | Waypoint)
├── actions/velocity_action.py      Shared by both tasks, unchanged
├── environments/drone_sim.py       Shared by both tasks. DroneSim — pure
│                                    PyBullet, no Gymnasium. Gained
│                                    color/radius params on
│                                    draw_target_marker() for waypoint
│                                    marker differentiation.
├── models/networks.py              Still empty/placeholder
├── policies/ppo_policy.py          Shared by both tasks, unchanged
└── training/
    ├── hover_train.py              Hover entry point
    ├── waypoint_train.py           Waypoint entry point — has an extra
    │                                --init-from flag hover_train.py
    │                                doesn't, to warm-start from an
    │                                existing checkpoint (see below).
    │                                CHANGED 2026-08-08: uses
    │                                waypoint_ppo_config(), explicitly
    │                                overrides gamma/ent_coef on a
    │                                warm-started model (PPO.load()
    │                                otherwise silently ignores
    │                                config.ppo), and archives a
    │                                timestamped copy of every save.
    ├── gym_wrapper/
    │   ├── hover_gym_wrapper.py    HoverGymEnv, 9-dim obs
    │   └── waypoint_gym_wrapper.py WaypointGymEnv, ALSO 9-dim obs
    │                                (deliberately shape-identical to
    │                                hover's — see "Weight transfer"
    │                                below). CHANGED 2026-08-08: fixed a
    │                                stale-obs bug on intermediate
    │                                waypoint transitions — see "Task 2"
    │                                below.
    ├── evaluate/
    │   ├── hover_evaluate.py
    │   ├── hover_evaluate_disturbance.py
    │   └── waypoint_evaluate.py    CHANGED 2026-08-08: added a per-leg
    │                                "closest approach on the stuck leg"
    │                                report and an unseeded-run warning.
    └── demo/
        ├── hover_demo.py
        └── waypoint_demo.py         KNOWN BROKEN — see "Known issues"
```

### Weight transfer: why waypoint's obs space matches hover's exactly

`WaypointGymEnv` was originally drafted with a 10th observation dimension
(a `landing_phase` flag) that hover's env doesn't have. This was dropped
once weight transfer became the plan: SB3's `PPO.load()` rebuilds a
policy's input layer from the saved observation shape, so a 9-vs-10
mismatch would make a hover checkpoint unloadable into the waypoint env.
Since the hover-trained policy already knows "minimize position error,
don't move too fast" — most of what waypoint-following needs — that was
judged more valuable than explicit phase-awareness. The landing phase is
still tracked internally (`WaypointGymEnv._in_landing`) for reward and
termination logic; it's just not a dedicated input to the policy.

This is why `waypoint_train.py --init-from <hover checkpoint>.zip` works
at all — see `docs/decisions/devlog/2026_08_06.md` for the full reasoning
and `docs/training-log.md`'s waypoint section for the run this produced.

**IMPORTANT caveat added 2026-08-08:** `PPO.load()` restores
hyperparameters (gamma, ent_coef, learning_rate, etc.) from the
checkpoint file itself, **not** from whatever `PPOConfig`/`ProjectConfig`
is passed alongside it. This means any hyperparameter change made in
`config.py` has **no effect on a warm-started run** unless the training
script explicitly re-applies it to the loaded model after `PPO.load()`.
This is exactly what caused the entropy-runaway bug to go unnoticed for
two full training runs (see "Task 2" below) — the fix wasn't just
changing the config value, it was making sure it actually reached the
warm-started model at all. `waypoint_train.py` now does this explicitly;
keep that pattern for any future hyperparameter change on a warm-started
run.

## Model / log directory layout (as of 2026-08-08)

- `model/model_weights/` — **one flat directory for all tasks.** Tasks
  are told apart by filename prefix (`hover_stabilize_ppo*.zip` vs.
  `waypoint_nav_ppo*.zip`), not by subdirectory.
- `model/model_weights/history/` — every `waypoint_train.py` run also
  archives a timestamped copy here (`waypoint_nav_ppo_seed0_<YYYYMMDD_HHMMSS>.zip`),
  in addition to overwriting the standard path. Added after discovering
  that three separate training runs on 2026-08-06/07 had all silently
  overwritten the same `waypoint_nav_ppo_seed0.zip`, with no way to
  know which run's weights actually ended up on disk except
  cross-referencing `tb_logs` wall-clock timestamps against the file's
  mtime after the fact.
- `model/model_weights/checkpoints/` — **NEW 2026-08-09.** When
  `--checkpoint-every N` is passed to `waypoint_train.py`, intermediate
  checkpoints save here (`<name>_<step>_steps.zip`) during the run, not
  just at the end. Added after finding `ep_rew_mean` can keep improving
  for hundreds of k of steps past the point where eval waypoints-reached
  peaks and starts declining — without this, a long run only gives a
  start point and an end point, with no way to check where in between
  the real task metric was actually best.
- `tb_logs/hover_logs/`, `tb_logs/waypoint_logs/` — **still split per
  task** (unlike the flat model dir) since TensorBoard runs are compared
  within a task, not across tasks.
- `src/paths.py` is the single source of truth for both — never
  hardcode a save/load path elsewhere.

---

## Task 1: Hover/Stabilize — COMPLETE, PAUSED

### Definition of done (full detail in `docs/hover-model-plan.md`)

Staged, not binary:
- **Stage 0** — pipeline sanity
- **Stage 1** — learning signal present
- **Stage 2** — usable/viable baseline: mean final position error < 0.3 m,
  crash rate < 10%, over 20 eval episodes
- **Stage 3** — robust hover: same criteria hold across 3+ random seeds,
  position error < 0.1 m, recovers from mid-episode disturbance
- **Stage 4** — transplant-ready (belongs to `AGERE_sims`, out of scope here)

### Status: **Stage 3 fully complete** (as of 2026-08-02)

All three criteria met:

| Seed | Mean pos error | Crash rate | Notes |
|---|---|---|---|
| 0 | 0.025 m | 5% (1/20) | tilt crash, episode 14 — start condition unremarkable |
| 1 | 0.015 m | 0% | clean, best result to date |
| 2 | 0.018 m | 0% | clean |

Criterion 3 (disturbance recovery) also built and passing this session —
`hover_evaluate_disturbance.py`, velocity-kick mechanism, 0.2 m/s tested
across seeds, all recovered within the configured window.

**Decision (2026-08-06):** rather than continue polishing hover
(diminishing returns, criteria already comfortably cleared), paused here
to spend the remaining demo-prep time on waypoint navigation + landing —
see `docs/planning/stage3-push-plan.md` for the scoping call and
`docs/decisions/devlog/2026_08_06.md` for the session this pivot happened in.

Full run details in `docs/training-log.md`'s hover section (runs
`2026-07-31-0` through `2026-08-02-0`).

---

## Task 2: Waypoint Navigation + Landing — IN PROGRESS

### Scope (demo, not full campaign)

- 4-6 waypoints in sequence (currently 5, see `WaypointTaskConfig` in
  `config.py`), then a soft landing (touchdown velocity ≤ 0.15 m/s, held
  ~2s)
- Success bar: **one seed with a consistently good success rate
  (~15/20+)**, not hover's three-seed robustness requirement
- Timeline: design → sanity run → real run → landing-specific tuning →
  full run → eval/demo → buffer

### Status: 802,816-step checkpoint confirmed as current best; three
### more levers tested and ruled out; potential-based progress shaping
### written, reviewed, and ready to test (as of 2026-08-09)

All pipeline pieces exist and run end-to-end: `WaypointTaskConfig`,
`WaypointGymEnv`, `waypoint_train.py` (with `--init-from` warm-start and,
as of today, `--checkpoint-every`), `waypoint_evaluate.py` (with, as of
today, `--episode-len-sec`). `waypoint_demo.py` is still the one broken
piece — see Known Issues.

**Data-integrity issue found (2026-08-07), fixed 2026-08-08:** the
"first real training run" reported on 2026-08-06 was actually run
**twice** (byte-identical, since `--init-from` reproduces exactly given
the same checkpoint's RNG state), plus a third interrupted attempt in
between — invisible from the devlog at the time. `waypoint_train.py` now
archives a timestamped copy of every save under
`model/model_weights/history/`.

**Root-cause diagnosis (2026-08-07/08) — entropy runaway, not
undertraining:** the original 300k-step run peaked at step ~729k then
*declined*; `train/std` climbed monotonically (0.85→1.18) instead of
converging. Diagnosis: `ent_coef=0.01` (inherited from hover) applied a
constant entropy pull that hover's stronger gradient could override but
waypoint's weaker one couldn't. **Fix:** `config.waypoint_ppo_config()`
(`gamma=0.995, ent_coef=0.003`), applied via an explicit post-`PPO.load()`
override in `waypoint_train.py` (`PPO.load()` otherwise silently ignores
`config.ppo` — see the IMPORTANT caveat above). Also raised
`waypoint_bonus` 5.0→15.0 in the same experiment. **Result:** `std`
stayed flat (0.81–0.89), `ep_rew_mean` still climbing at cutoff
(-247.6). This checkpoint, at **802,816 cumulative steps**, is referred
to below as "the baseline" — archived at
`model/model_weights/history/waypoint_nav_ppo_seed0_20260808_202404.zip`.

**Second bug found (2026-08-08) — stale obs on intermediate waypoint
transitions:** `waypoint_evaluate.py`'s new per-leg diagnostic initially
reported impossible closest-approach values (episodes 1.4m from target
reporting ~0.148m). Root cause: `WaypointGymEnv.step()` only re-derived
`obs` on the transition *into landing*, not on intermediate transitions
(1→2, 2→3, 3→4) — same staleness the code already handled for landing,
never generalized. **Fixed** — any `waypoint_bonus > 0` now re-derives
`obs`. Clean re-read after the fix: mean closest approach on the stuck
leg = 0.850m, min 0.184m, **0/20 ever within `waypoint_reach_radius`
(0.15m) — reach radius definitively ruled out as the bottleneck.**

**Baseline numbers (802,816-step checkpoint, `--seed 42`, 20 episodes):**
Success 0.0% | Mean waypoints reached **3.00/5** | Crash rate 0.0% |
Mean reward -292.6 | 20/20 timeout, 0/20 ever reached landing.
**Confirmed robust across eval seeds** (2026-08-09): 3.00, 3.00, 2.95,
2.70 across seeds 42/7/100/123 — a real property of this checkpoint, not
a lucky draw.

**Velocity-penalty experiment (2026-08-08/09) — tried and reverted, with
a real finding:** lowered `velocity_penalty_weight` 0.05→0.02 to test
whether it was suppressing commitment to travel across 1-1.5m gaps.
Trained 300k more from the baseline. Result: waypoints-reached **dropped**
to 1.35/5 despite a healthy, normally-adapting training curve (`std` flat
0.80–0.83, no instability) — ruling out "needed more steps to adapt."
The stuck-leg diagnostic showed why: episodes stalled **closer** to
target on average (0.271m vs. baseline's 0.850m) but still failed to
durably enter the 0.15m radius, mostly on early/short legs. **Reading:
the penalty's real job wasn't suppressing travel, it was forcing
deceleration/stabilization precisely at each target** — removing it made
the drone faster but less precise, and precision mattered more than
speed for actually completing legs. **Reverted to 0.05.** Do not
re-lower without new evidence pointing the other way.

**Checkpoint sweep (2026-08-09) — the 802,816-step checkpoint is a real
local optimum, not just an undertrained point on a still-rising curve:**
continued training from the baseline for 300k more steps (reverted
0.05 config), this time with `--checkpoint-every 50000`. Every one of
the six resulting checkpoints was worse than the baseline:

| Cumulative steps | Waypoints reached |
|---|---|
| 802,816 (baseline) | **3.00** |
| 852,816 | 2.15 |
| 902,816 | 1.90 |
| 952,816 | 1.75 |
| 1,002,816 | 1.45 |
| 1,052,816 | 2.15 |
| 1,102,816 | 1.40 |

Noisy (1,052,816 partially recovers before dropping again), but never
back to 3.00. Combined with the velocity-penalty experiment (also worse,
also from the same baseline), **"just keep training from here" is now
closed off as a strategy** — three separate continuations from 802,816,
two different reward configs, all worse. `waypoint_nav_ppo_seed0.zip`
has been restored to the 802,816-step baseline; do not train further
from a later checkpoint without a structural change first.

**Episode-length test (2026-08-09) — budget ruled out:** added
`--episode-len-sec` to `waypoint_evaluate.py` to test, at zero training
cost, whether the 600-step/20s budget was the real constraint (policy
behavior doesn't change, only when timeout fires). Baseline checkpoint,
30s: 2.80/5. 40s: 2.75/5. **No improvement — if anything slightly worse.**
Several episodes at 40s still showed 4/5 waypoints with ~1.3-1.5m final
error, meaning no further progress was made even with 20 extra seconds.
Budget-limited is ruled out; the policy is genuinely stuck, not merely
out of time.

**Potential-based progress shaping — written, reviewed, one bug caught
before running (2026-08-09):** with three magnitude-tweak levers and one
budget test all exhausted, added a structurally different term: reward
now includes `progress_shaping_weight * (distance closed this step)`
(Ng, Harada & Russell 1999-style potential-based shaping), directly
rewarding closing distance rather than only penalizing absolute distance
— addresses the actual finding (dense reward improving while task
completion doesn't) rather than another weight guess. Reviewed and
confirmed correct: cliff-avoidance at waypoint transitions is handled
properly (both sides of the delta measured against the same
pre-transition target; the *next* step's baseline uses the
post-transition distance), and the first-step-after-reset case is seeded
correctly (no spurious jump). **One real issue caught before any training
run used it:** a magnitude check showed this term is roughly comparable
to, not clearly dominated by, `landing_velocity_penalty_weight`'s safety
penalty at unsafe descent speeds (~+0.33/step vs. ~-0.3/step at 1.0 m/s
descent) — a real bias toward rushing the touchdown, in a phase no
episode has ever reached, so there was no prior run to catch it. **Fixed**
by disabling this term during `self._in_landing` before any run used it —
a design correction, not an observed failure. `progress_shaping_weight
=10.0` for the route phase is otherwise untested in practice; the
single most uncertain number in the system right now.

**Not yet run:** the actual training run with progress shaping enabled.
This is tomorrow's first step.

### Open items (waypoint_nav) — HISTORICAL, task retired 2026-08-16

Kept for the record; no longer actionable since the task is retired and
its checkpoint weights are deleted (see "What this project is" at top).

- `waypoint_reach_radius=0.15` — settled, not revisited.
- `velocity_penalty_weight=0.05` — settled, not revisited.
- Episode budget (`episode_len_sec=20`) — ruled out as the bottleneck,
  not revisited.
- `progress_shaping_weight=10.0` — **never actually run.** The
  2026-08-09 session ended with this written, reviewed, and one bug
  caught before any run used it (see below) — the run itself never
  happened before the retirement decision. If waypoint nav is ever
  revived, this experiment is still the logical next step, not a dead
  end.
- Landing phase — never once exercised in any run across the task's
  entire history. Real PyBullet contact-based "success" was never
  implemented or tested.
- `waypoint_demo.py` — was broken (duplicate of `waypoint_evaluate.py`),
  never fixed. Moot now.

### Current open items (hover, active as of 2026-08-25)

**Superseded, for context:** the 1a/1b/1c/... sub-stage roadmap below
this section (and in `hover-robustness-curriculum-plan.md`) was replaced
2026-08-25 by a 3-type/5-level scoped design (kick/torque/wind x 5
magnitude levels, one event/episode, trained together rather than
staged) — see `docs/architecture/hover-disturbance-3x5-design.md` and
`training-log.md`'s 2026-08-25 entries for the full history. The 1a
null-result finding directly motivated that redesign. Takeoff/landing
are scripted, not learned, and explicitly out of scope for this push.

- **Two training runs (`disturbance_3x5`, then +ent_coef/gamma fix)
  plateaued at ~37% crash rate; root cause turned out to be the crash
  criterion itself, not the policy.** `max_tilt_rad` was checked with
  zero hold-time — a momentary corrective tilt (e.g. redirecting thrust
  to arrest a kick) was scored identically to genuine loss of control.
  Diagnostic (`hover_tilt_diagnostic.py`) found 68% of tilt-truncated
  episodes recovered cleanly when just given room to keep flying. Fixed
  via `max_tilt_hold_steps` (sustained-hold check, mirroring
  `recovery_hold_steps`'s existing non-momentary-touch pattern). Crash
  rate on the same checkpoint dropped from ~37% to 23% from the fix
  alone, before any retraining.
- **`max_tilt_hold_steps=6` is a first guess, not independently
  validated** the way the magnitude levels were — worth its own
  diagnostic pass (rerun `hover_tilt_diagnostic.py` against a current
  checkpoint) if crash numbers look off in either direction later.
- **Torque and wind's magnitude level bounds are unvalidated
  estimates** (wind scaled against hover thrust, torque has no
  real-world reference at all) — kick's floor was corrected once
  already (1a's 0.1–0.3 m/s confirmed too weak); torque/wind haven't
  been checked the same way yet. Wind turned out fine empirically
  (0% crash, 100% recovery all 5 levels once its own timing bug was
  fixed) but that's not the same as the magnitude scale being right —
  it may just mean wind is comfortably within the recoverable envelope
  at every level tested.
- **Training is still actively improving as of the last two runs**
  (`disturbance_3x5_tiltfix`, `disturbance_3x5_tiltfix2` — +5.6pp and
  +3.3pp per the checkpoint-sweep tool's trailing-window comparison),
  crash rate now ~18–23%, still short of the <10% mastery gate. Wind
  and torque L1–L3 are fully mastered (0% crash); kick L3–L5 and torque
  L4–L5 remain the open problem.
- **A late-episode instability pattern in kick specifically**: several
  crashing episodes show excellent recovery (position error near zero)
  followed by a NEW tilt excursion many steps later, with no further
  disturbance event in that episode. Looks like a separate
  marginal-stability issue distinct from initial-kick recovery — not
  yet investigated (candidate next thread once the current training
  line plateaus for real).
- **Parallel training (`--n-envs`, `SubprocVecEnv`) is now available**
  in `hover_train.py` — ~2600 fps at `--n-envs 6` vs. single-process.
  GPU was investigated and deliberately NOT adopted (PyBullet stepping
  in a single process, not GPU compute, is this workload's actual
  bottleneck for a network this small).
- **A checkpoint-sweep tool exists**
  (`src/training/evaluate/hover_checkpoint_sweep.py`) to measure
  whether a run is still improving or has plateaued from actual
  task-performance numbers, before committing to further training —
  used to catch both plateaus above rather than guessing from
  `train/std`/`approx_kl` alone.
- Two still-unexplained crash-rate blips from before this session
  remain unresolved and are now lower priority: Stage 0's 250k–350k
  window (overcorrection hypothesis tested and **refuted**, mechanism
  still unknown — Theory 2026-08-16-0/1) and 1a's 300k checkpoint blip
  (likely noise, not confirmed — `--seed 7` rerun still not done, and
  now moot given 1a's own checkpoints were never promoted).
- A hover demo script exists (`src/training/demo/hover_demo.py`) but
  hasn't been reviewed or extended to show disturbance-recovery
  behavior — still not started.
- `hover_evaluate.py`'s `--stage` flag is required to see any
  disturbance behavior at all; omitting it silently evaluates as if
  undisturbed regardless of how the model was trained — still easy to
  forget, worth double-checking on any future eval command.
- `checkpoint_manager.py`'s `backfill` command still doesn't know about
  `--stage` — not fixed, same gap as before.

### Next action

1. Continue the `disturbance_3x5_tiltfix2` training line while it's
   still improving per the checkpoint sweep (+3.3pp on the last check) —
   `--init-from` its final checkpoint, same `--n-envs 6`, sweep again
   after ~300k steps before committing to the full run.
2. Watch specifically for: (a) whether kick keeps closing the gap or
   stalls again, (b) whether torque (currently flat/noisy, 17–39%
   across the last full run) starts moving or becomes the new
   bottleneck once kick catches up.
3. Once this line plateaus for real (checkpoint sweep says so, not a
   guess), investigate the late-episode kick instability pattern above
   rather than immediately reaching for another hyperparameter change —
   two hyperparameter-only attempts already failed to fix what turned
   out to be a criterion bug; don't repeat that pattern on a genuinely
   different problem without checking first.
4. Validate `max_tilt_hold_steps=6` and the torque/wind magnitude
   tables with their own diagnostic passes, same discipline already
   applied to kick and to the tilt criterion itself — not yet done.
5. Pick an eval-based champion from checkpoints once this line is
   considered done, not the final save automatically — final save has
   not been the best checkpoint in any run so far in this project.

---

## Known issues / environment gotchas (both tasks)

- **`setuptools>=82` breaks `gym-pybullet-drones`.** Pin
  `setuptools<82` in `environment.yml`.
- **`device="cpu"` is set in `ppo_policy.py`** and passed explicitly at
  eval/demo load time too — confirmed present, no action needed.
- Runtime verification of new code in this project has generally been
  done by the project owner locally, not by whichever LLM wrote the
  code — code gets syntax-checked and logic-traced against source before
  handoff, then run and iterated on with real results. This has held for
  all waypoint-task code changes through 2026-08-08.
- `--init-from`'s `total_timesteps` counter in SB3's training-log
  printout is cumulative from the loaded checkpoint's own history
  (`reset_num_timesteps=False`), not a fresh count for the current run —
  don't misread large printed step counts as more work having been done
  than actually was.
- **`PPO.load()` ignores `config.ppo`** — see the IMPORTANT caveat under
  "Weight transfer" above. Any future hyperparameter change intended for
  a warm-started run needs an explicit post-load override, or it will
  silently do nothing.

## Other docs in this repo worth reading, in rough priority order

**Current (hover), read these first:**
1. `docs/architecture/hover-disturbance-3x5-design.md` — the ACTIVE
   disturbance design (supersedes the 1a/1b/1c/... roadmap in the doc
   below for anything past 2026-08-25): 3 types x 5 levels, scoping
   rationale, what's validated vs. still a guess.
2. `docs/planning/hover-robustness-curriculum-plan.md` — original plan;
   still useful for the disturbance taxonomy and Stage 0's history, but
   its sub-stage roadmap (1a onward) is superseded — see doc above.
3. `docs/research/theory-log.md` — dated hypothesis/interpretation log,
   companion to training-log.md's raw results
4. `docs/training-log.md` — living log; hover entries from 2026-08-16
   onward are current, everything before that predates the from-scratch
   retrain and the tooling described above. 2026-08-25 entries cover the
   wind-timing bug, parallel training, the ent_coef/gamma dead end, and
   the tilt-criterion fix that actually unblocked training — read that
   whole sequence before assuming another hyperparameter tweak is the
   answer to a plateau.
5. `src/training/evaluate/hover_checkpoint_sweep.py` — measures whether
   a run is still improving or has plateaued from real eval numbers
   across a run's own checkpoints; use this before deciding to train
   more OR to stop, rather than guessing from the training printout.
6. `src/training/evaluate/hover_tilt_diagnostic.py` — checks whether a
   "crash" was a real loss of control or an artifact of the (now fixed,
   but re-check if it's ever loosened/tightened again) tilt-truncation
   criterion.
7. `src/model_registry.py` / `src/checkpoint_manager.py` — read their
   module docstrings for the champion-selection tooling now used for any
   task

**Historical (waypoint_nav, retired 2026-08-16):**
5. `docs/decisions/devlog/2026_08_09.md` — velocity-penalty test/revert,
   checkpoint sweep confirming the 802,816-step local optimum, episode-
   length test ruling out budget, progress-shaping addition (never run)
6. `docs/decisions/devlog/2026_08_06.md` — waypoint task build + first
   real run + initial diagnosis
7. `docs/code-structure.md` — full reasoning for the src/ layout
   (2026-08-09-vintage, see the note in the code-structure section above
   for what's changed since)
8. `docs/hover-model-plan.md` — original hover task spec + Stage 1–3
   completion criteria (superseded in spirit by the robustness curriculum
   plan for anything past Stage 3, but Stages 1–3's criteria are still
   the ones `hover_evaluate.py` checks)
9. `docs/planning/stage3-push-plan.md` — hover Stage 3 push + the
   original pivot decision to waypoint nav (itself now superseded by the
   pivot back)
10. `docs/devlog/2026_07_30.md` — the AGERE/AGERE_sims split decision
11. `docs/architecture/Architecture.md` — long-term system architecture (PX4/ROS2)
