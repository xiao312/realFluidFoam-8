#!/bin/bash
# Bounded 2-D two-stream cold-mixing diagnostic (G2-related, explicitly not a G2 replication).
#
# One case generated from committed dictionaries by prepare_mixing_case.py, starting at
# startTime 0 with no carried-over field: 80 x 40 uniform cells over 0.04 m x 0.02 m, CH4 at
# 288 K below mid-height and O2 at 100 K above it, both at 101325 Pa, ideal gas, chemistry
# off, u_fuel = 10 m/s and u_ox set by the registered G2 mass-flow ratio 44.4/143.1, 1000
# step-steps of 2e-7 s to 2e-4 s with 5 writes.
#
# Measurements per write: exact inlet mass/momentum/energy flux against the integrated outlet
# flux and the measured accumulation (mixing_metrics.py), positivity and species closure,
# pressure excursion max|p-p0|/p0, acoustic Mach number, and the 10/90 % mixing width.
#
# The registered target state (LOx 85 K, 5.59 MPa) is not representable by this build; the
# receipt lists that deviation, and this job measures the numerics, not the figure.
set -uo pipefail
RUN=${RUN:-/workspace/forge-out/runs/of8-mixing-v1}
BUILD=${1:-/workspace/forge-out/runs/of8-build-v5}
MECH=${MECH:-/workspace/forge-out/runs/of8-case-v1/case/constant}
MODULE=${MODULE:-/workspace/science/replication/development/of8-clean-start}
NX=${NX:-80}
NY=${NY:-40}
END_TIME=${END_TIME:-2e-4}
DELTA_T=${DELTA_T:-2e-7}
WRITE_INTERVAL=${WRITE_INTERVAL:-4e-5}
LOG="$RUN/diag.log"
START=$(date +%s)

mkdir -p "$RUN" || exit 1
: > "$LOG"
log() { echo "$@" >> "$LOG"; date -u +%Y-%m-%dT%H:%M:%SZ >> "$LOG"; }

log "mixing diagnostic v1 start"
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
case_dir="$RUN/mix-${NX}x${NY}"
receipt="$case_dir.receipt.json"
log "== mix-${NX}x${NY} =="
rm -rf "$case_dir" "$receipt"
if ! python3 -B "$MODULE/prepare_mixing_case.py" --out "$case_dir" --mechanism-source "$MECH" \
        --source-commit "$COMMIT" --nx "$NX" --ny "$NY" --end-time "$END_TIME" \
        --delta-t "$DELTA_T" --write-interval "$WRITE_INTERVAL" \
        > "$RUN/mix.prepare.log" 2>&1; then
    log "case generation FAILED"
    tail -20 "$RUN/mix.prepare.log" >> "$LOG"
    printf 'FAILED case-generation\n' > "$RUN/status.txt"; exit 1
fi
# blockMesh reads controlDict, so a missing terminator is fatal before any solve starts
# (job 125290253 died this way). Fail here with the dictionary named.
for key in endTime deltaT writeInterval; do
    if ! grep -qE "^$key +[0-9.eE+-]+;" "$case_dir/system/controlDict"; then
        log "controlDict entry $key missing or unterminated"
        printf 'FAILED controlDict-%s\n' "$key" > "$RUN/status.txt"; exit 1
    fi
done
end_time=$(grep -oE '^endTime +[0-9.eE+-]+' "$case_dir/system/controlDict" | awk '{print $2}')
write_interval=$(grep -oE '^writeInterval +[0-9.eE+-]+' "$case_dir/system/controlDict" | awk '{print $2}')
expected_writes=$(python3 -c "print(round($end_time/$write_interval))")
log "controls endTime=$end_time writeInterval=$write_interval expected_writes=$expected_writes"

if ! ( cd "$case_dir" && find 0 constant system -type f -print0 | sort -z | xargs -0 sha256sum ) \
        > "$RUN/mix.inputs.sha256" 2>>"$LOG"; then
    log "input hashing FAILED"; printf 'FAILED input-hashing\n' > "$RUN/status.txt"; exit 1
fi
if ! blockMesh -case "$case_dir" > "$RUN/mix.blockmesh.log" 2>&1; then
    log "blockMesh FAILED"; tail -20 "$RUN/mix.blockmesh.log" >> "$LOG"
    printf 'FAILED blockMesh\n' > "$RUN/status.txt"; exit 1
fi
if ! checkMesh -case "$case_dir" > "$RUN/mix.checkmesh.log" 2>&1; then
    log "checkMesh FAILED"; tail -20 "$RUN/mix.checkmesh.log" >> "$LOG"
    printf 'FAILED checkMesh\n' > "$RUN/status.txt"; exit 1
fi
grep -E 'cells:|Mesh OK|Failed' "$RUN/mix.checkmesh.log" | head -3 >> "$LOG" 2>/dev/null || true

log "solver start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
start=$(date +%s)
if "$BUILD/bin/realFluidReactingFoam" -case "$case_dir" > "$RUN/mix.solver.log" 2>&1; then
    rc_solve=0
else
    rc_solve=$?
fi
log "solver end rc=$rc_solve elapsed=$(( $(date +%s) - start ))s"

last_time=$(grep -oE '^Time = [0-9.eE+-]+' "$RUN/mix.solver.log" | tail -1 | sed 's/^Time = //')
end_marker=$(grep -cx 'End' "$RUN/mix.solver.log" || true)
steps=$(grep -c '^Time = ' "$RUN/mix.solver.log" || true)
writes=$(cd "$case_dir" && ls -d [0-9]* 2>/dev/null | grep -vx '0' | wc -l)
maxco=$(grep -oE 'max: [0-9.eE+-]+' "$RUN/mix.solver.log" | tail -1 | awk '{print $2}')
log "last_time=$last_time steps=$steps end_marker=$end_marker write_dirs=$writes max_co=$maxco"

stopped=no
if [ "$rc_solve" -eq 0 ] && [ "$end_marker" -ge 1 ] && \
   python3 -c "import sys; sys.exit(0 if abs(${last_time:-nan} - $end_time) <= 1e-9*max(1.0,$end_time) else 1)"; then
    stopped=yes
fi
log "verified clean stop at endTime = $stopped (expected writes $expected_writes, got $writes)"
printf 'case=mix-%sx%s rc_solve=%s last_time=%s end_marker=%s steps=%s writes=%s expected_writes=%s max_co=%s stopped=%s\n' \
    "$NX" "$NY" "$rc_solve" "$last_time" "$end_marker" "$steps" "$writes" \
    "$expected_writes" "$maxco" "$stopped" > "$RUN/mix.stop.txt"

times=$(cd "$case_dir" && ls -d [0-9]* 2>/dev/null | sort -g | grep -vx '0' | tr '\n' ',' | sed 's/,$//')
if [ -n "${times:-}" ]; then
    python3 -B "$MODULE/mixing_metrics.py" --case "$case_dir" --receipt "$receipt" \
        --out "$RUN/mix.metrics.json" > "$RUN/mix.metrics.stdout" 2>&1 || overall=1
    python3 - "$RUN" <<'PY' > "$RUN/summary.txt" 2>&1 || overall=1
import json, sys
from pathlib import Path
run = Path(sys.argv[1])
d = json.loads((run / 'mix.metrics.json').read_text())
print('bounded 2-D two-stream cold-mixing diagnostic (NOT a G2 replication)')
print('cells=%d times=%s' % (d['cells'], d['times']))
print('exact inlet mass flux %.6e kg/s, momentum %.6e, energy %.6e J/s' % (
    d['inlet_flux']['total_mass_flux_kg_per_s'],
    d['inlet_flux']['total_momentum_flux_kg_m_per_s2'],
    d['inlet_flux']['total_energy_flux_J_per_s']))
print('%-8s %-9s %-11s %-11s %-11s %-11s' % ('t', 'width_m', 'mass_in', 'mass_out',
      'mom_in', 'mom_out'))
for row in d['per_time']:
    w = row['mixing']['width_10_90']
    print('%-8s %-9s %-11.4e %-11.4e %-11.4e %-11.4e' % (
        row['time'], ('%.5f' % w) if w else 'none', row['fluxes']['mass_in'],
        row['fluxes']['mass_out'], row['fluxes']['momentum_in'], row['fluxes']['momentum_out']))
print('%-8s %-9s %-11s %-11s' % ('t', 'p_exc_rel', 'max_mach', 'Y_min'))
for row in d['per_time']:
    b = row['bounds']
    print('%-8s %-9.3e %-11.3e %-11.3e' % (row['time'], b['pressure_excursion'],
          b['max_mach'], b['Y_min']))
print('%-8s %-11s %-11s %-11s %-11s' % ('interval', 'mass_imb', 'mom_imb', 'energy_imb',
      'dt'))
for b in d['balances']:
    print('%-8s %-11.3e %-11.3e %-11.3e %-11.3e' % ('%g-%g' % tuple(b['interval']),
          b['mass_imbalance_fraction'], b['momentum_imbalance_fraction'],
          b['energy_imbalance_fraction'], b['dt']))
print('scope: %s' % d['scope'])
PY
else
    log "no saved field beyond 0 - nothing to measure"
    overall=1
fi
[ "$rc_solve" -ne 0 ] && overall=1
[ "$stopped" = no ] && overall=1

if python3 -B -m unittest discover -s "$MODULE" -p 'test_mixing.py' -t "$MODULE" \
        > "$RUN/mixing-selftest.log" 2>&1; then rc_self=0; else rc_self=$?; fi
log "mixing self-test rc=$rc_self $(grep -E '^OK|FAILED|Ran ' "$RUN/mixing-selftest.log" | tr '\n' ' ')"

printf 'RAN overall=%s rc_selftest=%s total=%ss\n' "$overall" "$rc_self" \
    "$(( $(date +%s) - START ))" > "$RUN/status.txt"
log "mixing diagnostic done overall=$overall"
tail -60 "$LOG"
[ "$overall" -eq 0 ]
