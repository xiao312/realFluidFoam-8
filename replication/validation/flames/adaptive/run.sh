#!/bin/bash
set -Eeuo pipefail
release=${1:?}; job=${2:?}; key=${3:?}; mode=${4:?}
module="$release/replication/validation/flames/adaptive"
python3 -B "$module/prepare.py" plan /work "$key" "$job/case" "$mode" > "$job/adaptive-plan.json"
python3 -B "$module/prepare.py" apply /work "$key" "$job/case" "$mode" > "$job/adaptive-applied.json"
ranks=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["config"]["ranks"])' "$job/case/restart.json")
mpirun --mca btl self,vader,tcp -np "$ranks" realFluidReactingFoam -case "$job/case" -parallel > "$job/solver.log" 2>&1
grep -q '^End' "$job/solver.log"
grep -q '^deltaT = ' "$job/solver.log"
python3 -B "$module/check.py" "$job/case" > "$job/endpoint-check.json"
echo "PASS: adaptive $key $mode; finite normalized endpoint, convergence unqualified" > "$job/result.txt"
