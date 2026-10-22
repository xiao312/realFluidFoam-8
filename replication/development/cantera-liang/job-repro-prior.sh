#!/bin/bash
# Rebuild the registered previous generation of `liang-8a` from its own source commits and
# push the frozen inputs through it, so the reproducibility finding is answered with re-run
# numbers instead of an asserted cause.
#
# The registered previous generation is the payload's `liang-8a-data.json`. Each row of it
# names the source commit that produced that row, and the rows do not all name the same one:
# the stage-1 point comes from `961f6a1f`, the stage-2/3/4 points from `cf408344`, its
# descendant. Both are ancestors here, so neither tree is lost. Each is archived as a frozen
# input, rebuilt separately with this campaign's compiler and SDK, and used only for the
# points whose declared value came from it. Comparing a point against a value produced by a
# different tree would measure the trees rather than the reproduction, so the pairing is
# declared per point in `expected.json` and a run with the wrong tree is rejected.
#
# Nothing is read from the live checkout of either old tree, and nothing about the current
# tree is changed: only the archived bytes are compiled.
#
# The point list is small on purpose: one stage-1 point as a harness control (ideal gas plus
# mixture-averaged transport, none of the staged code), then the stage-2/3/4 points where the
# generations differ most. A failed case is written as a failed case, never as a missing one.
#
# Usage: job-repro-prior.sh MODULE INPUTS RUN
set -uo pipefail

module=${1:?module directory}
inputs=${2:?frozen inputs directory (prior-*.tar.gz, expected.json, case inputs)}
run=${3:?run directory}

sdk=/opt/cantera-sdk
compiler=/opt/gcc-11.2.0/bin/g++
case_timeout=${CASE_TIMEOUT:-900}
wall_budget=${WALL_BUDGET:-5400}
start=$(date +%s)

log=$run/repro-prior.log
mkdir -p "$run" || exit 1
: > "$log"
logline() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >> "$log"; }
step=start
trap 'rc=$?; logline "ABORT step=$step rc=$rc"; if [ "$rc" -ne 0 ]; then printf "FAILED step=%s rc=%s\n" "$step" "$rc" > "'"$run"'/status.txt"; fi; printf "%s\n" "$rc" > "'"$run"'/rc.txt"; exit $rc' EXIT

logline "repro-prior start host=$(hostname) slurm=${SLURM_JOB_ID:-unset} case_timeout=${case_timeout}s budget=${wall_budget}s"

step=verify
[ -f "$run/module.sha256" ] || { logline "no module.sha256 frozen in the run directory"; exit 2; }
( cd "$module" && sha256sum -c --quiet "$run/module.sha256" ) >> "$log" 2>&1 || {
    logline "MODULE MISMATCH - refusing to build"; exit 1; }
( cd "$inputs" && sha256sum -c --quiet "$run/inputs.sha256" ) >> "$log" 2>&1 || {
    logline "INPUT MISMATCH - refusing to run"; exit 1; }
logline "module and inputs match their frozen manifests"

step=extract
rm -rf "$run/prior"
mkdir -p "$run/prior"
trees=""
for archive in "$inputs"/prior-*.tar.gz; do
    tag=$(basename "$archive" .tar.gz)
    tag=${tag#prior-}
    mkdir -p "$run/prior/$tag"
    tar -xzf "$archive" -C "$run/prior/$tag" || { logline "extract failed: $archive"; exit 1; }
    [ -f "$run/prior/$tag/replication/development/cantera-liang/flame.cpp" ] || {
        logline "archive $archive does not contain flame.cpp"; exit 1; }
    ( cd "$run/prior/$tag" && find . -type f -print0 | sort -z | xargs -0 sha256sum ) \
        > "$run/prior-members-$tag.sha256"
    logline "tree $tag extracted: $(wc -l < "$run/prior-members-$tag.sha256") members"
    trees="$trees $tag"
done

step=probe
printf '#include <cstdint>\n#include <cstdio>\nint main(){std::uint32_t v=1;std::printf("%%u\\n",v);return 0;}\n' > "$run/probe.cpp"
config=base
flags_core=""
if ! "$compiler" -std=c++17 "$run/probe.cpp" -o "$run/probe" >> "$run/probe-attempts.txt" 2>&1; then
    echo "base FAILED" >> "$run/probe-attempts.txt"
    config=registry
    flags_core="-isystem /usr/include/x86_64-linux-gnu -B/usr/lib/x86_64-linux-gnu/"
    if ! "$compiler" -std=c++17 $flags_core "$run/probe.cpp" -o "$run/probe" >> "$run/probe-attempts.txt" 2>&1; then
        echo "registry FAILED" >> "$run/probe-attempts.txt"
        logline "no compile configuration links a trivial program"; exit 1; fi
else
    echo "base OK" >> "$run/probe-attempts.txt"
fi
printf '%s\n' "$config" > "$run/compile-config.txt"
pkgconfig=/opt/cantera-sdk/bin/pkg-config
flags=$($pkgconfig --define-variable=prefix="$sdk" --cflags --libs cantera)
printf '%s\n' "$flags" > "$run/compiler-flags.txt"
"$compiler" --version > "$run/compiler.txt" 2>&1
logline "compile configuration $config compiler $("$compiler" --version 2>&1 | head -1)"

: > "$run/binaries.txt"
for tag in $trees; do
    prior=$run/prior/$tag/replication/development/cantera-liang
    step=build-kernel-$tag
    unset CPLUS_INCLUDE_PATH C_INCLUDE_PATH CPATH LIBRARY_PATH
    "$compiler" -std=c++17 -O2 $flags_core -D_GLIBCXX_USE_CXX11_ABI=1 \
        -I "$prior" "$prior/test_srk.cpp" -o "$run/$tag-test-srk" \
        > "$run/compile-srk-$tag.log" 2>&1 || {
        logline "tree $tag: test_srk failed to compile"
        tail -20 "$run/compile-srk-$tag.log" >> "$log"; exit 1; }
    "$run/$tag-test-srk" > "$run/$tag-kernel-check.txt" 2>&1 || {
        logline "tree $tag: kernel check failed"
        tail -10 "$run/$tag-kernel-check.txt" >> "$log"; exit 1; }
    logline "tree $tag kernel check $(head -1 "$run/$tag-kernel-check.txt")"

    step=build-solver-$tag
    "$compiler" -std=c++17 -O2 -D_GLIBCXX_USE_CXX11_ABI=1 -I "$prior" "$prior/flame.cpp" \
        $flags -Wl,-rpath,"$sdk/lib" -o "$run/$tag-liang-flame" \
        > "$run/compile-flame-$tag.log" 2>&1 || {
        logline "tree $tag: flame.cpp failed to compile"
        tail -20 "$run/compile-flame-$tag.log" >> "$log"; exit 1; }
    sha256sum "$run/$tag-liang-flame" >> "$run/binaries.txt"
    ldd "$run/$tag-liang-flame" > "$run/$tag-ldd.txt" 2>&1 || logline "tree $tag ldd rc non-zero"
    "$run/$tag-liang-flame" > "$run/$tag-usage.txt" 2>&1 || true
    logline "tree $tag solver built $(cut -d' ' -f1 "$run/binaries.txt" | tail -1)"
done
logline "binaries: $(tr '\n' ' ' < "$run/binaries.txt")"

: > "$run/cases.txt"
step=cases
python3 -B - "$inputs/expected.json" > "$run/point-list.txt" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1]))
for point in doc['points']:
    print('%s %s %s' % (point['stage'], point['phi'], point['declared_source']))
PY
[ -s "$run/point-list.txt" ] || { logline "expected.json lists no points"; exit 1; }

while read -r stage phi source; do
    tag=$(printf '%s' "$source" | cut -c1-8)
    dir=$run/cases/s${stage}-phi${phi}-$tag
    mkdir -p "$dir"
    elapsed=$(( $(date +%s) - start ))
    if [ "$elapsed" -gt "$wall_budget" ]; then
        logline "wall budget reached before stage=$stage phi=$phi tree=$tag"
        printf '%s|%s|%s|%s|0|-|-\n' "$stage" "$phi" "$tag" 125 >> "$run/cases.txt"
        continue
    fi
    if [ ! -x "$run/$tag-liang-flame" ]; then
        logline "no binary for tree $tag demanded by stage=$stage phi=$phi"
        printf '%s|%s|%s|%s|0|-|-\n' "$stage" "$phi" "$tag" 127 >> "$run/cases.txt"
        continue
    fi
    t0=$(date +%s)
    rc=0
    # The 961f6a1f tree takes four arguments and fixes the pressure at 100 atm; the later
    # tree takes the same four and defaults to 100 atm as well, so both are invoked alike.
    ( cd "$dir" && timeout "$case_timeout" "$run/$tag-liang-flame" "$inputs" "$stage" "$phi" \
        "$dir/result" ) > "$dir/flame.log" 2>&1 || rc=$?
    taken=$(( $(date +%s) - t0 ))
    speed=""; grid="-"
    if [ -s "$dir/result/refinement.csv" ]; then
        grid=$(tail -1 "$dir/result/refinement.csv" | cut -d, -f5)
    fi
    line=$(grep -o 'COMPLETED stage=[0-9]* phi=[0-9.]* speed_cm_s=[0-9.eE+-]*' "$dir/flame.log" 2>/dev/null || true)
    if [ -n "$line" ]; then
        speed=${line##*speed_cm_s=}
    fi
    printf '%s|%s|%s|%s|%s|%s|%s\n' "$stage" "$phi" "$tag" "$rc" "$taken" "$grid" "${speed:--}" \
        >> "$run/cases.txt"
    logline "case stage=$stage phi=$phi tree=$tag rc=$rc elapsed=${taken}s points=$grid speed=${speed:-none}"
done < "$run/point-list.txt"

step=reduce
if ! python3 -B "$module/reduce_repro_prior.py" --expected "$inputs/expected.json" \
        --cases "$run/cases.txt" --binaries "$run/binaries.txt" \
        --out "$run/repro-prior.json" > "$run/reduce.log" 2>&1; then
    logline "reducer failed"; tail -20 "$run/reduce.log" >> "$log"; exit 1
fi

step=selftest
python3 -B -m unittest discover -s "$module" -p 'test_reduce_repro_prior.py' -t "$module" \
    > "$run/reduce-selftest.log" 2>&1 && rc_selftest=0 || rc_selftest=$?
logline "reducer self-test rc=$rc_selftest"
verdict=$(sed -n 's/.*"verdict": "\([a-z_]*\)".*/\1/p' "$run/repro-prior.json" | head -1)
printf 'RAN verdict=%s points=%s config=%s total=%ss\n' \
    "$verdict" "$(wc -l < "$run/cases.txt")" "$config" \
    "$(( $(date +%s) - start ))" > "$run/status.txt"
logline "repro-prior done verdict=$verdict"
tail -20 "$log"
exit 0
