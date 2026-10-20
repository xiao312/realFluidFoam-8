#!/bin/bash
set -euo pipefail
mode=${1:?plan or apply}; root=${2:?}; release=${3:?}; sdk=${4:?}; inputs=${5:?}
[[ $mode == plan || $mode == apply ]] || exit 2
[[ $(realpath -e "$root") == "$root" && $root == /public/home/dfagent/FlamePilot/* ]] || exit 2
for path in "$release" "$sdk" "$inputs"; do
    [[ $(realpath -e "$path") == "$root/"* ]] || exit 2
done
module_path="$release/replication/validation/diffusion"
test -f "$module_path/property_probe.cpp"
test -f "$inputs/ideal.yaml"
test -f "$inputs/species.txt"
test -f "$release/SOURCE_REVISION"
if [[ $mode == plan ]]; then
    printf 'PLAN: compile prescribed-state probe; release=%s sdk=%s inputs=%s\n' "$release" "$sdk" "$inputs"
    printf 'Outputs: %s/jobs/SLURM_JOB_ID; no flame solve\n' "$root"
    exit 0
fi
[[ -n ${SLURM_JOB_ID:-} ]] || exit 2
job="$root/jobs/$SLURM_JOB_ID"
test ! -e "$job"
mkdir -p "$job"/{home,tmp,cache}
export HOME="$job/home" TMPDIR="$job/tmp" XDG_CACHE_HOME="$job/cache"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export LD_LIBRARY_PATH="$sdk/lib:${LD_LIBRARY_PATH:-}"
export CANTERA_DATA="$sdk/share/cantera/data" PKG_CONFIG_PATH="$sdk/lib/pkgconfig"
unset CPLUS_INCLUDE_PATH C_INCLUDE_PATH CPATH LIBRARY_PATH
cd "$job"
cp "$release/SOURCE_REVISION" source-revision.txt
sha256sum "$inputs/ideal.yaml" "$inputs/species.txt" "$module_path/references.json" \
    "$sdk/lib/libcantera.so" > input-sha256.txt
compiler=/public/software/compiler/gcc/11.2.0/bin/g++
"$compiler" --version > compiler.txt
flags=$("$sdk/bin/pkg-config" --cflags --libs cantera)
printf '%s\n' "$flags" > compiler-flags.txt
"$compiler" -std=c++17 -O2 -D_GLIBCXX_USE_CXX11_ABI=1 \
    "$module_path/property_probe.cpp" $flags -Wl,-rpath,"$sdk/lib" \
    -o property-probe > compile.log 2>&1
sha256sum property-probe > binary.sha256
ldd property-probe > dependencies.txt
python3 -B "$module_path/prepare.py" "$inputs"
python3 -B "$module_path/prepare.py" "$inputs" --output requests.csv
./property-probe "$inputs" requests.csv corrected > corrected.csv 2> corrected.log
python3 -B "$module_path/check.py" requests.csv corrected.csv > corrected-report.json
./property-probe "$inputs" requests.csv legacy > legacy.csv 2> legacy.log
set +e
python3 -B "$module_path/check.py" requests.csv legacy.csv > legacy-report.json
legacy_status=$?
set -e
[[ $legacy_status == 1 ]] || { echo "Legacy control did not fail as expected"; exit 1; }
touch verification-passed.txt
