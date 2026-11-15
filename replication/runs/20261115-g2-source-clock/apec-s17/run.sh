#!/usr/bin/env bash
set -euo pipefail
mode=${1:?};nx=${2:?};end=${3:?}
input=/workspace/inputs/apec-s17;build=/workspace/build/apec-s17;out=/workspace/results/apec-s17
case=/workspace/cases/contact-apec-s17-$mode-oxygen-$nx
driver=$build/source/replication/validation/schmitt-contact
cells=400;[[ $mode != grid800 ]] || cells=800;[[ $mode != grid1600 ]] || cells=1600
[[ ! -e $case ]]
node "$driver/prepare.mjs" --thermo-dir "$input/contact-thermo" --kind oxygen --nx "$nx" --cells "$cells" > "$out/$mode-$nx-plan.json"
node "$driver/prepare.mjs" --thermo-dir "$input/contact-thermo" --kind oxygen --nx "$nx" --cells "$cells" --out "$case" > "$out/$mode-$nx-preparation.json"
flags=();[[ $mode != uniform ]] || flags+=(--uniform);[[ $mode != baseline ]] || flags+=(--uncorrected)
node "$driver/apec/configure.mjs" "$case" "$end" "${flags[@]}" > "$out/$mode-$nx-control-plan.json"
node "$driver/apec/configure.mjs" "$case" "$end" "${flags[@]}" --apply > "$out/$mode-$nx-control.json"
blockMesh -case "$case" > "$case/log.blockMesh" 2>&1
checkMesh -case "$case" > "$case/log.checkMesh" 2>&1
"$build/bin/initializeSchmittContact" -case "$case" > "$case/log.initialize" 2>&1
(cd "$case";find 0 constant system -type f -print0 | sort -z | xargs -0 sha256sum > active-timezero.sha256)
if timeout --signal=TERM --kill-after=15 600 "$build/bin/realFluidContactAPEC" -case "$case" > "$case/log.solver" 2>&1;then rc=0;else rc=$?;fi
printf '%s\n' "$rc" > "$case/solver-exit.txt"
printf '{"mode":"%s","nx":%s,"solverExit":%s,"startTime":0,"requestedEnd":%s,"scientificAcceptance":false}\n' "$mode" "$nx" "$rc" "$end" > "$out/$mode-$nx-result.json"
tail -8 "$case/log.solver"
[[ $rc == 0 ]]
node "$input/check.mjs" "$case" "$mode" > "$out/$mode-$nx-check.json"
