#!/bin/sh
# Reproduce the Liang et al. (2019) Fig. 1 numbers of this directory.
#
#   sh job.sh <case-dir> <run-dir>
#
# <case-dir> holds fig1_probe.cpp (this directory); everything is written below
# <run-dir>, never into the repository.  The probe is header-only: no Cantera SDK, no
# MPI, one thread.
set -u
CASE=${1:?case directory}
RUN=${2:?run directory}
mkdir -p "$RUN" || exit 1
CXX=${CXX:-/opt/gcc-11.2.0/bin/g++}
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
: > "$RUN/status.txt"

say() { echo "$@" >> "$RUN/status.txt"; }

say "case $CASE"
say "run $RUN"
say "compiler $CXX"
"$CXX" --version 2>&1 | head -1 >> "$RUN/status.txt" || true

# The batch image's g++ finds its own libstdc++ headers but not the glibc headers of the
# host; -isystem/-B point at them, exactly as the qualified Cantera build does.
CXXFLAGS="-std=c++17 -O2 -Wall -Wextra -isystem /usr/include/x86_64-linux-gnu -L/usr/lib/x86_64-linux-gnu -B/usr/lib/x86_64-linux-gnu/"
say "flags $CXXFLAGS"
if "$CXX" $CXXFLAGS -o "$RUN/fig1-probe" "$CASE/fig1_probe.cpp" \
        > "$RUN/build.log" 2>&1; then
    say "build OK"
else
    say "build FAILED (see build.log)"
    printf 'FAILED\n' > "$RUN/rc.txt"
    exit 1
fi

"$RUN/fig1-probe" 150 1000 1 > "$RUN/fig1-probe.csv" 2> "$RUN/probe.err"
rc=$?
say "probe rc=$rc rows=$(wc -l < "$RUN/fig1-probe.csv")"
cat "$RUN/probe.err" >> "$RUN/status.txt"

# A 6-point check table for the report, taken from the same CSV.
if [ -s "$RUN/fig1-probe.csv" ]; then
    grep -E '^#|^T_K' "$RUN/fig1-probe.csv" > "$RUN/head.txt" 2>/dev/null || true
fi
printf '%s\n' "--- provenance ---" >> "$RUN/status.txt"
sha256sum "$CASE/fig1_probe.cpp" 2>/dev/null >> "$RUN/status.txt" || true
sha256sum "$RUN/fig1-probe.csv" >> "$RUN/status.txt" || true
printf '%s\n' "rc=$rc" > "$RUN/rc.txt"
[ "$rc" -eq 0 ] || exit "$rc"
exit 0
