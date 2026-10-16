#!/bin/bash
# Read-only plan by default. Prepare creates only paths below the selected root.
set -euo pipefail
mode=${1:-plan}
requested=${2:?Usage: workspace.sh plan|prepare /absolute/project/root}
[[ "$mode" == plan || "$mode" == prepare ]] || exit 2
[[ "$requested" == /* && "$requested" != / ]] || { echo 'Use an absolute project root' >&2; exit 2; }
root=$(realpath -m -- "$requested")
[[ "$root" == "$requested" && "$root" == */FlamePilot/trials/realfluidfoam ]] || {
    echo 'Root must resolve unchanged and end in /FlamePilot/trials/realfluidfoam' >&2; exit 2;
}
for name in images releases builds jobs logs cache tmp home results config; do
    path="$root/$name"
    [[ $(realpath -m -- "$path") == "$path" ]] || { echo "Symlink escape: $path" >&2; exit 2; }
    printf '%s\n' "$path"
done
if [[ "$mode" == prepare ]]; then
    mkdir -p -- "$root"/{images,releases,builds,jobs,logs,cache,tmp,home,results,config}
fi
