#!/usr/bin/env bash
# Champion selection + packaging pipeline for the hover disturbance-robustness
# checkpoints. Run from the AGERE repo root (where `src/` lives).
#
# What this does, in order:
#   1. Sweeps each candidate training line's checkpoints (60 eps, cheap) to
#      find the best-looking checkpoint PER LINE. Doesn't trust "latest run"
#      or "final save" -- both have been wrong before in this project.
#   2. Thoroughly re-evaluates each line's sweep-winner (200 eps, tagged to
#      the registry) -- the sweep is a cheap filter, not the final number.
#   3. Leaderboards on `kick_crash_rate`, NOT plain `crash_rate` -- plain
#      crash_rate is logged on every hover eval ever run, including old
#      undisturbed Stage 2/3 baseline evals (~0% crash), which would
#      silently outrank every disturbance-trained checkpoint. kick_crash_rate
#      only exists on evals that were run with --stage (and kick fired), so
#      old baseline evals are automatically excluded from this ranking.
#   4. Runs the tilt-criterion diagnostic on the leaderboard winner, so you
#      know whether its remaining kick/torque crashes are real or an
#      artifact before freezing it.
#   5. Pauses for a manual confirm (prints the winner's hash/path first).
#   6. Promotes it to hover_champion.zip, describes it from the registry,
#      and compiles every log above into one markdown report.
#
# Usage:
#   ./select_and_package_champion.sh
#   ./select_and_package_champion.sh --yes        # skip the confirm prompt
#
# Edit CANDIDATE_LINES below to add/remove training lines to compare.

set -euo pipefail

# ---------------------------------------------------------------------------
# Config -- edit as needed
# ---------------------------------------------------------------------------
STAGE=disturbance_3x5
SWEEP_EPISODES=60
SWEEP_SEED=0
THOROUGH_EPISODES=200
THOROUGH_SEED=0
TILT_EPISODES=90

# Which training lines to compare. tiltfix (v1) is superseded by tiltfix2/3
# per training-log.md -- add it back here if you want it in the comparison
# anyway.
CANDIDATE_LINES=(
    "hover_stabilize_ppo_seed0_disturbance_3x5_tiltfix2"
    "hover_stabilize_ppo_seed0_disturbance_3x5_tiltfix3"
)

AUTO_YES=0
[[ "${1:-}" == "--yes" ]] && AUTO_YES=1

# ---------------------------------------------------------------------------
# Sanity check: must be run from repo root
# ---------------------------------------------------------------------------
if [[ ! -d "src" || ! -f "src/paths.py" ]]; then
    echo "ERROR: run this from the AGERE repo root (src/ not found in $(pwd))." >&2
    exit 1
fi

REPORT_DIR="reports/champion_selection_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$REPORT_DIR"
echo "Report directory: $REPORT_DIR"

declare -A BEST_STEP
declare -A BEST_SWEEP_CRASH

# ---------------------------------------------------------------------------
# Step 1: sweep each candidate line
# ---------------------------------------------------------------------------
echo
echo "== Step 1: sweeping candidate lines (${SWEEP_EPISODES} eps each, cheap filter only) =="
for prefix in "${CANDIDATE_LINES[@]}"; do
    log="$REPORT_DIR/sweep_${prefix}.log"
    echo "-- sweeping $prefix --"
    python -m src.training.evaluate.hover_checkpoint_sweep \
        --prefix "$prefix" --stage "$STAGE" \
        --episodes "$SWEEP_EPISODES" --seed "$SWEEP_SEED" | tee "$log"

    read -r step crash < <(python3 - "$log" <<'PY'
import re, sys
best_step, best_crash = None, None
pat = re.compile(r'^\s*(\d+)\s+steps\s+\|\s+crash\s+([\d.]+)%')
for line in open(sys.argv[1]):
    m = pat.match(line)
    if m:
        step, crash = int(m.group(1)), float(m.group(2))
        if best_crash is None or crash < best_crash:
            best_step, best_crash = step, crash
if best_step is None:
    print("NONE 0")
else:
    print(best_step, best_crash)
PY
)
    if [[ "$step" == "NONE" ]]; then
        echo "  WARNING: couldn't parse any checkpoint rows for $prefix -- skipping it."
        continue
    fi
    BEST_STEP[$prefix]=$step
    BEST_SWEEP_CRASH[$prefix]=$crash
    echo "  -> sweep-best for $prefix: ${step} steps (${crash}% crash @ ${SWEEP_EPISODES} eps -- not final)"
done

# ---------------------------------------------------------------------------
# Step 2: thorough eval of each line's sweep-winner (this is what gets
# logged to the registry and is what leaderboard/promote will actually use)
# ---------------------------------------------------------------------------
echo
echo "== Step 2: thorough eval (${THOROUGH_EPISODES} eps, tagged to registry) =="
for prefix in "${CANDIDATE_LINES[@]}"; do
    step="${BEST_STEP[$prefix]:-}"
    [[ -z "$step" ]] && continue
    ckpt="model/model_weights/checkpoints/${prefix}_${step}_steps.zip"
    if [[ ! -f "$ckpt" ]]; then
        echo "  WARNING: $ckpt not found on disk -- skipping."
        continue
    fi
    log="$REPORT_DIR/eval_${prefix}_${step}.log"
    echo "-- evaluating $ckpt --"
    python -m src.training.evaluate.hover_evaluate \
        --model "$ckpt" --stage "$STAGE" \
        --episodes "$THOROUGH_EPISODES" --seed "$THOROUGH_SEED" | tee "$log"
done

# ---------------------------------------------------------------------------
# Step 3: leaderboard on a disturbance-only metric (see header comment for
# why NOT plain crash_rate)
# ---------------------------------------------------------------------------
echo
echo "== Step 3: leaderboard (kick_crash_rate, minimize -- excludes old undisturbed baseline evals) =="
python -m src.weight_manager.checkpoint_manager leaderboard hover kick_crash_rate --minimize \
    | tee "$REPORT_DIR/leaderboard.log"

top_line=$(sed -n '2p' "$REPORT_DIR/leaderboard.log")
if [[ -z "$top_line" ]]; then
    echo "ERROR: leaderboard produced no rows -- nothing to promote. Check the eval logs above." >&2
    exit 1
fi
top_hash=$(awk '{print $2}' <<< "$top_line")
top_path=$(awk '{print $NF}' <<< "$top_line")
echo "Leaderboard winner: hash=$top_hash  path=$top_path"

# ---------------------------------------------------------------------------
# Step 4: tilt-criterion diagnostic on the winner -- know whether its
# remaining kick/torque crashes are real before freezing it
# ---------------------------------------------------------------------------
echo
echo "== Step 4: tilt-criterion diagnostic on the leaderboard winner =="
python -m src.training.evaluate.hover_tilt_diagnostic \
    --model "$top_path" --stage "$STAGE" \
    --episodes "$TILT_EPISODES" --seed "$THOROUGH_SEED" \
    | tee "$REPORT_DIR/tilt_diagnostic.log"

# ---------------------------------------------------------------------------
# Step 5: confirm before promoting (promote overwrites hover_champion.zip)
# ---------------------------------------------------------------------------
echo
echo "About to promote:"
echo "  hash: $top_hash"
echo "  path: $top_path"
echo "This OVERWRITES model/model_weights/hover_champion.zip."
if [[ "$AUTO_YES" -eq 0 ]]; then
    read -r -p "Proceed? [y/N] " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo "Aborted before promote. Everything up to here is saved in $REPORT_DIR."
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
# Step 6: promote, describe, compile one report
# ---------------------------------------------------------------------------
echo
echo "== Step 5: promoting champion =="
python -m src.weight_manager.checkpoint_manager promote hover kick_crash_rate --minimize \
    | tee "$REPORT_DIR/promote.log"

echo
echo "== Step 6: verifying promoted champion =="
python -m src.weight_manager.model_registry describe model/model_weights/hover_champion.zip \
    | tee "$REPORT_DIR/champion_describe.log"

echo
echo "== Compiling single report =="
{
    echo "# Hover Champion Selection Report"
    echo
    echo "Generated: $(date)"
    echo
    echo "Candidate lines compared: ${CANDIDATE_LINES[*]}"
    echo
    echo "## 1. Checkpoint sweeps (${SWEEP_EPISODES} episodes each -- filter only)"
    for prefix in "${CANDIDATE_LINES[@]}"; do
        f="$REPORT_DIR/sweep_${prefix}.log"
        [[ -f "$f" ]] || continue
        echo
        echo "### $prefix"
        echo '```'
        cat "$f"
        echo '```'
    done
    echo
    echo "## 2. Thorough evaluations (${THOROUGH_EPISODES} episodes each, seed=${THOROUGH_SEED})"
    for prefix in "${CANDIDATE_LINES[@]}"; do
        step="${BEST_STEP[$prefix]:-}"
        [[ -z "$step" ]] && continue
        f="$REPORT_DIR/eval_${prefix}_${step}.log"
        [[ -f "$f" ]] || continue
        echo
        echo "### $prefix @ ${step} steps"
        echo '```'
        cat "$f"
        echo '```'
    done
    echo
    echo "## 3. Leaderboard (kick_crash_rate, minimize)"
    echo '```'
    cat "$REPORT_DIR/leaderboard.log"
    echo '```'
    echo
    echo "## 4. Tilt-criterion diagnostic on the winner ($top_path)"
    echo '```'
    cat "$REPORT_DIR/tilt_diagnostic.log"
    echo '```'
    echo
    echo "## 5. Promotion"
    echo '```'
    cat "$REPORT_DIR/promote.log"
    echo '```'
    echo
    echo "## 6. Champion registry record"
    echo '```'
    cat "$REPORT_DIR/champion_describe.log"
    echo '```'
} > "$REPORT_DIR/champion_selection_report.md"

echo
echo "Done."
echo "Champion: model/model_weights/hover_champion.zip"
echo "Full report: $REPORT_DIR/champion_selection_report.md"
