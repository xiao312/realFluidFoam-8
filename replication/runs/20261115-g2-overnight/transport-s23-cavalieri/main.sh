#!/usr/bin/env bash
set -euo pipefail
input=/workspace/inputs/transport-s23-cavalieri
build=/workspace/build/transport-s23-cavalieri
out=/workspace/results/transport-s23-cavalieri
parent=/workspace/build/exact-clock-s13
[[ -n ${SLURM_JOB_ID:-} && ${SLURM_NTASKS:-0} == 32 && ! -e $build && ! -e $out ]]
export HOME=/workspace/home TMPDIR=/workspace/tmp/transport-s23-cavalieri
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 WM_NCOMPPROCS=4
mkdir -p "$TMPDIR" "$build/source" "$build/bin" "$build/logs" "$out"
ulimit -c 0
(cd "$input";sha256sum -c inputs.sha256)
node "$input/verify-parent.mjs" "$parent" > "$out/parent-runtime.json"
tar -xzf "$input/source.tar.gz" -C "$build/source"
ln -s "$parent/lib" "$build/lib"
ln -s "$parent/bin/realFluidG2ThermoProbe" "$build/bin/realFluidG2ThermoProbe"
export FOAM_USER_LIBBIN="$parent/lib" FOAM_USER_APPBIN="$build/bin" LIB_rfFoam8_SRC="$parent/source/src"
export CPATH=/usr/include/x86_64-linux-gnu${CPATH:+:$CPATH}
export LD_LIBRARY_PATH="$parent/lib:/opt/gcc-11.2.0/lib64:${LD_LIBRARY_PATH:-}"
node "$input/patch-build-options.mjs" "$build/source" > "$out/options.json"
if bash -euo pipefail -c 'cd "$1";wmake -j 4' _ "$build/source/applications/solvers/reactingFoamSolveZ" > "$build/logs/build.log" 2>&1;then :;else rc=$?;tail -60 "$build/logs/build.log";exit "$rc";fi
"$build/bin/reactingFoamSolveZ" -help > "$build/logs/help.txt" 2>&1
ldd "$build/bin/reactingFoamSolveZ" > "$build/logs/solver-ldd.txt"
node "$input/qualify.mjs" "$build" "$input" "$parent" > "$out/build-receipt.json"
export G2_RELAXED_INPUT="$input" G2_RELAXED_BUILD="$build"
for variant in defaultOff tight;do
 export G2_RELAXED_OUT="$out/$variant";mkdir "$G2_RELAXED_OUT"
 if bash -euo pipefail "$input/run.sh" "$variant" > "$out/$variant-driver.log" 2>&1;then rc=0;else rc=$?;tail -45 "$out/$variant-driver.log";fi
 printf '{"variant":"%s","solverExit":%s,"startTime":0,"scientificAcceptance":false}\n' "$variant" "$rc" >> "$out/phases.jsonl"
 [[ $rc == 0 ]] || exit "$rc"
 if [[ $variant == defaultOff ]];then
  node "$input/check-default-flow.mjs" /workspace/cases/g2-relaxed-transport-s23-cavalieri-defaultOff "$out/default-flow-parity.json"
 fi
done
