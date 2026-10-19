#!/bin/bash
set -Eeuo pipefail
release=${1:?}; job=${2:?}; key=${3:?}
module="$release/replication/development/premixed-sensitivity"
python3 -B "$module/prepare.py" plan "$job" "$key" > "$job/copy-plan.json"
python3 -B "$module/prepare.py" apply "$job" "$key" > "$job/copy.log"
solver="/work/jobs/124870644/openfoam-user/platforms/$WM_OPTIONS/bin/rfSpatialReactingFoam"
printf '%s  %s\n' e3ef56491e44c2dfdd79826805f992ed8220901643ac14554c38ca8e81e6b385 "$solver" | sha256sum -c - > "$job/binary-verified.txt"
sha256sum "$solver" > "$job/solver-product.sha256"
ldd "$solver" > "$job/sensitivity-ldd.txt"
! grep -q 'not found' "$job/sensitivity-ldd.txt"
mpirun --mca btl self,vader,tcp -np 8 "$solver" -case "$job/case" -parallel > "$job/solver.log" 2>&1
grep -q '^End' "$job/solver.log"
python3 -B "$module/check.py" "$job" > "$job/check.log"
echo 'PASS: fixed-step segment completed; scientific convergence remains unqualified' > "$job/result.txt"
