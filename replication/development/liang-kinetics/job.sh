#!/bin/bash
set -euo pipefail
root=${1:?}; release=${2:?}; sdk=${3:?}; mechanism=${4:?}
action=${5:?}; build=${6:?}; phi=${7:?}; expected_sha=${8:?}
guess=${9:--}
[[ -n ${SLURM_JOB_ID:-} ]] || exit 2
for path in "$release" "$sdk" "$mechanism"; do
 [[ $(realpath -e "$path") == "$root/"* ]] || exit 2
done
[[ $(sha256sum "$mechanism" | cut -d' ' -f1) == "$expected_sha" ]] || exit 2
job="$root/jobs/$SLURM_JOB_ID"
mkdir -p "$job"/{home,tmp,cache}
export HOME="$job/home" TMPDIR="$job/tmp" XDG_CACHE_HOME="$job/cache"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export LD_LIBRARY_PATH="$sdk/lib:${LD_LIBRARY_PATH:-}"
export CANTERA_DATA="$sdk/share/cantera/data" PKG_CONFIG_PATH="$sdk/lib/pkgconfig"
cd "$job"
cp "$release/SOURCE_REVISION" source-revision.txt
sha256sum "$mechanism" > input-sha256.txt
if [[ $action == build ]]; then
 unset CPLUS_INCLUDE_PATH C_INCLUDE_PATH CPATH LIBRARY_PATH
 compiler=/public/software/compiler/gcc/11.2.0/bin/g++
 "$compiler" --version > compiler.txt
 flags=$("$sdk/bin/pkg-config" --cflags --libs cantera)
 printf '%s\n' "$flags" > compiler-flags.txt
 "$compiler" -std=c++17 -O2 -D_GLIBCXX_USE_CXX11_ABI=1 \
  "$release/replication/development/liang-kinetics/flame.cpp" $flags \
  -Wl,-rpath,"$sdk/lib" -o kinetics-flame > compile.log 2>&1
 sha256sum kinetics-flame > binary.sha256
 ldd kinetics-flame > dependencies.txt
 touch build-passed.txt
else
 [[ $action == flame && $(realpath -e "$build") == "$root/jobs/"* ]] || exit 2
 test -f "$build/build-passed.txt"
 (cd "$build"; sha256sum -c binary.sha256)
 cmp "$build/source-revision.txt" "$release/SOURCE_REVISION"
 if [[ $guess != - ]]; then
  [[ $(realpath -e "$guess") == "$root/"* ]] || exit 2
  sha256sum "$guess" > guess-sha256.txt
 fi
 "$build/kinetics-flame" "$mechanism" "$phi" "$job/result" "$guess" > flame.log 2>&1
fi
