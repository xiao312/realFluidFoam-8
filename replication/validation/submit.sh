#!/bin/bash
set -euo pipefail
action=${1:?plan or apply}; root=${2:?root}; image=${3:?runtime}; release=${4:?release}
build=${5:?completed build job}; stage=${6:?stage}; partition=${7:?partition}
[[ "$action" == plan || "$action" == apply ]] || exit 2
[[ "$build" =~ ^[0-9]+$ && "$partition" =~ ^[a-zA-Z0-9_-]+$ ]] || exit 2
[[ "$stage" == properties ]] || { echo "Unsupported stage: $stage" >&2; exit 2; }
scripts=$(cd -- "$(dirname -- "$0")/../environment" && pwd)
bash "$scripts/workspace.sh" plan "$root" >/dev/null
for path in "$image" "$release"; do
    [[ $(realpath -e -- "$path") == "$root/"* ]] || exit 2
done
grep -q '^PASS: build,' "$root/jobs/$build/result.txt"
cpus=2; limit=00:20:00
args=(--parsable --partition="$partition" --nodes=1 --ntasks=1 --cpus-per-task="$cpus"
    --time="$limit" --job-name="rf8-$stage" --chdir="$root"
    --output="$root/logs/%x-%j.out" --error="$root/logs/%x-%j.err"
    "$scripts/job.sh" "$root" "$image" "$release" validation "$build" "$stage")
printf 'sbatch '; printf '%q ' "${args[@]}"; printf '\n'
if [[ "$action" == apply ]]; then sbatch "${args[@]}"; fi
