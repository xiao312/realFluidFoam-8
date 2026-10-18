#!/bin/bash
set -euo pipefail
action=${1:?plan/apply}; root=${2:?}; image=${3:?}; release=${4:?}; key=${5:?}
[[ "$action" == plan || "$action" == apply ]] || exit 2
[[ "$key" == phi-110-u010 || "$key" == phi-110-u020 ]] || exit 2
bash "$release/replication/environment/workspace.sh" plan "$root" >/dev/null
for path in "$image" "$release"; do [[ $(realpath -e "$path") == "$root/"* ]] || exit 2; done
python3 -B "$release/replication/development/premixed-inlet/prepare.py" plan "$key" "$root/jobs/PLANNED-inlet-$key/case" smoke
args=(--parsable --partition=kshcnormal --nodes=1 --ntasks=1 --cpus-per-task=4 --time=60
    --job-name="rfdev-$key" --chdir="$root" --output="$root/logs/%x-%j.out" --error="$root/logs/%x-%j.err"
    "$release/replication/environment/job.sh" "$root" "$image" "$release" validation 124657926 "dev-inlet-$key")
printf 'sbatch '; printf '%q ' "${args[@]}"; printf '\n'
if [[ "$action" == apply ]]; then
    ledger="$root/results/development-reservations.tsv"
    exec 9>"$ledger.lock"; flock -x 9
    sha=$(cat "$release/SOURCE_REVISION")
    if [[ -f "$ledger" ]] && grep -q "$(printf '\t%s\t%s$' "$key" "$sha")" "$ledger"; then
        echo 'Submission already recorded for this key/source; inspect it before retrying' >&2; exit 2
    fi
    id=$(sbatch "${args[@]}")
    printf '%s\t4\t%s\t%s\n' "$id" "$key" "$sha" >> "$ledger"
    echo "SUBMITTED $key $id (4 core-hours maximum)"
fi
