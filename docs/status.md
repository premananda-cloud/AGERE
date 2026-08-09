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
- `model/model_weights/history/` — **NEW 2026-08-08.** Every
  `waypoint_train.py` run now also archives a timestamped copy here
  (`waypoint_nav_ppo_seed0_<YYYYMMDD_HHMMSS>.zip`), in addition to
  overwriting the standard path. Added after discovering (see "Task 2")
  that three separate training runs on 2026-08-06/07 had all silently
  overwritten the same `waypoint_nav_ppo_seed0.zip`, with no way to
  know which run's weights actually ended up on disk except
  cross-referencing `tb_logs` wall-clock timestamps against the file's
  mtime after the fact. `hover_train.py` doesn't have this problem the
  same way since Stage 3's multi-seed requirement already forces
  distinct filenames per seed — this was waypoint-specific because
  repeated `--init-from` reruns against the same nominal seed all
  resolve to the same save path.
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

### Status: two real bugs found and fixed, one hyperparameter cause
### diagnosed and corrected; route completion improving but not yet
### converged (as of 2026-08-08)

All pipeline pieces exist and run end-to-end: `WaypointTaskConfig`,
`WaypointGymEnv`, `waypoint_train.py` (with `--init-from` warm-start),
`waypoint_evaluate.py`. `waypoint_demo.py` is still the one broken piece
— see Known Issues.

**Data-integrity issue found (2026-08-07):** cross-referencing `tb_logs`
event files against their wall-clock timestamps showed the "first real
training run" reported on 2026-08-06 was actually run **twice** (two
byte-identical 300k-step curves, confirmed reproducible because
`--init-from` inherits the loaded checkpoint's own RNG state and PyBullet
is deterministic given that state), plus a third, interrupted attempt
(~188k of 300k steps) in between — none of this was visible from the
devlog, which described it as a single run. Since `waypoint_train.py`
saved to a fixed path with no run-id, it was only possible to determine
which run's weights ended up on disk by comparing file mtimes against
`tb_logs` timestamps. **Fixed 2026-08-08** — see "Model / log directory
layout" above (timestamped archiving).

**Root-cause diagnosis (2026-08-07/08) — entropy runaway, not
undertraining:** the original 300k-step run's `tb_logs` curve showed
`ep_rew_mean` peaking at step ~729k (-274.4) then *declining* for the
remaining ~73k steps (ending at -291.25) — not a plateau, a reversal.
`train/std` climbed monotonically the entire run (0.85 → 1.18),
`entropy_loss` grew steadily more negative, while `approx_kl`,
`clip_fraction`, and `explained_variance` all stayed in healthy ranges —
ruling out PPO instability or a bad value function. Diagnosis: PPO's
`ent_coef` (0.01, inherited unchanged from hover's `PPOConfig`) applies a
constant pull toward higher entropy every update; hover's strong,
unambiguous position-error gradient was enough to override that pull as
the policy converged, but waypoint's gradient is weaker/more
delayed-relative-to-action (`gamma=0.99` gives an effective ~100-step
credit horizon, right at the ~108-step-per-waypoint pace implied by the
episode budget — the one-time `waypoint_bonus` was landing at or past the
edge of what could meaningfully shape earlier approach states), so the
entropy term won by default instead of being overridden. **Fix:** added
`config.waypoint_ppo_config()` (`gamma=0.995, ent_coef=0.003`,
task-specific — NOT applied to hover). Confirmed applying correctly via
an explicit `model.gamma`/`model.ent_coef` override in `waypoint_train.py`
after `PPO.load()` — see the IMPORTANT caveat above; without that
explicit override, this fix would have silently done nothing on any
`--init-from` run. Also raised `waypoint_bonus` 5.0 → 15.0 in the same
experiment (bundled — see config.py's comment on why, and un-bundle if a
future result is ambiguous about which change did what).

**Result after the fix (300k-step rerun, 2026-08-08):** `train/std`
stayed flat in a 0.81–0.89 band the whole run (vs. the old run's
0.85→1.18 climb) and `ep_rew_mean` was **still climbing** at the 300k
cutoff (-247.6, not yet plateaued) — the opposite of the old run's
peak-then-decline shape. This is the first run where "train longer from
here" is actually justified by the curve shape, rather than a hopeful
guess.

**Second bug found (2026-08-08) — stale obs on intermediate waypoint
transitions:** `waypoint_evaluate.py`'s new per-leg "closest approach on
the stuck leg" diagnostic (added this session specifically to settle the
open `waypoint_reach_radius` question) initially reported every
never-finished episode getting within ~0.148m of its stuck target
regardless of actual outcome — including episodes that timed out 1.4m
from the landing target, which is impossible if the number were real.
Root cause: `WaypointGymEnv.step()` only re-derived `obs` after a
transition *into landing*, not after an intermediate waypoint transition
(1→2, 2→3, 3→4) — the exact staleness the code's own existing comment
already described for the landing case, just never generalized to every
case that has it. On any transition step, that step's `obs` (and
therefore its reward and `info["position_error_norm"]`) reflected
distance to the just-passed target, not the new one, and the stale
near-zero value leaked into the next leg's diagnostic bucket. **Fixed**
by dropping the `self._in_landing` condition — any `waypoint_bonus > 0`
now re-derives `obs`. This also means training itself was getting a
(narrow — one step out of ~600 per episode) wrong observation/reward on
every intermediate transition prior to this fix; not expected to be a
major driver of the low completion rate on its own, but real.

**Reach radius — now genuinely settled, not guessed at:** re-running
`waypoint_evaluate.py` against the *existing* trained checkpoint after
the stale-obs fix (no retraining needed — the fix only corrects
evaluation-time bookkeeping) gave a clean read: mean closest approach on
the stuck leg = 0.850 m, min = 0.184 m, max = 1.390 m, **0/20 episodes
ever got within `waypoint_reach_radius` (0.15 m) on their stuck leg.**
Reach radius is definitively not the bottleneck — do not widen it based
on any pre-2026-08-08 eval data, which was reading contaminated values.

**Current numbers (post-fix, `--seed 42`, 20 episodes):**

| Metric | Pre-fix (2026-08-06) | Post-fix (2026-08-08) |
|---|---|---|
| Success rate | 0.0% | 0.0% |
| Mean waypoints reached | 2.05 / 5 | **3.00 / 5** |
| Crash rate | 0.0% | 0.0% |
| Mean episode reward | -218 to -273 (varied, unseeded runs) | -292.6 (seeded) |
| Failure breakdown | 20/20 timeout, 0/20 ever reached landing | 20/20 timeout, 0/20 ever reached landing |

Reward looks worse in the post-fix column than some pre-fix samples, but
those pre-fix numbers came from unseeded eval runs with no fixed episode
sequence (see "Known issues" below) and from a policy that had already
started degrading (see peak-then-decline note above) — they aren't
directly comparable. Waypoints-reached is the more trustworthy
comparison point here, and it improved substantially.

**New structural observation (2026-08-08), not yet confirmed as a real
factor:** 10/20 episodes in the post-fix eval stalled at exactly 4/5
waypoints, with final position errors clustered high (0.98–1.47 m) —
consistently on the wp3→wp4 leg specifically, which at 1.50 m is the
longest single leg in the route (others: wp0→wp1 1.12 m, wp1→wp2 1.12 m,
wp2→wp3 1.22 m). Plausible as either "the hardest leg genuinely needs
more training" (consistent with the curve still climbing) or "this leg
is disproportionately hard, independent of training progress" — not yet
distinguished. Worth checking again after the next training run rather
than acting on now.

### Open items

- `waypoint_reach_radius=0.15` — **settled, see above. Do not change
  based on eval data from before 2026-08-08 (the stale-obs bugfix).**
- `waypoint_bonus` — was 5.0 (untuned guess), raised to 15.0 on
  2026-08-08 alongside the ent_coef/gamma fix (bundled — see config.py).
  Not yet isolated as independently responsible for any of the
  improvement seen; un-bundle if needed.
- `velocity_penalty_weight` — **deliberately left unchanged** (still
  0.05, same as hover) as of 2026-08-08. Was a candidate suspect for
  suppressing committed movement toward distant waypoints, but the
  better-evidenced entropy-runaway finding was addressed first; revisit
  only if the wp3→wp4 pattern above turns out not to resolve with more
  training.
- Landing "success" is still altitude+velocity-based, not real PyBullet
  contact detection — still untested in practice, since no episode has
  reached the landing phase yet.
- **`waypoint_demo.py` is broken** — still a byte-for-byte duplicate of
  `waypoint_evaluate.py`. Not touched this session; not urgent while
  there's no policy worth demoing yet.
- **Cosmetic, low-priority:** `docs/decisions/devlog/2026_08_06.md` and
  `docs/decisions/devlog/devlog_2026_08_06.md` are byte-identical
  duplicate files (same copy-paste-and-forget-to-rename pattern as
  `waypoint_demo.py`). Harmless, but worth deleting one when convenient.
- Eval reproducibility — `waypoint_evaluate.py` only seeds the episode
  sequence if `--seed` is passed explicitly; every eval command run
  2026-08-06/07 omitted it, which is why aggregate numbers varied
  between runs of the *same* checkpoint even before any weights changed.
  The script now prints a warning when `--seed` is omitted. Always pass
  `--seed` for any result meant to be compared against a later run.

### Next action

Both prerequisites for "train more" are now genuinely met, for the first
time this project: the post-fix curve was still climbing at the 300k
cutoff (not peaked-and-declining like the pre-fix run), and the two
other candidate explanations (reach radius, stale-obs corruption) have
been ruled out or fixed rather than left open. Planned next step:
continue training from the current `waypoint_nav_ppo_seed0.zip` for
another few hundred k steps, then re-eval with a fixed `--seed` and check
specifically whether the wp3→wp4 stall pattern above resolves on its own
or persists.

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

1. `docs/training-log.md` — living log, one entry per training run, both
   tasks; see the 2026-08-08 waypoint entries for the full run-by-run
   detail behind this file's summary
2. `docs/decisions/devlog/2026_08_06.md` — waypoint task build + first
   real run + initial diagnosis (superseded in part by the 2026-08-08
   findings above — the "needs more timesteps" conclusion there turned
   out to be premature; see "Task 2" above for why)
3. `docs/code-structure.md` — full reasoning for the src/ layout above
4. `docs/hover-model-plan.md` — hover task spec + staged completion criteria
5. `docs/planning/stage3-push-plan.md` — hover Stage 3 push + the pivot
   decision to waypoint nav
6. `docs/devlog/2026_07_30.md` — the AGERE/AGERE_sims split decision
7. `docs/architecture/Architecture.md` — long-term system architecture (PX4/ROS2)
