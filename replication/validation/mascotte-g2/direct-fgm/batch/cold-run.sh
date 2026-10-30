#!/usr/bin/env bash
set -euo pipefail
MANIFEST=${1:?manifest}; MODE=${2:---plan}
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [[ $MODE == --plan ]]; then node "$HERE/cold-preflight.mjs" "$MANIFEST" --plan; exit 0; fi
[[ $MODE == --apply && -n ${SLURM_JOB_ID:-} && ${WM_PROJECT_VERSION:-} == 8 ]] || exit 2
VALUES=$(node "$HERE/cold-preflight.mjs" "$MANIFEST" --apply); readarray -t INPUTS <<< "$VALUES"
ARCHIVE=${INPUTS[0]}; BUILD=${INPUTS[1]}; OUT=${INPUTS[2]}; CASE=${INPUTS[3]}; FULL=${INPUTS[4]}
TABLE=${INPUTS[5]}; METADATA=${INPUTS[6]}; THERMO=${INPUTS[7]}; SOURCE=${INPUTS[8]}
RANKS=${INPUTS[9]}; MEMORY=${INPUTS[10]}; END_TIME=${INPUTS[11]}
[[ ${SLURM_JOB_NUM_NODES:-1} == 1 && ${SLURM_NTASKS:-0} == "$RANKS" ]] || exit 3
if [[ ${SLURM_MEM_PER_NODE:-} =~ ^[0-9]+$ ]]; then (( SLURM_MEM_PER_NODE >= MEMORY*1024 )) || exit 4; fi
export HOME=/workspace/home TMPDIR="$OUT/tmp" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
mkdir -p "$OUT/logs" "$TMPDIR" "$HOME"
cp "$MANIFEST" "$OUT/input-manifest.json"
printf '%s\n' "${INPUTS[12]}" > "$OUT/time-controls.json"
printf '%s\n' "${INPUTS[13]}" > "$OUT/decomposition.json"
printf '%s\n' "${INPUTS[14]}" > "$OUT/reacting-initialization.json"
node --input-type=module - "$OUT" <<'NODE'
import{readFileSync,writeFileSync}from'node:fs'; const root=process.argv[2];
const initial=JSON.parse(readFileSync(`${root}/reacting-initialization.json`));
writeFileSync(`${root}/transport-initialization.json`,JSON.stringify({mode:'uniform-cmin',mixtureFraction:initial.mixtureFraction})+'\n');
const controls=JSON.parse(readFileSync(`${root}/time-controls.json`));
for(const kind of ['transport','reacting'])writeFileSync(`${root}/${kind}-observations.json`,JSON.stringify(controls[kind].observations)+'\n');
NODE
stage=preparation; ulimit -c 0
trap 'rc=$?; printf "COLD_BATCH_EXIT utc=%s stage=%s rc=%s job=%s\n" "$(date -u +%FT%TZ)" "$stage" "$rc" "$SLURM_JOB_ID" | tee "$OUT/terminal.txt"; exit "$rc"' EXIT
run_stage() {
 stage=$1; local seconds=$2; shift 2
 printf 'STAGE_START name=%s utc=%s\n' "$stage" "$(date -u +%FT%TZ)"
 if timeout "$seconds" "$@" > "$OUT/logs/$stage.log" 2>&1; then rc=0; else rc=$?; fi
 printf '%s\n' "$rc" > "$OUT/logs/$stage-exit.txt"
 tail -12 "$OUT/logs/$stage.log"; printf 'STAGE_EXIT name=%s rc=%s utc=%s\n' "$stage" "$rc" "$(date -u +%FT%TZ)"; return "$rc"
}
run_stage cold-input-plan 120 node "$HERE/../prepare.mjs" --table-dir "$TABLE" --metadata "$METADATA" \
 --mesh-dir /references/mascotte-mesh-20261026 --thermo-mode cold-real-fluid --thermo-dir "$THERMO" \
 --initialization "$OUT/reacting-initialization.json" --bounds error --ranks "$RANKS" --end-time "${INPUTS[18]}" \
 --initial-dt "${INPUTS[19]}" --max-dt "${INPUTS[20]}" \
 --observations "$OUT/reacting-observations.json" --decomposition "$OUT/decomposition.json"
run_stage build 900 bash -euo pipefail "$HERE/cold-build.sh" "$BUILD" "$ARCHIVE" "$SOURCE" "$FULL"
export LD_LIBRARY_PATH="$FULL/lib:/opt/gcc-11.2.0/lib64:${LD_LIBRARY_PATH:-}"
SOLVER=$BUILD/bin/reactingFoamSolveZ; PROBE=$BUILD/bin/realFluidG2ThermoProbe
G2=$BUILD/source/replication/validation/mascotte-g2/direct-fgm
[[ $(command -v mpirun) == /usr/bin/mpirun && $(command -v mpicc) == /usr/bin/mpicc ]] || exit 5
mpicc -isystem /usr/include/x86_64-linux-gnu -B/usr/lib/x86_64-linux-gnu/ "$HERE/mpi-interface.c" -o "$OUT/mpi-interface"
ldd "$OUT/mpi-interface" > "$OUT/mpi-interface-ldd.txt"
node --input-type=module - "$BUILD" "$OUT" <<'NODE'
import{readFileSync,realpathSync,writeFileSync}from'node:fs';import{createHash}from'node:crypto';
const[build,out]=process.argv.slice(2),solver=readFileSync(`${build}/logs/reactingFoamSolveZ-ldd.txt`,'utf8'),probe=readFileSync(`${out}/mpi-interface-ldd.txt`,'utf8');
const path=(text,name)=>{const match=text.split('\n').find(row=>row.trim().startsWith(name))?.match(/=>\s+(\S+)/);if(!match||!match[1].startsWith('/'))throw Error(`Unresolved ${name}`);return realpathSync(match[1]);};
const mpi=path(solver,'libmpi.so'),pstream=path(solver,'libPstream.so');
if(mpi!==path(probe,'libmpi.so')||pstream.includes('/dummy/'))throw Error('Cold solver/probe MPI mismatch');
const hash=file=>createHash('sha256').update(readFileSync(file)).digest('hex');
writeFileSync(`${out}/mpi-linkage.json`,JSON.stringify({mpi,pstream,mpiSha256:hash(mpi),pstreamSha256:hash(pstream),probeMatchesSolver:true},null,2)+'\n');
NODE
MPI_ARGS=(--mca plm isolated --mca ras '^slurm' --host "localhost:$RANKS" --bind-to none --mca btl self,vader,tcp --mca orte_tmpdir_base "$TMPDIR/mpi" -np "$RANKS")
run_stage mpi 60 /usr/bin/mpirun "${MPI_ARGS[@]}" "$OUT/mpi-interface" "$RANKS"
EXPECTED_SUM=$(( RANKS*(RANKS-1)/2 ))
for ((rank=0;rank<RANKS;rank++)); do grep -Fx "MPI_INTERFACE rank=$rank size=$RANKS sum=$EXPECTED_SUM" "$OUT/logs/mpi.log"; done
for kind in transport reacting; do
 current=$CASE-$kind; chemistry=table; [[ $kind != transport ]] || chemistry=disabled
 offset=15; [[ $kind != reacting ]] || offset=18
 args=(--table-dir "$TABLE" --metadata "$METADATA" --mesh-dir /references/mascotte-mesh-20261026
  --thermo-mode cold-real-fluid --thermo-dir "$THERMO" --initialization "$OUT/$kind-initialization.json"
  --chemistry "$chemistry" --bounds error --ranks "$RANKS" --end-time "${INPUTS[offset]}"
  --initial-dt "${INPUTS[offset+1]}" --max-dt "${INPUTS[offset+2]}"
  --observations "$OUT/$kind-observations.json" --decomposition "$OUT/decomposition.json")
 run_stage "$kind-plan" 120 node "$G2/prepare.mjs" "${args[@]}"
 run_stage "$kind-prepare" 120 node "$G2/prepare.mjs" "${args[@]}" --out "$current"
 run_stage "$kind-checkMesh" 180 checkMesh -case "$current"
 run_stage "$kind-initialize" 300 node "$G2/initialize-cold.mjs" --case "$current" --runtime "$FULL" --probe "$PROBE" --solver "$SOLVER" --apply
 run_stage "$kind-decompose" 180 decomposePar -case "$current"
 run_stage "$kind-solver" 2700 /usr/bin/mpirun "${MPI_ARGS[@]}" "$SOLVER" -case "$current" -parallel
 cp "$OUT/logs/$kind-solver.log" "$current/log.solver"
 run_stage "$kind-reconstruct" 300 reconstructPar -case "$current"
 run_stage "$kind-check" 120 node "$G2/check.mjs" "$current"
done
printf 'Fresh cold transport/reacting diagnostics executed; no independent science approval.\n' > "$OUT/qualification.txt"
