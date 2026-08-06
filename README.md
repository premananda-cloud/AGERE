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
- **Waypoint navigation + landing — in progress**, scoped for a demo
  (see `docs/status.md`). Pipeline built and running; first real training
  run shows zero crashes but hasn't yet finished a full route within the
  episode budget (0% success, 2.05/5 mean waypoints reached, 20-episode
  eval as of 2026-08-06).

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
                                   (hyperparameters).

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
                                    identical to make this work).
    gym_wrapper/hover_gym_wrapper.py       HoverGymEnv
    gym_wrapper/waypoint_gym_wrapper.py    WaypointGymEnv
    evaluate/hover_evaluate.py             Hover eval vs. staged criteria
    evaluate/hover_evaluate_disturbance.py Hover Stage 3 disturbance test
    evaluate/waypoint_evaluate.py          Waypoint success rate / route
                                            failure breakdown
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
python -m src.training.evaluate.waypoint_evaluate --model model/model_weights/waypoint_nav_ppo_seed0.zip --episodes 20
```
Watch progress with:
```bash
tensorboard --logdir tb_logs/waypoint_logs
```

`python -m src.training.demo.waypoint_demo` is **not yet functional** —
see `docs/status.md`'s Known Issues.

## Model / log storage

All checkpoints save to a single flat `model/model_weights/` directory,
distinguished by filename prefix (`hover_stabilize_ppo*.zip` vs.
`waypoint_nav_ppo*.zip`). `tb_logs/` stays split per task
(`tb_logs/hover_logs/`, `tb_logs/waypoint_logs/`). Both directories are
`.gitignore`d — weights/logs are pushed to Hugging Face instead (see
`docs/conventions.md`). `src/paths.py` is the single source of truth for
every save/load path — never hardcode one elsewhere.

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
- **Waypoint navigation isn't reliably completing the route yet** — see
  `docs/status.md`'s Task 2 section for current numbers and diagnosis.
  Zero crashes so far, but success rate is 0% as of 2026-08-06; more
  fine-tuning is the current hypothesis, being tested next session.
- `waypoint_demo.py` is a known-broken placeholder (duplicate of
  `waypoint_evaluate.py`), not yet written for real.
