# AGERE Project — Status / Context Handoff

**Purpose of this file:** give a new LLM chat (or another person) full
context on this project in one read, without needing the prior
conversation history. If you're an LLM reading this cold: this is a
real, ongoing project with real training runs already completed — treat
stated results as ground truth, not as something to re-derive from
scratch.

## What this project is

Reinforcement learning for a multirotor drone, part of a larger project
called **Agere** / **Backseat Driver**. Currently working on the first
task in a planned sequence: **hover/stabilize** — hold station at a fixed
target point, starting from a randomized nearby position.

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
(WSL2 loopback-vs-real-interface ambiguity, MAVLink broadcast flag
hunting, GPU rendering hacks for Gazebo's GUI) that had nothing to do
with learning RL or building the model. Decision: fully decouple model
development from flight-stack integration. `AGERE` ships a trained model
to `AGERE_sims` for plug-and-test; `AGERE_sims`'s integration problems do
not block or feed back into `AGERE`'s development. See
`docs/devlog/2026_07_30.md` for the full reasoning.

The old PX4/MAVSDK code that used to live in `AGERE` (parked, then later
fully removed) is gone from this repo. If it's needed again, it belongs
in `AGERE_sims`, not here.

## Simulation framework

Training runs against
[`gym-pybullet-drones`](https://github.com/learnsyslab/gym-pybullet-drones)
— in-process PyBullet physics, no network, no SITL. Specifically built on
top of their `HoverAviary` class as the physics engine (used via
composition, not by inheriting its Gym-Env-ness into our own code — see
code structure below).

Key facts about this dependency, established by reading its actual source
(not assumed from memory):
- `ActionType.VEL` (what this project uses) = direction vector + speed
  magnitude, PID-controlled internally via `DSLPIDControl`.
  **No yaw-rate control** — the internal PID always holds whatever yaw
  the drone currently has. Acceptable for pure position-hold; would need
  a different action type if yaw stabilization becomes part of the task.
- `ObservationType.KIN` = 12-dim kinematic state (position, roll/pitch/yaw,
  linear velocity, angular velocity), read via `_getDroneStateVector()`.
- `BaseAviary._housekeeping()` reads `INIT_XYZS`/`INIT_RPYS` fresh on every
  `reset()` call — this is how true per-episode start-position
  randomization was implemented (mutate those arrays before calling the
  parent's `reset()`).
- Installing it (`pip install -e .` or via `git+https://...` in
  `environment.yml`) compiles `pybullet` from source — needs a C compiler.

## Code structure (`src/`)

Full rationale in `docs/code-structure.md`. The organizing principle:
**simulation** (physics facts, doesn't know about RL) is separate from
**training** (RL design choices: reward, spaces, episode logic).

```
src/
├── config.py                    All tunable constants:
│                                   SimConfig       — pyb_freq, ctrl_freq, gui
│                                   HoverTaskConfig — target position, episode
│                                                     length, reset jitter,
│                                                     termination bounds,
│                                                     reward weights
│                                   PPOConfig       — PPO hyperparameters
│
├── actions/velocity_action.py   Defines what a raw 4-vector action MEANS
│                                 physically (direction + speed). No
│                                 gymnasium import, no PX4.
│
├── environments/drone_sim.py    DroneSim: pure PyBullet wrapper around
│                                 gym-pybullet-drones' HoverAviary. No
│                                 reward, no episode logic, no Gymnasium
│                                 spaces exposed at this layer — just
│                                 reset_episode() / apply_action() /
│                                 get_state() / draw_target_marker() /
│                                 close(). NOTE: the underlying HoverAviary
│                                 class IS itself a gymnasium.Env internally
│                                 (that's baked into the third-party
│                                 library) — this wrapper doesn't re-expose
│                                 that, but it's not a from-scratch physics
│                                 implementation either. Known, accepted
│                                 tradeoff, not hidden.
│
├── models/networks.py           Placeholder for custom feature extractors.
│                                 Empty — not needed yet (12-dim obs is
│                                 small). Extension point for later (e.g.
│                                 vision/LiDAR input for obstacle avoidance).
│
├── policies/ppo_policy.py       build_ppo(env, config) — constructs SB3
│                                 PPO. Track-agnostic; only file that knows
│                                 we're using PPO specifically.
│
└── training/
    ├── gym_wrapper.py           HoverGymEnv(gymnasium.Env) — THIS is where
    │                             Gymnasium lives. Action/observation
    │                             spaces, reward function, episode
    │                             termination/truncation logic. Wraps
    │                             DroneSim. step() returns an info dict
    │                             with truncation_reason ("out_of_bounds" /
    │                             "tilt" / "timeout"), is_crash (bool —
    │                             timeout ≠ crash), and position_error_norm.
    ├── train.py                 Entry point: python -m src.training.train
    │                             [--gui] [--timesteps N]
    ├── evaluate.py               python -m src.training.evaluate
    │                             [--model path] [--episodes N] [--gui]
    │                             Runs the saved model deterministically,
    │                             reports mean final position error + crash
    │                             rate against Stage 2 criteria (below).
    └── demo.py                   python -m src.training.demo [--model path]
                                  [--episodes N]
                                  Live PyBullet GUI demo for showing to
                                  other people — loops episodes, paced to
                                  real time via gym-pybullet-drones' own
                                  sync() helper, draws a green marker at
                                  the target position.
```

## Reward function (in `gym_wrapper.py`)

```
reward = -w_pos * ||target_position - position||
         -w_vel * ||velocity||
         -w_smooth * ||action_t - action_{t-1}||
         +survival_bonus
```
Default weights: `position_error_weight=1.0`, `velocity_penalty_weight=0.05`,
`action_smoothness_weight=0.01`, `survival_bonus=0.01`. Custom — not
`HoverAviary`'s built-in `max(0, 2 - ||pos_error||**4)` reward.

## Definition of done (full detail in `docs/hover-model-plan.md`)

Staged, not binary:
- **Stage 0** — pipeline sanity (env installs, training runs without error)
- **Stage 1** — learning signal present (reward trending, episodes surviving longer)
- **Stage 2** — usable/viable baseline: mean final position error < 0.3 m,
  crash rate < 10%, over 20 eval episodes
- **Stage 3** — robust hover: same criteria hold across 3+ random seeds,
  position error < 0.1 m, recovers from mid-episode disturbance
- **Stage 4** — transplant-ready (belongs to `AGERE_sims`, out of scope here)

## Current status: **Stage 2 reached** (2026-07-31 run)

Real evaluation results, `python -m src.training.evaluate`, 20 episodes,
deterministic policy:
- Mean final position error: **0.088 m** (well under the 0.3 m bar)
- Crash rate: **0%** (every episode ran the full 240 steps)
- Mean episode reward: -29.0
- **Caveat worth carrying forward:** not uniform — 2 of 20 episodes
  reached 0.24–0.29 m, right up against the Stage 2 ceiling, and
  correlated with the worst-reward episodes (-55 to -75). This is a real
  tail in the policy's behavior, not just noise around a tight mean.
  Relevant to whether Stage 3 (tighter 0.1 m bar, 3+ seeds) will pass
  without further training or reward tuning.

Full run details logged in `docs/training-log.md` (run `2026-07-31-0`) —
check there for exact config values used, since defaults in `config.py`
may have changed since.

## Known issues / environment gotchas

- **`setuptools>=82` breaks `gym-pybullet-drones`.** It imports
  `pkg_resources` internally (`BaseAviary.py`), which setuptools removed
  in version 82+. Fix: pin `setuptools<82` in `environment.yml` (already
  done as of the version referenced in this handoff — verify it's still
  there).
- **SB3 warns about running PPO's MlpPolicy on GPU.** This is a real
  inefficiency, not just noise — MLP-based PPO is typically faster on CPU
  given the tiny network size and GPU transfer overhead. Consider passing
  `device="cpu"` in `ppo_policy.py`'s `PPO(...)` call. Not yet done as of
  this handoff.
- Runtime verification of new code in this project has generally been done
  by the project owner locally, not by whichever LLM wrote the code —
  earlier sessions were built inside a sandboxed environment that couldn't
  finish compiling `pybullet` (execution time limits), so code was
  syntax-checked and logic-traced against the actual gym-pybullet-drones
  source, then handed off for real testing. This has generally gone well,
  but don't assume newly-written code in this repo has been run
  end-to-end unless a human confirms it (as happened for `evaluate.py` and
  is expected for `demo.py`).

## Suggested next steps (as of this handoff)

1. Set `device="cpu"` in `ppo_policy.py`.
2. Decide: push for Stage 3 (more seeds, tighter threshold, investigate
   the position-error tail from episodes 9/18 in the 07-31 run — was it a
   bad start-jitter draw, or a genuine policy weak spot?), or move on to
   the next task (waypoint navigation) using this as a working baseline.
3. `docs/hover-model-plan.md` explicitly recommends not over-polishing
   Stage 2 before checking whether the current design (obs space, reward
   shape, PPO config) generalizes to the next task at all.

## Other docs in this repo worth reading, in rough priority order

1. `docs/code-structure.md` — full reasoning for the src/ layout above
2. `docs/hover-model-plan.md` — full task spec + staged completion criteria
3. `docs/training-log.md` — living log, one entry per training run
4. `docs/devlog/2026_07_30.md` — the AGERE/AGERE_sims split decision
5. `docs/architecture/Architecture.md` — long-term system architecture (PX4/ROS2)
