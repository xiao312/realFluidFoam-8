#!/usr/bin/env bash
set -euo pipefail
input=/workspace/inputs/apec-s18
build=/workspace/build/apec-s18
parent=/workspace/build/exact-clock-s13
out=/workspace/results/apec-s18
[[ -n ${SLURM_JOB_ID:-} && ! -e $build && ! -e $out ]]
export HOME=/workspace/home TMPDIR=/workspace/tmp/apec-s18
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 WM_NCOMPPROCS=4
mkdir -p "$TMPDIR" "$build/source" "$build/bin" "$build/lib" "$build/logs" "$out"
(cd "$input";sha256sum -c inputs.sha256)
node "$input/verify-runtime.mjs" "$parent" > "$out/parent-runtime.json"
tar -xzf "$input/source.tar.gz" -C "$build/source"
for d in /opt/openfoam8/src/*;do name=${d##*/};[[ -e $build/source/src/$name ]] || ln -s "$d" "$build/source/src/$name";done
for f in "$parent"/lib/*.so;do ln -s "$f" "$build/lib/${f##*/}";done
export FOAM_USER_LIBBIN="$build/lib" FOAM_USER_APPBIN="$build/bin" LIB_rfFoam8_SRC="$build/source/src"
export CPATH=/usr/include/x86_64-linux-gnu${CPATH:+:$CPATH}
export LD_LIBRARY_PATH="$build/lib:/opt/gcc-11.2.0/lib64:${LD_LIBRARY_PATH:-}"
node "$input/patch-options.mjs" "$build/source"
mapfile -t modules < "$input/modules.txt"
for module in "${modules[@]}";do wmakeLnInclude -s "$build/source/$module" >> "$build/logs/includes.log" 2>&1;done
for module in replication/validation/schmitt-contact replication/validation/schmitt-contact/apec;do
 tag=${module//\//-}
 if bash -euo pipefail -c 'cd "$1";wmake -j 4' _ "$build/source/$module" > "$build/logs/$tag.log" 2>&1;then :;else rc=$?;tail -35 "$build/logs/$tag.log";exit "$rc";fi
done
for app in realFluidContactAPEC initializeSchmittContact;do
 "$build/bin/$app" -help > "$build/logs/$app-help.txt" 2>&1
 ldd "$build/bin/$app" > "$build/logs/$app-ldd.txt"
done
node "$input/qualify.mjs" "$build" "$parent" "$input" > "$out/build-qualification.json"
bash -euo pipefail "$input/run.sh" uniform 2 0.0001
pids=()
for mode in baseline full;do bash -euo pipefail "$input/run.sh" "$mode" 2 0.02 & pids+=("$!");done
failed=0;for pid in "${pids[@]}";do if wait "$pid";then :;else failed=$((failed+1));fi;done
printf 'APEC_CONTACT_BATCH_END failures=%s scientificAcceptance=0\n' "$failed"
[[ $failed == 0 ]]
