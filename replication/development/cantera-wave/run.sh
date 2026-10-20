#!/bin/bash
set -o pipefail
release=${1:?}; library=${2:?}; profile=${3:?}; results=${4:?}; velocity=${5:?}
. /opt/openfoam8/etc/bashrc
set -euo pipefail
job=/work/jobs/$RF_JOB_ID
module=$release/replication/development/cantera-wave
thermo_module=$release/replication/development/temperature-inversion
platform=/work/jobs/$library/openfoam-user/platforms/$WM_OPTIONS
export LIB_rfFoam8_SRC=/work/builds/$library/src
export FOAM_USER_LIBBIN=$platform/lib
export LD_LIBRARY_PATH="$FOAM_USER_LIBBIN:$LD_LIBRARY_PATH"
export WM_PROJECT_USER_DIR=$job/openfoam-user
export FOAM_USER_APPBIN=$WM_PROJECT_USER_DIR/platforms/$WM_OPTIONS/bin
export FOAM_JOB_DIR=$job/jobControl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
mkdir -p "$FOAM_USER_APPBIN" "$FOAM_JOB_DIR"
sha256sum -c "/work/jobs/$library/products.sha256" > "$job/library-verified.txt"
python3 -B "$thermo_module/instrument.py" plan "$release" "$job/solver-source" > "$job/solver-plan.txt"
python3 -B "$thermo_module/instrument.py" apply "$release" "$job/solver-source" > "$job/instrument.log"
wmake "$job/solver-source" > "$job/build.log" 2>&1
solver=$FOAM_USER_APPBIN/rfThermoReactingFoam
sha256sum "$solver" > "$job/solver-product.sha256"
ldd "$solver" > "$job/solver-ldd.txt"
! grep -q 'not found' "$job/solver-ldd.txt"
grep -F "$platform/lib/libspecie.so" "$job/solver-ldd.txt"
cp -a "$release/replication/validation/properties" "$job/property-probe"
wmake "$job/property-probe" > "$job/probe-build.log" 2>&1
probe=$FOAM_USER_APPBIN/rfPropertyProbe
for action in plan apply; do
 python3 -B "$module/prepare.py" "$action" phi110 "$profile" "$results" "$job/case" \
  --velocity "$velocity" --end-us 20 > "$job/case-$action.log"
done
python3 -B "$thermo_module/case.py" configure "$job" "$library" 8 full
blockMesh -case "$job/case" > "$job/blockMesh.log" 2>&1
checkMesh -case "$job/case" > "$job/checkMesh.log" 2>&1
grep -q 'Mesh OK' "$job/checkMesh.log"
"$probe" -case "$job/case" -initial > "$job/initial-probe.log" 2>&1
"$probe" -case "$job/case" -small-increments > "$job/ideal-increments.log" 2>&1
grep -q 'Small-increment inversion failures: 0/144' "$job/ideal-increments.log"
python3 -B "$release/replication/development/premixed-paper/check.py" finalize "$job/case" > "$job/finalize.log"
decomposePar -case "$job/case" > "$job/decompose.log" 2>&1
python3 -B "$module/prepare.py" verify "$job/case" > "$job/wave-verified.json"
python3 -B "$release/replication/development/fresh-start/prepare.py" verify energy "$job/case" > "$job/initial-state-verified.json"
python3 - "$job" <<'PY'
import json,os,sys
from pathlib import Path
cpus=sorted(os.sched_getaffinity(0));assert len(cpus)==8
(Path(sys.argv[1])/'allocation-cpus.json').write_text(json.dumps(cpus)+'\n')
PY
mpirun --bind-to none --mca btl self,vader,tcp -np 8 python3 "$thermo_module/rank.py" \
 "$job" "$solver" -case "$job/case" -parallel > "$job/case.log" 2>&1
grep -q '^End' "$job/case.log"
python3 -B "$thermo_module/case.py" check "$job" "$library" 8 full > "$job/endpoint-check.json"
echo 'PASS: original-zero reference-wave endpoint and finite fields; steady flame speed unqualified' > "$job/result.txt"
