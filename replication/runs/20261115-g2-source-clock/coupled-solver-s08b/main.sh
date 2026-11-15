#!/usr/bin/env bash
set -euo pipefail
input=/workspace/inputs/coupled-solver-s08b
build=/workspace/build/coupled-solver-s08b
out=/workspace/results/coupled-solver-s08b
parent=/workspace/build/source-clock-s01
[[ -n ${SLURM_JOB_ID:-} && ! -e $build && ! -e $out ]]
export HOME=/workspace/home TMPDIR=/workspace/tmp/coupled-solver-s08b
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 WM_NCOMPPROCS=4
mkdir -p "$TMPDIR" "$build/source" "$build/bin" "$build/logs" "$out"
ulimit -c 0
(cd "$input";sha256sum -c inputs.sha256)
node "$input/verify-parent.mjs" "$parent" > "$out/parent-runtime.json"
node --input-type=module -e 'import fs from "node:fs";let q=JSON.parse(fs.readFileSync("/workspace/results/rho-ha-probe-s07/qualification.json"));if(q.executedQueries!==21||q.tests.length!==7)throw Error("RhoHa API not qualified");' > "$out/api-gate.txt"
tar -xzf "$input/source.tar.gz" -C "$build/source"
export FOAM_USER_LIBBIN="$parent/lib" FOAM_USER_APPBIN="$build/bin" LIB_rfFoam8_SRC="$parent/source/src"
export CPATH=/usr/include/x86_64-linux-gnu${CPATH:+:$CPATH}
export LD_LIBRARY_PATH="$parent/lib:/opt/gcc-11.2.0/lib64:${LD_LIBRARY_PATH:-}"
node "$input/patch-build-options.mjs" "$build/source" > "$out/options.json"
if bash -euo pipefail -c 'cd "$1";wmake -j 4' _ "$build/source/applications/solvers/reactingFoamSolveZ" > "$build/logs/build.log" 2>&1;then :;else rc=$?;tail -60 "$build/logs/build.log";exit "$rc";fi
"$build/bin/reactingFoamSolveZ" -help > "$build/logs/help.txt" 2>&1
ldd "$build/bin/reactingFoamSolveZ" > "$build/logs/solver-ldd.txt"
node "$input/qualify.mjs" "$build" "$input" "$parent" > "$out/build-receipt.json"
ln -s /workspace/build/relaxed-table-r54/bin/realFluidG2ThermoProbe "$build/bin/realFluidG2ThermoProbe"
case=/workspace/cases/coupled-solver-s08b-default-source
node "$input/prepare.mjs" "$build" /workspace/results/g2-fixed-h-r42-schmitt/thermo /workspace/inputs/g2-diagnostics-20261114-r21/schmitt-table/steady.tbl "$case" 100 --apply > "$out/default-source-preparation.json"
blockMesh -case "$case" > "$case/log.blockMesh" 2>&1
"$build/bin/realFluidG2ThermoProbe" -case "$case" -initialize-Ha > "$case/log.initialize" 2>&1
"$build/bin/reactingFoamSolveZ" -case "$case" -relaxation-probe > "$case/log.source" 2>&1
cp "$case/relaxation-probe.csv" "$out/default-source.csv"
node "$input/compare-probes.mjs" /workspace/results/source-clock-s01/steps.csv "$out/default-source.csv" "$out/default-parity.json"
printf 'COUPLED_SOLVER_BUILD_AND_DEFAULT_SOURCE_PARITY_RETURN no_CFD_qualification=1\n'
