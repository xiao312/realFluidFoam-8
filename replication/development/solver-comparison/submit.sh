#!/bin/bash
set -euo pipefail
action=${1:?plan/apply}; root=${2:?}; release=${3:?}; mode=${4:?}; dependency=${5:-}
[[ $action == plan || $action == apply ]] || exit 2
[[ $mode == stock || $mode == deep-build || $mode == deep || $mode == probe ]] || exit 2
[[ $(realpath -e "$release") == "$root/releases/"* ]] || exit 2
bash "$release/replication/environment/workspace.sh" plan "$root" >/dev/null
minutes=360; cpus=8
[[ $mode != deep-build ]] || { minutes=120; cpus=16; }
[[ $mode != probe ]] || { minutes=30; cpus=2; }
tasks=1; cpus_per_task=$cpus
[[ $mode != deep ]] || { tasks=8; cpus_per_task=1; }
args=(--parsable --partition=kshcnormal --nodes=1 --ntasks="$tasks" --cpus-per-task="$cpus_per_task"
 --time="$minutes" --chdir="$root" --job-name="rf-compare-$mode"
 --output="$root/logs/compare-$mode-%j.out" --error="$root/logs/compare-$mode-%j.err")
if [[ -n $dependency ]]; then
 [[ $dependency =~ ^[0-9]+$ ]] || exit 2
 args+=(--dependency="afterok:$dependency")
fi
printf '%q ' sbatch "${args[@]}" "$release/replication/development/solver-comparison/job.sh" "$root" "$release" "$mode" "$dependency"
printf '\n'
[[ $action == apply ]] || exit 0
exec 9>"$root/results/solver-comparison.lock"
flock 9
ledger="$root/results/solver-comparison.tsv"
if [[ -f $ledger ]] && grep -Fq "$release $mode $dependency|" "$ledger"; then
 echo 'Already reserved; inspect ledger before retry' >&2; exit 2
fi
id=$(sbatch "${args[@]}" "$release/replication/development/solver-comparison/job.sh" "$root" "$release" "$mode" "$dependency")
printf '%s %s %s|%s|%s|%s\n' "$release" "$mode" "$dependency" "$id" "$cpus" "$minutes" >> "$ledger"
echo "$id"
