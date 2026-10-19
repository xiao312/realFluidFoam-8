#!/bin/bash
set -Eeuo pipefail
action=${1:?}; root=${2:?}; image=${3:?}; release=${4:?}
[[ "$action" == plan || "$action" == apply ]] || exit 2
bash "$release/replication/environment/workspace.sh" plan "$root" >/dev/null
for path in "$image" "$release"; do [[ $(realpath -e "$path") == "$root/"* ]] || exit 2; done
for id in 124873143 124873144 124873146; do test -f "$root/jobs/$id/case-inputs.json"; done
args=(--parsable --partition=kshcnormal --nodes=1 --ntasks=1 --cpus-per-task=1 --time=10
    --dependency=afterany:124873143:124873144:124873146 --job-name=rf-sensitivity-check
    --chdir="$root" --output="$root/logs/%x-%j.out" --error="$root/logs/%x-%j.err"
    "$release/replication/environment/job.sh" "$root" "$image" "$release" validation 124657926 premixed-sensitivity-check)
printf 'sbatch '; printf '%q ' "${args[@]}"; printf '\n'
if [[ "$action" == apply ]]; then
    ledger="$root/results/premixed-sensitivity-check.tsv"
    [[ $(realpath -m "$ledger") == "$root/results/premixed-sensitivity-check.tsv" ]] || exit 2
    exec 9>"$ledger.lock"; flock -x 9
    sha=$(cat "$release/SOURCE_REVISION")
    if [[ -f "$ledger" ]] && grep -Fq "$sha" "$ledger"; then
        echo 'Already submitted; inspect qualification ledger' >&2; exit 2
    fi
    id=$(sbatch "${args[@]}")
    printf '%s\t0.166667\t%s\n' "$id" "$sha" >> "$ledger"
    echo "SUBMITTED $id qualification"
fi
