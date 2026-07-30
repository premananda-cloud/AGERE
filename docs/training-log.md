# Training Log — Hover/Stabilize Model

Living document. One entry per training run. Copy the template below for
each new run — don't edit past entries except to add follow-up notes; the
point is an honest record of what was tried, not a polished current state.

Cross-reference `hover-model-plan.md` for what each field means and what
counts as progress toward a usable model.

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
