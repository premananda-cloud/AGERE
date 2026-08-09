# AGERE — Drone RL Training Stack

RL training stack for the Agere project. **PyBullet + Gymnasium only. No
PX4, no MAVSDK, no network dependency.** Per the 2026-07-30 decision,
`AGERE` and `AGERE_sims` are separate repos: `AGERE` (this repo) builds
and trains models against
[`gym-pybullet-drones`](https://github.com/learnsyslab/gym-pybullet-drones)
— in-process PyBullet physics, no SITL, fast iteration. `AGERE_sims` owns
PX4/Gazebo/MAVSDK entirely and is where a trained model eventually gets
plugged in and tested. See `docs/architecture/Architecture.md` for the
unchanged end-state architecture, and `docs/devlog/2026_07_30.md` for why
the split happened.

**Status:**
- **Hover/stabilize — Stage 3 complete, paused** (2026-08-02). Mean
  position error 0.015-0.025 m and 0-5% crash rate across 3 seeds,
  disturbance recovery confirmed.
- **Waypoint navigation + landing — in progress** (see `docs/status.md`
  for the full 2026-08-08 write-up). Two real bugs found and fixed this
  session (a PPO entropy-runaway cause traced to `ent_coef`/`gamma`
  inherited unchanged from hover, and a stale-observation bug on
  intermediate waypoint transitions that was corrupting eval
  diagnostics), plus a data-integrity issue (repeated training runs were
  silently overwriting the same checkpoint file — now archived with
  timestamps). Post-fix: mean waypoints reached improved from 2.05/5 to
  3.00/5, zero crashes throughout, `waypoint_reach_radius` confirmed NOT
  to be the bottleneck (0/20 episodes ever got within it on their stuck
  leg). Success rate still 0% — no episode has reached the landing phase
  yet. Training curve was still improving (not plateaued) as of the
  latest run, so continuing training from the current checkpoint is the
  planned next step.

See `docs/status.md` for full project context, `docs/hover-model-plan.md`
for what the hover stages mean, `docs/training-log.md` for the complete
run history of both tasks.

## Layout

See `docs/code-structure.md` for the full reasoning. Short version:

```
src/
  config.py                       All tunable constants — SimConfig
                                   (physics), HoverTaskConfig /
                                   WaypointTaskConfig (per-task reward
                                   and episode design), PPOConfig
                                   (hyperparameters), waypoint_ppo_config()
                                   (waypoint-specific gamma/ent_coef —
                                   added 2026-08-08, see docs/status.md).

  actions/velocity_action.py      Defines what a raw action means
                                   physically (direction + speed). Shared
                                   by both tasks. No gymnasium, no PX4.

  environments/drone_sim.py       Pure PyBullet simulation wrapper around
                                   gym-pybullet-drones' HoverAviary. No
                                   reward, no episode logic, no Gymnasium
                                   spaces — just physics. Shared by both
                                   tasks.

  training/
    hover_train.py                 Hover training entry point.
    waypoint_train.py               Waypoint training entry point. Extra
                                    --init-from flag to warm-start from
                                    an existing checkpoint (e.g. a hover
                                    checkpoint — see docs/status.md for
                                    why the observation spaces are kept
                                    identical to make this work). Applies
                                    waypoint_ppo_config() and explicitly
                                    overrides gamma/ent_coef on a
                                    warm-started model (PPO.load()
                                    otherwise ignores config.ppo — see
                                    docs/status.md). Archives a
                                    timestamped copy of every save under
                                    model/model_weights/history/.
    gym_wrapper/hover_gym_wrapper.py       HoverGymEnv
    gym_wrapper/waypoint_gym_wrapper.py    WaypointGymEnv. Fixed
                                            2026-08-08: obs is now
                                            re-derived on any waypoint
                                            transition, not just the
                                            transition into landing (see
                                            docs/status.md).
    evaluate/hover_evaluate.py             Hover eval vs. staged criteria
    evaluate/hover_evaluate_disturbance.py Hover Stage 3 disturbance test
    evaluate/waypoint_evaluate.py          Waypoint success rate / route
                                            failure breakdown. Added
                                            2026-08-08: per-leg "closest
                                            approach on the stuck leg"
                                            diagnostic, and a warning when
                                            run without --seed.
    demo/hover_demo.py                     Live GUI demo, hover
    demo/waypoint_demo.py                  BROKEN — currently a duplicate
                                            of waypoint_evaluate.py, not
                                            yet rewritten as a real demo

  policies/ppo_policy.py          Builds SB3 PPO from PPOConfig. Shared
                                   by both tasks, algorithm-agnostic
                                   design otherwise.

  models/networks.py              Placeholder for custom feature
                                   extractors — not needed yet.
```

## Setup

**1. Create the environment**
```bash
conda env create -f environment.yml
conda activate rl_env
```
This installs `gym-pybullet-drones` from GitHub via pip, which compiles
`pybullet` from source — needs a C compiler:
```bash
sudo apt install build-essential   # if the pybullet wheel build fails
```
`environment.yml` pins `setuptools<82` — versions 82+ removed the
`pkg_resources` module that `gym-pybullet-drones` still imports
internally. If you hit `ModuleNotFoundError: No module named
'pkg_resources'`, this pin is missing or something re-upgraded setuptools;
`pip install --force-reinstall "setuptools<82"` fixes it directly.

**2. Sanity-check the install**
```bash
python -c "import gym_pybullet_drones; import torch; print('cuda:', torch.cuda.is_available())"
```

## Commands — Hover/Stabilize

```bash
python -m src.training.hover_train
python -m src.training.hover_train --gui
python -m src.training.hover_train --timesteps 500000
python -m src.training.hover_train --seed 0

python -m src.training.evaluate.hover_evaluate
python -m src.training.evaluate.hover_evaluate --model model/model_weights/hover_stabilize_ppo_seed0.zip --episodes 20

python -m src.training.evaluate.hover_evaluate_disturbance
python -m src.training.evaluate.hover_evaluate_disturbance --kick-speed 2.0

python -m src.training.demo.hover_demo
python -m src.training.demo.hover_demo --episodes 5
```
Watch progress with:
```bash
tensorboard --logdir tb_logs/hover_logs
```

## Commands — Waypoint Navigation + Landing

```bash
# Train from scratch
python -m src.training.waypoint_train
python -m src.training.waypoint_train --gui
python -m src.training.waypoint_train --timesteps 500000
python -m src.training.waypoint_train --seed 0

# Warm-start from an existing checkpoint (e.g. a trained hover model —
# see docs/status.md for why this works)
python -m src.training.waypoint_train --init-from model/model_weights/hover_stabilize_ppo_seed0.zip --timesteps 300000 --seed 0

python -m src.training.evaluate.waypoint_evaluate
python -m src.training.evaluate.waypoint_evaluate --model model/model_weights/waypoint_nav_ppo_seed0.zip --episodes 20 --seed 42
```
**Always pass `--seed` to `waypoint_evaluate.py`** when the result needs
to be compared against another run — without it, the episode sequence is
unseeded and two runs against the *same* checkpoint can legitimately
disagree (this is why early sessions saw different "mean waypoints
reached" numbers before the underlying model had even changed).

Watch progress with:
```bash
tensorboard --logdir tb_logs/waypoint_logs
```

`python -m src.training.demo.waypoint_demo` is **not yet functional** —
see `docs/status.md`'s Known Issues.

## Model / log storage

All checkpoints save to a single flat `model/model_weights/` directory,
distinguished by filename prefix (`hover_stabilize_ppo*.zip` vs.
`waypoint_nav_ppo*.zip`). A timestamped copy of every waypoint save is
also archived under `model/model_weights/history/` (added 2026-08-08,
after discovering that three separate training runs had silently
overwritten the same checkpoint file with no record of which one's
weights ended up on disk — see `docs/status.md`). `tb_logs/` stays split
per task (`tb_logs/hover_logs/`, `tb_logs/waypoint_logs/`). Both
directories are `.gitignore`d — weights/logs are pushed to Hugging Face
instead (see `docs/conventions.md`). `src/paths.py` is the single source
of truth for every save/load path — never hardcode one elsewhere.

## After each run

Copy the relevant template in `docs/training-log.md` (hover or waypoint
section) and log the config used and the results — that file is the
living record of what was tried and what worked, this README isn't.

## Known limitations

- **No yaw-rate control.** gym-pybullet-drones' `VEL` action type
  (direction + speed magnitude) always holds the drone's current yaw
  internally. Fine for hover; waypoint nav's `VelocityCommand` inherits
  the same limitation.
- **Reward is custom for both tasks**, not `HoverAviary`'s built-in
  `max(0, 2 - ||pos_error||**4)`.
- **`PPO.load()` ignores whatever `PPOConfig` is passed alongside it** —
  it restores hyperparameters from the checkpoint file itself. Any
  hyperparameter change meant to apply to a warm-started (`--init-from`)
  run needs an explicit post-load override on the loaded `PPO` object,
  or it will silently have no effect. See `docs/status.md` for the bug
  this caused and how `waypoint_train.py` now handles it.
- **Waypoint navigation isn't reliably completing the route yet**, though
  meaningfully improved as of 2026-08-08 (mean waypoints reached 3.00/5,
  up from 2.05/5) after fixing an entropy-runaway training issue and a
  stale-observation bug on intermediate waypoint transitions. Zero
  crashes throughout. `waypoint_reach_radius` has been confirmed, with
  real per-leg data, NOT to be the bottleneck — don't widen it. See
  `docs/status.md`'s Task 2 section for the full diagnosis and current
  numbers.
- `waypoint_demo.py` is a known-broken placeholder (duplicate of
  `waypoint_evaluate.py`), not yet written for real.
