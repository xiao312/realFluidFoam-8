#!/usr/bin/env bash
set -euo pipefail
input=/workspace/inputs/schmitt-state-s10
out=/workspace/results/schmitt-state-s10
parent=/workspace/build/relaxed-table-r54
probe=/workspace/build/rho-ha-probe-s07/bin/realFluidG2ThermoProbe
[[ -n ${SLURM_JOB_ID:-} && ! -e $out ]]
export HOME=/workspace/home TMPDIR=/workspace/tmp/schmitt-state-s10 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export FOAM_USER_LIBBIN="$parent/lib" LD_LIBRARY_PATH="$parent/lib:/opt/gcc-11.2.0/lib64:${LD_LIBRARY_PATH:-}"
mkdir -p "$out" "$TMPDIR"
ulimit -c 0
(cd "$input";sha256sum -c inputs.sha256)
node "$input/verify-runtime.mjs" "$parent" > "$out/runtime.json"
printf '%s  %s\n' 599c29fee8bd509f3b9b58700a1c04048fffd0dea719221e8c4ac5a41ae9156d "$probe" | sha256sum -c - > "$out/probe-hash.txt"
case=/workspace/cases/schmitt-state-s10-scan
node "$input/prepare-scan.mjs" "$input" "$case" scan > "$out/scan-plan.json"
node "$input/prepare-scan.mjs" "$input" "$case" scan --apply > "$out/scan-preparation.json"
blockMesh -case "$case" > "$case/log.blockMesh" 2>&1
if timeout --signal=TERM --kill-after=10 180 "$parent/bin/realFluidG2ThermoProbe" -case "$case" > "$case/log.query" 2>&1;then rc=0;else rc=$?;fi
printf '{"phase":"scan","exit":%s,"CFDsteps":0}\n' "$rc" >> "$out/phases.jsonl"
mkdir "$out/scan";cp "$case"/*.csv "$out/scan/"
for index in 0 1;do
 case=/workspace/cases/schmitt-state-s10-rho-ha-$index
 node "$input/prepare-rho-ha.mjs" "$input" "$case" "$index" > "$out/rho-ha-$index-plan.json"
 node "$input/prepare-rho-ha.mjs" "$input" "$case" "$index" --apply > "$out/rho-ha-$index-preparation.json"
 blockMesh -case "$case" > "$case/log.blockMesh" 2>&1
 if timeout --signal=TERM --kill-after=10 180 "$probe" -case "$case" -audit-rho-ha-state > "$case/log.query" 2>&1;then rc=0;else rc=$?;fi
 printf '{"phase":"rhoHa","index":%s,"exit":%s,"CFDsteps":0}\n' "$index" "$rc" >> "$out/phases.jsonl"
 mkdir "$out/rho-ha-$index";cp "$case/point-input.json" "$case/rho-ha-state.csv" "$out/rho-ha-$index/"
done
printf 'EXACT_STATE_DELIVERY_RETURN no_CFD_or_science_acceptance=1\n'
