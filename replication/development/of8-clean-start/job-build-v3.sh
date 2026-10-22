#!/bin/sh
# Third attempt at the exact-source OF8 build (job of8-build-v3).
#
# Attempt 1 (124204321-ish job 125204321) and attempt 2 (125205324) both died on
#   /usr/include/features.h:461: fatal error: sys/cdefs.h: No such file or directory
# because /opt/gcc-11.2.0 is an upstream gcc that does not search the Debian
# multiarch header directory /usr/include/x86_64-linux-gnu where this glibc keeps
# sys/cdefs.h.
#
# Attempt 2 also carried a *measurement defect of its own*: its `default` probe ran
#   env true g++ -std=c++11 -O2 -c probe/t.cpp ...
# i.e. it executed `true` with extra arguments instead of the compiler, so `default`
# was recorded OK without compiling anything and was then chosen first, which
# bypassed every configuration that could have worked.  This wrapper fixes the probe
# and makes it faithful: the probe translation unit now includes an OF8 public header
# (`bool.H`) with the same -D/-I flags wmake uses, which is exactly the include chain
# that failed in the real build.
#
# Configurations are tried in the order the registry documents for this image
# (-isystem /usr/include/x86_64-linux-gnu, -L/usr/lib/x86_64-linux-gnu -B/...), and if
# none compiles the probe the payload stops with FAILED toolchain-headers instead of
# spending the allocation on a build that cannot start.
RUN=/workspace/forge-out/runs/of8-build-v3
IN=/workspace/forge-out/inputs/of8-build-v1
LOG="$RUN/build.log"
mkdir -p "$RUN/lib" "$RUN/bin" "$RUN/probe" "$RUN/toolchain" || exit 1
: > "$LOG"
log() { echo "$@" >> "$LOG"; date -u +%Y-%m-%dT%H:%M:%SZ >> "$LOG"; }
trap 'rc=$?; echo "trap rc=$rc at $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "'"$LOG"'"; printf "%s\n" "$rc" > "'"$RUN"'/rc.txt"; exit $rc' EXIT

log "build wrapper v3 start"
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
for name in C_INCLUDE_PATH CPLUS_INCLUDE_PATH CPATH LIBRARY_PATH; do
    eval "value=\${$name:-unset}"
    log "env $name=$value"
done
for candidate in /usr/include/x86_64-linux-gnu /usr/include/x86_64-linux-gnu/sys/cdefs.h \
                 /usr/include/sys/cdefs.h /usr/lib/x86_64-linux-gnu /opt/gcc-11.2.0/include; do
    if [ -e "$candidate" ]; then log "exists $candidate"; else log "absent $candidate"; fi
done
log "gxx default includes:"
echo '' | g++ -E -x c++ -v - >> "$LOG" 2>&1 || true

# ---- faithful probe: an OF8 public header with the wmake flags -----------
# bool.H pulls <cstdint> -> c++config -> os_defines -> features.h -> sys/cdefs.h,
# which is the include chain the real build failed on.
printf '#include <cstdint>\n#include <cstdio>\n#include "bool.H"\nint main(){return 0;}\n' > "$RUN/probe/t.cpp"
cat > "$RUN/toolchain/g++" <<'WRAP'
#!/bin/sh
# Registry-qualified flags for this image: the upstream gcc at /opt needs the Debian
# multiarch header and library directories named explicitly.
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
# probe_with [VAR=VAL ...] -- compiles the faithful probe with the given environment
probe_with() {
    if [ "$#" -gt 0 ]; then
        if env "$@" g++ $PROBE_FLAGS -c "$RUN/probe/t.cpp" -o "$RUN/probe/t.o" >> "$RUN/probe/attempts.txt" 2>&1; then
            return 0
        fi
        return 1
    fi
    if g++ $PROBE_FLAGS -c "$RUN/probe/t.cpp" -o "$RUN/probe/t.o" >> "$RUN/probe/attempts.txt" 2>&1; then
        return 0
    fi
    return 1
}
try_config() {
    label=$1; shift
    echo "--- $label" >> "$RUN/probe/attempts.txt"
    if probe_with "$@"; then
        echo "$label OK" >> "$RUN/probe/attempts.txt"
        if [ -z "$chosen" ]; then chosen="$label"; fi
        return 0
    fi
    echo "$label FAILED" >> "$RUN/probe/attempts.txt"
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

log "probe attempts (faithful probe: OF8 bool.H + wmake flags):"
cat "$RUN/probe/attempts.txt" >> "$LOG"
log "chosen configuration [$chosen]"
if [ -z "$chosen" ]; then
    log "no compile configuration resolves the system headers; the image cannot host the build"
    printf 'FAILED toolchain-headers\n' > "$RUN/status.txt"
    exit 1
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
printf 'chosen %s\ngxx %s\nPATH %s\nCPLUS_INCLUDE_PATH %s\nCPATH %s\n' \
    "$chosen" "$(command -v g++)" "${PATH:-}" "${CPLUS_INCLUDE_PATH:-unset}" "${CPATH:-unset}" \
    > "$RUN/compile-config.txt"
log "compile config: $(tr '\n' ' ' < "$RUN/compile-config.txt")"

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
    printf 'FAILED libraries rc=%s config=%s\n' "$rc_lib" "$chosen" > "$RUN/status.txt"
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
    printf 'FAILED solver rc=%s config=%s\n' "$rc_exe" "$chosen" > "$RUN/status.txt"
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
    printf 'FAILED no-executable config=%s\n' "$chosen" > "$RUN/status.txt"
    exit 1
fi
log "build wrapper v3 done"
tail -80 "$LOG"
