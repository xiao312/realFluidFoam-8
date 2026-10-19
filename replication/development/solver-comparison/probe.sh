#!/bin/bash
set -euo pipefail
release=${1:?}; job=${2:?}
module="$release/replication/development/solver-comparison"
stock_ld="$LD_LIBRARY_PATH"
for family in stock native; do
 build="$job/$family-build"
 mkdir "$build"
 cp "$module/chemistryProbe.C" "$build/"
 cp -r "$module/Make" "$build/"
 export CHEM_SRC="$LIB_SRC" CHEM_LIB="$FOAM_LIBBIN" LD_LIBRARY_PATH="$stock_ld"
 if [[ $family == native ]]; then
  export CHEM_SRC="/work/builds/124657926/src"
  export CHEM_LIB="/work/jobs/124657926/openfoam-user/platforms/$WM_OPTIONS/lib"
  export LD_LIBRARY_PATH="$CHEM_LIB:$stock_ld"
 fi
 wmake "$build" > "$job/$family-build.log" 2>&1
 cp "$FOAM_USER_APPBIN/rfChemistryCompare" "$build/rfChemistryCompare"
 ldd "$build/rfChemistryCompare" > "$build/ldd.txt"
 ! grep -q 'not found' "$build/ldd.txt"
 sha256sum "$build/rfChemistryCompare" > "$build/binary.sha256"
 for tolerance in base tight; do
  case="$job/$family-$tolerance"
  python3 -B "$module/probe_case.py" "$family" "$tolerance" /work/cache/solver-comparison/chemistry-states.json "$case" > "$job/$family-$tolerance-prepare.log"
  blockMesh -case "$case" > "$job/$family-$tolerance-mesh.log" 2>&1
  "$build/rfChemistryCompare" -case "$case" > "$job/$family-$tolerance.log" 2>&1
 done
done
echo 'PASS: chemistry probes completed; compare numerical evidence before interpretation' > "$job/probe-completed.txt"

