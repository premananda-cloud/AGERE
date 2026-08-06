# Repo Conventions — Trained Artifacts, Weights, and Logs

**Purpose:** as of 2026-08-02, `model/` and `tb_logs/` were pulled out of
git and pushed to Hugging Face instead (both directories are now
`.gitignore`d). This doc is the standing reference for the layout and
workflow that replaces "just save wherever and commit it" — read this
before adding a new task's training code, not just for hover/stabilize.

## Directory layout

```
model/
  hover_stabilize/
    hover_stabilize_ppo.zip           # unseeded / default run
    hover_stabilize_ppo_seed0.zip     # Stage 3 multi-seed runs
    hover_stabilize_ppo_seed1.zip
    hover_stabilize_ppo_seed2.zip
tb_logs/
  hover/
    PPO_1/  PPO_2/  ...               # SB3 auto-numbers subfolders per run
```

One subdirectory per task, both under `model/` and `tb_logs/`. When the
next task starts (waypoint navigation, per the Backseat Driver plan),
it gets its own `model/<task_name>/` and `tb_logs/<task_name>/` — not a
flat dump of every task's checkpoints in one folder, and not reusing
`hover_stabilize`'s subfolder for a different task's weights.

## `src/paths.py` is the single source of truth

`src/training/hover_train.py`, `src/training/evaluate/hover_evaluate.py`,
`src/training/evaluate/hover_evaluate_disturbance.py`, and
`src/training/demo/hover_demo.py` all import their save/load paths from
`src/paths.py` rather than each hardcoding (or independently guessing) a
location. (`demo_intel.py`, a Mesa/OpenGL-compatibility variant of the
demo script, has been removed — re-add something like it under
`src/training/demo/` if that need resurfaces.) If you're adding a new
task's training entry point, add its path constants and a
`<task_name>_model_path()` helper function to `src/paths.py`, following
the same pattern as `hover_stabilize_model_path()` — don't invent a new
per-script convention.

**Why centralize this:** before this convention, `train.py` saved to
whatever the working directory happened to be when you ran it, which is
exactly how weights ended up scattered at the repo root instead of a
predictable location. A single module that every entry point imports from
means there's one place to change if the layout ever needs to move again,
and no risk of `train.py` and `evaluate.py` quietly disagreeing about
where a checkpoint lives.

## Why weights/logs aren't in git

Binary checkpoints and TensorBoard event files grow without bound as
training runs accumulate (already 4 `.zip`s and 6 `tb_logs/hover/PPO_*`
runs as of this doc) and don't compress or diff usefully in git — every
clone would carry every historical checkpoint forever, even ones long
superseded. `.gitignore` covers both `model/` and `tb_logs/` at the repo
root.

## Where weights actually live: Hugging Face Hub

Model weights are pushed to Hugging Face instead of git. When pushing a
new checkpoint:

- Note the Hugging Face revision/commit (or tag) in the corresponding
  `docs/training-log.md` entry for that run, alongside the config values
  already recorded there. The log entry is what ties a specific set of
  results back to the exact weights that produced them — without that
  cross-reference, "which HF checkpoint matches the 0.018 m seed-2 result"
  becomes a guessing game once weights no longer sit next to the code and
  config that made them.
- The `huggingface_sb3` package (`push_to_hub`/`load_from_hub`) is a
  closer fit than raw git-lfs for anything built on Stable-Baselines3,
  since it understands SB3's model format directly, generates a model
  card, and can attach an eval video. Prefer it over manual git-lfs
  commands for this project's checkpoints.
- Keep `model/` populated locally with whatever you're actively working
  with (that's what `src/paths.py`'s helpers assume) — the Hugging Face
  repo is the durable/shared copy, not a replacement for having weights
  on disk while iterating.

## Checklist for a new task's training code

1. Add `<task_name>_model_path(seed=None)` and the matching `MODEL_DIR`/
   `TB_LOG_DIR` constants to `src/paths.py`.
2. Point that task's `hover_train.py`-equivalent,
   `evaluate/hover_evaluate.py`-equivalent, etc. at those helpers — same
   pattern as hover/stabilize's entry points (one training script directly
   under `training/`, plus `demo/`, `evaluate/`, and `gym_wrapper/`
   subpackages for the others).
3. Confirm `model/<task_name>/` and `tb_logs/<task_name>/` fall under the
   existing `.gitignore` rules (they should, if those rules are on the
   parent `model/`/`tb_logs/` directories rather than hover-specific
   paths — worth double-checking rather than assuming).
4. Push checkpoints to the Hugging Face repo and record the revision in
   that task's training log, same as above.
