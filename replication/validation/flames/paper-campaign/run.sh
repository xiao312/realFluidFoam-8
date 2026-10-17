#!/bin/bash
set -Eeuo pipefail
module=${1:?module}; job=${2:?job}; key=${3:?key}; mode=${4:?mode}
flames=$(dirname "$module")
cases="$job/paper-cases"
python3 -B "$module/prepare.py" plan "$key" "$cases" "$mode" > "$job/paper-plan.json"
python3 -B "$module/prepare.py" apply "$key" "$cases" "$mode" > "$job/paper-applied.log"
family=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["configuration"]["family"])' "$cases/paper-case.json")
if [[ "$family" == counterflow ]]; then phases=(one-step gri30); ranks=8
else phases=(premixed); ranks=4; fi
for phase in "${phases[@]}"; do
    case_dir="$cases/$phase"
    blockMesh -case "$case_dir" > "$job/$phase-blockMesh.log" 2>&1
    checkMesh -case "$case_dir" > "$job/$phase-checkMesh.log" 2>&1
    grep -q 'Mesh OK' "$job/$phase-checkMesh.log"
    rfPropertyProbe -case "$case_dir" -initial > "$job/$phase-inlet-probe.log" 2>&1
    if [[ "$phase" == premixed ]]; then
        python3 -B "$flames/finalize_premixed.py" "$case_dir" > "$job/$phase-inlets.json"
        setFields -case "$case_dir" > "$job/setFields.log" 2>&1
    else
        python3 -B "$flames/finalize_inlets.py" "$case_dir" > "$job/$phase-inlets.json"
        if [[ "$phase" == gri30 ]]; then
            python3 -B "$flames/author-counterflow/transfer.py" plan "$cases/one-step" "$case_dir" > "$job/transfer-plan.json"
            python3 -B "$flames/author-counterflow/transfer.py" apply "$cases/one-step" "$case_dir" > "$job/transfer-applied.json"
        fi
    fi
    # Hash the actual pre-decomposition inputs after runtime finalization/transfer.
    (cd "$case_dir"; find 0 constant system -type f -print0 | sort -z | xargs -0 sha256sum) > "$job/$phase-initialized-inputs.sha256"
    decomposePar -case "$case_dir" > "$job/$phase-decompose.log" 2>&1
    mpirun --mca btl self,vader,tcp -np "$ranks" realFluidReactingFoam -case "$case_dir" -parallel > "$job/$phase-solver.log" 2>&1
    grep -q '^End' "$job/$phase-solver.log"
    reconstructPar -case "$case_dir" -latestTime > "$job/$phase-reconstruct.log" 2>&1
    if [[ "$phase" == premixed ]]; then
        python3 -B "$flames/summarize.py" "$case_dir" > "$job/$phase-field-check.json"
    else
        python3 -B "$flames/author-counterflow/transfer.py" check "$case_dir" > "$job/$phase-field-check.json"
    fi
done
echo "PASS: paper case $key $mode; finite endpoint only, convergence/comparison pending" | tee "$job/result.txt"
