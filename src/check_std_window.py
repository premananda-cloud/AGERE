"""
Checks the theory-log.md Theory 2026-08-16-0 hypothesis: that the 250k-350k
crash-rate spike in the hover from-scratch run corresponds to elevated
train/std (action distribution spread) -- i.e. an aggressive/high-variance
correction phase, not some other mechanism.

Usage:
    python check_std_window.py                    # lists all runs + their step ranges
    python check_std_window.py --run PPO_7         # inspects one run's std curve
"""
import argparse
from pathlib import Path

from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

HOVER_LOGS = Path("tb_logs/hover_logs")


def load_scalar(run_dir: Path, tag: str):
    ea = EventAccumulator(str(run_dir), size_guidance={"scalars": 0})
    ea.Reload()
    if tag not in ea.Tags().get("scalars", []):
        return []
    return [(e.step, e.value) for e in ea.Scalars(tag)]


def list_runs():
    print(f"{'run':<10}{'first_step':<14}{'last_step':<14}{'n_points'}")
    for run_dir in sorted(HOVER_LOGS.glob("PPO_*")):
        points = load_scalar(run_dir, "train/std")
        if not points:
            print(f"{run_dir.name:<10}(no train/std tag found)")
            continue
        steps = [s for s, v in points]
        print(f"{run_dir.name:<10}{min(steps):<14}{max(steps):<14}{len(points)}")
    print("\nMatch the run whose last_step is ~500,000 (or close) to today's hover run. "
          "Then: python check_std_window.py --run <that PPO_N>")


def inspect_run(run_name: str):
    run_dir = HOVER_LOGS / run_name
    points = load_scalar(run_dir, "train/std")
    if not points:
        print(f"No train/std tag found in {run_dir}")
        return

    print(f"{'step':<12}{'std':<10}{'window'}")
    for step, val in points:
        if 200_000 <= step <= 400_000:
            window = "<-- CRASH SPIKE WINDOW (250k-350k)" if 250_000 <= step <= 350_000 else ""
            print(f"{step:<12}{val:<10.4f}{window}")

    in_window = [v for s, v in points if 250_000 <= s <= 350_000]
    before = [v for s, v in points if 200_000 <= s < 250_000]
    after = [v for s, v in points if 350_000 < s <= 400_000]

    def _avg(vals):
        return sum(vals) / len(vals) if vals else float("nan")

    print(f"\nmean std, 200k-250k (before spike): {_avg(before):.4f}")
    print(f"mean std, 250k-350k (crash window):  {_avg(in_window):.4f}")
    print(f"mean std, 350k-400k (after spike):   {_avg(after):.4f}")

    if in_window and before and after:
        if _avg(in_window) > _avg(before) * 1.15 and _avg(in_window) > _avg(after) * 1.15:
            print(
                "\n-> std IS elevated in the crash window relative to both neighbors. "
                "Consistent with the overcorrection hypothesis (theory-log.md 2026-08-16-0)."
            )
        else:
            print(
                "\n-> std is NOT clearly elevated in the crash window. The overcorrection "
                "hypothesis is NOT supported by this data -- the crash spike likely has a "
                "different mechanism (value-function transient, specific start-condition "
                "subset, etc). Update theory-log.md with a superseding entry, don't just "
                "delete the original -- see that file's append-only convention."
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=str, default=None, help="e.g. PPO_7 -- omit to list all runs first")
    args = parser.parse_args()
    if args.run:
        inspect_run(args.run)
    else:
        list_runs()
