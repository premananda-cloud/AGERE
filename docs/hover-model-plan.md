# Hover/Stabilize Model — Plan & Definition of Done

Reference document. Unlike `training-log.md`, this describes the intended
design and the bar for "done" — update it when the *design* changes, not
every run. If you find yourself editing this file after every training
run, that's a sign something belongs in the log instead.

## 1. Task

Learn a policy that holds a multirotor at a fixed target point in 3D space,
starting from a randomized nearby position, and stays there.

This is the first task in the Backseat Driver RL sequence — deliberately
the simplest closed-loop control problem (single static target, no path,
no obstacles) before attempting waypoint navigation or obstacle avoidance.

## 2. Environment

**Physics:** `gym-pybullet-drones`, in-process PyBullet simulation. No
network, no SITL — this is the fast-iteration training environment, not
the deployment target (see `Architecture.md` and `README.md` for the
PX4/ROS 2 path, currently parked).

**Drone model:** CF2X (Crazyflie 2.X quadrotor model, as shipped by
gym-pybullet-drones).

### Observation space (`ObservationType.KIN`, 12 dims)
| Field | Description |
|---|---|
| position (3) | x, y, z, world frame |
| orientation (3) | roll, pitch, yaw, radians |
| linear velocity (3) | vx, vy, vz |
| angular velocity (3) | wx, wy, wz |

Note: `ConfigurableHoverAviary` computes reward/termination directly from
`_getDroneStateVector()`, not from the stacked observation the policy
receives — the two are related but not identical; see the source if the
distinction matters for debugging.

### Action space (`ActionType.VEL`, 4 dims)
Direction vector (3) + speed magnitude (1), normalized, PID-controlled
internally by gym-pybullet-drones' `DSLPIDControl`.

**Known limitation:** no yaw-rate command — the internal PID always holds
whatever yaw the drone currently has. Acceptable for pure position-hold.
If yaw stabilization becomes part of the task definition, this needs
`ActionType.PID` (position-delta control) or a custom action handler —
not a config toggle, an actual code change.

### Episode structure
- **Reset:** start position = `target_position` + uniform jitter
  (`reset_position_jitter`, meters per axis) + small yaw jitter. True
  per-episode randomization (mutates `INIT_XYZS`/`INIT_RPYS` before the
  parent reset, confirmed against `BaseAviary` source — not inherited free
  from `HoverAviary`).
- **Step:** apply velocity setpoint, advance physics, compute reward.
- **Terminated** (task success — early stop): position error < 0.0001 m
  (essentially exact target match — in practice this will rarely fire;
  it's inherited from `HoverAviary` and worth revisiting once real
  training data shows whether it ever triggers).
- **Truncated** (episode ends, not a success): out of xy/altitude bounds,
  excessive tilt, or `episode_len_sec` elapsed.

### Reward
```
reward = -w_pos * ||target - position||
         -w_vel * ||velocity||
         -w_smooth * ||action_t - action_{t-1}||
         +survival_bonus
```
Custom, not `HoverAviary`'s default quartic reward — chosen to stay
conceptually consistent with the reward shape originally designed for the
(parked) PX4 track. This is a reasonable starting design, not a validated
one; if training stalls or the policy finds a degenerate solution (e.g.
oscillating for survival bonus without closing position error), revisit
the weights here and log the change plus rationale in the training log.

## 3. Model

**Algorithm:** PPO (stable-baselines3), on-policy — chosen for forgiving
early-training instability over sample efficiency, appropriate for a
first working baseline. SAC is the natural next thing to try if sample
efficiency becomes the bottleneck once the pipeline itself is trusted.

**Network:** default MLP, `net_arch={"pi": [64,64], "vf": [64,64]}` — small
on purpose; the 12-dim observation doesn't need capacity beyond this, and
starting bigger just slows iteration without evidence it's needed.

**Extension point:** `src/models/networks.py` is where a custom feature
extractor would go if later tasks add richer observations (e.g. vision or
LiDAR for obstacle avoidance). Empty by design right now.

## 4. Definition of done — staged, not binary

"Done" isn't one bar. Use these stages to know where the model actually is
and what to attempt next. Each stage should be logged in `training-log.md`
when it's first reached, with the run entry that demonstrated it.

### Stage 0 — Pipeline sanity
- [ ] `conda env create -f environment.yml` completes, `pybullet` builds
- [ ] `python -m src.training.train --timesteps 5000 --gui` runs without
      erroring, drone visibly attempts to counteract drift (even badly)
- **Gate:** infrastructure works. Says nothing about model quality yet.

### Stage 1 — Learning signal present
- [ ] Episode reward trends upward over training (not flat, not diverging)
- [ ] Episode length trends toward the truncation limit (surviving longer,
      not terminating early via out-of-bounds/tilt every episode)
- **Gate:** the reward function and PPO hyperparameters are basically sane.
  Doesn't mean the policy is good — means it's learning *something*.

### Stage 2 — Usable / viable baseline
- [ ] Over 20 evaluation episodes (randomized starts, no training updates):
      mean position error at episode end < 0.3 m
- [ ] No crashes (truncation via tilt/out-of-bounds) in >90% of eval episodes
- [ ] Behavior is visually recognizable as "hovering near target," not
      oscillating wildly or drifting slowly away
- **Gate:** this is the "good enough to move on" bar. A model at this
  stage is a legitimate baseline to branch from for the next task
  (waypoint navigation) even though it's not polished — don't over-invest
  in perfecting hover before checking whether these design choices (obs
  space, reward shape, PPO config) generalize to the next task at all.

### Stage 3 — Robust hover
- [ ] Stage 2 criteria hold across at least 3 different random seeds
      (rules out "got lucky once")
- [ ] Mean position error at episode end < 0.1 m
- [ ] Recovers from a mid-episode external disturbance (if you add one —
      e.g. an impulse force via PyBullet's `applyExternalForce`) within a
      few seconds
- **Gate:** this is what "complete" means for the hover task specifically.
  Meeting this stage is the trigger to seriously consider the PX4/SITL
  transplant phase for *this* policy, per `Architecture.md`.

### Stage 4 — Transplant-ready (out of scope for this doc)
Belongs to the parked PX4 track, not the PyBullet training loop — noted
here only so Stage 3 doesn't get mistaken for "ready to fly." Transplant
readiness additionally requires validating the policy against
domain-randomized physics (mass, drag, sensor noise) since none of that
exists in the current PyBullet setup, and re-deriving the action interface
against MAVSDK or ROS 2 rather than gym-pybullet-drones' internal PID
controller. Not defined in detail here — revisit when Stage 3 is reached.

## 5. What would make this plan wrong

Worth stating explicitly rather than treating this document as fixed
truth:
- If Stage 1 never triggers even after hyperparameter sweeps, the reward
  shape (not just the weights) may be the problem — the smoothness/survival
  terms could be dominating the position-error term in a way that isn't
  obvious from the formula alone.
- If Stage 2's 0.3 m threshold turns out to be trivially easy or
  unreasonably hard once real data comes in, that's a sign the threshold
  was a reasonable guess, not a calibrated number — adjust it and note why
  in the training log rather than silently redefining "done."
