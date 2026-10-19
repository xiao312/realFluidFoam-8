#!/bin/bash
set -o pipefail
release=${1:?}
. /opt/openfoam8/etc/bashrc
set -euo pipefail
job="/work/jobs/$RF_JOB_ID"
module="$release/replication/development/energy-update"
comparison="$release/replication/development/solver-comparison"
export LIB_rfFoam8_SRC=/work/builds/124657926/src
export FOAM_USER_LIBBIN="/work/jobs/124657926/openfoam-user/platforms/$WM_OPTIONS/lib"
export WM_PROJECT_USER_DIR="$job/openfoam-user"
export FOAM_USER_APPBIN="$WM_PROJECT_USER_DIR/platforms/$WM_OPTIONS/bin"
export FOAM_JOB_DIR="$job/jobControl" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export LD_LIBRARY_PATH="$FOAM_USER_LIBBIN:$LD_LIBRARY_PATH"
export CHEM_SRC="$LIB_rfFoam8_SRC" CHEM_LIB="$FOAM_USER_LIBBIN"
mkdir -p "$FOAM_USER_APPBIN" "$FOAM_JOB_DIR" "$job/probe-source/Make"
python3 -B "$module/instrument.py" plan "$release" "$job/solver-source" > "$job/solver-plan.txt"
python3 -B "$module/instrument.py" apply "$release" "$job/solver-source" > "$job/instrument.log"
wmake "$job/solver-source" > "$job/build.log" 2>&1
solver="$FOAM_USER_APPBIN/rfEnergyReactingFoam"
sha256sum "$solver" > "$job/solver-product.sha256"
ldd "$solver" > "$job/solver-ldd.txt"
! grep -q 'not found' "$job/solver-ldd.txt"
cp "$module/checkEnthalpyUpdate.C" "$module/CurrentSpeciesEnthalpy.H" "$job/probe-source/"
cp "$comparison/Make/options" "$job/probe-source/Make/options"
printf 'checkEnthalpyUpdate.C\nEXE = $(FOAM_USER_APPBIN)/rfCheckEnthalpyUpdate\n' > "$job/probe-source/Make/files"
wmake "$job/probe-source" > "$job/probe-build.log" 2>&1
python3 -B "$comparison/probe_case.py" native base "$comparison/chemistry-states.json" "$job/probe" > "$job/probe-prepare.log"
blockMesh -case "$job/probe" > "$job/probe-mesh.log" 2>&1
set +e
rfCheckEnthalpyUpdate -case "$job/probe" -legacy > "$job/legacy-probe.log" 2>&1
legacy_status=$?
set -e
[[ $legacy_status == 1 ]]
grep -q 'ENTHALPY_CHECK' "$job/legacy-probe.log"
rfCheckEnthalpyUpdate -case "$job/probe" > "$job/refreshed-probe.log" 2>&1
grep -q 'failures=0' "$job/refreshed-probe.log"
printf 'PASS: unchanged cache fails; current species enthalpy passes\n' > "$job/enthalpy-probe-passed.txt"
tracking="$release/replication/development/flame-tracking"
python3 -B "$tracking/prepare.py" plan "$job" phi110 full > "$job/case-plan.json"
python3 -B "$tracking/prepare.py" apply "$job" phi110 full > "$job/copy.log"
python3 -B "$module/check.py" inputs "$job" > "$job/inputs-check.log"
cp -a "$job/case" "$job/smoke"
python3 -B "$module/check.py" prepare-smoke "$job"
mpirun --mca btl self,vader,tcp -np 8 "$solver" -case "$job/smoke" -parallel > "$job/smoke.log" 2>&1
grep -q '^End' "$job/smoke.log"
python3 -B "$module/check.py" smoke "$job" > "$job/smoke-check.log"
printf 'PASS: isolated energy-update smoke; flame speed unqualified\n' > "$job/smoke-passed.txt"
mpirun --mca btl self,vader,tcp -np 8 "$solver" -case "$job/case" -parallel > "$job/case.log" 2>&1
grep -q '^End' "$job/case.log"
python3 -B "$tracking/check.py" "$job" full > "$job/full-check.log"
echo 'PASS: energy-update endpoint; scientific convergence unqualified' > "$job/result.txt"
