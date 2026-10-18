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
fixture="$job/inlet-probe-check"
python3 -B "$module/parallel_inlets.py" fixture-plan "$fixture" 4 --fixture-source "$case" > "$job/probe-check-plan.json"
python3 -B "$module/parallel_inlets.py" fixture-apply "$fixture" 4 --fixture-source "$case" > "$job/probe-check-prepare.json"
blockMesh -case "$fixture" > "$job/probe-check-mesh.log" 2>&1
rfPropertyProbe -case "$fixture" -initial > "$job/probe-check-serial.log" 2>&1
decomposePar -case "$fixture" > "$job/probe-check-decompose.log" 2>&1
mpirun --mca btl self,vader,tcp -np 4 rfPropertyProbe -case "$fixture" -initial -parallel > "$job/probe-check-parallel.log" 2>&1
python3 -B "$module/parallel_inlets.py" plan "$fixture" 4 --reference "$fixture/inlet-densities.csv" > "$job/probe-serial-parallel-check.json"
decomposePar -case "$case" > "$job/decompose-mesh.log" 2>&1
/usr/bin/time -v mpirun --mca btl self,vader,tcp -np 32 rfPropertyProbe -case "$case" -initial -parallel > "$job/inlet-probe.log" 2> "$job/inlet-probe-resources.txt"
python3 -B "$module/parallel_inlets.py" plan "$case" 32 --reference "$fixture/inlet-densities.csv" > "$job/parallel-inlets-plan.json"
python3 -B "$module/parallel_inlets.py" apply "$case" 32 --reference "$fixture/inlet-densities.csv" > "$job/parallel-inlets-check.json"
python3 -B "$release/replication/validation/flames/finalize_inlets.py" "$case" > "$job/inlet-settings.json"
mapFields "$job/donor" -case "$case" -parallelSource -sourceTime "$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["donor_time_s"])' "$job/refinement.json")" -mapMethod interpolate > "$job/mapFields.log" 2>&1
(cd "$case"; find 0 constant system -type f -print0 | sort -z | xargs -0 sha256sum) > "$job/initialized-inputs.sha256"
decomposePar -fields -case "$case" > "$job/decompose.log" 2>&1
python3 -B "$module/check_refined.py" "$case" initial > "$job/mapped-field-check.json"
/usr/bin/time -v mpirun --mca btl self,vader,tcp -np 32 "$named" -case "$case" -parallel > "$job/solver.log" 2> "$job/solver-resources.txt"
grep -q '^End' "$job/solver.log"
python3 -B "$module/check_refined.py" "$case" endpoint > "$job/endpoint-check.json"
echo "PASS: paper-resolution $key 10-us qualification; no steady or grid-convergence acceptance" | tee "$job/result.txt"
