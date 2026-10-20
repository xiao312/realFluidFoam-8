#!/bin/bash
set -euo pipefail
mode=${1:?}; root=${2:?}; release=${3:?}; sdk=${4:?}; mechanism=${5:?}
action=${6:?}; build=${7:?}; partition=${8:?}; phi=${9:-1.1}
guess=${10:--}
[[ $mode == plan || $mode == apply ]] || exit 2
[[ $action == build || $action == flame ]] || exit 2
[[ $partition =~ ^[a-zA-Z0-9_-]+$ ]] || exit 2
[[ $(realpath -e "$root") == "$root" ]] || exit 2
for path in "$release" "$sdk" "$mechanism"; do
 [[ $(realpath -e "$path") == "$root/"* ]] || exit 2
done
test -f "$release/SOURCE_REVISION"
test -f "$mechanism"
sha=$(sha256sum "$mechanism" | cut -d' ' -f1)
if [[ $(basename "$mechanism") == hp-2017-fixed-100atm.yaml ]]; then
 [[ $sha == cc34fbe54bfe71c79edabc6763934bdfbe4d1046ae5e33f67ca1efae02aa9afb ]] || exit 2
fi
if [[ $guess != - ]]; then
 [[ $(realpath -e "$guess") == "$root/"* ]] || exit 2
 test -f "$guess"
fi
if [[ $action == flame ]]; then
 [[ $(realpath -e "$build") == "$root/jobs/"* ]] || exit 2
 test -f "$build/build-passed.txt"
fi
memory_mb=16384; cpus=5
if [[ $action == build ]]; then memory_mb=3072; cpus=1; fi
printf 'PLAN %s phi=%s; 100 atm, 298 K, 1 compute thread, %s allocated CPUs, 2 hours, %s MiB; mechanism_sha=%s; source=%s\n' \
 "$action" "$phi" "$cpus" "$memory_mb" "$sha" "$(cat "$release/SOURCE_REVISION")"
[[ $mode == apply ]] || exit 0
sbatch --parsable --partition="$partition" --nodes=1 --ntasks=1 --cpus-per-task="$cpus" \
 --time=02:00:00 --mem="${memory_mb}M" --job-name="liang-kinetics-$phi" --chdir="$root" \
 --output="$root/logs/%j-kinetics.out" --error="$root/logs/%j-kinetics.err" \
 "$release/replication/development/liang-kinetics/job.sh" \
 "$root" "$release" "$sdk" "$mechanism" "$action" "$build" "$phi" "$sha" "$guess"
