#!/usr/bin/env bash
# Tomorrow's demo command. Run from the AGERE repo root.
#
# Uses hover_champion.zip -- the evaluated, packaged, known-quantity model,
# not the angvel experiment. Defaults matched to the last run that showed
# clean numbers (17.4-19.8 deg max tilt, no crash, 0.51 m/s max speed).
#
# Usage tonight (test run, do this at least once before showing anyone):
#   ./run_governor_demo.sh
#
# Tomorrow, live:
#   ./run_governor_demo.sh
#
# If you want a recorded backup video in case anything goes wrong live,
# run this once tonight too:
#   ./run_governor_demo.sh --record

set -euo pipefail

python -m src.training.demo.sim_transfer_test_demo \
    --model model/model_weights/hover_champion.zip \
    --hover-duration 6 \
    --settle-duration 2 \
    "$@"
