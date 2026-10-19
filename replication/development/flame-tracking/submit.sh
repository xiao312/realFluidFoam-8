#!/bin/bash
set -Eeuo pipefail
action=${1:?}; root=${2:?}; image=${3:?}; release=${4:?}; key=${5:?}; build=${6:-}
[[ "$action" == plan || "$action" == apply ]] || exit 2
bash "$release/replication/environment/workspace.sh" plan "$root" >/dev/null
for path in "$image" "$release"; do [[ $(realpath -e "$path") == "$root/"* ]] || exit 2; done
minutes=30; selector=qualify; casekey=phi110; mode=qualify
if [[ "$key" != qualify ]]; then
    [[ "$key" =~ ^phi[0-9]{3}$ && "$build" =~ ^[0-9]+$ ]] || exit 2
    grep -q '^PASS: tracking qualify' "$root/jobs/$build/result.txt"
    minutes=360; selector="$key-$build"; casekey=$key; mode=full
fi
python3 -B "$release/replication/development/flame-tracking/prepare.py" plan "$root/jobs/PLANNED-tracking-$key" "$casekey" "$mode" --root "$root"
args=(--parsable --partition=kshcnormal --nodes=1 --ntasks=1 --cpus-per-task=8 --time="$minutes"
    --job-name="rftracking-$key" --chdir="$root" --output="$root/logs/%x-%j.out" --error="$root/logs/%x-%j.err"
    "$release/replication/environment/job.sh" "$root" "$image" "$release" validation 124657926 "flame-tracking-$selector")
printf 'sbatch '; printf '%q ' "${args[@]}"; printf '\n'
if [[ "$action" == apply ]]; then
    ledger="$root/results/flame-tracking-reservations.tsv"
    exec 9>"$ledger.lock"; flock -x 9
    sha=$(cat "$release/SOURCE_REVISION")
    if [[ -f "$ledger" ]] && awk -F '\t' -v sha="$sha" -v key="$key" '$3==sha && $4==key{found=1} END{exit !found}' "$ledger"; then
        echo 'Already submitted; inspect ledger' >&2; exit 2
    fi
    id=$(sbatch "${args[@]}")
    printf '%s\t%s\t%s\t%s\t%s\n' "$id" "$((8*minutes/60))" "$sha" "$key" "$build" >> "$ledger"
    echo "SUBMITTED $id $key"
fi
