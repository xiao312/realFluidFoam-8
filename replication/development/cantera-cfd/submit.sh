#!/bin/bash
set -euo pipefail
action=${1:?}; root=${2:?}; release=${3:?}; bridge_job=${4:?}; key=${5:?}; mode=${6:-build}; build_job=${7:-none}
chemistry=${8:-native}; reactor_job=${9:-none}
execution=${10:-uniform8}
[[ $action == plan || $action == apply ]] || exit 2
[[ $mode == build || $mode == full ]] || exit 2
[[ $chemistry == native || $chemistry == adiabaticCP ]] || exit 2
[[ $execution == uniform8 || $execution == bands32 ]] || exit 2
ranks=8; [[ $execution == bands32 ]] && ranks=32
[[ $bridge_job =~ ^[0-9]+$ && $key =~ ^phi(090|095|100|105|110|115|120|125|130|135|140)$ ]] || exit 2
root=$(realpath -e "$root")
[[ $(realpath -e "$release") == "$root/releases/"* ]] || exit 2
test -f "$root/jobs/$bridge_job/result.txt"
if [[ $chemistry == adiabaticCP ]]; then
 [[ $reactor_job =~ ^[0-9]+$ ]] || exit 2
 test -f "$root/jobs/$reactor_job/result.txt"
 python3 - "$root/jobs/$reactor_job/ideal.json" "$root/jobs/$bridge_job/librfcantera.so" <<'PY'
import hashlib,json,sys
assert json.load(open(sys.argv[1]))['library_sha256']==hashlib.sha256(open(sys.argv[2],'rb').read()).hexdigest(), 'Reactor qualification belongs to a different library'
PY
fi
if [[ $mode == full ]]; then
 [[ $build_job =~ ^[0-9]+$ ]] || exit 2
 test -f "$root/jobs/$build_job/qualification-passed.txt"
 grep -q '"chemistry_mode": "'"$chemistry"'"' "$root/jobs/$build_job/bridge-inputs.json"
 if [[ $execution == bands32 ]]; then
  grep -q '"execution_profile": "bands32"' "$root/jobs/$build_job/bridge-inputs.json"
 else
  ! grep -q '"execution_profile": "bands32"' "$root/jobs/$build_job/bridge-inputs.json"
 fi
fi
hours=1; [[ $mode == full ]] && hours=8
echo "PLAN: $mode ideal Cantera transport + $chemistry chemistry, $key, original-zero fields; $ranks cores; $execution; $hours hours; bridge=$bridge_job; source=$release"
[[ $action == apply ]] || exit 0
sbatch --parsable --partition=kshcnormal --cpus-per-task="$ranks" --time="$hours:00:00" \
 --chdir="$root" --job-name="rf-ct-$mode-$key" --output="$root/logs/ct-cfd-%j.out" \
 --error="$root/logs/ct-cfd-%j.err" "$release/replication/development/cantera-cfd/job.sh" \
 "$root" "$release" "$bridge_job" "$key" "$mode" "$build_job" "$chemistry" "$reactor_job" "$execution"
