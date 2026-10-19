#!/bin/bash
set -euo pipefail
action=${1:?}; root=${2:?}; release=${3:?}; sdk=${4:?}; inputs=${5:?}
[[ $action == plan || $action == apply ]] || exit 2
root=$(realpath -e "$root")
for path in "$release" "$sdk" "$inputs"; do
 [[ $(realpath -e "$path") == "$root/"* ]] || exit 2
done
bash -n "$release/replication/development/cantera-bridge/job.sh"
echo "Cantera C ABI qualification: 1 core, 20 minutes; source=$release; SDK=$sdk; inputs=$inputs; output=$root/jobs/SLURM_JOB_ID"
[[ $action == apply ]] || exit 0
sbatch --parsable --partition=kshcnormal --cpus-per-task=1 --time=00:20:00 \
 --chdir="$root" --job-name=rf-ct-bridge --output="$root/logs/ct-bridge-%j.out" \
 --error="$root/logs/ct-bridge-%j.err" "$release/replication/development/cantera-bridge/job.sh" \
 "$root" "$release" "$sdk" "$inputs"
