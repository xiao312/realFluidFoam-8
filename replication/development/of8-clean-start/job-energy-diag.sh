#!/bin/bash
# Small, genuinely bounded clean-start energy / inversion / conservation diagnostic.
#
# Replaces the of8-diag-v1 approach (8000 cells, ~20 s per 1e-10 s step, a watchdog that
# rewrote endTime while the solver kept running, one saved field, no metrics) with two
# 32-cell cases that provably reach endTime:
#
#   caseA  chemistry off, 300 K | 1200 K step, 1000 steps to 1e-5 s, writes every 2.5e-6 s
#   caseB  chemistry on  (GRI-3.0), uniform 1500 K, 100 steps to 1e-6 s, writes every 2.5e-7 s
#
# Both are generated from committed dictionaries by prepare_energy_case.py, both start at
# startTime 0, and the wrapper never edits endTime or any solver input after generation.
# The stop is verified against the log (rc, "End" marker, last written time == endTime,
# expected number of writes) rather than assumed.
#
# Measurements: metrics.py (mass, sensible-energy integral, species positivity,
# ideal-gas density closure, temperature inversion from the stored he) and
# expected_energy.py (absolute comparison against an independent JANAF recomputation of
# the initial state, including the formation-enthalpy offset that sensibleEnthalpy drops).
#
# A nonzero solver exit, a missing write, an inversion residual above the round-trip
# floor or a drifting energy integral is the *result*; nothing here claims a flame, a
# flame speed or convergence.
set -uo pipefail
RUN=${RUN:-/workspace/forge-out/runs/of8-energy-diag-v1}
BUILD=${1:-/workspace/forge-out/runs/of8-build-v5}
MECH=${MECH:-/workspace/forge-out/runs/of8-case-v1/case/constant}
MODULE=${MODULE:-/workspace/science/replication/development/of8-clean-start}
LOG="$RUN/diag.log"
START=$(date +%s)

mkdir -p "$RUN" || exit 1
: > "$LOG"
log() { echo "$@" >> "$LOG"; date -u +%Y-%m-%dT%H:%M:%SZ >> "$LOG"; }

log "energy diagnostic v1 start"
log "host $(hostname) slurm_job ${SLURM_JOB_ID:-unset} build=$BUILD"
log "module $MODULE"

status=$(cat "$BUILD/status.txt" 2>/dev/null || echo missing)
log "build status [$status]"
case "$status" in
    BUILT*) log "build accepted" ;;
    *) printf 'FAILED build-not-built status=%s\n' "$status" > "$RUN/status.txt"; exit 1 ;;
esac
if ! ( cd "$BUILD" && sha256sum -c exe.sha256 && sha256sum -c libs.sha256 ) > "$RUN/build-verify.txt" 2>&1; then
    log "built artefacts do not match their recorded hashes"
    printf 'FAILED build-artefact-mismatch\n' > "$RUN/status.txt"; exit 1
fi
cp "$BUILD/exe.sha256" "$RUN/solver.sha256"
cp "$BUILD/libs.sha256" "$RUN/libs.sha256"
cp "$BUILD/compile-config.txt" "$RUN/compile-config.txt" 2>/dev/null || true

COMMIT=$(export PATH=/workspace/.tooling/git-2.30.2/bin:$PATH; \
         git -C /workspace/science rev-parse HEAD 2>/dev/null || echo unrecorded)
printf '%s\n' "$COMMIT" > "$RUN/source-commit.txt"
log "source commit ${COMMIT:-unrecorded}"

export LD_LIBRARY_PATH="$BUILD/lib:${LD_LIBRARY_PATH:-}"
export PATH="$BUILD/bin:${PATH:-}"
export OMP_NUM_THREADS=1
log "which realFluidReactingFoam $(command -v realFluidReactingFoam)"

overall=0
for spec in "caseA chemOff" "caseB chemOn"; do
    set -- $spec
    name=$1; variant=$2
    case_dir="$RUN/$name"
    log "== $name ($variant) =="
    rm -rf "$case_dir" "$case_dir.receipt.json"
    if ! python3 -B "$MODULE/prepare_energy_case.py" --out "$case_dir" --variant "$variant" \
            --mechanism-source "$MECH" --source-commit "$COMMIT" > "$RUN/$name.prepare.log" 2>&1; then
        log "$name: case generation FAILED"
        tail -20 "$RUN/$name.prepare.log" >> "$LOG"
        overall=1; continue
    fi
    end_time=$(grep -oE '^endTime +[0-9.eE+-]+' "$case_dir/system/controlDict" | awk '{print $2}')
    write_interval=$(grep -oE '^writeInterval +[0-9.eE+-]+' "$case_dir/system/controlDict" | awk '{print $2}')
    expected_writes=$(python3 -c "print(round($end_time/$write_interval))")
    log "$name controls endTime=$end_time writeInterval=$write_interval expected_writes=$expected_writes"

    if ! ( cd "$case_dir" && find 0 constant system -type f -print0 | sort -z | xargs -0 sha256sum ) \
            > "$RUN/$name.inputs.sha256" 2>>"$LOG"; then
        log "$name: input hashing FAILED"; overall=1; continue
    fi

    if ! blockMesh -case "$case_dir" > "$RUN/$name.blockmesh.log" 2>&1; then
        log "$name: blockMesh FAILED"; tail -10 "$RUN/$name.blockmesh.log" >> "$LOG"
        overall=1; continue
    fi
    if ! checkMesh -case "$case_dir" > "$RUN/$name.checkmesh.log" 2>&1; then
        log "$name: checkMesh FAILED"; tail -10 "$RUN/$name.checkmesh.log" >> "$LOG"
        overall=1; continue
    fi
    grep -E "cells:" "$RUN/$name.checkmesh.log" | head -2 >> "$LOG" 2>/dev/null || true

    # one clean-start solve, in the foreground, with no endTime rewriting anywhere
    log "$name: solver start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    start=$(date +%s)
    if "$BUILD/bin/realFluidReactingFoam" -case "$case_dir" > "$RUN/$name.solver.log" 2>&1; then
        rc_solve=0
    else
        rc_solve=$?
    fi
    log "$name: solver end rc=$rc_solve elapsed=$(( $(date +%s) - start ))s"

    last_time=$(grep -oE '^Time = [0-9.eE+-]+' "$RUN/$name.solver.log" | tail -1 | sed 's/^Time = //')
    end_marker=$(grep -cx 'End' "$RUN/$name.solver.log" || true)
    steps=$(grep -c '^Time = ' "$RUN/$name.solver.log" || true)
    writes=$(cd "$case_dir" && ls -d [0-9]* 2>/dev/null | grep -vx '0' | wc -l)
    log "$name: last_time=$last_time steps=$steps end_marker=$end_marker write_dirs=$writes"

    stopped=no
    if [ "$rc_solve" -eq 0 ] && [ "$end_marker" -ge 1 ] && \
       python3 -c "import sys; sys.exit(0 if abs(${last_time:-nan} - $end_time) <= 1e-12*max(1.0,$end_time) else 1)"; then
        stopped=yes
    fi
    log "$name: verified clean stop at endTime = $stopped (expected writes $expected_writes, got $writes)"
    printf 'case=%s variant=%s rc_solve=%s last_time=%s end_marker=%s steps=%s writes=%s expected_writes=%s stopped=%s\n' \
        "$name" "$variant" "$rc_solve" "$last_time" "$end_marker" "$steps" "$writes" \
        "$expected_writes" "$stopped" >> "$RUN/$name.stop.txt"

    times=$(cd "$case_dir" && ls -d [0-9]* 2>/dev/null | sort -g | tr '\n' ',' | sed 's/,$//')
    expect=sensible
    [ "$variant" = chemOn ] && expect=total
    if [ "$(cd "$case_dir" && ls -d [0-9]* 2>/dev/null | grep -vx '0' | wc -l)" -gt 0 ]; then
        python3 -B "$MODULE/metrics.py" --case "$case_dir" --times "$times" \
            --out "$RUN/$name.metrics.json" > "$RUN/$name.metrics.stdout" 2>&1 || overall=1
        python3 -B "$MODULE/expected_energy.py" --case "$case_dir" --expect "$expect" \
            --out "$RUN/$name.expected-energy.json" > "$RUN/$name.expected-energy.stdout" 2>&1 || overall=1
        python3 - "$RUN/$name.metrics.json" "$RUN/$name.expected-energy.json" <<'PY' \
            > "$RUN/$name.summary.txt" 2>&1 || overall=1
import json, sys
m, e = (json.load(open(p)) for p in sys.argv[1:3])
print('times', [r['time_s'] for r in m['times']])
for r in m['times']:
    print('t=%-8g T=[%.2f,%.2f] rho=[%.4f,%.4f] p=[%.2f,%.2f] inv_max=%s inv_med=%s mass=%.12g hs=%.12g'
          % (r['time_s'], r['finite']['T'][0], r['finite']['T'][1],
             r['finite']['rho'][0], r['finite']['rho'][1],
             r['finite']['p'][0], r['finite']['p'][1],
             r['inversion']['max_rel_residual'], r['inversion']['median_rel_residual'],
             r['conservation']['total_mass_kg_per_m2'],
             r['conservation']['total_sensible_energy_J_per_m2']))
print('expected', json.dumps(e['expected_initial_state'], sort_keys=True))
for d in e['conservation']:
    print('t=%-8g conserved=%s measured=%.12g expected=%.12g rel=%.3e rel_to_first=%.3e'
          % (d['time_s'], e['declared_conserved_quantity'], d['measured_J_per_m2'],
             d['expected_J_per_m2'], d['relative_to_expected'], d['relative_to_first_write']))
PY
    else
        log "$name: no saved field beyond 0 - nothing to measure"
        overall=1
    fi
    [ "$rc_solve" -ne 0 ] && overall=1
    [ "$stopped" = no ] && overall=1
done

# test the metric module itself in the same allocation
if python3 -B -m unittest discover -s "$MODULE" -p 'test_metrics.py' -t "$MODULE" \
        > "$RUN/metrics-selftest.log" 2>&1; then rc_self=0; else rc_self=$?; fi
log "metrics self-test rc=$rc_self $(grep -E '^OK|FAILED|Ran ' "$RUN/metrics-selftest.log" | tr '\n' ' ')"

printf 'RAN overall=%s rc_selftest=%s total=%ss\n' "$overall" "$rc_self" \
    "$(( $(date +%s) - START ))" > "$RUN/status.txt"
log "energy diagnostic done overall=$overall"
tail -60 "$LOG"
[ "$overall" -eq 0 ]
