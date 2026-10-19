#!/bin/bash
set -euo pipefail
root=${1:?}; release=${2:?}; sdk=${3:?}; inputs=${4:?}; stage=${5:?}; build=${6:-}
phi=${7:-1.10}
variant=${8:-full}
[[ $variant =~ ^(full|(dense-increment|bounded-takahashi|pressure-chemistry|fine-grid|smoothed-alpha|takahashi-table2|takahashi-high-t)(,(dense-increment|bounded-takahashi|pressure-chemistry|fine-grid|smoothed-alpha|takahashi-table2|takahashi-high-t))*)$ ]] || exit 2
pressure=${9:-100}
[[ $pressure =~ ^[0-9]+([.][0-9]+)?$ ]] || exit 2
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
module_path="$release/replication/development/cantera-liang"
if [[ $stage == build ]]; then
 unset CPLUS_INCLUDE_PATH C_INCLUDE_PATH CPATH LIBRARY_PATH
 compiler=/public/software/compiler/gcc/11.2.0/bin/g++
 "$compiler" --version > compiler.txt
 flags=$($sdk/bin/pkg-config --cflags --libs cantera)
 printf '%s\n' "$flags" > compiler-flags.txt
 # pkg-config supplies compiler arguments, not shell commands.
 "$compiler" -std=c++17 -O2 -D_GLIBCXX_USE_CXX11_ABI=1 "$module_path/test_srk.cpp" -o test-srk
 ./test-srk > kernel-check.txt
 "$compiler" -std=c++17 -O2 "$module_path/test_alpha.cpp" -o test-alpha
 ./test-alpha > alpha-check.txt
 "$compiler" -std=c++17 -O2 "$module_path/test_takahashi.cpp" $flags -Wl,-rpath,"$sdk/lib" -o test-takahashi
 ./test-takahashi > takahashi-check.txt
 if ./test-takahashi legacy > takahashi-legacy-control.txt; then exit 1; fi
 if ./test-alpha legacy > alpha-legacy-control.txt; then exit 1; fi
 "$compiler" -std=c++17 -O2 -D_GLIBCXX_USE_CXX11_ABI=1 "$module_path/flame.cpp" \
   $flags -Wl,-rpath,"$sdk/lib" -o liang-flame > compile.log 2>&1
 "$compiler" -std=c++17 -O2 -D_GLIBCXX_USE_CXX11_ABI=1 "$module_path/model_probe.cpp" \
   $flags -Wl,-rpath,"$sdk/lib" -o model-probe > compile-probe.log 2>&1
 sha256sum model-probe > probe-binary.sha256
 "$compiler" -std=c++17 -O2 -D_GLIBCXX_USE_CXX11_ABI=1 "$module_path/energy_probe.cpp" \
   $flags -Wl,-rpath,"$sdk/lib" -o energy-probe > compile-energy.log 2>&1
 sha256sum energy-probe > energy-binary.sha256
 sha256sum liang-flame > binary.sha256
 ldd liang-flame > dependencies.txt
 touch build-passed.txt
else
 [[ $stage =~ ^[1-5]$ && $(realpath -e "$build") == "$root/jobs/"* ]] || exit 2
 test -f "$build/build-passed.txt"
 (cd "$build"; sha256sum -c binary.sha256)
 sha256sum "$inputs"/* > input-sha256.txt
 cp "$release/SOURCE_REVISION" source-revision.txt
 # Always pass defaults explicitly: older site Bash treats an empty array as
 # unbound under nounset, preventing the default ideal control from starting.
 "$build/liang-flame" "$inputs" "$stage" "$phi" "$job/result" "$variant" "$pressure" > flame.log 2>&1
fi
