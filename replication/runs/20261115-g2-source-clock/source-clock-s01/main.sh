#!/usr/bin/env bash
set -euo pipefail
input=/workspace/inputs/source-clock-s01
build=/workspace/build/source-clock-s01
out=/workspace/results/source-clock-s01
parent=/workspace/build/relaxed-table-r54
[[ -n ${SLURM_JOB_ID:-} && ! -e $build && ! -e $out ]]
export HOME=/workspace/home TMPDIR=/workspace/tmp/source-clock-s01
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 WM_NCOMPPROCS=8
mkdir -p "$TMPDIR" "$build/source" "$build/bin" "$build/lib" "$build/logs" "$out"
ulimit -c 0
(cd "$input";sha256sum -c inputs.sha256)
tar -xzf "$input/source.tar.gz" -C "$build/source"
for directory in /opt/openfoam8/src/*;do name=${directory##*/};if [[ ! -e $build/source/src/$name ]];then ln -s "$directory" "$build/source/src/$name";fi;done
for file in "$parent"/lib/*.so;do name=${file##*/};if [[ $name != libcombustionModels.so ]];then ln -s "$file" "$build/lib/$name";fi;done
ln -s "$parent/bin/realFluidG2ThermoProbe" "$build/bin/realFluidG2ThermoProbe"
export FOAM_USER_LIBBIN="$build/lib" FOAM_USER_APPBIN="$build/bin" LIB_rfFoam8_SRC="$build/source/src"
export CPATH=/usr/include/x86_64-linux-gnu${CPATH:+:$CPATH}
export LD_LIBRARY_PATH="$build/lib:/opt/gcc-11.2.0/lib64:${LD_LIBRARY_PATH:-}"
unset WM_CONTINUE_ON_ERROR
node "$input/patch-build-options.mjs" "$build/source" > "$out/build-options.json"
mapfile -t modules < "$input/modules.txt"
for module in "${modules[@]}";do wmakeLnInclude -s "$build/source/$module" >> "$build/logs/includes.log" 2>&1;done
for module in src/combustionModels applications/solvers/reactingFoamSolveZ;do
 tag=${module//\//-}
 printf 'BUILD_BEGIN module=%s utc=%s\n' "$module" "$(date -u +%FT%TZ)"
 if bash -euo pipefail -c 'cd "$1";wmake -j 8' _ "$build/source/$module" > "$build/logs/$tag.log" 2>&1;then :;else rc=$?;tail -60 "$build/logs/$tag.log";exit "$rc";fi
 printf 'BUILD_COMPLETE module=%s utc=%s\n' "$module" "$(date -u +%FT%TZ)"
done
"$build/bin/reactingFoamSolveZ" -help > "$build/logs/reactingFoamSolveZ-help.txt" 2>&1
ldd "$build/bin/reactingFoamSolveZ" > "$build/logs/reactingFoamSolveZ-ldd.txt"
node "$input/qualify.mjs" "$build" "$input" "$parent" > "$out/build-receipt.json"
thermo=/workspace/results/g2-fixed-h-r42-schmitt/thermo
table=/workspace/inputs/g2-diagnostics-20261114-r21/schmitt-table/steady.tbl
for mode in steps fixedTime invalid;do
 case=/workspace/cases/source-clock-s01-$mode
 node "$input/prepare.mjs" "$build" "$thermo" "$table" "$case" 100 --apply > "$out/$mode-preparation.json"
 if [[ $mode != steps ]];then
  tau=100;[[ $mode != invalid ]] || tau=0.5
  sed -i "s/relaxationSteps 100;/relaxationMode fixedTime;relaxationTime $tau;/" "$case/constant/combustionProperties"
 fi
 blockMesh -case "$case" > "$case/log.blockMesh" 2>&1
 "$build/bin/realFluidG2ThermoProbe" -case "$case" -initialize-Ha > "$case/log.initialize-Ha" 2>&1
 (cd "$case";find 0 constant system -type f -print0 | sort -z | xargs -0 sha256sum > active-timezero.sha256)
 if timeout --signal=TERM --kill-after=15 180 "$build/bin/reactingFoamSolveZ" -case "$case" -relaxation-probe > "$case/log.source" 2>&1;then rc=0;else rc=$?;fi
 printf '{"mode":"%s","exit":%s,"CFDsteps":0}\n' "$mode" "$rc" >> "$out/phases.jsonl"
 if [[ $mode == invalid ]];then
  [[ $rc != 0 ]];grep -F 'relaxationTime must be positive, finite and >= deltaT' "$case/log.source" > "$out/invalid-rejection.txt"
 else
  [[ $rc == 0 ]];cp "$case/relaxation-probe.csv" "$out/$mode.csv"
 fi
done
node "$input/compare-probes.mjs" "$out/steps.csv" "$out/fixedTime.csv" "$out/parity.json"
printf 'CLOCK_BUILD_SOURCE_PARITY_QUALIFIED job=%s CFDsteps=0\n' "$SLURM_JOB_ID"
