#!/bin/bash
set -euo pipefail
root=${1:?}; release=${2:?}; sdk=${3:?}; inputs=${4:?}; action=${5:?}
build=${6:?}; phi=${7:-1.0}; guess=${8:--}; width=${9:-0.01}; tu=${10:-298}
variant=${11:-baseline}
grid_factor=${12:-1}
[[ -n ${SLURM_JOB_ID:-} ]] || exit 2
for path in "$release" "$sdk" "$inputs"; do
 [[ $(realpath -e "$path") == "$root/"* ]] || exit 2
done
job="$root/jobs/$SLURM_JOB_ID"
mkdir -p "$job"/{home,tmp,cache}
export HOME="$job/home" TMPDIR="$job/tmp" XDG_CACHE_HOME="$job/cache"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export LD_LIBRARY_PATH="$sdk/lib:${LD_LIBRARY_PATH:-}"
export CANTERA_DATA="$sdk/share/cantera/data" PKG_CONFIG_PATH="$sdk/lib/pkgconfig"
cd "$job"
cp "$release/SOURCE_REVISION" source-revision.txt
module="$release/replication/development/liang-hydrogen"
if [[ $action == build ]]; then
 unset CPLUS_INCLUDE_PATH C_INCLUDE_PATH CPATH LIBRARY_PATH
 compiler=/public/software/compiler/gcc/11.2.0/bin/g++
 "$compiler" --version > compiler.txt
 flags=$("$sdk/bin/pkg-config" --cflags --libs cantera)
 printf '%s\n' "$flags" > compiler-flags.txt
 for target in srk alpha takahashi; do
  "$compiler" -std=c++17 -O2 -D_GLIBCXX_USE_CXX11_ABI=1 \
   "$module/../cantera-liang/test_$target.cpp" $flags -Wl,-rpath,"$sdk/lib" -o "test-$target"
  "./test-$target" > "$target-check.txt"
 done
 "$compiler" -std=c++17 -O2 -D_GLIBCXX_USE_CXX11_ABI=1 "$module/test_pairs.cpp" \
  $flags -Wl,-rpath,"$sdk/lib" -o test-pairs > compile-pairs.log 2>&1
 ./test-pairs "$inputs" > pairs-check.txt
 "$compiler" -std=c++17 -O2 -D_GLIBCXX_USE_CXX11_ABI=1 "$module/test_midpoint.cpp" \
  $flags -Wl,-rpath,"$sdk/lib" -o test-midpoint > compile-midpoint.log 2>&1
 ./test-midpoint "$inputs/ideal.yaml" > midpoint-check.txt
 "$compiler" -std=c++17 -O2 -D_GLIBCXX_USE_CXX11_ABI=1 "$module/flame.cpp" \
  $flags -Wl,-rpath,"$sdk/lib" -o hydrogen-flame > compile.log 2>&1
 sha256sum hydrogen-flame > binary.sha256
 ldd hydrogen-flame > dependencies.txt
 touch build-passed.txt
else
 [[ $action =~ ^(1|2|3|3star|4|5)$ ]] || exit 2
 [[ $(realpath -e "$build") == "$root/jobs/"* ]] || exit 2
 test -f "$build/build-passed.txt"
 (cd "$build"; sha256sum -c binary.sha256)
 cmp "$build/source-revision.txt" "$release/SOURCE_REVISION"
 sha256sum "$inputs"/* > input-sha256.txt
 if [[ $guess != - ]]; then
  [[ $(realpath -e "$guess") == "$root/jobs/"* ]] || exit 2
  sha256sum "$guess" > guess-sha256.txt
 fi
 "$build/hydrogen-flame" "$inputs" "$action" "$phi" "$job/result" "$guess" "$width" "$tu" "$variant" "$grid_factor" > flame.log 2>&1
fi
