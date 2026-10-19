#!/bin/bash
set -euo pipefail
action=${1:?}; root=${2:?}; release=${3:?}; sdk=${4:?}; build=${5:?}; inputs=${6:?}; reference=${7:?}
[[ $action == plan || $action == apply ]] || exit 2
root=$(realpath -e "$root")
for path in "$release" "$sdk" "$build" "$inputs" "$reference"; do
 [[ $(realpath -e "$path") == "$root/"* ]] || exit 2
done
test -f "$build/result.txt"
bash -n "$release/replication/development/cantera-bridge/reactor-job.sh"
echo "CP reactor qualification: one core, twenty minutes; build=$build; reference=$reference; output=$root/jobs/SLURM_JOB_ID"
[[ $action == apply ]] || exit 0
sbatch --parsable --partition=kshcnormal --cpus-per-task=1 --time=00:20:00 \
 --chdir="$root" --job-name=rf-ct-reactor --output="$root/logs/ct-reactor-%j.out" \
 --error="$root/logs/ct-reactor-%j.err" "$release/replication/development/cantera-bridge/reactor-job.sh" \
 "$root" "$release" "$sdk" "$build" "$inputs" "$reference"
