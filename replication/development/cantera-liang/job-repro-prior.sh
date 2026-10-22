#!/bin/bash
# Rebuild the registered previous generation of `liang-8a` from its own source commit and
# push the frozen inputs through it, so the reproducibility finding is answered with
# re-run numbers instead of an asserted cause.
#
# The previous generation is the payload's `liang-8a-data.json`; every row of it names the
# source commit `961f6a1f…` that produced the value. That commit is an ancestor here, so
# the module is not lost - it is archived as a frozen input (`prior-module.tar.gz`, hashed
# in `inputs.sha256`) and rebuilt with the same compiler, SDK and flags this campaign uses
# for the current tree. Nothing is read from the live checkout of the old tree, and nothing
# about the current tree is changed: only the archived bytes are compiled.
#
# The point list is deliberately small and declared in `expected.json`: one stage-1 point as
# a harness control, then the stage-2/3/4 points where the two generations differ most. A
# failed case is written as a failed case, never as a missing one.
#
# Usage: job-repro-prior.sh MODULE INPUTS RUN
set -uo pipefail

module=${1:?module directory}
inputs=${2:?frozen inputs directory (prior-module.tar.gz, expected.json, case inputs)}
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
tar -xzf "$inputs/prior-module.tar.gz" -C "$run/prior" || { logline "extract failed"; exit 1; }
prior="$run/prior/replication/development/cantera-liang"
[ -f "$prior/flame.cpp" ] || { logline "archive does not contain flame.cpp"; exit 1; }
( cd "$run/prior" && find . -type f -print0 | sort -z | xargs -0 sha256sum ) > "$run/prior-members.sha256"
logline "prior module extracted: $(wc -l < "$run/prior-members.sha256") members"
sha256sum "$prior"/* > "$run/prior-module-files.sha256"
cat "$run/prior-module-files.sha256" >> "$run/repro-prior.log"

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

step=build-kernel
unset CPLUS_INCLUDE_PATH C_INCLUDE_PATH CPATH LIBRARY_PATH
"$compiler" -std=c++17 -O2 $flags_core -D_GLIBCXX_USE_CXX11_ABI=1 "$prior/test_srk.cpp" \
    -o "$run/prior-test-srk" > "$run/compile-srk.log" 2>&1 || {
    logline "prior test_srk failed to compile"; tail -20 "$run/compile-srk.log" >> "$log"; exit 1; }
"$run/prior-test-srk" > "$run/prior-kernel-check.txt" 2>&1 || {
    logline "prior kernel check failed"; tail -10 "$run/prior-kernel-check.txt" >> "$log"; exit 1; }
logline "prior kernel check $(head -2 "$run/prior-kernel-check.txt" | tr '\n' ' ')"

step=build-solver
"$compiler" -std=c++17 -O2 -D_GLIBCXX_USE_CXX11_ABI=1 "$prior/flame.cpp" \
    $flags -Wl,-rpath,"$sdk/lib" -o "$run/prior-liang-flame" > "$run/compile-flame.log" 2>&1 || {
    logline "prior flame.cpp failed to compile"; tail -20 "$run/compile-flame.log" >> "$log"; exit 1; }
binary_sha=$(sha256sum "$run/prior-liang-flame" | cut -d' ' -f1)
logline "prior solver built sha256 $binary_sha"
ldd "$run/prior-liang-flame" > "$run/prior-ldd.txt" 2>&1 || logline "ldd rc non-zero"
"$run/prior-liang-flame" > "$run/prior-usage.txt" 2>&1 || true

: > "$run/cases.txt"
points="1:0.95 2:0.95 2:1.2 3:1.0 3:1.2 4:1.0 4:1.2"
step=cases
for point in $points; do
    stage=${point%%:*}
    phi=${point##*:}
    dir=$run/cases/s${stage}-phi${phi}
    mkdir -p "$dir"
    elapsed=$(( $(date +%s) - start ))
    if [ "$elapsed" -gt "$wall_budget" ]; then
        logline "wall budget reached before stage=$stage phi=$phi"
        printf '%s|%s|%s|0|-|-\n' "$stage" "$phi" 125 >> "$run/cases.txt"
        continue
    fi
    t0=$(date +%s)
    rc=0
    timeout "$case_timeout" "$run/prior-liang-flame" "$inputs" "$stage" "$phi" "$dir/result" \
        > "$dir/flame.log" 2>&1 || rc=$?
    taken=$(( $(date +%s) - t0 ))
    speed=""; grid="-"
    if [ -s "$dir/result/refinement.csv" ]; then
        grid=$(tail -1 "$dir/result/refinement.csv" | cut -d, -f5)
    fi
    line=$(grep -o 'COMPLETED stage=[0-9]* phi=[0-9.]* speed_cm_s=[0-9.eE+-]*' "$dir/flame.log" 2>/dev/null || true)
    if [ -n "$line" ]; then
        speed=${line##*speed_cm_s=}
    fi
    printf '%s|%s|%s|%s|%s|%s\n' "$stage" "$phi" "$rc" "$taken" "$grid" "${speed:--}" >> "$run/cases.txt"
    logline "case stage=$stage phi=$phi rc=$rc elapsed=${taken}s points=$grid speed=${speed:-none}"
done

step=reduce
if ! python3 -B "$module/reduce_repro_prior.py" --expected "$inputs/expected.json" \
        --cases "$run/cases.txt" --out "$run/repro-prior.json" \
        --prior-commit 961f6a1fc6662167076abea2b8d4c6aee449622c \
        --prior-binary-sha256 "$binary_sha" > "$run/reduce.log" 2>&1; then
    logline "reducer failed"; tail -20 "$run/reduce.log" >> "$log"; exit 1
fi
rc_reduce=0

step=selftest
python3 -B -m unittest discover -s "$module" -p 'test_reduce_repro_prior.py' -t "$module" \
    > "$run/reduce-selftest.log" 2>&1 && rc_selftest=0 || rc_selftest=$?
logline "reducer self-test rc=$rc_selftest"
verdict=$(sed -n 's/.*"verdict": "\([a-z_]*\)".*/\1/p' "$run/repro-prior.json" | head -1)
printf 'RAN verdict=%s points=%s binary=%s config=%s total=%ss\n' \
    "$verdict" "$(wc -l < "$run/cases.txt")" "$binary_sha" "$config" \
    "$(( $(date +%s) - start ))" > "$run/status.txt"
logline "repro-prior done verdict=$verdict"
tail -20 "$log"
exit "$rc_reduce"
