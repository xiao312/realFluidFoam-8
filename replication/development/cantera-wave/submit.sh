#!/bin/bash
set -euo pipefail
action=${1:?}; root=${2:?}; release=${3:?}; library=${4:?}
increments=${5:?}; properties=${6:?}; profile=${7:?}; results=${8:?}; velocity=${9:?}
family=${10:-native}; bridge=${11:-none}
step_ns=${12:-50}
[[ $step_ns == 5 || $step_ns == 50 ]] || exit 2
wall_time=01:00:00
[[ $step_ns != 5 ]] || wall_time=08:00:00
[[ $action == plan || $action == apply ]] || exit 2
[[ $library =~ ^[0-9]+$ && $increments =~ ^[0-9]+$ && $properties =~ ^[0-9]+$ ]] || exit 2
[[ $velocity == travelling || $velocity == zero ]] || exit 2
[[ $family == native || $family == cantera ]] || exit 2
[[ ( $family == native && $bridge == none ) || ( $family == cantera && $bridge =~ ^[0-9]+$ ) ]] || exit 2
root=$(realpath -e "$root")
[[ $root == */FlamePilot/trials/realfluidfoam ]] || exit 2
for path in "$release" "$profile" "$results"; do
 [[ $(realpath -e "$path") == "$root/"* ]] || exit 2
done
sha=$(cat "$release/SOURCE_REVISION")
[[ $sha =~ ^[0-9a-f]{40}$ ]] || exit 2
ledger=$root/results/cantera-wave-${sha:0:12}-$library-$velocity-$family-$bridge-${step_ns}ns.txt
[[ ! -e $ledger ]] || { echo "Already submitted: $ledger" >&2; exit 2; }
printf 'PLAN: phi110 paired Cantera profile; velocity=%s; transport=%s; bridge=%s; original zero; 8 distinct CPUs; 20 us; maxDeltaT=%s ns; wall cap=%s; library=%s; tests=%s,%s\n' "$velocity" "$family" "$bridge" "$step_ns" "$wall_time" "$library" "$increments" "$properties"
[[ $action == apply ]] || exit 0
grep -q '^PASS: build,' "$root/jobs/$library/result.txt"
for test_job in "$increments" "$properties"; do
 grep -q '^PASS:' "$root/jobs/$test_job/result.txt"
 grep -q "^build_job=$library$" "$root/jobs/$test_job/validation-inputs.txt"
done
if [[ $family == cantera ]]; then
 grep -q '^PASS: C ABI' "$root/jobs/$bridge/result.txt"
 (cd "$root/jobs/$bridge"; sha256sum -c binary.sha256)
 cmp "$root/cache/cantera-liang-20261019/inputs/ideal.yaml" "$root/cache/cantera-liang-20261019/sweep-inputs-v2/phi110/ideal.yaml"
fi
job=$(sbatch --parsable --partition=kshcnormal --nodes=1 --ntasks=1 --cpus-per-task=8 \
 --time="$wall_time" --chdir="$root" --job-name="rf-wave-$velocity-$family-${step_ns}ns" \
 --output="$root/logs/%x-%j.out" --error="$root/logs/%x-%j.err" \
 "$release/replication/development/cantera-wave/job.sh" \
 "$root" "$release" "$library" "$profile" "$results" "$velocity" "$family" "$bridge" "$step_ns")
job=${job%%;*}; [[ $job =~ ^[0-9]+$ ]] || exit 2
printf '%s\n' "$job" > "$ledger"
printf '%s\n' "$job"
