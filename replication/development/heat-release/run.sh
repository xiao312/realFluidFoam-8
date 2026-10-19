#!/bin/bash
set -Eeuo pipefail
release=${1:?}; job=${2:?}
module="$release/replication/development/heat-release"
cp -a "$module" "$job/monitor-source"
export RF_MONITOR_LIBBIN="$job/monitor-lib"
mkdir "$RF_MONITOR_LIBBIN"
wmake libso "$job/monitor-source" > "$job/monitor-build.log" 2>&1
sha256sum "$RF_MONITOR_LIBBIN/librfHeatReleaseMonitor.so" > "$job/monitor-library.sha256"
ldd "$RF_MONITOR_LIBBIN/librfHeatReleaseMonitor.so" > "$job/monitor-ldd.txt"
! grep -q 'not found' "$job/monitor-ldd.txt"
python3 -B "$module/qualify.py" prepare "$job"
solver="/work/jobs/124864535/openfoam-user/platforms/$WM_OPTIONS/bin/rfPaperReactingFoam"
sha256sum -c /work/jobs/124864535/solver-product.sha256 > "$job/solver-verified.txt"
for mode in off on; do
    mpirun --mca btl self,vader,tcp -np 8 "$solver" -case "$job/$mode" -parallel > "$job/$mode.log" 2>&1
    grep -q '^End' "$job/$mode.log"
done
python3 -B "$module/qualify.py" check "$job" > "$job/qualification.log"
echo 'PASS: heat-release monitor qualification' > "$job/result.txt"
