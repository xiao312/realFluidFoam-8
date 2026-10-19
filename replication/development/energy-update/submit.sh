#!/bin/bash
set -euo pipefail
action=${1:?plan/apply}; root=${2:?}; release=${3:?}
[[ $action == plan || $action == apply ]] || exit 2
[[ $(realpath -e "$release") == "$root/releases/"* ]] || exit 2
bash "$release/replication/environment/workspace.sh" plan "$root" >/dev/null
args=(--parsable --partition=kshcnormal --nodes=1 --ntasks=1 --cpus-per-task=8
 --time=360 --chdir="$root" --job-name=rf-energy-refresh
 --output="$root/logs/energy-%j.out" --error="$root/logs/energy-%j.err"
 "$release/replication/development/energy-update/job.sh" "$root" "$release")
printf '%q ' sbatch "${args[@]}"; printf '\n'
[[ $action == apply ]] || exit 0
exec 9>"$root/results/energy-update.lock"; flock 9
ledger="$root/results/energy-update.tsv"
if [[ -f $ledger ]] && grep -Fq "$release|" "$ledger"; then
 echo 'Release already submitted; inspect ledger' >&2; exit 2
fi
id=$(sbatch "${args[@]}")
printf '%s|%s|8|360\n' "$release" "$id" >> "$ledger"
echo "$id"
