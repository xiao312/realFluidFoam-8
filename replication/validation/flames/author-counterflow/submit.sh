#!/bin/bash
set -euo pipefail
action=${1:?plan or apply}; root=${2:?root}; image=${3:?image}; release=${4:?release}
build=${5:?build}; mode=${6:?smoke or full}; partition=${7:?partition}; budget=${8:?cap}
[[ "$action" == plan || "$action" == apply ]] || exit 2
[[ "$mode" == smoke || "$mode" == full ]] || exit 2
[[ "$build" =~ ^[0-9]+$ && "$partition" =~ ^[a-zA-Z0-9_-]+$ ]] || exit 2
scripts="$release/replication/environment"
bash "$scripts/workspace.sh" plan "$root" >/dev/null
for path in "$image" "$release"; do
    [[ $(realpath -e -- "$path") == "$root/"* ]] || exit 2
done
grep -q '^PASS: build,' "$root/jobs/$build/result.txt"
python3 -B "$release/replication/validation/flames/author-counterflow/prepare.py" plan "$root/jobs/PLANNED/author-cases" "$mode"
minutes=30; [[ "$mode" != full ]] || minutes=720
ledger="$root/results/campaign-reservations-20261017.tsv"
check_budget() {
python3 - "$ledger" "$budget" "$minutes" <<'PY'
import math,sys
from pathlib import Path
p=Path(sys.argv[1]); cap=float(sys.argv[2]); reserve=8*int(sys.argv[3])/60
used=sum(float(l.split('\t')[2]) for l in p.read_text().splitlines()) if p.exists() else 0
if not math.isfinite(cap) or cap<=0 or used+reserve>cap:raise SystemExit('Counterflow budget exceeded/invalid')
print('Reserved %.3f + new %.3f core-hours; cap %.3f' % (used,reserve,cap))
PY
}
check_budget
args=(--parsable --partition="$partition" --nodes=1 --ntasks=1 --cpus-per-task=8 --time="$minutes"
    --job-name="rf8-author-$mode" --chdir="$root" --output="$root/logs/%x-%j.out" --error="$root/logs/%x-%j.err"
    "$scripts/job.sh" "$root" "$image" "$release" validation "$build" "author-counterflow-$mode")
printf 'sbatch '; printf '%q ' "${args[@]}"; printf '\n'
if [[ "$action" == apply ]]; then
    exec 9>"$ledger.lock"; flock -x 9
    check_budget
    id=$(sbatch "${args[@]}")
    cost=$(python3 -c 'import sys; print(8*int(sys.argv[1])/60)' "$minutes")
    printf '%s\tauthor-%s\t%s\t%s\n' "$id" "$mode" "$cost" "$(cat "$release/SOURCE_REVISION")" >> "$ledger"
    printf 'Submitted %s\n' "$id"
fi
