# AGERE Project — Status / Context Handoff

**Purpose of this file:** give a new LLM chat (or another person) full
context on this project in one read, without needing the prior
conversation history. If you're an LLM reading this cold: this is a
real, ongoing project with real training runs already completed — treat
stated results as ground truth, not as something to re-derive from
scratch.

## What this project is

Reinforcement learning for a multirotor drone, part of a larger project
called **Agere** / **Backseat Driver**. Task 1, **hover/stabilize**, is
complete (Stage 3 met, see below) and paused. Current focus is task 2,
**waypoint navigation + landing**, scoped for a professor demo rather
than a full multi-stage campaign — see "Current task" below.

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

Full rationale in `docs/code-structure.md`. Both tasks now exist
side by side under the same split (simulation vs. training):

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

### Open items

- `waypoint_reach_radius=0.15` — **settled. Do not change based on eval
  data from before 2026-08-08 (the stale-obs bugfix).**
- `velocity_penalty_weight=0.05` — **settled for now, tested and
  reverted with a real mechanistic finding (see above). Don't re-lower
  without new evidence.**
- Episode budget (`episode_len_sec=20`) — **settled, ruled out as the
  bottleneck (see episode-length test above). Don't extend it expecting
  this alone to help.**
- `progress_shaping_weight=10.0` — new, untested in an actual training
  run. First thing to retune if the resulting behavior looks wrong (e.g.
  reckless straight-line rushing showing up as more crashes than the 0%
  seen in every run to date).
- `waypoint_bonus=15.0` — still not isolated from the ent_coef/gamma fix
  it was bundled with; lower priority to unbundle now given other
  findings since.
- **`ep_rew_mean` is not a reliable proxy for waypoints-reached past the
  802,816-step checkpoint** — two different 300k-step continuations both
  improved training AND eval reward while waypoints-reached got worse.
  Any future long run should use `--checkpoint-every` and be evaluated
  at intermediate points, not trusted from the final checkpoint or the
  TensorBoard curve alone.
- Landing "success" is still altitude+velocity-based, not real PyBullet
  contact detection — still untested in practice, since no episode has
  reached the landing phase yet. Progress shaping is now explicitly
  disabled during landing (see above) precisely because this phase is
  still completely unexercised.
- **`waypoint_demo.py` is broken** — still a byte-for-byte duplicate of
  `waypoint_evaluate.py`. Not touched this session; not urgent while
  there's no policy worth demoing yet.
- **Cosmetic, low-priority:** `docs/decisions/devlog/2026_08_06.md` and
  `docs/decisions/devlog/devlog_2026_08_06.md` are byte-identical
  duplicate files. Harmless, worth deleting one when convenient.
- Eval reproducibility — `waypoint_evaluate.py` warns when `--seed` is
  omitted. Always pass it for anything meant to be compared later.

### Next action

Run the progress-shaping experiment tomorrow, from the restored
802,816-step baseline, with `--checkpoint-every 50000` from the start
(not added after the fact this time):
```
python -m src.training.waypoint_train --init-from model/model_weights/waypoint_nav_ppo_seed0.zip --timesteps 300000 --seed 0 --checkpoint-every 50000
```
Sweep all 6 checkpoints against `--seed 42` rather than trusting the
final one — given the `ep_rew_mean`-vs-waypoints-reached divergence
found today, this is no longer optional. Watch specifically: (1) whether
any episode finally reaches the landing phase at all — new information
this task has never produced; (2) if one does, whether `hard_landing`
stays at 0% in the crash breakdown, which would confirm the landing-phase
exclusion fix was worth making; (3) `train/std` stays flat, confirming
nothing about this change reopens the entropy-runaway issue.

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

1. `docs/decisions/devlog/2026_08_09.md` — today's session: velocity-
   penalty test/revert, checkpoint sweep confirming the 802,816-step
   local optimum, episode-length test ruling out budget, progress-shaping
   addition + landing-phase fix
2. `docs/training-log.md` — living log, one entry per training run, both
   tasks; see the 2026-08-08/09 waypoint entries for full run-by-run
   detail behind this file's summary
3. `docs/decisions/devlog/2026_08_06.md` — waypoint task build + first
   real run + initial diagnosis (superseded in part — the "needs more
   timesteps" conclusion there turned out to be premature; see "Task 2"
   above for why)
4. `docs/code-structure.md` — full reasoning for the src/ layout above
5. `docs/hover-model-plan.md` — hover task spec + staged completion criteria
6. `docs/planning/stage3-push-plan.md` — hover Stage 3 push + the pivot
   decision to waypoint nav
7. `docs/devlog/2026_07_30.md` — the AGERE/AGERE_sims split decision
8. `docs/architecture/Architecture.md` — long-term system architecture (PX4/ROS2)
