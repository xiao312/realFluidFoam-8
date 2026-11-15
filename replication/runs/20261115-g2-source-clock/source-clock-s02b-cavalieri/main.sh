#!/usr/bin/env bash
set -euo pipefail
input=/workspace/inputs/source-clock-s02b-cavalieri
build=/workspace/build/source-clock-s01
out=/workspace/results/source-clock-s02b-cavalieri
[[ -n ${SLURM_JOB_ID:-} && ! -e $out && ${SLURM_NTASKS:-0} == 32 ]]
export HOME=/workspace/home TMPDIR=/workspace/tmp/source-clock-s02b-cavalieri
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export FOAM_USER_LIBBIN="$build/lib" FOAM_USER_APPBIN="$build/bin" LIB_rfFoam8_SRC="$build/source/src"
export LD_LIBRARY_PATH="$build/lib:/opt/gcc-11.2.0/lib64:${LD_LIBRARY_PATH:-}"
mkdir -p "$TMPDIR" "$out"
ulimit -c 0
(cd "$input";sha256sum -c inputs.sha256)
node "$input/verify-runtime.mjs" "$build" > "$out/runtime.json"
export G2_RELAXED_INPUT="$input" G2_RELAXED_BUILD="$build"
failed=0
for mode in steps fixedTime;do
 export G2_RELAXED_OUT="$out/$mode";mkdir "$G2_RELAXED_OUT"
 if bash -euo pipefail "$input/run.sh" "$mode" > "$out/$mode-driver.log" 2>&1;then rc=0;else rc=$?;failed=1;tail -40 "$out/$mode-driver.log";fi
 printf '{"mode":"%s","solverExit":%s,"startTime":0,"requestedEnd":0.0003,"scientificAcceptance":false}\n' "$mode" "$rc" >> "$out/phases.jsonl"
done
[[ $failed == 0 ]]
