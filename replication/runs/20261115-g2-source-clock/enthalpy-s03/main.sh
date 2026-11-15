#!/usr/bin/env bash
set -euo pipefail
input=/workspace/inputs/enthalpy-s03
out=/workspace/results/enthalpy-s03
build=/workspace/build/relaxed-table-r54
[[ -n ${SLURM_JOB_ID:-} && ! -e $out ]]
export HOME=/workspace/home TMPDIR=/workspace/tmp/enthalpy-s03
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export FOAM_USER_LIBBIN="$build/lib" FOAM_USER_APPBIN="$build/bin"
export LD_LIBRARY_PATH="$build/lib:/opt/gcc-11.2.0/lib64:${LD_LIBRARY_PATH:-}"
mkdir -p "$TMPDIR" "$out"
ulimit -c 0
(cd "$input";sha256sum -c inputs.sha256)
node "$input/verify-runtime.mjs" "$build" > "$out/runtime.json"
for index in 0 1 2 3 4 5 6 7;do
 case=/workspace/cases/enthalpy-s03-$index
 node "$input/prepare.mjs" "$input" "$case" "$index" > "$out/plan-$index.json"
 node "$input/prepare.mjs" "$input" "$case" "$index" --apply > "$out/preparation-$index.json"
 blockMesh -case "$case" > "$case/log.blockMesh" 2>&1
 if timeout --signal=TERM --kill-after=10 45 "$build/bin/realFluidG2ThermoProbe" -case "$case" > "$case/log.properties" 2>&1;then first=0;else first=$?;fi
 if test -s "$case/cold-properties.csv";then
  node "$input/target.mjs" "$case"
  if timeout --signal=TERM --kill-after=10 60 "$build/bin/realFluidG2ThermoProbe" -case "$case" > "$case/log.enthalpy" 2>&1;then second=0;else second=$?;fi
 else second=99;fi
 printf '{"index":%s,"propertyExit":%s,"enthalpyExit":%s,"CFDsteps":0}\n' "$index" "$first" "$second" >> "$out/phases.jsonl"
 mkdir "$out/query-$index"
 cp "$case/query.json" "$out/query-$index/"
 for file in "$case"/*.csv "$case"/enthalpy-query-input.json;do if [[ -f $file ]];then cp "$file" "$out/query-$index/";fi;done
done
printf 'ENTHALPY_QUERY_DELIVERY_COMPLETE no_science_acceptance=1 CFDsteps=0\n'
