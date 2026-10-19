#!/bin/bash
set -Eeuo pipefail
action=${1:?}; root=${2:?}; image=${3:?}; release=${4:?}; key=${5:?}; mode=${6:?}; smoke=${7:-}
[[ "$action" == plan || "$action" == apply ]] || exit 2
[[ "$key" == phi110-dt100 || "$key" == phi110-dt050 ]] || exit 2
[[ "$mode" == smoke || "$mode" == full ]] || exit 2
bash "$release/replication/environment/workspace.sh" plan "$root" >/dev/null
for path in "$image" "$release"; do [[ $(realpath -e "$path") == "$root/"* ]] || exit 2; done
minutes=60
if [[ "$mode" == full ]]; then
    [[ "$smoke" =~ ^[0-9]+$ ]] || exit 2
    grep -q "^PASS: paper premixed $key smoke;" "$root/jobs/$smoke/result.txt"
    grep -Fx "source=$(cat "$release/SOURCE_REVISION")" "$root/jobs/$smoke/validation-inputs.txt"
    minutes=1440
fi
python3 -B "$release/replication/development/premixed-paper/prepare.py" plan "$key" "$root/jobs/PLANNED-paper-$key-$mode/case" "$mode"
args=(--parsable --partition=kshcnormal --nodes=1 --ntasks=1 --cpus-per-task=8 --time="$minutes"
    --job-name="rfpaper-$key-$mode" --chdir="$root" --output="$root/logs/%x-%j.out" --error="$root/logs/%x-%j.err"
    "$release/replication/environment/job.sh" "$root" "$image" "$release" validation 124657926 "paper-premixed-$key-$mode")
printf 'sbatch '; printf '%q ' "${args[@]}"; printf '\n'
if [[ "$action" == apply ]]; then
    ledger="$root/results/paper-premixed-reservations.tsv"
    exec 9>"$ledger.lock"; flock -x 9
    sha=$(cat "$release/SOURCE_REVISION")
    if [[ -f "$ledger" ]] && grep -q "$(printf '\t%s\t%s$' "$key-$mode" "$sha")" "$ledger"; then
        echo 'Submission already recorded; inspect before retrying' >&2; exit 2
    fi
    id=$(sbatch "${args[@]}")
    printf '%s\t%s\t%s\t%s\n' "$id" "$((8*minutes/60))" "$key-$mode" "$sha" >> "$ledger"
    echo "SUBMITTED $id"
fi
