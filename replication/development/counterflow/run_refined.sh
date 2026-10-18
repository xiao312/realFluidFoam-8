#!/bin/bash
# Bounded fine-grid flow qualification. Original coarse jobs remain read-only.
set -euo pipefail
release=${1:?}; job=${2:?}; key=${3:?}
module="$release/replication/development/counterflow"
python3 -B "$module/refine.py" plan "$key" "$job" > "$job/refinement-plan.json"
python3 -B "$module/refine.py" apply "$key" "$job" > "$job/refinement-prepare.log"
case="$job/paper-cases/gri30"
cp -a "$release/replication/development/solver" "$job/solver-source"
wmake "$job/solver-source" > "$job/solver-build.log" 2>&1
named="$FOAM_USER_APPBIN/rfReactingFoam"
sha256sum "$named" > "$job/solver-product.sha256"
ldd "$named" > "$job/named-solver-ldd.txt"
! grep -q 'not found' "$job/named-solver-ldd.txt"
grep -F '/work/jobs/124657926/openfoam-user/platforms/' "$job/named-solver-ldd.txt"
cp -a "$release/replication/validation/properties" "$job/property-probe"
wmake "$job/property-probe" > "$job/property-probe-build.log" 2>&1
blockMesh -case "$case" > "$job/blockMesh.log" 2>&1
checkMesh -case "$case" > "$job/checkMesh.log" 2>&1
grep -q 'Mesh OK' "$job/checkMesh.log"
rfPropertyProbe -case "$case" -initial > "$job/inlet-probe.log" 2>&1
python3 -B "$release/replication/validation/flames/finalize_inlets.py" "$case" > "$job/inlet-settings.json"
mapFields "$job/donor" -case "$case" -parallelSource -sourceTime "$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["donor_time_s"])' "$job/refinement.json")" -mapMethod interpolate > "$job/mapFields.log" 2>&1
(cd "$case"; find 0 constant system -type f -print0 | sort -z | xargs -0 sha256sum) > "$job/initialized-inputs.sha256"
decomposePar -case "$case" > "$job/decompose.log" 2>&1
python3 -B "$module/check_refined.py" "$case" initial > "$job/mapped-field-check.json"
/usr/bin/time -v mpirun --mca btl self,vader,tcp -np 32 "$named" -case "$case" -parallel > "$job/solver.log" 2> "$job/solver-resources.txt"
grep -q '^End' "$job/solver.log"
python3 -B "$module/check_refined.py" "$case" endpoint > "$job/endpoint-check.json"
echo "PASS: paper-resolution $key 10-us qualification; no steady or grid-convergence acceptance" | tee "$job/result.txt"
