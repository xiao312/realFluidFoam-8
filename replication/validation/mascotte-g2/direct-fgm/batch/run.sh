#!/usr/bin/env bash
set -euo pipefail
MANIFEST=${1:?input manifest}; MODE=${2:---plan}
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [[ $MODE == --plan ]]; then node "$HERE/preflight.mjs" "$MANIFEST" --plan; exit 0; fi
[[ $MODE == --apply && -n ${SLURM_JOB_ID:-} && ${WM_PROJECT_VERSION:-} == 8 ]] || exit 2
[[ ${SLURM_NTASKS:-0} == 4 && ${SLURM_JOB_NUM_NODES:-1} == 1 ]] || { echo 'Requires one admitted node with four tasks'; exit 3; }
VALUES=$(node "$HERE/preflight.mjs" "$MANIFEST" --apply)
readarray -t INPUTS <<< "$VALUES"
ARCHIVE=${INPUTS[0]}; BUILD=${INPUTS[1]}; OUT=${INPUTS[2]}; CASE=${INPUTS[3]}
TABLE=${INPUTS[4]}; METADATA=${INPUTS[5]}; SOURCE=${INPUTS[6]}
export HOME=/workspace/home TMPDIR="$OUT/tmp" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
mkdir -p "$OUT/logs" "$TMPDIR" "$HOME"
cp "$MANIFEST" "$OUT/input-manifest.json"
ulimit -c 0
stage=initialization
trap 'rc=$?; printf "BATCH_EXIT utc=%s stage=%s rc=%s job=%s\n" "$(date -u +%FT%TZ)" "$stage" "$rc" "$SLURM_JOB_ID" | tee "$OUT/terminal.txt"; exit "$rc"' EXIT
run_stage() {
    stage=$1; local seconds=$2; shift 2
    printf 'STAGE_START name=%s utc=%s\n' "$stage" "$(date -u +%FT%TZ)"
    if timeout "$seconds" "$@" > "$OUT/logs/$stage.log" 2>&1; then rc=0; else rc=$?; fi
    printf '%s\n' "$rc" > "$OUT/logs/$stage-exit.txt"
    printf 'STAGE_EXIT name=%s rc=%s utc=%s\n' "$stage" "$rc" "$(date -u +%FT%TZ)"
    tail -12 "$OUT/logs/$stage.log"
    return "$rc"
}
run_stage build 900 bash -euo pipefail "$HERE/build.sh" "$BUILD" "$ARCHIVE" "$SOURCE"
export LD_LIBRARY_PATH="$BUILD/lib:/opt/gcc-11.2.0/lib64:${LD_LIBRARY_PATH:-}"
SOLVER=$BUILD/bin/reactingFoamSolveZ
DRIVER=$BUILD/source/replication/validation/fgm-of8/direct-verification
G2=$BUILD/source/replication/validation/mascotte-g2/direct-fgm
export BUILD OUT CASE SOLVER DRIVER G2 TABLE METADATA

# New diagnostics may fail independently; retain all three before refusing G2.
failed=0
for kind in heating contact conversion; do
    if run_stage "$kind" 360 bash -euo pipefail -c '
        node "$DRIVER/prepare.mjs" --out "$CASE-$1" --kind "$1"
        bash -euo pipefail "$DRIVER/run.sh" "$CASE-$1" "$SOLVER"
    ' bash "$kind"; then :; else failed=1; fi
done
[[ $failed == 0 ]] || { echo 'G2_REFUSED: repaired solver numerical verification failed'; exit 30; }
run_stage physical 360 bash -euo pipefail -c '
    node "$DRIVER/prepare-physical.mjs" --table-dir "$TABLE" --metadata "$METADATA" --out "$CASE-physical"
    bash -euo pipefail "$DRIVER/run.sh" "$CASE-physical" "$SOLVER"
'

# Only runtime-local OpenMPI is allowed. Force one-host direct fork launching;
# this does not call Slurm, rsh or ssh from inside the allocation.
MPI=$(command -v mpirun); MPICC=$(command -v mpicc)
[[ $MPI == /usr/bin/mpirun && $MPICC == /usr/bin/mpicc ]] || { echo 'Unexpected MPI launcher/compiler paths'; exit 31; }
"$MPI" --version > "$OUT/mpi-version.txt"
"$MPICC" --showme:command > "$OUT/mpi-compiler.txt"
ldd "$MPI" > "$OUT/mpi-launcher-ldd.txt"
if grep -F 'not found' "$OUT/mpi-launcher-ldd.txt"; then exit 32; fi
"$MPICC" -isystem /usr/include/x86_64-linux-gnu -B/usr/lib/x86_64-linux-gnu/ \
    "$HERE/mpi-interface.c" -o "$OUT/mpi-interface"
ldd "$OUT/mpi-interface" > "$OUT/mpi-interface-ldd.txt"
if grep -F 'not found' "$OUT/mpi-interface-ldd.txt"; then exit 33; fi
grep -F 'libPstream.so' "$BUILD/logs/ldd.txt" > "$OUT/solver-pstream.txt"
grep -F 'libmpi.so' "$BUILD/logs/ldd.txt" > "$OUT/solver-mpi.txt"
node --input-type=module - "$BUILD" "$OUT" <<'NODE'
import { readFileSync, realpathSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
const [build, out] = process.argv.slice(2);
const solver = readFileSync(`${build}/logs/ldd.txt`, 'utf8');
const probe = readFileSync(`${out}/mpi-interface-ldd.txt`, 'utf8');
const resolve = (text, name) => {
  const line = text.split('\n').find(row => row.trim().startsWith(name));
  const path = line?.match(/=>\s+(\S+)/)?.[1];
  if (!path || !path.startsWith('/')) throw new Error(`Unresolved ${name}`);
  return realpathSync(path);
};
const mpi = resolve(solver, 'libmpi.so'), probeMpi = resolve(probe, 'libmpi.so');
const pstream = resolve(solver, 'libPstream.so');
if (mpi !== probeMpi || pstream.includes('/dummy/')) throw new Error('Solver/probe MPI libraries differ or Pstream is dummy');
const hash = path => createHash('sha256').update(readFileSync(path)).digest('hex');
writeFileSync(`${out}/mpi-linkage.json`, JSON.stringify({ mpi, pstream,
  mpiSha256: hash(mpi), pstreamSha256: hash(pstream), probeMatchesSolver: true }, null, 2) + '\n');
NODE
sha256sum "$MPI" "$OUT/mpi-interface" > "$OUT/mpi-products.sha256"
MPI_ARGS=(--mca plm isolated --mca ras '^slurm' --host localhost:4 --bind-to none --mca btl self,vader,tcp --mca orte_tmpdir_base "$TMPDIR/mpi" -np 4)
run_stage mpi-interface 60 "$MPI" "${MPI_ARGS[@]}" "$OUT/mpi-interface"
for rank in 0 1 2 3; do grep -Fx "MPI_INTERFACE rank=$rank size=4 sum=6" "$OUT/logs/mpi-interface.log"; done

stage=contact-mpi-preparation
node "$DRIVER/prepare.mjs" --out "$CASE-contact-mpi" --kind contact > "$OUT/logs/contact-mpi-prepare.log"
cat > "$CASE-contact-mpi/system/decomposeParDict" <<'DICT'
FoamFile { version 2.0; format ascii; class dictionary; object decomposeParDict; }
numberOfSubdomains 4; method simple; simpleCoeffs { n (4 1 1); delta 0.001; }
DICT
blockMesh -case "$CASE-contact-mpi" > "$OUT/logs/contact-mpi-mesh.log" 2>&1
decomposePar -case "$CASE-contact-mpi" > "$OUT/logs/contact-mpi-decompose.log" 2>&1
run_stage contact-mpi 360 "$MPI" "${MPI_ARGS[@]}" "$SOLVER" -case "$CASE-contact-mpi" -parallel
reconstructPar -case "$CASE-contact-mpi" > "$OUT/logs/contact-mpi-reconstruct.log" 2>&1
node "$DRIVER/check.mjs" "$CASE-contact-mpi" "$OUT/logs/contact-mpi.log" > "$OUT/logs/contact-mpi-check.log"
node "$HERE/compare-contact.mjs" "$CASE-contact" "$CASE-contact-mpi" "$OUT/contact-mpi-comparison.json"

stage=g2-preparation
node "$G2/prepare.mjs" --table-dir "$TABLE" --metadata "$METADATA" \
    --mesh-dir /references/mascotte-mesh-20261026 --bounds error --ranks 4 --end-time 0.00002 \
    > "$OUT/logs/g2-read-only-plan.json"
node "$G2/prepare.mjs" --table-dir "$TABLE" --metadata "$METADATA" \
    --mesh-dir /references/mascotte-mesh-20261026 --bounds error --ranks 4 --end-time 0.00002 \
    --out "$CASE-g2" > "$OUT/logs/g2-prepare.json"
run_stage g2-checkMesh 180 checkMesh -case "$CASE-g2"
run_stage g2-decompose 180 decomposePar -case "$CASE-g2"
run_stage g2 2700 "$MPI" "${MPI_ARGS[@]}" "$SOLVER" -case "$CASE-g2" -parallel
cp "$OUT/logs/g2.log" "$CASE-g2/log.solver"
run_stage g2-reconstruct 300 reconstructPar -case "$CASE-g2"
run_stage g2-check 120 node "$G2/check.mjs" "$CASE-g2"
printf 'Completed execution diagnostics; no independent scientific acceptance or publication.\n' > "$OUT/qualification.txt"
