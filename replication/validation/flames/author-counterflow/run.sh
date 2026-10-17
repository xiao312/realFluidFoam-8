#!/bin/bash
# Called after validation/inside.sh verifies the isolated OF8 build.
set -Eeuo pipefail
module=${1:?module}; job=${2:?job}; mode=${3:?smoke or full}
[[ "$mode" == smoke || "$mode" == full ]] || exit 2
cases="$job/author-cases"
python3 -B "$module/prepare.py" plan "$cases" "$mode" > "$job/author-plan.json"
python3 -B "$module/prepare.py" apply "$cases" "$mode" > "$job/author-applied.json"
for phase in one-step gri30; do
    case_dir="$cases/$phase"
    blockMesh -case "$case_dir" > "$job/$phase-blockMesh.log" 2>&1
    checkMesh -case "$case_dir" > "$job/$phase-checkMesh.log" 2>&1
    grep -q 'Mesh OK' "$job/$phase-checkMesh.log"
    if [[ "$phase" == gri30 ]]; then
        python3 -B "$module/transfer.py" plan "$cases/one-step" "$case_dir" > "$job/transfer-plan.json"
        python3 -B "$module/transfer.py" apply "$cases/one-step" "$case_dir" > "$job/transfer-applied.json"
    fi
    decomposePar -case "$case_dir" > "$job/$phase-decompose.log" 2>&1
    mpirun --mca btl self,vader,tcp -np 8 realFluidReactingFoam -case "$case_dir" -parallel > "$job/$phase-solver.log" 2>&1
    grep -q '^End' "$job/$phase-solver.log"
    reconstructPar -case "$case_dir" -latestTime > "$job/$phase-reconstruct.log" 2>&1
    if [[ "$mode" == full ]]; then
        reconstructPar -case "$case_dir" -fields '(T p rho U CH4 O2 CO2 H2O)' >> "$job/$phase-reconstruct.log" 2>&1
    fi
    python3 -B "$module/transfer.py" check "$case_dir" > "$job/$phase-field-check.json"
done
echo "PASS: author counterflow $mode, both mechanisms and field transfer; steady/grid convergence not established" | tee "$job/result.txt"
