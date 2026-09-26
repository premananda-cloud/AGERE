"""
Parse hover_evaluate.py console logs from N seeded eval runs of the same
checkpoint and produce a paper-ready summary table (mean +/- std across runs)
plus the per-run breakdown for a reproducibility appendix.

Reads exactly the fields hover_evaluate.py's own summary block prints:
    Mean final pos error:  <float> m
    Crash rate:             <float>%
    Mean episode reward:   <float>

Usage:
    python aggregate_champion_eval.py paper_results/hover_champion_eval/run_seed*.log
"""
import re
import statistics
import sys
from pathlib import Path

PATTERNS = {
    "mean_pos_error_m": re.compile(r"Mean final pos error:\s*([\d.]+)\s*m"),
    "crash_rate_pct": re.compile(r"Crash rate:\s*([\d.]+)%"),
    "mean_reward": re.compile(r"Mean episode reward:\s*(-?[\d.]+)"),
}
SEED_PATTERN = re.compile(r"seed[=_]?(\d+)", re.IGNORECASE)


def parse_log(path: Path) -> dict:
    text = path.read_text()
    row = {"file": path.name}
    seed_match = SEED_PATTERN.search(path.name)
    row["seed"] = seed_match.group(1) if seed_match else "?"
    for key, pattern in PATTERNS.items():
        m = pattern.search(text)
        if not m:
            raise ValueError(f"{path}: could not find pattern for {key!r} -- "
                              f"was this a hover_evaluate.py log, and did the run finish?")
        row[key] = float(m.group(1))
    return row


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    paths = [Path(p) for p in sys.argv[1:]]
    rows = [parse_log(p) for p in paths]

    print(f"Parsed {len(rows)} run(s):\n")
    print(f"{'seed':<8}{'crash_rate_%':<15}{'mean_pos_error_m':<20}{'mean_reward'}")
    for r in rows:
        print(f"{r['seed']:<8}{r['crash_rate_pct']:<15.1f}{r['mean_pos_error_m']:<20.4f}{r['mean_reward']:.1f}")

    if len(rows) < 2:
        print("\nOnly one run -- no std to report. Add more seeded runs for a paper-grade "
              "mean +/- std figure.")
        return

    print("\n" + "=" * 60)
    print("Aggregate across runs (paste into paper table):\n")
    for key, label, fmt in [
        ("crash_rate_pct", "Crash rate (%)", ".2f"),
        ("mean_pos_error_m", "Mean position error (m)", ".4f"),
        ("mean_reward", "Mean episode reward", ".2f"),
    ]:
        vals = [r[key] for r in rows]
        mean = statistics.mean(vals)
        std = statistics.stdev(vals)  # sample std (n-1) -- standard for reporting across independent runs
        print(f"  {label:<28} {mean:{fmt}} +/- {std:{fmt}}  (n={len(rows)} runs, "
              f"seeds={[r['seed'] for r in rows]})")

    print("\nMarkdown table row:")
    crash = [r["crash_rate_pct"] for r in rows]
    pos = [r["mean_pos_error_m"] for r in rows]
    print(f"| hover_champion | {statistics.mean(crash):.2f} ± {statistics.stdev(crash):.2f} | "
          f"{statistics.mean(pos):.4f} ± {statistics.stdev(pos):.4f} | n={len(rows)} runs |")


if __name__ == "__main__":
    main()
