#!/bin/bash
set -Eeuo pipefail
action=${1:?}; root=${2:?}; image=${3:?}; release=${4:?}; key=${5:?}
[[ "$action" == plan || "$action" == apply ]] || exit 2
[[ "$key" == dt100 || "$key" == dt50 || "$key" == dt25 ]] || exit 2
bash "$release/replication/environment/workspace.sh" plan "$root" >/dev/null
for path in "$image" "$release"; do [[ $(realpath -e "$path") == "$root/"* ]] || exit 2; done
grep -q '^PASS: spatial diagnostics' "$root/jobs/124870644/result.txt"
for rank in {0..7}; do test -f "$root/jobs/124864929/case/processor$rank/7.99834968798e-05/T"; done
args=(--parsable --partition=kshcnormal --nodes=1 --ntasks=1 --cpus-per-task=8 --time=120
    --job-name="rf-sensitivity-$key" --chdir="$root" --output="$root/logs/%x-%j.out" --error="$root/logs/%x-%j.err"
    "$release/replication/environment/job.sh" "$root" "$image" "$release" validation 124657926 "premixed-sensitivity-$key")
printf 'sbatch '; printf '%q ' "${args[@]}"; printf '\n'
if [[ "$action" == apply ]]; then
    ledger="$root/results/premixed-sensitivity-reservations.tsv"
    [[ $(realpath -m "$ledger") == "$root/results/premixed-sensitivity-reservations.tsv" ]] || exit 2
    exec 9>"$ledger.lock"; flock -x 9
    sha=$(cat "$release/SOURCE_REVISION")
    if [[ -f "$ledger" ]] && awk -F '\t' -v sha="$sha" -v key="$key" '$3==sha && $4==key{found=1} END{exit !found}' "$ledger"; then
        echo 'Already submitted; inspect ledger' >&2; exit 2
    fi
    id=$(sbatch "${args[@]}")
    printf '%s\t16\t%s\t%s\n' "$id" "$sha" "$key" >> "$ledger"
    echo "SUBMITTED $id $key"
fi
