#!/bin/bash
set -Eeuo pipefail
release=${1:?}; job=${2:?}; key=${3:?}; mode=${4:?}
module="$release/replication/development/ideal-baseline"
solver="/work/jobs/124870644/openfoam-user/platforms/$WM_OPTIONS/bin/rfSpatialReactingFoam"
printf '%s  %s\n' e3ef56491e44c2dfdd79826805f992ed8220901643ac14554c38ca8e81e6b385 "$solver" | sha256sum -c - > "$job/binary-verified.txt"
sha256sum "$solver" > "$job/solver-product.sha256"
ldd "$solver" > "$job/ideal-ldd.txt"
! grep -q 'not found' "$job/ideal-ldd.txt"
cp -a "$release/replication/validation/properties" "$job/property-probe"
wmake "$job/property-probe" > "$job/property-build.log" 2>&1
python3 -B "$module/prepare.py" plan "$key" "$job/case" "$mode" > "$job/case-plan.json"
python3 -B "$module/prepare.py" apply "$key" "$job/case" "$mode" > "$job/prepare.log"
blockMesh -case "$job/case" > "$job/blockMesh.log" 2>&1
checkMesh -case "$job/case" > "$job/checkMesh.log" 2>&1
grep -q 'Mesh OK' "$job/checkMesh.log"
rfPropertyProbe -case "$job/case" -initial > "$job/initial-probe.log" 2>&1
python3 -B "$release/replication/development/premixed-paper/check.py" finalize "$job/case" > "$job/finalize.log"
decomposePar -case "$job/case" > "$job/decompose.log" 2>&1
if [[ "$mode" == smoke ]]; then
    cp -a "$job/case" "$job/diagnostics-off"
    sed -i 's/enabled true;/enabled false;/' "$job/diagnostics-off/constant/flameSpeedProperties"
fi
mpirun --mca btl self,vader,tcp -np 8 "$solver" -case "$job/case" -parallel > "$job/solver.log" 2>&1
grep -q '^End' "$job/solver.log"
if [[ "$mode" == smoke ]]; then
    mpirun --mca btl self,vader,tcp -np 8 "$solver" -case "$job/diagnostics-off" -parallel > "$job/off-solver.log" 2>&1
    grep -q '^End' "$job/off-solver.log"
fi
python3 -B "$module/check.py" "$job" "$mode" > "$job/check.log"
echo "PASS: ideal baseline $key $mode; scientific convergence unqualified" > "$job/result.txt"
