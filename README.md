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

**Status (as of 2026-08-16):**
- **Hover/stabilize — active task, disturbance-robustness curriculum in
  progress.** Stage 0 (baseline re-selection via a from-scratch 500k-step
  run, since the prior seed0/1/2 checkpoints were retired — see below)
  produced a champion (`hover_champion.zip`, 0.020m mean position error,
  0% crash rate). Stage 1 (impulse-kick disturbance, sub-stage 1a) trained
  and evaluated — **null result**: the untouched champion already passes
  1a's mastery gate with zero disturbance-specific training, meaning 1a's
  magnitude range (0.1–0.3 m/s) was calibrated below the champion's
  existing competence and taught it nothing measurable. Recalibrating the
  magnitude floor is the next step. Full detail: `docs/planning/
  hover-robustness-curriculum-plan.md`, `docs/research/theory-log.md`,
  `docs/training-log.md`.
- **Waypoint navigation + landing — retired 2026-08-16.** Stuck at a hard
  local optimum (802,816-step checkpoint, 3.00/5 mean waypoints reached);
  four independent fixes (continued training, a reward-weight tweak, a
  checkpoint sweep, and a structural potential-based reward-shaping
  change) all failed to beat it. Checkpoint weights were deliberately
  deleted; all training/eval history is preserved permanently in
  `model/model_weights/registry.jsonl` and queryable via
  `python -m src.checkpoint_manager leaderboard waypoint_nav
  mean_waypoints_reached` even though the files themselves are gone.
  `waypoint_train.py`/`waypoint_evaluate.py`/`waypoint_gym_wrapper.py`
  still exist in this repo (untouched, still runnable if the task is ever
  revived) — only the trained weights were removed.

See `docs/status.md` for full project context, `docs/hover-model-plan.md`
for what the hover stages mean, `docs/training-log.md` for the complete
run history of both tasks.

## Layout

See `docs/code-structure.md` for the full reasoning. Short version:

```
src/
  config.py                       All tunable constants — SimConfig
                                   (physics; gained `record: bool` toggle
                                   2026-08-16, see demo section below),
                                   HoverTaskConfig (gained disturbance_*/
                                   recovery_* fields 2026-08-16) /
                                   WaypointTaskConfig (per-task reward
                                   and episode design), PPOConfig
                                   (hyperparameters), waypoint_ppo_config()
                                   (waypoint-specific gamma/ent_coef —
                                   added 2026-08-08, see docs/status.md).
                                   Also HOVER_STAGE_PRESETS (2026-08-16) —
                                   shared disturbance-curriculum sub-stage
                                   configs, single source for hover_train.py/
                                   hover_evaluate.py/hover_demo.py's --stage
                                   flag so they can't silently drift apart.

  model_registry.py               Content-hash-addressed, append-only,
                                   multi-task checkpoint registry (added
                                   2026-08-13, generalized from an earlier
                                   waypoint-only version). Identifies
                                   checkpoints by SHA256, not path — paths
                                   get overwritten, hashes don't. See its
                                   own module docstring for the full
                                   rationale and the 2026-08-09 incident
                                   that motivated it.

  checkpoint_manager.py           CLI built on model_registry.py:
                                   leaderboard / backfill / promote /
                                   archive / retire-task, per task. This is
                                   the standard way to pick a "champion"
                                   checkpoint now — see its module
                                   docstring. `retire-task` is how
                                   waypoint_nav's weights were deliberately
                                   removed while keeping their eval history.

  actions/velocity_action.py      Defines what a raw action means
                                   physically (direction + speed). Shared
                                   by both tasks. No gymnasium, no PX4.

  environments/drone_sim.py       Pure PyBullet simulation wrapper around
                                   gym-pybullet-drones' HoverAviary. No
                                   reward, no episode logic, no Gymnasium
                                   spaces — just physics. Shared by both
                                   tasks. Gained a `record` passthrough
                                   2026-08-16 (see demo section below);
                                   output location is NOT configurable
                                   from here — confirmed against
                                   gym-pybullet-drones source that
                                   HoverAviary never exposes
                                   `output_folder` to its own constructor.

  training/
    hover_train.py                 Hover training entry point. Gained
                                    --init-from, --stage, --tag, and
                                    --checkpoint-every 2026-08-16 (had
                                    none of these before) — needed for the
                                    disturbance curriculum's sub-stage
                                    progression (each sub-stage warm-
                                    starts from the previous one's
                                    champion, tagged so saves don't
                                    clobber each other).
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
                                    model/model_weights/history/. Task
                                    retired 2026-08-16 (see Status above)
                                    — this script still runs, just isn't
                                    the active focus.
    gym_wrapper/hover_gym_wrapper.py       HoverGymEnv. Gained kick
                                            injection + recovery-hold
                                            tracking 2026-08-16 (see
                                            hover-robustness-curriculum-
                                            plan.md's Stage 1 section) —
                                            off by default
                                            (disturbance_enabled=False),
                                            existing calls unaffected.
    gym_wrapper/waypoint_gym_wrapper.py    WaypointGymEnv. Fixed
                                            2026-08-08: obs is now
                                            re-derived on any waypoint
                                            transition, not just the
                                            transition into landing (see
                                            docs/status.md).
    evaluate/hover_evaluate.py             Hover eval vs. staged criteria.
                                            Gained --stage (must match
                                            training config or disturbance
                                            silently evaluates as off) and
                                            a disturbance-recovery report
                                            2026-08-16.
    evaluate/hover_evaluate_disturbance.py Hover Stage 3 disturbance test
                                            (predates and is separate from
                                            the 2026-08-16 curriculum work
                                            above — not yet reconciled
                                            with it).
    evaluate/waypoint_evaluate.py          Waypoint success rate / route
                                            failure breakdown. Added
                                            2026-08-08: per-leg "closest
                                            approach on the stuck leg"
                                            diagnostic, and a warning when
                                            run without --seed.
    demo/hover_demo.py                     Live GUI demo, hover. Gained
                                            --stage/--kick-min/--kick-max
                                            (visualize disturbance
                                            recovery, with an orange
                                            marker at the kick moment) and
                                            --record/--headless (save a
                                            .mp4 instead of/alongside
                                            watching live) 2026-08-16. No
                                            flags = unchanged from before.
    demo/waypoint_demo.py                  BROKEN — currently a duplicate
                                            of waypoint_evaluate.py, not
                                            yet rewritten as a real demo.
                                            Moot while the task is retired.

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
python -m src.training.hover_train --seed 0 --checkpoint-every 50000

# Disturbance curriculum (2026-08-16) — warm-start from an existing
# champion, apply a sub-stage's config from config.py's HOVER_STAGE_PRESETS:
python -m src.training.hover_train --seed 0 --stage 1a \
    --init-from model/model_weights/hover_champion.zip \
    --timesteps 300000 --checkpoint-every 50000

python -m src.training.evaluate.hover_evaluate
python -m src.training.evaluate.hover_evaluate --model model/model_weights/hover_champion.zip --episodes 20
python -m src.training.evaluate.hover_evaluate --model model/model_weights/hover_champion.zip --stage 1a --episodes 20
# --stage is required to see any disturbance behavior at all — omitting
# it silently evaluates as undisturbed regardless of how the model was
# trained.

python -m src.training.evaluate.hover_evaluate_disturbance
python -m src.training.evaluate.hover_evaluate_disturbance --kick-speed 2.0

python -m src.training.demo.hover_demo
python -m src.training.demo.hover_demo --episodes 5
python -m src.training.demo.hover_demo --model model/model_weights/hover_champion.zip --kick-min 0.4 --kick-max 0.6 --episodes 1
python -m src.training.demo.hover_demo --model model/model_weights/hover_champion.zip --kick-min 0.4 --kick-max 0.6 --episodes 1 --record
python -m src.training.demo.hover_demo --model model/model_weights/hover_champion.zip --kick-min 0.4 --kick-max 0.6 --episodes 1 --headless
# --record saves a .mp4 while the window is still open (./results/,
# location not configurable — see src/environments/drone_sim.py).
# --headless additionally skips the window and real-time pacing entirely,
# stitching per-frame PNGs into an .mp4 via ffmpeg if it's on PATH.
```
Picking a champion, and browsing what's been tried, via the registry
instead of guessing from filenames:
```bash
python -m src.checkpoint_manager backfill hover --seed 42 --episodes 20
python -m src.checkpoint_manager leaderboard hover mean_position_error --minimize
python -m src.checkpoint_manager promote hover mean_position_error --minimize
```
Watch progress with:
```bash
tensorboard --logdir tb_logs/hover_logs
```

## Commands — Waypoint Navigation + Landing (RETIRED 2026-08-16, historical)

**Checkpoint weights no longer exist on disk** — deliberately deleted
after the task was retired (see Status above). The commands below won't
run against a real model anymore; kept for reference and in case the task
is ever revived. Eval history is still queryable:
```bash
python -m src.checkpoint_manager leaderboard waypoint_nav mean_waypoints_reached
```

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

`python -m src.training.demo.waypoint_demo` was never functional and is
now moot — see `docs/status.md`'s Known Issues.

## Model / log storage

All checkpoints save to a single flat `model/model_weights/` directory,
distinguished by filename prefix (`hover_stabilize_ppo*.zip` vs.
`waypoint_nav_ppo*.zip`) and, since 2026-08-16, an optional `_<tag>`
suffix for curriculum sub-stages (e.g. `hover_stabilize_ppo_seed0_1a.zip`
— see `src/paths.py`'s `hover_stabilize_model_path()`). A timestamped copy
of every waypoint save is also archived under
`model/model_weights/history/` (added 2026-08-08). `tb_logs/` stays split
per task (`tb_logs/hover_logs/`, `tb_logs/waypoint_logs/`). Both
directories are `.gitignore`d — weights/logs are pushed to Hugging Face
instead (see `docs/conventions.md`). `src/paths.py` is the single source
of truth for every save/load path — never hardcode one elsewhere.

**Don't pick a "best" checkpoint by eyeballing filenames or trusting the
final save.** Since 2026-08-13, `model/model_weights/registry.jsonl`
(content-hash-addressed, append-only — see `src/model_registry.py`) is
the source of truth for "what actually got evaluated and how it scored,"
independent of what happens to the file on disk afterward. `src/
checkpoint_manager.py` is the CLI on top of it: `leaderboard` (rank every
evaluated checkpoint for a task by a metric), `backfill` (evaluate every
checkpoint that doesn't have a registry record yet), `promote` (copy the
current best to a canonical `<task>_champion.zip`), `archive`/
`retire-task` (move checkpoint files out — reversibly — while keeping
their eval history forever). This is how `hover_champion.zip` was
actually selected (see Status above), and how waypoint_nav's weights were
deliberately retired without losing what was learned from them.

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
- **Disturbance curriculum's Level 1 magnitude (0.1–0.3 m/s) is
  confirmed too low to teach anything** (2026-08-16) — the untouched
  hover champion already passes the sub-stage 1a mastery gate with zero
  disturbance-specific training. Don't trust `config.py`'s
  `HOVER_STAGE_PRESETS["1a"]` magnitude numbers as "the right difficulty"
  until they're recalibrated — see `docs/research/theory-log.md` Theory
  2026-08-16-3.
- `HoverAviary`'s built-in video recorder (`SimConfig.record`, added
  2026-08-16) always writes to `./results/` relative to cwd — not
  configurable from this codebase; confirmed against
  gym-pybullet-drones' source directly, `HoverAviary` never exposes
  `output_folder` to its own constructor.
- **Waypoint navigation (retired 2026-08-16) never reliably completed the
  route** — stuck at 3.00/5 mean waypoints reached (802,816-step
  checkpoint), with zero crashes throughout. Four independent fixes
  failed to beat this local optimum; `waypoint_reach_radius` was
  confirmed, with real per-leg data, NOT to be the bottleneck. Full
  diagnosis in `docs/status.md`'s Task 2 section (now historical) and
  `docs/decisions/devlog/2026_08_09.md`. Task weights deleted, eval
  history preserved in the registry.
- `waypoint_demo.py` is a known-broken placeholder (duplicate of
  `waypoint_evaluate.py`), never rewritten. Moot while the task is retired.
