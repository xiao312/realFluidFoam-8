#!/usr/bin/env bash
# Compute the Cavalieri et al. (2025) Fig. 1 comparison: SRK + Chung, pure O2 and CH4.
#
#   bash job.sh <source-root> <run-dir>
#
# <source-root> is the extracted snapshot of this directory in the candidate commit, so every
# hash recorded below identifies code that exists in the candidate.  The control adapter
# prepends `#!/usr/bin/env bash` and `set -euo pipefail`; this script is written to be correct
# under exactly that shell, and it never disables `-e` or `pipefail`.  Pipelines are avoided:
# every listing is written to a file and read back with a bounded reader.
set -u

CASE=${1:?source root}
RUN=${2:?run directory}
mkdir -p "$RUN" || exit 1

PY=${PY:-python3}
NODE=${NODE:-node}
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1

STATUS="$RUN/status.txt"
: > "$STATUS" || exit 1
say() { printf '%s\n' "$*" >> "$STATUS"; }

rc_of() {  # rc_of <logfile> <command...>  -> echoes the exit status, never aborts
    log=$1
    shift
    if "$@" > "$log" 2>&1; then
        echo 0
    else
        echo $?
    fi
}

say "case $CASE"
say "run  $RUN"
say "host $(hostname)"
say "start $(date -u +%Y-%m-%dT%H:%M:%SZ)"

{
    echo "--- environment ---"
    date -u +%Y-%m-%dT%H:%M:%SZ
    hostname
    uname -a
    "$PY" -c 'import sys, platform; print("python", sys.version.replace(chr(10), " ")); print("platform", platform.platform())' 2>&1 || true
    "$NODE" --version 2>&1 || true
    echo "--- files ---"
    ls -l "$CASE" 2>&1 || true
} > "$RUN/environment.txt" 2>&1

# ---------------------------------------------------------------------------
# 1. code identity: the SHA256 of every file this run executes, recorded inside the job
# ---------------------------------------------------------------------------
sha256sum "$CASE/srk_chung.py" "$CASE/sweep_properties.py" "$CASE/compare_reference.py" \
    "$CASE/test_srk_chung.py" "$CASE/checks.py" "$CASE/job.sh" \
    "$CASE/render_figures.mjs" "$CASE/figure1-vector.json" \
    > "$RUN/hashes.txt" 2>&1
hashes_rc=$?
say "hashes rc=$hashes_rc"
printf '%s\n' "$hashes_rc" > "$RUN/hashes.rc"

# ---------------------------------------------------------------------------
# 2. unit and consistency tests at the exact commit
# ---------------------------------------------------------------------------
tests_rc=$(rc_of "$RUN/tests.log" "$PY" "$CASE/test_srk_chung.py")
printf '%s\n' "$tests_rc" > "$RUN/tests.rc"
say "tests rc=$tests_rc"

# ---------------------------------------------------------------------------
# 3. property sweep (pure standard-library Python, no solver library involved)
# ---------------------------------------------------------------------------
sweep_rc=$(rc_of "$RUN/sweep.log" "$PY" "$CASE/sweep_properties.py" --out-dir "$RUN/out")
printf '%s\n' "$sweep_rc" > "$RUN/sweep.rc"
say "sweep rc=$sweep_rc"
printf '%s\n' "$sweep_rc" >&2

# ---------------------------------------------------------------------------
# 4. comparison against the digitised published figure
# ---------------------------------------------------------------------------
compare_rc=$(rc_of "$RUN/compare.log" "$PY" "$CASE/compare_reference.py" \
    --vector "$CASE/figure1-vector.json" --sweep "$RUN/out/sweep.json" \
    --out "$RUN/out/comparison.json")
printf '%s\n' "$compare_rc" > "$RUN/compare.rc"
say "compare rc=$compare_rc"
printf '%s\n' "$compare_rc" >&2

# ---------------------------------------------------------------------------
# 5. figure build through the shared renderer
# ---------------------------------------------------------------------------
SOURCE_COMMIT=${SOURCE_COMMIT:-unknown}
JOB_ID=${SLURM_JOB_ID:-${FLAMEPILOT_JOB_ID:-unknown}}
render_rc=$(rc_of "$RUN/render.log" "$NODE" "$CASE/render_figures.mjs" \
    --vector "$CASE/figure1-vector.json" --out-dir "$RUN/out" \
    --source-commit "$SOURCE_COMMIT" --sweep "$RUN/out/sweep.json" \
    --run-job-id "$JOB_ID")
printf '%s\n' "$render_rc" > "$RUN/render.rc"
say "render rc=$render_rc job_id=$JOB_ID commit=$SOURCE_COMMIT"
printf '%s\n' "$render_rc" >&2

# ---------------------------------------------------------------------------
# 6. campaign checks over the files this run produced
# ---------------------------------------------------------------------------
if [ "$sweep_rc" -ne 0 ]; then
    checks_rc=4
else
    checks_rc=$(rc_of "$RUN/checks.log" "$PY" "$CASE/checks.py" --src "$CASE" \
        --run-dir "$RUN" --vector "$CASE/figure1-vector.json" \
        --commit "$SOURCE_COMMIT" --job-id "$JOB_ID" \
        --expect-pdf-sha256 bcd4f0fdac3c4063c744e331c0b2e6af7e311837f99230502cde2c97257d0843)
fi
printf '%s\n' "$checks_rc" > "$RUN/checks.rc"
say "checks rc=$checks_rc"
printf '%s\n' "$checks_rc" >&2

# ---------------------------------------------------------------------------
# 7. output inventory and verdict
# ---------------------------------------------------------------------------
{
    echo "--- outputs ---"
    ls -l "$RUN" 2>&1 || true
    ls -l "$RUN/out" 2>&1 || true
    echo "--- output hashes ---"
    sha256sum "$RUN"/out/* 2>&1 || true
} > "$RUN/inventory.txt" 2>&1
inventory_rc=$?
say "inventory rc=$inventory_rc"

say "end $(date -u +%Y-%m-%dT%H:%M:%SZ)"

status=0
if [ "$hashes_rc" -ne 0 ]; then status=1; fi
if [ "$tests_rc" -ne 0 ]; then status=2; fi
if [ "$sweep_rc" -ne 0 ]; then status=3; fi
if [ "$compare_rc" -ne 0 ]; then status=4; fi
if [ "$render_rc" -ne 0 ]; then status=5; fi
if [ "$checks_rc" -ne 0 ]; then status=6; fi
if [ "$inventory_rc" -ne 0 ]; then status=7; fi

printf 'payload_rc=%s tests_rc=%s sweep_rc=%s compare_rc=%s render_rc=%s checks_rc=%s\n' \
    "$status" "$tests_rc" "$sweep_rc" "$compare_rc" "$render_rc" "$checks_rc" > "$RUN/rc.txt"
say "payload_rc=$status"
exit "$status"
