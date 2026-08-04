"""
Single source of truth for where trained artifacts live on disk.

train.py, evaluate.py, demo.py, and demo_intel.py all import from here
instead of each hardcoding (or worse, each independently guessing) a save/
load path. See docs/conventions.md for the full directory-layout
convention this implements and why weights/logs live outside git (pushed
to Hugging Face instead — see that doc for the current repo/workflow).

Extension point for future tasks: this project is a staged sequence
(hover/stabilize now, waypoint navigation next, per docs/hover-model-plan.md
and the wider Backseat Driver plan). When the next task starts, add its
own MODEL_DIR/TB_LOG_DIR pair and path-helper function here, following the
same one-subdirectory-per-task pattern — don't hardcode a new path
convention per script.
"""

from pathlib import Path

# Resolved relative to this file's location (src/paths.py -> repo root is
# one level up from src/), so this works regardless of the caller's cwd.
REPO_ROOT = Path(__file__).resolve().parent.parent

MODEL_ROOT = REPO_ROOT / "model"
TB_LOG_ROOT = REPO_ROOT / "tb_logs"

# --- hover/stabilize task -------------------------------------------------
HOVER_STABILIZE_MODEL_DIR = MODEL_ROOT / "hover_stabilize"
HOVER_STABILIZE_TB_LOG_DIR = TB_LOG_ROOT / "hover"


def hover_stabilize_model_path(seed: int | None = None) -> Path:
    """Standard save/load path for a hover/stabilize PPO checkpoint.

    seed=None -> model/hover_stabilize/hover_stabilize_ppo.zip
    seed=N    -> model/hover_stabilize/hover_stabilize_ppo_seedN.zip

    Creates the directory if it doesn't exist yet (safe to call before
    saving; a no-op if just reading an existing path for loading).
    """
    HOVER_STABILIZE_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    name = f"hover_stabilize_ppo_seed{seed}" if seed is not None else "hover_stabilize_ppo"
    return HOVER_STABILIZE_MODEL_DIR / f"{name}.zip"
