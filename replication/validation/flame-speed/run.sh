#!/bin/bash
set -Eeuo pipefail
release=${1:?}; job=${2:?}
module="$release/replication/validation/flame-speed"
python3 -B "$module/prepare.py" plan /work "$job" > "$job/diagnostic-plan.json"
python3 -B "$module/prepare.py" apply /work "$job" > "$job/prepare.log"
cp -a "$module" "$job/diagnostic-source"
wmake "$job/diagnostic-source" > "$job/build.log" 2>&1
sha256sum "$FOAM_USER_APPBIN/rfFlameSpeedTerms" > "$job/diagnostic-product.sha256"
ldd "$FOAM_USER_APPBIN/rfFlameSpeedTerms" > "$job/diagnostic-ldd.txt"
! grep -q 'not found' "$job/diagnostic-ldd.txt"
grep -F '/work/jobs/124657926/openfoam-user/platforms/' "$job/diagnostic-ldd.txt"
reconstructPar -case "$job/case" -time 0.00095:0.001 > "$job/reconstruct.log" 2>&1
rfFlameSpeedTerms -case "$job/case" -time 0.00095:0.001 > "$job/diagnostic.log" 2>&1
grep -q '^End' "$job/diagnostic.log"
python3 -B "$module/analyze.py" "$job/case" > "$job/eq40.json"
echo 'PASS: direct Eq40 checkpoint evaluation; estimator agreement not assumed' > "$job/result.txt"
