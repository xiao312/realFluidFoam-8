#!/bin/bash
set -o pipefail
release=${1:?}; library=${2:?}; profile=${3:?}; results=${4:?}; velocity=${5:?}
family=${6:-native}; bridge=${7:-none}
step_ns=${8:-50}
[[ $step_ns == 5 || $step_ns == 50 ]] || exit 2
[[ ( $family == native && $bridge == none ) || ( $family == cantera && $bridge =~ ^[0-9]+$ ) ]] || exit 2
# OF8 bashrc treats existing positional file arguments as extra shell settings.
# Keep data paths in named variables and never expose them to that mechanism.
set --
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
instrument=$thermo_module/instrument.py
solver=$FOAM_USER_APPBIN/rfThermoReactingFoam
if [[ $family == cantera ]]; then
 instrument=$release/replication/development/cantera-cfd/instrument.py
 solver=$FOAM_USER_APPBIN/rfCanteraBridgeFoam
 sdk=/work/jobs/124917358/sdk
 export LD_LIBRARY_PATH="$sdk/lib:$LD_LIBRARY_PATH" CANTERA_DATA=$sdk/share/cantera/data
fi
python3 -B "$instrument" plan "$release" "$job/solver-source" > "$job/solver-plan.txt"
python3 -B "$instrument" apply "$release" "$job/solver-source" > "$job/instrument.log"
wmake "$job/solver-source" > "$job/build.log" 2>&1
sha256sum "$solver" > "$job/solver-product.sha256"
ldd "$solver" > "$job/solver-ldd.txt"
! grep -q 'not found' "$job/solver-ldd.txt"
grep -F "$platform/lib/libspecie.so" "$job/solver-ldd.txt"
cp -a "$release/replication/validation/properties" "$job/property-probe"
wmake "$job/property-probe" > "$job/probe-build.log" 2>&1
probe=$FOAM_USER_APPBIN/rfPropertyProbe
for action in plan apply; do
 python3 -B "$module/prepare.py" "$action" phi110 "$profile" "$results" "$job/case" \
  --velocity "$velocity" --end-us 20 --max-delta-t-ns "$step_ns" > "$job/case-$action.log"
done
python3 -B "$thermo_module/case.py" configure "$job" "$library" 8 full
if [[ $family == cantera ]]; then
 python3 -B "$release/replication/development/cantera-cfd/case.py" configure "$job" "$bridge" full \
  --chemistry-mode native --execution-profile uniform8 --numerical-profile strict12
fi
python3 - "$job" "$family" "$bridge" "$library" "$step_ns" <<'PY'
import json,sys
from pathlib import Path
job=Path(sys.argv[1]);family,bridge,library,step_ns=sys.argv[2:]
record=dict(solver_family=family,bridge_job=None if bridge=='none' else bridge,
    library_job=library,chemistry='native',transport=family,max_delta_t_s=int(step_ns)*1e-9,
    initialization='generated_original_zero')
(job/'wave-run-inputs.json').write_text(json.dumps(record,indent=2)+'\n')
path=job/'thermo-inputs.json';data=json.loads(path.read_text())
data.update(transport=family,solver_family=family,bridge_job=record['bridge_job'])
path.write_text(json.dumps(data,indent=2)+'\n')
PY
blockMesh -case "$job/case" > "$job/blockMesh.log" 2>&1
checkMesh -case "$job/case" > "$job/checkMesh.log" 2>&1
grep -q 'Mesh OK' "$job/checkMesh.log"
"$probe" -case "$job/case" -initial > "$job/initial-probe.log" 2>&1
for action in plan apply; do
 python3 -B "$module/increment_case.py" "$action" "$job/case" "$job/increment-probe-case" > "$job/increment-case-$action.json"
done
blockMesh -case "$job/increment-probe-case" > "$job/increment-blockMesh.log" 2>&1
"$probe" -case "$job/increment-probe-case" -small-increments > "$job/ideal-increments.log" 2>&1
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
