#!/bin/sh
# Serial property sweep for the O2 PR / PR-VTA verification (Fig. 1 of
# Mueller & Pfitzner 2015). Intended for the scheduler, one rank.
#
# Usage: job.sh <case-dir> <run-dir>
#   case-dir  replication/development/oxygen-properties inside the checkout
#   run-dir   output directory (outside the repository; raw data is not committed)
set -eu
CASE_DIR=${1:?case directory}
RUN_DIR=${2:?run directory}

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1

cd "$CASE_DIR"
echo "host: $(hostname)"
echo "cwd:  $(pwd)"
echo "date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
python3 --version
mkdir -p "$RUN_DIR"
exec python3 run_properties.py --out "$RUN_DIR"
