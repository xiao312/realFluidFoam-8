#!/usr/bin/env bash
set -euo pipefail
input=/workspace/inputs/rho-ha-probe-s07
build=/workspace/build/rho-ha-probe-s07
out=/workspace/results/rho-ha-probe-s07
parent=/workspace/build/relaxed-table-r54
[[ -n ${SLURM_JOB_ID:-} && ! -e $build && ! -e $out ]]
export HOME=/workspace/home TMPDIR=/workspace/tmp/rho-ha-probe-s07
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 WM_NCOMPPROCS=2
mkdir -p "$TMPDIR" "$build/source" "$build/bin" "$build/logs" "$out"
ulimit -c 0
(cd "$input";sha256sum -c inputs.sha256)
node "$input/verify-runtime.mjs" "$parent" > "$out/parent-runtime.json"
tar -xzf "$input/source.tar.gz" -C "$build/source"
export FOAM_USER_LIBBIN="$parent/lib" FOAM_USER_APPBIN="$build/bin" LIB_rfFoam8_SRC="$parent/source/src"
export CPATH=/usr/include/x86_64-linux-gnu${CPATH:+:$CPATH}
export LD_LIBRARY_PATH="$parent/lib:/opt/gcc-11.2.0/lib64:${LD_LIBRARY_PATH:-}"
node "$input/patch-build-options.mjs" "$build/source" > "$out/options.json"
if bash -euo pipefail -c 'cd "$1";wmake -j 2' _ "$build/source/replication/validation/realfluid-g2-thermo/probe" > "$build/logs/build.log" 2>&1;then :;else rc=$?;tail -60 "$build/logs/build.log";exit "$rc";fi
"$build/bin/realFluidG2ThermoProbe" -help > "$build/logs/help.txt" 2>&1
grep -F -- '-audit-rho-ha-state' "$build/logs/help.txt" > "$out/help-witness.txt"
ldd "$build/bin/realFluidG2ThermoProbe" > "$build/logs/probe-ldd.txt"
node "$input/qualify.mjs" "$build" "$input" "$parent" > "$out/build-receipt.json"
for index in 0 1 2 3 4 5 6;do
 case=/workspace/cases/rho-ha-probe-s07-$index
 node "$input/prepare.mjs" "$input" "$case" "$index" > "$out/plan-$index.json"
 node "$input/prepare.mjs" "$input" "$case" "$index" --apply > "$out/preparation-$index.json"
 blockMesh -case "$case" > "$case/log.blockMesh" 2>&1
 if timeout --signal=TERM --kill-after=10 120 "$build/bin/realFluidG2ThermoProbe" -case "$case" -audit-rho-ha-state > "$case/log.query" 2>&1;then rc=0;else rc=$?;fi
 printf '{"index":%s,"probeExit":%s,"CFDsteps":0}\n' "$index" "$rc" >> "$out/phases.jsonl"
 mkdir "$out/point-$index";cp "$case/point-input.json" "$out/point-$index/"
 if [[ -f $case/rho-ha-state.csv ]];then cp "$case/rho-ha-state.csv" "$out/point-$index/";fi
 tail -3 "$case/log.query"
done
node "$input/check.mjs" "$input" "$out"
