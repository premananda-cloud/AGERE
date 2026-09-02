# Training Log — Hover/Stabilize Model

Living document. One entry per training run. Copy the template below for
each new run — don't edit past entries except to add follow-up notes; the
point is an honest record of what was tried, not a polished current state.

Cross-reference `hover-model-plan.md` for what each field means and what
counts as progress toward a usable model.

**Note (2026-08-06):** hover/stabilize is paused as of Stage 3 completion
(2026-08-02) to focus on waypoint navigation + landing — see
`docs/status.md` and `docs/decisions/devlog/2026_08_06.md`. This section
of the log is frozen at that point; new entries go in the "Waypoint
Navigation + Landing Model" section below.

---

## How to fill this in

After each `python -m src.training.train` run, grab:
- The config values actually used (copy relevant fields from `config.py` at
  the time of the run — if you change a default between runs, the log is
  the only place that survives)
- TensorBoard summary: final/best mean episode reward, episode length trend
- Your own read of the PyBullet GUI behavior if you ran with `--gui`
- A one-line verdict: keep this run's config as the new baseline, revert,
  or iterate again

---

## Template

### Run YYYY-MM-DD-N

**Git commit / project state:** (commit hash, or "no git yet" / describe)

**Environment config** (`PyBulletHoverConfig`)
- `target_position`:
- `episode_len_sec`:
- `action_type` / `observation_type`:
- `reset_position_jitter` / `reset_yaw_jitter_deg`:
- `max_xy_distance` / `max_altitude` / `max_tilt_rad`:
- Reward weights (`position_error_weight`, `velocity_penalty_weight`,
  `action_smoothness_weight`, `survival_bonus`):

**Model config** (`PPOConfig`)
- `learning_rate`:
- `n_steps` / `batch_size` / `n_epochs`:
- `gamma` / `gae_lambda` / `clip_range` / `ent_coef`:
- `net_arch`:
- `total_timesteps`:

**Hardware / duration**
- GPU used, wall-clock training time:

**Results**
- Final mean episode reward:
- Episode reward trend (still climbing / plateaued / diverged):
- Episode length trend:
- GUI observation (if run with `--gui`):
- TensorBoard screenshot or note (optional):

**Verdict**
- [ ] New baseline — keep this config
- [ ] Revert — worse than previous baseline
- [ ] Inconclusive — need another run before deciding

**Notes / what to try next:**

---

## Entries

### Run 2026-07-29-0 (not yet run)

Baseline config as built in the 2026-07-29 session — see `config.py`
defaults (`PyBulletHoverConfig`, `PPOConfig`). Not yet executed; `pip
install -e .` for `gym-pybullet-drones` was not completed in the sandbox
this was built in. This entry exists as a placeholder for the first real
run — fill in the template above once it's actually run.

### Run 2026-07-31-0

**Git commit / project state:** post-cleanup, gym_wrapper.py info-dict update
(truncation_reason / is_crash / position_error_norm added for eval)

**Environment config** (`HoverTaskConfig`, assumed defaults — update if changed)
- `target_position`: (0.0, 0.0, 1.0)
- `episode_len_sec`: 8.0
- `reset_position_jitter` / `reset_yaw_jitter_deg`: 0.3 / 15.0
- `max_xy_distance` / `max_altitude` / `max_tilt_rad`: 1.5 / 2.0 / 0.4
- Reward weights: position=1.0, velocity=0.05, smoothness=0.01, survival=0.01

**Model config** (`PPOConfig`, assumed defaults)
- `learning_rate`: 3e-4, `n_steps`/`batch_size`/`n_epochs`: 2048/64/10
- `gamma`/`gae_lambda`/`clip_range`/`ent_coef`: 0.99/0.95/0.2/0.01
- `net_arch`: {pi:[64,64], vf:[64,64]}, `total_timesteps`: 200,000

**Results** (via `python -m src.training.evaluate`, 20 episodes, deterministic)
- Mean final position error: 0.088 m
- Crash rate: 0%
- Mean episode reward: -29.0
- Episode-level variance: mostly 0.02–0.11 m, but 2/20 episodes (9, 18) reached
  0.24–0.29 m — a real tail, not just noise around a tight mean

**Verdict**
- [x] New baseline — keep this config
- Stage 2 (usable/viable) reached per `hover-model-plan.md`

**Notes / what to try next:**
- Set `device="cpu"` in `ppo_policy.py` — SB3 warns MLP-PPO is inefficient on GPU
- Consider Stage 3 push: same eval across 2 more random seeds, tighter 0.1 m bar,
  investigate what's different about episodes 9/18 (worse start jitter draw? or
  a policy weak spot worth more training time on?)

### Run 2026-08-01-0

**Git commit / project state:** Stage 3 instrumentation added this session —
`gym_wrapper.py` `reset()` now returns `start_position`/`start_yaw_rad` in
info; `evaluate.py` gained `--seed`, `--tail-threshold`, per-episode
start-jitter/yaw logging, tail-vs-start-condition correlation, per-step
trajectory classification ("never converged" vs "converged then
drifted"), and separate crash reporting (reason: tilt/out_of_bounds,
independent of the position-error tail threshold); `train.py` and
`ppo_policy.py` gained an optional `--seed`, passed to SB3's `PPO(...)`,
with seed-aware save filenames (`hover_stabilize_ppo_seed{N}.zip`).
`device="cpu"` confirmed already present in `ppo_policy.py` — the
07-31 entry's "not yet done" note above was stale; no code change needed.

**Environment config** (`HoverTaskConfig`, unchanged from 07-31-0 — not
touched this session)
- `target_position`: (0.0, 0.0, 1.0)
- `episode_len_sec`: 8.0
- `reset_position_jitter` / `reset_yaw_jitter_deg`: 0.3 / 15.0
- `max_xy_distance` / `max_altitude` / `max_tilt_rad`: 1.5 / 2.0 / 0.4
- Reward weights: position=1.0, velocity=0.05, smoothness=0.01, survival=0.01

**Model config** (`PPOConfig`, unchanged defaults except timesteps)
- `learning_rate`: 3e-4, `n_steps`/`batch_size`/`n_epochs`: 2048/64/10
- `gamma`/`gae_lambda`/`clip_range`/`ent_coef`: 0.99/0.95/0.2/0.01
- `net_arch`: {pi:[64,64], vf:[64,64]}
- `total_timesteps`: 500,000 (override via `--timesteps 500000`, up from
  the 07-31 run's 200,000 default)
- `--seed 0` (new this session — first of the 3+ seeds Stage 3 requires)

**Command:** `python -m src.training.train --seed 0 --timesteps 500000`

**Hardware / duration**
- CPU (device="cpu"), ~1426s wall-clock (per training log's `time_elapsed`
  at final iteration)

**Results (training)**
- `ep_rew_mean`: -87.5 (iter 1) → -14.3 (final, iter 245) — steady climb,
  no divergence
- `std` (policy action distribution): 1.0 → peaked ~1.11 mid-run → settled
  to 0.849 by the end
- `explained_variance`: 0.96–0.98 by the end (healthy)
- Saved: `hover_stabilize_ppo_seed0.zip`

**Results (eval, `python -m src.training.evaluate --model hover_stabilize_ppo_seed0.zip --seed 42`)**
- Mean final position error: **0.025 m** (vs. 0.088 m / 0.099 m in the two
  07-31-vintage 200k-timestep eval runs — large improvement)
- Crash rate: **5.0%** (1/20) — **new failure mode, not seen in any prior
  eval run of this project.** Episode 14: final pos error 0.152 m,
  `truncation_reason: tilt`. Start condition unremarkable (jitter 0.234 m,
  yaw jitter 8.4°, both mid-distribution) — doesn't look start-condition-
  driven, same pattern as the position-error tail investigated earlier
  this session.
- Tail episodes (>0.2 m): **0/20** — the position-error tail from the
  200k-timestep model is gone at 500k timesteps.
- Mean episode reward: -11.3

**Verdict**
- [x] Inconclusive — need another run before deciding
- Quantitatively clears Stage 3's mean-error bar (0.025 m ≪ 0.1 m) and the
  Stage 2 crash-rate bar (5% < 10%) on this one seed. But the tilt crash
  is new territory — one data point can't distinguish "rare fluke" from
  "longer training trades convergence tightness for occasional brittleness
  near the tilt limit." Needs seeds 1 and 2 before treating either
  explanation as settled.

**Notes / what to try next:**
- Confirms undertraining (not reward shape) explained the 07-31 tail —
  200k timesteps wasn't enough, 500k resolved it.
- Watch for tilt crashes recurring across seeds 1/2. If they do, especially
  as isolated single episodes rather than a consistent rate, consider
  whether `action_smoothness_weight` (currently 0.01, fairly low) is
  under-penalizing sharp corrective actions from a policy with less
  exploration noise (`std` dropped from ~1.0 to ~0.85 over this run).

### Run 2026-08-01-1

**Git commit / project state:** same as 2026-08-01-0 (same session, no
further code changes between these two runs).

**Environment config:** unchanged, same as 2026-08-01-0 above.

**Model config:** unchanged, same as 2026-08-01-0, except:
- `--seed 2` (second of the 3+ seeds Stage 3 requires — note seed 1 was
  not run this session; sequence is 0, 2, with 1 still pending)

**Command:** `python -m src.training.train --seed 2 --timesteps 500000`

**Hardware / duration**
- CPU, total_timesteps 501,760 at completion (same as seed 0 run)

**Results (training)**
- Final visible metrics: `approx_kl` 0.011, `clip_fraction` 0.153,
  `explained_variance` 0.979, `std` **0.684** (tighter than seed 0's
  0.849 — less exploration noise at convergence for this seed)
- Saved: `hover_stabilize_ppo_seed2.zip`

**Results (eval, `python -m src.training.evaluate --model hover_stabilize_ppo_seed2.zip --seed 42`)**
- Mean final position error: **0.018 m** — best of any run this project
  has produced so far
- Crash rate: **0.0%** (0/20) — the seed-0 tilt crash did **not**
  reproduce here
- Tail episodes (>0.2 m): **0/20**
- Mean episode reward: -9.4

**Verdict**
- [x] Inconclusive — need seed 1 before calling Stage 3's multi-seed
  criterion met
- Best result of the three runs to date. One seed with a crash (0), one
  without (2) — not enough to conclude whether the seed-0 tilt crash was
  a fluke or a real (if rare) tendency of longer-trained policies on this
  config.

**Notes / what to try next:**
- Run seed 1 with identical settings (`--seed 1 --timesteps 500000`),
  eval with `--seed 42` for direct comparability with these two.
- Once all three are in: this is the complete Stage 3 seed-robustness
  picture (mean error + crash rate + crash pattern × 3). If quantitative
  bars hold across all three and the tilt crash doesn't recur (or recurs
  at a similarly low, non-alarming single-episode rate), Stage 3's first
  two criteria are reasonably met. Disturbance-recovery (Stage 3's third
  criterion) is still entirely unbuilt — needs `environments/drone_sim.py`
  reviewed for where to hook `applyExternalForce`, plus a concrete numeric
  pass/fail threshold for "recovers within a few seconds" (currently
  qualitative in `hover-model-plan.md`).

### Run 2026-08-02-0

**Git commit / project state:** repo reorganized since the last two
entries — `model/`/`tb_logs/` moved out of git (pushed to Hugging Face
instead, both `.gitignore`d), `src/paths.py` added as the single save/load
path source of truth for all four training entry points. No changes to
env/reward/PPO config itself.

**Environment / model config:** same as `2026-08-01-0`/`2026-08-01-1`
(unchanged this session) — `--seed 1`, `--timesteps 500000`, same
`HoverTaskConfig`/`PPOConfig` defaults.

**Command:** `python -m src.training.train --seed 1 --timesteps 500000`
(training stdout not captured this session — only the eval run below was
shared; config assumed unchanged from the two prior runs since nothing
in `config.py` was touched between sessions)

**Results (eval, `python -m src.training.evaluate --model model/hover_stabilize/hover_stabilize_ppo_seed1.zip --seed 42`)**
- Mean final position error: **0.015 m** — best result of any run to date
- Crash rate: **0.0%** (0/20)
- Tail episodes (>0.2 m): 0/20
- Mean episode reward: -9.3

**Verdict**
- [x] New baseline — completes the Stage 3 seed set
- All three seeds now individually clear both Stage 3 bars:

  | Seed | Mean pos error | Crash rate |
  |---|---|---|
  | 0 | 0.025 m | 5% (1/20, tilt, ep 14) |
  | 1 | 0.015 m | 0% |
  | 2 | 0.018 m | 0% |

  Stage 3 criteria 1 ("Stage 2 holds across 3+ seeds") and 2 ("mean
  position error < 0.1 m") are met — every seed clears both bars
  individually, no borderline cases, so the earlier open question about
  whether these are compound or separate per-seed checks turned out not
  to matter. The seed-0 tilt crash didn't recur in either seed 1 or 2 —
  2/3 seeds fully clean is reasonable evidence it was a rare fluke rather
  than a systemic tendency, though "reasonable evidence" with n=3 seeds
  and 20 eval episodes each isn't the same as ruling it out entirely.

**Notes / what to try next:**
- Stage 3 criterion 3 (disturbance recovery) is the only remaining piece.
  Needs `environments/drone_sim.py` reviewed for where to hook PyBullet's
  `applyExternalForce`, and a concrete numeric threshold for "recovers
  within a few seconds" — still qualitative in `hover-model-plan.md`.
- `evaluate.py`/`demo.py`/`demo_intel.py` now load models with
  `device="cpu"` explicitly (previously only training specified this,
  causing a spurious SB3 GPU warning at eval/demo time even though the
  model was trained CPU-only).

---

# Training Log — Waypoint Navigation + Landing Model

Same format/conventions as the hover log above, cross-referencing
`WaypointTaskConfig` in `config.py` instead of `HoverTaskConfig`. New
field this task cares about: `--init-from`, since waypoint runs
warm-start from a hover checkpoint rather than training from random init
(see `docs/decisions/devlog/2026_08_06.md` for why the observation space
was kept identical to hover's specifically to allow this).

## Entries

### Run 2026-08-06-0 (sanity)

**Git commit / project state:** first working version of
`waypoint_gym_wrapper.py`, `waypoint_train.py`, restructured `paths.py`
(flat `model/model_weights/`, per-task `tb_logs/`).

**Command:**
```
python -m src.training.waypoint_train --init-from model/model_weights/hover_stabilize_ppo_seed0.zip --timesteps 5000 --gui
```

**Environment config** (`WaypointTaskConfig`, defaults, unchanged from `config.py`)
- `waypoints`: 5-point route, see `config.py` for exact coordinates
- `episode_len_sec`: 20.0
- `reset_position_jitter` / `reset_yaw_jitter_deg`: 0.2 / 15.0
- `max_xy_distance` / `max_altitude` / `max_tilt_rad`: 3.0 / 2.5 / 0.4
- `landing_target_altitude` / `landing_max_velocity` / `landing_hold_time_sec`: 0.05 / 0.15 / 2.0
- Reward weights: position=1.0, velocity=0.05, smoothness=0.01, survival=0.01,
  waypoint_bonus=5.0, landing_velocity_penalty=0.3

**Model config:** loaded from `hover_stabilize_ppo_seed0.zip` (own
hyperparameters carried over via `PPO.load`, not re-specified) —
`total_timesteps` override 5000, actual steps run ≈6144
(`n_steps=2048`-rounded).

**Results:** purely a pipeline check — confirmed env runs end-to-end,
waypoint advancement and landing-phase switch trigger correctly,
warm-start load/save works. Not evaluated (too few steps to mean
anything). Saved to `model/model_weights/waypoint_nav_ppo.zip`
(unseeded — treated as disposable, expected to be overwritten by real runs).

**Verdict**
- [x] Inconclusive — pipeline sanity only, not a real training result

**Notes:** `total_timesteps` in the SB3 training-log printout is
cumulative from the loaded checkpoint's history when using `--init-from`
(`reset_num_timesteps=False`), not a fresh count — don't misread the
large printed numbers as this run having done far more work than it did.

### Run 2026-08-06-1

**Git commit / project state:** same code as 2026-08-06-0, no changes
between these two runs.

**Command:**
```
python -m src.training.waypoint_train --init-from model/model_weights/hover_stabilize_ppo_seed0.zip --timesteps 300000 --seed 0
```

**Environment / model config:** same `WaypointTaskConfig` as
2026-08-06-0. `--seed 0` passed for the save filename
(`waypoint_nav_ppo_seed0.zip`) — note per `waypoint_train.py`'s own
warning, `--seed` is cosmetic/filename-only here since a loaded
checkpoint carries its own RNG/optimizer state; it does not reseed
training the way it would for a from-scratch run.

**Hardware / duration:** CPU, ~251s wall-clock for the final logged
iteration window (147 iterations total this run, per training stdout).

**Results (training, final logged iteration only — full curve not yet
reviewed, see notes)**
- `ep_len_mean`: 600 (== max episode length; no episode ended early via
  crash or success)
- `ep_rew_mean`: -291
- `explained_variance`: 0.928
- `std`: 1.07 (higher than the hover source checkpoint's converged 0.849 —
  consistent with the policy re-exploring under the new reward landscape,
  not a red flag on its own)
- Saved: `waypoint_nav_ppo_seed0.zip`

**Results (eval, `python -m src.training.evaluate.waypoint_evaluate --model model/model_weights/waypoint_nav_ppo_seed0.zip --episodes 20`)**
- Success rate: **0.0%**
- Mean waypoints reached: **2.05 / 5**
- Crash rate: **0.0%** (0/20 — no out_of_bounds, no tilt, no hard_landing)
- Mean episode reward: -273.5
- Failure breakdown: 20/20 never finished the route; 0/20 reached the
  landing phase at all; all 20 failures are `timeout`

**Verdict**
- [x] Inconclusive — need another run (more timesteps and/or a `--gui`
  pacing check) before deciding whether this needs more training time or
  a reward/pacing adjustment

**Notes / what to try next:**
- Zero crashes across 20 episodes is a genuinely good sign for a first
  real run off a warm start — stability transferred cleanly from the
  hover checkpoint.
- 100% `timeout` with 0% ever reaching the landing phase points at a
  progress/pacing problem, not a control problem: the policy isn't yet
  committing to closing 1-2m gaps between waypoints quickly enough to
  finish a 5-waypoint route in 600 steps / 20s.
- Full `ep_rew_mean` curve over all 147 iterations not yet reviewed —
  only the final iteration's numbers were captured. Checking
  `tb_logs/waypoint_logs` for whether reward was still climbing or had
  plateaued is the first thing to do before deciding on next steps.
- Most likely next action: continue fine-tuning from
  `waypoint_nav_ppo_seed0.zip` (via `--init-from`) for another few
  hundred k steps, re-run eval, and watch specifically whether `mean
  waypoints reached` climbs — don't touch reward weights until that's
  been tried, per the plan in `docs/decisions/devlog/2026_08_06.md`.

**Follow-up note (2026-08-07):** cross-referencing `tb_logs`' four event
files against their wall-clock timestamps revealed this "one run"
description above was incomplete — the exact command shown here was
actually **run twice**, producing two byte-identical 300k-step curves
(confirmed reproducible: `--init-from` inherits the loaded checkpoint's
own RNG state, and PyBullet is deterministic given that state, so
re-running the identical command from the identical checkpoint
reproduces the identical trajectory). A third, **interrupted** attempt
(~188k of the intended 300k steps) happened in between the two — see
Run 2026-08-06-2 below. Since `waypoint_train.py` saved to a fixed path
with no run-id at the time, it was only possible to determine after the
fact (by comparing file mtime against `tb_logs` wall-clock) that the
*second* full run's weights were what ended up in the saved
`waypoint_nav_ppo_seed0.zip` — the eval results recorded above are
consistent with either full run (they're identical), so this doesn't
invalidate the numbers above, but it means "this run" should be read as
"the (identical, reproducible) 300k-step curve," not literally one
`python` invocation. Fixed going forward — see `docs/status.md`'s
"Model / log directory layout" (2026-08-08): every save now also
archives a timestamped copy so this ambiguity can't recur.

### Run 2026-08-06-2 (interrupted, discovered retroactively 2026-08-07)

**Git commit / project state:** same code as 2026-08-06-1 — this was a
rerun of that exact command, not a new config.

**Command:** identical to 2026-08-06-1
(`--init-from hover_stabilize_ppo_seed0.zip --timesteps 300000 --seed 0`),
attempted between the two runs described under 2026-08-06-1's follow-up
note above.

**Discovery method:** not observed live — reconstructed 2026-08-07 by
loading all four `tb_logs/waypoint_logs/PPO_0/` event files and comparing
step ranges and wall-clock timestamps. This run's event file
(`events.out.tfevents.1786012343...`) starts immediately after the first
full run ends and stops at cumulative step 692,224 — roughly 188k of the
intended ~300k fine-tuning steps — then a fresh event file for the second
full run begins ~78s later.

**Results (partial, final logged point before stopping)**
- `ep_rew_mean`: -284.59 at step 692,224
- Never reached a `model.save()` call (process was interrupted/stopped
  before completing `--timesteps 300000`), so this run did not itself
  overwrite the saved checkpoint — the second full run's completion is
  what determined the final `waypoint_nav_ppo_seed0.zip` contents.

**Verdict**
- [x] Inconclusive — not a deliberate experiment, a reconstructed
  data-integrity finding. No config lesson to draw from the numbers
  themselves; the lesson is procedural (see Notes).

**Notes / what to try next:**
- This is the run that made "which checkpoint is actually on disk"
  genuinely ambiguous for a period — see `docs/status.md`'s "Model / log
  directory layout" section for the fix (timestamped archiving in
  `waypoint_train.py`, added 2026-08-08).

### Run 2026-08-08-0 — entropy-runaway fix (gamma/ent_coef) + waypoint_bonus

**Git commit / project state:** `config.py` gained `waypoint_ppo_config()`
(waypoint-specific `PPOConfig`, does not affect hover);
`WaypointTaskConfig.waypoint_bonus` changed 5.0 → 15.0.
`waypoint_train.py` now explicitly overrides `model.gamma`/
`model.ent_coef` on the loaded model after `PPO.load()` — required
because `PPO.load()` otherwise restores hyperparameters from the
checkpoint file itself and silently ignores whatever `PPOConfig` is
passed alongside it (see `docs/status.md`'s IMPORTANT caveat). Also adds
timestamped archiving of every save to `model/model_weights/history/`.

**Command:**
```
python -m src.training.waypoint_train --init-from model/model_weights/hover_stabilize_ppo_seed0.zip --timesteps 300000 --seed 0
```

**Why this run:** diagnosed from `tb_logs` analysis (2026-08-07/08) of
the 2026-08-06 run(s) above — `train/std` climbed monotonically the
entire 300k-step run (0.85 → 1.18) instead of converging the way it did
for hover (0.68–0.85), and `ep_rew_mean` peaked at step ~729,088
(-274.38) then *declined* for the remaining ~73k steps, ending at -291.25
— a reversal, not a plateau. `approx_kl` (0.008–0.014), `clip_fraction`
(0.09–0.16), and `explained_variance` (0.96–0.98) all stayed in healthy
ranges throughout, ruling out PPO instability or a bad value function —
pointed specifically at `ent_coef=0.01` (inherited unchanged from
hover's `PPOConfig`) applying a constant entropy-increasing pull that
hover's stronger position-error gradient could override but waypoint's
weaker/more-delayed one (see `gamma` note below) could not.

**Environment config** (`WaypointTaskConfig`)
- `waypoints` / episode / reset / truncation bounds: unchanged from
  2026-08-06 runs
- Reward weights: position=1.0, velocity=0.05 (**unchanged — deliberately
  not touched this experiment**, see `config.py`'s comment on why),
  smoothness=0.01, survival=0.01, **waypoint_bonus=15.0 (was 5.0)**,
  landing_velocity_penalty=0.3

**Model config** (`waypoint_ppo_config()`, NEW — waypoint-specific)
- `gamma`: **0.995** (was 0.99) — extends the effective credit horizon
  from ~100 to ~200 steps, since the one-time `waypoint_bonus` was
  landing at or past the edge of what a 0.99 horizon could meaningfully
  shape given the ~108-step-per-waypoint pace implied by the episode
  budget
- `ent_coef`: **0.003** (was 0.01) — directly weakens the entropy pull
  identified above
- All other PPO hyperparameters unchanged (learning_rate 3e-4, n_steps
  2048, batch_size 64, n_epochs 10, gae_lambda 0.95, clip_range 0.2,
  net_arch {pi:[64,64], vf:[64,64]})
- **Critical implementation detail:** since this is an `--init-from` run,
  `gamma`/`ent_coef` above only take effect because `waypoint_train.py`
  explicitly sets `model.gamma`/`model.ent_coef` after `PPO.load()` —
  confirmed via the script's own printed "Overriding warm-started
  model's hyperparameters" line at the start of the run.

**Results (training)**
| Metric | Pre-fix run (2026-08-06) | This run |
|---|---|---|
| `train/std`, final | 1.17 | **0.8095** |
| `train/std` trend | climbed 0.85→1.18, never turned back | flat, 0.81–0.89 band throughout |
| `ep_rew_mean`, final | -291.25 (past its own peak of -274.38) | **-247.63, still climbing at cutoff** |
| `train/entropy_loss`, final | -6.21 | -4.78 |
| `train/explained_variance`, final | 0.966 | 0.9696 |
| `train/approx_kl`, final | 0.0112 | 0.0119 |

**Saved to:** `model/model_weights/waypoint_nav_ppo_seed0.zip`, archived
copy `model/model_weights/history/waypoint_nav_ppo_seed0_20260808_202404.zip`

**Verdict**
- [x] New baseline — entropy runaway confirmed fixed
- `std` no longer climbs; `ep_rew_mean` is still improving (not
  peaked-and-reversed) at the 300k cutoff — the first waypoint run where
  "train longer from here" is justified by the curve shape rather than a
  hopeful guess.

**Notes / what to try next:** see eval results below (Runs 2026-08-08-1
and -2) before deciding whether to continue training.

### Run 2026-08-08-1 — eval, before stale-obs bugfix (contaminated, do not use)

**Command:**
```
python -m src.training.evaluate.waypoint_evaluate --model model/model_weights/waypoint_nav_ppo_seed0.zip --seed 42
```
(model from Run 2026-08-08-0)

**Results**
- Success rate: 0.0% | Mean waypoints reached: 3.05/5 | Crash rate: 0.0%
  | Mean episode reward: -322.3
- New "stuck-leg closest approach" diagnostic (added this session to
  `waypoint_evaluate.py`): mean 0.148m, min 0.144m, max 0.150m — **20/20
  episodes reported getting within `waypoint_reach_radius` (0.15m)
  without it registering.**

**Verdict**
- [x] Revert / do not use — diagnostic output contaminated
- The stuck-leg numbers are internally inconsistent with the same run's
  own final-position-error data (several episodes ended 1.3–1.46m from
  target yet reported ~0.148m closest approach on that same leg —
  impossible if both numbers were real). Root-caused to a stale-`obs` bug
  in `WaypointGymEnv.step()` — see Run 2026-08-08-2 for the fix and clean
  re-read. **Do not use this run's stuck-leg numbers for any
  `waypoint_reach_radius` decision.**

**Notes:** the success-rate/waypoints-reached/crash-rate numbers above
are NOT affected by this bug (that data path was always correct) — only
the new per-leg diagnostic was contaminated, and only because it reads
`info["position_error_norm"]`, which the bug also affected.

### Run 2026-08-08-2 — eval, after stale-obs bugfix (clean)

**Git commit / project state:** `training/gym_wrapper/waypoint_gym_wrapper.py`
fixed — `step()` now re-derives `obs` after ANY waypoint transition
(`waypoint_bonus > 0.0`), not only the transition into landing
(`self._in_landing and waypoint_bonus > 0.0`, the old condition). Root
cause: on any transition step, `obs` (and therefore that step's reward
and `info["position_error_norm"]`) was left computed against the
just-passed target instead of the new one — the exact staleness the
code's own pre-existing comment already described for the landing-phase
case specifically, just never generalized to intermediate transitions
(1→2, 2→3, 3→4) which have the identical issue. **No retraining, no
checkpoint change** — this is a pure evaluation/observation-correctness
fix, re-run against the exact same weights as Run 2026-08-08-1.

**Command:** identical to 2026-08-08-1.

**Results**
- Success rate: 0.0% | Mean waypoints reached: **3.00/5** | Crash rate:
  0.0% | Mean episode reward: -292.6
- Failure breakdown: 20/20 timeout, 0/20 ever reached landing phase
- Stuck-leg closest approach (clean): **mean 0.850m, min 0.184m, max
  1.390m — 0/20 episodes got within `waypoint_reach_radius` (0.15m) on
  their stuck leg.**

**Verdict**
- [x] New baseline — `waypoint_reach_radius` question now genuinely
  settled
- No episode came remotely close to the reach radius on its stuck leg.
  **`waypoint_reach_radius=0.15` is confirmed NOT the bottleneck — do not
  widen it based on this or any earlier data.**

**Notes / what to try next:**
- New structural observation, not yet confirmed as a real factor: 10/20
  episodes stalled at exactly 4/5 waypoints, final pos error clustered
  0.98–1.47m, consistently on the wp3→wp4 leg — at 1.50m, the longest
  single leg in the route (others: 1.12m, 1.12m, 1.22m). Could be "needs
  more training" (consistent with the curve still climbing in
  2026-08-08-0) or "genuinely harder leg regardless of training progress"
  — not yet distinguished. Check again after the next training run
  before acting on it (e.g. before considering re-spacing waypoints).
- Both prerequisites for "train more" are now met for the first time
  this task: curve still climbing at cutoff (2026-08-08-0), and the two
  other candidate explanations (reach radius, stale-obs corruption) ruled
  out/fixed rather than left open. Planned next run: continue training
  from the current `waypoint_nav_ppo_seed0.zip` for another few hundred k
  steps, re-eval with `--seed 42` for direct comparability, and check
  whether the wp3→wp4 stall resolves.
- `velocity_penalty_weight` (0.05, unchanged since 2026-08-06) remains a
  candidate for a future experiment if the wp3→wp4 pattern doesn't
  resolve with more training — deliberately not touched this session to
  keep the ent_coef/gamma fix's effect isolated and attributable.

### Run 2026-08-08-3 — velocity_penalty_weight lowered 0.05→0.02 (regression, reverted)

**Git commit / project state:** `WaypointTaskConfig.velocity_penalty_weight`
changed 0.05 → 0.02, all other config unchanged from Run 2026-08-08-2's
checkpoint (802,816 steps).

**Command:**
```
python -m src.training.waypoint_train --init-from model/model_weights/waypoint_nav_ppo_seed0.zip --timesteps 300000 --seed 0
```

**Why:** hypothesis going in — the velocity penalty was suppressing
commitment to travel across 1-1.5m waypoint gaps, since it applies every
step regardless of how far from target the drone is.

**Results (training)**
| Metric | Final value |
|---|---|
| `ep_rew_mean` | -185.99 (recovered from a -284.62 dip, still near its own peak — healthy curve, not unstable) |
| `train/std` | 0.803 (flat 0.80–0.83 throughout — entropy fix still holding) |
| `explained_variance` | 0.945 |

**Results (eval, `--seed 42`)**
- Mean waypoints reached: **1.35/5** (down from 3.00/5)
- Mean reward: -202.0 (better, but NOT comparable to the 0.05-scale
  baseline — lower velocity_penalty_weight directly lowers every step's
  cost regardless of task performance)
- Stuck-leg closest approach: mean 0.271m (down from 0.850m) — episodes
  stalled MUCH closer to target on average, but still failed to durably
  enter the 0.15m radius, mostly on early/short legs

**Verdict**
- [x] Revert — hypothesis was backwards
- Training curve was healthy (ruling out "needed more steps to adapt" as
  the explanation). The stuck-leg data shows why it regressed anyway:
  the penalty's real job wasn't suppressing travel commitment, it was
  forcing deceleration/stabilization precisely at each target. Removing
  it made the drone faster but less precise, and precision near-target
  mattered more for completion than travel speed did. **Reverted to
  0.05.** Do not re-lower without new evidence pointing the other way.

**Notes:** this is a genuine, repeatable finding (theory tested,
falsified, reverted with the mechanism understood) — not a wasted run.

### Run 2026-08-09-0 — checkpoint sweep, 802,816-step checkpoint confirmed as local optimum

**Git commit / project state:** config reverted to Run 2026-08-08-2's
state (`velocity_penalty_weight=0.05`). `waypoint_train.py` gained
`--checkpoint-every` this session (saves intermediate checkpoints via
SB3's `CheckpointCallback`, not just the final one).

**Command:**
```
cp model/model_weights/history/waypoint_nav_ppo_seed0_20260808_202404.zip model/model_weights/waypoint_nav_ppo_seed0.zip
python -m src.training.waypoint_train --init-from model/model_weights/waypoint_nav_ppo_seed0.zip --timesteps 300000 --seed 0 --checkpoint-every 50000
```

**Why:** two separate 300k-step continuations from the 802,816-step
checkpoint (this run's predecessor and Run 2026-08-08-3) had both
regressed waypoints-reached despite improving `ep_rew_mean` — needed to
know whether that was consistent across the whole run or just an
artifact of looking only at the endpoint.

**Results (eval, `--seed 42`, each of the 6 checkpoints saved during the run)**
| Cumulative steps | Waypoints reached |
|---|---|
| 852,816 | 2.15 |
| 902,816 | 1.90 |
| 952,816 | 1.75 |
| 1,002,816 | 1.45 |
| 1,052,816 | 2.15 |
| 1,102,816 | 1.40 |

(802,816 baseline for reference: 3.00)

**Verdict**
- [x] New baseline confirmed — DO NOT train further from a later
  checkpoint without a structural change first
- Every single post-baseline checkpoint is worse than 802,816, across
  the entire 300k-step span — not a single peak-then-decline, more a
  step down into a noisy lower band (1,052,816 partially recovers before
  dropping again) that never returns to 3.00. Combined with Run
  2026-08-08-3 (also worse, different reward config), three separate
  continuations from the same baseline have now all regressed. "Just
  train longer" is closed off as a strategy for the current reward
  shape. `waypoint_nav_ppo_seed0.zip` restored to the 802,816-step
  baseline after this sweep.

**Notes / what to try next:** a structurally different lever is needed,
not another continuation or magnitude tweak — see Run 2026-08-09-2.

### Run 2026-08-09-1 — seed robustness check + episode-length test (both free, no training)

**Git commit / project state:** `waypoint_evaluate.py` gained
`--episode-len-sec` this session (overrides `episode_len_sec` for eval
only, no retraining — tests whether budget is the constraint at zero
training cost, since the policy's per-step behavior doesn't change,
only when timeout fires).

**Commands:**
```
for s in 42 7 100 123; do
  python -m src.training.evaluate.waypoint_evaluate --model model/model_weights/waypoint_nav_ppo_seed0.zip --seed $s
done
python -m src.training.evaluate.waypoint_evaluate --model model/model_weights/waypoint_nav_ppo_seed0.zip --seed 42 --episode-len-sec 30
python -m src.training.evaluate.waypoint_evaluate --model model/model_weights/waypoint_nav_ppo_seed0.zip --seed 42 --episode-len-sec 40
```
(802,816-step baseline checkpoint for all of the above)

**Results — seed robustness**
| Seed | Waypoints reached |
|---|---|
| 42 | 3.00 |
| 7 | 3.00 |
| 100 | 2.95 |
| 123 | 2.70 |

**Results — episode length**
| Episode length | Waypoints reached |
|---|---|
| 20s (trained) | 3.00 |
| 30s | 2.80 |
| 40s | 2.75 |

**Verdict**
- [x] New baseline — 3.00/5 confirmed robust (not a lucky eval-seed
  draw); budget confirmed NOT the bottleneck
- Seed sweep: tight 2.70–3.00 range across 4 seeds — real, stable
  property of the checkpoint. Episode-length sweep: no improvement with
  more time, if anything slightly worse. At 40s several episodes still
  showed 4/5 waypoints with 1.3–1.5m final error — no further progress
  even with 20 extra seconds, meaning the policy is genuinely stuck on
  that leg, not merely out of time. Don't extend `episode_len_sec`
  expecting this alone to help.

### Run 2026-08-09-2 — potential-based progress shaping (written + reviewed, not yet run)

**Git commit / project state:** `WaypointTaskConfig.progress_shaping_weight`
added (10.0). `WaypointGymEnv.step()`/`_progress_reward()` implements
Ng-Harada-Russell-style potential-based shaping: reward gains
`progress_shaping_weight * (distance closed this step)`, positive for
closing distance to the current target, negative for moving away.
Disabled during `self._in_landing` (see below).

**Why:** three magnitude-tweak levers (ent_coef/gamma — kept,
velocity_penalty — reverted, waypoint_bonus — kept but unbundled
priority lowered) and one budget test (ruled out) exhausted without
recovering past the 802,816-step baseline. The existing per-step penalty
(`position_error_weight * distance`) penalizes absolute distance every
step but never directly rewards CLOSING it — consistent with the
observed pattern of `ep_rew_mean` improving while waypoints-reached got
worse (Runs 2026-08-08-3, 2026-08-09-0). This term directly targets that
gap instead of another weight guess.

**Review before running (2026-08-09):**
- Cliff-avoidance at waypoint transitions verified correct: both sides
  of the per-step delta are measured against the same pre-transition
  target; the cached baseline for the *next* step uses the
  post-transition distance. First-step-after-reset seeded with the
  actual starting distance (no spurious full-route-length jump).
- **Bug caught before any run used it:** a magnitude check found this
  term roughly comparable to, not clearly dominated by,
  `landing_velocity_penalty_weight`'s safety penalty at unsafe descent
  speeds (~+0.33/step vs. ~-0.3/step at 1.0 m/s, well above
  `landing_max_velocity=0.15`) — a real bias toward rushing the
  touchdown. `velocity_penalty_weight` already gets swapped for a
  heavier landing-specific value once `_in_landing`; this term wasn't
  given the same treatment when first written. Since no episode has ever
  reached the landing phase, there was no prior run to catch this.
  **Fixed** by returning 0.0 from `_progress_reward()` while
  `self._in_landing` — a design correction, not an observed failure.
- Minor/cosmetic: the implementation omits the `γ` discount on the next
  state's potential that strict Ng et al. shaping requires
  (`F=γΦ(s')-Φ(s)`, implemented here as `Φ(s')-Φ(s)`). Negligible at
  `gamma=0.995`, not worth blocking on, but not the exact textbook
  policy-invariance guarantee if anyone checks.

**Verdict**
- [ ] Not yet run — first task for 2026-08-10

**Notes / what to try next:** run from the restored 802,816-step
baseline with `--checkpoint-every 50000` from the start this time (not
added after the fact). Sweep all 6 checkpoints against `--seed 42`
rather than trusting the final one, given Run 2026-08-09-0's finding.
Watch specifically: (1) whether any episode finally reaches the landing
phase — new information this task has never produced; (2) if one does,
whether `hard_landing` stays at 0%, confirming the landing-phase
exclusion fix was worth making; (3) `train/std` stays flat, confirming
this doesn't reopen the entropy-runaway issue from Run 2026-08-06-1.


### Run 2026-08-16-0 — hover_stabilize_ppo_seed0, from-scratch baseline, 500k steps

Fresh from-scratch run (no init_from — hover_train.py has no warm-start path),
seed=0, --checkpoint-every 25000... actually saved at 50k intervals per SB3's
CheckpointCallback rounding to nearest n_steps multiple. 11 checkpoints total
(50k-500k) + final save, all backfilled through the registry (seed=42, 20
episodes/checkpoint):

| Steps        | Mean pos error | Crash rate | Hash        |
|--------------|-----------------|------------|-------------|
| 450,000      | 0.020 m         | 0%         | f9153039... |
| 400,000      | 0.024 m         | 5%         | 33f67eba... |
| 500,000      | 0.024 m         | 0%         | 3a406650... |
| final(~502k) | 0.025 m         | 5%         | 3c742f0d... |
| 300,000      | 0.034 m         | 50%        | 441c1a6e... |
| 250,000      | 0.035 m         | 80%        | dd380618... |
| 350,000      | 0.044 m         | 10%        | bf1d2c09... |
| 200,000      | 0.074 m         | 0%         | 87620be6... |
| 150,000      | 0.202 m         | 0%         | 101e06f7... |
| 50,000       | 0.251 m         | 0%         | 2bc8eb84... |
| 100,000      | 0.264 m         | 0%         | 6170c1f8... |

Champion: 450,000-step checkpoint (f9153039...) — lowest position error AND
0% crash rate simultaneously, not a tradeoff. Also mildly beats the final
save (0.020 vs 0.025 m, 0% vs 5% crash) — same "final save isn't
automatically best" shape as the waypoint story, much gentler here.

Real finding: a crash-rate spike at 250k-350k (peaking 80% at 250k) that
resolves by 450k, WHILE position error over the same window looks good
(0.034-0.044 m, second-best band overall). Checking position error alone
would have missed this entirely — see theory-log.md Theory 2026-08-16-0 for
the working hypothesis on mechanism. Promoted 450k checkpoint to
hover_champion.zip via checkpoint_manager.

Full episode-level backfill logged in registry.jsonl (task=hover).

### Run 2026-08-16-1 — hover_stabilize_ppo_seed0_1a, warm-started from champion, 300k steps

Trained from hover_champion.zip with Stage 1a preset (single kick,
0.1-0.3 m/s, step window 60-150, recovery threshold 0.2m/60 steps).
6 checkpoints (50k-300k) + final (~301k), all evaluated with --stage 1a.

Result: NULL. The untouched champion (zero 1a training) passes the exact
same mastery gate the trained checkpoints do -- 0% crash, 100% recovery,
0.021m mean error, every single recovery logged as "0 steps" across every
checkpoint including the untrained baseline. Confirmed via direct
side-by-side eval of hover_champion.zip under --stage 1a. Level 1's
magnitude range (0.1-0.3 m/s) never displaces the drone past the 0.2m
recovery threshold in the first place -- sub-stage 1a as specified did
not exercise recovery behavior at all, so the ~300k training steps spent
on it produced no measurable change. Not a wasted debugging session --
this is a real, useful negative result (see plan doc update below) -- but
1a's checkpoints should NOT be treated as "hover champion + kick-hardened,"
they're statistically indistinguishable from the champion alone.

One checkpoint (300,000 steps specifically) showed 10% crash rate (2/20,
both tilt) where every other checkpoint including the champion baseline
showed 0% -- see theory-log.md 2026-08-16-2. Given the null result above,
this is now read as more likely noise on a 2-episode sample (or a
transient artifact of continued fine-tuning) than a real capability
regression, but not yet confirmed either way -- reproduction check with
a different seed still open.

Decision: do not promote any 1a checkpoint as a new champion. Proceed to
1b (introduces Level 2, 0.3-0.6 m/s) directly from hover_champion.zip,
not from any 1a checkpoint, since 1a training added no verified value to
warm-start from. Revise the plan doc's magnitude levels before running 1b
-- see below.

## Superseding decision, 2026-08-25: 3-type/5-level scoped design replaces the 1a/1b/1c/... roadmap

The strict sequential sub-stage curriculum above (1a -> 1b -> 1c -> ...)
is superseded, not continued. See
`docs/architecture/hover-disturbance-3x5-design.md` for the full design
and rationale. Summary: 3 disturbance types (kick, torque, wind) x 5
magnitude levels each, one event sampled per episode (type uniform,
level uniform 1-5), trained together in one run rather than staged
narrow presets one at a time -- directly motivated by 1a's null result
above (a single narrow preset can burn a full run with zero learning
signal; sampling the whole scoped space at once avoids repeating that).
Kick's magnitude floor was corrected up from 1a's confirmed-too-weak
0.1-0.3 m/s to 0.3-0.5 m/s at L1. Torque and wind level bounds are
first-guess estimates, not yet independently validated the way kick's
were.

Takeoff and landing are explicitly out of scope for this push --
scripted, not learned, decided separately from the disturbance work.

### Run 2026-08-25-0 — hover_stabilize_ppo_seed0_disturbance_3x5, first 3x5 run, 500k steps (superseded by bug fix below)

From hover_champion.zip, single-process (pre-parallelization), --stage
disturbance_3x5. Hash `706fcaceb85a...`.

Eval (90 episodes, --stage disturbance_3x5): overall crash 33.3%. Kick
crash rate climbed cleanly with level (0%/33%/83%/50%/100%) -- a real,
well-calibrated difficulty ramp, unlike 1a. Torque similar shape
(0%/0%/33%/67%/75%). **Wind numbers were bogus**: recovery read as low as
12% at L5 despite in-window steady-state error staying under 0.06m the
whole time -- a bug, not a real finding (see below).

### Bug found + fixed, 2026-08-25 — wind recovery window didn't fit inside the episode

`WIND_CONFIG.duration_steps=90` (~3s) combined with the shared
`[60,150]`-step onset window and `recovery_hold_steps=60` meant a wind
window ending late in that range left no room for the required 60-step
recovery hold before the 240-step (8s) episode ended -- recovery was
**structurally impossible** for a large fraction of episodes regardless
of policy quality. Fixed two ways: `duration_steps` 90->60 in
`config.py`, and `hover_gym_wrapper.py`'s onset-window clamp now
subtracts `recovery_hold_steps` too, not just the event's own duration
-- so this class of bug can't recur for any future type/duration/window
combination.

### Infra, 2026-08-25 — parallel training (`--n-envs`) added

PyBullet stepping in a single process, not GPU compute, is the actual
bottleneck for this workload (tiny `[64,64]` MLP) -- confirmed this
rather than assumed it before adding GPU support. Added `--n-envs` to
`hover_train.py` (SB3 `SubprocVecEnv`, one PyBullet instance per
process). `ppo_policy.py`'s `build_ppo` now skips its internal
`Monitor`-wrap when given an already-vectorized env. `--checkpoint-every`
divides by `n_envs` internally (SB3's callback fires once per vectorized
step, not once per single-env step -- easy to get silently wrong).
Measured ~2600 fps at `--n-envs 6` vs. single-process baseline.

Two warm-start bugs surfaced and fixed while wiring this up:
- `PPO.load(path); model.set_env(vec_env)` raises `AssertionError` if the
  checkpoint's own `n_envs` (always 1 for anything trained before this)
  doesn't match the new env's count. Fixed: `PPO.load(path, env=vec_env)`
  instead, which re-initializes rollout buffers against the given env
  rather than asserting they match.
- `hover_champion.zip` was missing after moving to a new machine
  (WSL/`DESKTOP-5B0JLP7`, migrated from `debian` via HuggingFace
  upload/download) -- large model weights aren't in git, don't come
  along with a plain clone. Not a code bug, but cost a debugging cycle
  before being recognized as a missing-file problem, not a `.zip.zip`
  path-construction bug (SB3's loader's own fallback-suffix behavior
  made the real error message misleading).

### Run 2026-08-25-1 — hover_stabilize_ppo_seed0_disturbance_3x5, wind-fixed + parallel (--n-envs 6), 500k steps

From hover_champion.zip (same parent as Run 2026-08-25-0 -- this
restarted disturbance training from the undisturbed baseline again, not
building on 2026-08-25-0's steps), `--n-envs 6`, wind bug fix in place.
Hash `3df3deb1a99f...`.

Eval (90 episodes): overall crash 33.3% (same aggregate as
2026-08-25-0's pre-fix run, coincidentally -- composition shifted: kick
50% (was 58%), torque 54% (was 41%, got worse), **wind 0% crash / 100%
recovery all 5 levels -- fully mastered, fix confirmed working.**
`train/std` climbed the entire run (1.15->1.49) instead of settling --
flagged as a live concern, not yet acted on.

### Diagnostic, 2026-08-25 — checkpoint sweep tool built (`hover_checkpoint_sweep.py`)

Re-evaluates every checkpoint from one run under an identical seeded
condition (same start/disturbance draw sequence per checkpoint), to
measure whether a run is still improving or has plateaued from actual
task performance rather than inferring it from `train/std`/`approx_kl`
alone. Verdict: compares trailing-3-checkpoint mean crash rate against
the previous 3; >3pp improvement = "still learning," else "plateaued."

Swept Run 2026-08-25-1's own 10 checkpoints (50k-500k, seed=0, 60
episodes each): **PLATEAUED**, trailing window (300k-500k) mean crash
33.3% vs. prior window (150k-300k... actually the two nearest 3-checkpoint
windows) mean crash rate essentially flat/regressed, -4.4pp "improvement."

### Run 2026-08-25-2 — ent_coef/gamma fix + continued training, 500k steps

Hypothesis: `train/std` never stopped climbing across 2026-08-25-1
because `ent_coef` (0.01 default) never adapted across ~1M cumulative
disturbance-training steps -- every warm-start went through `PPO.load()`,
which restores hyperparameters from the checkpoint file itself, ignoring
`config.py`. Same failure signature as the 2026-08-09 waypoint-nav
finding (entropy pull winning over a weak gradient), fixed there by
lowering `ent_coef`/raising `gamma`. Added `--ent-coef`/`--gamma` flags
to `hover_train.py` that set the value directly on the live model object
post-construction (`config.ppo` alone doesn't reach a warm-started
model). Ran 500k more steps from 2026-08-25-1's checkpoint with
`--ent-coef 0.003 --gamma 0.995`.

Checkpoint sweep verdict: **still PLATEAUED** -- trailing window
(450k-500k window) mean crash 37.2% vs. prior 36.7%, -0.6pp. The
hyperparameter fix alone did not resolve it. Torque got noticeably worse
at the final checkpoint specifically (33%->56% between adjacent 50k
checkpoints) -- flagged as possibly small-sample noise (n~4-8 per
type/level bucket at 60 total eval episodes), not confirmed.

### Diagnostic, 2026-08-25 — tilt-criterion diagnostic (`hover_tilt_diagnostic.py`): the crash check itself was the bottleneck

Two consecutive interventions (raw continued training, then the
ent_coef/gamma fix) landing at the same ~37% crash rate pointed at a
structural ceiling rather than an undertrained policy. Candidate:
`max_tilt_rad=0.4` rad (~23deg) was checked with **zero hold-time** -- a
single momentary breach ended the episode permanently, unlike
`recovery_hold_steps` elsewhere in this codebase, which requires 60
*sustained* steps under threshold specifically because a momentary touch
isn't real recovery. No equivalent grace existed in the crash direction.

Method: re-ran eval with `max_tilt_rad` loosened to 1.2 rad (~69deg,
diagnostic-only, not a training config change) and classified every
episode that crossed the *real* 0.4 rad line: did it settle back down
and finish cleanly (criterion was the artifact), or genuinely keep
diverging (real capability ceiling)?

**Result: 68% (17/25) recovered cleanly once given room** -- mostly
kick, peak tilt up to 55deg, final position error as low as 0.017m.
**Only 12% (3/25) were genuine loss of control** -- all torque L5
(9-10 rad/s), peak tilt 72-75deg, a real qualitative jump from the
recovered group, not just "a bit higher." 20% ambiguous (mostly torque
L3-L4, settled but with poor final position error).

Conclusion: the crash *criterion*, not the policy, was the dominant
cause of the two-run plateau. Also explains why the ent_coef/gamma fix
didn't help -- the training signal itself was corrupted by false-positive
crash penalties on cases that were actually fine, independent of policy
entropy.

### Fix, 2026-08-25 — sustained-hold tilt criterion (`max_tilt_hold_steps`)

Mirrors `recovery_hold_steps`'s own non-momentary-touch principle,
applied in the crash direction: tilt must exceed `max_tilt_rad` for
`max_tilt_hold_steps` (new field, default 6 steps / ~0.2s @ 30Hz)
*consecutive* steps before truncating, not a single-step check.
`out_of_bounds`/altitude remain single-step checks deliberately -- no
equivalent "brief excursion that self-corrects" case exists for
physically leaving the flight volume. `max_tilt_hold_steps=6` is a first
guess (sized to pass a one-step corrective spike while still catching
the observed genuine-crash cases, which reached 70+ degrees implying
several steps of sustained climb already) -- **not yet independently
validated with its own diagnostic pass** the way kick's magnitude levels
were.

Re-evaluating the EXACT SAME checkpoint from Run 2026-08-25-2 (no
retraining) under the corrected criterion: crash rate dropped from
~37% to **23.3% (21/90)**, hash `9694bdcd86ea...`, purely from the
criterion fix. Wind stayed perfect. Torque L1-L3 now read 0% crash
(previously showed crashes even at low levels) -- newly fully mastered.
Torque L4/L5 and kick L3-L5 remain genuinely problematic even under the
corrected criterion (~48% kick crash rate) -- these are real, not
artifacts. Notable new pattern: most remaining kick crashes now happen
well AFTER the drone visibly recovered from the disturbance (e.g. best
position error 0.001-0.03m mid-episode, crash 10-40 steps later with no
new disturbance event) -- looks like a late, separate marginal-stability
issue distinct from the initial-recovery phase, not yet investigated
further.

### Run 2026-08-25-3 — hover_stabilize_ppo_seed0_disturbance_3x5_tiltfix, 500k steps (first run under corrected criterion)

From the 9694bdcd86ea checkpoint (ent_coef/gamma-fixed, old tilt
criterion), `--ent-coef 0.003 --gamma 0.995` (re-applied), `--n-envs 6`,
new tag `disturbance_3x5_tiltfix` (first run to use a distinct tag
rather than overwriting `disturbance_3x5` in place -- kept so this and
prior checkpoints stay separately comparable).

Checkpoint sweep (10 checkpoints, 50k-500k, seed=0, 60 episodes each):
**STILL IMPROVING**, +5.6pp (trailing window 20.0% vs. prior 25.6%).
Kick showed a real (noisy but directional) downtrend across the run:
50%->55%->45%->35%->55%->45%->40%->45%->40%->25%, ending well below the
~48% pre-tiltfix baseline. Torque stayed flatter/noisier (17-39%, no
clear trend) -- next thing to watch. Wind stayed perfect throughout.

This is the first run where more training steps produced a real,
reproducible improvement on kick/torque -- unlike Runs 2026-08-25-1 and
2026-08-25-2, both of which plateaued. Consistent with the tilt-criterion
diagnostic's conclusion: the earlier plateaus were very likely measuring
a corrupted training signal, not a real capability ceiling.

### Run 2026-08-25-4 — hover_stabilize_ppo_seed0_disturbance_3x5_tiltfix2, 500k steps

From `..._tiltfix.zip`'s final save (no `--ent-coef`/`--gamma` reapplied
-- already baked into the checkpoint from the previous run, confirmed
`PPO.save()` persists live hyperparameter values). `--n-envs 6`. Hash
`bbc4335cb6ea...`.

Checkpoint sweep: **STILL IMPROVING**, +3.3pp (trailing window 20.6% vs.
prior 23.9%). Final checkpoint (499,980 steps): crash 20.0%, kick 35%,
torque 28%, wind 0%. Best single checkpoint in this run was 449,982 steps
(18.3% crash, kick 35%, torque 22%) -- final save is not automatically
best, same pattern as every prior baseline in this project; worth an
eval-based champion pick from checkpoints, not just trusting the final
save, once this line of training is considered done.

**Current status, end of 2026-08-25 session:** overall crash rate has
gone from ~37-40% (pre-tiltfix plateau) to ~18-23% across two
tiltfix-line runs, with wind fully mastered and torque L1-L3 fully
mastered. Still improving; still short of the <10% mastery gate defined
in `hover-robustness-curriculum-plan.md`. Not yet at a stopping point --
see `docs/status.md` for the current open-items list and next action.
