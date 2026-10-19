#!/bin/bash
set -euo pipefail
action=${1:?}; root=${2:?}; release=${3:?}; family=${4:?}; key=${5:?}
[[ $action == plan || $action == apply ]] || exit 2
[[ $(realpath -e "$release") == "$root/releases/"* ]] || exit 2
[[ $family == native || $family == energy ]] || exit 2
[[ $key =~ ^phi(090|095|100|105|110|115|120|125|130|135|140)$ ]] || exit 2
[[ $family != energy || $key == phi110 ]] || exit 2
bash "$release/replication/environment/workspace.sh" plan "$root" >/dev/null
python3 -B "$release/replication/development/fresh-start/prepare.py" plan "$family" "$key" "$root/jobs/PLANNED-fresh-$family-$key/case"
minutes=480
[[ $key != phi090 ]] || minutes=2880
args=(--parsable --partition=kshcnormal --nodes=1 --ntasks=1 --cpus-per-task=8 --time="$minutes"
 --chdir="$root" --job-name="rf0-$family-$key" --output="$root/logs/%x-%j.out" --error="$root/logs/%x-%j.err"
 "$release/replication/development/fresh-start/job.sh" "$root" "$release" "$family" "$key")
printf '%q ' sbatch "${args[@]}"; printf '\n'
[[ $action == apply ]] || exit 0
exec 9>"$root/results/fresh-start.lock"; flock 9
ledger="$root/results/fresh-start.tsv"
if [[ -f $ledger ]] && awk -F '\t' -v release="$release" -v family="$family" -v key="$key" '$2==release && $3==family && $4==key{found=1} END{exit !found}' "$ledger"; then
 echo 'Already submitted; inspect fresh-start.tsv' >&2; exit 2
fi
id=$(sbatch "${args[@]}")
printf '%s\t%s\t%s\t%s\t%s\n' "$id" "$release" "$family" "$key" "$minutes" >> "$ledger"
echo "SUBMITTED $id $family $key"
