# Code Structure

This document explains how `src/` is organized and why — written so you
can make consistent decisions about where new code goes without having to
re-derive the reasoning each time.

## The core idea: separate "what the simulation is" from "how we train on it"

Everything in this codebase splits along one line:

- **Simulation** — the physics, the drone, stepping time forward, reading
  state back. This doesn't know or care that it's being used for
  reinforcement learning.
- **Training** — turning that simulation into something an RL algorithm
  can learn from: defining what the agent observes, what counts as a
  reward, when an episode ends, and running the actual learning loop.

Keeping these separate is a standard practice for a simple reason: the
simulation is a fact about the world (how a drone physically behaves), but
reward functions, observation choices, and episode termination rules are
*design decisions* you'll change constantly while tuning the model. If
those two things are tangled together in one class, every time you tweak a
reward weight you're touching the same file that defines how PyBullet
physics steps forward — and it becomes hard to tell, months later, whether
a bug is a physics bug or a reward-shaping bug.

This split also paid off concretely once a second task (waypoint
navigation + landing) was added: `environments/drone_sim.py` and
`actions/velocity_action.py` needed zero changes (drone_sim.py gained
optional `color`/`radius` params on one method, for waypoint marker
differentiation — not a behavior change for existing callers). Everything
task-specific — reward, observation space, episode termination — lives
entirely in `training/`, exactly where the split predicts it should.

## Folder-by-folder

```
src/
├── actions/       — action space definitions (shared across tasks)
├── environments/  — PyBullet simulation (no Gymnasium dependency, shared)
├── models/        — network architectures
├── policies/      — RL algorithm construction (PPO, etc., shared)
└── training/      — Gymnasium wrapping + the training loop
    ├── hover_train.py        — hover training entry point, stays flat here
    ├── waypoint_train.py     — waypoint training entry point, also flat
    ├── gym_wrapper/          — the Gymnasium wrapper (one file per task)
    ├── evaluate/             — evaluation scripts (one file per task,
    │                           plus variants like disturbance-recovery)
    └── demo/                 — live/watchable demo scripts
```

`training/` itself is flat only for the per-task training entry points
(`hover_train.py`, `waypoint_train.py`). Anything that comes in
task-specific variants — the Gymnasium wrapper, evaluation, demo — gets
its own subpackage instead, so that adding a second task's
evaluate/demo/wrapper file doesn't turn `training/` into an
undifferentiated pile of `<task>_<purpose>.py` files. Each of those
subpackages has an `__init__.py`, same as any other Python package under
`src/`. This is no longer hypothetical — both `hover_train.py` and
`waypoint_train.py` sit directly in `training/`, while
`gym_wrapper/hover_gym_wrapper.py` + `gym_wrapper/waypoint_gym_wrapper.py`
(and the equivalent `evaluate/`, `demo/` pairs) demonstrate the
subpackage pattern in practice.

### `actions/`

Defines what a number coming out of a neural network *means* as a physical
command. A policy network outputs raw numbers — this module is the only
place that knows how to turn those into something like "move at 2 m/s
forward."

Kept separate because the action representation is something you'll want
to change independent of everything else — e.g. switching from velocity
commands to position commands shouldn't require touching the simulation,
the reward function, or the training loop. It's a self-contained
translation layer. Confirmed unchanged and directly reusable when
waypoint navigation was added — direction+speed semantics don't care what
task is using them.

### `environments/`

The PyBullet simulation itself. This layer:
- Steps physics forward
- Applies whatever command `actions/` produced
- Reports back the drone's raw state (position, velocity, orientation,
  etc.)

**Deliberately does not import Gymnasium.** No `observation_space`, no
`action_space`, no reward, no concept of an "episode." This is a hard
rule, not a style preference — the value of drawing this line is that
`environments/` stays reusable by anything that needs "a simulated drone I
can command and read state from," whether that's RL training, a
visualization script, a unit test, or something else entirely. If
Gymnasium leaks in here, that reusability is gone, and the simulation
layer is now secretly an RL-specific thing wearing a simulation costume.

### `models/`

Network architectures (e.g. custom feature extractors). Most of the time
this stays empty or minimal — small observation spaces don't need custom
networks, stable-baselines3's defaults are fine. This folder exists as the
deliberate landing spot for when that stops being true (e.g. adding camera
or LiDAR input later).

### `policies/`

Builds the actual RL algorithm (currently PPO) from configuration. This is
the layer that knows *which algorithm* you're using. If you later want to
compare PPO against SAC, this is the only folder that changes — the
environment, the actions, and the training loop don't need to know or
care which algorithm is running underneath.

### `training/`

This is where the two worlds meet:

1. **The Gymnasium wrapper** (`training/gym_wrapper/`) — takes the plain
   PyBullet simulation from `environments/` and wraps it into a proper
   `gymnasium.Env`: defines the observation space, defines the reward
   function, defines when an episode is terminated or truncated. This is
   intentionally *not* in `environments/` — reward and termination logic
   are RL design choices you'll iterate on constantly, and they belong
   next to the training loop that's most affected by them, not buried
   inside the physics layer.
2. **The training loop itself** (`training/hover_train.py`,
   `training/waypoint_train.py`) — wires the wrapped environment into the
   policy from `policies/` and runs `model.learn()`. A per-task training
   script can extend this pattern beyond hover's — `waypoint_train.py`
   adds an `--init-from` flag to warm-start from an existing checkpoint
   (e.g. a trained hover model) instead of random init, which only works
   because `WaypointGymEnv`'s observation space was deliberately kept
   shape-identical to `HoverGymEnv`'s (see `docs/status.md` for why).

`training/` also holds `evaluate/` (scoring a trained policy against a
task's criteria, including variants like disturbance-recovery testing for
hover, or route-vs-landing failure breakdowns for waypoint nav) and
`demo/` (live, watchable runs for showing to other people — not for
scoring). Each task gets its own file inside `gym_wrapper/`, `evaluate/`,
and `demo/` (e.g. `hover_gym_wrapper.py`/`waypoint_gym_wrapper.py`,
`hover_evaluate.py`/`waypoint_evaluate.py`,
`hover_demo.py`/`waypoint_demo.py`), following the same one-file-per-task
naming used for the model/tb_logs directories in `docs/conventions.md`.
Only the top-level training-loop scripts (`hover_train.py`,
`waypoint_train.py`) sit directly in `training/` rather than in their own
subfolder, since they don't have further per-task variants the way
evaluate/demo do.

The "disturbance-recovery testing for hover" variant mentioned above is
no longer hypothetical as of 2026-08-25: `evaluate/` now also holds
`hover_checkpoint_sweep.py` (re-evaluates a run's own checkpoint series
under an identical seeded condition to measure whether training is still
improving or has plateaued) and `hover_tilt_diagnostic.py` (checks
whether an episode's crash was genuine loss of control or a truncation-
criterion artifact, by temporarily loosening the tilt bound for the eval
pass only). Both import and reuse `hover_evaluate.py`'s `run_episode()`
rather than duplicating episode logic — a second instance of the same
"shared core, task/purpose-specific file" pattern this section already
describes for `gym_wrapper/`/`evaluate/`/`demo/` generally, one level
down: multiple *evaluation* variants for one task, not just one eval
file per task.

## A rule of thumb for "where does this code go?"

Ask: **does this fact stay true even if we swapped PPO for SAC, or changed
the reward function entirely?**

- Yes → it belongs in `environments/` or `actions/` (it's about the
  physical world, not the learning problem).
- No, it depends on how we're training → it belongs in `training/`,
  `policies/`, or `models/`.

## What this buys you, concretely

- You can change the reward function ten times in an afternoon without
  touching anything that talks to PyBullet.
- You can test the simulation in isolation (does the drone physically
  behave correctly?) without needing Gymnasium installed at all.
- When something breaks, "is this a physics problem or a training
  problem?" has an answer based on which folder you'd look in first.
- Adding waypoint navigation as a second task needed a new file in
  `training/gym_wrapper/`, `training/evaluate/`, `training/demo/`, and a
  new top-level `training/waypoint_train.py` — but `environments/` needed
  no changes beyond an optional cosmetic parameter, and `actions/` needed
  none at all. This was the actual outcome, not just the design's intent.
