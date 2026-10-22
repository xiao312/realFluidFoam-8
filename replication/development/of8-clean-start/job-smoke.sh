#!/bin/sh
# 100 ns original-time-zero startup of the liang-8a Case1 ideal methane/air case
# with the executable built from exact source b778d884 in this trial (job of8-build-v1).
# Bounded startup evidence only: no flame-speed or convergence claim.
# The adapter prepends "#!/usr/bin/env bash" and "set -euo pipefail".
RUN=/workspace/forge-out/runs/of8-smoke-v1
BUILD=/workspace/forge-out/runs/of8-build-v1
SRC=/workspace/forge-out/runs/of8-case-v1/case
LOG="$RUN/smoke.log"
mkdir -p "$RUN" || exit 1
: > "$LOG"
log() { echo "$@" >> "$LOG"; date -u +%Y-%m-%dT%H:%M:%SZ >> "$LOG"; }
trap 'rc=$?; echo "trap rc=$rc at $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "'"$LOG"'"; printf "%s\n" "$rc" > "'"$RUN"'/rc.txt"; exit $rc' EXIT

log "smoke wrapper start"
log "host $(hostname) slurm_job ${SLURM_JOB_ID:-unset} args [${*:-}]"

status=$(cat "$BUILD/status.txt" 2>/dev/null || echo missing)
log "build status [$status]"
if [ "$status" != "BUILT" ]; then
    log "build not BUILT - refusing to run"
    printf 'FAILED build-not-built\n' > "$RUN/status.txt"
    exit 1
fi
( cd "$BUILD" && sha256sum -c exe.sha256 && sha256sum -c libs.sha256 ) > "$RUN/build-verify.txt" 2>&1
log "build artifact verify rc=0 lines=$(wc -l < "$RUN/build-verify.txt")"

rm -rf "$RUN/case"
cp -a "$SRC" "$RUN/case"
( cd "$RUN/case" && find 0 constant system -type f -print0 | sort -z | xargs -0 sha256sum ) > "$RUN/inputs.sha256"
log "input file hashes $(wc -l < "$RUN/inputs.sha256")"

export LD_LIBRARY_PATH="$BUILD/lib:${LD_LIBRARY_PATH:-}"
export PATH="$BUILD/bin:${PATH:-}"
log "LD_LIBRARY_PATH=$LD_LIBRARY_PATH"

blockMesh -case "$RUN/case" > "$RUN/blockmesh.log" 2>&1
log "blockMesh rc=0 cells recorded below"
grep -E "^    nCells" "$RUN/blockmesh.log" >> "$LOG" 2>/dev/null || true
if checkMesh -case "$RUN/case" > "$RUN/checkmesh.log" 2>&1; then rc_mesh=0; else rc_mesh=$?; fi
log "checkMesh rc=$rc_mesh"
grep -E "Mesh OK|Failed|cells:" "$RUN/checkmesh.log" | head -6 >> "$LOG" 2>/dev/null || true
if [ "$rc_mesh" -ne 0 ]; then
    log "checkMesh nonzero, tail:"
    tail -20 "$RUN/checkmesh.log" >> "$LOG"
fi

log "solver start (100 ns target, deltaT 1e-10, 1000 steps, serial)"
start=$(date +%s)
"$BUILD/bin/realFluidReactingFoam" -case "$RUN/case" > "$RUN/solver.log" 2>&1 &
pid=$!
# Clean-stop watchdog: after 5400 s ask the solver to stop at its last written time
# instead of being killed mid-write by the allocation wall.
(
    sleep 5400
    if kill -0 "$pid" 2>/dev/null; then
        last=$(grep -oE '^Time = [0-9.eE+-]+' "$RUN/solver.log" | tail -1 | sed 's/^Time = //')
        if [ -n "$last" ]; then
            sed -i "s/^endTime .*/endTime $last;/" "$RUN/case/system/controlDict"
            echo "watchdog: endTime set to last written time $last at $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$LOG"
        else
            echo "watchdog: no written time found" >> "$LOG"
        fi
    fi
) &
watcher=$!
if wait "$pid"; then rc_solve=0; else rc_solve=$?; fi
end=$(date +%s)
kill "$watcher" 2>/dev/null || true
log "solver end rc=$rc_solve elapsed=$((end-start))s"
log "steps recorded $(grep -c '^Time = ' "$RUN/solver.log" || true)"
log "last times: $(grep -oE '^Time = [0-9.eE+-]+' "$RUN/solver.log" | tail -3 | tr '\n' ' ')"
log "execution lines: $(grep -E 'ExecutionTime|ClockTime' "$RUN/solver.log" | tail -2 | tr '\n' ' ')"
log "End marker present: $(grep -c '^End$' "$RUN/solver.log" || true)"
if [ "$rc_solve" -ne 0 ]; then
    log "solver tail:"
    tail -30 "$RUN/solver.log" >> "$LOG"
fi

( cd "$RUN/case" && for d in $(ls -d [0-9]* 2>/dev/null); do echo "== $d"; find "$d" -type f -print0 | sort -z | xargs -0 sha256sum; done ) > "$RUN/fields.sha256" 2>>"$LOG"
log "written time dirs: $(cd "$RUN/case" && ls -d [0-9]* 2>/dev/null | tr '\n' ' ')"
log "field hash lines $(wc -l < "$RUN/fields.sha256")"
if [ -f "$RUN/case/flame-speed.csv" ]; then
    sha256sum "$RUN/case/flame-speed.csv" >> "$LOG"
    log "flame-speed rows $(wc -l < "$RUN/case/flame-speed.csv")"
else
    log "no flame-speed.csv (solver carries no in-situ diagnostics in this repo)"
fi
printf 'RAN rc=%s\n' "$rc_solve" > "$RUN/status.txt"
log "smoke wrapper done"
tail -60 "$LOG"
