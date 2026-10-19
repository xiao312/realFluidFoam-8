#!/bin/bash
set -euo pipefail
action=${1:?}; root=${2:?}; release=${3:?}; bridge_job=${4:?}; key=${5:?}; mode=${6:-build}; build_job=${7:-none}
[[ $action == plan || $action == apply ]] || exit 2
[[ $mode == build || $mode == full ]] || exit 2
[[ $bridge_job =~ ^[0-9]+$ && $key =~ ^phi(090|095|100|105|110|115|120|125|130|135|140)$ ]] || exit 2
root=$(realpath -e "$root")
[[ $(realpath -e "$release") == "$root/releases/"* ]] || exit 2
test -f "$root/jobs/$bridge_job/result.txt"
if [[ $mode == full ]]; then
 [[ $build_job =~ ^[0-9]+$ ]] || exit 2
 test -f "$root/jobs/$build_job/qualification-passed.txt"
fi
hours=1; [[ $mode == full ]] && hours=8
echo "PLAN: $mode ideal Cantera transport, $key, original-zero fields; 8 cores; $hours hours; bridge=$bridge_job; source=$release"
[[ $action == apply ]] || exit 0
sbatch --parsable --partition=kshcnormal --cpus-per-task=8 --time="$hours:00:00" \
 --chdir="$root" --job-name="rf-ct-$mode-$key" --output="$root/logs/ct-cfd-%j.out" \
 --error="$root/logs/ct-cfd-%j.err" "$release/replication/development/cantera-cfd/job.sh" \
 "$root" "$release" "$bridge_job" "$key" "$mode" "$build_job"
