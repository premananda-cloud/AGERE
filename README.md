# Backseat Driver RL — Hover/Stabilize (R&D path)

RL training stack for the Agere project's hover/stabilization task, built
against MAVSDK + PX4 SITL for fast iteration. Deployment later moves to
ROS 2 / uXRCE-DDS per `Architecture.md` — the module boundaries below are
drawn specifically so that move doesn't require rewriting the RL logic.

## Layout

```
src/
  config.py                 All tunable constants (control rate, velocity
                             limits, task/reward params, PPO hyperparams).
                             Change numbers here, not inside logic files.

  actions/
    velocity_action.py       Normalized [-1,1] policy output -> real
                              (vx, vy, vz, yaw_rate) command. Swap this file
                              alone to move to position-setpoint control.

  environments/
    px4_interface.py         All MAVSDK/async code lives here. The only file
                              that knows the transport is UDP + MAVSDK. A
                              ROS2Interface with the same method signatures
                              (connect, arm_and_takeoff, get_state,
                              send_velocity_body, land_and_disarm) is the
                              intended way to add the deployment path later.
    hover_env.py              The Gymnasium Env: observation/reward/
                              termination logic for hover-and-stabilize.
                              Talks to PX4Interface and VelocityActionSpace,
                              doesn't know MAVSDK exists.

  policies/
    ppo_policy.py             Builds the SB3 PPO model from PPOConfig. Only
                              file that imports the PPO class — add
                              build_sac() alongside it later if you want to
                              compare algorithms.

  models/
    networks.py               Placeholder for custom feature extractors.
                              Empty for now (9-dim obs doesn't need one) —
                              this is where richer sensor inputs
                              (LiDAR/vision, for obstacle avoidance) would
                              plug in later.

  training/
    train.py                  Entry point. Wires config -> env -> policy ->
                              model.learn(). Run as `python -m src.training.train`.
```

## Before running

1. `conda env create -f environment.yml` (adds `mavsdk`, which the original
   file didn't have but `px4_interface.py` needs).
2. PX4 SITL + Gazebo running (per the 2026-07-23 session setup), with the
   MAVSDK connection actually confirmed receiving packets first — the
   `hostname -I` / `nc -ul 14540` diagnostic from that session's "next
   steps" was flagged as not yet re-run. Do that before launching training,
   or `env.reset()` will hang indefinitely with no useful error.
3. `python -m src.training.train`

## Known rough edges (flagged deliberately, not hidden)

- **Episode reset doesn't truly randomize the start position yet.**
  `hover_env.reset()` currently just re-arms/takes off from the same
  point. Real position randomization needs either a Gazebo model-reset
  call or a "fly to a jittered point before starting the episode" step —
  noted as a TODO in `hover_env.py`, not yet implemented.
- **Takeoff completion is a 5-second sleep**, not a telemetry check. Works
  for a first pass; replace with an in-air/altitude poll once the basic
  loop is confirmed working end to end.
- **`PX4Interface` polls `position_velocity_ned` for pos+vel and a second
  generator for attitude** rather than fusing telemetry streams properly.
  Fine for 15 Hz control; revisit if you need tighter sync between the two.
