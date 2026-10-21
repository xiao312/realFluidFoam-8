#!/bin/sh
# Probe the Cantera 3.2 build for the Cavalieri et al. (2025) Fig. 1 models.
#
#   sh job.sh <case-dir> <run-dir>
#
# The probe only reports which equation-of-state and transport model names this
# installation accepts and what they return at two state points.  It writes
# nothing into the repository and exits nonzero if the payload fails.
set -u
CASE=${1:?case directory}
RUN=${2:?run directory}
mkdir -p "$RUN" || exit 1
PY=${PY:-/opt/python/bin/python3}
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 RUN_DIR="$RUN"
: > "$RUN/status.txt"

say() { echo "$@" >> "$RUN/status.txt"; }

say "case $CASE"
say "run $RUN"
say "python $PY"
"$PY" -c 'import sys; print(sys.version.replace("\n", " "))' >> "$RUN/status.txt" 2>&1 || true
{
    echo "--- environment ---"
    date -u +%Y-%m-%dT%H:%M:%SZ
    hostname
    "$PY" -c 'import cantera as ct, sys; print("cantera", ct.__version__); print("module", ct.__file__); print("python", sys.version.replace("\n", " "))' 2>&1
} > "$RUN/environment.txt" 2>&1

"$PY" "$CASE/probe_models.py" > "$RUN/probe.log" 2>&1
rc=$?
say "probe rc=$rc"
printf '%s\n' "--- provenance ---" >> "$RUN/status.txt"
sha256sum "$CASE/probe_models.py" "$CASE/job.sh" >> "$RUN/status.txt" 2>/dev/null || true
sha256sum "$RUN/probe.log" >> "$RUN/status.txt" 2>/dev/null || true
printf 'rc=%s\n' "$rc" > "$RUN/rc.txt"
[ "$rc" -eq 0 ] || exit "$rc"
exit 0
