"""
Checkpoint/artifact bookkeeping — task-agnostic, algorithm-agnostic.

This package answers "which checkpoint is which, and which one is
actually good" as a mechanical, data-backed question instead of one
reconstructed from devlog prose and file mtimes (see model_registry.py's
module docstring for the 2026-08-09 incident that motivated this).

Deliberately its own top-level package under src/, not nested inside
training/, because nothing here is specific to one task or one RL
algorithm the way training/gym_wrapper or policies/ are — a checkpoint
from any task, trained under any config, gets the same hash-identified
tracking, ranking, and archiving treatment. See docs/code-structure.md
("weight_manager/") for the full reasoning.

    model_registry.py      — append-only, content-hashed record of every
                              training run and eval, per checkpoint file.
    checkpoint_manager.py   — leaderboard / promote / archive / retire-task
                              operations built on top of the registry.
    check_std_window.py     — one-off diagnostic checking a specific
                              theory-log hypothesis (crash-rate spike vs
                              elevated train/std) against TensorBoard logs.
"""
