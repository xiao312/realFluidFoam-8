#!/bin/sh
# Exact-source OF8 build of realFluidReactingFoam (registered profile 9c72ecb7),
# one rank, for the liang-8a Case1 ideal methane/air clean-start diagnostic.
# The adapter prepends "#!/usr/bin/env bash" and "set -euo pipefail"; every stage
# below is guarded so an expected non-zero status cannot silently pass.
RUN=/workspace/forge-out/runs/of8-build-v1
IN=/workspace/forge-out/inputs/of8-build-v1
LOG="$RUN/build.log"
mkdir -p "$RUN/lib" "$RUN/bin" || exit 1
: > "$LOG"
log() { echo "$@" >> "$LOG"; date -u +%Y-%m-%dT%H:%M:%SZ >> "$LOG"; }
trap 'rc=$?; echo "trap rc=$rc at $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "'"$LOG"'"; printf "%s\n" "$rc" > "'"$RUN"'/rc.txt"; exit $rc' EXIT

log "build wrapper start"
log "host $(hostname) slurm_job ${SLURM_JOB_ID:-unset} pwd $(pwd) args [${*:-}]"
log "shellopts [${SHELLOPTS:-}]"

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
log "extract ok, members $(find "$RUN/src-tree" -type f | wc -l)"

cd "$RUN/src-tree" || exit 1
find . -type f -print0 | sort -z | xargs -0 sha256sum > "$RUN/members.sha256" 2>>"$LOG"
log "member hash lines $(wc -l < "$RUN/members.sha256")"

if [ -z "${WM_PROJECT_DIR:-}" ] || ! command -v wmake >/dev/null 2>&1; then
    log "wmake or WM_PROJECT_DIR missing; searching bounded candidate etc/bashrc paths"
    found=""
    for cand in /opt/openfoam8/etc/bashrc /usr/lib/openfoam/openfoam8/etc/bashrc /opt/openfoam*/etc/bashrc /usr/lib/openfoam/*/etc/bashrc "$HOME"/OpenFOAM/*/etc/bashrc; do
        if [ -f "$cand" ]; then found="$cand"; break; fi
    done
    log "bashrc candidate [$found]"
    if [ -n "$found" ]; then
        # shellcheck disable=SC1090
        . "$found" || log "sourcing $found failed"
    fi
else
    log "wmake present on PATH: $(command -v wmake)"
fi
log "WM_PROJECT_DIR=${WM_PROJECT_DIR:-unset} WM_PROJECT_VERSION=${WM_PROJECT_VERSION:-unset}"
log "gxx $(g++ --version 2>&1 | head -1)"
log "cpus $(nproc 2>/dev/null || echo unknown)"
log "disk $(df -k /workspace 2>&1 | tail -1)"

LIB_rfFoam8_SRC="$RUN/src-tree/src"
FOAM_USER_LIBBIN="$RUN/lib"
FOAM_USER_APPBIN="$RUN/bin"
export LIB_rfFoam8_SRC FOAM_USER_LIBBIN FOAM_USER_APPBIN
log "LIB_rfFoam8_SRC=$LIB_rfFoam8_SRC"
log "FOAM_USER_LIBBIN=$FOAM_USER_LIBBIN FOAM_USER_APPBIN=$FOAM_USER_APPBIN"

log "solver Make/files+options hashes:"
sha256sum applications/solvers/realFluidReactingFoam/Make/files \
         applications/solvers/realFluidReactingFoam/Make/options >> "$LOG" 2>&1 || log "make files missing"

for probe in -show-cxx -show-compile -show-link; do
    out=$(wmake $probe 2>&1 || true)
    log "wmake $probe -> $out"
done

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
    log "ldd start"
    ldd "$RUN/bin/realFluidReactingFoam" >> "$RUN/ldd.txt" 2>&1 || log "ldd rc non-zero"
    log "ldd lines $(wc -l < "$RUN/ldd.txt")"
    printf 'BUILT\n' > "$RUN/status.txt"
else
    log "no executable at $RUN/bin/realFluidReactingFoam"
    printf 'FAILED no-executable\n' > "$RUN/status.txt"
    exit 1
fi
log "build wrapper done"
cat "$LOG"
