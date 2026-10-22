#!/bin/bash
# Batch adaptation of job.sh for the registered `cantera32` image.
#
# job.sh above is the legacy site wrapper: it requires the old project root, a
# `release/` tree, the site compiler /public/software/compiler/gcc/11.2.0/bin/g++
# and the SDK unpacked under the project root, and it writes into $root/jobs. None of
# that exists in this campaign. This file keeps job.sh's build and case logic (same
# tests, same flags, same ordering, same controls) and changes only the four
# environment bindings, which stay read-only inputs:
#
#   compiler  /opt/gcc-11.2.0/bin/g++
#   SDK       /opt/cantera-sdk           (pkg-config: --define-variable=prefix=...)
#   module    this checkout's cantera-liang directory
#   inputs    a frozen science-inputs directory (ideal.yaml, srk.yaml, species.txt, guess.csv)
#
# Two identities are checked before anything is compiled or solved, both frozen by the
# submitter into the run directory: `<run>/module.sha256` (every module source this
# wrapper compiles) and, for the inputs, `<run>/inputs.sha256`. A mismatch aborts; the
# wrapper never silently builds a different tree than the one the receipt names.
#
# Usage:
#   job-batch.sh build MODULE INPUTS RUN
#   job-batch.sh case  MODULE INPUTS RUN BUILD STAGE PHI VARIANT PRESSURE_ATM RTOL ATOL
#
# The `case` mode reuses the binary and its sha256 from BUILD, so a case never silently
# recompiles. Every artefact is written under RUN.
set -euo pipefail

mode=${1:?mode: build|case}
module=${2:?module directory}
inputs=${3:?inputs directory}
run=${4:?run directory}
[[ $mode == build || $mode == case ]] || { echo "unknown mode $mode" >&2; exit 2; }

sdk=/opt/cantera-sdk
compiler=/opt/gcc-11.2.0/bin/g++
case $mode in
  build)
    build=$run ;;
  case)
    build=${5:?build directory}
    stage=${6:?stage}; phi=${7:?phi}; variant=${8:?variant}
    pressure=${9:?pressure_atm}; steady_rtol=${10:?rtol}; steady_atol=${11:?atol}
    [[ $stage =~ ^[1-5]$ ]] || exit 2
    [[ $pressure =~ ^[0-9]+([.][0-9]+)?$ ]] || exit 2
    [[ $steady_rtol =~ ^[0-9.eE+-]+$ && $steady_atol =~ ^[0-9.eE+-]+$ ]] || exit 2
    [[ $variant =~ ^(full|(dense-increment|bounded-takahashi|pressure-chemistry|fine-grid|smoothed-alpha|takahashi-table2|takahashi-high-t|takahashi-bulk|mass-gradient|total-enthalpy|pure-species-flux|soret|manual-soret|conservative-species)(,(dense-increment|bounded-takahashi|pressure-chemistry|fine-grid|smoothed-alpha|takahashi-table2|takahashi-high-t|takahashi-bulk|mass-gradient|total-enthalpy|pure-species-flux|soret|manual-soret|conservative-species))*)$ ]] || exit 2
    ;;
esac

log=$run/batch.log
mkdir -p "$run"
: > "$log"
log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >> "$log"; }

log "job-batch start mode=$mode host=$(hostname) slurm=${SLURM_JOB_ID:-unset}"
log "module=$module inputs=$inputs sdk=$sdk compiler=$compiler"

# ---- frozen identities ---------------------------------------------------
if [ -f "$run/module.sha256" ]; then
    (cd "$module" && sha256sum -c --quiet "$run/module.sha256") >> "$log" 2>&1 || {
        log "MODULE MISMATCH - refusing to build or solve"
        printf 'FAILED module-mismatch\n' > "$run/status.txt"; exit 1; }
    log "module hashes ok ($(wc -l < "$run/module.sha256") files)"
else
    log "no module.sha256 supplied; recording the tree this job actually used"
    (cd "$module" && sha256sum *.h *.cpp) > "$run/module-observed.sha256"
fi
if [ -f "$run/inputs.sha256" ]; then
    (cd "$inputs" && sha256sum -c --quiet "$run/inputs.sha256") >> "$log" 2>&1 || {
        log "INPUT MISMATCH - refusing to run"
        printf 'FAILED input-mismatch\n' > "$run/status.txt"; exit 1; }
    log "input hashes ok"
else
    (cd "$inputs" && sha256sum ./*) > "$run/inputs-observed.sha256"
fi

export HOME="$run/home" TMPDIR="$run/tmp" XDG_CACHE_HOME="$run/cache"
mkdir -p "$HOME" "$TMPDIR" "$XDG_CACHE_HOME"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export LD_LIBRARY_PATH="$sdk/lib:${LD_LIBRARY_PATH:-}"
export CANTERA_DATA="$sdk/share/cantera/data"
export PKG_CONFIG_PATH="$sdk/lib/pkgconfig"
printf 'cpus=%s memory_MiB=%s\n' "${SLURM_CPUS_PER_TASK:-unknown}" "${SLURM_MEM_PER_NODE:-unknown}" > "$run/resources.txt"

# ---- compiler flags ------------------------------------------------------
if [ -x "$sdk/bin/pkg-config" ]; then pkgconfig="$sdk/bin/pkg-config"; else pkgconfig=$(command -v pkg-config); fi
log "pkg-config $pkgconfig"
flags=$($pkgconfig --define-variable=prefix="$sdk" --cflags --libs cantera)
printf '%s\n' "$flags" > "$run/compiler-flags.txt"
"$compiler" --version > "$run/compiler.txt" 2>&1
log "compiler $("$compiler" --version 2>&1 | head -1)"

# The OF8 image in this campaign cannot see sys/cdefs.h through its inherited include
# path; the registry lists -isystem /usr/include/x86_64-linux-gnu and
# -B/usr/lib/x86_64-linux-gnu for this image. Probe both configurations on one file and
# use the first that links, recording which one ran.
printf '#include <cstdint>\n#include <cstdio>\nint main(){std::uint32_t v=1;std::printf("%%u\\n",v);return 0;}\n' > "$run/probe.cpp"
config=base
if ! "$compiler" -std=c++17 "$run/probe.cpp" -o "$run/probe" >> "$run/probe-attempts.txt" 2>&1; then
    echo "base FAILED" >> "$run/probe-attempts.txt"
    config=registry
    if ! "$compiler" -std=c++17 -isystem /usr/include/x86_64-linux-gnu \
            -B/usr/lib/x86_64-linux-gnu/ "$run/probe.cpp" -o "$run/probe" >> "$run/probe-attempts.txt" 2>&1; then
        echo "registry FAILED" >> "$run/probe-attempts.txt"
        log "no compile configuration links a trivial program; see probe-attempts.txt"
        printf 'FAILED toolchain-headers\n' > "$run/status.txt"; exit 1
    fi
else
    echo "base OK" >> "$run/probe-attempts.txt"
fi
if [ "$config" = registry ]; then
    flags="$flags -isystem /usr/include/x86_64-linux-gnu -B/usr/lib/x86_64-linux-gnu/"
fi
printf '%s\n' "$config" > "$run/compile-config.txt"
log "compile configuration $config"

if [ "$mode" = build ]; then
    # Same sequence and same negative controls as job.sh: a control that starts
    # passing is an error, so `if <control>; then exit 1; fi`.
    unset CPLUS_INCLUDE_PATH C_INCLUDE_PATH CPATH LIBRARY_PATH
    "$compiler" -std=c++17 -O2 -D_GLIBCXX_USE_CXX11_ABI=1 "$module/test_srk.cpp" -o "$run/test-srk" > "$run/compile-srk.log" 2>&1
    "$run/test-srk" > "$run/kernel-check.txt"
    "$compiler" -std=c++17 -O2 "$module/test_alpha.cpp" -o "$run/test-alpha" > "$run/compile-alpha.log" 2>&1
    "$run/test-alpha" > "$run/alpha-check.txt"
    "$compiler" -std=c++17 -O2 "$module/test_takahashi.cpp" $flags -Wl,-rpath,"$sdk/lib" -o "$run/test-takahashi" > "$run/compile-takahashi.log" 2>&1
    "$run/test-takahashi" > "$run/takahashi-check.txt"
    if "$run/test-takahashi" legacy > "$run/takahashi-legacy-control.txt"; then
        log "NEGATIVE CONTROL PASSED: takahashi legacy control must fail"; printf 'FAILED legacy-control\n' > "$run/status.txt"; exit 1; fi
    if "$run/test-alpha" legacy > "$run/alpha-legacy-control.txt"; then
        log "NEGATIVE CONTROL PASSED: alpha legacy control must fail"; printf 'FAILED alpha-control\n' > "$run/status.txt"; exit 1; fi
    "$compiler" -std=c++17 -O2 -D_GLIBCXX_USE_CXX11_ABI=1 "$module/test_soret.cpp" \
        $flags -Wl,-rpath,"$sdk/lib" -o "$run/test-soret" > "$run/compile-soret.log" 2>&1
    "$run/test-soret" "$inputs" "$inputs/guess.csv" > "$run/soret-check.txt"
    "$compiler" -std=c++17 -O2 -D_GLIBCXX_USE_CXX11_ABI=1 "$module/test_conservative.cpp" \
        $flags -Wl,-rpath,"$sdk/lib" -o "$run/test-conservative" > "$run/compile-conservative.log" 2>&1
    "$run/test-conservative" "$inputs/ideal.yaml" > "$run/conservative-check.txt"
    "$compiler" -std=c++17 -O2 -D_GLIBCXX_USE_CXX11_ABI=1 "$module/flame.cpp" \
        $flags -Wl,-rpath,"$sdk/lib" -o "$run/liang-flame" > "$run/compile-flame.log" 2>&1
    "$compiler" -std=c++17 -O2 -D_GLIBCXX_USE_CXX11_ABI=1 "$module/model_probe.cpp" \
        $flags -Wl,-rpath,"$sdk/lib" -o "$run/model-probe" > "$run/compile-probe.log" 2>&1
    (cd "$run" && sha256sum liang-flame > binary.sha256 && sha256sum model-probe > probe-binary.sha256)
    ldd "$run/liang-flame" > "$run/dependencies.txt" 2>&1 || log "ldd rc non-zero"
    : > "$run/build-passed.txt"
    printf 'BUILT compile_config=%s\n' "$config" > "$run/status.txt"
    log "build done: $(cat "$run/binary.sha256")"
    exit 0
fi

# ---- case ---------------------------------------------------------------
test -f "$build/build-passed.txt"
test -f "$build/binary.sha256"
(cd "$build" && sha256sum -c --quiet binary.sha256) >> "$log" 2>&1
sha256sum "$inputs"/* > "$run/input-sha256.txt"
cp "$build/binary.sha256" "$run/executable.sha256"
printf '%q ' "$build/liang-flame" "$inputs" "$stage" "$phi" "$run/result" "$variant" "$pressure" "$steady_rtol" "$steady_atol" > "$run/command.txt"
printf '\n' >> "$run/command.txt"
start=$(date +%s)
rc=0
"$build/liang-flame" "$inputs" "$stage" "$phi" "$run/result" "$variant" "$pressure" \
    "$steady_rtol" "$steady_atol" > "$run/flame.log" 2>&1 || rc=$?
end=$(date +%s)
log "flame exit=$rc elapsed=$((end-start))s"
printf 'CASE rc=%s stage=%s phi=%s variant=%s pressure_atm=%s\n' "$rc" "$stage" "$phi" "$variant" "$pressure" > "$run/status.txt"
tail -5 "$run/flame.log" >> "$log" 2>&1 || true
exit "$rc"
