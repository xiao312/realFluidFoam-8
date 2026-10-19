#!/bin/bash
set -Eeuo pipefail
action=${1:?}; root=${2:?}; image=${3:?}; release=${4:?}
kind=${5:-observer}; stage=heat-release
[[ "$kind" == observer || "$kind" == native ]] || exit 2
if [[ "$kind" == native ]]; then
    stage=heat-release-native
    grep -q '^PASS: heat-release monitor qualification' "$root/jobs/124867177/result.txt"
fi
[[ "$action" == plan || "$action" == apply ]] || exit 2
bash "$release/replication/environment/workspace.sh" plan "$root" >/dev/null
for path in "$image" "$release"; do [[ $(realpath -e "$path") == "$root/"* ]] || exit 2; done
grep -q '^PASS: paper premixed phi110-equilibrium smoke;' "$root/jobs/124864535/result.txt"
args=(--parsable --partition=kshcnormal --nodes=1 --ntasks=1 --cpus-per-task=8 --time=30
    --job-name=rf-heat-release-check --chdir="$root" --output="$root/logs/%x-%j.out" --error="$root/logs/%x-%j.err"
    "$release/replication/environment/job.sh" "$root" "$image" "$release" validation 124657926 "$stage")
printf 'sbatch '; printf '%q ' "${args[@]}"; printf '\n'
if [[ "$action" == apply ]]; then
    ledger="$root/results/heat-release-reservations.tsv"
    exec 9>"$ledger.lock"; flock -x 9
    sha=$(cat "$release/SOURCE_REVISION")
    if [[ -f "$ledger" ]] && grep -q "$sha" "$ledger"; then echo 'Already submitted; inspect ledger' >&2;exit 2;fi
    id=$(sbatch "${args[@]}")
    printf '%s\t4\t%s\n' "$id" "$sha" >> "$ledger"
    echo "SUBMITTED $id"
fi
