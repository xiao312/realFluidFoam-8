#!/bin/bash
set -Eeuo pipefail
release=${1:?}; job=${2:?}
module="$release/replication/development/liang-properties"
cp -a "$module" "$job/property-source"
g++ -std=c++11 -O2 "$job/property-source/test_kernel.C" -o "$job/test-kernel"
"$job/test-kernel" > "$job/kernel-check.log"
wmake "$job/property-source" > "$job/property-build.log" 2>&1
solver="$FOAM_USER_APPBIN/rfLiangPropertyProbe"
sha256sum "$solver" > "$job/property-product.sha256"
ldd "$solver" > "$job/property-ldd.txt"
! grep -q 'not found' "$job/property-ldd.txt"
input="$release/replication/validation/flames/author-counterflow/original/GRI30/constant/thermo.inputData_GRI"
sha256sum "$input" > "$job/species-input.sha256"
mkdir "$job/properties"
"$solver" "$input" "$job/properties" > "$job/properties.log" 2>&1
python3 -B "$module/check.py" "$job/properties" > "$job/check.log"
echo 'PASS: Liang property implementation checks; reference agreement unqualified' > "$job/result.txt"
