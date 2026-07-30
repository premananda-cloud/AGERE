# Backseat Driver RL — Hover/Stabilize

RL training stack for the Agere project's hover/stabilization task.

**Architecture unchanged (see `Architecture.md`):** the eventual deployment
target is still PX4 + uXRCE-DDS/ROS 2 per the Backseat Driver model. What
changed is *where the model gets built*. Fighting PX4/Gazebo/MAVSDK
networking (WSL2 loopback ambiguity, MAVLink broadcast flags, D3D12/Mesa
GPU hacks — see the 2026-07-23 session) was consuming time that should go
into learning RL and building the model itself. So:

- **Active now**: train against
  [`gym-pybullet-drones`](https://github.com/learnsyslab/gym-pybullet-drones)
  — in-process PyBullet physics, no network, no SITL, fast iteration.
- **Parked, not deleted**: the PX4/MAVSDK integration built for the SITL
  path. It's the transplant target once the model is good — likely a
  separate effort (possibly outsourced), not blocking model development now.

## Layout

```
src/
  config.py                       All tunable constants. PyBulletHoverConfig
                                   is what the active training script reads;
                                   HoverTaskConfig/ControlConfig/ActionLimits
                                   are the parked PX4 equivalents, unused by
                                   the active path but kept for the
                                   transplant phase.

  environments/
    pybullet/hover_env.py           ACTIVE. ConfigurableHoverAviary — a thin
                                     subclass of gym-pybullet-drones'
                                     HoverAviary. Leverages their physics,
                                     observation space (KIN), and VEL action
                                     type (PID-controlled velocity setpoints)
                                     rather than reimplementing any of it.
                                     Adds: config-driven target/episode
                                     length, custom reward shaping, and true
                                     per-episode start-position
                                     randomization (HoverAviary doesn't
                                     randomize its own reset by default).
    px4/                             PARKED. px4_interface.py (MAVSDK bridge)
                                     + hover_env.py (hand-built Gym env).
                                     Not re-tested since being parked.

  actions/
    px4/velocity_action.py           PARKED. Normalized-action -> real
                                     velocity-setpoint scaling for the
                                     MAVSDK path. Not needed for the active
                                     track — gym-pybullet-drones' VEL action
                                     type owns this scaling internally.

  policies/ppo_policy.py            ACTIVE, track-agnostic. Builds SB3 PPO
                                     from PPOConfig. Works with either env.

  models/networks.py                Placeholder for custom feature
                                     extractors — not needed yet (9-12 dim
                                     KIN observation), extension point for
                                     later (e.g. vision/LiDAR obs for
                                     obstacle avoidance).

  training/
    train.py                        ACTIVE. Trains ConfigurableHoverAviary
                                     with PPO. `python -m src.training.train
                                     [--gui] [--timesteps N]`
    train_px4_parked.py             PARKED. Original PX4/MAVSDK training
                                     script.
```

## Before running

1. `conda env create -f environment.yml`. This now installs
   `gym-pybullet-drones` directly from GitHub via pip, which compiles
   `pybullet` from source — needs a C compiler
   (`sudo apt install build-essential` on Ubuntu first if the wheel build
   fails). This step took long enough that I could not finish it inside my
   own sandboxed environment while building this, so it has **not** been
   runtime-verified end-to-end — only syntax-checked and traced by hand
   against the actual `gym_pybullet_drones` source. Run it and tell me what
   breaks; I read `BaseAviary.py`/`BaseRLAviary.py` carefully but real
   PyBullet execution can still surprise you.
2. `python -m src.training.train --gui` to watch it train, or without
   `--gui` for headless/faster runs.

## Known limitations / things I flagged rather than papered over

- **`ActionType.VEL` has no yaw-rate control.** `BaseRLAviary`'s VEL handler
  always targets the drone's *current* yaw — it's direction + speed
  magnitude only. Fine for pure position-hold; if yaw stabilization turns
  out to matter, switch `action_type` to `"pid"` (3D position-delta control)
  or write a custom action type. Not silently assumed away — see the
  docstring in `hover_env.py`.
- **Reward is custom, not HoverAviary's default.** Their built-in reward is
  `max(0, 2 - ||pos_error||**4)`; I replaced it with position-error +
  velocity + smoothness penalties (closer to what we designed for the PX4
  track) so the two tracks stay conceptually comparable. Worth watching the
  training curve to confirm this shape actually works better in practice —
  it's a reasonable design, not a proven one.
- **Not yet run.** See point 1 above. Don't assume this trains cleanly on
  first try; treat it as a strong starting point, not a finished baseline.
