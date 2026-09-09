# Hover Champion Selection Report

Generated: Wed Sep  9 09:12:29 UTC 2026

Candidate lines compared: hover_stabilize_ppo_seed0_disturbance_3x5_tiltfix2 hover_stabilize_ppo_seed0_disturbance_3x5_tiltfix3

## 1. Checkpoint sweeps (60 episodes each -- filter only)

### hover_stabilize_ppo_seed0_disturbance_3x5_tiltfix2
```
Applied stage preset 'disturbance_3x5': {'disturbance_enabled': True, 'disturbance_types_active': ('kick', 'torque', 'wind')}
Sweeping 10 checkpoints, 60 episodes each, seed=0 (identical eval condition per checkpoint)

[INFO] BaseAviary.__init__() loaded parameters from the drone's .urdf:
[INFO] m 0.027000, L 0.039700,
[INFO] ixx 0.000014, iyy 0.000014, izz 0.000022,
[INFO] kf 3.160000e-10, km 7.940000e-12,
[INFO] t2w 2.250000, max_speed_kmh 30.000000,
[INFO] gnd_eff_coeff 11.368590, prop_radius 0.023135,
[INFO] drag_xy_coeff 0.000001, drag_z_coeff 0.000001,
[INFO] dw_coeff_1 2267.180000, dw_coeff_2 0.160000, dw_coeff_3 -0.110000
  49998 steps | crash  18.3% | pos_err 0.085 m | kick=35% | wind=0% | torque=22%
[INFO] BaseAviary.__init__() loaded parameters from the drone's .urdf:
[INFO] m 0.027000, L 0.039700,
[INFO] ixx 0.000014, iyy 0.000014, izz 0.000022,
[INFO] kf 3.160000e-10, km 7.940000e-12,
[INFO] t2w 2.250000, max_speed_kmh 30.000000,
[INFO] gnd_eff_coeff 11.368590, prop_radius 0.023135,
[INFO] drag_xy_coeff 0.000001, drag_z_coeff 0.000001,
[INFO] dw_coeff_1 2267.180000, dw_coeff_2 0.160000, dw_coeff_3 -0.110000
  99996 steps | crash  23.3% | pos_err 0.099 m | kick=45% | wind=0% | torque=28%
[INFO] BaseAviary.__init__() loaded parameters from the drone's .urdf:
[INFO] m 0.027000, L 0.039700,
[INFO] ixx 0.000014, iyy 0.000014, izz 0.000022,
[INFO] kf 3.160000e-10, km 7.940000e-12,
[INFO] t2w 2.250000, max_speed_kmh 30.000000,
[INFO] gnd_eff_coeff 11.368590, prop_radius 0.023135,
[INFO] drag_xy_coeff 0.000001, drag_z_coeff 0.000001,
[INFO] dw_coeff_1 2267.180000, dw_coeff_2 0.160000, dw_coeff_3 -0.110000
 149994 steps | crash  21.7% | pos_err 0.088 m | kick=35% | wind=0% | torque=33%
[INFO] BaseAviary.__init__() loaded parameters from the drone's .urdf:
[INFO] m 0.027000, L 0.039700,
[INFO] ixx 0.000014, iyy 0.000014, izz 0.000022,
[INFO] kf 3.160000e-10, km 7.940000e-12,
[INFO] t2w 2.250000, max_speed_kmh 30.000000,
[INFO] gnd_eff_coeff 11.368590, prop_radius 0.023135,
[INFO] drag_xy_coeff 0.000001, drag_z_coeff 0.000001,
[INFO] dw_coeff_1 2267.180000, dw_coeff_2 0.160000, dw_coeff_3 -0.110000
 199992 steps | crash  23.3% | pos_err 0.096 m | kick=50% | wind=0% | torque=22%
[INFO] BaseAviary.__init__() loaded parameters from the drone's .urdf:
[INFO] m 0.027000, L 0.039700,
[INFO] ixx 0.000014, iyy 0.000014, izz 0.000022,
[INFO] kf 3.160000e-10, km 7.940000e-12,
[INFO] t2w 2.250000, max_speed_kmh 30.000000,
[INFO] gnd_eff_coeff 11.368590, prop_radius 0.023135,
[INFO] drag_xy_coeff 0.000001, drag_z_coeff 0.000001,
[INFO] dw_coeff_1 2267.180000, dw_coeff_2 0.160000, dw_coeff_3 -0.110000
 249990 steps | crash  21.7% | pos_err 0.105 m | kick=45% | wind=0% | torque=22%
[INFO] BaseAviary.__init__() loaded parameters from the drone's .urdf:
[INFO] m 0.027000, L 0.039700,
[INFO] ixx 0.000014, iyy 0.000014, izz 0.000022,
[INFO] kf 3.160000e-10, km 7.940000e-12,
[INFO] t2w 2.250000, max_speed_kmh 30.000000,
[INFO] gnd_eff_coeff 11.368590, prop_radius 0.023135,
[INFO] drag_xy_coeff 0.000001, drag_z_coeff 0.000001,
[INFO] dw_coeff_1 2267.180000, dw_coeff_2 0.160000, dw_coeff_3 -0.110000
 299988 steps | crash  21.7% | pos_err 0.089 m | kick=40% | wind=0% | torque=28%
[INFO] BaseAviary.__init__() loaded parameters from the drone's .urdf:
[INFO] m 0.027000, L 0.039700,
[INFO] ixx 0.000014, iyy 0.000014, izz 0.000022,
[INFO] kf 3.160000e-10, km 7.940000e-12,
[INFO] t2w 2.250000, max_speed_kmh 30.000000,
[INFO] gnd_eff_coeff 11.368590, prop_radius 0.023135,
[INFO] drag_xy_coeff 0.000001, drag_z_coeff 0.000001,
[INFO] dw_coeff_1 2267.180000, dw_coeff_2 0.160000, dw_coeff_3 -0.110000
 349986 steps | crash  28.3% | pos_err 0.104 m | kick=50% | wind=0% | torque=39%
[INFO] BaseAviary.__init__() loaded parameters from the drone's .urdf:
[INFO] m 0.027000, L 0.039700,
[INFO] ixx 0.000014, iyy 0.000014, izz 0.000022,
[INFO] kf 3.160000e-10, km 7.940000e-12,
[INFO] t2w 2.250000, max_speed_kmh 30.000000,
[INFO] gnd_eff_coeff 11.368590, prop_radius 0.023135,
[INFO] drag_xy_coeff 0.000001, drag_z_coeff 0.000001,
[INFO] dw_coeff_1 2267.180000, dw_coeff_2 0.160000, dw_coeff_3 -0.110000
 399984 steps | crash  23.3% | pos_err 0.090 m | kick=45% | wind=0% | torque=28%
[INFO] BaseAviary.__init__() loaded parameters from the drone's .urdf:
[INFO] m 0.027000, L 0.039700,
[INFO] ixx 0.000014, iyy 0.000014, izz 0.000022,
[INFO] kf 3.160000e-10, km 7.940000e-12,
[INFO] t2w 2.250000, max_speed_kmh 30.000000,
[INFO] gnd_eff_coeff 11.368590, prop_radius 0.023135,
[INFO] drag_xy_coeff 0.000001, drag_z_coeff 0.000001,
[INFO] dw_coeff_1 2267.180000, dw_coeff_2 0.160000, dw_coeff_3 -0.110000
 449982 steps | crash  18.3% | pos_err 0.086 m | kick=35% | wind=0% | torque=22%
[INFO] BaseAviary.__init__() loaded parameters from the drone's .urdf:
[INFO] m 0.027000, L 0.039700,
[INFO] ixx 0.000014, iyy 0.000014, izz 0.000022,
[INFO] kf 3.160000e-10, km 7.940000e-12,
[INFO] t2w 2.250000, max_speed_kmh 30.000000,
[INFO] gnd_eff_coeff 11.368590, prop_radius 0.023135,
[INFO] drag_xy_coeff 0.000001, drag_z_coeff 0.000001,
[INFO] dw_coeff_1 2267.180000, dw_coeff_2 0.160000, dw_coeff_3 -0.110000
 499980 steps | crash  20.0% | pos_err 0.087 m | kick=35% | wind=0% | torque=28%

============================================================
Trailing window:  steps 399984-499980 -> mean crash rate 20.6%
Prior window:     steps 249990-349986 -> mean crash rate 23.9%
Improvement:      +3.3 percentage points (threshold for 'still learning': >3pp)

-> STILL IMPROVING. Crash rate dropped meaningfully in the most recent window vs the one before it. More training steps at current settings look like a reasonable next move -- continue with --init-from this run's final checkpoint.
```

### hover_stabilize_ppo_seed0_disturbance_3x5_tiltfix3
```
Applied stage preset 'disturbance_3x5': {'disturbance_enabled': True, 'disturbance_types_active': ('kick', 'torque', 'wind')}
Sweeping 10 checkpoints, 60 episodes each, seed=0 (identical eval condition per checkpoint)

[INFO] BaseAviary.__init__() loaded parameters from the drone's .urdf:
[INFO] m 0.027000, L 0.039700,
[INFO] ixx 0.000014, iyy 0.000014, izz 0.000022,
[INFO] kf 3.160000e-10, km 7.940000e-12,
[INFO] t2w 2.250000, max_speed_kmh 30.000000,
[INFO] gnd_eff_coeff 11.368590, prop_radius 0.023135,
[INFO] drag_xy_coeff 0.000001, drag_z_coeff 0.000001,
[INFO] dw_coeff_1 2267.180000, dw_coeff_2 0.160000, dw_coeff_3 -0.110000
  49998 steps | crash  23.3% | pos_err 0.099 m | kick=45% | wind=0% | torque=28%
[INFO] BaseAviary.__init__() loaded parameters from the drone's .urdf:
[INFO] m 0.027000, L 0.039700,
[INFO] ixx 0.000014, iyy 0.000014, izz 0.000022,
[INFO] kf 3.160000e-10, km 7.940000e-12,
[INFO] t2w 2.250000, max_speed_kmh 30.000000,
[INFO] gnd_eff_coeff 11.368590, prop_radius 0.023135,
[INFO] drag_xy_coeff 0.000001, drag_z_coeff 0.000001,
[INFO] dw_coeff_1 2267.180000, dw_coeff_2 0.160000, dw_coeff_3 -0.110000
  99996 steps | crash  25.0% | pos_err 0.102 m | kick=45% | wind=0% | torque=33%
[INFO] BaseAviary.__init__() loaded parameters from the drone's .urdf:
[INFO] m 0.027000, L 0.039700,
[INFO] ixx 0.000014, iyy 0.000014, izz 0.000022,
[INFO] kf 3.160000e-10, km 7.940000e-12,
[INFO] t2w 2.250000, max_speed_kmh 30.000000,
[INFO] gnd_eff_coeff 11.368590, prop_radius 0.023135,
[INFO] drag_xy_coeff 0.000001, drag_z_coeff 0.000001,
[INFO] dw_coeff_1 2267.180000, dw_coeff_2 0.160000, dw_coeff_3 -0.110000
 149994 steps | crash  21.7% | pos_err 0.101 m | kick=45% | wind=0% | torque=22%
[INFO] BaseAviary.__init__() loaded parameters from the drone's .urdf:
[INFO] m 0.027000, L 0.039700,
[INFO] ixx 0.000014, iyy 0.000014, izz 0.000022,
[INFO] kf 3.160000e-10, km 7.940000e-12,
[INFO] t2w 2.250000, max_speed_kmh 30.000000,
[INFO] gnd_eff_coeff 11.368590, prop_radius 0.023135,
[INFO] drag_xy_coeff 0.000001, drag_z_coeff 0.000001,
[INFO] dw_coeff_1 2267.180000, dw_coeff_2 0.160000, dw_coeff_3 -0.110000
 199992 steps | crash  23.3% | pos_err 0.092 m | kick=45% | wind=0% | torque=28%
[INFO] BaseAviary.__init__() loaded parameters from the drone's .urdf:
[INFO] m 0.027000, L 0.039700,
[INFO] ixx 0.000014, iyy 0.000014, izz 0.000022,
[INFO] kf 3.160000e-10, km 7.940000e-12,
[INFO] t2w 2.250000, max_speed_kmh 30.000000,
[INFO] gnd_eff_coeff 11.368590, prop_radius 0.023135,
[INFO] drag_xy_coeff 0.000001, drag_z_coeff 0.000001,
[INFO] dw_coeff_1 2267.180000, dw_coeff_2 0.160000, dw_coeff_3 -0.110000
 249990 steps | crash  23.3% | pos_err 0.095 m | kick=45% | wind=0% | torque=28%
[INFO] BaseAviary.__init__() loaded parameters from the drone's .urdf:
[INFO] m 0.027000, L 0.039700,
[INFO] ixx 0.000014, iyy 0.000014, izz 0.000022,
[INFO] kf 3.160000e-10, km 7.940000e-12,
[INFO] t2w 2.250000, max_speed_kmh 30.000000,
[INFO] gnd_eff_coeff 11.368590, prop_radius 0.023135,
[INFO] drag_xy_coeff 0.000001, drag_z_coeff 0.000001,
[INFO] dw_coeff_1 2267.180000, dw_coeff_2 0.160000, dw_coeff_3 -0.110000
 299988 steps | crash  26.7% | pos_err 0.110 m | kick=45% | wind=0% | torque=39%
[INFO] BaseAviary.__init__() loaded parameters from the drone's .urdf:
[INFO] m 0.027000, L 0.039700,
[INFO] ixx 0.000014, iyy 0.000014, izz 0.000022,
[INFO] kf 3.160000e-10, km 7.940000e-12,
[INFO] t2w 2.250000, max_speed_kmh 30.000000,
[INFO] gnd_eff_coeff 11.368590, prop_radius 0.023135,
[INFO] drag_xy_coeff 0.000001, drag_z_coeff 0.000001,
[INFO] dw_coeff_1 2267.180000, dw_coeff_2 0.160000, dw_coeff_3 -0.110000
 349986 steps | crash  26.7% | pos_err 0.092 m | kick=40% | wind=0% | torque=44%
[INFO] BaseAviary.__init__() loaded parameters from the drone's .urdf:
[INFO] m 0.027000, L 0.039700,
[INFO] ixx 0.000014, iyy 0.000014, izz 0.000022,
[INFO] kf 3.160000e-10, km 7.940000e-12,
[INFO] t2w 2.250000, max_speed_kmh 30.000000,
[INFO] gnd_eff_coeff 11.368590, prop_radius 0.023135,
[INFO] drag_xy_coeff 0.000001, drag_z_coeff 0.000001,
[INFO] dw_coeff_1 2267.180000, dw_coeff_2 0.160000, dw_coeff_3 -0.110000
 399984 steps | crash  21.7% | pos_err 0.083 m | kick=40% | wind=0% | torque=28%
[INFO] BaseAviary.__init__() loaded parameters from the drone's .urdf:
[INFO] m 0.027000, L 0.039700,
[INFO] ixx 0.000014, iyy 0.000014, izz 0.000022,
[INFO] kf 3.160000e-10, km 7.940000e-12,
[INFO] t2w 2.250000, max_speed_kmh 30.000000,
[INFO] gnd_eff_coeff 11.368590, prop_radius 0.023135,
[INFO] drag_xy_coeff 0.000001, drag_z_coeff 0.000001,
[INFO] dw_coeff_1 2267.180000, dw_coeff_2 0.160000, dw_coeff_3 -0.110000
 449982 steps | crash  21.7% | pos_err 0.089 m | kick=40% | wind=0% | torque=28%
[INFO] BaseAviary.__init__() loaded parameters from the drone's .urdf:
[INFO] m 0.027000, L 0.039700,
[INFO] ixx 0.000014, iyy 0.000014, izz 0.000022,
[INFO] kf 3.160000e-10, km 7.940000e-12,
[INFO] t2w 2.250000, max_speed_kmh 30.000000,
[INFO] gnd_eff_coeff 11.368590, prop_radius 0.023135,
[INFO] drag_xy_coeff 0.000001, drag_z_coeff 0.000001,
[INFO] dw_coeff_1 2267.180000, dw_coeff_2 0.160000, dw_coeff_3 -0.110000
 499980 steps | crash  25.0% | pos_err 0.100 m | kick=50% | wind=0% | torque=28%

============================================================
Trailing window:  steps 399984-499980 -> mean crash rate 22.8%
Prior window:     steps 249990-349986 -> mean crash rate 25.6%
Improvement:      +2.8 percentage points (threshold for 'still learning': >3pp)

-> PLATEAUED (or noisy/flat). No meaningful crash-rate improvement between the two most recent windows at current settings. More steps alone are unlikely to help much from here -- worth pausing to reconsider rather than continuing to spend compute (candidates: the ent_coef/std issue flagged earlier, curriculum restructuring, or a larger eval to confirm this reading before deciding).
```

## 2. Thorough evaluations (200 episodes each, seed=0)

### hover_stabilize_ppo_seed0_disturbance_3x5_tiltfix2 @ 49998 steps
```
Applied stage preset 'disturbance_3x5' for evaluation: {'disturbance_enabled': True, 'disturbance_types_active': ('kick', 'torque', 'wind')}

[INFO] BaseAviary.__init__() loaded parameters from the drone's .urdf:
[INFO] m 0.027000, L 0.039700,
[INFO] ixx 0.000014, iyy 0.000014, izz 0.000022,
[INFO] kf 3.160000e-10, km 7.940000e-12,
[INFO] t2w 2.250000, max_speed_kmh 30.000000,
[INFO] gnd_eff_coeff 11.368590, prop_radius 0.023135,
[INFO] drag_xy_coeff 0.000001, drag_z_coeff 0.000001,
[INFO] dw_coeff_1 2267.180000, dw_coeff_2 0.160000, dw_coeff_3 -0.110000
episode  1/200 | final pos error: 0.474 m | crash: True (tilt) | reward: -14.6 | start jitter: 0.319 m | start yaw jitter: 14.5 deg | kick L5 (1.956m/s), crashed
episode  2/200 | final pos error: 0.023 m | crash: False | reward: -18.8 | start jitter: 0.413 m | start yaw jitter: 14.0 deg | wind L4 (0.107N), steady-state err 0.026m, recovered in 0 steps
episode  3/200 | final pos error: 0.030 m | crash: False | reward: -20.6 | start jitter: 0.365 m | start yaw jitter: 5.1 deg | torque L4 (7.846rad/s), recovered in 22 steps
episode  4/200 | final pos error: 0.025 m | crash: False | reward: -9.4 | start jitter: 0.159 m | start yaw jitter: 10.9 deg | wind L3 (0.086N), steady-state err 0.026m, recovered in 0 steps
episode  5/200 | final pos error: 0.032 m | crash: False | reward: -12.8 | start jitter: 0.277 m | start yaw jitter: 5.3 deg | wind L3 (0.080N), steady-state err 0.019m, recovered in 0 steps
episode  6/200 | final pos error: 0.023 m | crash: False | reward: -20.2 | start jitter: 0.363 m | start yaw jitter: 7.8 deg | torque L4 (6.176rad/s), recovered in 21 steps
episode  7/200 | final pos error: 0.035 m | crash: False | reward: -13.9 | start jitter: 0.361 m | start yaw jitter: 2.9 deg | wind L1 (0.022N), steady-state err 0.021m, recovered in 0 steps
episode  8/200 | final pos error: 0.013 m | crash: False | reward: -21.5 | start jitter: 0.365 m | start yaw jitter: 3.9 deg | kick L4 (1.276m/s), recovered in 18 steps
episode  9/200 | final pos error: 0.037 m | crash: False | reward: -20.3 | start jitter: 0.312 m | start yaw jitter: 0.1 deg | torque L3 (5.572rad/s), recovered in 29 steps
episode 10/200 | final pos error: 0.031 m | crash: False | reward: -17.7 | start jitter: 0.372 m | start yaw jitter: 14.0 deg | wind L5 (0.175N), steady-state err 0.041m, recovered in 0 steps
episode 11/200 | final pos error: 0.011 m | crash: False | reward: -19.2 | start jitter: 0.415 m | start yaw jitter: 0.6 deg | kick L2 (0.741m/s), recovered in 0 steps
episode 12/200 | final pos error: 0.017 m | crash: False | reward: -20.9 | start jitter: 0.403 m | start yaw jitter: 3.4 deg | torque L3 (5.438rad/s), recovered in 0 steps
episode 13/200 | final pos error: 0.031 m | crash: False | reward: -18.9 | start jitter: 0.420 m | start yaw jitter: 13.0 deg | torque L2 (2.861rad/s), recovered in 0 steps
episode 14/200 | final pos error: 0.707 m | crash: True (tilt) | reward: -18.3 | start jitter: 0.363 m | start yaw jitter: 6.4 deg | kick L5 (1.777m/s), crashed
episode 15/200 | final pos error: 0.061 m | crash: False | reward: -13.3 | start jitter: 0.212 m | start yaw jitter: 13.8 deg | torque L2 (3.105rad/s), recovered in 0 steps
episode 16/200 | final pos error: 0.095 m | crash: True (tilt) | reward: -16.1 | start jitter: 0.416 m | start yaw jitter: 2.5 deg | torque L5 (9.040rad/s), crashed
episode 17/200 | final pos error: 0.008 m | crash: False | reward: -18.7 | start jitter: 0.323 m | start yaw jitter: 11.2 deg | kick L5 (1.530m/s), recovered in 20 steps
episode 18/200 | final pos error: 0.011 m | crash: False | reward: -10.4 | start jitter: 0.244 m | start yaw jitter: 10.9 deg | wind L4 (0.120N), steady-state err 0.029m, recovered in 0 steps
episode 19/200 | final pos error: 0.054 m | crash: True (tilt) | reward: -10.4 | start jitter: 0.351 m | start yaw jitter: 5.0 deg | torque L5 (12.703rad/s), crashed
episode 20/200 | final pos error: 0.674 m | crash: True (tilt) | reward: -14.9 | start jitter: 0.259 m | start yaw jitter: 3.1 deg | kick L5 (1.781m/s), crashed
episode 21/200 | final pos error: 0.006 m | crash: False | reward: -15.6 | start jitter: 0.380 m | start yaw jitter: 2.1 deg | torque L1 (1.773rad/s), recovered in 0 steps
episode 22/200 | final pos error: 0.037 m | crash: False | reward: -13.4 | start jitter: 0.215 m | start yaw jitter: 3.1 deg | kick L5 (1.536m/s), recovered in 14 steps
episode 23/200 | final pos error: 0.297 m | crash: True (tilt) | reward: -13.1 | start jitter: 0.289 m | start yaw jitter: 11.2 deg | kick L3 (1.074m/s), crashed
episode 24/200 | final pos error: 0.027 m | crash: False | reward: -15.5 | start jitter: 0.349 m | start yaw jitter: 0.1 deg | kick L1 (0.435m/s), recovered in 0 steps
episode 25/200 | final pos error: 0.017 m | crash: False | reward: -13.3 | start jitter: 0.300 m | start yaw jitter: 2.4 deg | kick L1 (0.462m/s), recovered in 0 steps
episode 26/200 | final pos error: 0.021 m | crash: False | reward: -12.7 | start jitter: 0.261 m | start yaw jitter: 3.1 deg | wind L4 (0.137N), steady-state err 0.043m, recovered in 0 steps
episode 27/200 | final pos error: 0.221 m | crash: False | reward: -35.9 | start jitter: 0.357 m | start yaw jitter: 0.4 deg | kick L3 (1.063m/s), DID NOT recover in budget
episode 28/200 | final pos error: 0.011 m | crash: False | reward: -11.6 | start jitter: 0.265 m | start yaw jitter: 4.1 deg | wind L4 (0.122N), steady-state err 0.036m, recovered in 0 steps
episode 29/200 | final pos error: 0.544 m | crash: True (tilt) | reward: -16.8 | start jitter: 0.336 m | start yaw jitter: 6.1 deg | kick L5 (1.991m/s), crashed
episode 30/200 | final pos error: 0.033 m | crash: False | reward: -11.9 | start jitter: 0.291 m | start yaw jitter: 0.7 deg | wind L2 (0.061N), steady-state err 0.024m, recovered in 0 steps
episode 31/200 | final pos error: 0.029 m | crash: False | reward: -19.8 | start jitter: 0.359 m | start yaw jitter: 0.7 deg | kick L3 (0.927m/s), recovered in 19 steps
episode 32/200 | final pos error: 0.013 m | crash: False | reward: -13.5 | start jitter: 0.311 m | start yaw jitter: 13.8 deg | wind L1 (0.031N), steady-state err 0.021m, recovered in 0 steps
episode 33/200 | final pos error: 0.016 m | crash: False | reward: -16.0 | start jitter: 0.369 m | start yaw jitter: 3.2 deg | wind L4 (0.118N), steady-state err 0.029m, recovered in 0 steps
episode 34/200 | final pos error: 0.221 m | crash: True (tilt) | reward: -11.4 | start jitter: 0.289 m | start yaw jitter: 0.5 deg | kick L4 (1.134m/s), crashed
episode 35/200 | final pos error: 0.015 m | crash: False | reward: -8.6 | start jitter: 0.168 m | start yaw jitter: 13.3 deg | torque L1 (1.512rad/s), recovered in 0 steps
episode 36/200 | final pos error: 0.027 m | crash: False | reward: -10.1 | start jitter: 0.173 m | start yaw jitter: 14.6 deg | wind L1 (0.034N), steady-state err 0.025m, recovered in 0 steps
episode 37/200 | final pos error: 0.009 m | crash: False | reward: -9.5 | start jitter: 0.171 m | start yaw jitter: 14.8 deg | wind L5 (0.146N), steady-state err 0.032m, recovered in 0 steps
episode 38/200 | final pos error: 0.024 m | crash: False | reward: -12.7 | start jitter: 0.302 m | start yaw jitter: 9.7 deg | wind L2 (0.054N), steady-state err 0.019m, recovered in 0 steps
episode 39/200 | final pos error: 0.033 m | crash: False | reward: -14.5 | start jitter: 0.344 m | start yaw jitter: 11.8 deg | wind L3 (0.082N), steady-state err 0.023m, recovered in 0 steps
episode 40/200 | final pos error: 0.034 m | crash: False | reward: -14.0 | start jitter: 0.266 m | start yaw jitter: 2.2 deg | wind L5 (0.148N), steady-state err 0.035m, recovered in 0 steps
episode 41/200 | final pos error: 0.033 m | crash: False | reward: -21.4 | start jitter: 0.205 m | start yaw jitter: 9.7 deg | kick L4 (1.435m/s), recovered in 29 steps
episode 42/200 | final pos error: 0.012 m | crash: False | reward: -14.9 | start jitter: 0.348 m | start yaw jitter: 2.2 deg | wind L5 (0.148N), steady-state err 0.031m, recovered in 0 steps
episode 43/200 | final pos error: 0.029 m | crash: False | reward: -15.0 | start jitter: 0.343 m | start yaw jitter: 9.9 deg | torque L1 (1.586rad/s), recovered in 0 steps
episode 44/200 | final pos error: 0.036 m | crash: False | reward: -18.3 | start jitter: 0.391 m | start yaw jitter: 11.7 deg | torque L2 (2.713rad/s), recovered in 0 steps
episode 45/200 | final pos error: 0.022 m | crash: False | reward: -14.0 | start jitter: 0.204 m | start yaw jitter: 5.2 deg | kick L4 (1.144m/s), recovered in 0 steps
episode 46/200 | final pos error: 0.013 m | crash: False | reward: -8.7 | start jitter: 0.130 m | start yaw jitter: 8.1 deg | wind L3 (0.091N), steady-state err 0.028m, recovered in 0 steps
episode 47/200 | final pos error: 0.031 m | crash: False | reward: -11.2 | start jitter: 0.206 m | start yaw jitter: 0.7 deg | wind L2 (0.045N), steady-state err 0.023m, recovered in 0 steps
episode 48/200 | final pos error: 0.023 m | crash: False | reward: -13.0 | start jitter: 0.269 m | start yaw jitter: 3.4 deg | torque L3 (5.754rad/s), recovered in 0 steps
episode 49/200 | final pos error: 0.013 m | crash: False | reward: -9.5 | start jitter: 0.202 m | start yaw jitter: 9.3 deg | torque L1 (1.506rad/s), recovered in 0 steps
episode 50/200 | final pos error: 0.156 m | crash: True (tilt) | reward: -11.7 | start jitter: 0.358 m | start yaw jitter: 9.6 deg | torque L5 (10.176rad/s), crashed
episode 51/200 | final pos error: 0.120 m | crash: True (tilt) | reward: -5.5 | start jitter: 0.121 m | start yaw jitter: 5.3 deg | torque L3 (4.775rad/s), crashed
episode 52/200 | final pos error: 0.065 m | crash: False | reward: -9.4 | start jitter: 0.104 m | start yaw jitter: 14.6 deg | torque L1 (1.843rad/s), recovered in 0 steps
episode 53/200 | final pos error: 0.022 m | crash: False | reward: -18.2 | start jitter: 0.326 m | start yaw jitter: 9.5 deg | wind L5 (0.176N), steady-state err 0.059m, recovered in 0 steps
episode 54/200 | final pos error: 0.019 m | crash: False | reward: -13.3 | start jitter: 0.315 m | start yaw jitter: 1.8 deg | wind L2 (0.055N), steady-state err 0.026m, recovered in 0 steps
episode 55/200 | final pos error: 0.011 m | crash: False | reward: -22.7 | start jitter: 0.364 m | start yaw jitter: 7.9 deg | kick L4 (1.230m/s), recovered in 17 steps
episode 56/200 | final pos error: 0.009 m | crash: False | reward: -13.2 | start jitter: 0.279 m | start yaw jitter: 0.4 deg | kick L1 (0.456m/s), recovered in 0 steps
episode 57/200 | final pos error: 0.349 m | crash: True (tilt) | reward: -10.3 | start jitter: 0.256 m | start yaw jitter: 6.6 deg | kick L4 (1.327m/s), crashed
episode 58/200 | final pos error: 0.033 m | crash: False | reward: -12.1 | start jitter: 0.233 m | start yaw jitter: 10.9 deg | kick L1 (0.435m/s), recovered in 0 steps
episode 59/200 | final pos error: 0.044 m | crash: False | reward: -14.9 | start jitter: 0.367 m | start yaw jitter: 12.7 deg | wind L3 (0.075N), steady-state err 0.028m, recovered in 0 steps
episode 60/200 | final pos error: 0.011 m | crash: False | reward: -14.4 | start jitter: 0.332 m | start yaw jitter: 2.5 deg | torque L2 (3.222rad/s), recovered in 0 steps
episode 61/200 | final pos error: 0.020 m | crash: False | reward: -10.4 | start jitter: 0.232 m | start yaw jitter: 2.7 deg | wind L1 (0.022N), steady-state err 0.022m, recovered in 0 steps
episode 62/200 | final pos error: 0.003 m | crash: False | reward: -9.4 | start jitter: 0.155 m | start yaw jitter: 6.3 deg | wind L2 (0.067N), steady-state err 0.036m, recovered in 0 steps
episode 63/200 | final pos error: 0.023 m | crash: False | reward: -8.2 | start jitter: 0.181 m | start yaw jitter: 2.6 deg | torque L1 (1.669rad/s), recovered in 0 steps
episode 64/200 | final pos error: 0.122 m | crash: True (tilt) | reward: -8.4 | start jitter: 0.244 m | start yaw jitter: 3.7 deg | torque L5 (9.924rad/s), crashed
episode 65/200 | final pos error: 0.033 m | crash: False | reward: -10.7 | start jitter: 0.243 m | start yaw jitter: 7.5 deg | wind L1 (0.034N), steady-state err 0.023m, recovered in 0 steps
episode 66/200 | final pos error: 0.016 m | crash: False | reward: -20.3 | start jitter: 0.431 m | start yaw jitter: 7.7 deg | kick L1 (0.405m/s), recovered in 0 steps
episode 67/200 | final pos error: 0.654 m | crash: True (tilt) | reward: -19.4 | start jitter: 0.331 m | start yaw jitter: 1.5 deg | kick L5 (1.801m/s), crashed
episode 68/200 | final pos error: 0.033 m | crash: False | reward: -21.3 | start jitter: 0.194 m | start yaw jitter: 9.8 deg | torque L2 (3.778rad/s), recovered in 39 steps
episode 69/200 | final pos error: 0.010 m | crash: False | reward: -17.2 | start jitter: 0.386 m | start yaw jitter: 8.4 deg | torque L3 (4.260rad/s), recovered in 0 steps
episode 70/200 | final pos error: 0.019 m | crash: False | reward: -17.6 | start jitter: 0.283 m | start yaw jitter: 13.5 deg | kick L5 (1.533m/s), recovered in 20 steps
episode 71/200 | final pos error: 0.012 m | crash: False | reward: -13.6 | start jitter: 0.209 m | start yaw jitter: 7.6 deg | kick L4 (1.290m/s), recovered in 13 steps
episode 72/200 | final pos error: 0.031 m | crash: False | reward: -12.8 | start jitter: 0.313 m | start yaw jitter: 8.2 deg | wind L2 (0.066N), steady-state err 0.017m, recovered in 0 steps
episode 73/200 | final pos error: 0.034 m | crash: False | reward: -13.9 | start jitter: 0.295 m | start yaw jitter: 10.1 deg | kick L1 (0.444m/s), recovered in 0 steps
episode 74/200 | final pos error: 0.048 m | crash: False | reward: -10.8 | start jitter: 0.193 m | start yaw jitter: 10.8 deg | wind L1 (0.037N), steady-state err 0.027m, recovered in 0 steps
episode 75/200 | final pos error: 0.029 m | crash: False | reward: -17.4 | start jitter: 0.406 m | start yaw jitter: 11.3 deg | kick L1 (0.423m/s), recovered in 0 steps
episode 76/200 | final pos error: 0.032 m | crash: False | reward: -13.1 | start jitter: 0.306 m | start yaw jitter: 3.1 deg | wind L1 (0.029N), steady-state err 0.023m, recovered in 0 steps
episode 77/200 | final pos error: 0.008 m | crash: False | reward: -13.8 | start jitter: 0.301 m | start yaw jitter: 9.5 deg | torque L4 (6.815rad/s), recovered in 0 steps
episode 78/200 | final pos error: 0.016 m | crash: False | reward: -20.6 | start jitter: 0.415 m | start yaw jitter: 10.4 deg | kick L4 (1.199m/s), recovered in 0 steps
episode 79/200 | final pos error: 0.097 m | crash: False | reward: -31.8 | start jitter: 0.264 m | start yaw jitter: 5.2 deg | torque L4 (8.535rad/s), recovered in 54 steps
episode 80/200 | final pos error: 0.010 m | crash: False | reward: -13.6 | start jitter: 0.335 m | start yaw jitter: 12.4 deg | wind L2 (0.046N), steady-state err 0.020m, recovered in 0 steps
episode 81/200 | final pos error: 0.010 m | crash: False | reward: -11.1 | start jitter: 0.233 m | start yaw jitter: 3.3 deg | wind L1 (0.022N), steady-state err 0.026m, recovered in 0 steps
episode 82/200 | final pos error: 0.022 m | crash: False | reward: -10.5 | start jitter: 0.221 m | start yaw jitter: 13.2 deg | wind L4 (0.117N), steady-state err 0.024m, recovered in 0 steps
episode 83/200 | final pos error: 0.030 m | crash: False | reward: -17.9 | start jitter: 0.297 m | start yaw jitter: 3.8 deg | torque L2 (2.819rad/s), recovered in 27 steps
episode 84/200 | final pos error: 0.047 m | crash: False | reward: -11.8 | start jitter: 0.266 m | start yaw jitter: 12.7 deg | torque L3 (4.654rad/s), recovered in 0 steps
episode 85/200 | final pos error: 0.038 m | crash: False | reward: -19.3 | start jitter: 0.415 m | start yaw jitter: 3.9 deg | wind L2 (0.052N), steady-state err 0.039m, recovered in 0 steps
episode 86/200 | final pos error: 0.043 m | crash: False | reward: -26.6 | start jitter: 0.249 m | start yaw jitter: 4.3 deg | torque L3 (4.260rad/s), recovered in 55 steps
episode 87/200 | final pos error: 0.031 m | crash: False | reward: -15.0 | start jitter: 0.347 m | start yaw jitter: 14.0 deg | kick L1 (0.455m/s), recovered in 0 steps
episode 88/200 | final pos error: 0.015 m | crash: False | reward: -7.7 | start jitter: 0.128 m | start yaw jitter: 1.3 deg | wind L4 (0.132N), steady-state err 0.030m, recovered in 0 steps
episode 89/200 | final pos error: 0.021 m | crash: False | reward: -11.7 | start jitter: 0.216 m | start yaw jitter: 10.7 deg | wind L1 (0.033N), steady-state err 0.022m, recovered in 0 steps
episode 90/200 | final pos error: 0.509 m | crash: True (tilt) | reward: -12.8 | start jitter: 0.202 m | start yaw jitter: 11.6 deg | kick L4 (1.320m/s), crashed
episode 91/200 | final pos error: 0.020 m | crash: False | reward: -11.8 | start jitter: 0.298 m | start yaw jitter: 14.3 deg | wind L4 (0.116N), steady-state err 0.026m, recovered in 0 steps
episode 92/200 | final pos error: 0.021 m | crash: False | reward: -12.4 | start jitter: 0.210 m | start yaw jitter: 10.3 deg | torque L5 (11.064rad/s), recovered in 0 steps
episode 93/200 | final pos error: 0.069 m | crash: False | reward: -13.9 | start jitter: 0.322 m | start yaw jitter: 1.5 deg | torque L2 (3.056rad/s), recovered in 0 steps
episode 94/200 | final pos error: 0.071 m | crash: True (tilt) | reward: -10.7 | start jitter: 0.312 m | start yaw jitter: 12.6 deg | torque L3 (5.529rad/s), crashed
episode 95/200 | final pos error: 0.012 m | crash: False | reward: -13.8 | start jitter: 0.314 m | start yaw jitter: 4.3 deg | wind L5 (0.152N), steady-state err 0.033m, recovered in 0 steps
episode 96/200 | final pos error: 0.061 m | crash: False | reward: -18.1 | start jitter: 0.305 m | start yaw jitter: 15.0 deg | torque L3 (5.216rad/s), recovered in 0 steps
episode 97/200 | final pos error: 0.529 m | crash: True (tilt) | reward: -15.2 | start jitter: 0.286 m | start yaw jitter: 6.7 deg | kick L4 (1.318m/s), crashed
episode 98/200 | final pos error: 0.014 m | crash: False | reward: -20.1 | start jitter: 0.206 m | start yaw jitter: 5.4 deg | kick L3 (0.824m/s), recovered in 31 steps
episode 99/200 | final pos error: 0.012 m | crash: False | reward: -12.9 | start jitter: 0.265 m | start yaw jitter: 8.1 deg | wind L1 (0.034N), steady-state err 0.024m, recovered in 0 steps
episode 100/200 | final pos error: 0.032 m | crash: False | reward: -18.4 | start jitter: 0.390 m | start yaw jitter: 7.3 deg | torque L2 (3.639rad/s), recovered in 0 steps
episode 101/200 | final pos error: 0.126 m | crash: True (tilt) | reward: -10.8 | start jitter: 0.297 m | start yaw jitter: 13.2 deg | torque L4 (6.675rad/s), crashed
episode 102/200 | final pos error: 0.017 m | crash: False | reward: -24.8 | start jitter: 0.299 m | start yaw jitter: 4.0 deg | torque L3 (5.655rad/s), recovered in 35 steps
episode 103/200 | final pos error: 0.013 m | crash: False | reward: -15.8 | start jitter: 0.338 m | start yaw jitter: 5.5 deg | wind L4 (0.126N), steady-state err 0.041m, recovered in 0 steps
episode 104/200 | final pos error: 0.049 m | crash: False | reward: -17.5 | start jitter: 0.339 m | start yaw jitter: 10.1 deg | torque L2 (2.026rad/s), recovered in 0 steps
episode 105/200 | final pos error: 0.085 m | crash: False | reward: -12.9 | start jitter: 0.252 m | start yaw jitter: 7.0 deg | torque L1 (1.266rad/s), recovered in 0 steps
episode 106/200 | final pos error: 0.075 m | crash: False | reward: -22.1 | start jitter: 0.415 m | start yaw jitter: 12.2 deg | kick L3 (1.000m/s), recovered in 14 steps
episode 107/200 | final pos error: 0.050 m | crash: False | reward: -11.6 | start jitter: 0.221 m | start yaw jitter: 10.9 deg | wind L1 (0.030N), steady-state err 0.033m, recovered in 0 steps
episode 108/200 | final pos error: 0.057 m | crash: False | reward: -9.2 | start jitter: 0.163 m | start yaw jitter: 5.8 deg | wind L3 (0.094N), steady-state err 0.020m, recovered in 0 steps
episode 109/200 | final pos error: 0.105 m | crash: True (tilt) | reward: -10.1 | start jitter: 0.287 m | start yaw jitter: 2.7 deg | torque L4 (7.364rad/s), crashed
episode 110/200 | final pos error: 0.122 m | crash: True (tilt) | reward: -7.4 | start jitter: 0.252 m | start yaw jitter: 10.4 deg | torque L4 (8.826rad/s), crashed
episode 111/200 | final pos error: 0.560 m | crash: True (tilt) | reward: -15.5 | start jitter: 0.287 m | start yaw jitter: 13.0 deg | kick L5 (1.900m/s), crashed
episode 112/200 | final pos error: 0.011 m | crash: False | reward: -28.2 | start jitter: 0.358 m | start yaw jitter: 11.0 deg | kick L5 (1.872m/s), recovered in 38 steps
episode 113/200 | final pos error: 0.011 m | crash: False | reward: -11.3 | start jitter: 0.234 m | start yaw jitter: 10.8 deg | wind L3 (0.080N), steady-state err 0.028m, recovered in 0 steps
episode 114/200 | final pos error: 0.053 m | crash: False | reward: -10.5 | start jitter: 0.230 m | start yaw jitter: 8.0 deg | wind L3 (0.074N), steady-state err 0.033m, recovered in 0 steps
episode 115/200 | final pos error: 0.014 m | crash: False | reward: -11.8 | start jitter: 0.239 m | start yaw jitter: 12.1 deg | wind L1 (0.036N), steady-state err 0.024m, recovered in 0 steps
episode 116/200 | final pos error: 0.036 m | crash: False | reward: -16.0 | start jitter: 0.339 m | start yaw jitter: 11.0 deg | kick L3 (0.860m/s), recovered in 0 steps
episode 117/200 | final pos error: 0.016 m | crash: False | reward: -10.4 | start jitter: 0.217 m | start yaw jitter: 1.6 deg | wind L2 (0.063N), steady-state err 0.020m, recovered in 0 steps
episode 118/200 | final pos error: 0.064 m | crash: False | reward: -15.2 | start jitter: 0.312 m | start yaw jitter: 5.8 deg | torque L5 (11.807rad/s), recovered in 0 steps
episode 119/200 | final pos error: 0.027 m | crash: False | reward: -17.9 | start jitter: 0.430 m | start yaw jitter: 14.0 deg | torque L1 (1.833rad/s), recovered in 0 steps
episode 120/200 | final pos error: 0.146 m | crash: True (tilt) | reward: -10.8 | start jitter: 0.341 m | start yaw jitter: 3.5 deg | torque L5 (11.187rad/s), crashed
episode 121/200 | final pos error: 0.024 m | crash: False | reward: -11.1 | start jitter: 0.213 m | start yaw jitter: 12.5 deg | wind L4 (0.134N), steady-state err 0.037m, recovered in 0 steps
episode 122/200 | final pos error: 0.024 m | crash: False | reward: -15.0 | start jitter: 0.344 m | start yaw jitter: 9.7 deg | wind L1 (0.036N), steady-state err 0.029m, recovered in 0 steps
episode 123/200 | final pos error: 0.069 m | crash: False | reward: -20.9 | start jitter: 0.340 m | start yaw jitter: 7.2 deg | kick L4 (1.399m/s), recovered in 13 steps
episode 124/200 | final pos error: 0.018 m | crash: False | reward: -17.5 | start jitter: 0.392 m | start yaw jitter: 3.5 deg | wind L1 (0.021N), steady-state err 0.019m, recovered in 0 steps
episode 125/200 | final pos error: 0.042 m | crash: False | reward: -12.4 | start jitter: 0.326 m | start yaw jitter: 9.7 deg | wind L3 (0.074N), steady-state err 0.020m, recovered in 0 steps
episode 126/200 | final pos error: 0.034 m | crash: False | reward: -13.8 | start jitter: 0.340 m | start yaw jitter: 7.9 deg | torque L1 (1.878rad/s), recovered in 0 steps
episode 127/200 | final pos error: 0.021 m | crash: False | reward: -8.2 | start jitter: 0.137 m | start yaw jitter: 13.8 deg | kick L1 (0.318m/s), recovered in 0 steps
episode 128/200 | final pos error: 0.087 m | crash: False | reward: -14.9 | start jitter: 0.235 m | start yaw jitter: 5.3 deg | wind L3 (0.086N), steady-state err 0.045m, recovered in 0 steps
episode 129/200 | final pos error: 0.016 m | crash: False | reward: -14.9 | start jitter: 0.333 m | start yaw jitter: 9.1 deg | kick L2 (0.513m/s), recovered in 0 steps
episode 130/200 | final pos error: 0.084 m | crash: True (tilt) | reward: -8.3 | start jitter: 0.294 m | start yaw jitter: 14.5 deg | torque L4 (6.076rad/s), crashed
episode 131/200 | final pos error: 0.020 m | crash: False | reward: -15.6 | start jitter: 0.372 m | start yaw jitter: 12.9 deg | torque L2 (3.686rad/s), recovered in 0 steps
episode 132/200 | final pos error: 0.021 m | crash: False | reward: -11.2 | start jitter: 0.286 m | start yaw jitter: 1.3 deg | torque L1 (1.363rad/s), recovered in 0 steps
episode 133/200 | final pos error: 0.015 m | crash: False | reward: -17.1 | start jitter: 0.348 m | start yaw jitter: 2.8 deg | torque L1 (1.592rad/s), recovered in 0 steps
episode 134/200 | final pos error: 0.016 m | crash: False | reward: -15.1 | start jitter: 0.328 m | start yaw jitter: 2.5 deg | wind L5 (0.180N), steady-state err 0.038m, recovered in 0 steps
episode 135/200 | final pos error: 0.054 m | crash: False | reward: -17.0 | start jitter: 0.431 m | start yaw jitter: 12.6 deg | wind L1 (0.031N), steady-state err 0.026m, recovered in 0 steps
episode 136/200 | final pos error: 0.035 m | crash: False | reward: -9.8 | start jitter: 0.215 m | start yaw jitter: 10.8 deg | wind L5 (0.158N), steady-state err 0.029m, recovered in 0 steps
episode 137/200 | final pos error: 0.091 m | crash: False | reward: -22.8 | start jitter: 0.262 m | start yaw jitter: 4.9 deg | torque L3 (4.599rad/s), recovered in 24 steps
episode 138/200 | final pos error: 0.508 m | crash: True (tilt) | reward: -15.9 | start jitter: 0.403 m | start yaw jitter: 10.5 deg | kick L5 (1.687m/s), crashed
episode 139/200 | final pos error: 0.124 m | crash: False | reward: -24.4 | start jitter: 0.431 m | start yaw jitter: 3.8 deg | wind L3 (0.082N), steady-state err 0.043m, recovered in 0 steps
episode 140/200 | final pos error: 0.020 m | crash: False | reward: -13.4 | start jitter: 0.252 m | start yaw jitter: 3.3 deg | torque L3 (4.030rad/s), recovered in 0 steps
episode 141/200 | final pos error: 0.049 m | crash: False | reward: -12.8 | start jitter: 0.271 m | start yaw jitter: 14.2 deg | torque L2 (2.896rad/s), recovered in 0 steps
episode 142/200 | final pos error: 0.006 m | crash: False | reward: -9.0 | start jitter: 0.146 m | start yaw jitter: 9.0 deg | wind L5 (0.146N), steady-state err 0.026m, recovered in 0 steps
episode 143/200 | final pos error: 0.135 m | crash: True (tilt) | reward: -11.6 | start jitter: 0.315 m | start yaw jitter: 8.7 deg | torque L5 (9.143rad/s), crashed
episode 144/200 | final pos error: 0.034 m | crash: False | reward: -19.1 | start jitter: 0.432 m | start yaw jitter: 11.6 deg | wind L1 (0.034N), steady-state err 0.018m, recovered in 0 steps
episode 145/200 | final pos error: 0.032 m | crash: False | reward: -18.2 | start jitter: 0.085 m | start yaw jitter: 5.8 deg | torque L5 (11.368rad/s), recovered in 33 steps
episode 146/200 | final pos error: 0.023 m | crash: False | reward: -15.4 | start jitter: 0.371 m | start yaw jitter: 11.8 deg | wind L3 (0.078N), steady-state err 0.018m, recovered in 0 steps
episode 147/200 | final pos error: 0.183 m | crash: True (tilt) | reward: -5.7 | start jitter: 0.231 m | start yaw jitter: 10.6 deg | torque L5 (11.021rad/s), crashed
episode 148/200 | final pos error: 0.042 m | crash: False | reward: -17.1 | start jitter: 0.400 m | start yaw jitter: 4.5 deg | kick L2 (0.676m/s), recovered in 0 steps
episode 149/200 | final pos error: 0.169 m | crash: True (tilt) | reward: -11.9 | start jitter: 0.298 m | start yaw jitter: 5.0 deg | torque L5 (10.297rad/s), crashed
episode 150/200 | final pos error: 0.611 m | crash: True (tilt) | reward: -22.0 | start jitter: 0.401 m | start yaw jitter: 13.1 deg | kick L5 (1.614m/s), crashed
episode 151/200 | final pos error: 0.027 m | crash: False | reward: -16.0 | start jitter: 0.364 m | start yaw jitter: 14.9 deg | wind L3 (0.083N), steady-state err 0.029m, recovered in 0 steps
episode 152/200 | final pos error: 0.025 m | crash: False | reward: -17.6 | start jitter: 0.403 m | start yaw jitter: 5.4 deg | kick L1 (0.328m/s), recovered in 0 steps
episode 153/200 | final pos error: 0.047 m | crash: False | reward: -28.1 | start jitter: 0.365 m | start yaw jitter: 4.1 deg | kick L5 (1.682m/s), recovered in 33 steps
episode 154/200 | final pos error: 0.033 m | crash: False | reward: -16.4 | start jitter: 0.275 m | start yaw jitter: 9.4 deg | kick L3 (1.059m/s), recovered in 18 steps
episode 155/200 | final pos error: 0.023 m | crash: False | reward: -15.7 | start jitter: 0.290 m | start yaw jitter: 12.4 deg | torque L3 (4.196rad/s), recovered in 0 steps
episode 156/200 | final pos error: 0.083 m | crash: True (tilt) | reward: -11.5 | start jitter: 0.356 m | start yaw jitter: 6.8 deg | torque L5 (12.693rad/s), crashed
episode 157/200 | final pos error: 0.041 m | crash: False | reward: -18.3 | start jitter: 0.408 m | start yaw jitter: 14.3 deg | wind L3 (0.094N), steady-state err 0.024m, recovered in 0 steps
episode 158/200 | final pos error: 0.025 m | crash: False | reward: -11.8 | start jitter: 0.274 m | start yaw jitter: 5.6 deg | wind L4 (0.128N), steady-state err 0.025m, recovered in 0 steps
episode 159/200 | final pos error: 0.177 m | crash: True (tilt) | reward: -8.7 | start jitter: 0.254 m | start yaw jitter: 9.2 deg | torque L5 (12.847rad/s), crashed
episode 160/200 | final pos error: 0.650 m | crash: True (tilt) | reward: -10.8 | start jitter: 0.209 m | start yaw jitter: 5.2 deg | kick L5 (1.888m/s), crashed
episode 161/200 | final pos error: 0.033 m | crash: False | reward: -15.3 | start jitter: 0.338 m | start yaw jitter: 14.5 deg | torque L1 (1.838rad/s), recovered in 0 steps
episode 162/200 | final pos error: 0.016 m | crash: False | reward: -10.0 | start jitter: 0.118 m | start yaw jitter: 4.9 deg | kick L2 (0.772m/s), recovered in 0 steps
episode 163/200 | final pos error: 0.032 m | crash: False | reward: -10.2 | start jitter: 0.262 m | start yaw jitter: 0.4 deg | wind L1 (0.024N), steady-state err 0.024m, recovered in 0 steps
episode 164/200 | final pos error: 0.018 m | crash: False | reward: -14.0 | start jitter: 0.358 m | start yaw jitter: 5.4 deg | wind L3 (0.084N), steady-state err 0.027m, recovered in 0 steps
episode 165/200 | final pos error: 0.560 m | crash: True (tilt) | reward: -14.3 | start jitter: 0.153 m | start yaw jitter: 12.8 deg | kick L5 (1.786m/s), crashed
episode 166/200 | final pos error: 0.035 m | crash: False | reward: -15.3 | start jitter: 0.333 m | start yaw jitter: 10.8 deg | wind L4 (0.113N), steady-state err 0.027m, recovered in 0 steps
episode 167/200 | final pos error: 0.177 m | crash: False | reward: -27.8 | start jitter: 0.322 m | start yaw jitter: 9.1 deg | torque L3 (5.783rad/s), DID NOT recover in budget
episode 168/200 | final pos error: 0.092 m | crash: False | reward: -23.2 | start jitter: 0.345 m | start yaw jitter: 13.8 deg | torque L3 (5.633rad/s), recovered in 0 steps
episode 169/200 | final pos error: 0.021 m | crash: False | reward: -18.4 | start jitter: 0.375 m | start yaw jitter: 10.1 deg | kick L3 (0.833m/s), recovered in 0 steps
episode 170/200 | final pos error: 0.074 m | crash: False | reward: -12.5 | start jitter: 0.250 m | start yaw jitter: 2.8 deg | torque L1 (1.530rad/s), recovered in 0 steps
episode 171/200 | final pos error: 0.045 m | crash: False | reward: -17.3 | start jitter: 0.371 m | start yaw jitter: 2.7 deg | kick L2 (0.569m/s), recovered in 0 steps
episode 172/200 | final pos error: 0.012 m | crash: False | reward: -13.2 | start jitter: 0.375 m | start yaw jitter: 8.4 deg | wind L3 (0.099N), steady-state err 0.020m, recovered in 0 steps
episode 173/200 | final pos error: 0.430 m | crash: True (tilt) | reward: -8.7 | start jitter: 0.204 m | start yaw jitter: 9.5 deg | kick L5 (1.948m/s), crashed
episode 174/200 | final pos error: 0.323 m | crash: True (tilt) | reward: -14.8 | start jitter: 0.370 m | start yaw jitter: 8.3 deg | kick L4 (1.481m/s), crashed
episode 175/200 | final pos error: 0.030 m | crash: False | reward: -9.9 | start jitter: 0.211 m | start yaw jitter: 1.8 deg | wind L1 (0.027N), steady-state err 0.024m, recovered in 0 steps
episode 176/200 | final pos error: 0.019 m | crash: False | reward: -14.8 | start jitter: 0.390 m | start yaw jitter: 8.7 deg | torque L1 (1.606rad/s), recovered in 0 steps
episode 177/200 | final pos error: 0.323 m | crash: False | reward: -65.0 | start jitter: 0.352 m | start yaw jitter: 1.5 deg | kick L3 (1.030m/s), DID NOT recover in budget
episode 178/200 | final pos error: 0.052 m | crash: False | reward: -9.5 | start jitter: 0.262 m | start yaw jitter: 3.1 deg | torque L4 (6.027rad/s), recovered in 0 steps
episode 179/200 | final pos error: 0.045 m | crash: False | reward: -20.2 | start jitter: 0.263 m | start yaw jitter: 12.3 deg | kick L3 (1.085m/s), recovered in 26 steps
episode 180/200 | final pos error: 0.042 m | crash: False | reward: -12.1 | start jitter: 0.271 m | start yaw jitter: 2.1 deg | wind L4 (0.136N), steady-state err 0.037m, recovered in 0 steps
episode 181/200 | final pos error: 0.019 m | crash: False | reward: -23.2 | start jitter: 0.306 m | start yaw jitter: 3.8 deg | kick L4 (1.232m/s), recovered in 37 steps
episode 182/200 | final pos error: 0.218 m | crash: False | reward: -34.0 | start jitter: 0.329 m | start yaw jitter: 5.5 deg | torque L3 (5.777rad/s), recovered in 0 steps
episode 183/200 | final pos error: 0.022 m | crash: False | reward: -10.7 | start jitter: 0.238 m | start yaw jitter: 12.8 deg | wind L2 (0.070N), steady-state err 0.027m, recovered in 0 steps
episode 184/200 | final pos error: 0.069 m | crash: False | reward: -16.2 | start jitter: 0.201 m | start yaw jitter: 4.1 deg | wind L4 (0.126N), steady-state err 0.079m, recovered in 0 steps
episode 185/200 | final pos error: 0.027 m | crash: False | reward: -11.5 | start jitter: 0.304 m | start yaw jitter: 5.2 deg | wind L3 (0.071N), steady-state err 0.020m, recovered in 0 steps
episode 186/200 | final pos error: 0.102 m | crash: False | reward: -22.6 | start jitter: 0.320 m | start yaw jitter: 12.9 deg | kick L3 (0.833m/s), recovered in 0 steps
episode 187/200 | final pos error: 0.008 m | crash: False | reward: -13.2 | start jitter: 0.319 m | start yaw jitter: 7.6 deg | wind L2 (0.060N), steady-state err 0.029m, recovered in 0 steps
episode 188/200 | final pos error: 0.274 m | crash: True (tilt) | reward: -9.3 | start jitter: 0.305 m | start yaw jitter: 2.1 deg | kick L4 (1.323m/s), crashed
episode 189/200 | final pos error: 0.029 m | crash: False | reward: -16.5 | start jitter: 0.357 m | start yaw jitter: 14.9 deg | wind L4 (0.115N), steady-state err 0.030m, recovered in 0 steps
episode 190/200 | final pos error: 0.090 m | crash: False | reward: -21.6 | start jitter: 0.318 m | start yaw jitter: 12.6 deg | torque L3 (5.144rad/s), recovered in 0 steps
episode 191/200 | final pos error: 0.080 m | crash: False | reward: -14.4 | start jitter: 0.287 m | start yaw jitter: 0.3 deg | wind L5 (0.167N), steady-state err 0.029m, recovered in 0 steps
episode 192/200 | final pos error: 0.363 m | crash: True (tilt) | reward: -13.4 | start jitter: 0.339 m | start yaw jitter: 9.0 deg | kick L5 (1.504m/s), crashed
episode 193/200 | final pos error: 0.167 m | crash: False | reward: -20.1 | start jitter: 0.223 m | start yaw jitter: 9.6 deg | kick L1 (0.491m/s), recovered in 0 steps
episode 194/200 | final pos error: 0.786 m | crash: True (tilt) | reward: -15.1 | start jitter: 0.122 m | start yaw jitter: 13.7 deg | kick L5 (1.872m/s), crashed
episode 195/200 | final pos error: 0.020 m | crash: False | reward: -12.1 | start jitter: 0.290 m | start yaw jitter: 3.6 deg | torque L2 (3.882rad/s), recovered in 0 steps
episode 196/200 | final pos error: 0.021 m | crash: False | reward: -10.0 | start jitter: 0.206 m | start yaw jitter: 6.8 deg | kick L1 (0.327m/s), recovered in 0 steps
episode 197/200 | final pos error: 0.031 m | crash: False | reward: -12.4 | start jitter: 0.230 m | start yaw jitter: 10.3 deg | kick L2 (0.649m/s), recovered in 0 steps
episode 198/200 | final pos error: 0.045 m | crash: False | reward: -15.5 | start jitter: 0.182 m | start yaw jitter: 7.1 deg | kick L3 (0.860m/s), recovered in 0 steps
episode 199/200 | final pos error: 0.102 m | crash: True (tilt) | reward: -10.5 | start jitter: 0.341 m | start yaw jitter: 7.4 deg | torque L5 (9.885rad/s), crashed
episode 200/200 | final pos error: 0.035 m | crash: False | reward: -18.6 | start jitter: 0.406 m | start yaw jitter: 1.7 deg | wind L1 (0.021N), steady-state err 0.019m, recovered in 0 steps

==================================================
Episodes run:          200
Mean final pos error:  0.091 m
Crash rate:            18.5%
Mean episode reward:   -15.2
==================================================

Disturbance report (200/200 episodes had an event fire):

  --- kick (62/200 of fired episodes) ---
    Crash rate:           32.3%  (n=62)
    Recovery rate:        95.2%  (of 42 non-crashed)
    Mean recovery time:  9.0 steps (0.30s @ 30Hz)
    [FAIL] mastery gate: crash rate <10% AND recovery rate >90%
    By level: L1: n=12 crash=0% recover=100% | L2: n=6 crash=0% recover=100% | L3: n=12 crash=8% recover=82% | L4: n=14 crash=43% recover=100% | L5: n=18 crash=72% recover=100%

  --- torque (66/200 of fired episodes) ---
    Crash rate:           25.8%  (n=66)
    Recovery rate:        98.0%  (of 49 non-crashed)
    Mean recovery time:  7.1 steps (0.24s @ 30Hz)
    [FAIL] mastery gate: crash rate <10% AND recovery rate >90%
    By level: L1: n=14 crash=0% recover=100% | L2: n=12 crash=0% recover=100% | L3: n=17 crash=12% recover=93% | L4: n=9 crash=44% recover=100% | L5: n=14 crash=79% recover=100%

  --- wind (72/200 of fired episodes) ---
    Crash rate:            0.0%  (n=72)
    Recovery rate:       100.0%  (of 72 non-crashed)
    Mean recovery time:  0.0 steps (0.00s @ 30Hz)
    Mean steady-state error during wind window: 0.029 m
    [PASS] mastery gate: crash rate <10% AND recovery rate >90%
    By level: L1: n=19 crash=0% recover=100% | L2: n=11 crash=0% recover=100% | L3: n=17 crash=0% recover=100% | L4: n=15 crash=0% recover=100% | L5: n=10 crash=0% recover=100%
[registry] WARNING: hash 4a68b97b82a4... has no matching training-run record. This file's origin (config, cumulative steps, parent checkpoint) is unknown to the registry -- it may have been hand-copied, or predates the registry. Eval result is still logged, but treat provenance as unverified.
Logged to model registry (hash 4a68b97b82a4...). Query with: python -m src.weight_manager.model_registry describe model/model_weights/checkpoints/hover_stabilize_ppo_seed0_disturbance_3x5_tiltfix2_49998_steps.zip

Stage 2 criteria (docs/hover-model-plan.md):
  [PASS] mean pos error < 0.3 m
  [FAIL] crash rate < 10%

-> Stage 2 not yet reached. See docs/hover-model-plan.md for what to try next.

Tail episodes (final pos error > 0.2 m): 23/200
  episode  1 | pos error 0.474 m | reward -14.6 | start jitter 0.319 m | start yaw jitter 14.5 deg | best=0.004 m @ step 95/121 (converged then drifted) | kick L5 (1.956m/s), crashed
  episode 14 | pos error 0.707 m | reward -18.3 | start jitter 0.363 m | start yaw jitter 6.4 deg | best=0.002 m @ step 112/128 (converged then drifted) | kick L5 (1.777m/s), crashed
  episode 20 | pos error 0.674 m | reward -14.9 | start jitter 0.259 m | start yaw jitter 3.1 deg | best=0.004 m @ step 130/156 (converged then drifted) | kick L5 (1.781m/s), crashed
  episode 23 | pos error 0.297 m | reward -13.1 | start jitter 0.289 m | start yaw jitter 11.2 deg | best=0.003 m @ step 92/127 (converged then drifted) | kick L3 (1.074m/s), crashed
  episode 27 | pos error 0.221 m | reward -35.9 | start jitter 0.357 m | start yaw jitter 0.4 deg | best=0.003 m @ step 71/240 (converged then drifted) | kick L3 (1.063m/s), DID NOT recover in budget
  episode 29 | pos error 0.544 m | reward -16.8 | start jitter 0.336 m | start yaw jitter 6.1 deg | best=0.005 m @ step 101/132 (converged then drifted) | kick L5 (1.991m/s), crashed
  episode 34 | pos error 0.221 m | reward -11.4 | start jitter 0.289 m | start yaw jitter 0.5 deg | best=0.003 m @ step 68/153 (converged then drifted) | kick L4 (1.134m/s), crashed
  episode 57 | pos error 0.349 m | reward -10.3 | start jitter 0.256 m | start yaw jitter 6.6 deg | best=0.008 m @ step 54/97 (converged then drifted) | kick L4 (1.327m/s), crashed
  episode 67 | pos error 0.654 m | reward -19.4 | start jitter 0.331 m | start yaw jitter 1.5 deg | best=0.004 m @ step 76/141 (converged then drifted) | kick L5 (1.801m/s), crashed
  episode 90 | pos error 0.509 m | reward -12.8 | start jitter 0.202 m | start yaw jitter 11.6 deg | best=0.003 m @ step 124/157 (converged then drifted) | kick L4 (1.320m/s), crashed
  episode 97 | pos error 0.529 m | reward -15.2 | start jitter 0.286 m | start yaw jitter 6.7 deg | best=0.007 m @ step 117/156 (converged then drifted) | kick L4 (1.318m/s), crashed
  episode 111 | pos error 0.560 m | reward -15.5 | start jitter 0.287 m | start yaw jitter 13.0 deg | best=0.004 m @ step 87/124 (converged then drifted) | kick L5 (1.900m/s), crashed
  episode 138 | pos error 0.508 m | reward -15.9 | start jitter 0.403 m | start yaw jitter 10.5 deg | best=0.017 m @ step 62/82 (converged then drifted) | kick L5 (1.687m/s), crashed
  episode 150 | pos error 0.611 m | reward -22.0 | start jitter 0.401 m | start yaw jitter 13.1 deg | best=0.005 m @ step 54/148 (converged then drifted) | kick L5 (1.614m/s), crashed
  episode 160 | pos error 0.650 m | reward -10.8 | start jitter 0.209 m | start yaw jitter 5.2 deg | best=0.003 m @ step 81/93 (converged then drifted) | kick L5 (1.888m/s), crashed
  episode 165 | pos error 0.560 m | reward -14.3 | start jitter 0.153 m | start yaw jitter 12.8 deg | best=0.004 m @ step 54/159 (converged then drifted) | kick L5 (1.786m/s), crashed
  episode 173 | pos error 0.430 m | reward -8.7 | start jitter 0.204 m | start yaw jitter 9.5 deg | best=0.007 m @ step 52/103 (converged then drifted) | kick L5 (1.948m/s), crashed
  episode 174 | pos error 0.323 m | reward -14.8 | start jitter 0.370 m | start yaw jitter 8.3 deg | best=0.004 m @ step 51/99 (converged then drifted) | kick L4 (1.481m/s), crashed
  episode 177 | pos error 0.323 m | reward -65.0 | start jitter 0.352 m | start yaw jitter 1.5 deg | best=0.003 m @ step 48/240 (converged then drifted) | kick L3 (1.030m/s), DID NOT recover in budget
  episode 182 | pos error 0.218 m | reward -34.0 | start jitter 0.329 m | start yaw jitter 5.5 deg | best=0.007 m @ step 86/240 (converged then drifted) | torque L3 (5.777rad/s), recovered in 0 steps
  episode 188 | pos error 0.274 m | reward -9.3 | start jitter 0.305 m | start yaw jitter 2.1 deg | best=0.009 m @ step 39/74 (converged then drifted) | kick L4 (1.323m/s), crashed
  episode 192 | pos error 0.363 m | reward -13.4 | start jitter 0.339 m | start yaw jitter 9.0 deg | best=0.005 m @ step 80/105 (converged then drifted) | kick L5 (1.504m/s), crashed
  episode 194 | pos error 0.786 m | reward -15.1 | start jitter 0.122 m | start yaw jitter 13.7 deg | best=0.008 m @ step 92/153 (converged then drifted) | kick L5 (1.872m/s), crashed
  mean start jitter (tail episodes):     0.294 m
  mean start jitter (non-tail episodes): 0.294 m
  mean start yaw jitter (tail episodes):     7.5 deg
  mean start yaw jitter (non-tail episodes): 7.7 deg
  (23/23 tail episodes had a disturbance event fire -- expected overlap, not necessarily a general policy weak spot)

Correlation (start jitter vs. final pos error):     -0.04
Correlation (start yaw jitter vs. final pos error): +0.05
  -> Weak/no relationship: position jitter doesn't explain the tail.
  -> Weak/no relationship: yaw jitter doesn't explain the tail.

Neither start condition strongly predicts the tail. This leans toward a policy weak spot independent of start draw, rather than 'got an unusually hard start position.' Check the per-episode 'converged then drifted' vs 'never converged' tags above: the former points at a late-episode stability issue (reward/PID interaction, maybe survival_bonus vs. position_error_weight balance); the latter points at slow/incomplete convergence within the episode length, which more training timesteps might fix on its own. If most tail episodes also show a disturbance note, check the disturbance report above before concluding this is a general weak spot rather than a disturbance-recovery gap.

Crashed episodes: 37/200
  episode  1 | reason: tilt | final pos error 0.474 m | reward -14.6 | start jitter 0.319 m | start yaw jitter 14.5 deg | kick L5 (1.956m/s), crashed
  episode 14 | reason: tilt | final pos error 0.707 m | reward -18.3 | start jitter 0.363 m | start yaw jitter 6.4 deg | kick L5 (1.777m/s), crashed
  episode 16 | reason: tilt | final pos error 0.095 m | reward -16.1 | start jitter 0.416 m | start yaw jitter 2.5 deg | torque L5 (9.040rad/s), crashed
  episode 19 | reason: tilt | final pos error 0.054 m | reward -10.4 | start jitter 0.351 m | start yaw jitter 5.0 deg | torque L5 (12.703rad/s), crashed
  episode 20 | reason: tilt | final pos error 0.674 m | reward -14.9 | start jitter 0.259 m | start yaw jitter 3.1 deg | kick L5 (1.781m/s), crashed
  episode 23 | reason: tilt | final pos error 0.297 m | reward -13.1 | start jitter 0.289 m | start yaw jitter 11.2 deg | kick L3 (1.074m/s), crashed
  episode 29 | reason: tilt | final pos error 0.544 m | reward -16.8 | start jitter 0.336 m | start yaw jitter 6.1 deg | kick L5 (1.991m/s), crashed
  episode 34 | reason: tilt | final pos error 0.221 m | reward -11.4 | start jitter 0.289 m | start yaw jitter 0.5 deg | kick L4 (1.134m/s), crashed
  episode 50 | reason: tilt | final pos error 0.156 m | reward -11.7 | start jitter 0.358 m | start yaw jitter 9.6 deg | torque L5 (10.176rad/s), crashed
  episode 51 | reason: tilt | final pos error 0.120 m | reward -5.5 | start jitter 0.121 m | start yaw jitter 5.3 deg | torque L3 (4.775rad/s), crashed
  episode 57 | reason: tilt | final pos error 0.349 m | reward -10.3 | start jitter 0.256 m | start yaw jitter 6.6 deg | kick L4 (1.327m/s), crashed
  episode 64 | reason: tilt | final pos error 0.122 m | reward -8.4 | start jitter 0.244 m | start yaw jitter 3.7 deg | torque L5 (9.924rad/s), crashed
  episode 67 | reason: tilt | final pos error 0.654 m | reward -19.4 | start jitter 0.331 m | start yaw jitter 1.5 deg | kick L5 (1.801m/s), crashed
  episode 90 | reason: tilt | final pos error 0.509 m | reward -12.8 | start jitter 0.202 m | start yaw jitter 11.6 deg | kick L4 (1.320m/s), crashed
  episode 94 | reason: tilt | final pos error 0.071 m | reward -10.7 | start jitter 0.312 m | start yaw jitter 12.6 deg | torque L3 (5.529rad/s), crashed
  episode 97 | reason: tilt | final pos error 0.529 m | reward -15.2 | start jitter 0.286 m | start yaw jitter 6.7 deg | kick L4 (1.318m/s), crashed
  episode 101 | reason: tilt | final pos error 0.126 m | reward -10.8 | start jitter 0.297 m | start yaw jitter 13.2 deg | torque L4 (6.675rad/s), crashed
  episode 109 | reason: tilt | final pos error 0.105 m | reward -10.1 | start jitter 0.287 m | start yaw jitter 2.7 deg | torque L4 (7.364rad/s), crashed
  episode 110 | reason: tilt | final pos error 0.122 m | reward -7.4 | start jitter 0.252 m | start yaw jitter 10.4 deg | torque L4 (8.826rad/s), crashed
  episode 111 | reason: tilt | final pos error 0.560 m | reward -15.5 | start jitter 0.287 m | start yaw jitter 13.0 deg | kick L5 (1.900m/s), crashed
  episode 120 | reason: tilt | final pos error 0.146 m | reward -10.8 | start jitter 0.341 m | start yaw jitter 3.5 deg | torque L5 (11.187rad/s), crashed
  episode 130 | reason: tilt | final pos error 0.084 m | reward -8.3 | start jitter 0.294 m | start yaw jitter 14.5 deg | torque L4 (6.076rad/s), crashed
  episode 138 | reason: tilt | final pos error 0.508 m | reward -15.9 | start jitter 0.403 m | start yaw jitter 10.5 deg | kick L5 (1.687m/s), crashed
  episode 143 | reason: tilt | final pos error 0.135 m | reward -11.6 | start jitter 0.315 m | start yaw jitter 8.7 deg | torque L5 (9.143rad/s), crashed
  episode 147 | reason: tilt | final pos error 0.183 m | reward -5.7 | start jitter 0.231 m | start yaw jitter 10.6 deg | torque L5 (11.021rad/s), crashed
  episode 149 | reason: tilt | final pos error 0.169 m | reward -11.9 | start jitter 0.298 m | start yaw jitter 5.0 deg | torque L5 (10.297rad/s), crashed
  episode 150 | reason: tilt | final pos error 0.611 m | reward -22.0 | start jitter 0.401 m | start yaw jitter 13.1 deg | kick L5 (1.614m/s), crashed
  episode 156 | reason: tilt | final pos error 0.083 m | reward -11.5 | start jitter 0.356 m | start yaw jitter 6.8 deg | torque L5 (12.693rad/s), crashed
  episode 159 | reason: tilt | final pos error 0.177 m | reward -8.7 | start jitter 0.254 m | start yaw jitter 9.2 deg | torque L5 (12.847rad/s), crashed
  episode 160 | reason: tilt | final pos error 0.650 m | reward -10.8 | start jitter 0.209 m | start yaw jitter 5.2 deg | kick L5 (1.888m/s), crashed
  episode 165 | reason: tilt | final pos error 0.560 m | reward -14.3 | start jitter 0.153 m | start yaw jitter 12.8 deg | kick L5 (1.786m/s), crashed
  episode 173 | reason: tilt | final pos error 0.430 m | reward -8.7 | start jitter 0.204 m | start yaw jitter 9.5 deg | kick L5 (1.948m/s), crashed
  episode 174 | reason: tilt | final pos error 0.323 m | reward -14.8 | start jitter 0.370 m | start yaw jitter 8.3 deg | kick L4 (1.481m/s), crashed
  episode 188 | reason: tilt | final pos error 0.274 m | reward -9.3 | start jitter 0.305 m | start yaw jitter 2.1 deg | kick L4 (1.323m/s), crashed
  episode 192 | reason: tilt | final pos error 0.363 m | reward -13.4 | start jitter 0.339 m | start yaw jitter 9.0 deg | kick L5 (1.504m/s), crashed
  episode 194 | reason: tilt | final pos error 0.786 m | reward -15.1 | start jitter 0.122 m | start yaw jitter 13.7 deg | kick L5 (1.872m/s), crashed
  episode 199 | reason: tilt | final pos error 0.102 m | reward -10.5 | start jitter 0.341 m | start yaw jitter 7.4 deg | torque L5 (9.885rad/s), crashed
  37/37 crashes had a disturbance event fire. Crashes matter independently of the position-error tail — a policy that rarely-but-genuinely crashes is a different (and more serious) problem than one that just converges slowly. Worth tracking whether this reproduces on other seeds/eval runs before assuming it's a one-off.
```

### hover_stabilize_ppo_seed0_disturbance_3x5_tiltfix3 @ 149994 steps
```
Applied stage preset 'disturbance_3x5' for evaluation: {'disturbance_enabled': True, 'disturbance_types_active': ('kick', 'torque', 'wind')}

[INFO] BaseAviary.__init__() loaded parameters from the drone's .urdf:
[INFO] m 0.027000, L 0.039700,
[INFO] ixx 0.000014, iyy 0.000014, izz 0.000022,
[INFO] kf 3.160000e-10, km 7.940000e-12,
[INFO] t2w 2.250000, max_speed_kmh 30.000000,
[INFO] gnd_eff_coeff 11.368590, prop_radius 0.023135,
[INFO] drag_xy_coeff 0.000001, drag_z_coeff 0.000001,
[INFO] dw_coeff_1 2267.180000, dw_coeff_2 0.160000, dw_coeff_3 -0.110000
episode  1/200 | final pos error: 0.533 m | crash: True (tilt) | reward: -14.7 | start jitter: 0.319 m | start yaw jitter: 14.5 deg | kick L5 (1.956m/s), crashed
episode  2/200 | final pos error: 0.020 m | crash: False | reward: -17.5 | start jitter: 0.413 m | start yaw jitter: 14.0 deg | wind L4 (0.107N), steady-state err 0.021m, recovered in 0 steps
episode  3/200 | final pos error: 0.020 m | crash: False | reward: -18.3 | start jitter: 0.365 m | start yaw jitter: 5.1 deg | torque L4 (7.846rad/s), recovered in 0 steps
episode  4/200 | final pos error: 0.017 m | crash: False | reward: -7.4 | start jitter: 0.159 m | start yaw jitter: 10.9 deg | wind L3 (0.086N), steady-state err 0.018m, recovered in 0 steps
episode  5/200 | final pos error: 0.021 m | crash: False | reward: -11.8 | start jitter: 0.277 m | start yaw jitter: 5.3 deg | wind L3 (0.080N), steady-state err 0.018m, recovered in 0 steps
episode  6/200 | final pos error: 0.164 m | crash: True (tilt) | reward: -14.6 | start jitter: 0.363 m | start yaw jitter: 7.8 deg | torque L4 (6.176rad/s), crashed
episode  7/200 | final pos error: 0.015 m | crash: False | reward: -13.6 | start jitter: 0.361 m | start yaw jitter: 2.9 deg | wind L1 (0.022N), steady-state err 0.020m, recovered in 0 steps
episode  8/200 | final pos error: 0.025 m | crash: False | reward: -17.6 | start jitter: 0.365 m | start yaw jitter: 3.9 deg | kick L4 (1.276m/s), recovered in 0 steps
episode  9/200 | final pos error: 0.022 m | crash: False | reward: -22.0 | start jitter: 0.312 m | start yaw jitter: 0.1 deg | torque L3 (5.572rad/s), recovered in 30 steps
episode 10/200 | final pos error: 0.020 m | crash: False | reward: -19.5 | start jitter: 0.372 m | start yaw jitter: 14.0 deg | wind L5 (0.175N), steady-state err 0.038m, recovered in 0 steps
episode 11/200 | final pos error: 0.018 m | crash: False | reward: -18.1 | start jitter: 0.415 m | start yaw jitter: 0.6 deg | kick L2 (0.741m/s), recovered in 0 steps
episode 12/200 | final pos error: 0.025 m | crash: False | reward: -26.1 | start jitter: 0.403 m | start yaw jitter: 3.4 deg | torque L3 (5.438rad/s), recovered in 28 steps
episode 13/200 | final pos error: 0.006 m | crash: False | reward: -18.0 | start jitter: 0.420 m | start yaw jitter: 13.0 deg | torque L2 (2.861rad/s), recovered in 0 steps
episode 14/200 | final pos error: 0.788 m | crash: True (tilt) | reward: -19.8 | start jitter: 0.363 m | start yaw jitter: 6.4 deg | kick L5 (1.777m/s), crashed
episode 15/200 | final pos error: 0.021 m | crash: False | reward: -13.8 | start jitter: 0.212 m | start yaw jitter: 13.8 deg | torque L2 (3.105rad/s), recovered in 0 steps
episode 16/200 | final pos error: 0.186 m | crash: True (tilt) | reward: -17.5 | start jitter: 0.416 m | start yaw jitter: 2.5 deg | torque L5 (9.040rad/s), crashed
episode 17/200 | final pos error: 0.016 m | crash: False | reward: -14.6 | start jitter: 0.323 m | start yaw jitter: 11.2 deg | kick L5 (1.530m/s), recovered in 0 steps
episode 18/200 | final pos error: 0.009 m | crash: False | reward: -10.7 | start jitter: 0.244 m | start yaw jitter: 10.9 deg | wind L4 (0.120N), steady-state err 0.027m, recovered in 0 steps
episode 19/200 | final pos error: 0.246 m | crash: False | reward: -46.5 | start jitter: 0.351 m | start yaw jitter: 5.0 deg | torque L5 (12.703rad/s), DID NOT recover in budget
episode 20/200 | final pos error: 0.477 m | crash: True (tilt) | reward: -11.3 | start jitter: 0.259 m | start yaw jitter: 3.1 deg | kick L5 (1.781m/s), crashed
episode 21/200 | final pos error: 0.030 m | crash: False | reward: -17.0 | start jitter: 0.380 m | start yaw jitter: 2.1 deg | torque L1 (1.773rad/s), recovered in 0 steps
episode 22/200 | final pos error: 0.040 m | crash: False | reward: -25.6 | start jitter: 0.215 m | start yaw jitter: 3.1 deg | kick L5 (1.536m/s), DID NOT recover in budget
episode 23/200 | final pos error: 0.030 m | crash: False | reward: -19.8 | start jitter: 0.289 m | start yaw jitter: 11.2 deg | kick L3 (1.074m/s), recovered in 21 steps
episode 24/200 | final pos error: 0.017 m | crash: False | reward: -15.4 | start jitter: 0.349 m | start yaw jitter: 0.1 deg | kick L1 (0.435m/s), recovered in 0 steps
episode 25/200 | final pos error: 0.053 m | crash: False | reward: -14.7 | start jitter: 0.300 m | start yaw jitter: 2.4 deg | kick L1 (0.462m/s), recovered in 0 steps
episode 26/200 | final pos error: 0.015 m | crash: False | reward: -13.2 | start jitter: 0.261 m | start yaw jitter: 3.1 deg | wind L4 (0.137N), steady-state err 0.039m, recovered in 0 steps
episode 27/200 | final pos error: 0.032 m | crash: False | reward: -20.8 | start jitter: 0.357 m | start yaw jitter: 0.4 deg | kick L3 (1.063m/s), recovered in 0 steps
episode 28/200 | final pos error: 0.006 m | crash: False | reward: -10.7 | start jitter: 0.265 m | start yaw jitter: 4.1 deg | wind L4 (0.122N), steady-state err 0.029m, recovered in 0 steps
episode 29/200 | final pos error: 0.314 m | crash: True (tilt) | reward: -13.5 | start jitter: 0.336 m | start yaw jitter: 6.1 deg | kick L5 (1.991m/s), crashed
episode 30/200 | final pos error: 0.036 m | crash: False | reward: -11.7 | start jitter: 0.291 m | start yaw jitter: 0.7 deg | wind L2 (0.061N), steady-state err 0.019m, recovered in 0 steps
episode 31/200 | final pos error: 0.274 m | crash: True (tilt) | reward: -13.5 | start jitter: 0.359 m | start yaw jitter: 0.7 deg | kick L3 (0.927m/s), crashed
episode 32/200 | final pos error: 0.029 m | crash: False | reward: -13.6 | start jitter: 0.311 m | start yaw jitter: 13.8 deg | wind L1 (0.031N), steady-state err 0.019m, recovered in 0 steps
episode 33/200 | final pos error: 0.044 m | crash: False | reward: -17.8 | start jitter: 0.369 m | start yaw jitter: 3.2 deg | wind L4 (0.118N), steady-state err 0.030m, recovered in 0 steps
episode 34/200 | final pos error: 0.564 m | crash: True (tilt) | reward: -16.6 | start jitter: 0.289 m | start yaw jitter: 0.5 deg | kick L4 (1.134m/s), crashed
episode 35/200 | final pos error: 0.046 m | crash: False | reward: -8.2 | start jitter: 0.168 m | start yaw jitter: 13.3 deg | torque L1 (1.512rad/s), recovered in 0 steps
episode 36/200 | final pos error: 0.018 m | crash: False | reward: -8.2 | start jitter: 0.173 m | start yaw jitter: 14.6 deg | wind L1 (0.034N), steady-state err 0.014m, recovered in 0 steps
episode 37/200 | final pos error: 0.009 m | crash: False | reward: -10.2 | start jitter: 0.171 m | start yaw jitter: 14.8 deg | wind L5 (0.146N), steady-state err 0.036m, recovered in 0 steps
episode 38/200 | final pos error: 0.015 m | crash: False | reward: -12.0 | start jitter: 0.302 m | start yaw jitter: 9.7 deg | wind L2 (0.054N), steady-state err 0.021m, recovered in 0 steps
episode 39/200 | final pos error: 0.020 m | crash: False | reward: -13.7 | start jitter: 0.344 m | start yaw jitter: 11.8 deg | wind L3 (0.082N), steady-state err 0.022m, recovered in 0 steps
episode 40/200 | final pos error: 0.011 m | crash: False | reward: -12.5 | start jitter: 0.266 m | start yaw jitter: 2.2 deg | wind L5 (0.148N), steady-state err 0.027m, recovered in 0 steps
episode 41/200 | final pos error: 0.262 m | crash: True (tilt) | reward: -9.4 | start jitter: 0.205 m | start yaw jitter: 9.7 deg | kick L4 (1.435m/s), crashed
episode 42/200 | final pos error: 0.016 m | crash: False | reward: -14.5 | start jitter: 0.348 m | start yaw jitter: 2.2 deg | wind L5 (0.148N), steady-state err 0.036m, recovered in 0 steps
episode 43/200 | final pos error: 0.017 m | crash: False | reward: -14.9 | start jitter: 0.343 m | start yaw jitter: 9.9 deg | torque L1 (1.586rad/s), recovered in 0 steps
episode 44/200 | final pos error: 0.029 m | crash: False | reward: -16.8 | start jitter: 0.391 m | start yaw jitter: 11.7 deg | torque L2 (2.713rad/s), recovered in 0 steps
episode 45/200 | final pos error: 0.320 m | crash: True (tilt) | reward: -11.0 | start jitter: 0.204 m | start yaw jitter: 5.2 deg | kick L4 (1.144m/s), crashed
episode 46/200 | final pos error: 0.024 m | crash: False | reward: -7.9 | start jitter: 0.130 m | start yaw jitter: 8.1 deg | wind L3 (0.091N), steady-state err 0.023m, recovered in 0 steps
episode 47/200 | final pos error: 0.014 m | crash: False | reward: -9.3 | start jitter: 0.206 m | start yaw jitter: 0.7 deg | wind L2 (0.045N), steady-state err 0.020m, recovered in 0 steps
episode 48/200 | final pos error: 0.028 m | crash: False | reward: -15.3 | start jitter: 0.269 m | start yaw jitter: 3.4 deg | torque L3 (5.754rad/s), recovered in 0 steps
episode 49/200 | final pos error: 0.045 m | crash: False | reward: -8.8 | start jitter: 0.202 m | start yaw jitter: 9.3 deg | torque L1 (1.506rad/s), recovered in 0 steps
episode 50/200 | final pos error: 0.139 m | crash: True (tilt) | reward: -11.2 | start jitter: 0.358 m | start yaw jitter: 9.6 deg | torque L5 (10.176rad/s), crashed
episode 51/200 | final pos error: 0.186 m | crash: True (tilt) | reward: -7.1 | start jitter: 0.121 m | start yaw jitter: 5.3 deg | torque L3 (4.775rad/s), crashed
episode 52/200 | final pos error: 0.016 m | crash: False | reward: -7.6 | start jitter: 0.104 m | start yaw jitter: 14.6 deg | torque L1 (1.843rad/s), recovered in 0 steps
episode 53/200 | final pos error: 0.014 m | crash: False | reward: -16.0 | start jitter: 0.326 m | start yaw jitter: 9.5 deg | wind L5 (0.176N), steady-state err 0.028m, recovered in 0 steps
episode 54/200 | final pos error: 0.009 m | crash: False | reward: -12.3 | start jitter: 0.315 m | start yaw jitter: 1.8 deg | wind L2 (0.055N), steady-state err 0.020m, recovered in 0 steps
episode 55/200 | final pos error: 0.025 m | crash: False | reward: -19.0 | start jitter: 0.364 m | start yaw jitter: 7.9 deg | kick L4 (1.230m/s), recovered in 12 steps
episode 56/200 | final pos error: 0.006 m | crash: False | reward: -12.5 | start jitter: 0.279 m | start yaw jitter: 0.4 deg | kick L1 (0.456m/s), recovered in 0 steps
episode 57/200 | final pos error: 0.600 m | crash: True (tilt) | reward: -12.8 | start jitter: 0.256 m | start yaw jitter: 6.6 deg | kick L4 (1.327m/s), crashed
episode 58/200 | final pos error: 0.012 m | crash: False | reward: -11.6 | start jitter: 0.233 m | start yaw jitter: 10.9 deg | kick L1 (0.435m/s), recovered in 0 steps
episode 59/200 | final pos error: 0.019 m | crash: False | reward: -13.7 | start jitter: 0.367 m | start yaw jitter: 12.7 deg | wind L3 (0.075N), steady-state err 0.024m, recovered in 0 steps
episode 60/200 | final pos error: 0.014 m | crash: False | reward: -14.9 | start jitter: 0.332 m | start yaw jitter: 2.5 deg | torque L2 (3.222rad/s), recovered in 0 steps
episode 61/200 | final pos error: 0.029 m | crash: False | reward: -8.6 | start jitter: 0.232 m | start yaw jitter: 2.7 deg | wind L1 (0.022N), steady-state err 0.018m, recovered in 0 steps
episode 62/200 | final pos error: 0.013 m | crash: False | reward: -8.9 | start jitter: 0.155 m | start yaw jitter: 6.3 deg | wind L2 (0.067N), steady-state err 0.018m, recovered in 0 steps
episode 63/200 | final pos error: 0.006 m | crash: False | reward: -7.6 | start jitter: 0.181 m | start yaw jitter: 2.6 deg | torque L1 (1.669rad/s), recovered in 0 steps
episode 64/200 | final pos error: 0.139 m | crash: True (tilt) | reward: -8.2 | start jitter: 0.244 m | start yaw jitter: 3.7 deg | torque L5 (9.924rad/s), crashed
episode 65/200 | final pos error: 0.008 m | crash: False | reward: -9.4 | start jitter: 0.243 m | start yaw jitter: 7.5 deg | wind L1 (0.034N), steady-state err 0.018m, recovered in 0 steps
episode 66/200 | final pos error: 0.019 m | crash: False | reward: -20.7 | start jitter: 0.431 m | start yaw jitter: 7.7 deg | kick L1 (0.405m/s), recovered in 0 steps
episode 67/200 | final pos error: 0.352 m | crash: True (tilt) | reward: -14.9 | start jitter: 0.331 m | start yaw jitter: 1.5 deg | kick L5 (1.801m/s), crashed
episode 68/200 | final pos error: 0.065 m | crash: False | reward: -9.2 | start jitter: 0.194 m | start yaw jitter: 9.8 deg | torque L2 (3.778rad/s), recovered in 0 steps
episode 69/200 | final pos error: 0.019 m | crash: False | reward: -18.5 | start jitter: 0.386 m | start yaw jitter: 8.4 deg | torque L3 (4.260rad/s), recovered in 0 steps
episode 70/200 | final pos error: 0.015 m | crash: False | reward: -31.3 | start jitter: 0.283 m | start yaw jitter: 13.5 deg | kick L5 (1.533m/s), recovered in 49 steps
episode 71/200 | final pos error: 0.010 m | crash: False | reward: -18.5 | start jitter: 0.209 m | start yaw jitter: 7.6 deg | kick L4 (1.290m/s), recovered in 28 steps
episode 72/200 | final pos error: 0.051 m | crash: False | reward: -16.7 | start jitter: 0.313 m | start yaw jitter: 8.2 deg | wind L2 (0.066N), steady-state err 0.025m, recovered in 0 steps
episode 73/200 | final pos error: 0.015 m | crash: False | reward: -14.6 | start jitter: 0.295 m | start yaw jitter: 10.1 deg | kick L1 (0.444m/s), recovered in 0 steps
episode 74/200 | final pos error: 0.023 m | crash: False | reward: -9.3 | start jitter: 0.193 m | start yaw jitter: 10.8 deg | wind L1 (0.037N), steady-state err 0.022m, recovered in 0 steps
episode 75/200 | final pos error: 0.038 m | crash: False | reward: -18.4 | start jitter: 0.406 m | start yaw jitter: 11.3 deg | kick L1 (0.423m/s), recovered in 0 steps
episode 76/200 | final pos error: 0.016 m | crash: False | reward: -13.7 | start jitter: 0.306 m | start yaw jitter: 3.1 deg | wind L1 (0.029N), steady-state err 0.015m, recovered in 0 steps
episode 77/200 | final pos error: 0.019 m | crash: False | reward: -17.2 | start jitter: 0.301 m | start yaw jitter: 9.5 deg | torque L4 (6.815rad/s), recovered in 0 steps
episode 78/200 | final pos error: 0.028 m | crash: False | reward: -19.7 | start jitter: 0.415 m | start yaw jitter: 10.4 deg | kick L4 (1.199m/s), recovered in 0 steps
episode 79/200 | final pos error: 0.020 m | crash: False | reward: -16.7 | start jitter: 0.264 m | start yaw jitter: 5.2 deg | torque L4 (8.535rad/s), recovered in 0 steps
episode 80/200 | final pos error: 0.038 m | crash: False | reward: -14.5 | start jitter: 0.335 m | start yaw jitter: 12.4 deg | wind L2 (0.046N), steady-state err 0.037m, recovered in 0 steps
episode 81/200 | final pos error: 0.008 m | crash: False | reward: -11.5 | start jitter: 0.233 m | start yaw jitter: 3.3 deg | wind L1 (0.022N), steady-state err 0.020m, recovered in 0 steps
episode 82/200 | final pos error: 0.004 m | crash: False | reward: -10.6 | start jitter: 0.221 m | start yaw jitter: 13.2 deg | wind L4 (0.117N), steady-state err 0.022m, recovered in 0 steps
episode 83/200 | final pos error: 0.035 m | crash: False | reward: -14.4 | start jitter: 0.297 m | start yaw jitter: 3.8 deg | torque L2 (2.819rad/s), recovered in 0 steps
episode 84/200 | final pos error: 0.013 m | crash: False | reward: -12.3 | start jitter: 0.266 m | start yaw jitter: 12.7 deg | torque L3 (4.654rad/s), recovered in 0 steps
episode 85/200 | final pos error: 0.033 m | crash: False | reward: -16.5 | start jitter: 0.415 m | start yaw jitter: 3.9 deg | wind L2 (0.052N), steady-state err 0.020m, recovered in 0 steps
episode 86/200 | final pos error: 0.004 m | crash: False | reward: -11.9 | start jitter: 0.249 m | start yaw jitter: 4.3 deg | torque L3 (4.260rad/s), recovered in 0 steps
episode 87/200 | final pos error: 0.019 m | crash: False | reward: -15.3 | start jitter: 0.347 m | start yaw jitter: 14.0 deg | kick L1 (0.455m/s), recovered in 0 steps
episode 88/200 | final pos error: 0.012 m | crash: False | reward: -6.7 | start jitter: 0.128 m | start yaw jitter: 1.3 deg | wind L4 (0.132N), steady-state err 0.029m, recovered in 0 steps
episode 89/200 | final pos error: 0.019 m | crash: False | reward: -10.0 | start jitter: 0.216 m | start yaw jitter: 10.7 deg | wind L1 (0.033N), steady-state err 0.019m, recovered in 0 steps
episode 90/200 | final pos error: 0.259 m | crash: True (tilt) | reward: -9.2 | start jitter: 0.202 m | start yaw jitter: 11.6 deg | kick L4 (1.320m/s), crashed
episode 91/200 | final pos error: 0.054 m | crash: False | reward: -13.5 | start jitter: 0.298 m | start yaw jitter: 14.3 deg | wind L4 (0.116N), steady-state err 0.041m, recovered in 0 steps
episode 92/200 | final pos error: 0.029 m | crash: False | reward: -13.5 | start jitter: 0.210 m | start yaw jitter: 10.3 deg | torque L5 (11.064rad/s), recovered in 0 steps
episode 93/200 | final pos error: 0.012 m | crash: False | reward: -14.7 | start jitter: 0.322 m | start yaw jitter: 1.5 deg | torque L2 (3.056rad/s), recovered in 0 steps
episode 94/200 | final pos error: 0.100 m | crash: True (tilt) | reward: -11.2 | start jitter: 0.312 m | start yaw jitter: 12.6 deg | torque L3 (5.529rad/s), crashed
episode 95/200 | final pos error: 0.007 m | crash: False | reward: -12.9 | start jitter: 0.314 m | start yaw jitter: 4.3 deg | wind L5 (0.152N), steady-state err 0.024m, recovered in 0 steps
episode 96/200 | final pos error: 0.032 m | crash: False | reward: -18.8 | start jitter: 0.305 m | start yaw jitter: 15.0 deg | torque L3 (5.216rad/s), recovered in 26 steps
episode 97/200 | final pos error: 0.526 m | crash: True (tilt) | reward: -14.7 | start jitter: 0.286 m | start yaw jitter: 6.7 deg | kick L4 (1.318m/s), crashed
episode 98/200 | final pos error: 0.026 m | crash: False | reward: -12.1 | start jitter: 0.206 m | start yaw jitter: 5.4 deg | kick L3 (0.824m/s), recovered in 0 steps
episode 99/200 | final pos error: 0.019 m | crash: False | reward: -10.5 | start jitter: 0.265 m | start yaw jitter: 8.1 deg | wind L1 (0.034N), steady-state err 0.019m, recovered in 0 steps
episode 100/200 | final pos error: 0.024 m | crash: False | reward: -16.8 | start jitter: 0.390 m | start yaw jitter: 7.3 deg | torque L2 (3.639rad/s), recovered in 0 steps
episode 101/200 | final pos error: 0.021 m | crash: False | reward: -16.6 | start jitter: 0.297 m | start yaw jitter: 13.2 deg | torque L4 (6.675rad/s), recovered in 0 steps
episode 102/200 | final pos error: 0.096 m | crash: False | reward: -29.3 | start jitter: 0.299 m | start yaw jitter: 4.0 deg | torque L3 (5.655rad/s), DID NOT recover in budget
episode 103/200 | final pos error: 0.020 m | crash: False | reward: -14.2 | start jitter: 0.338 m | start yaw jitter: 5.5 deg | wind L4 (0.126N), steady-state err 0.026m, recovered in 0 steps
episode 104/200 | final pos error: 0.014 m | crash: False | reward: -13.0 | start jitter: 0.339 m | start yaw jitter: 10.1 deg | torque L2 (2.026rad/s), recovered in 0 steps
episode 105/200 | final pos error: 0.063 m | crash: False | reward: -11.9 | start jitter: 0.252 m | start yaw jitter: 7.0 deg | torque L1 (1.266rad/s), recovered in 0 steps
episode 106/200 | final pos error: 0.269 m | crash: True (tilt) | reward: -16.9 | start jitter: 0.415 m | start yaw jitter: 12.2 deg | kick L3 (1.000m/s), crashed
episode 107/200 | final pos error: 0.011 m | crash: False | reward: -9.3 | start jitter: 0.221 m | start yaw jitter: 10.9 deg | wind L1 (0.030N), steady-state err 0.024m, recovered in 0 steps
episode 108/200 | final pos error: 0.021 m | crash: False | reward: -7.8 | start jitter: 0.163 m | start yaw jitter: 5.8 deg | wind L3 (0.094N), steady-state err 0.025m, recovered in 0 steps
episode 109/200 | final pos error: 0.130 m | crash: True (tilt) | reward: -11.5 | start jitter: 0.287 m | start yaw jitter: 2.7 deg | torque L4 (7.364rad/s), crashed
episode 110/200 | final pos error: 0.157 m | crash: True (tilt) | reward: -7.3 | start jitter: 0.252 m | start yaw jitter: 10.4 deg | torque L4 (8.826rad/s), crashed
episode 111/200 | final pos error: 0.594 m | crash: True (tilt) | reward: -15.5 | start jitter: 0.287 m | start yaw jitter: 13.0 deg | kick L5 (1.900m/s), crashed
episode 112/200 | final pos error: 0.700 m | crash: True (tilt) | reward: -18.6 | start jitter: 0.358 m | start yaw jitter: 11.0 deg | kick L5 (1.872m/s), crashed
episode 113/200 | final pos error: 0.035 m | crash: False | reward: -11.0 | start jitter: 0.234 m | start yaw jitter: 10.8 deg | wind L3 (0.080N), steady-state err 0.028m, recovered in 0 steps
episode 114/200 | final pos error: 0.032 m | crash: False | reward: -9.5 | start jitter: 0.230 m | start yaw jitter: 8.0 deg | wind L3 (0.074N), steady-state err 0.021m, recovered in 0 steps
episode 115/200 | final pos error: 0.084 m | crash: False | reward: -13.4 | start jitter: 0.239 m | start yaw jitter: 12.1 deg | wind L1 (0.036N), steady-state err 0.029m, recovered in 0 steps
episode 116/200 | final pos error: 0.008 m | crash: False | reward: -16.2 | start jitter: 0.339 m | start yaw jitter: 11.0 deg | kick L3 (0.860m/s), recovered in 0 steps
episode 117/200 | final pos error: 0.036 m | crash: False | reward: -14.7 | start jitter: 0.217 m | start yaw jitter: 1.6 deg | wind L2 (0.063N), steady-state err 0.061m, recovered in 0 steps
episode 118/200 | final pos error: 0.086 m | crash: False | reward: -23.7 | start jitter: 0.312 m | start yaw jitter: 5.8 deg | torque L5 (11.807rad/s), recovered in 0 steps
episode 119/200 | final pos error: 0.052 m | crash: False | reward: -16.7 | start jitter: 0.430 m | start yaw jitter: 14.0 deg | torque L1 (1.833rad/s), recovered in 0 steps
episode 120/200 | final pos error: 0.153 m | crash: True (tilt) | reward: -10.9 | start jitter: 0.341 m | start yaw jitter: 3.5 deg | torque L5 (11.187rad/s), crashed
episode 121/200 | final pos error: 0.017 m | crash: False | reward: -9.3 | start jitter: 0.213 m | start yaw jitter: 12.5 deg | wind L4 (0.134N), steady-state err 0.021m, recovered in 0 steps
episode 122/200 | final pos error: 0.030 m | crash: False | reward: -14.9 | start jitter: 0.344 m | start yaw jitter: 9.7 deg | wind L1 (0.036N), steady-state err 0.017m, recovered in 0 steps
episode 123/200 | final pos error: 0.009 m | crash: False | reward: -18.8 | start jitter: 0.340 m | start yaw jitter: 7.2 deg | kick L4 (1.399m/s), recovered in 18 steps
episode 124/200 | final pos error: 0.010 m | crash: False | reward: -16.1 | start jitter: 0.392 m | start yaw jitter: 3.5 deg | wind L1 (0.021N), steady-state err 0.020m, recovered in 0 steps
episode 125/200 | final pos error: 0.025 m | crash: False | reward: -14.7 | start jitter: 0.326 m | start yaw jitter: 9.7 deg | wind L3 (0.074N), steady-state err 0.043m, recovered in 0 steps
episode 126/200 | final pos error: 0.038 m | crash: False | reward: -16.1 | start jitter: 0.340 m | start yaw jitter: 7.9 deg | torque L1 (1.878rad/s), recovered in 0 steps
episode 127/200 | final pos error: 0.040 m | crash: False | reward: -8.4 | start jitter: 0.137 m | start yaw jitter: 13.8 deg | kick L1 (0.318m/s), recovered in 0 steps
episode 128/200 | final pos error: 0.021 m | crash: False | reward: -9.0 | start jitter: 0.235 m | start yaw jitter: 5.3 deg | wind L3 (0.086N), steady-state err 0.024m, recovered in 0 steps
episode 129/200 | final pos error: 0.021 m | crash: False | reward: -15.8 | start jitter: 0.333 m | start yaw jitter: 9.1 deg | kick L2 (0.513m/s), recovered in 0 steps
episode 130/200 | final pos error: 0.280 m | crash: True (tilt) | reward: -11.9 | start jitter: 0.294 m | start yaw jitter: 14.5 deg | torque L4 (6.076rad/s), crashed
episode 131/200 | final pos error: 0.388 m | crash: True (tilt) | reward: -19.9 | start jitter: 0.372 m | start yaw jitter: 12.9 deg | torque L2 (3.686rad/s), crashed
episode 132/200 | final pos error: 0.024 m | crash: False | reward: -11.0 | start jitter: 0.286 m | start yaw jitter: 1.3 deg | torque L1 (1.363rad/s), recovered in 0 steps
episode 133/200 | final pos error: 0.016 m | crash: False | reward: -14.0 | start jitter: 0.348 m | start yaw jitter: 2.8 deg | torque L1 (1.592rad/s), recovered in 0 steps
episode 134/200 | final pos error: 0.017 m | crash: False | reward: -15.2 | start jitter: 0.328 m | start yaw jitter: 2.5 deg | wind L5 (0.180N), steady-state err 0.033m, recovered in 0 steps
episode 135/200 | final pos error: 0.016 m | crash: False | reward: -17.9 | start jitter: 0.431 m | start yaw jitter: 12.6 deg | wind L1 (0.031N), steady-state err 0.018m, recovered in 0 steps
episode 136/200 | final pos error: 0.037 m | crash: False | reward: -8.5 | start jitter: 0.215 m | start yaw jitter: 10.8 deg | wind L5 (0.158N), steady-state err 0.030m, recovered in 0 steps
episode 137/200 | final pos error: 0.007 m | crash: False | reward: -16.8 | start jitter: 0.262 m | start yaw jitter: 4.9 deg | torque L3 (4.599rad/s), recovered in 26 steps
episode 138/200 | final pos error: 0.568 m | crash: True (tilt) | reward: -19.2 | start jitter: 0.403 m | start yaw jitter: 10.5 deg | kick L5 (1.687m/s), crashed
episode 139/200 | final pos error: 0.037 m | crash: False | reward: -18.6 | start jitter: 0.431 m | start yaw jitter: 3.8 deg | wind L3 (0.082N), steady-state err 0.036m, recovered in 0 steps
episode 140/200 | final pos error: 0.022 m | crash: False | reward: -12.7 | start jitter: 0.252 m | start yaw jitter: 3.3 deg | torque L3 (4.030rad/s), recovered in 0 steps
episode 141/200 | final pos error: 0.057 m | crash: False | reward: -12.0 | start jitter: 0.271 m | start yaw jitter: 14.2 deg | torque L2 (2.896rad/s), recovered in 0 steps
episode 142/200 | final pos error: 0.018 m | crash: False | reward: -8.2 | start jitter: 0.146 m | start yaw jitter: 9.0 deg | wind L5 (0.146N), steady-state err 0.033m, recovered in 0 steps
episode 143/200 | final pos error: 0.145 m | crash: True (tilt) | reward: -11.4 | start jitter: 0.315 m | start yaw jitter: 8.7 deg | torque L5 (9.143rad/s), crashed
episode 144/200 | final pos error: 0.018 m | crash: False | reward: -17.8 | start jitter: 0.432 m | start yaw jitter: 11.6 deg | wind L1 (0.034N), steady-state err 0.019m, recovered in 0 steps
episode 145/200 | final pos error: 0.128 m | crash: True (tilt) | reward: -5.1 | start jitter: 0.085 m | start yaw jitter: 5.8 deg | torque L5 (11.368rad/s), crashed
episode 146/200 | final pos error: 0.048 m | crash: False | reward: -16.1 | start jitter: 0.371 m | start yaw jitter: 11.8 deg | wind L3 (0.078N), steady-state err 0.023m, recovered in 0 steps
episode 147/200 | final pos error: 0.103 m | crash: True (tilt) | reward: -5.5 | start jitter: 0.231 m | start yaw jitter: 10.6 deg | torque L5 (11.021rad/s), crashed
episode 148/200 | final pos error: 0.037 m | crash: False | reward: -18.5 | start jitter: 0.400 m | start yaw jitter: 4.5 deg | kick L2 (0.676m/s), recovered in 15 steps
episode 149/200 | final pos error: 0.138 m | crash: True (tilt) | reward: -10.3 | start jitter: 0.298 m | start yaw jitter: 5.0 deg | torque L5 (10.297rad/s), crashed
episode 150/200 | final pos error: 0.697 m | crash: True (tilt) | reward: -23.6 | start jitter: 0.401 m | start yaw jitter: 13.1 deg | kick L5 (1.614m/s), crashed
episode 151/200 | final pos error: 0.078 m | crash: False | reward: -18.8 | start jitter: 0.364 m | start yaw jitter: 14.9 deg | wind L3 (0.083N), steady-state err 0.022m, recovered in 0 steps
episode 152/200 | final pos error: 0.037 m | crash: False | reward: -17.8 | start jitter: 0.403 m | start yaw jitter: 5.4 deg | kick L1 (0.328m/s), recovered in 0 steps
episode 153/200 | final pos error: 0.104 m | crash: False | reward: -28.5 | start jitter: 0.365 m | start yaw jitter: 4.1 deg | kick L5 (1.682m/s), recovered in 28 steps
episode 154/200 | final pos error: 0.021 m | crash: False | reward: -16.8 | start jitter: 0.275 m | start yaw jitter: 9.4 deg | kick L3 (1.059m/s), recovered in 19 steps
episode 155/200 | final pos error: 0.005 m | crash: False | reward: -15.2 | start jitter: 0.290 m | start yaw jitter: 12.4 deg | torque L3 (4.196rad/s), recovered in 0 steps
episode 156/200 | final pos error: 0.128 m | crash: True (tilt) | reward: -12.7 | start jitter: 0.356 m | start yaw jitter: 6.8 deg | torque L5 (12.693rad/s), crashed
episode 157/200 | final pos error: 0.025 m | crash: False | reward: -17.4 | start jitter: 0.408 m | start yaw jitter: 14.3 deg | wind L3 (0.094N), steady-state err 0.022m, recovered in 0 steps
episode 158/200 | final pos error: 0.071 m | crash: False | reward: -12.2 | start jitter: 0.274 m | start yaw jitter: 5.6 deg | wind L4 (0.128N), steady-state err 0.027m, recovered in 0 steps
episode 159/200 | final pos error: 0.170 m | crash: True (tilt) | reward: -8.6 | start jitter: 0.254 m | start yaw jitter: 9.2 deg | torque L5 (12.847rad/s), crashed
episode 160/200 | final pos error: 0.589 m | crash: True (tilt) | reward: -12.0 | start jitter: 0.209 m | start yaw jitter: 5.2 deg | kick L5 (1.888m/s), crashed
episode 161/200 | final pos error: 0.068 m | crash: False | reward: -14.1 | start jitter: 0.338 m | start yaw jitter: 14.5 deg | torque L1 (1.838rad/s), recovered in 0 steps
episode 162/200 | final pos error: 0.176 m | crash: True (tilt) | reward: -4.6 | start jitter: 0.118 m | start yaw jitter: 4.9 deg | kick L2 (0.772m/s), crashed
episode 163/200 | final pos error: 0.033 m | crash: False | reward: -9.8 | start jitter: 0.262 m | start yaw jitter: 0.4 deg | wind L1 (0.024N), steady-state err 0.027m, recovered in 0 steps
episode 164/200 | final pos error: 0.010 m | crash: False | reward: -14.2 | start jitter: 0.358 m | start yaw jitter: 5.4 deg | wind L3 (0.084N), steady-state err 0.018m, recovered in 0 steps
episode 165/200 | final pos error: 0.455 m | crash: True (tilt) | reward: -10.4 | start jitter: 0.153 m | start yaw jitter: 12.8 deg | kick L5 (1.786m/s), crashed
episode 166/200 | final pos error: 0.014 m | crash: False | reward: -14.9 | start jitter: 0.333 m | start yaw jitter: 10.8 deg | wind L4 (0.113N), steady-state err 0.026m, recovered in 0 steps
episode 167/200 | final pos error: 0.080 m | crash: False | reward: -21.0 | start jitter: 0.322 m | start yaw jitter: 9.1 deg | torque L3 (5.783rad/s), recovered in 0 steps
episode 168/200 | final pos error: 0.011 m | crash: False | reward: -17.4 | start jitter: 0.345 m | start yaw jitter: 13.8 deg | torque L3 (5.633rad/s), recovered in 20 steps
episode 169/200 | final pos error: 0.063 m | crash: False | reward: -18.6 | start jitter: 0.375 m | start yaw jitter: 10.1 deg | kick L3 (0.833m/s), recovered in 0 steps
episode 170/200 | final pos error: 0.032 m | crash: False | reward: -10.2 | start jitter: 0.250 m | start yaw jitter: 2.8 deg | torque L1 (1.530rad/s), recovered in 0 steps
episode 171/200 | final pos error: 0.036 m | crash: False | reward: -16.7 | start jitter: 0.371 m | start yaw jitter: 2.7 deg | kick L2 (0.569m/s), recovered in 0 steps
episode 172/200 | final pos error: 0.029 m | crash: False | reward: -14.0 | start jitter: 0.375 m | start yaw jitter: 8.4 deg | wind L3 (0.099N), steady-state err 0.027m, recovered in 0 steps
episode 173/200 | final pos error: 0.411 m | crash: True (tilt) | reward: -9.5 | start jitter: 0.204 m | start yaw jitter: 9.5 deg | kick L5 (1.948m/s), crashed
episode 174/200 | final pos error: 0.448 m | crash: True (tilt) | reward: -15.3 | start jitter: 0.370 m | start yaw jitter: 8.3 deg | kick L4 (1.481m/s), crashed
episode 175/200 | final pos error: 0.021 m | crash: False | reward: -7.9 | start jitter: 0.211 m | start yaw jitter: 1.8 deg | wind L1 (0.027N), steady-state err 0.022m, recovered in 0 steps
episode 176/200 | final pos error: 0.022 m | crash: False | reward: -14.5 | start jitter: 0.390 m | start yaw jitter: 8.7 deg | torque L1 (1.606rad/s), recovered in 0 steps
episode 177/200 | final pos error: 0.054 m | crash: False | reward: -17.6 | start jitter: 0.352 m | start yaw jitter: 1.5 deg | kick L3 (1.030m/s), recovered in 14 steps
episode 178/200 | final pos error: 0.114 m | crash: False | reward: -13.4 | start jitter: 0.262 m | start yaw jitter: 3.1 deg | torque L4 (6.027rad/s), recovered in 0 steps
episode 179/200 | final pos error: 0.206 m | crash: False | reward: -37.2 | start jitter: 0.263 m | start yaw jitter: 12.3 deg | kick L3 (1.085m/s), DID NOT recover in budget
episode 180/200 | final pos error: 0.024 m | crash: False | reward: -10.6 | start jitter: 0.271 m | start yaw jitter: 2.1 deg | wind L4 (0.136N), steady-state err 0.019m, recovered in 0 steps
episode 181/200 | final pos error: 0.060 m | crash: False | reward: -16.7 | start jitter: 0.306 m | start yaw jitter: 3.8 deg | kick L4 (1.232m/s), recovered in 0 steps
episode 182/200 | final pos error: 0.093 m | crash: True (tilt) | reward: -9.3 | start jitter: 0.329 m | start yaw jitter: 5.5 deg | torque L3 (5.777rad/s), crashed
episode 183/200 | final pos error: 0.015 m | crash: False | reward: -9.8 | start jitter: 0.238 m | start yaw jitter: 12.8 deg | wind L2 (0.070N), steady-state err 0.029m, recovered in 0 steps
episode 184/200 | final pos error: 0.057 m | crash: False | reward: -11.3 | start jitter: 0.201 m | start yaw jitter: 4.1 deg | wind L4 (0.126N), steady-state err 0.023m, recovered in 0 steps
episode 185/200 | final pos error: 0.058 m | crash: False | reward: -13.4 | start jitter: 0.304 m | start yaw jitter: 5.2 deg | wind L3 (0.071N), steady-state err 0.024m, recovered in 0 steps
episode 186/200 | final pos error: 0.040 m | crash: False | reward: -15.5 | start jitter: 0.320 m | start yaw jitter: 12.9 deg | kick L3 (0.833m/s), recovered in 0 steps
episode 187/200 | final pos error: 0.023 m | crash: False | reward: -13.4 | start jitter: 0.319 m | start yaw jitter: 7.6 deg | wind L2 (0.060N), steady-state err 0.027m, recovered in 0 steps
episode 188/200 | final pos error: 0.344 m | crash: True (tilt) | reward: -10.1 | start jitter: 0.305 m | start yaw jitter: 2.1 deg | kick L4 (1.323m/s), crashed
episode 189/200 | final pos error: 0.021 m | crash: False | reward: -14.5 | start jitter: 0.357 m | start yaw jitter: 14.9 deg | wind L4 (0.115N), steady-state err 0.031m, recovered in 0 steps
episode 190/200 | final pos error: 0.125 m | crash: True (tilt) | reward: -12.4 | start jitter: 0.318 m | start yaw jitter: 12.6 deg | torque L3 (5.144rad/s), crashed
episode 191/200 | final pos error: 0.047 m | crash: False | reward: -16.0 | start jitter: 0.287 m | start yaw jitter: 0.3 deg | wind L5 (0.167N), steady-state err 0.039m, recovered in 0 steps
episode 192/200 | final pos error: 0.379 m | crash: True (tilt) | reward: -14.6 | start jitter: 0.339 m | start yaw jitter: 9.0 deg | kick L5 (1.504m/s), crashed
episode 193/200 | final pos error: 0.028 m | crash: False | reward: -12.0 | start jitter: 0.223 m | start yaw jitter: 9.6 deg | kick L1 (0.491m/s), recovered in 0 steps
episode 194/200 | final pos error: 0.532 m | crash: True (tilt) | reward: -9.5 | start jitter: 0.122 m | start yaw jitter: 13.7 deg | kick L5 (1.872m/s), crashed
episode 195/200 | final pos error: 0.012 m | crash: False | reward: -13.4 | start jitter: 0.290 m | start yaw jitter: 3.6 deg | torque L2 (3.882rad/s), recovered in 0 steps
episode 196/200 | final pos error: 0.018 m | crash: False | reward: -9.0 | start jitter: 0.206 m | start yaw jitter: 6.8 deg | kick L1 (0.327m/s), recovered in 0 steps
episode 197/200 | final pos error: 0.034 m | crash: False | reward: -12.5 | start jitter: 0.230 m | start yaw jitter: 10.3 deg | kick L2 (0.649m/s), recovered in 0 steps
episode 198/200 | final pos error: 0.049 m | crash: False | reward: -11.9 | start jitter: 0.182 m | start yaw jitter: 7.1 deg | kick L3 (0.860m/s), recovered in 0 steps
episode 199/200 | final pos error: 0.125 m | crash: True (tilt) | reward: -10.7 | start jitter: 0.341 m | start yaw jitter: 7.4 deg | torque L5 (9.885rad/s), crashed
episode 200/200 | final pos error: 0.048 m | crash: False | reward: -18.6 | start jitter: 0.406 m | start yaw jitter: 1.7 deg | wind L1 (0.021N), steady-state err 0.018m, recovered in 0 steps

==================================================
Episodes run:          200
Mean final pos error:  0.097 m
Crash rate:            22.5%
Mean episode reward:   -14.3
==================================================

Disturbance report (200/200 episodes had an event fire):

  --- kick (62/200 of fired episodes) ---
    Crash rate:           40.3%  (n=62)
    Recovery rate:        94.6%  (of 37 non-crashed)
    Mean recovery time:  5.8 steps (0.19s @ 30Hz)
    [FAIL] mastery gate: crash rate <10% AND recovery rate >90%
    By level: L1: n=12 crash=0% recover=100% | L2: n=6 crash=17% recover=100% | L3: n=12 crash=17% recover=90% | L4: n=14 crash=57% recover=100% | L5: n=18 crash=78% recover=75%

  --- torque (66/200 of fired episodes) ---
    Crash rate:           30.3%  (n=66)
    Recovery rate:        95.7%  (of 46 non-crashed)
    Mean recovery time:  3.0 steps (0.10s @ 30Hz)
    [FAIL] mastery gate: crash rate <10% AND recovery rate >90%
    By level: L1: n=14 crash=0% recover=100% | L2: n=12 crash=8% recover=100% | L3: n=17 crash=24% recover=92% | L4: n=9 crash=44% recover=100% | L5: n=14 crash=79% recover=67%

  --- wind (72/200 of fired episodes) ---
    Crash rate:            0.0%  (n=72)
    Recovery rate:       100.0%  (of 72 non-crashed)
    Mean recovery time:  0.0 steps (0.00s @ 30Hz)
    Mean steady-state error during wind window: 0.025 m
    [PASS] mastery gate: crash rate <10% AND recovery rate >90%
    By level: L1: n=19 crash=0% recover=100% | L2: n=11 crash=0% recover=100% | L3: n=17 crash=0% recover=100% | L4: n=15 crash=0% recover=100% | L5: n=10 crash=0% recover=100%
[registry] WARNING: hash 0e78e3ec08a9... has no matching training-run record. This file's origin (config, cumulative steps, parent checkpoint) is unknown to the registry -- it may have been hand-copied, or predates the registry. Eval result is still logged, but treat provenance as unverified.
Logged to model registry (hash 0e78e3ec08a9...). Query with: python -m src.weight_manager.model_registry describe model/model_weights/checkpoints/hover_stabilize_ppo_seed0_disturbance_3x5_tiltfix3_149994_steps.zip

Stage 2 criteria (docs/hover-model-plan.md):
  [PASS] mean pos error < 0.3 m
  [FAIL] crash rate < 10%

-> Stage 2 not yet reached. See docs/hover-model-plan.md for what to try next.

Tail episodes (final pos error > 0.2 m): 28/200
  episode  1 | pos error 0.533 m | reward -14.7 | start jitter 0.319 m | start yaw jitter 14.5 deg | best=0.003 m @ step 52/122 (converged then drifted) | kick L5 (1.956m/s), crashed
  episode 14 | pos error 0.788 m | reward -19.8 | start jitter 0.363 m | start yaw jitter 6.4 deg | best=0.007 m @ step 46/129 (converged then drifted) | kick L5 (1.777m/s), crashed
  episode 19 | pos error 0.246 m | reward -46.5 | start jitter 0.351 m | start yaw jitter 5.0 deg | best=0.005 m @ step 56/240 (converged then drifted) | torque L5 (12.703rad/s), DID NOT recover in budget
  episode 20 | pos error 0.477 m | reward -11.3 | start jitter 0.259 m | start yaw jitter 3.1 deg | best=0.002 m @ step 97/152 (converged then drifted) | kick L5 (1.781m/s), crashed
  episode 29 | pos error 0.314 m | reward -13.5 | start jitter 0.336 m | start yaw jitter 6.1 deg | best=0.005 m @ step 116/131 (converged then drifted) | kick L5 (1.991m/s), crashed
  episode 31 | pos error 0.274 m | reward -13.5 | start jitter 0.359 m | start yaw jitter 0.7 deg | best=0.006 m @ step 63/99 (converged then drifted) | kick L3 (0.927m/s), crashed
  episode 34 | pos error 0.564 m | reward -16.6 | start jitter 0.289 m | start yaw jitter 0.5 deg | best=0.004 m @ step 135/159 (converged then drifted) | kick L4 (1.134m/s), crashed
  episode 41 | pos error 0.262 m | reward -9.4 | start jitter 0.205 m | start yaw jitter 9.7 deg | best=0.007 m @ step 52/121 (converged then drifted) | kick L4 (1.435m/s), crashed
  episode 45 | pos error 0.320 m | reward -11.0 | start jitter 0.204 m | start yaw jitter 5.2 deg | best=0.007 m @ step 124/144 (converged then drifted) | kick L4 (1.144m/s), crashed
  episode 57 | pos error 0.600 m | reward -12.8 | start jitter 0.256 m | start yaw jitter 6.6 deg | best=0.004 m @ step 40/101 (converged then drifted) | kick L4 (1.327m/s), crashed
  episode 67 | pos error 0.352 m | reward -14.9 | start jitter 0.331 m | start yaw jitter 1.5 deg | best=0.003 m @ step 100/139 (converged then drifted) | kick L5 (1.801m/s), crashed
  episode 90 | pos error 0.259 m | reward -9.2 | start jitter 0.202 m | start yaw jitter 11.6 deg | best=0.003 m @ step 43/152 (converged then drifted) | kick L4 (1.320m/s), crashed
  episode 97 | pos error 0.526 m | reward -14.7 | start jitter 0.286 m | start yaw jitter 6.7 deg | best=0.002 m @ step 74/155 (converged then drifted) | kick L4 (1.318m/s), crashed
  episode 106 | pos error 0.269 m | reward -16.9 | start jitter 0.415 m | start yaw jitter 12.2 deg | best=0.003 m @ step 71/160 (converged then drifted) | kick L3 (1.000m/s), crashed
  episode 111 | pos error 0.594 m | reward -15.5 | start jitter 0.287 m | start yaw jitter 13.0 deg | best=0.004 m @ step 97/123 (converged then drifted) | kick L5 (1.900m/s), crashed
  episode 112 | pos error 0.700 m | reward -18.6 | start jitter 0.358 m | start yaw jitter 11.0 deg | best=0.005 m @ step 88/123 (converged then drifted) | kick L5 (1.872m/s), crashed
  episode 130 | pos error 0.280 m | reward -11.9 | start jitter 0.294 m | start yaw jitter 14.5 deg | best=0.003 m @ step 64/86 (converged then drifted) | torque L4 (6.076rad/s), crashed
  episode 131 | pos error 0.388 m | reward -19.9 | start jitter 0.372 m | start yaw jitter 12.9 deg | best=0.007 m @ step 124/158 (converged then drifted) | torque L2 (3.686rad/s), crashed
  episode 138 | pos error 0.568 m | reward -19.2 | start jitter 0.403 m | start yaw jitter 10.5 deg | best=0.007 m @ step 69/86 (converged then drifted) | kick L5 (1.687m/s), crashed
  episode 150 | pos error 0.697 m | reward -23.6 | start jitter 0.401 m | start yaw jitter 13.1 deg | best=0.003 m @ step 75/150 (converged then drifted) | kick L5 (1.614m/s), crashed
  episode 160 | pos error 0.589 m | reward -12.0 | start jitter 0.209 m | start yaw jitter 5.2 deg | best=0.003 m @ step 53/96 (converged then drifted) | kick L5 (1.888m/s), crashed
  episode 165 | pos error 0.455 m | reward -10.4 | start jitter 0.153 m | start yaw jitter 12.8 deg | best=0.003 m @ step 31/157 (converged then drifted) | kick L5 (1.786m/s), crashed
  episode 173 | pos error 0.411 m | reward -9.5 | start jitter 0.204 m | start yaw jitter 9.5 deg | best=0.006 m @ step 38/105 (converged then drifted) | kick L5 (1.948m/s), crashed
  episode 174 | pos error 0.448 m | reward -15.3 | start jitter 0.370 m | start yaw jitter 8.3 deg | best=0.007 m @ step 79/101 (converged then drifted) | kick L4 (1.481m/s), crashed
  episode 179 | pos error 0.206 m | reward -37.2 | start jitter 0.263 m | start yaw jitter 12.3 deg | best=0.010 m @ step 85/240 (converged then drifted) | kick L3 (1.085m/s), DID NOT recover in budget
  episode 188 | pos error 0.344 m | reward -10.1 | start jitter 0.305 m | start yaw jitter 2.1 deg | best=0.006 m @ step 40/76 (converged then drifted) | kick L4 (1.323m/s), crashed
  episode 192 | pos error 0.379 m | reward -14.6 | start jitter 0.339 m | start yaw jitter 9.0 deg | best=0.003 m @ step 93/107 (converged then drifted) | kick L5 (1.504m/s), crashed
  episode 194 | pos error 0.532 m | reward -9.5 | start jitter 0.122 m | start yaw jitter 13.7 deg | best=0.004 m @ step 82/144 (converged then drifted) | kick L5 (1.872m/s), crashed
  mean start jitter (tail episodes):     0.295 m
  mean start jitter (non-tail episodes): 0.294 m
  mean start yaw jitter (tail episodes):     8.5 deg
  mean start yaw jitter (non-tail episodes): 7.5 deg
  (28/28 tail episodes had a disturbance event fire -- expected overlap, not necessarily a general policy weak spot)

Correlation (start jitter vs. final pos error):     +0.01
Correlation (start yaw jitter vs. final pos error): +0.07
  -> Weak/no relationship: position jitter doesn't explain the tail.
  -> Weak/no relationship: yaw jitter doesn't explain the tail.

Neither start condition strongly predicts the tail. This leans toward a policy weak spot independent of start draw, rather than 'got an unusually hard start position.' Check the per-episode 'converged then drifted' vs 'never converged' tags above: the former points at a late-episode stability issue (reward/PID interaction, maybe survival_bonus vs. position_error_weight balance); the latter points at slow/incomplete convergence within the episode length, which more training timesteps might fix on its own. If most tail episodes also show a disturbance note, check the disturbance report above before concluding this is a general weak spot rather than a disturbance-recovery gap.

Crashed episodes: 45/200
  episode  1 | reason: tilt | final pos error 0.533 m | reward -14.7 | start jitter 0.319 m | start yaw jitter 14.5 deg | kick L5 (1.956m/s), crashed
  episode  6 | reason: tilt | final pos error 0.164 m | reward -14.6 | start jitter 0.363 m | start yaw jitter 7.8 deg | torque L4 (6.176rad/s), crashed
  episode 14 | reason: tilt | final pos error 0.788 m | reward -19.8 | start jitter 0.363 m | start yaw jitter 6.4 deg | kick L5 (1.777m/s), crashed
  episode 16 | reason: tilt | final pos error 0.186 m | reward -17.5 | start jitter 0.416 m | start yaw jitter 2.5 deg | torque L5 (9.040rad/s), crashed
  episode 20 | reason: tilt | final pos error 0.477 m | reward -11.3 | start jitter 0.259 m | start yaw jitter 3.1 deg | kick L5 (1.781m/s), crashed
  episode 29 | reason: tilt | final pos error 0.314 m | reward -13.5 | start jitter 0.336 m | start yaw jitter 6.1 deg | kick L5 (1.991m/s), crashed
  episode 31 | reason: tilt | final pos error 0.274 m | reward -13.5 | start jitter 0.359 m | start yaw jitter 0.7 deg | kick L3 (0.927m/s), crashed
  episode 34 | reason: tilt | final pos error 0.564 m | reward -16.6 | start jitter 0.289 m | start yaw jitter 0.5 deg | kick L4 (1.134m/s), crashed
  episode 41 | reason: tilt | final pos error 0.262 m | reward -9.4 | start jitter 0.205 m | start yaw jitter 9.7 deg | kick L4 (1.435m/s), crashed
  episode 45 | reason: tilt | final pos error 0.320 m | reward -11.0 | start jitter 0.204 m | start yaw jitter 5.2 deg | kick L4 (1.144m/s), crashed
  episode 50 | reason: tilt | final pos error 0.139 m | reward -11.2 | start jitter 0.358 m | start yaw jitter 9.6 deg | torque L5 (10.176rad/s), crashed
  episode 51 | reason: tilt | final pos error 0.186 m | reward -7.1 | start jitter 0.121 m | start yaw jitter 5.3 deg | torque L3 (4.775rad/s), crashed
  episode 57 | reason: tilt | final pos error 0.600 m | reward -12.8 | start jitter 0.256 m | start yaw jitter 6.6 deg | kick L4 (1.327m/s), crashed
  episode 64 | reason: tilt | final pos error 0.139 m | reward -8.2 | start jitter 0.244 m | start yaw jitter 3.7 deg | torque L5 (9.924rad/s), crashed
  episode 67 | reason: tilt | final pos error 0.352 m | reward -14.9 | start jitter 0.331 m | start yaw jitter 1.5 deg | kick L5 (1.801m/s), crashed
  episode 90 | reason: tilt | final pos error 0.259 m | reward -9.2 | start jitter 0.202 m | start yaw jitter 11.6 deg | kick L4 (1.320m/s), crashed
  episode 94 | reason: tilt | final pos error 0.100 m | reward -11.2 | start jitter 0.312 m | start yaw jitter 12.6 deg | torque L3 (5.529rad/s), crashed
  episode 97 | reason: tilt | final pos error 0.526 m | reward -14.7 | start jitter 0.286 m | start yaw jitter 6.7 deg | kick L4 (1.318m/s), crashed
  episode 106 | reason: tilt | final pos error 0.269 m | reward -16.9 | start jitter 0.415 m | start yaw jitter 12.2 deg | kick L3 (1.000m/s), crashed
  episode 109 | reason: tilt | final pos error 0.130 m | reward -11.5 | start jitter 0.287 m | start yaw jitter 2.7 deg | torque L4 (7.364rad/s), crashed
  episode 110 | reason: tilt | final pos error 0.157 m | reward -7.3 | start jitter 0.252 m | start yaw jitter 10.4 deg | torque L4 (8.826rad/s), crashed
  episode 111 | reason: tilt | final pos error 0.594 m | reward -15.5 | start jitter 0.287 m | start yaw jitter 13.0 deg | kick L5 (1.900m/s), crashed
  episode 112 | reason: tilt | final pos error 0.700 m | reward -18.6 | start jitter 0.358 m | start yaw jitter 11.0 deg | kick L5 (1.872m/s), crashed
  episode 120 | reason: tilt | final pos error 0.153 m | reward -10.9 | start jitter 0.341 m | start yaw jitter 3.5 deg | torque L5 (11.187rad/s), crashed
  episode 130 | reason: tilt | final pos error 0.280 m | reward -11.9 | start jitter 0.294 m | start yaw jitter 14.5 deg | torque L4 (6.076rad/s), crashed
  episode 131 | reason: tilt | final pos error 0.388 m | reward -19.9 | start jitter 0.372 m | start yaw jitter 12.9 deg | torque L2 (3.686rad/s), crashed
  episode 138 | reason: tilt | final pos error 0.568 m | reward -19.2 | start jitter 0.403 m | start yaw jitter 10.5 deg | kick L5 (1.687m/s), crashed
  episode 143 | reason: tilt | final pos error 0.145 m | reward -11.4 | start jitter 0.315 m | start yaw jitter 8.7 deg | torque L5 (9.143rad/s), crashed
  episode 145 | reason: tilt | final pos error 0.128 m | reward -5.1 | start jitter 0.085 m | start yaw jitter 5.8 deg | torque L5 (11.368rad/s), crashed
  episode 147 | reason: tilt | final pos error 0.103 m | reward -5.5 | start jitter 0.231 m | start yaw jitter 10.6 deg | torque L5 (11.021rad/s), crashed
  episode 149 | reason: tilt | final pos error 0.138 m | reward -10.3 | start jitter 0.298 m | start yaw jitter 5.0 deg | torque L5 (10.297rad/s), crashed
  episode 150 | reason: tilt | final pos error 0.697 m | reward -23.6 | start jitter 0.401 m | start yaw jitter 13.1 deg | kick L5 (1.614m/s), crashed
  episode 156 | reason: tilt | final pos error 0.128 m | reward -12.7 | start jitter 0.356 m | start yaw jitter 6.8 deg | torque L5 (12.693rad/s), crashed
  episode 159 | reason: tilt | final pos error 0.170 m | reward -8.6 | start jitter 0.254 m | start yaw jitter 9.2 deg | torque L5 (12.847rad/s), crashed
  episode 160 | reason: tilt | final pos error 0.589 m | reward -12.0 | start jitter 0.209 m | start yaw jitter 5.2 deg | kick L5 (1.888m/s), crashed
  episode 162 | reason: tilt | final pos error 0.176 m | reward -4.6 | start jitter 0.118 m | start yaw jitter 4.9 deg | kick L2 (0.772m/s), crashed
  episode 165 | reason: tilt | final pos error 0.455 m | reward -10.4 | start jitter 0.153 m | start yaw jitter 12.8 deg | kick L5 (1.786m/s), crashed
  episode 173 | reason: tilt | final pos error 0.411 m | reward -9.5 | start jitter 0.204 m | start yaw jitter 9.5 deg | kick L5 (1.948m/s), crashed
  episode 174 | reason: tilt | final pos error 0.448 m | reward -15.3 | start jitter 0.370 m | start yaw jitter 8.3 deg | kick L4 (1.481m/s), crashed
  episode 182 | reason: tilt | final pos error 0.093 m | reward -9.3 | start jitter 0.329 m | start yaw jitter 5.5 deg | torque L3 (5.777rad/s), crashed
  episode 188 | reason: tilt | final pos error 0.344 m | reward -10.1 | start jitter 0.305 m | start yaw jitter 2.1 deg | kick L4 (1.323m/s), crashed
  episode 190 | reason: tilt | final pos error 0.125 m | reward -12.4 | start jitter 0.318 m | start yaw jitter 12.6 deg | torque L3 (5.144rad/s), crashed
  episode 192 | reason: tilt | final pos error 0.379 m | reward -14.6 | start jitter 0.339 m | start yaw jitter 9.0 deg | kick L5 (1.504m/s), crashed
  episode 194 | reason: tilt | final pos error 0.532 m | reward -9.5 | start jitter 0.122 m | start yaw jitter 13.7 deg | kick L5 (1.872m/s), crashed
  episode 199 | reason: tilt | final pos error 0.125 m | reward -10.7 | start jitter 0.341 m | start yaw jitter 7.4 deg | torque L5 (9.885rad/s), crashed
  45/45 crashes had a disturbance event fire. Crashes matter independently of the position-error tail — a policy that rarely-but-genuinely crashes is a different (and more serious) problem than one that just converges slowly. Worth tracking whether this reproduces on other seeds/eval runs before assuming it's a one-off.
```

## 3. Leaderboard (kick_crash_rate, minimize)
```
rank hash          kick_crash_rate     file      provenance  model_path
1    4a68b97b82a4  0.3226              OK        UNKNOWN     model/model_weights/checkpoints/hover_stabilize_ppo_seed0_disturbance_3x5_tiltfix2_49998_steps.zip
2    0e78e3ec08a9  0.4032              OK        UNKNOWN     model/model_weights/checkpoints/hover_stabilize_ppo_seed0_disturbance_3x5_tiltfix3_149994_steps.zip
3    9694bdcd86ea  0.4828              OK        known       model/model_weights/hover_stabilize_ppo_seed0_disturbance_3x5.zip
4    3df3deb1a99f  0.5000              OK        known       model/model_weights/hover_stabilize_ppo_seed0_disturbance_3x5.zip
5    706fcaceb85a  0.5600              OK        known       model/model_weights/hover_stabilize_ppo_seed0_disturbance_3x5.zip
6    706fcaceb85a  0.5833              OK        known       model/model_weights/hover_stabilize_ppo_seed0_disturbance_3x5.zip
```

## 4. Tilt-criterion diagnostic on the winner (model/model_weights/checkpoints/hover_stabilize_ppo_seed0_disturbance_3x5_tiltfix2_49998_steps.zip)
```
Applied stage preset 'disturbance_3x5': {'disturbance_enabled': True, 'disturbance_types_active': ('kick', 'torque', 'wind')}
Original max_tilt_rad: 0.400 rad (22.9 deg)
Loosened to:           1.200 rad (68.8 deg) for this diagnostic run ONLY -- not a training config change.

[INFO] BaseAviary.__init__() loaded parameters from the drone's .urdf:
[INFO] m 0.027000, L 0.039700,
[INFO] ixx 0.000014, iyy 0.000014, izz 0.000022,
[INFO] kf 3.160000e-10, km 7.940000e-12,
[INFO] t2w 2.250000, max_speed_kmh 30.000000,
[INFO] gnd_eff_coeff 11.368590, prop_radius 0.023135,
[INFO] drag_xy_coeff 0.000001, drag_z_coeff 0.000001,
[INFO] dw_coeff_1 2267.180000, dw_coeff_2 0.160000, dw_coeff_3 -0.110000
90 disturbed episodes evaluated under the loosened bound.

28/90 episodes crossed the ORIGINAL 0.40 rad line at some point (these are the ones that would have been truncated as 'crash' under the real training/eval config):

  recovered_despite_breach: 24/28
    kick L5 (1.956)              | peak tilt  43.2 deg | final pos err 0.177 m | ended: timeout
    torque L4 (7.846)            | peak tilt  30.4 deg | final pos err 0.015 m | ended: timeout
    torque L4 (6.176)            | peak tilt  23.9 deg | final pos err 0.025 m | ended: timeout
    kick L5 (1.777)              | peak tilt  51.9 deg | final pos err 0.019 m | ended: timeout
    kick L5 (1.781)              | peak tilt  44.5 deg | final pos err 0.016 m | ended: timeout
    kick L5 (1.536)              | peak tilt  23.8 deg | final pos err 0.016 m | ended: timeout
    kick L3 (1.074)              | peak tilt  27.0 deg | final pos err 0.016 m | ended: timeout
    kick L1 (0.435)              | peak tilt  25.5 deg | final pos err 0.030 m | ended: timeout
    ... and 16 more

  genuine_loss_of_control: 4/28
    torque L5 (9.040)            | peak tilt 141.1 deg | final pos err 0.383 m | ended: tilt
    torque L5 (12.703)           | peak tilt  76.3 deg | final pos err 0.374 m | ended: tilt
    torque L5 (10.176)           | peak tilt 166.3 deg | final pos err 0.454 m | ended: tilt
    torque L5 (9.924)            | peak tilt 153.9 deg | final pos err 0.413 m | ended: tilt

  ambiguous: 0/28

============================================================
Of episodes that breached the original tilt line:
  86% recovered cleanly once given room (criterion looks too strict)
  14% were genuine loss of control regardless (criterion isn't the problem)
  0% ambiguous

-> Majority recovered once given room. The 0.4 rad zero-hold-time crash check is very likely conflating a legitimate hard-tilt recovery maneuver with a real crash. Consider either raising max_tilt_rad, or (better, matching this codebase's own recovery-hold pattern) requiring tilt to EXCEED the bound for N sustained steps before truncating, not a single-step check.
```

## 5. Promotion
```
Promoted model/model_weights/checkpoints/hover_stabilize_ppo_seed0_disturbance_3x5_tiltfix2_49998_steps.zip (hash 4a68b97b82a4, kick_crash_rate=0.3225806451612903) -> /home/premananda/projects/AGERE/model/model_weights/hover_champion.zip
Original left in place -- this is a copy, not a move.
```

## 6. Champion registry record
```
hash: 4a68b97b82a4f74ca93419aae501886ed092f75461a57e83d59076fb3e2d9660
  no matching run record (unknown provenance)
  eval (seed=0, n=200): {'mean_position_error': 0.09099544540862553, 'crash_rate': 0.185, 'mean_reward': -15.210869943281313, 'kick_crash_rate': 0.3225806451612903, 'kick_recovery_rate': 0.9523809523809523, 'kick_mean_recovery_time_steps': 9.0, 'kick_n_episodes': 62, 'torque_crash_rate': 0.25757575757575757, 'torque_recovery_rate': 0.9795918367346939, 'torque_mean_recovery_time_steps': 7.0625, 'torque_n_episodes': 66, 'wind_crash_rate': 0.0, 'wind_recovery_rate': 1.0, 'wind_mean_recovery_time_steps': 0.0, 'wind_n_episodes': 72}
```
