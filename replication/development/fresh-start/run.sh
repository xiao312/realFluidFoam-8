#!/bin/bash
set -o pipefail
release=${1:?}; family=${2:?}; key=${3:?}
. /opt/openfoam8/etc/bashrc
set -euo pipefail
job="/work/jobs/$RF_JOB_ID"
module="$release/replication/development/fresh-start"
export LIB_rfFoam8_SRC=/work/builds/124657926/src
export FOAM_USER_LIBBIN="/work/jobs/124657926/openfoam-user/platforms/$WM_OPTIONS/lib"
export LD_LIBRARY_PATH="$FOAM_USER_LIBBIN:$LD_LIBRARY_PATH"
export WM_PROJECT_USER_DIR="$job/openfoam-user" FOAM_JOB_DIR="$job/jobControl"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
mkdir -p "$FOAM_JOB_DIR"
if [[ $family == native ]]; then
 solver="/work/jobs/124883260/openfoam-user/platforms/$WM_OPTIONS/bin/rfTrackedReactingFoam"
 expected=ebd0b93a17d77d417b0ee20250d1fb886b4982777ee51c896bc75b59c384796a
elif [[ $family == energy ]]; then
 solver="/work/jobs/124900963/openfoam-user/platforms/$WM_OPTIONS/bin/rfEnergyReactingFoam"
 expected=d07e6e45ae48aaf3a10ac1555c3630128ee03ed09bd58a50602fbd5722190304
else exit 2; fi
printf '%s  %s\n' "$expected" "$solver" | sha256sum -c - > "$job/binary-verified.txt"
sha256sum "$solver" > "$job/solver-product.sha256"
ldd "$solver" > "$job/solver-ldd.txt"
! grep -q 'not found' "$job/solver-ldd.txt"
python3 -B "$module/prepare.py" plan "$family" "$key" "$job/case" > "$job/case-plan.json"
python3 -B "$module/prepare.py" apply "$family" "$key" "$job/case" > "$job/prepare.log"
blockMesh -case "$job/case" > "$job/blockMesh.log" 2>&1
checkMesh -case "$job/case" > "$job/checkMesh.log" 2>&1
grep -q 'Mesh OK' "$job/checkMesh.log"
probe="/work/jobs/124878193/openfoam-user/platforms/$WM_OPTIONS/bin/rfPropertyProbe"
sha256sum -c "$release/replication/development/fresh-start/probe.sha256" > "$job/probe-verified.txt"
"$probe" -case "$job/case" -initial > "$job/initial-probe.log" 2>&1
python3 -B "$release/replication/development/premixed-paper/check.py" finalize "$job/case" > "$job/finalize.log"
decomposePar -case "$job/case" > "$job/decompose.log" 2>&1
python3 -B "$module/prepare.py" verify "$family" "$job/case" > "$job/initial-state-verified.json"
mpirun --mca btl self,vader,tcp -np 8 "$solver" -case "$job/case" -parallel > "$job/case.log" 2>&1
grep -q '^End' "$job/case.log"
python3 -B "$release/replication/development/flame-tracking/check.py" "$job" full > "$job/check.log"
echo 'PASS: original-zero endpoint; scientific convergence unqualified' > "$job/result.txt"
