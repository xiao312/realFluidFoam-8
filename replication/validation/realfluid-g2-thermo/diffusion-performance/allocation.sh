#!/usr/bin/env bash
set -euo pipefail
manifest=${1:?manifest}; mode=${2:---plan}
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [[ $mode == --plan ]]; then
  node "$here/package.mjs" "$manifest" --plan
  node "$here/prepare-cfd.mjs" "$manifest"
  exit 0
fi
[[ $mode == --apply && -n ${SLURM_JOB_ID:-} ]] || exit 2
values=$(node "$here/package.mjs" "$manifest" --inputs); readarray -t inputs <<< "$values"
build=${inputs[1]}; out=${inputs[2]}; table=${inputs[4]}; metadata=${inputs[5]}; thermo=${inputs[6]}
export HOME=/workspace/home TMPDIR=/workspace/tmp OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
mkdir -p "$HOME" "$TMPDIR"
ulimit -c 0
stage=build
trap 'rc=$?; printf "DIFFUSION_QUAL_EXIT utc=%s stage=%s rc=%s job=%s\n" "$(date -u +%FT%TZ)" "$stage" "$rc" "$SLURM_JOB_ID"; exit "$rc"' EXIT
bash -euo pipefail "$here/build.sh" "$manifest" --apply
export LD_LIBRARY_PATH="$build/lib:/opt/gcc-11.2.0/lib64:${LD_LIBRARY_PATH:-}"
probe="$build/bin/realFluidG2ThermoProbe"; solver="$build/bin/reactingFoamSolveZ"
stage=properties
node "$here/prepare.mjs" --table-dir "$table" --metadata "$metadata" --thermo-dir "$thermo" > "$out/property-plan.json"
node "$here/prepare.mjs" --table-dir "$table" --metadata "$metadata" --thermo-dir "$thermo" --out "$out/properties" > "$out/property-preparation.json"
bash -euo pipefail "$here/run.sh" "$out/properties" "$probe" --apply > "$out/property-run.log" 2>&1
stage=cfd-preparation
node "$here/prepare-cfd.mjs" "$manifest" --apply > "$out/cfd-preparation.json"
for variant in baseline optimized; do
  current="$out/cfd/$variant"; stage="cfd-$variant-mesh"
  blockMesh -case "$current" > "$current/log.blockMesh" 2>&1
  checkMesh -case "$current" > "$current/log.checkMesh" 2>&1
  stage="cfd-$variant-Ha"
  "$probe" -case "$current" -initialize-Ha > "$current/log.initialize-Ha" 2>&1
  stage="cfd-$variant-solver"
  "$solver" -case "$current" > "$current/log.solver" 2>&1
done
stage=cfd-comparison
node "$here/compare-cfd.mjs" "$out/cfd" > "$out/cfd-comparison.log"
stage=complete
printf 'Property/inversion/negative-control and fresh CFD parity completed. Scientific acceptance remains separate.\n' > "$out/qualification.txt"
