#!/bin/bash
set -euo pipefail
action=${1:-plan}; root=${2:?root}; image=${3:?image}; source_dir=${4:?source}
mode=${5:?preflight or build}; partition=${6:?partition}
[[ "$action" == plan || "$action" == apply ]] || exit 2
[[ "$mode" == preflight || "$mode" == build ]] || exit 2
[[ "$partition" =~ ^[a-zA-Z0-9_-]+$ ]] || exit 2
script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
bash "$script_dir/workspace.sh" plan "$root" >/dev/null
for path in "$image" "$source_dir"; do
    [[ $(realpath -e -- "$path") == "$root/"* ]] || exit 2
done
cpus=2; limit=00:10:00
if [[ "$mode" == build ]]; then cpus=16; limit=01:00:00; fi
args=(--parsable --partition="$partition" --nodes=1 --ntasks=1 --cpus-per-task="$cpus"
    --time="$limit" --job-name="rf8-$mode" --chdir="$root"
    --output="$root/logs/%x-%j.out" --error="$root/logs/%x-%j.err"
    "$script_dir/job.sh" "$root" "$image" "$source_dir" "$mode")
printf 'sbatch '; printf '%q ' "${args[@]}"; printf '\n'
if [[ "$action" == apply ]]; then sbatch "${args[@]}"; fi
