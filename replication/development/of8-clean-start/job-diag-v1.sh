#!/bin/bash
# Smallest clean-start diagnostic on the executable built by job of8-build-v5.
#
# The owner's next action after the build is a diagnostic that can *fail on physics*
# rather than on packaging: energy, temperature inversion and conservation on a case that
# starts at time 0 with no intermediate field carried in from anywhere. This wrapper does
# exactly one bounded thing and then measures it:
#
#   * mesh      the frozen 1-D slab, blockMesh + checkMesh, no solver input edited;
#   * startup   the case exactly as frozen (startTime 0, startFrom startTime, deltaT
#               fixed at 1e-10, chemistry on, seulex), 1000 steps to 1e-7 s, five writes
#               at 2e-8 s intervals;
#   * measure   `metrics.py`, which reads only the solver's own saved fields and the
#               committed JANAF table and reports (a) the residual between the stored
#               temperature and the temperature recovered from the stored sensible
#               enthalpy - a temperature inversion shows up here as a residual at the
#               round-trip level, (b) species positivity and the ideal-gas density
#               closure, and (c) total mass and total sensible energy at every write.
#
# Nothing here claims a flame speed, a converged flame or an accepted case. A nonzero
# solver exit, an inversion residual above the round-trip floor, a negative mass fraction
# or a drifting total mass/energy is the *result*; the wrapper records it and exits with
# the solver's status so a failure is never read as a missing run.
#
# Usage: job-diag-v1.sh [BUILD]   (defaults to runs/of8-build-v5)
set -uo pipefail
RUN=/workspace/forge-out/runs/of8-diag-v1
BUILD=${1:-/workspace/forge-out/runs/of8-build-v5}
SRC=/workspace/forge-out/runs/of8-case-v1/case
MODULE=${MODULE:-/workspace/science/replication/development/of8-clean-start}
LOG="$RUN/diag.log"
SOLVE_BUDGET=${SOLVE_BUDGET:-3600}
START=$(date +%s)

mkdir -p "$RUN" || exit 1
: > "$LOG"
log() { echo "$@" >> "$LOG"; date -u +%Y-%m-%dT%H:%M:%SZ >> "$LOG"; }
trap 'rc=$?; echo "trap rc=$rc elapsed=$(( $(date +%s) - START ))s" >> "'"$LOG"'"; printf "%s\n" "$rc" > "'"$RUN"'/rc.txt"; exit $rc' EXIT

log "diag wrapper v1 start"
log "host $(hostname) slurm_job ${SLURM_JOB_ID:-unset} build=$BUILD solve_budget=$SOLVE_BUDGET"

# ---- the executable must be the one that was built and identified ----------
status=$(cat "$BUILD/status.txt" 2>/dev/null || echo missing)
log "build status [$status]"
case "$status" in
    BUILT*) log "build accepted" ;;
    *) log "build is not BUILT - refusing to run"
       printf 'FAILED build-not-built status=%s\n' "$status" > "$RUN/status.txt"; exit 1 ;;
esac
if ! ( cd "$BUILD" && sha256sum -c exe.sha256 && sha256sum -c libs.sha256 ) > "$RUN/build-verify.txt" 2>&1; then
    log "built artefacts do not match their recorded hashes"
    printf 'FAILED build-artefact-mismatch\n' > "$RUN/status.txt"; exit 1
fi
cp "$BUILD/exe.sha256" "$RUN/solver.sha256"
cp "$BUILD/libs.sha256" "$RUN/libs.sha256"
cp "$BUILD/compile-config.txt" "$RUN/compile-config.txt" 2>/dev/null || true
log "solver $(cat "$RUN/solver.sha256")"
log "libraries verified $(wc -l < "$RUN/libs.sha256")"

# ---- the case is used unmodified; its bytes are frozen next to the result ---
rm -rf "$RUN/case"
cp -a "$SRC" "$RUN/case" || { log "case copy failed"; printf 'FAILED case-copy\n' > "$RUN/status.txt"; exit 1; }
( cd "$RUN/case" && find 0 constant system -type f -print0 | sort -z | xargs -0 sha256sum ) > "$RUN/inputs.sha256"
cp "$RUN/inputs.sha256" "$RUN/frozen-inputs.sha256"
log "input file hashes $(wc -l < "$RUN/inputs.sha256")"
grep -E '^(startTime|startFrom|endTime|deltaT|writeInterval|writeControl|adjustTimeStep|application)' \
    "$RUN/case/system/controlDict" >> "$LOG" 2>&1 || log "controlDict keys not found"

# ---- environment: only the freshly built tree, nothing inherited -----------
export LD_LIBRARY_PATH="$BUILD/lib:${LD_LIBRARY_PATH:-}"
export PATH="$BUILD/bin:${PATH:-}"
export OMP_NUM_THREADS=1
log "LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
log "which realFluidReactingFoam $(command -v realFluidReactingFoam)"

step=blockmesh
if blockMesh -case "$RUN/case" > "$RUN/blockmesh.log" 2>&1; then rc_mesh=0; else rc_mesh=$?; fi
grep -E "^    nCells|^    nPoints" "$RUN/blockmesh.log" >> "$LOG" 2>/dev/null || true
if [ "$rc_mesh" -ne 0 ]; then
    log "blockMesh FAILED rc=$rc_mesh, tail:"
    tail -20 "$RUN/blockmesh.log" >> "$LOG"
    printf 'FAILED blockMesh rc=%s\n' "$rc_mesh" > "$RUN/status.txt"; exit "$rc_mesh"
fi
step=checkmesh
if checkMesh -case "$RUN/case" > "$RUN/checkmesh.log" 2>&1; then rc_check=0; else rc_check=$?; fi
grep -E "Mesh OK|Failed|cells:" "$RUN/checkmesh.log" | head -6 >> "$LOG" 2>/dev/null || true
log "checkMesh rc=$rc_check"

# ---- one bounded clean-start solve ----------------------------------------
step=solve
log "solver start (startTime 0, 1000 fixed 1e-10 s steps, serial)"
start=$(date +%s)
"$BUILD/bin/realFluidReactingFoam" -case "$RUN/case" > "$RUN/solver.log" 2>&1 &
pid=$!
# Clean stop: at the budget the case is asked to finish at the last written time so the
# run ends on a saved field instead of being killed in the middle of a write.
(
    sleep "$SOLVE_BUDGET"
    if kill -0 "$pid" 2>/dev/null; then
        last=$(grep -oE '^Time = [0-9.eE+-]+' "$RUN/solver.log" | tail -1 | sed 's/^Time = //')
        if [ -n "$last" ]; then
            sed -i "s/^endTime .*/endTime $last;/" "$RUN/case/system/controlDict"
            echo "watchdog: endTime set to last written time $last" >> "$LOG"
        else
            echo "watchdog: no written time yet" >> "$LOG"
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
log "End marker present $(grep -c '^End$' "$RUN/solver.log" || true)"
if [ "$rc_solve" -ne 0 ]; then
    log "solver nonzero, tail:"
    tail -40 "$RUN/solver.log" >> "$LOG"
fi
( cd "$RUN/case" && for d in $(ls -d [0-9]* 2>/dev/null); do echo "== $d"; \
    find "$d" -type f -print0 | sort -z | xargs -0 sha256sum; done ) > "$RUN/fields.sha256" 2>>"$LOG"
log "written time dirs: $(cd "$RUN/case" && ls -d [0-9]* 2>/dev/null | tr '\n' ' ')"

# ---- measure the saved fields --------------------------------------------
writes=$(cd "$RUN/case" && ls -d [0-9]* 2>/dev/null | grep -v '^0$' | sort -g | tr '\n' ',' | sed 's/,$//')
log "measuring write times [$writes]"
step=metrics
if [ -n "$writes" ]; then
    python3 -B "$MODULE/metrics.py" --case "$RUN/case" --times "$writes" --out "$RUN/metrics.json" \
        > "$RUN/metrics.stdout" 2>&1 && rc_metrics=0 || rc_metrics=$?
else
    rc_metrics=2
    log "no written fields beyond 0 - nothing to measure"
    : > "$RUN/metrics.stdout"
fi
log "metrics rc=$rc_metrics"
if [ "$rc_metrics" -ne 0 ]; then
    tail -20 "$RUN/metrics.stdout" >> "$LOG"
fi

# Test the metric module itself in the same allocation: a diagnostic whose checker is
# broken reports a clean run for a dirty one.
step=metrics-selftest
python3 -B -m unittest discover -s "$MODULE" -p 'test_metrics.py' -t "$MODULE" \
    > "$RUN/metrics-selftest.log" 2>&1 && rc_self=0 || rc_self=$?
log "metrics self-test rc=$rc_self $(grep -E '^OK|FAILED|Ran ' "$RUN/metrics-selftest.log" | tr '\n' ' ')"

printf 'RAN rc_solve=%s rc_metrics=%s rc_selftest=%s writes=%s total=%ss\n' \
    "$rc_solve" "$rc_metrics" "$rc_self" "${writes:-none}" "$(( $(date +%s) - START ))" > "$RUN/status.txt"
log "diag wrapper done"
tail -50 "$LOG"
[ "$rc_solve" -eq 0 ]
