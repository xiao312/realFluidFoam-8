#!/bin/bash
# Run one Liang Fig. 8(a) operating point per `job-batch.sh case` call.
#
# The equivalence-ratio grid is the set of digitised marker centres of the reference
# panel, so stages 2, 3 and 4 are compared marker-to-marker and stages 1 and 5 are
# interpolated from the two traced curves at exactly the same phi. Nothing is
# extrapolated: the grid lies inside the digitised span 0.95-1.40.
#
# Each point gets its own directory under $run/cases so a single failure (or a killed
# allocation) never looks like a completed point. `timeout` bounds one flame solve and
# the remaining-wall check stops the sweep cleanly instead of being killed mid-write.
#
# Usage: job-sweep.sh MODULE INPUTS RUN BUILD STAGES PHIS
#   STAGES  comma list, e.g. 1,2,3,4,5
#   PHIS    comma list of equivalence ratios
set -euo pipefail

module=${1:?module directory}
inputs=${2:?inputs directory}
run=${3:?run directory}
build=${4:?build directory (from job-batch.sh build)}
stages=${5:?comma separated stages}
phis=${6:?comma separated equivalence ratios}

variant=full
pressure=100
rtol=1e-5
atol=1e-11
per_run_timeout=${PER_RUN_TIMEOUT:-1200}
wall_budget=${WALL_BUDGET:-6300}     # stop starting new points after this

mkdir -p "$run/cases"
start=$(date +%s)
printf 'sweep start %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$run/sweep.txt"
printf 'stages=%s phis=%s variant=%s pressure_atm=%s rtol=%s atol=%s\n' \
    "$stages" "$phis" "$variant" "$pressure" "$rtol" "$atol" >> "$run/sweep.txt"

IFS=',' read -r -a stage_list <<< "$stages"
IFS=',' read -r -a phi_list <<< "$phis"
done_count=0
failed_count=0
skipped_count=0

for stage in "${stage_list[@]}"; do
    for phi in "${phi_list[@]}"; do
        case_dir=$run/cases/stage-${stage}-phi-${phi}
        mkdir -p "$case_dir"
        # Freeze the identities next to the result so the check is per operating point.
        cp "$run/module.sha256" "$case_dir/module.sha256"
        cp "$run/inputs.sha256" "$case_dir/inputs.sha256"
        elapsed=$(( $(date +%s) - start ))
        remaining=$(( wall_budget - elapsed ))
        if [ "$remaining" -lt 120 ]; then
            printf 'NOT_ATTEMPTED stage=%s phi=%s elapsed=%ss\n' "$stage" "$phi" "$elapsed" \
                > "$case_dir/status.txt"
            skipped_count=$((skipped_count + 1))
            continue
        fi
        limit=$per_run_timeout
        if [ "$limit" -gt "$remaining" ]; then limit=$remaining; fi
        rc=0
        timeout --signal=TERM --kill-after=60 "$limit" \
            bash "$module/job-batch.sh" case "$module" "$inputs" "$case_dir" "$build" \
            "$stage" "$phi" "$variant" "$pressure" "$rtol" "$atol" || rc=$?
        if [ "$rc" -eq 0 ] && grep -q '^COMPLETED ' "$case_dir/flame.log" 2>/dev/null; then
            done_count=$((done_count + 1))
            printf 'COMPLETED stage=%s phi=%s timeout=%s %s\n' "$stage" "$phi" "$limit" \
                "$(grep '^COMPLETED ' "$case_dir/flame.log")" >> "$run/sweep.txt"
        else
            failed_count=$((failed_count + 1))
            printf 'FAILED stage=%s phi=%s rc=%s timeout=%s\n' "$stage" "$phi" "$rc" "$limit" \
                >> "$run/sweep.txt"
        fi
    done
done

printf 'sweep done completed=%s failed=%s not_attempted=%s elapsed=%ss\n' \
    "$done_count" "$failed_count" "$skipped_count" "$(( $(date +%s) - start ))" >> "$run/sweep.txt"
printf 'SWEEP completed=%s failed=%s not_attempted=%s\n' \
    "$done_count" "$failed_count" "$skipped_count" > "$run/status.txt"
[ "$failed_count" -eq 0 ] && [ "$skipped_count" -eq 0 ]
