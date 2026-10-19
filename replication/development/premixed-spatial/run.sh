#!/bin/bash
set -Eeuo pipefail
release=${1:?}; job=${2:?}; module="$release/replication/development/premixed-spatial"
python3 -B "$module/prepare.py" plan "$job" > "$job/copy-plan.json"
python3 -B "$module/prepare.py" apply "$job" > "$job/copy.log"
python3 -B "$module/instrument.py" plan "$release" "$job/solver-source" > "$job/instrument-plan.json"
python3 -B "$module/instrument.py" apply "$release" "$job/solver-source" > "$job/instrument.log"
wmake "$job/solver-source" > "$job/build.log" 2>&1
solver="$FOAM_USER_APPBIN/rfSpatialReactingFoam"
sha256sum "$solver" > "$job/solver-product.sha256"
ldd "$solver" > "$job/spatial-ldd.txt"
! grep -q 'not found' "$job/spatial-ldd.txt"
sha256sum -c /work/jobs/124868494/solver-product.sha256 > "$job/qualified-native-verified.txt"
old="/work/jobs/124868494/openfoam-user/platforms/$WM_OPTIONS/bin/rfPaperReactingFoam"
mpirun --mca btl self,vader,tcp -np 8 "$old" -case "$job/off0" -parallel > "$job/off0.log" 2>&1
grep -q '^End' "$job/off0.log"
for case in on0 on1 on2 on3; do
    mpirun --mca btl self,vader,tcp -np 8 "$solver" -case "$job/$case" -parallel > "$job/$case.log" 2>&1
    grep -q '^End' "$job/$case.log"
done
python3 -B "$module/check.py" "$job" > "$job/check.log"
echo 'PASS: spatial diagnostics and replay field equivalence; flame convergence unqualified' > "$job/result.txt"
