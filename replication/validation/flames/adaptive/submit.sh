#!/bin/bash
set -euo pipefail
action=${1:?plan/apply}; root=${2:?}; image=${3:?}; release=${4:?}; key=${5:?}; mode=${6:?}; smoke=${7:-}
[[ "$action" == plan || "$action" == apply ]] || exit 2
[[ "$mode" == smoke || "$mode" == full ]] || exit 2
scripts="$release/replication/environment"
bash "$scripts/workspace.sh" plan "$root" >/dev/null
for path in "$image" "$release"; do [[ $(realpath -e "$path") == "$root/"* ]] || exit 2; done
module="$release/replication/validation/flames/adaptive"
python3 -B "$module/prepare.py" plan "$root" "$key" "$root/jobs/PLANNED-$key/case" "$mode"
ranks=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))[sys.argv[2]]["ranks"])' "$module/cases.json" "$key")
minutes=30
if [[ "$mode" == full ]]; then
    minutes=2880
    [[ "$smoke" =~ ^[0-9]+$ ]] || { echo 'Matching passed smoke job required' >&2; exit 2; }
    grep -q "^PASS: adaptive $key smoke;" "$root/jobs/$smoke/result.txt"
    grep -q '^build_job=124657926$' "$root/jobs/$smoke/validation-inputs.txt"
    python3 - "$module/cases.json" "$key" "$root/jobs/$smoke/case/restart.json" <<'PY'
import json,sys
current=json.load(open(sys.argv[1]))[sys.argv[2]]
previous=json.load(open(sys.argv[3]))
assert previous['key']==sys.argv[2] and previous['mode']=='smoke'
assert previous['config']==current,'Smoke configuration differs from continuation'
PY
fi
args=(--parsable --partition=kshcnormal --nodes=1 --ntasks=1 --cpus-per-task="$ranks" --time="$minutes"
    --job-name="rf8-ad-$key-$mode" --chdir="$root" --output="$root/logs/%x-%j.out" --error="$root/logs/%x-%j.err"
    "$scripts/job.sh" "$root" "$image" "$release" validation 124657926 "adaptive-$key-$mode")
printf 'sbatch '; printf '%q ' "${args[@]}"; printf '\n'
if [[ "$action" == apply ]]; then
    ledger="$root/results/adaptive-reservations-20261018.tsv"
    exec 9>"$ledger.lock"; flock -x 9
    if [[ -f "$ledger" ]] && grep -q "$(printf '\t%s\t%s\t.*\t%s$' "$key" "$mode" "$(cat "$release/SOURCE_REVISION")")" "$ledger"; then
        echo "A $key $mode submission is already recorded; inspect it before retrying" >&2; exit 2
    fi
    id=$(sbatch "${args[@]}")
    cost=$(python3 -c 'import sys;print(int(sys.argv[1])*int(sys.argv[2])/60)' "$ranks" "$minutes")
    printf '%s\t%s\t%s\t%s\t%s\n' "$id" "$key" "$mode" "$cost" "$(cat "$release/SOURCE_REVISION")" >> "$ledger"
    echo "SUBMITTED $key $mode $id"
fi
