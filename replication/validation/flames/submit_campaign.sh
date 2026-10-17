#!/bin/bash
# Configured job submission. Every apply requires an explicit owner-selected budget.
set -euo pipefail
action=${1:?plan or apply}; root=${2:?root}; image=${3:?runtime}; release=${4:?release}
build=${5:?build job}; name=${6:?campaign configuration name}; partition=${7:?partition}
budget=${8:?approved total core-hour budget}
[[ "$action" == plan || "$action" == apply ]] || exit 2
[[ "$name" =~ ^[a-z0-9-]+$ && "$build" =~ ^[0-9]+$ && "$partition" =~ ^[a-zA-Z0-9_-]+$ ]] || exit 2
scripts=$(cd -- "$(dirname -- "$0")/../../environment" && pwd)
bash "$scripts/workspace.sh" plan "$root" >/dev/null
for path in "$image" "$release"; do
    [[ $(realpath -e -- "$path") == "$root/"* ]] || exit 2
done
grep -q '^PASS: build,' "$root/jobs/$build/result.txt"
config="$release/replication/validation/flames/campaign/$name.json"
python3 -B "$release/replication/validation/flames/campaign.py" plan "$config" \
    "$release/replication/validation/inputs" "$root/jobs/PLANNED/case"
read -r ranks minutes < <(python3 -c 'import json,sys; c=json.load(open(sys.argv[1])); print(c["ranks"],c["wall_minutes"])' "$config")
# Conservative ledger reserves full walltime, including failed jobs. Reclaiming
# measured unused reservations requires an explicit reviewed ledger update.
ledger="$root/results/campaign-reservations-20261017.tsv"
check_budget() {
    python3 - "$ledger" "$budget" "$ranks" "$minutes" <<'PY'
import math,sys
from pathlib import Path
ledger=Path(sys.argv[1]); budget=float(sys.argv[2]); reserve=int(sys.argv[3])*int(sys.argv[4])/60
if not math.isfinite(budget) or budget<=0:raise ValueError('Positive finite budget required')
used=sum(float(line.split('\t')[2]) for line in ledger.read_text().splitlines()) if ledger.exists() else 0
print('Reserved core-hours: %.3f; new maximum: %.3f; approved cap: %.3f' % (used,reserve,budget))
if used+reserve>budget:raise SystemExit('Budget exceeded; do not submit')
PY
}
check_budget
args=(--parsable --partition="$partition" --nodes=1 --ntasks=1 --cpus-per-task="$ranks"
    --time="$minutes" --job-name="rf8-$name" --chdir="$root"
    --output="$root/logs/%x-%j.out" --error="$root/logs/%x-%j.err"
    "$scripts/job.sh" "$root" "$image" "$release" validation "$build" "campaign-$name")
printf 'sbatch '; printf '%q ' "${args[@]}"; printf '\n'
if [[ "$action" == apply ]]; then
    exec 9>"$ledger.lock"
    flock -x 9
    check_budget
    id=$(sbatch "${args[@]}")
    cost=$(python3 -c 'import sys; print(int(sys.argv[1])*int(sys.argv[2])/60)' "$ranks" "$minutes")
    printf '%s\t%s\t%s\t%s\n' "$id" "$name" "$cost" "$(cat "$release/SOURCE_REVISION")" >> "$ledger"
    printf 'Submitted %s\n' "$id"
fi
