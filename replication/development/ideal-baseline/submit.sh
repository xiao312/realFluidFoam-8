#!/bin/bash
set -Eeuo pipefail
action=${1:?}; root=${2:?}; image=${3:?}; release=${4:?}; key=${5:?}; mode=${6:?}; smoke=${7:-}
[[ "$action" == plan || "$action" == apply ]] || exit 2
[[ "$mode" == smoke || "$mode" == full ]] || exit 2
bash "$release/replication/environment/workspace.sh" plan "$root" >/dev/null
for path in "$image" "$release"; do [[ $(realpath -e "$path") == "$root/"* ]] || exit 2; done
python3 -B "$release/replication/development/ideal-baseline/prepare.py" plan "$key" "$root/jobs/PLANNED-ideal-$key-$mode/case" "$mode"
minutes=30
if [[ "$mode" == full ]]; then
    [[ "$smoke" =~ ^[0-9]+$ ]] || exit 2
    grep -q '^PASS: ideal baseline phi110 smoke;' "$root/jobs/$smoke/result.txt"
    grep -Fx "source=$(cat "$release/SOURCE_REVISION")" "$root/jobs/$smoke/validation-inputs.txt"
    minutes=360
fi
args=(--parsable --partition=kshcnormal --nodes=1 --ntasks=1 --cpus-per-task=8 --time="$minutes"
    --job-name="rfideal-$key-$mode" --chdir="$root" --output="$root/logs/%x-%j.out" --error="$root/logs/%x-%j.err"
    "$release/replication/environment/job.sh" "$root" "$image" "$release" validation 124657926 "ideal-baseline-$key-$mode")
printf 'sbatch '; printf '%q ' "${args[@]}"; printf '\n'
if [[ "$action" == apply ]]; then
    ledger="$root/results/ideal-baseline-reservations.tsv"
    exec 9>"$ledger.lock"; flock -x 9
    sha=$(cat "$release/SOURCE_REVISION")
    if [[ -f "$ledger" ]] && awk -F '\t' -v sha="$sha" -v key="$key-$mode" '$3==sha && $4==key{found=1} END{exit !found}' "$ledger"; then
        echo 'Already submitted; inspect ledger' >&2; exit 2
    fi
    id=$(sbatch "${args[@]}")
    printf '%s\t%s\t%s\t%s\n' "$id" "$((8*minutes/60))" "$sha" "$key-$mode" >> "$ledger"
    echo "SUBMITTED $id $key $mode"
fi
