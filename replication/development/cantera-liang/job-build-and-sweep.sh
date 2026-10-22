#!/bin/bash
# Build the Fig. 8(a) flame executable and then sweep operating points in ONE allocation.
#
# The registered `cantera32` image spends ~580 s of every allocation converting the SIF to
# a sandbox before any payload line runs. Submitting build and sweep separately pays that
# cost twice, so this wrapper runs `job-batch.sh build` (which writes `build-status.txt`)
# and then `job-sweep.sh` (which reuses the binary and its sha256) against the same run
# directory. Nothing else changes: both stages are the frozen scripts, each case still
# verifies the frozen module and input hashes, and a build failure stops before any case.
#
# Usage: job-build-and-sweep.sh MODULE INPUTS RUN STAGES PHIS
#   STAGES  comma list, e.g. 1,2
#   PHIS    comma list of equivalence ratios
# Environment: PER_RUN_TIMEOUT, WALL_BUDGET, PRESSURE_ATM (forwarded to job-sweep.sh)
set -euo pipefail

module=${1:?module directory}
inputs=${2:?inputs directory}
run=${3:?run directory}
stages=${4:?comma separated stages}
phis=${5:?comma separated equivalence ratios}

mkdir -p "$run"
printf 'combined start %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$run/combined.txt"
printf 'stages=%s phis=%s per_run_timeout=%s wall_budget=%s pressure_atm=%s\n' \
    "$stages" "$phis" "${PER_RUN_TIMEOUT:-1200}" "${WALL_BUDGET:-6300}" "${PRESSURE_ATM:-100}" \
    >> "$run/combined.txt"

rc=0
bash "$module/job-batch.sh" build "$module" "$inputs" "$run" || rc=$?
if [ "$rc" -ne 0 ]; then
    printf 'COMBINED build_rc=%s\n' "$rc" >> "$run/combined.txt"
    exit "$rc"
fi
cp "$run/status.txt" "$run/build-status.txt"
if ! grep -q '^BUILT ' "$run/build-status.txt"; then
    printf 'COMBINED no BUILT marker: %s\n' "$(cat "$run/build-status.txt")" >> "$run/combined.txt"
    exit 1
fi
printf 'build marker %s\n' "$(cat "$run/build-status.txt")" >> "$run/combined.txt"

rc=0
bash "$module/job-sweep.sh" "$module" "$inputs" "$run" "$run" "$stages" "$phis" || rc=$?
printf 'sweep rc=%s %s\n' "$rc" "$(cat "$run/status.txt" 2>/dev/null || echo 'no sweep status')" \
    >> "$run/combined.txt"
printf 'sweep rc=%s %s\n' "$rc" "$(cat "$run/status.txt" 2>/dev/null || echo 'no sweep status')"
exit "$rc"
