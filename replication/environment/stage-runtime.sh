#!/bin/bash
# Extract once on a compute node where direct SIF mounts are prohibited.
set -euo pipefail
action=${1:-plan}; root=${2:?root}; image=${3:?SIF}; runtime=${4:?new runtime directory}; partition=${5:?partition}
[[ "$action" == plan || "$action" == apply ]] || exit 2
[[ "$partition" =~ ^[a-zA-Z0-9_-]+$ ]] || exit 2
script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
bash "$script_dir/workspace.sh" plan "$root" >/dev/null
[[ -f "$image" && $(realpath -e -- "$image") == "$root/images/"* ]] || exit 2
[[ $(realpath -m -- "$runtime") == "$runtime" && $(dirname -- "$runtime") == "$root/images" ]] || exit 2
[[ ! -e "$runtime" && ! -e "$runtime.ready" ]] || exit 2
args=(--parsable --partition="$partition" --nodes=1 --ntasks=1 --cpus-per-task=4
    --time=02:00:00 --job-name=rf8-runtime --chdir="$root"
    --output="$root/logs/%x-%j.out" --error="$root/logs/%x-%j.err"
    "$script_dir/stage-runtime-job.sh" "$root" "$image" "$runtime" "$script_dir/workspace.sh")
printf 'sbatch '; printf '%q ' "${args[@]}"; printf '\n'
if [[ "$action" == apply ]]; then sbatch "${args[@]}"; fi
