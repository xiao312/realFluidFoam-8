#!/bin/bash
set -Eeuo pipefail
release=${1:?}; job=${2:?}; key=${3:?}; build=${4:-}
module="$release/replication/development/flame-tracking"
if [[ "$key" == qualify ]]; then
    mode=qualify; casekey=phi110
else
    mode=full; casekey=$key
    [[ "$build" =~ ^[0-9]+$ ]] || exit 2
    grep -q '^PASS: tracking qualify' "/work/jobs/$build/result.txt"
fi
python3 -B "$module/prepare.py" plan "$job" "$casekey" "$mode" > "$job/copy-plan.json"
python3 -B "$module/prepare.py" apply "$job" "$casekey" "$mode" > "$job/copy.log"
if [[ "$mode" == qualify ]]; then
    g++ -std=c++11 -O2 "$module/test_tracking.C" -o "$job/test-tracking"
    "$job/test-tracking" > "$job/core-test.log"
    python3 -B "$module/instrument.py" plan "$release" "$job/solver-source" > "$job/instrument-plan.json"
    python3 -B "$module/instrument.py" apply "$release" "$job/solver-source" > "$job/instrument.log"
    wmake "$job/solver-source" > "$job/build.log" 2>&1
    solver="$FOAM_USER_APPBIN/rfTrackedReactingFoam"
    sha256sum "$solver" > "$job/solver-product.sha256"
    ldd "$solver" > "$job/tracking-ldd.txt"
    ! grep -q 'not found' "$job/tracking-ldd.txt"
    old="/work/jobs/124870644/openfoam-user/platforms/$WM_OPTIONS/bin/rfSpatialReactingFoam"
    printf '%s  %s\n' e3ef56491e44c2dfdd79826805f992ed8220901643ac14554c38ca8e81e6b385 "$old" | sha256sum -c - > "$job/old-binary-verified.txt"
    mpirun --mca btl self,vader,tcp -np 8 "$old" -case "$job/reference" -parallel > "$job/reference.log" 2>&1
    for name in off on; do
        mpirun --mca btl self,vader,tcp -np 8 "$solver" -case "$job/$name" -parallel > "$job/$name.log" 2>&1
    done
else
    sha256sum -c "/work/jobs/$build/solver-product.sha256" > "$job/binary-verified.txt"
    cp "/work/jobs/$build/solver-product.sha256" "$job/solver-product.sha256"
    solver="/work/jobs/$build/openfoam-user/platforms/$WM_OPTIONS/bin/rfTrackedReactingFoam"
    mpirun --mca btl self,vader,tcp -np 8 "$solver" -case "$job/case" -parallel > "$job/case.log" 2>&1
fi
python3 -B "$module/check.py" "$job" "$mode" > "$job/check.log"
echo "PASS: tracking $mode; scientific convergence unqualified" > "$job/result.txt"
