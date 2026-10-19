#!/bin/bash
set -Eeuo pipefail
release=${1:?}; job=${2:?}; key=${3:?}; mode=${4:?}
module="$release/replication/development/premixed-paper"
g++ -std=c++11 -O2 "$module/test_sampling.C" -o "$job/test-sampling"
"$job/test-sampling" > "$job/sampling-test.txt"
python3 -B "$module/instrument.py" plan "$release/replication/development/solver" "$job/solver-source" > "$job/solver-plan.json"
python3 -B "$module/instrument.py" apply "$release/replication/development/solver" "$job/solver-source" > "$job/instrument.log"
wmake "$job/solver-source" > "$job/solver-build.log" 2>&1
sha256sum "$FOAM_USER_APPBIN/rfPaperReactingFoam" > "$job/solver-product.sha256"
ldd "$FOAM_USER_APPBIN/rfPaperReactingFoam" > "$job/solver-ldd.txt"
! grep -q 'not found' "$job/solver-ldd.txt"
grep -F '/work/jobs/124657926/openfoam-user/platforms/' "$job/solver-ldd.txt"
cp -a "$release/replication/validation/properties" "$job/property-probe"
wmake "$job/property-probe" > "$job/property-build.log" 2>&1
python3 -B "$module/prepare.py" plan "$key" "$job/case" "$mode" > "$job/case-plan.json"
python3 -B "$module/prepare.py" apply "$key" "$job/case" "$mode" > "$job/prepare.log"
blockMesh -case "$job/case" > "$job/blockMesh.log" 2>&1
checkMesh -case "$job/case" > "$job/checkMesh.log" 2>&1
grep -q 'Mesh OK' "$job/checkMesh.log"
rfPropertyProbe -case "$job/case" -initial > "$job/initial-probe.log" 2>&1
python3 -B "$module/check.py" finalize "$job/case" > "$job/finalize.log"
decomposePar -case "$job/case" > "$job/decompose.log" 2>&1
if [[ "$mode" == smoke ]]; then
    cp -a "$job/case" "$job/diagnostics-off"
    sed -i 's/enabled true;/enabled false;/' "$job/diagnostics-off/constant/flameSpeedProperties"
fi
mpirun --mca btl self,vader,tcp -np 8 rfPaperReactingFoam -case "$job/case" -parallel > "$job/solver.log" 2>&1
grep -q '^End' "$job/solver.log"
if [[ "$mode" == smoke ]]; then
    mpirun --mca btl self,vader,tcp -np 8 rfPaperReactingFoam -case "$job/diagnostics-off" -parallel > "$job/off-solver.log" 2>&1
    grep -q '^End' "$job/off-solver.log"
fi
python3 -B "$module/check.py" check "$job" "$mode" > "$job/endpoint.log"
echo "PASS: paper premixed $key $mode; convergence remains unqualified" > "$job/result.txt"
