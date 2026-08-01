# AGERE — Hover/Stabilize RL

RL training stack for the Agere project's hover/stabilization task.

**PyBullet + Gymnasium only. No PX4, no MAVSDK, no network dependency.**
Per the 2026-07-30 decision, `AGERE` and `AGERE_sims` are now separate
repos: `AGERE` (this repo) builds and trains the model against
[`gym-pybullet-drones`](https://github.com/learnsyslab/gym-pybullet-drones)
— in-process PyBullet physics, no SITL, fast iteration. `AGERE_sims` owns
PX4/Gazebo/MAVSDK entirely and is where a trained model eventually gets
plugged in and tested. See `docs/architecture/Architecture.md` for the
unchanged end-state architecture, and `docs/devlog/2026_07_30.md` for why
the split happened.

**Status:** Stage 2 (usable/viable baseline) reached as of 2026-07-31 —
mean position error 0.088 m, 0% crash rate over 20 eval episodes. See
`status.md` for full project context, `docs/hover-model-plan.md` for what
the stages mean, `docs/training-log.md` for the run history.

## Layout

See `docs/code-structure.md` for the full reasoning. Short version:

```
src/
  config.py                   All tunable constants — SimConfig (physics),
                               HoverTaskConfig (reward/episode design),
                               PPOConfig (hyperparameters).

  actions/velocity_action.py  Defines what a raw action means physically
                               (direction + speed). No gymnasium, no PX4.

  environments/drone_sim.py   Pure PyBullet simulation wrapper around
                               gym-pybullet-drones' HoverAviary. No reward,
                               no episode logic, no Gymnasium spaces —
                               just physics: reset, step, read state back.

  training/
    gym_wrapper.py               The actual Gymnasium environment
                                 (HoverGymEnv) — action/observation spaces,
                                 reward, termination. Wraps DroneSim.
    train.py                     Entry point: trains a new policy with PPO.
    evaluate.py                  Measures a saved policy against the
                                 staged criteria in hover-model-plan.md.
    demo.py                      Live PyBullet GUI demo for showing the
                                 trained policy to other people.

  policies/ppo_policy.py      Builds SB3 PPO from PPOConfig. Track-agnostic.

  models/networks.py          Placeholder for custom feature extractors —
                               not needed yet, extension point for later
                               (e.g. vision/LiDAR observations).
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

## Commands

### Train a new policy
```bash
python -m src.training.train
python -m src.training.train --gui               # watch training live
python -m src.training.train --timesteps 500000  # override config default (200,000)
```
Saves `hover_stabilize_ppo.zip` to the working directory when done.
Watch progress with:
```bash
tensorboard --logdir ./tb_logs/hover
```

### Evaluate a trained policy
```bash
python -m src.training.evaluate
python -m src.training.evaluate --model hover_stabilize_ppo.zip --episodes 20
python -m src.training.evaluate --gui             # watch the eval episodes
```
Runs the policy deterministically (no exploration noise) over N episodes
with randomized starts, then reports mean final position error and crash
rate against the Stage 2 thresholds from `docs/hover-model-plan.md`
(< 0.3 m position error, < 10% crash rate).

### Demo the trained policy live
```bash
python -m src.training.demo
python -m src.training.demo --model hover_stabilize_ppo.zip
python -m src.training.demo --episodes 5          # stop after N episodes instead of looping forever
```
Opens the PyBullet GUI and loops episodes continuously, paced to real
time so it's watchable, with a green marker showing the target position.
Ctrl+C to stop. Built for showing the model to other people, not for
measuring anything — use `evaluate.py` for real numbers.

## After each run

Copy the template in `docs/training-log.md` and log the config used and
the results — that file is the living record of what was tried and what
worked, this README isn't.

## Known limitations

- **No yaw-rate control.** gym-pybullet-drones' `VEL` action type (direction
  + speed magnitude) always holds the drone's current yaw internally — a
  property of the underlying library, not something controlled at this
  layer. Fine for pure position-hold; would need a different action type or
  a custom handler if yaw stabilization becomes part of the task.
- **Reward is custom, not HoverAviary's default.** Their built-in reward is
  `max(0, 2 - ||pos_error||**4)`; this project uses position-error +
  velocity + smoothness penalties instead. Validated by the Stage 2 eval
  results above, but worth re-checking if reward weights change.
- **PPO currently may run on GPU by default**, which SB3 warns against for
  small MLP policies (CPU is typically faster here) — worth passing
  `device="cpu"` in `ppo_policy.py` if training speed matters.
