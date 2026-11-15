#!/usr/bin/env bash
set -euo pipefail
input=/workspace/inputs/cold-inversion-s05
out=/workspace/results/cold-inversion-s05
build=/workspace/build/relaxed-table-r54
[[ -n ${SLURM_JOB_ID:-} && ! -e $out ]]
export HOME=/workspace/home TMPDIR=/workspace/tmp/cold-inversion-s05
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export FOAM_USER_LIBBIN="$build/lib" FOAM_USER_APPBIN="$build/bin"
export LD_LIBRARY_PATH="$build/lib:/opt/gcc-11.2.0/lib64:${LD_LIBRARY_PATH:-}"
mkdir -p "$TMPDIR" "$out"
ulimit -c 0
(cd "$input";sha256sum -c inputs.sha256)
node "$input/verify-runtime.mjs" "$build" > "$out/runtime.json"
for mode in passes12 passes50 scan;do
 case=/workspace/cases/cold-inversion-s05-$mode
 node "$input/prepare.mjs" "$input" "$case" "$mode" > "$out/$mode-plan.json"
 node "$input/prepare.mjs" "$input" "$case" "$mode" --apply > "$out/$mode-preparation.json"
 blockMesh -case "$case" > "$case/log.blockMesh" 2>&1
 if timeout --signal=TERM --kill-after=15 180 "$build/bin/realFluidG2ThermoProbe" -case "$case" > "$case/log.query" 2>&1;then rc=0;else rc=$?;fi
 printf '{"mode":"%s","probeExit":%s,"CFDsteps":0,"scientificAcceptance":false}\n' "$mode" "$rc" >> "$out/phases.jsonl"
 mkdir "$out/$mode"
 for file in "$case"/*.csv "$case"/captured-query.json;do if [[ -f $file ]];then cp "$file" "$out/$mode/";fi;done
 tail -4 "$case/log.query"
done
printf 'COLD_INVERSION_QUERIES_DELIVERED numerical_exits_in_phases=1 no_CFD=1\n'
