#!/bin/bash
set -Eeuo pipefail
release=${1:?}; job=${2:?}
module="$release/replication/development/heat-release"
generator="$release/replication/development/premixed-paper/instrument.py"
python3 -B "$generator" plan "$release/replication/development/solver" "$job/solver-source" > "$job/solver-plan.json"
python3 -B "$generator" apply "$release/replication/development/solver" "$job/solver-source" > "$job/instrument.log"
wmake "$job/solver-source" > "$job/solver-build.log" 2>&1
solver="$FOAM_USER_APPBIN/rfPaperReactingFoam"
sha256sum "$solver" > "$job/solver-product.sha256"
ldd "$solver" > "$job/native-solver-ldd.txt"
! grep -q 'not found' "$job/native-solver-ldd.txt"
grep -q '^PASS: heat-release monitor qualification' /work/jobs/124867177/result.txt
sha256sum -c /work/jobs/124867177/monitor-library.sha256 > "$job/monitor-verified.txt"
mkdir "$job/monitor-lib"
ln -s /work/jobs/124867177/monitor-lib/librfHeatReleaseMonitor.so "$job/monitor-lib/librfHeatReleaseMonitor.so"
python3 -B "$module/qualify.py" prepare "$job"
old="/work/jobs/124864535/openfoam-user/platforms/$WM_OPTIONS/bin/rfPaperReactingFoam"
sha256sum -c /work/jobs/124864535/solver-product.sha256 > "$job/previous-solver-verified.txt"
mpirun --mca btl self,vader,tcp -np 8 "$old" -case "$job/off" -parallel > "$job/off.log" 2>&1
grep -q '^End' "$job/off.log"
mpirun --mca btl self,vader,tcp -np 8 "$solver" -case "$job/on" -parallel > "$job/on.log" 2>&1
grep -q '^End' "$job/on.log"
python3 -B "$module/qualify.py" check "$job" --native > "$job/qualification.log"
echo 'PASS: native Qdot field qualification' > "$job/result.txt"
