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
    │                                existing checkpoint (see below)
    ├── gym_wrapper/
    │   ├── hover_gym_wrapper.py    HoverGymEnv, 9-dim obs
    │   └── waypoint_gym_wrapper.py WaypointGymEnv, ALSO 9-dim obs
    │                                (deliberately shape-identical to
    │                                hover's — see "Weight transfer" below)
    ├── evaluate/
    │   ├── hover_evaluate.py
    │   ├── hover_evaluate_disturbance.py
    │   └── waypoint_evaluate.py
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

## Model / log directory layout (as of 2026-08-06)

- `model/model_weights/` — **one flat directory for all tasks.** Tasks
  are told apart by filename prefix (`hover_stabilize_ppo*.zip` vs.
  `waypoint_nav_ppo*.zip`), not by subdirectory. This replaced an earlier
  one-subdirectory-per-task layout.
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

### Status: pipeline built and running; policy not yet converging on
### full-route completion (as of 2026-08-06)

All pipeline pieces exist and run end-to-end: `WaypointTaskConfig`,
`WaypointGymEnv`, `waypoint_train.py` (with `--init-from` warm-start),
`waypoint_evaluate.py`. `waypoint_demo.py` is the one broken piece — see
Known Issues.

**First real training run** (300k timesteps, warm-started from
`hover_stabilize_ppo_seed0.zip`, saved as `waypoint_nav_ppo_seed0.zip`) —
eval results, 20 episodes:

| Metric | Result |
|---|---|
| Success rate | 0.0% |
| Mean waypoints reached | 2.05 / 5 |
| Crash rate | **0.0%** |
| Failure breakdown | 20/20 timeout; 0/20 ever reached landing phase |

**Read on this:** the good sign is zero crashes — stability transferred
cleanly from the hover warm-start. The expected-at-this-stage part is
that it never finishes the route: every failure is a plain timeout, none
made it as far as attempting a landing. This points at a
progress/pacing issue (not committing to closing 1-2m gaps between
waypoints quickly enough within the 600-step/20s budget), not a control
issue. Full diagnosis and next-step plan in
`docs/decisions/devlog/2026_08_06.md`; run details in
`docs/training-log.md`'s waypoint section.

### Open items

- `waypoint_bonus=5.0` — untuned guess, still untested in practice since
  no episode has progressed far enough for it to matter much yet.
- Landing "success" is altitude+velocity-based, not real PyBullet contact
  detection — a deliberate scope simplification for the demo, untested
  in practice so far since nothing has reached the landing phase.
- **`waypoint_demo.py` is broken** — currently a byte-for-byte duplicate
  of `waypoint_evaluate.py` (looks like a copy-paste-and-forget-to-replace
  mistake from an earlier session). No live-GUI/real-time-paced/colored-
  marker demo script actually exists yet. Not urgent while there's no
  policy worth demoing, but needs real writing before the demo date.
  Also flagged from before: whenever it does get written, it'll need to
  reach into `WaypointGymEnv`'s private `_waypoints`/`_waypoint_idx` for
  marker drawing — works, but not a clean public interface.
- Policy not yet reliably finishing the waypoint route — see status
  table above. Not diagnosed further than "probably needs more
  fine-tuning timesteps, possibly a pacing/episode-length check" as of
  today; see devlog for the concrete next-step plan.

### Next action

Per `docs/decisions/devlog/2026_08_06.md`: check the full `ep_rew_mean`
curve in `tb_logs/waypoint_logs` for today's run (only the final
iteration's numbers were captured in the log so far), then most likely
continue fine-tuning from `waypoint_nav_ppo_seed0.zip` for another few
hundred k steps before touching any reward weights.

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
  the waypoint-task code added 2026-08-06 as well.
- `--init-from`'s `total_timesteps` counter in SB3's training-log
  printout is cumulative from the loaded checkpoint's own history
  (`reset_num_timesteps=False`), not a fresh count for the current run —
  don't misread large printed step counts as more work having been done
  than actually was.

## Other docs in this repo worth reading, in rough priority order

1. `docs/decisions/devlog/2026_08_06.md` — most recent session, waypoint
   task build + first real run + diagnosis
2. `docs/code-structure.md` — full reasoning for the src/ layout above
3. `docs/hover-model-plan.md` — hover task spec + staged completion criteria
4. `docs/planning/stage3-push-plan.md` — hover Stage 3 push + the pivot
   decision to waypoint nav
5. `docs/training-log.md` — living log, one entry per training run, both tasks
6. `docs/devlog/2026_07_30.md` — the AGERE/AGERE_sims split decision
7. `docs/architecture/Architecture.md` — long-term system architecture (PX4/ROS2)
