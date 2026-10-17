#!/bin/bash
set -euo pipefail
action=${1:?plan or apply}; root=${2:?root}; image=${3:?image}; release=${4:?release}
build=${5:?build}; key=${6:?case}; mode=${7:?mode}; partition=${8:?partition}; budget=${9:?cap}; smoke=${10:-}
[[ "$action" == plan || "$action" == apply ]] || exit 2
[[ "$mode" == smoke || "$mode" == full ]] || exit 2
[[ "$build" =~ ^[0-9]+$ && "$partition" =~ ^[a-zA-Z0-9_-]+$ && "$key" =~ ^[a-z0-9-]+$ ]] || exit 2
module="$release/replication/validation/flames/paper-campaign"
scripts="$release/replication/environment"
bash "$scripts/workspace.sh" plan "$root" >/dev/null
for path in "$image" "$release"; do
    [[ $(realpath -e -- "$path") == "$root/"* ]] || exit 2
done
grep -q '^PASS: build,' "$root/jobs/$build/result.txt"
python3 -B "$module/prepare.py" plan "$key" "$root/jobs/PLANNED/paper-cases" "$mode"
family=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["family"])' "$module/cases/$key.json")
ranks=4; minutes=480
if [[ "$family" == counterflow ]]; then ranks=8; minutes=720; fi
[[ "$mode" != smoke ]] || minutes=30
if [[ "$mode" == full ]]; then
    [[ "$smoke" =~ ^[0-9]+$ ]] || { echo 'Full run requires passed smoke job ID' >&2; exit 2; }
    grep -q '^PASS: paper case .* smoke;' "$root/jobs/$smoke/result.txt"
    python3 - "$root/jobs/$smoke/paper-cases/paper-case.json" "$module/cases/$key.json" "$key" <<'PY'
import json,sys
a=json.load(open(sys.argv[1])); b=json.load(open(sys.argv[2]))
if a['mode']!='smoke' or a['configuration']['family']!=b['family']: raise SystemExit('Wrong smoke family')
if b['family']=='counterflow' and a['key']!=sys.argv[3]: raise SystemExit('Wrong counterflow smoke condition')
PY
    grep -Fx "source=$(cat "$release/SOURCE_REVISION")" "$root/jobs/$smoke/validation-inputs.txt"
fi
ledger="$root/results/campaign-reservations-20261017.tsv"
check_budget() {
python3 - "$ledger" "$budget" "$ranks" "$minutes" <<'PY'
import math,sys
from pathlib import Path
p=Path(sys.argv[1]); cap=float(sys.argv[2]); reserve=int(sys.argv[3])*int(sys.argv[4])/60
used=sum(float(l.split('\t')[2]) for l in p.read_text().splitlines()) if p.exists() else 0
if not math.isfinite(cap) or not 0<cap<=1000 or used+reserve>cap: raise SystemExit('Campaign reservation exceeds authorized cap')
print('Reserved %.3f + new %.3f core-hours; cap %.3f' % (used,reserve,cap))
PY
}
check_budget
args=(--parsable --partition="$partition" --nodes=1 --ntasks=1 --cpus-per-task="$ranks" --time="$minutes"
    --job-name="rf8-$key-$mode" --chdir="$root" --output="$root/logs/%x-%j.out" --error="$root/logs/%x-%j.err"
    "$scripts/job.sh" "$root" "$image" "$release" validation "$build" "paper-$key-$mode")
printf 'sbatch '; printf '%q ' "${args[@]}"; printf '\n'
if [[ "$action" == apply ]]; then
    exec 9>"$ledger.lock"; flock -x 9
    check_budget
    id=$(sbatch "${args[@]}")
    cost=$(python3 -c 'import sys;print(int(sys.argv[1])*int(sys.argv[2])/60)' "$ranks" "$minutes")
    printf '%s\tpaper-%s-%s\t%s\t%s\n' "$id" "$key" "$mode" "$cost" "$(cat "$release/SOURCE_REVISION")" >> "$ledger"
    printf 'Submitted %s\n' "$id"
fi
