#!/bin/bash
# Compile the named baseline and compare it with the qualified original solver.
set -euo pipefail
release=${1:?}; job=${2:?}; key=${3:?}
module="$release/replication/development/premixed-inlet"
cp -a "$release/replication/development/solver" "$job/solver-source"
wmake "$job/solver-source" > "$job/solver-build.log" 2>&1
named="$FOAM_USER_APPBIN/rfReactingFoam"
sha256sum "$named" > "$job/solver-product.sha256"
ldd "$named" > "$job/solver-ldd.txt"
! grep -q 'not found' "$job/solver-ldd.txt"
grep -F '/work/jobs/124657926/openfoam-user/platforms/' "$job/solver-ldd.txt"
cp -a "$release/replication/validation/properties" "$job/property-probe"
wmake "$job/property-probe" > "$job/property-probe-build.log" 2>&1
case="$job/case"
python3 -B "$module/prepare.py" plan "$key" "$case" smoke > "$job/case-plan.json"
python3 -B "$module/prepare.py" apply "$key" "$case" smoke > "$job/case-apply.log"
blockMesh -case "$case" > "$job/blockMesh.log" 2>&1
checkMesh -case "$case" > "$job/checkMesh.log" 2>&1
grep -q 'Mesh OK' "$job/checkMesh.log"
"$FOAM_USER_APPBIN/rfPropertyProbe" -case "$case" -initial > "$job/initial-probe.log" 2>&1
python3 -B "$module/runtime.py" finalize "$case" > "$job/runtime-state.json"
decomposePar -case "$case" > "$job/decompose.log" 2>&1
cp -a "$case" "$job/upstream-case"
mpirun --mca btl self,vader,tcp -np 4 "$named" -case "$case" -parallel > "$job/solver.log" 2>&1
python3 -B "$module/runtime.py" check "$case" > "$job/endpoint-check.json"
mpirun --mca btl self,vader,tcp -np 4 realFluidReactingFoam -case "$job/upstream-case" -parallel > "$job/upstream-solver.log" 2>&1
python3 -B "$module/runtime.py" check "$job/upstream-case" > "$job/upstream-endpoint-check.json"
python3 -B "$module/compare.py" "$case" "$job/upstream-case" > "$job/baseline-comparison.json"
echo "PASS: inlet $key startup; renamed solver matches upstream fields; scientific acceptance pending" | tee "$job/result.txt"
