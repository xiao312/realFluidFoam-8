#!/bin/bash
set -eo pipefail
release=${1:?}; mode=${2:?}
. /opt/openfoam8/etc/bashrc
set -euo pipefail
job="/work/jobs/$RF_JOB_ID"
export WM_PROJECT_USER_DIR="$job/openfoam-user"
export FOAM_USER_APPBIN="$WM_PROJECT_USER_DIR/platforms/$WM_OPTIONS/bin"
export FOAM_USER_LIBBIN="$WM_PROJECT_USER_DIR/platforms/$WM_OPTIONS/lib"
export FOAM_JOB_DIR="$job/jobControl" OMP_NUM_THREADS=1
mkdir -p "$FOAM_USER_APPBIN" "$FOAM_USER_LIBBIN" "$FOAM_JOB_DIR"
module="$release/replication/development/solver-comparison"
if [[ $mode == probe ]]; then
 exec bash "$module/probe.sh" "$release" "$job"
fi
solver="$FOAM_APPBIN/reactingFoam"
sha256sum "$solver" > "$job/solver-product.sha256"
ldd "$solver" > "$job/solver-ldd.txt"
! grep -q 'not found\|/work/jobs/124657926' "$job/solver-ldd.txt"
python3 -B "$module/prepare.py" plan stock "$job/case" > "$job/case-plan.json"
python3 -B "$module/prepare.py" apply stock "$job/case" > "$job/prepare.log"
blockMesh -case "$job/case" > "$job/blockMesh.log" 2>&1
checkMesh -case "$job/case" > "$job/checkMesh.log" 2>&1
grep -q 'Mesh OK' "$job/checkMesh.log"
decomposePar -case "$job/case" > "$job/decompose.log" 2>&1
mpirun --mca btl self,vader,tcp -np 8 "$solver" -case "$job/case" -parallel > "$job/solver.log" 2>&1
grep -q '^End' "$job/solver.log"
