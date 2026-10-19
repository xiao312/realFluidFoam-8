#!/bin/bash
set -euo pipefail
action=${1:?}; root=${2:?}; release=${3:?}; sdk=${4:?}; inputs=${5:?}; stage=${6:?}; build=${7:-}
[[ $action == plan || $action == apply ]] || exit 2
root=$(realpath -e "$root")
for path in "$release" "$sdk" "$inputs"; do
 [[ $(realpath -e "$path") == "$root/"* ]] || exit 2
done
[[ $stage == build || $stage =~ ^[1-5]$ ]] || exit 2
if [[ $stage != build ]]; then
 [[ $(realpath -e "$build") == "$root/jobs/"* ]] || exit 2
 test -f "$build/build-passed.txt"
fi
printf 'Cantera stage=%s; 1 core; 4 hours; release=%s; sdk=%s; inputs=%s; build=%s\n' "$stage" "$release" "$sdk" "$inputs" "$build"
[[ $action == apply ]] || exit 0
sbatch --parsable --partition=kshcnormal --job-name="rf-liang-$stage" --cpus-per-task=1 --time=04:00:00 \
 --chdir="$root" --output="$root/logs/liang-$stage-%j.out" --error="$root/logs/liang-$stage-%j.err" \
 "$release/replication/development/cantera-liang/job.sh" "$root" "$release" "$sdk" "$inputs" "$stage" "${build:-none}"
