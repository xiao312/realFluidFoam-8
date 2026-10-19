#!/bin/bash
set -o pipefail
release=${1:?}; bridge_job=${2:?}; key=${3:?}; mode=${4:?}; build_job=${5:?}
chemistry=${6:-native}
execution=${7:-uniform8}
numerics=${8:-standard}
ranks=8; [[ $execution == bands32 ]] && ranks=32
. /opt/openfoam8/etc/bashrc
set -euo pipefail
job=/work/jobs/$RF_JOB_ID
module=$release/replication/development/cantera-cfd
sdk=/work/jobs/124917358/sdk
export LIB_rfFoam8_SRC=/work/builds/124657926/src
export FOAM_USER_LIBBIN=/work/jobs/124657926/openfoam-user/platforms/$WM_OPTIONS/lib
export WM_PROJECT_USER_DIR=$job/openfoam-user
export FOAM_USER_APPBIN=$WM_PROJECT_USER_DIR/platforms/$WM_OPTIONS/bin
export FOAM_JOB_DIR=$job/jobControl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export LD_LIBRARY_PATH="$sdk/lib:$FOAM_USER_LIBBIN:$LD_LIBRARY_PATH"
export CANTERA_DATA=$sdk/share/cantera/data
mkdir -p "$FOAM_USER_APPBIN" "$FOAM_JOB_DIR"
if [[ $mode == build ]]; then
 python3 -B "$module/instrument.py" plan "$release" "$job/solver-source" > "$job/solver-plan.txt"
 python3 -B "$module/instrument.py" apply "$release" "$job/solver-source" > "$job/instrument.log"
 wmake "$job/solver-source" > "$job/build.log" 2>&1
 solver=$FOAM_USER_APPBIN/rfCanteraBridgeFoam
else
 test -f "/work/jobs/$build_job/qualification-passed.txt"
 solver=/work/jobs/$build_job/openfoam-user/platforms/$WM_OPTIONS/bin/rfCanteraBridgeFoam
 sha256sum -c "/work/jobs/$build_job/solver-product.sha256" > "$job/solver-verified.txt"
fi
sha256sum "$solver" > "$job/solver-product.sha256"
ldd "$solver" > "$job/solver-ldd.txt"
! grep -q 'not found' "$job/solver-ldd.txt"
fresh=$release/replication/development/fresh-start
python3 -B "$fresh/prepare.py" plan energy "$key" "$job/case" --end-us 300 > "$job/case-plan.json"
python3 -B "$fresh/prepare.py" apply energy "$key" "$job/case" --end-us 300 > "$job/prepare.log"
python3 -B "$module/case.py" configure "$job" "$bridge_job" "$mode" --chemistry-mode "$chemistry" --execution-profile "$execution" --numerical-profile "$numerics"
blockMesh -case "$job/case" > "$job/blockMesh.log" 2>&1
checkMesh -case "$job/case" > "$job/checkMesh.log" 2>&1
grep -q 'Mesh OK' "$job/checkMesh.log"
probe=/work/jobs/124878193/openfoam-user/platforms/$WM_OPTIONS/bin/rfPropertyProbe
printf '%s  %s\n' b1c5a9c56e419bea81c556da391dd473df8011c066202f3fdb6a390683151c03 "$probe" | sha256sum -c - > "$job/probe-verified.txt"
"$probe" -case "$job/case" -initial > "$job/initial-probe.log" 2>&1
if [[ $execution == bands32 ]]; then
 python3 -B "$module/partition.py" plan "$job/case" "$execution" > "$job/partition-plan.json"
 python3 -B "$module/partition.py" apply "$job/case" "$execution" > "$job/partition-applied.json"
fi
python3 -B "$release/replication/development/premixed-paper/check.py" finalize "$job/case" > "$job/finalize.log"
decomposePar -case "$job/case" > "$job/decompose.log" 2>&1
python3 -B "$fresh/prepare.py" verify energy "$job/case" > "$job/initial-state-verified.json"
mpirun --mca btl self,vader,tcp -np "$ranks" "$solver" -case "$job/case" -parallel > "$job/case.log" 2>&1
grep -q '^End' "$job/case.log"
python3 -B "$module/case.py" check "$job" "$bridge_job" "$mode" --chemistry-mode "$chemistry" --execution-profile "$execution" --numerical-profile "$numerics" > "$job/endpoint-check.json"
if [[ $mode == build ]]; then
 printf 'PASS: ideal Cantera transport + %s chemistry original-zero smoke; steady speed unqualified\n' "$chemistry" > "$job/qualification-passed.txt"
else
 printf 'PASS: original-zero endpoint; steady speed unqualified\n' > "$job/result.txt"
fi
