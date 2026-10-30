#!/usr/bin/env bash
set -euo pipefail
PREFIX=${1:?new case prefix}; FULL=${2:?full runtime}; PROBE=${3:?probe}; SOLVER=${4:?solver}
THERMO=${5:?thermo export}; RANKS=${6:?admitted ranks}; OUT=${7:?result directory}
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
[[ -n ${SLURM_JOB_ID:-} && ${SLURM_NTASKS:-0} == "$RANKS" && $RANKS -gt 1 ]] || exit 2
CELLS=$((2*RANKS))
for species in O2 CH4; do
 for mode in serial parallel; do
  current=$PREFIX-$species-$mode
  node "$HERE/../../../realfluid-g2-thermo/probe/prepare.mjs" --thermo-dir "$THERMO" --species "$species" \
   --boundary fixed --cells "$CELLS" --out "$current" > "$OUT/$species-$mode-prepare.json"
  cat > "$current/system/decomposeParDict" <<DICT
FoamFile { version 2.0; format ascii; class dictionary; object decomposeParDict; }
numberOfSubdomains $RANKS; method simple; simpleCoeffs { n ($RANKS 1 1); delta 0.001; }
DICT
  blockMesh -case "$current" > "$current/log.blockMesh" 2>&1
  parallel=(); [[ $mode != parallel ]] || parallel=(--parallel-ranks "$RANKS")
  node "$HERE/../initialize-cold.mjs" --case "$current" --input-manifest "$current/initialization-input.json" \
   --runtime "$FULL" --probe "$PROBE" --solver "$SOLVER" "${parallel[@]}" --apply > "$OUT/$species-$mode-initialize.json"
 done
 node "$HERE/check-initialization-parity.mjs" "$PREFIX-$species-serial" "$PREFIX-$species-parallel" \
  "$RANKS" "$CELLS" "$OUT/$species-initialization-parity.json"
done
