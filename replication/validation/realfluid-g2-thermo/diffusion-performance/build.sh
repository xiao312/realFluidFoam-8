#!/usr/bin/env bash
set -euo pipefail
manifest=${1:?manifest}; mode=${2:---plan}
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [[ $mode == --plan ]]; then node "$here/package.mjs" "$manifest" --plan; exit 0; fi
[[ $mode == --apply && -n ${SLURM_JOB_ID:-} && ${WM_PROJECT_VERSION:-} == 8 ]] || exit 2
[[ $(g++ -dumpfullversion) == 11.2.0 ]] || exit 3
values=$(node "$here/package.mjs" "$manifest" --inputs); readarray -t inputs <<< "$values"
archive=${inputs[0]}; build=${inputs[1]}; out=${inputs[2]}
mkdir -p "$build/source" "$build/lib" "$build/bin" "$build/logs" "$out"
cp "$manifest" "$build/input-manifest.json"
tar -xf "$archive" -C "$build/source"
node "$here/package.mjs" "$manifest" --source > "$build/logs/source-verification.log"
export LIB_rfFoam8_SRC="$build/source/src" FOAM_USER_LIBBIN="$build/lib" FOAM_USER_APPBIN="$build/bin"
export WM_NCOMPPROCS=2 WM_CXX="$(command -v g++)" CPATH="/usr/include/x86_64-linux-gnu${CPATH:+:$CPATH}"
export LD_LIBRARY_PATH="$build/lib:/opt/gcc-11.2.0/lib64:${LD_LIBRARY_PATH:-}"
unset WM_CONTINUE_ON_ERROR
node "$here/package.mjs" "$manifest" --prepare-build > "$build/logs/build-preparation.log" 2>&1
printf '#include <iostream>\nint main(){std::cout<<"FULL_GCC_LINK_RUN_OK\\n";}\n' > "$build/link-probe.C"
g++ -isystem /usr/include/x86_64-linux-gnu -B/usr/lib/x86_64-linux-gnu/ "$build/link-probe.C" -o "$build/link-probe"
"$build/link-probe"
for module in basic reactionThermo; do
  printf 'PERF_BUILD_START module=%s utc=%s\n' "$module" "$(date -u +%FT%TZ)"
  if ! (cd "$build/source/src/thermophysicalModels/$module" && wmake -j 2 libso) > "$build/logs/$module.log" 2>&1; then
    tail -60 "$build/logs/$module.log"; exit 20
  fi
  printf 'PERF_BUILD_END module=%s utc=%s\n' "$module" "$(date -u +%FT%TZ)"
done
for module in applications/solvers/reactingFoamSolveZ replication/validation/realfluid-g2-thermo/probe; do
  if ! (cd "$build/source/$module" && wmake -j 2) > "$build/logs/${module##*/}.log" 2>&1; then
    tail -60 "$build/logs/${module##*/}.log"; exit 21
  fi
done
for binary in reactingFoamSolveZ realFluidG2ThermoProbe; do
  "$build/bin/$binary" -help > "$build/logs/$binary-help.txt" 2>&1
done
node "$here/package.mjs" "$manifest" --receipt
