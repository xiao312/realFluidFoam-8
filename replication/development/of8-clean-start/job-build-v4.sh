#!/bin/bash
# Fourth attempt at the exact-source OF8 build (job of8-build-v4): the first attempt
# intended to produce a *complete* solver, i.e. libraries AND the realFluidReactingFoam
# executable, with the compiler, library and executable hashes retained.
#
# What changed relative to job-build-v3.sh:
#   * the successful `wrapper-isystem` probe from job 125251689 is kept, and the probe
#     result is still recorded rather than assumed;
#   * the build is parallel (BUILD_JOBS, default 3) instead of `-j 1`, because 468
#     translation units serially do not fit a 7200 s wall next to the 578 s image
#     conversion and the cleanup tail;
#   * a wall budget stops the payload between the two stages instead of letting the
#     scheduler kill it with the solver half-built and no status file;
#   * compiler identity (sha256 of the compiler binaries it actually invokes, its -v
#     banner and the linker version) is retained next to the library and executable
#     hashes, so the build is identified by compiler bytes and not only by flags.
#
# Frozen inputs: /workspace/forge-out/inputs/of8-build-v4 (archive + snapshot.json,
# copied from of8-build-v1 unchanged). The archive is verified against snapshot.json
# before anything is compiled.
set -uo pipefail
RUN=/workspace/forge-out/runs/of8-build-v4
IN=/workspace/forge-out/inputs/of8-build-v4
LOG="$RUN/build.log"
BUILD_JOBS=${BUILD_JOBS:-3}
BUILD_BUDGET=${BUILD_BUDGET:-5400}
START=$(date +%s)

mkdir -p "$RUN/lib" "$RUN/bin" "$RUN/probe" "$RUN/toolchain" || exit 1
: > "$LOG"
log() { echo "$@" >> "$LOG"; date -u +%Y-%m-%dT%H:%M:%SZ >> "$LOG"; }
trap 'rc=$?; echo "trap rc=$rc elapsed=$(( $(date +%s) - START ))s at $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "'"$LOG"'"; printf "%s\n" "$rc" > "'"$RUN"'/rc.txt"; exit $rc' EXIT

log "build wrapper v4 start (parallel, complete solver, identity retained)"
log "host $(hostname) slurm_job ${SLURM_JOB_ID:-unset} BUILD_JOBS=$BUILD_JOBS BUILD_BUDGET=$BUILD_BUDGET"

# ---- frozen source -------------------------------------------------------
if [ ! -f "$IN/src.tar.gz" ] || [ ! -f "$IN/snapshot.json" ]; then
    log "frozen inputs absent under $IN"
    printf 'FAILED no-frozen-inputs\n' > "$RUN/status.txt"; exit 1
fi
want=$(sed -n 's/.*"archive_sha256": "\([0-9a-f]*\)".*/\1/p' "$IN/snapshot.json")
got=$(sha256sum "$IN/src.tar.gz"); got=${got%% *}
log "archive sha256 $got expected $want"
if [ "$want" != "$got" ]; then
    log "FROZEN SOURCE MISMATCH - refusing to build"
    printf 'FAILED source-mismatch\n' > "$RUN/status.txt"; exit 1
fi
cp "$IN/snapshot.json" "$RUN/snapshot.json"
rm -rf "$RUN/src-tree"
tar -xf "$IN/src.tar.gz" -C "$RUN" || { log "extract failed"; printf 'FAILED extract\n' > "$RUN/status.txt"; exit 1; }
find "$RUN/src-tree" -type f -print0 | sort -z | xargs -0 sha256sum > "$RUN/members.sha256" 2>>"$LOG"
log "extract ok, member hash lines $(wc -l < "$RUN/members.sha256")"

cd "$RUN/src-tree" || exit 1
log "WM_PROJECT_DIR=${WM_PROJECT_DIR:-unset} WM_PROJECT_VERSION=${WM_PROJECT_VERSION:-unset}"
log "solvers present: $(ls applications/solvers 2>/dev/null | tr '\n' ' ')"
sha256sum applications/solvers/realFluidReactingFoam/Make/files \
         applications/solvers/realFluidReactingFoam/Make/options >> "$LOG" 2>&1 \
    || log "realFluidReactingFoam make files missing"

# ---- toolchain identity --------------------------------------------------
for name in C_INCLUDE_PATH CPLUS_INCLUDE_PATH CPATH LIBRARY_PATH; do
    eval "value=\${$name:-unset}"
    log "env $name=$value"
done
{
    echo "gxx_path $(command -v g++)"
    g++ --version 2>&1 | head -3
    echo "dumpmachine $(g++ -dumpmachine 2>&1)"
    g++ -v 2>&1 | sed -n '/Configured with/,/^$/p'
    ld --version 2>&1 | head -2
    ldd --version 2>&1 | head -1
    echo "libc $(/lib/x86_64-linux-gnu/libc.so.6 2>&1 | head -1)"
} > "$RUN/toolchain-identity.txt" 2>&1
for bin in /opt/gcc-11.2.0/bin/g++ /opt/gcc-11.2.0/bin/gcc /opt/gcc-11.2.0/bin/ld \
           "$(command -v cc1plus 2>/dev/null || true)" \
           /opt/gcc-11.2.0/lib/gcc/x86_64-pc-linux-gnu/11.2.0/cc1plus; do
    if [ -n "$bin" ] && [ -e "$bin" ]; then sha256sum "$bin" >> "$RUN/compiler.sha256" 2>/dev/null; fi
done
log "compiler identity recorded: $(wc -l < "$RUN/compiler.sha256" 2>/dev/null || echo 0) binaries"

# ---- faithful probe ------------------------------------------------------
# bool.H pulls <cstdint> -> c++config -> os_defines -> features.h -> sys/cdefs.h,
# which is the include chain the first attempt died on.
printf '#include <cstdint>\n#include <cstdio>\n#include "bool.H"\nint main(){return 0;}\n' > "$RUN/probe/t.cpp"
cat > "$RUN/toolchain/g++" <<'WRAP'
#!/bin/sh
exec /opt/gcc-11.2.0/bin/g++ -isystem /usr/include/x86_64-linux-gnu -B/usr/lib/x86_64-linux-gnu/ -L/usr/lib/x86_64-linux-gnu "$@"
WRAP
cp "$RUN/toolchain/g++" "$RUN/toolchain/gcc"
cp "$RUN/toolchain/g++" "$RUN/toolchain/c++"
sed -i 's|/opt/gcc-11.2.0/bin/g++|/opt/gcc-11.2.0/bin/gcc|' "$RUN/toolchain/gcc"
chmod +x "$RUN/toolchain/g++" "$RUN/toolchain/gcc" "$RUN/toolchain/c++"

PROBE_DEFS="-Dlinux64 -DWM_ARCH_OPTION=64 -DWM_DP -DWM_LABEL_SIZE=32"
PROBE_INC="-I/opt/openfoam8/src/OpenFOAM/lnInclude -I/opt/openfoam8/src/OSspecific/POSIX/lnInclude"
PROBE_FLAGS="-std=c++11 -m64 $PROBE_DEFS $PROBE_INC -fPIC -O1"

: > "$RUN/probe/attempts.txt"
chosen=""
try_config() {
    label=$1; shift
    echo "--- $label" >> "$RUN/probe/attempts.txt"
    if [ "$#" -gt 0 ]; then
        env "$@" g++ $PROBE_FLAGS -c "$RUN/probe/t.cpp" -o "$RUN/probe/t.o" >> "$RUN/probe/attempts.txt" 2>&1 && rc=0 || rc=$?
    else
        g++ $PROBE_FLAGS -c "$RUN/probe/t.cpp" -o "$RUN/probe/t.o" >> "$RUN/probe/attempts.txt" 2>&1 && rc=0 || rc=$?
    fi
    if [ "$rc" -eq 0 ]; then
        echo "$label OK" >> "$RUN/probe/attempts.txt"
        [ -z "$chosen" ] && chosen="$label"
        return 0
    fi
    echo "$label FAILED rc=$rc" >> "$RUN/probe/attempts.txt"
    return 1
}

PATH="$RUN/toolchain:$PATH"; export PATH
try_config "wrapper-isystem" || true
if [ -z "$chosen" ]; then
    PATH=${PATH#"$RUN/toolchain:"}; export PATH
    try_config "cplus-multiarch" CPLUS_INCLUDE_PATH=/usr/include/x86_64-linux-gnu || true
fi
if [ -z "$chosen" ]; then
    try_config "cpath-multiarch" CPATH=/usr/include/x86_64-linux-gnu || true
fi
if [ -z "$chosen" ]; then
    PATH="$RUN/toolchain:$PATH"; export PATH
    try_config "wrapper+cplus" CPLUS_INCLUDE_PATH=/usr/include/x86_64-linux-gnu || true
fi
if [ -z "$chosen" ]; then
    PATH=${PATH#"$RUN/toolchain:"}; export PATH
    try_config "default" || true
fi

log "probe attempts: $(grep -E 'OK$|FAILED' "$RUN/probe/attempts.txt" | tr '\n' ' ')"
log "chosen configuration [$chosen]"
if [ -z "$chosen" ]; then
    log "no compile configuration resolves the system headers"
    printf 'FAILED toolchain-headers\n' > "$RUN/status.txt"; exit 1
fi
case "$chosen" in
    wrapper-isystem|wrapper+cplus) PATH="$RUN/toolchain:$PATH"; export PATH ;;
    cplus-multiarch) export CPLUS_INCLUDE_PATH=/usr/include/x86_64-linux-gnu ;;
    cpath-multiarch) export CPATH=/usr/include/x86_64-linux-gnu ;;
    default) ;;
esac
case "$chosen" in
    wrapper+cplus) export CPLUS_INCLUDE_PATH=/usr/include/x86_64-linux-gnu ;;
esac
printf 'chosen %s\ngxx %s\ngxx_sha256 %s\nPATH %s\nCPLUS_INCLUDE_PATH %s\nCPATH %s\nBUILD_JOBS %s\n' \
    "$chosen" "$(command -v g++)" \
    "$(sha256sum "$(command -v g++)" | cut -d' ' -f1)" \
    "${PATH:-}" "${CPLUS_INCLUDE_PATH:-unset}" "${CPATH:-unset}" "$BUILD_JOBS" \
    > "$RUN/compile-config.txt"
log "compile config: $(tr '\n' ' ' < "$RUN/compile-config.txt")"

LIB_rfFoam8_SRC="$RUN/src-tree/src"
FOAM_USER_LIBBIN="$RUN/lib"
FOAM_USER_APPBIN="$RUN/bin"
export LIB_rfFoam8_SRC FOAM_USER_LIBBIN FOAM_USER_APPBIN
export OMP_NUM_THREADS=1
log "LIB_rfFoam8_SRC=$LIB_rfFoam8_SRC FOAM_USER_LIBBIN=$FOAM_USER_LIBBIN FOAM_USER_APPBIN=$FOAM_USER_APPBIN"

# ---- stage 1: libraries --------------------------------------------------
start=$(date +%s)
log "library build start (-j $BUILD_JOBS)"
sh ./src/Allwmake -j "$BUILD_JOBS" > "$RUN/libraries.log" 2>&1 && rc_lib=0 || rc_lib=$?
end=$(date +%s); lib_secs=$((end - start))
units=$(grep -c '^ *g++ ' "$RUN/libraries.log" 2>/dev/null || echo 0)
log "library build end rc=$rc_lib elapsed=${lib_secs}s compile-lines=$units"
if [ "$rc_lib" -ne 0 ]; then
    log "library build FAILED, tail:"
    tail -40 "$RUN/libraries.log" >> "$LOG"
    printf 'FAILED libraries rc=%s config=%s elapsed=%ss\n' "$rc_lib" "$chosen" "$lib_secs" > "$RUN/status.txt"
    exit "$rc_lib"
fi
sha256sum "$RUN"/lib/*.so > "$RUN/libs.sha256" 2>>"$LOG" || log "no shared libraries produced"
log "produced libraries $(wc -l < "$RUN/libs.sha256" 2>/dev/null || echo 0)"

# ---- stage 2: solver -----------------------------------------------------
elapsed=$(( $(date +%s) - START ))
remaining=$(( BUILD_BUDGET - elapsed ))
log "stage 1 took ${elapsed}s total, ${remaining}s of payload budget left"
if [ "$remaining" -lt 300 ]; then
    log "not enough budget for the solver build; stopping with the libraries in place"
    printf 'PARTIAL libraries-only config=%s budget=%ss\n' "$chosen" "$BUILD_BUDGET" > "$RUN/status.txt"
    exit 1
fi
start=$(date +%s)
log "solver build start"
wmake -j "$BUILD_JOBS" applications/solvers/realFluidReactingFoam > "$RUN/solver.log" 2>&1 && rc_exe=0 || rc_exe=$?
end=$(date +%s); exe_secs=$((end - start))
log "solver build end rc=$rc_exe elapsed=${exe_secs}s"
if [ "$rc_exe" -ne 0 ]; then
    log "solver build FAILED, tail:"
    tail -40 "$RUN/solver.log" >> "$LOG"
    printf 'FAILED solver rc=%s config=%s lib_elapsed=%ss exe_elapsed=%ss\n' "$rc_exe" "$chosen" "$lib_secs" "$exe_secs" > "$RUN/status.txt"
    exit "$rc_exe"
fi

if [ -f "$RUN/bin/realFluidReactingFoam" ]; then
    sha256sum "$RUN/bin/realFluidReactingFoam" > "$RUN/exe.sha256"
    log "executable $(cat "$RUN/exe.sha256")"
    ldd "$RUN/bin/realFluidReactingFoam" > "$RUN/ldd.txt" 2>&1 || log "ldd rc non-zero"
    log "ldd lines $(wc -l < "$RUN/ldd.txt")"
    "$RUN/bin/realFluidReactingFoam" -help > "$RUN/solver-help.txt" 2>&1 || log "solver -help rc nonzero (retained)"
    log "solver -help lines $(wc -l < "$RUN/solver-help.txt")"
    printf 'BUILT compile_config=%s lib_elapsed=%ss exe_elapsed=%ss total=%ss jobs=%s\n' \
        "$chosen" "$lib_secs" "$exe_secs" "$(( $(date +%s) - START ))" "$BUILD_JOBS" > "$RUN/status.txt"
else
    log "no executable at $RUN/bin/realFluidReactingFoam after a successful wmake"
    ls -la "$RUN/bin" >> "$LOG" 2>&1
    printf 'FAILED no-executable config=%s\n' "$chosen" > "$RUN/status.txt"
    exit 1
fi
log "build wrapper v4 done"
tail -40 "$LOG"
