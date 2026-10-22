#!/bin/sh
# Second attempt at the exact-source OF8 build (job of8-build-v2).
# Attempt 1 (job 125204321) failed on the very first translation unit:
#   /usr/include/features.h:461: fatal error: sys/cdefs.h: No such file or directory
# i.e. the image compiler (/opt/gcc-11.2.0) does not add the Debian multiarch
# header directory that this glibc install uses. Before spending the allocation on
# a build this payload diagnoses the toolchain, proves a working compile
# configuration with a one-file test, and only then builds. A missing header is
# reported as the measured blocker instead of being retried blind.
RUN=/workspace/forge-out/runs/of8-build-v2
IN=/workspace/forge-out/inputs/of8-build-v1
LOG="$RUN/build.log"
mkdir -p "$RUN/lib" "$RUN/bin" "$RUN/probe" || exit 1
: > "$LOG"
log() { echo "$@" >> "$LOG"; date -u +%Y-%m-%dT%H:%M:%SZ >> "$LOG"; }
trap 'rc=$?; echo "trap rc=$rc at $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "'"$LOG"'"; printf "%s\n" "$rc" > "'"$RUN"'/rc.txt"; exit $rc' EXIT

log "build wrapper v2 start"
log "host $(hostname) slurm_job ${SLURM_JOB_ID:-unset} args [${*:-}]"

want=$(sed -n 's/.*"archive_sha256": "\([0-9a-f]*\)".*/\1/p' "$IN/snapshot.json")
got=$(sha256sum "$IN/src.tar.gz"); got=${got%% *}
log "archive sha256 $got expected $want"
if [ "$want" != "$got" ]; then
    log "FROZEN SOURCE MISMATCH - refusing to build"
    printf 'FAILED\n' > "$RUN/status.txt"
    exit 1
fi
cp "$IN/snapshot.json" "$RUN/snapshot.json"
rm -rf "$RUN/src-tree"
tar -xf "$IN/src.tar.gz" -C "$RUN"
find "$RUN/src-tree" -type f -print0 | sort -z | xargs -0 sha256sum > "$RUN/members.sha256" 2>>"$LOG"
log "extract ok, member hash lines $(wc -l < "$RUN/members.sha256")"

cd "$RUN/src-tree" || exit 1
log "WM_PROJECT_DIR=${WM_PROJECT_DIR:-unset} WM_PROJECT_VERSION=${WM_PROJECT_VERSION:-unset}"
sha256sum applications/solvers/realFluidReactingFoam/Make/files \
         applications/solvers/realFluidReactingFoam/Make/options >> "$LOG" 2>&1 || log "make files missing"

# ---- toolchain diagnosis -------------------------------------------------
log "gxx $(g++ --version 2>&1 | head -1)"
log "gxx dumpmachine $(g++ -dumpmachine 2>&1)"
log "gxx where $(command -v g++)"
for name in C_INCLUDE_PATH CPLUS_INCLUDE_PATH CPATH CPATH LIBRARY_PATH; do
    eval "value=\${$name:-unset}"
    log "env $name=$value"
done
for candidate in /usr/include/x86_64-linux-gnu /usr/include/x86_64-pc-linux-gnu \
                 /usr/include/sys /usr/include /opt/gcc-11.2.0/include \
                 /usr/include/x86_64-linux-gnu/sys; do
    if [ -e "$candidate" ]; then
        log "exists $candidate"
    else
        log "absent $candidate"
    fi
done
log "cdefs search:"
for candidate in /usr/include/x86_64-linux-gnu/sys/cdefs.h /usr/include/sys/cdefs.h \
                 /usr/local/include/sys/cdefs.h; do
    if [ -f "$candidate" ]; then log "have $candidate"; fi
done
ls -d /usr/include/*linux*/ 2>/dev/null >> "$LOG" 2>&1 || true
if [ -f "$WM_DIR/rules/linux64Gcc/c++" ]; then
    log "wmake c++ rule:"
    cat "$WM_DIR/rules/linux64Gcc/c++" >> "$LOG" 2>&1
fi
if [ -f "$WM_DIR/rules/linux64Gcc/c" ]; then
    log "wmake c rule:"
    cat "$WM_DIR/rules/linux64Gcc/c" >> "$LOG" 2>&1
fi
log "gxx search dirs:"
g++ -print-search-dirs >> "$LOG" 2>&1 || true
log "gxx default includes:"
echo '' | g++ -E -x c++ -v - >> "$LOG" 2>&1 || true
log "cdefs.h discovery (bounded):"
find /usr/include /usr/local/include -maxdepth 3 -type f -name cdefs.h > "$RUN/probe/cdefs-found.txt" 2>/dev/null || true
cat "$RUN/probe/cdefs-found.txt" >> "$LOG" 2>&1
log "alternative compilers:"
ls -l /usr/bin/g++ /usr/bin/gcc /usr/bin/c++ 2>/dev/null >> "$LOG" 2>&1 || true

# ---- find a compile configuration that resolves the system headers -------
printf '#include <cstdint>\n#include <cstdio>\nint main(){std::uint32_t v=1;std::printf("%%u\\n",v);return 0;}\n' > "$RUN/probe/t.cpp"
: > "$RUN/probe/attempts.txt"
chosen=""
try_config() {
    label=$1; shift
    if env "$@" g++ -std=c++11 -O2 -c "$RUN/probe/t.cpp" -o "$RUN/probe/t.o" >> "$RUN/probe/attempts.txt" 2>&1; then
        echo "$label OK" >> "$RUN/probe/attempts.txt"
        if [ -z "$chosen" ]; then chosen="$label"; fi
        return 0
    fi
    echo "$label FAILED" >> "$RUN/probe/attempts.txt"
    return 1
}
try_config "default" true || true
while IFS= read -r found; do
    [ -n "$found" ] || continue
    header_dir=$(dirname "$(dirname "$found")")
    log "discovered header dir $header_dir"
    try_config "discovered:$header_dir" CPLUS_INCLUDE_PATH="$header_dir" C_INCLUDE_PATH="$header_dir" || true
done < "$RUN/probe/cdefs-found.txt"
try_config "cplus-multiarch" CPLUS_INCLUDE_PATH=/usr/include/x86_64-linux-gnu || true
try_config "cpath-multiarch" CPATH=/usr/include/x86_64-linux-gnu || true
if [ -x /usr/bin/g++ ]; then
    if /usr/bin/g++ -std=c++11 -O2 -c "$RUN/probe/t.cpp" -o "$RUN/probe/t-alt.o" >> "$RUN/probe/attempts.txt" 2>&1; then
        echo "alt-compiler /usr/bin/g++ OK" >> "$RUN/probe/attempts.txt"
        if [ -z "$chosen" ]; then chosen="alt-compiler"; fi
    else
        echo "alt-compiler /usr/bin/g++ FAILED" >> "$RUN/probe/attempts.txt"
    fi
fi
log "probe attempts:"
cat "$RUN/probe/attempts.txt" >> "$LOG" 2>&1
log "chosen configuration [$chosen]"
log "compiler usable for reused objects: $(printf '#include <cstdint>\n#include <cstdio>\nint main(){return 0;}\n' > "$RUN/probe/u.cpp"; g++ -std=c++11 -c "$RUN/probe/u.cpp" -o "$RUN/probe/u.o" >/dev/null 2>&1 && echo yes || echo no)"
if [ -z "$chosen" ]; then
    log "no compile configuration resolves the system headers; the image cannot host the build"
    printf 'FAILED toolchain-headers\n' > "$RUN/status.txt"
    exit 1
fi
case "$chosen" in
    cplus-multiarch) export CPLUS_INCLUDE_PATH=/usr/include/x86_64-linux-gnu ;;
    cpath-multiarch) export CPATH=/usr/include/x86_64-linux-gnu ;;
    discovered:*) header_dir=${chosen#discovered:}
                  export CPLUS_INCLUDE_PATH="$header_dir" C_INCLUDE_PATH="$header_dir" ;;
    alt-compiler) mkdir -p "$RUN/toolchain"
                  ln -sf /usr/bin/g++ "$RUN/toolchain/g++"
                  ln -sf /usr/bin/gcc "$RUN/toolchain/gcc"
                  ln -sf /usr/bin/g++ "$RUN/toolchain/c++"
                  PATH="$RUN/toolchain:$PATH"
                  export PATH ;;
    default) ;;
esac
log "exported CPLUS_INCLUDE_PATH=${CPLUS_INCLUDE_PATH:-unset} CPATH=${CPATH:-unset} CFLAGS=${CFLAGS:-unset}"

LIB_rfFoam8_SRC="$RUN/src-tree/src"
FOAM_USER_LIBBIN="$RUN/lib"
FOAM_USER_APPBIN="$RUN/bin"
export LIB_rfFoam8_SRC FOAM_USER_LIBBIN FOAM_USER_APPBIN
log "LIB_rfFoam8_SRC=$LIB_rfFoam8_SRC FOAM_USER_LIBBIN=$FOAM_USER_LIBBIN FOAM_USER_APPBIN=$FOAM_USER_APPBIN"

start=$(date +%s)
log "library build start (src/Allwmake -j 1)"
if sh ./src/Allwmake -j 1 > "$RUN/libraries.log" 2>&1; then rc_lib=0; else rc_lib=$?; fi
end=$(date +%s)
log "library build end rc=$rc_lib elapsed=$((end-start))s"
if [ "$rc_lib" -ne 0 ]; then
    log "library build FAILED, tail:"
    tail -40 "$RUN/libraries.log" >> "$LOG"
    printf 'FAILED libraries rc=%s\n' "$rc_lib" > "$RUN/status.txt"
    exit "$rc_lib"
fi

start=$(date +%s)
log "solver build start"
if wmake applications/solvers/realFluidReactingFoam > "$RUN/solver.log" 2>&1; then rc_exe=0; else rc_exe=$?; fi
end=$(date +%s)
log "solver build end rc=$rc_exe elapsed=$((end-start))s"
if [ "$rc_exe" -ne 0 ]; then
    log "solver build FAILED, tail:"
    tail -40 "$RUN/solver.log" >> "$LOG"
    printf 'FAILED solver rc=%s\n' "$rc_exe" > "$RUN/status.txt"
    exit "$rc_exe"
fi

sha256sum "$RUN"/lib/*.so > "$RUN/libs.sha256" 2>>"$LOG" || log "no shared libraries produced"
log "produced libraries $(wc -l < "$RUN/libs.sha256" 2>/dev/null || echo 0)"
if [ -f "$RUN/bin/realFluidReactingFoam" ]; then
    sha256sum "$RUN/bin/realFluidReactingFoam" > "$RUN/exe.sha256"
    log "executable $(cat "$RUN/exe.sha256")"
    ldd "$RUN/bin/realFluidReactingFoam" >> "$RUN/ldd.txt" 2>&1 || log "ldd rc non-zero"
    log "ldd lines $(wc -l < "$RUN/ldd.txt")"
    printf 'BUILT compile_config=%s\n' "$chosen" > "$RUN/status.txt"
else
    log "no executable at $RUN/bin/realFluidReactingFoam"
    printf 'FAILED no-executable\n' > "$RUN/status.txt"
    exit 1
fi
log "build wrapper v2 done"
tail -80 "$LOG"
