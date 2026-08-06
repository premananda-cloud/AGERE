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
