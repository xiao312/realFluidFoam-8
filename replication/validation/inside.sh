#!/bin/bash
# Called only after environment/inside.sh has initialized the contained OF8 environment.
set -Eeuo pipefail
trap 'echo "Failed at ${BASH_SOURCE[0]}:${LINENO}: $BASH_COMMAND" >&2' ERR
release=${1:?source}; job="/work/jobs/${RF_JOB_ID:?}"
build_job=${RF_BUILD_JOB:?}; stage=${RF_STAGE:?}
[[ "$build_job" =~ ^[0-9]+$ && "$release" == /work/releases/* ]] || exit 2
build="/work/builds/$build_job"
grep -q '^PASS: build,' "/work/jobs/$build_job/result.txt"
sha256sum -c "/work/jobs/$build_job/products.sha256" > "$job/build-products-verified.txt"
platform="/work/jobs/$build_job/openfoam-user/platforms/$WM_OPTIONS"
export FOAM_USER_LIBBIN="$platform/lib"
export LD_LIBRARY_PATH="$FOAM_USER_LIBBIN:$LD_LIBRARY_PATH"
export PATH="$FOAM_USER_APPBIN:$platform/bin:$PATH"
export LIB_rfFoam8_SRC="$build/src"
printf 'source=%s\nbuild_job=%s\nstage=%s\n' "$(cat "$release/SOURCE_REVISION")" "$build_job" "$stage" > "$job/validation-inputs.txt"
ldd "$platform/bin/realFluidReactingFoam" > "$job/solver-ldd.txt"
grep -F "$platform/lib/libspecie.so" "$job/solver-ldd.txt"
if grep -q 'not found' "$job/solver-ldd.txt"; then exit 1; fi
if [[ "$stage" == properties ]]; then
    cp -a "$release/replication/validation/properties" "$job/property-probe"
    wmake "$job/property-probe" > "$job/property-probe-build.log" 2>&1
    ldd "$FOAM_USER_APPBIN/rfPropertyProbe" > "$job/property-probe-ldd.txt"
    grep -F "$platform/lib/libspecie.so" "$job/property-probe-ldd.txt"
    for eos in SRK PR; do
        case_dir="$job/properties-$eos"
        python3 -B "$release/replication/validation/properties/generate.py" \
            "$release/replication/validation/inputs" "$case_dir" "$eos"
        blockMesh -case "$case_dir" > "$job/blockMesh-$eos.log" 2>&1
        rfPropertyProbe -case "$case_dir" > "$job/properties-$eos.log" 2>&1
        test "$(wc -l < "$case_dir/properties.csv")" == 226
    done
    echo 'PASS: SRK and PR property sweeps; reference comparison pending' | tee "$job/result.txt"
else
    echo "Unsupported validation stage: $stage" >&2
    exit 2
fi
