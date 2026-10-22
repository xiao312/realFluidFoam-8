#!/bin/bash
# OF8 contact-advection diagnostic for `schmitt2020-fig-5`.
#
# Three cases, generated from committed dictionaries by prepare_advection_case.py and all
# starting at startTime 0 with no carried-over field: dx = 0.01 m, u = 10 m/s, p = 1 atm,
# ideal gas, an error-function temperature contact 300 K | 3000 K (density ratio 10, the
# ratio the registered target uses) resolved by n_x = 2, 4, 6 cells, chemistry off, t = 20 ms.
# The domain is periodic in x, so there is no boundary flux and the exact solution is a
# rigid shift of the initial profile.
#
# Measurements per case: mass, momentum and total-energy integrals against their initial
# values (periodic: exactly conserved in exact arithmetic), the spurious pressure deviation
# max|p-p0|/p0 and velocity deviation max|U-u0| that the target plots, positivity of density,
# species closure, Cp against the independent JANAF polynomial, and the L2 error against the
# shifted initial temperature profile.
#
# The built solver has no real-fluid equation of state, so the registered 6 MPa oxygen state
# (1000 -> 100 kg/m3) cannot be imposed; that is recorded as a blocker in each receipt and is
# not approximated silently. This job measures the numerics, not a figure replication.
set -uo pipefail
RUN=${RUN:-/workspace/forge-out/runs/of8-advection-v1}
BUILD=${1:-/workspace/forge-out/runs/of8-build-v5}
MECH=${MECH:-/workspace/forge-out/runs/of8-case-v1/case/constant}
MODULE=${MODULE:-/workspace/science/replication/development/of8-clean-start}
LOG="$RUN/diag.log"
START=$(date +%s)

mkdir -p "$RUN" || exit 1
: > "$LOG"
log() { echo "$@" >> "$LOG"; date -u +%Y-%m-%dT%H:%M:%SZ >> "$LOG"; }

log "advection diagnostic v1 start"
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

COMMIT=$(export PATH=/workspace/.tooling/git-2.30.2/bin:$PATH; \
         git -C /workspace/science rev-parse HEAD 2>/dev/null || echo unrecorded)
printf '%s\n' "$COMMIT" > "$RUN/source-commit.txt"
log "source commit ${COMMIT:-unrecorded}"

export LD_LIBRARY_PATH="$BUILD/lib:${LD_LIBRARY_PATH:-}"
export PATH="$BUILD/bin:${PATH:-}"
export OMP_NUM_THREADS=1
log "which realFluidReactingFoam $(command -v realFluidReactingFoam)"

overall=0
for name in nx2 nx4 nx6; do
    case_dir="$RUN/$name"
    log "== $name =="
    rm -rf "$case_dir" "$case_dir.receipt.json"
    if ! python3 -B "$MODULE/prepare_advection_case.py" --out "$case_dir" --variant "$name" \
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
    grep -E 'cells:' "$RUN/$name.checkmesh.log" | head -2 >> "$LOG" 2>/dev/null || true
    grep -E 'Cyclic|cyclic' "$RUN/$name.checkmesh.log" | head -2 >> "$LOG" 2>/dev/null || true

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
    maxco=$(grep -oE 'max: [0-9.eE+-]+' "$RUN/$name.solver.log" | tail -1 | awk '{print $2}')
    log "$name: last_time=$last_time steps=$steps end_marker=$end_marker write_dirs=$writes max_co=$maxco"

    stopped=no
    if [ "$rc_solve" -eq 0 ] && [ "$end_marker" -ge 1 ] && \
       python3 -c "import sys; sys.exit(0 if abs(${last_time:-nan} - $end_time) <= 1e-12*max(1.0,$end_time) else 1)"; then
        stopped=yes
    fi
    log "$name: verified clean stop at endTime = $stopped (expected writes $expected_writes, got $writes)"
    printf 'case=%s rc_solve=%s last_time=%s end_marker=%s steps=%s writes=%s expected_writes=%s max_co=%s stopped=%s\n' \
        "$name" "$rc_solve" "$last_time" "$end_marker" "$steps" "$writes" \
        "$expected_writes" "$maxco" "$stopped" >> "$RUN/$name.stop.txt"

    times=$(cd "$case_dir" && ls -d [0-9]* 2>/dev/null | sort -g | grep -vx '0' | tr '\n' ',' | sed 's/,$//')
    if [ -n "${times:-}" ]; then
        python3 -B "$MODULE/advection_metrics.py" --case "$case_dir" --times "$times" \
            --out "$RUN/$name.metrics.json" > "$RUN/$name.metrics.stdout" 2>&1 || overall=1
    else
        log "$name: no saved field beyond 0 - nothing to measure"
        overall=1
    fi
    [ "$rc_solve" -ne 0 ] && overall=1
    [ "$stopped" = no ] && overall=1
done

# cross-case summary: the two amplitudes the registered target plots, per interface resolution
python3 - "$RUN" <<'PY' > "$RUN/summary.txt" 2>&1 || overall=1
import json, sys
from pathlib import Path
run = Path(sys.argv[1])
print('target schmitt2020-fig-5 (numerics-only stand-in; ideal gas, 1 atm, T 300|3000 K)')
print('%-5s %-6s %-11s %-11s %-11s %-11s %-11s' % ('case', 't', 'p_dev_rel', 'u_dev_m/s',
      'mass_drift', 'energy_drift', 'T_l2_rel'))
for name in ('nx2', 'nx4', 'nx6'):
    path = run / (name + '.metrics.json')
    if not path.exists():
        print('%-5s missing metrics' % name)
        continue
    d = json.loads(path.read_text())
    for row in d['times']:
        print('%-5s %-6s %-11.3e %-11.3e %-11.3e %-11.3e %-11.3e' % (
            name, row['time'], row['pressure_deviation_rel'],
            row['velocity_deviation_m_per_s'], row['mass_rel_drift'],
            row['energy_rel_drift'], row['temperature_l2_relative_to_jump'] or float('nan')))
    last = d['times'][-1]
    print('  %-5s final rho=[%.4f, %.4f] T=[%.1f, %.1f] species_sum_err=%.2e cp_err=%s' % (
        name, last['density_min_kg_per_m3'], last['density_max_kg_per_m3'],
        last['temperature_min_K'], last['temperature_max_K'],
        last['species_sum_max_error'], last['cp_max_rel_error_vs_janaf']))
PY

if python3 -B -m unittest discover -s "$MODULE" -p 'test_metrics.py' -t "$MODULE" \
        > "$RUN/metrics-selftest.log" 2>&1; then rc_self=0; else rc_self=$?; fi
log "metrics self-test rc=$rc_self $(grep -E '^OK|FAILED|Ran ' "$RUN/metrics-selftest.log" | tr '\n' ' ')"

printf 'RAN overall=%s rc_selftest=%s total=%ss\n' "$overall" "$rc_self" \
    "$(( $(date +%s) - START ))" > "$RUN/status.txt"
log "advection diagnostic done overall=$overall"
tail -60 "$LOG"
[ "$overall" -eq 0 ]
