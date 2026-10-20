#!/bin/bash
set -o pipefail
release=${1:?}; library=${2:?}; ranks=${3:?}; key=${4:?}; mode=${5:?}; build=${6:?}
. /opt/openfoam8/etc/bashrc
set -euo pipefail
job=/work/jobs/$RF_JOB_ID
module=$release/replication/development/temperature-inversion
platform=/work/jobs/$library/openfoam-user/platforms/$WM_OPTIONS
export LIB_rfFoam8_SRC=/work/builds/$library/src
export FOAM_USER_LIBBIN=$platform/lib
export LD_LIBRARY_PATH="$FOAM_USER_LIBBIN:$LD_LIBRARY_PATH"
export WM_PROJECT_USER_DIR=$job/openfoam-user
export FOAM_USER_APPBIN=$WM_PROJECT_USER_DIR/platforms/$WM_OPTIONS/bin
export FOAM_JOB_DIR=$job/jobControl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
mkdir -p "$FOAM_USER_APPBIN" "$FOAM_JOB_DIR"
sha256sum -c "/work/jobs/$library/products.sha256" > "$job/library-verified.txt"
if [[ $mode == build ]]; then
 python3 -B "$module/instrument.py" plan "$release" "$job/solver-source" > "$job/solver-plan.txt"
 python3 -B "$module/instrument.py" apply "$release" "$job/solver-source" > "$job/instrument.log"
 wmake "$job/solver-source" > "$job/build.log" 2>&1
 solver=$FOAM_USER_APPBIN/rfThermoReactingFoam
 cp -a "$release/replication/validation/properties" "$job/property-probe"
 wmake "$job/property-probe" > "$job/probe-build.log" 2>&1
 probe=$FOAM_USER_APPBIN/rfPropertyProbe
 sha256sum "$probe" > "$job/probe-product.sha256"
else
 solver=/work/jobs/$build/openfoam-user/platforms/$WM_OPTIONS/bin/rfThermoReactingFoam
 probe=/work/jobs/$build/openfoam-user/platforms/$WM_OPTIONS/bin/rfPropertyProbe
 sha256sum -c "/work/jobs/$build/solver-product.sha256" > "$job/solver-verified.txt"
 sha256sum -c "/work/jobs/$build/probe-product.sha256" > "$job/probe-verified.txt"
fi
sha256sum "$solver" > "$job/solver-product.sha256"
ldd "$solver" > "$job/solver-ldd.txt"
! grep -q 'not found' "$job/solver-ldd.txt"
grep -F "$platform/lib/libspecie.so" "$job/solver-ldd.txt"
fresh=$release/replication/development/fresh-start
python3 -B "$fresh/prepare.py" plan energy "$key" "$job/case" --end-us 300 > "$job/case-plan.json"
python3 -B "$fresh/prepare.py" apply energy "$key" "$job/case" --end-us 300 > "$job/prepare.log"
python3 -B "$module/case.py" configure "$job" "$library" "$ranks" "$mode"
blockMesh -case "$job/case" > "$job/blockMesh.log" 2>&1
checkMesh -case "$job/case" > "$job/checkMesh.log" 2>&1
grep -q 'Mesh OK' "$job/checkMesh.log"
"$probe" -case "$job/case" -initial > "$job/initial-probe.log" 2>&1
if [[ $ranks == 32 ]]; then
 for action in plan apply; do
  python3 -B "$release/replication/development/cantera-cfd/partition.py" "$action" "$job/case" bands32 > "$job/partition-$action.json"
 done
fi
python3 -B "$release/replication/development/premixed-paper/check.py" finalize "$job/case" > "$job/finalize.log"
decomposePar -case "$job/case" > "$job/decompose.log" 2>&1
python3 -B "$fresh/prepare.py" verify energy "$job/case" > "$job/initial-state-verified.json"
python3 - "$job" "$ranks" <<'PY'
import json,os,sys
from pathlib import Path
cpus=sorted(os.sched_getaffinity(0))
assert len(cpus)==int(sys.argv[2]), 'Batch CPU affinity does not match the requested rank count'
(Path(sys.argv[1])/'allocation-cpus.json').write_text(json.dumps(cpus)+'\n')
PY
mpirun --bind-to none --mca btl self,vader,tcp -np "$ranks" python3 "$module/rank.py" "$job" "$solver" -case "$job/case" -parallel > "$job/case.log" 2>&1
grep -q '^End' "$job/case.log"
python3 -B "$module/case.py" check "$job" "$library" "$ranks" "$mode" > "$job/endpoint-check.json"
echo 'PASS: original-zero endpoint and finite fields; steady flame speed unqualified' > "$job/result.txt"
