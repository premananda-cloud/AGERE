# AGERE — Project Status (handoff doc)

Single-file context dump for picking this project up in a new chat/session.
Read this first; deeper detail lives in the files referenced throughout.

## What this project is

RL training for a drone hover/stabilization task, part of a larger project
called "Backseat Driver" (see `docs/architecture/Architecture.md` for the
full intended system — PX4 flight stack + a supervisory RL/AI layer).

**Two separate repos, one-directional relationship:**
- **`AGERE`** (this repo) — model building only. **PyBullet + Gymnasium +
  stable-baselines3. No PX4, no MAVSDK, no network dependency at all.**
  This is where the RL policy gets trained and iterated on.
- **`AGERE_sims`** — a *different* repo. PX4 + Gazebo SITL lives there
  exclusively. `AGERE` ships a trained model to `AGERE_sims` for plug-and-
  test; `AGERE_sims`'s integration problems do not feed back into `AGERE`'s
  development. This split was deliberate — earlier attempts to train
  directly against PX4/Gazebo/MAVSDK burned significant time on networking
  issues (WSL2 loopback ambiguity, MAVLink broadcast flags, GPU rendering
  hacks) instead of on the actual RL model. Full story in the 2026-07-23
  session notes (PX4 pain — shared as context earlier, may or may not be
  committed under `docs/devlog/` in your actual repo, worth checking) and
  `docs/devlog/2026_07_29.md` / `2026_07_30.md` (the pivot and repo split
  decisions, confirmed present).

**Current priority, explicitly stated by the project owner:** build and
train the model. PX4/SITL integration is deferred, possibly to be
outsourced later. Don't let SITL/deployment concerns creep back into this
repo's scope.

## Current task: hover/stabilize

Learn a policy that holds a quadrotor at a fixed 3D target point, starting
from a randomized nearby position, using velocity-setpoint actions.

Full spec — environment, action space, reward, and **staged definition of
"done"** (Stage 0 sanity check → Stage 1 learning signal → Stage 2 usable
baseline → Stage 3 robust hover) — is in `docs/hover-model-plan.md`. Don't
duplicate that spec here; this doc points to it.

**Status as of 2026-07-31: Stage 2 reached.** See "Results so far" below.

## Repo structure (`AGERE/src/`)

Full rationale for this layout is in `docs/code-structure.md`. Short
version — the dependency direction is: `actions/` and `environments/` know
nothing about Gymnasium or RL; `training/` is where Gymnasium, reward
design, and the training loop all live.

```
src/
  config.py                    All tunable constants:
                                - SimConfig: pyb_freq, ctrl_freq, gui (physics-only, no RL concepts)
                                - HoverTaskConfig: target_position, episode_len_sec,
                                  reset jitter, truncation bounds, reward weights
                                - PPOConfig: PPO hyperparameters
                                - ProjectConfig: bundles the three above

  actions/velocity_action.py   Defines what a raw 4-vector action means physically:
                                direction (3) + speed magnitude (1), matching
                                gym-pybullet-drones' own VEL action convention.
                                No gymnasium import. VelocityCommand dataclass +
                                normalize_action() function.

  environments/drone_sim.py    DroneSim — pure PyBullet simulation wrapper around
                                gym_pybullet_drones.envs.HoverAviary. No reward, no
                                episode/termination logic, no Gymnasium spaces exposed
                                at this layer (NOTE: HoverAviary itself IS built as a
                                gymnasium.Env internally — that's a property of the
                                third-party library we didn't remove, just didn't
                                re-expose). Methods: reset_episode(pos, yaw),
                                apply_action(VelocityCommand), get_state(),
                                draw_target_marker(pos) [GUI-only, for demos], close().

  training/gym_wrapper.py      HoverGymEnv(gymnasium.Env) — THE Gymnasium environment.
                                Owns action_space/observation_space, reward function,
                                termination/truncation logic. Wraps DroneSim.
                                step() returns an info dict with: truncation_reason
                                ("out_of_bounds"/"tilt"/"timeout"/absent),
                                is_crash (bool, timeout doesn't count as a crash),
                                position_error_norm (float, every step).

  training/train.py            Entry point. `python -m src.training.train [--gui]
                                [--timesteps N]`. Saves hover_stabilize_ppo.zip.

  training/evaluate.py         Runs N deterministic episodes against a saved model,
                                reports mean position error + crash rate, checks
                                against Stage 2 thresholds (0.3m, <10% crash) from
                                hover-model-plan.md. `python -m src.training.evaluate
                                [--model path] [--episodes N] [--gui]`.

  training/demo.py             Live PyBullet GUI demo for showing to other people
                                (not for evaluation). Loops episodes continuously,
                                real-time paced via gym_pybullet_drones.utils.utils.sync,
                                draws a target marker. `python -m src.training.demo
                                [--model path] [--episodes N]`.

  policies/ppo_policy.py       build_ppo(env, ppo_config) — only file that imports
                                the PPO class specifically. Track-agnostic otherwise.

  models/networks.py           Placeholder for custom feature extractors. Empty by
                                design — current 9-dim observation doesn't need one.
                                Extension point for later (e.g. vision/LiDAR obs).
```

## Docs already written (don't recreate these)

- `docs/code-structure.md` — why the folders are organized this way
- `docs/hover-model-plan.md` — environment/action/model spec + staged
  completion criteria (the authoritative "when is this done" reference)
- `docs/training-log.md` — living log, one entry per training run (copy the
  template at the top for new entries)
- `docs/devlog/2026_07_13.md`, `2026_07_21.md`, `2026_07_29.md`,
  `2026_07_30.md` — dated session records (underscore naming convention —
  stick to it for new devlogs). A 2026-07-23 session (the PX4 networking
  troubleshooting day) was referenced earlier in this project's history but
  wasn't confirmed to be committed as a devlog file — check if it exists.
- `docs/architecture/Architecture.md` — the original, unchanged, intended
  end-state system architecture (PX4 + ROS2/uXRCE-DDS)

## Environment setup

Conda env `rl_env`, defined in `environment.yml`. Key points:
- **`setuptools<82` is pinned.** `setuptools>=82` removed the `pkg_resources`
  module entirely; `gym_pybullet_drones`'s `BaseAviary.py` still imports it
  internally, causing `ModuleNotFoundError: No module named 'pkg_resources'`
  without this pin. Remove the pin only once gym-pybullet-drones drops that
  dependency upstream.
- `gym-pybullet-drones` is installed via
  `git+https://github.com/learnsyslab/gym-pybullet-drones.git` — compiles
  `pybullet` from source, needs a C compiler (`build-essential` on
  Debian/Ubuntu).
- **No `mavsdk`** — removed entirely; PX4 tooling belongs in `AGERE_sims`,
  not here.
- PyTorch installed via `cu126` wheel index (CUDA 12.6, compatible with the
  dev machine's driver 595.x / CUDA 13.2 and RTX 4070 SUPER).

## Results so far

First full training run (2026-07-31), 200,000 timesteps, default config.
Evaluated with `evaluate.py`, 20 deterministic episodes:

- **Mean final position error: 0.088 m** (Stage 2 threshold: <0.3 m — PASS)
- **Crash rate: 0%** (Stage 2 threshold: <10% — PASS)
- **Mean episode reward: -29.0**
- **Stage 2 (usable/viable baseline) reached.**
- Caveat worth carrying forward: not uniform — 2 of 20 episodes had final
  position error 0.24–0.29 m (right up against the Stage 2 ceiling) with
  correspondingly worse rewards (-55 to -75). A real tail, not just noise
  around a tight mean. Stage 3 (tighter 0.1 m bar, held across 3 seeds) is
  the next thing this tail should be checked against before calling the
  hover task genuinely solved.

Full entry logged in `docs/training-log.md`.

## Known issues / open items (flagged, not fixed yet)

1. **PPO on GPU is inefficient for this task.** stable-baselines3 warns
   about this — `MlpPolicy` (not CNN-based) is usually faster on CPU given
   the network's small size and GPU transfer overhead. Fix: add
   `device="cpu"` to the `PPO(...)` constructor call in
   `src/policies/ppo_policy.py`. **Not yet applied.**
2. **No yaw-rate control** in the action space — a `gym-pybullet-drones`
   library limitation (its `VEL` action type holds current yaw always), not
   something introduced by this project's code. Acceptable for pure
   position-hold; would need `ActionType.PID` or a custom action handler if
   yaw stabilization becomes part of the task.
3. **Reward function is a custom design**, not `HoverAviary`'s built-in
   quartic reward. Reasonable, but not independently validated beyond the
   one training run above.
4. **Total timesteps**: default is 200,000; there's a case for bumping to
   ~1,000,000 for a more thoroughly trained policy, especially to see if
   the Stage 2 tail (episodes 9/18 above) tightens up with more training.
   Not yet done — would need re-running `train.py` with `--timesteps
   1000000` or updating the default in `config.py`.

## Suggested next steps (pick up here in a new chat)

1. Apply `device="cpu"` fix to `ppo_policy.py`.
2. Decide: push for Stage 3 (more seeds, 0.1 m bar, investigate the
   episode 9/18 tail) vs. move on to the next task (waypoint navigation)
   with this as the baseline. `hover-model-plan.md` has the Stage 3
   checklist already written.
3. If continuing to train, consider whether 1,000,000 timesteps is
   actually justified by the reward curve shape so far (check TensorBoard,
   `./tb_logs/hover`) rather than assuming more steps automatically means a
   better policy — the plateau behavior described in earlier devlog
   entries is worth re-checking against the full curve.
4. Log whatever's done next in `docs/training-log.md` using its template.
