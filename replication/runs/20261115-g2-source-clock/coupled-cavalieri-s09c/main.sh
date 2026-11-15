#!/usr/bin/env bash
set -euo pipefail
input=/workspace/inputs/coupled-cavalieri-s09c
build=/workspace/build/coupled-solver-s08b
out=/workspace/results/coupled-cavalieri-s09c
parent=/workspace/build/source-clock-s01
[[ -n ${SLURM_JOB_ID:-} && ! -e $out && ${SLURM_NTASKS:-0} == 32 ]]
export HOME=/workspace/home TMPDIR=/workspace/tmp/coupled-cavalieri-s09c
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export FOAM_USER_LIBBIN="$parent/lib" FOAM_USER_APPBIN="$build/bin" LIB_rfFoam8_SRC="$parent/source/src"
export LD_LIBRARY_PATH="$parent/lib:/opt/gcc-11.2.0/lib64:${LD_LIBRARY_PATH:-}"
mkdir -p "$TMPDIR" "$out"
ulimit -c 0
(cd "$input";sha256sum -c inputs.sha256)
node "$input/verify-runtime.mjs" "$build" "$parent" > "$out/runtime.json"
export G2_RELAXED_INPUT="$input" G2_RELAXED_BUILD="$build"
for variant in default gibbs coupled;do
 export G2_RELAXED_OUT="$out/$variant";mkdir "$G2_RELAXED_OUT"
 if bash -euo pipefail "$input/run.sh" "$variant" > "$out/$variant-driver.log" 2>&1;then rc=0;else rc=$?;tail -45 "$out/$variant-driver.log";fi
 end=0.0003;[[ $variant != default ]] || end=0.0001
 printf '{"variant":"%s","solverExit":%s,"startTime":0,"requestedEnd":%s,"scientificAcceptance":false}\n' "$variant" "$rc" "$end" >> "$out/phases.jsonl"
 if [[ $variant == default ]];then
  [[ $rc == 0 ]]
  node "$input/check-default-flow.mjs" /workspace/cases/g2-relaxed-coupled-s09c-cavalieri-default "$out/default-flow-regression.json"
 fi
done
printf 'CONTROLLED_CFD_DELIVERY_RETURN per_case_failures_in_phases=1 no_science_acceptance=1\n'
