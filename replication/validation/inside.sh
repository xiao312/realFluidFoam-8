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
cp -a "$release/replication/validation/properties" "$job/property-probe"
wmake "$job/property-probe" > "$job/property-probe-build.log" 2>&1
ldd "$FOAM_USER_APPBIN/rfPropertyProbe" > "$job/property-probe-ldd.txt"
grep -F "$platform/lib/libspecie.so" "$job/property-probe-ldd.txt"
if [[ "$stage" == properties || "$stage" == properties-nitrogen ]]; then
    inversion_failed=0
    for eos in SRK PR; do
        case_dir="$job/properties-$eos"
        probe_args=(); expected_lines=226
        if [[ "$stage" == properties-nitrogen ]]; then
            python3 -B "$release/replication/validation/properties/generate.py" \
                "$release/replication/validation/inputs" "$case_dir" "$eos" N2 \
                "$release/tutorials/N2.jet.LES/c3.PR/constant/thermo.inputData"
            probe_args=(-nitrogen); expected_lines=902
        else
            python3 -B "$release/replication/validation/properties/generate.py" \
                "$release/replication/validation/inputs" "$case_dir" "$eos"
        fi
        blockMesh -case "$case_dir" > "$job/blockMesh-$eos.log" 2>&1
        probe_status=0
        rfPropertyProbe -case "$case_dir" "${probe_args[@]}" > "$job/properties-$eos.log" 2>&1 || probe_status=$?
        if [[ "$probe_status" == 3 ]]; then inversion_failed=1
        elif [[ "$probe_status" != 0 ]]; then exit "$probe_status"; fi
        test "$(wc -l < "$case_dir/properties.csv")" == "$expected_lines"
    done
    if [[ "$inversion_failed" == 1 ]]; then
        echo 'CHECK_FAILED: inversion tolerance; SRK and PR finite property sweeps completed, reference comparison pending' | tee "$job/result.txt"
        exit 3
    fi
    echo 'PASS: SRK and PR property sweeps and inversion criterion; reference comparison pending' | tee "$job/result.txt"
elif [[ "$stage" == campaign-* ]]; then
    config="$release/replication/validation/flames/campaign/${stage#campaign-}.json"
    case_dir="$job/case"
    python3 -B "$release/replication/validation/flames/campaign.py" apply "$config" \
        "$release/replication/validation/inputs" "$case_dir" > "$job/campaign-plan.json"
    blockMesh -case "$case_dir" > "$job/blockMesh.log" 2>&1
    checkMesh -case "$case_dir" > "$job/checkMesh.log" 2>&1
    grep -q 'Mesh OK' "$job/checkMesh.log"
    rfPropertyProbe -case "$case_dir" -initial > "$job/inlet-probe.log" 2>&1
    if python3 -c 'import json,sys; sys.exit(json.load(open(sys.argv[1]))["case"]!="premixed")' "$config"; then
        python3 -B "$release/replication/validation/flames/finalize_premixed.py" "$case_dir" > "$job/inlet-settings.json"
        setFields -case "$case_dir" > "$job/setFields.log" 2>&1
    else
        python3 -B "$release/replication/validation/flames/finalize_inlets.py" "$case_dir" > "$job/inlet-settings.json"
    fi
    ranks=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["ranks"])' "$config")
    if [[ "$ranks" -gt 1 ]]; then
        decomposePar -case "$case_dir" > "$job/decompose.log" 2>&1
        mpirun --mca btl self,vader,tcp -np "$ranks" realFluidReactingFoam -case "$case_dir" -parallel > "$job/solver.log" 2>&1
        reconstructPar -case "$case_dir" > "$job/reconstruct.log" 2>&1
    else
        realFluidReactingFoam -case "$case_dir" > "$job/solver.log" 2>&1
    fi
    grep -q '^End' "$job/solver.log"
    python3 -B "$release/replication/validation/flames/summarize.py" "$case_dir" > "$job/field-summary.json"
    echo 'PASS: configured development run and final field checks; temporal/grid convergence not established' | tee "$job/result.txt"
elif [[ "$stage" == counterflow-pilot-* || "$stage" == premixed-pilot-phi1 ]]; then
    case_name=${stage#counterflow-pilot-}
    case_dir="$job/$case_name"
    if [[ "$stage" == premixed-pilot-phi1 ]]; then
        python3 -B "$release/replication/validation/flames/generate_premixed.py" \
            "$release/replication/validation/inputs" "$case_dir" 1.0
    else
        python3 -B "$release/replication/validation/flames/generate_counterflow.py" \
            "$release/replication/validation/inputs" "$case_dir" "$case_name"
    fi
    blockMesh -case "$case_dir" > "$job/blockMesh.log" 2>&1
    checkMesh -case "$case_dir" > "$job/checkMesh.log" 2>&1
    grep -q 'Mesh OK' "$job/checkMesh.log"
    rfPropertyProbe -case "$case_dir" -initial > "$job/inlet-probe.log" 2>&1
    if [[ "$stage" == premixed-pilot-phi1 ]]; then
        python3 -B "$release/replication/validation/flames/finalize_premixed.py" "$case_dir" > "$job/inlet-settings.json"
        setFields -case "$case_dir" > "$job/setFields.log" 2>&1
    else
        python3 -B "$release/replication/validation/flames/finalize_inlets.py" "$case_dir" > "$job/inlet-settings.json"
    fi
    realFluidReactingFoam -case "$case_dir" > "$job/solver.log" 2>&1
    grep -q '^End' "$job/solver.log"
    grep -q 'seulex' "$job/solver.log"
    python3 -B "$release/replication/validation/flames/summarize.py" "$case_dir" > "$job/pilot-summary.json"
    echo 'PASS: flame startup/cost pilot and final field checks only; convergence and scientific comparison pending' | tee "$job/result.txt"
else
    echo "Unsupported validation stage: $stage" >&2
    exit 2
fi
