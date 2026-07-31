# AGERE — Hover/Stabilize RL

RL training stack for the Agere project's hover/stabilization task.

**PyBullet + Gymnasium only. No PX4, no MAVSDK, no network dependency.**
Per the 2026-07-30 decision, `AGERE` and `AGERE_sims` are now separate
repos: `AGERE` (this repo) builds and trains the model against
[`gym-pybullet-drones`](https://github.com/learnsyslab/gym-pybullet-drones)
— in-process PyBullet physics, no SITL, fast iteration. `AGERE_sims` owns
PX4/Gazebo/MAVSDK entirely and is where a trained model eventually gets
plugged in and tested. See `Architecture.md` for the unchanged end-state
architecture, and `docs/devlog/2026_07_30.md` for why the split happened —
mainly, PX4/Gazebo networking (WSL2 loopback ambiguity, MAVLink broadcast
flags, D3D12/Mesa GPU hacks) was consuming time that should go into
learning RL and building the model itself.

## Layout

See `docs/code-structure.md` for the full reasoning. Short version:

```
src/
  config.py                 All tunable constants — SimConfig (physics),
                             HoverTaskConfig (reward/episode design),
                             PPOConfig (hyperparameters).

  actions/velocity_action.py  Defines what a raw action means physically
                             (direction + speed). No gymnasium, no PX4.

  environments/drone_sim.py   Pure PyBullet simulation wrapper around
                             gym-pybullet-drones' HoverAviary. No reward,
                             no episode logic, no Gymnasium spaces —
                             just physics: reset, step, read state back.

  training/
    gym_wrapper.py             The actual Gymnasium environment
                               (HoverGymEnv) — action/observation spaces,
                               reward, termination. Wraps DroneSim.
    train.py                   Entry point. Wires config -> DroneSim (via
                               gym_wrapper) -> PPO -> model.learn().

  policies/ppo_policy.py      Builds SB3 PPO from PPOConfig. Track-agnostic.

  models/networks.py          Placeholder for custom feature extractors —
                             not needed yet, extension point for later
                             (e.g. vision/LiDAR observations).
```

## How to run training

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

**2. Sanity-check the install**
```bash
python -c "import gym_pybullet_drones; import torch; print('cuda:', torch.cuda.is_available())"
```

**3. Run training**
```bash
python -m src.training.train --gui
```
- `--gui` opens the PyBullet window so you can watch the drone attempt to
  hover — worth doing at least once to confirm it's not doing something
  obviously wrong (flipping immediately, shooting off in one direction).
- Drop `--gui` for faster/headless runs once you trust it's working.
- `--timesteps N` overrides the default (200,000, set in `config.py`) —
  useful for a quick smoke test first, e.g. `--timesteps 5000`.

**4. Watch training progress**
```bash
tensorboard --logdir ./tb_logs/hover
```
Open the printed URL. Episode reward trending up and episode length
stabilizing is the "is this actually learning" signal — see
`docs/hover-model-plan.md` for the staged definition of "done."

**5. After training**
Saves `hover_stabilize_ppo.zip` to the working directory. Load it back with:
```python
from stable_baselines3 import PPO
model = PPO.load("hover_stabilize_ppo")
```

**6. Log the run**
Copy the template in `docs/training-log.md` and fill in the config used and
the results — that file is the living record of what was tried and what
worked, this README isn't.

## Known limitations

- **No yaw-rate control.** gym-pybullet-drones' `VEL` action type (direction
  + speed magnitude) always holds the drone's current yaw internally — this
  is a property of the underlying library, not something we control at this
  layer. Fine for pure position-hold; would need a different action type or
  a custom handler if yaw stabilization becomes part of the task.
- **Reward is custom, not HoverAviary's default.** Their built-in reward is
  `max(0, 2 - ||pos_error||**4)`; this project uses position-error +
  velocity + smoothness penalties instead, designed to generalize better
  across reward-shaping experiments. A reasonable design, not a proven one —
  watch the training curve rather than assuming it's correct.
- **Runtime-unverified as of the last structural refactor.** The
  `gym_wrapper.py` / `drone_sim.py` split was syntax-checked but not run
  end-to-end in the environment it was written in (pybullet's source compile
  exceeded that sandbox's time limits). Treat the first real run as a
  genuine test, not a formality.
