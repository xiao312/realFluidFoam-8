#!/bin/bash
set -euo pipefail
action=${1:?plan/apply}; root=${2:?}; image=${3:?}; release=${4:?}; key=${5:?}
mode=${6:-smoke}; smoke=${7:-}
[[ "$action" == plan || "$action" == apply ]] || exit 2
[[ "$mode" == smoke || "$mode" == full ]] || exit 2
[[ "$key" =~ ^phi-[0-9]{3}-(u010|u020|liang)$ ]] || exit 2
bash "$release/replication/environment/workspace.sh" plan "$root" >/dev/null
for path in "$image" "$release"; do [[ $(realpath -e "$path") == "$root/"* ]] || exit 2; done
minutes=60
if [[ "$mode" == full ]]; then
    [[ "$smoke" =~ ^[0-9]+$ ]] || { echo 'Passed smoke ID required' >&2; exit 2; }
    grep -q "^PASS: inlet $key startup;" "$root/jobs/$smoke/result.txt"
    grep -q '^build_job=124657926$' "$root/jobs/$smoke/validation-inputs.txt"
    python3 -B "$release/replication/development/premixed-inlet/qualify.py" "$release" "$key" "$root/jobs/$smoke"
    minutes=2880
fi
python3 -B "$release/replication/development/premixed-inlet/prepare.py" plan "$key" "$root/jobs/PLANNED-inlet-$key/case" "$mode"
args=(--parsable --partition=kshcnormal --nodes=1 --ntasks=1 --cpus-per-task=4 --time="$minutes"
    --job-name="rfdev-$key-$mode" --chdir="$root" --output="$root/logs/%x-%j.out" --error="$root/logs/%x-%j.err"
    "$release/replication/environment/job.sh" "$root" "$image" "$release" validation 124657926 "dev-inlet-$key-$mode")
printf 'sbatch '; printf '%q ' "${args[@]}"; printf '\n'
if [[ "$action" == apply ]]; then
    ledger="$root/results/development-reservations.tsv"
    exec 9>"$ledger.lock"; flock -x 9
    sha=$(cat "$release/SOURCE_REVISION")
    if [[ -f "$ledger" ]] && grep -q "$(printf '\t%s-%s\t%s$' "$key" "$mode" "$sha")" "$ledger"; then
        echo 'Submission already recorded for this key/source; inspect it before retrying' >&2; exit 2
    fi
    id=$(sbatch "${args[@]}")
    cost=$((minutes*4/60))
    printf '%s\t%s\t%s-%s\t%s\n' "$id" "$cost" "$key" "$mode" "$sha" >> "$ledger"
    echo "SUBMITTED $key $mode $id ($cost core-hours maximum)"
fi
