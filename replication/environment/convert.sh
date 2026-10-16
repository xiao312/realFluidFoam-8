#!/bin/bash
# Convert the verified offline archive on a compute node.
set -euo pipefail
action=${1:-plan}; root=${2:?root}; archive=${3:?archive}; digest=${4:?sha256}; partition=${5:?partition}
[[ "$action" == plan || "$action" == apply ]] || exit 2
[[ "$digest" =~ ^[0-9a-f]{64}$ && "$partition" =~ ^[a-zA-Z0-9_-]+$ ]] || exit 2
script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
bash "$script_dir/workspace.sh" plan "$root" >/dev/null
[[ $(realpath -e -- "$archive") == "$root/images/"* ]] || exit 2
[[ ! -e "$root/images/openfoam8.sif" ]] || { echo 'Image exists; use a new versioned project/image path' >&2; exit 2; }
args=(--parsable --partition="$partition" --nodes=1 --ntasks=1 --cpus-per-task=4
    --time=00:30:00 --job-name=rf8-image --chdir="$root"
    --output="$root/logs/%x-%j.out" --error="$root/logs/%x-%j.err"
    "$script_dir/convert-job.sh" "$root" "$archive" "$digest" "$script_dir")
printf 'sbatch '; printf '%q ' "${args[@]}"; printf '\n'
if [[ "$action" == apply ]]; then sbatch "${args[@]}"; fi
