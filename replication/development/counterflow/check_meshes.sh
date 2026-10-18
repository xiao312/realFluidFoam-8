#!/bin/bash
# Geometry qualification only; no chemistry or flow integration.
set -euo pipefail
release=${1:?}; job=${2:?}
for key in oxy-1 oxy-200 air-100; do
    output="$job/$key"
    python3 -B "$release/replication/development/counterflow/prepare.py" plan "$key" paper "$output" > "$job/$key-plan.json"
    python3 -B "$release/replication/development/counterflow/prepare.py" apply "$key" paper "$output" > "$job/$key-prepare.log"
    cmp "$output/one-step/system/blockMeshDict" "$output/gri30/system/blockMeshDict"
    blockMesh -case "$output/gri30" > "$job/$key-blockMesh.log" 2>&1
    checkMesh -case "$output/gri30" > "$job/$key-checkMesh.log" 2>&1
    grep -q 'Mesh OK' "$job/$key-checkMesh.log"
done
echo 'PASS: three paper-informed counterflow meshes; no flow/chemistry acceptance' | tee "$job/result.txt"
