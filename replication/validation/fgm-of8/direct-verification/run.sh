#!/usr/bin/env bash
set -euo pipefail
case_dir=${1:?case directory}
solver=${2:?absolute solver executable}
[[ -n ${SLURM_JOB_ID:-} ]] || { echo 'Run only inside an admitted Slurm allocation' >&2; exit 2; }
[[ -d "$case_dir/0" && -f "$case_dir/verification-input.json" && -x "$solver" ]] || exit 2
for path in "$case_dir"/[0-9]*; do
    [[ ${path##*/} == 0 ]] || { echo "Refusing existing time directory: $path" >&2; exit 2; }
done
[[ ! -e "$case_dir/constant/polyMesh" ]] || { echo 'Refusing previously meshed case' >&2; exit 2; }
blockMesh -case "$case_dir" > "$case_dir/blockMesh.log" 2>&1
"$solver" -case "$case_dir" > "$case_dir/solver.log" 2>&1
node "$(dirname "$0")/check.mjs" "$case_dir" "$case_dir/solver.log"
