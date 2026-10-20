#!/bin/bash
set -euo pipefail
root=${1:?}; release=${2:?}; library=${3:?}; ranks=${4:?}; key=${5:?}; mode=${6:?}; build=${7:?}
increments=${8:?}; properties=${9:?}
for test_job in "$increments" "$properties"; do
 [[ $test_job =~ ^[0-9]+$ ]] || exit 2
 grep -q '^PASS:' "$root/jobs/$test_job/result.txt"
 grep -q "^build_job=$library$" "$root/jobs/$test_job/validation-inputs.txt"
done
if [[ $mode == full ]]; then
 grep -q '^PASS:' "$root/jobs/$build/result.txt"
 grep -q 'Small-increment inversion failures: 0/144' "$root/jobs/$build/ideal-increments.log"
fi
exec bash "$release/replication/development/temperature-inversion/job.sh" \
 "$root" "$release" "$library" "$ranks" "$key" "$mode" "$build"
