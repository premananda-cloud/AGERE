# results/

Raw, generated data — never hand-edited. Every run of
`run_report_pipeline.py` (or any future data-generation script) writes
into its own timestamped/labeled subfolder here and never overwrites a
previous one, so old sweeps stay around for comparison.

```
results/
    <label>/                            e.g. tiltfix2_champion_20260903T...
        manifest.json                   what produced this: model path, git
                                         commit, args, timestamp — the
                                         provenance record for every other
                                         file in this folder
        raw_episodes.csv                one row per episode, scalar fields
                                         only (crash, recovered, magnitude,
                                         peak tilt, etc.) — open in
                                         pandas/Excel directly
        raw_episodes_full.jsonl         same episodes, but with full
                                         per-step tilt/position-error
                                         traces included — for digging
                                         into one specific episode later
        summary_by_type_level.csv       one row per (disturbance type,
                                         level) bucket — the table the
                                         report's figures/numbers come from
        figures/
            crash_rate_by_level.png
            peak_tilt_vs_magnitude.png
            recovery_time_vs_magnitude.png
            wind_steady_state_error_vs_magnitude.png
```

**Convention:** if you add a new kind of sweep (e.g. comparing two
checkpoints, or a different task), give it its own script and its own
`results/<something>/` subfolder with the same manifest-first pattern —
don't reuse a label across genuinely different runs.

**Not committed to git by default** if these folders get large — add
`results/*/raw_episodes_full.jsonl` to `.gitignore` if repo size becomes
an issue; keep `manifest.json` and `summary_by_type_level.csv` tracked
either way, since those are small and are what the report actually cites.
