#!/bin/bash
set -Eeuo pipefail
action=${1:?}; root=${2:?}; image=${3:?}; release=${4:?}
[[ "$action" == plan || "$action" == apply ]] || exit 2
bash "$release/replication/environment/workspace.sh" plan "$root" >/dev/null
for path in "$image" "$release"; do [[ $(realpath -e "$path") == "$root/"* ]] || exit 2; done
args=(--parsable --partition=kshcnormal --nodes=1 --ntasks=1 --cpus-per-task=1 --time=20
    --job-name=rf-liang-properties --chdir="$root" --output="$root/logs/%x-%j.out" --error="$root/logs/%x-%j.err"
    "$release/replication/environment/job.sh" "$root" "$image" "$release" validation 124657926 liang-properties)
printf 'sbatch '; printf '%q ' "${args[@]}"; printf '\n'
if [[ "$action" == apply ]]; then
    sha=$(cat "$release/SOURCE_REVISION")
    ledger="$root/results/liang-properties-reservations.tsv"
    exec 9>"$ledger.lock"; flock -x 9
    if [[ -f "$ledger" ]] && grep -q "$sha" "$ledger"; then echo 'Already submitted' >&2; exit 2; fi
    id=$(sbatch "${args[@]}")
    printf '%s\t0.333333\t%s\n' "$id" "$sha" >> "$ledger"
    echo "SUBMITTED $id"
fi
