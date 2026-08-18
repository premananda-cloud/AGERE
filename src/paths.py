"""
Single source of truth for where trained artifacts live on disk.

train.py, evaluate.py, demo.py, and demo_intel.py all import from here
instead of each hardcoding (or worse, each independently guessing) a save/
load path. See docs/conventions.md for the full directory-layout
convention this implements and why weights/logs live outside git (pushed
to Hugging Face instead — see that doc for the current repo/workflow).

Layout convention (as of the waypoint-nav addition):
  - model/model_weights/  — ONE flat directory for all tasks' checkpoints.
    Tasks are distinguished by filename prefix (hover_stabilize_ppo*.zip
    vs waypoint_nav_ppo*.zip), not by subdirectory. This is a deliberate
    change from the original one-subdirectory-per-task layout (hover's
    own model/hover_stabilize/ existed briefly) — flat naming makes it
    obvious at a glance which checkpoints exist across all tasks, and
    keeps --init-from paths (waypoint_train.py warm-starting from a hover
    checkpoint) from crossing a directory boundary that implied "these
    are unrelated."
  - tb_logs/<task>_logs/  — STILL split per task (hover_logs, waypoint_logs).
    TensorBoard runs are for comparing training curves within one task,
    not across tasks, so keeping them separated by directory (rather than
    by filename prefix) matches how they're actually browsed.

Extension point for future tasks: add the new task's filename prefix
convention to MODEL_WEIGHTS_DIR (no new model/ subdirectory needed) and
its own tb_logs/<task>_logs/ + path-helper function here.
"""

from pathlib import Path

# Resolved relative to this file's location (src/paths.py -> repo root is
# one level up from src/), so this works regardless of the caller's cwd.
REPO_ROOT = Path(__file__).resolve().parent.parent

MODEL_ROOT = REPO_ROOT / "model"
TB_LOG_ROOT = REPO_ROOT / "tb_logs"

# Single flat directory for all tasks' checkpoint files — see module
# docstring. Tasks are told apart by filename prefix, not subdirectory.
MODEL_WEIGHTS_DIR = MODEL_ROOT / "model_weights"

# --- hover/stabilize task -------------------------------------------------
HOVER_STABILIZE_TB_LOG_DIR = TB_LOG_ROOT / "hover_logs"


def hover_stabilize_model_path(seed: int | None = None, tag: str | None = None) -> Path:
    """Standard save/load path for a hover/stabilize PPO checkpoint.

    seed=None, tag=None       -> model/model_weights/hover_stabilize_ppo.zip
    seed=N,    tag=None       -> model/model_weights/hover_stabilize_ppo_seedN.zip
    seed=N,    tag="1a"       -> model/model_weights/hover_stabilize_ppo_seedN_1a.zip

    tag added 2026-08-16 for the disturbance curriculum (Stage 1 sub-stages
    1a, 1b, 1c, ...) -- without it, every sub-stage's from-scratch-or-warm-
    started save would clobber the same canonical path, exactly the
    path-mutability problem the model registry exists to work around at the
    eval-tracking layer. This solves it one level earlier, at the filename
    layer, so sub-stage checkpoints are distinguishable on disk by name
    alone, not just by registry hash lookup.

    Creates the directory if it doesn't exist yet (safe to call before
    saving; a no-op if just reading an existing path for loading).
    """
    MODEL_WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    name = f"hover_stabilize_ppo_seed{seed}" if seed is not None else "hover_stabilize_ppo"
    if tag is not None:
        name = f"{name}_{tag}"
    return MODEL_WEIGHTS_DIR / f"{name}.zip"


# --- waypoint navigation + landing task ------------------------------------
WAYPOINT_TB_LOG_DIR = TB_LOG_ROOT / "waypoint_logs"


def waypoint_model_path(seed: int | None = None) -> Path:
    """Standard save/load path for a waypoint-nav PPO checkpoint.

    seed=None -> model/model_weights/waypoint_nav_ppo.zip
    seed=N    -> model/model_weights/waypoint_nav_ppo_seedN.zip

    Same pattern as hover_stabilize_model_path() above — same flat
    MODEL_WEIGHTS_DIR, distinguished only by the waypoint_nav_ prefix.
    """
    MODEL_WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    name = f"waypoint_nav_ppo_seed{seed}" if seed is not None else "waypoint_nav_ppo"
    return MODEL_WEIGHTS_DIR / f"{name}.zip"
