#!/usr/bin/env bash
set -euo pipefail
input=/workspace/inputs/oxygen-audit-s20
out=/workspace/results/oxygen-audit-s20
parent=/workspace/build/relaxed-table-r54
probe=/workspace/build/rho-ha-probe-s07/bin/realFluidG2ThermoProbe
[[ -n ${SLURM_JOB_ID:-} && ! -e $out ]]
export HOME=/workspace/home TMPDIR=/workspace/tmp/oxygen-audit-s20
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export FOAM_USER_LIBBIN="$parent/lib" FOAM_USER_APPBIN=/workspace/build/rho-ha-probe-s07/bin
export LD_LIBRARY_PATH="$parent/lib:/opt/gcc-11.2.0/lib64:${LD_LIBRARY_PATH:-}"
mkdir -p "$TMPDIR" "$out"
ulimit -c 0
(cd "$input";sha256sum -c inputs.sha256)
node "$input/verify-probe.mjs" > "$out/runtime.json"
for mode in p6000 p5610 p4994 p4869;do
 case=/workspace/cases/oxygen-audit-s20-$mode
 node "$input/prepare.mjs" "$case" "$mode" > "$out/$mode-plan.json"
 node "$input/prepare.mjs" "$case" "$mode" --apply > "$out/$mode-input.json"
 blockMesh -case "$case" > "$case/log.blockMesh" 2>&1
 if timeout --signal=TERM --kill-after=10 180 "$probe" -case "$case" > "$case/log.query" 2>&1;then rc=0;else rc=$?;fi
 printf '{"mode":"%s","probeExit":%s,"CFDsteps":0,"scientificAcceptance":false}\n' "$mode" "$rc" >> "$out/phases.jsonl"
 mkdir "$out/$mode"
 for file in "$case"/*.csv "$case/query-input.json";do [[ ! -f $file ]] || cp "$file" "$out/$mode/";done
 tail -3 "$case/log.query"
done
printf 'OXYGEN_DIAGNOSTIC_DELIVERED scientificAcceptance=0 CFDsteps=0\n'
