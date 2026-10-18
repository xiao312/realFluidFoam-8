#!/bin/bash
set -Eeuo pipefail
release=${1:?}; job=${2:?}; build=${3:?}
module="$release/replication/validation/profiling"
python3 -B "$module/instrument.py" plan "$build" "$job/profile-solver" > "$job/profile-plan.json"
python3 -B "$module/instrument.py" apply "$build" "$job/profile-solver" > "$job/instrument.log"
wmake "$job/profile-solver" > "$job/profile-build.log" 2>&1
sha256sum "$FOAM_USER_APPBIN/rfProfileReactingFoam" > "$job/profile-binary.sha256"
python3 -B "$module/replay.py" prepare "$job"
for key in one-step oxy-1 oxy-200 air-100 premixed; do
    ranks=8; [[ "$key" != premixed ]] || ranks=4
    for variant in timed baseline; do
        case_dir="$job/$key-$variant"
        [[ -d "$case_dir" ]] || continue
        solver=rfProfileReactingFoam
        [[ "$variant" != baseline ]] || solver=realFluidReactingFoam
        mpirun --mca btl self,vader,tcp -np "$ranks" "$solver" -case "$case_dir" -parallel > "$job/$key-$variant.log" 2>&1
        grep -q '^End' "$job/$key-$variant.log"
    done
done
python3 -B "$module/replay.py" verify "$job" > "$job/equivalence.log"
echo 'PASS: section profiles and baseline field comparison' > "$job/result.txt"
