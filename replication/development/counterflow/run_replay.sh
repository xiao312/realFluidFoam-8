#!/bin/bash
set -euo pipefail
TIMEFORMAT='real_seconds=%3R user_seconds=%3U system_seconds=%3S'
release=${1:?}; job=${2:?}; donor_id=${3:?}
[[ "$donor_id" =~ ^[0-9]+$ ]] || exit 2
source_job="/work/jobs/$donor_id"
module="$release/replication/development/counterflow"
python3 -B "$module/replay.py" plan "$source_job" "$job" > "$job/replay-plan.json"
python3 -B "$module/replay.py" apply "$source_job" "$job" > "$job/replay-prepare.json"
named="$source_job/openfoam-user/platforms/$WM_OPTIONS/bin/rfReactingFoam"
sha256sum "$named" > "$job/solver-product.sha256"
ldd "$named" > "$job/named-solver-ldd.txt"
! grep -q 'not found' "$job/named-solver-ldd.txt"
grep -F '/work/jobs/124657926/openfoam-user/platforms/' "$job/named-solver-ldd.txt"
case="$job/paper-cases/gri30"
python3 -B "$module/check_refined.py" "$case" initial > "$job/mapped-field-check.json"
{ time mpirun --mca btl self,vader,tcp -np 32 "$named" -case "$case" -parallel > "$job/solver.log"; } 2> "$job/solver-resources.txt"
grep -q '^End' "$job/solver.log"
python3 -B "$module/check_refined.py" "$case" endpoint > "$job/endpoint-check.json"
echo 'PASS: checkpointed 10-us fine-grid replay; no steady or grid-convergence acceptance' | tee "$job/result.txt"
