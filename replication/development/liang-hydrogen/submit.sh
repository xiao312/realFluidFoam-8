#!/bin/bash
set -euo pipefail
mode=${1:?}; root=${2:?}; release=${3:?}; sdk=${4:?}; inputs=${5:?}
action=${6:?}; build=${7:?}; partition=${8:?}; phi=${9:-1.0}
guess=${10:--}; width=${11:-0.01}; tu=${12:-298}
variant=${13:-baseline}
grid_factor=${14:-1}
steady_rtol=${15:-1e-5}; steady_atol=${16:-1e-11}
[[ $mode == plan || $mode == apply ]] || exit 2
[[ $action =~ ^(build|1|2|3|3star|4|5)$ ]] || exit 2
[[ $partition =~ ^[a-zA-Z0-9_-]+$ ]] || exit 2
[[ $(realpath -e "$root") == "$root" ]] || exit 2
for path in "$release" "$sdk" "$inputs"; do
 [[ $(realpath -e "$path") == "$root/"* ]] || exit 2
done
test -f "$release/SOURCE_REVISION"
test -f "$inputs/manifest.json"
if [[ $action != build ]]; then
 [[ $(realpath -e "$build") == "$root/jobs/"* ]] || exit 2
 test -f "$build/build-passed.txt"
fi
[[ $grid_factor == 1 || $grid_factor == 2 || $grid_factor == 4 ]] || exit 2
printf 'PLAN case=%s phi=%s width=%s Tu=%s variant=%s grid_factor=%s rtol=%s atol=%s; 1 CPU, 1 hour; inputs=%s; source=%s\n' \
 "$action" "$phi" "$width" "$tu" "$variant" "$grid_factor" "$steady_rtol" "$steady_atol" "$inputs" "$(cat "$release/SOURCE_REVISION")"
[[ $mode == apply ]] || exit 0
sbatch --parsable --partition="$partition" --nodes=1 --ntasks=1 --cpus-per-task=1 \
 --time=01:00:00 --job-name="liang-h2-$action-$phi" --chdir="$root" \
 --output="$root/logs/%j-hydrogen.out" --error="$root/logs/%j-hydrogen.err" \
 "$release/replication/development/liang-hydrogen/job.sh" \
 "$root" "$release" "$sdk" "$inputs" "$action" "$build" "$phi" "$guess" "$width" "$tu" "$variant" "$grid_factor" "$steady_rtol" "$steady_atol"
