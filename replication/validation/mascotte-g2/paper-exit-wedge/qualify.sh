#!/usr/bin/env bash
set -euo pipefail

[[ $# == 5 && ( $5 == --plan || $5 == --apply ) ]] || {
    printf 'Usage: qualify.sh SOURCE_ROOT NEW_RESULT_DIR NEW_ASSET_DIR SOURCE_COMMIT --plan|--apply\n' >&2; exit 2;
}
SOURCE=$(realpath -m "$1")
OUT=$(realpath -m "$2")
ASSET=$(realpath -m "$3")
SOURCE_COMMIT=$4
mode=$5
[[ $SOURCE_COMMIT =~ ^[a-f0-9]{40}$ ]] || { printf 'Require exact source commit\n' >&2; exit 2; }
for path in "$SOURCE" "$OUT" "$ASSET"; do
    [[ $path == /workspace/* ]] || { printf 'Path must stay below /workspace: %s\n' "$path" >&2; exit 2; }
done
[[ $OUT != "$SOURCE" && $OUT != "$SOURCE/"* && $ASSET != "$SOURCE" && $ASSET != "$SOURCE/"* && $ASSET != "$OUT" && $ASSET != "$OUT/"* && $OUT != "$ASSET/"* ]] || {
    printf 'Source, result and asset paths must be separate\n' >&2; exit 2;
}
MODULE=$SOURCE/replication/validation/mascotte-g2/paper-exit-wedge
CASE=$OUT/case
PYTHON=/opt/python/bin/python3
[[ -f $MODULE/generate.mjs && ! -e $OUT && ! -e $ASSET ]] || {
    printf 'Missing source, or output/asset occupied: preserve and reconcile prior attempt\n' >&2; exit 2;
}
# The adapter has already sourced OF8. Do not pass our arguments into bashrc.
[[ ${WM_PROJECT_DIR:-} == /opt/openfoam8 && ${WM_PROJECT_VERSION:-} == 8 && -x $PYTHON ]] || {
    printf 'Require already qualified OF8 environment and /opt/python\n' >&2; exit 2;
}
for name in node blockMesh checkMesh timeout sha256sum; do command -v "$name" >/dev/null; done
if [[ $mode == --plan ]]; then
    node "$MODULE/generate.mjs"
    printf '{"mode":"plan","source_commit":"%s","output":"%s","asset":"%s","execution_pending":true}\n' "$SOURCE_COMMIT" "$OUT" "$ASSET"
    exit 0
fi
[[ -n ${SLURM_JOB_ID:-} ]] || { printf 'Mesh execution requires a Slurm allocation\n' >&2; exit 2; }
mkdir -p "$(dirname "$OUT")"
mkdir "$OUT"
stage=setup
started_utc=$(date -u +%FT%TZ)
finish() {
    local final_rc=$?
    trap - EXIT
    if "$PYTHON" - "$OUT" "$ASSET" "$SOURCE" "$SOURCE_COMMIT" "$final_rc" "$stage" "$started_utc" <<'PY'
import datetime, hashlib, json, os, pathlib, sys
out, asset, source = map(pathlib.Path, sys.argv[1:4])
commit, rc, stage, started = sys.argv[4], int(sys.argv[5]), sys.argv[6], sys.argv[7]
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
steps=[]
if (out/'steps.tsv').exists():
    for line in (out/'steps.tsv').read_text().splitlines():
        name,code=line.split('\t');steps.append({'step':name,'exit_code':int(code)})
module=source/'replication/validation/mascotte-g2/paper-exit-wedge'
inputs={str(p.relative_to(source)):digest(p) for p in module.iterdir() if p.is_file()}
parser=module.parent/'coarse-wedge/ascii-mesh.mjs'; inputs[str(parser.relative_to(source))]=digest(parser)
artifacts={str(p.relative_to(out)):{'bytes':p.stat().st_size,'sha256':digest(p)}
           for p in out.rglob('*') if p.is_file() and 'polyMesh' not in p.parts and p.name!='phase.json'}
builds={}
for name in ['blockMesh','checkMesh']:
    path=out/'case'/('log.'+name)
    if path.exists():
        lines=path.read_text(errors='replace').splitlines()
        builds[name]={key:next((s for s in lines if s.startswith(prefix)),None)
                      for key,prefix in [('build_line','Build '),('exec_line','Exec ')]}
manifest=asset/'manifest.json'
receipt={'schema':'paper-exit-g2-allocated-qualification/v1','job_id':os.environ['SLURM_JOB_ID'],
 'source_commit_declared_by_admitting_wrapper':commit,'source_file_sha256':inputs,
 'started_utc':started,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'stage_at_exit':stage,'exit_code':rc,'steps':steps,'tool_builds':builds,
 'environment':{k:os.environ.get(k) for k in ['WM_PROJECT_DIR','WM_PROJECT_VERSION','WM_OPTIONS','WM_COMPILER','WM_PRECISION_OPTION','WM_LABEL_SIZE','APPTAINER_CONTAINER']},
 'artifacts':artifacts,'mesh_asset':str(asset),'asset_manifest_sha256':digest(manifest) if manifest.exists() else None,
 'mesh_qualified':rc==0 and manifest.exists(),'CFD_executed':False,'scientific_acceptance':False,
 'interpretation':'Exit-area mesh qualification only; dependent CFD requires this pass, unrelated phases remain separate'}
(out/'phase.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'exit_code':rc,'stage':stage,'mesh_qualified':receipt['mesh_qualified']}))
PY
    then :; else printf 'Could not write phase receipt; existing logs retained\n' >&2; fi
    exit "$final_rc"
}
trap finish EXIT
trap 'exit 143' TERM
trap 'exit 130' INT
run_step() {
    stage=$1
    local logfile=$2 limit=$3 result=0
    shift 3
    if timeout "$limit" "$@" > "$logfile" 2>&1; then result=0; else result=$?; fi
    printf '%s\t%d\n' "$stage" "$result" >> "$OUT/steps.tsv"
    return "$result"
}
node_binary=$(node -p 'process.execPath')
block_binary=$(readlink -f "$(command -v blockMesh)")
check_binary=$(readlink -f "$(command -v checkMesh)")
sha256sum "$node_binary" "$block_binary" "$check_binary" "$PYTHON" > "$OUT/binaries.sha256"
printf 'node=%s\nblockMesh=%s\ncheckMesh=%s\npython=%s\n' "$node_binary" "$block_binary" "$check_binary" "$PYTHON" > "$OUT/binary-paths.txt"
run_step node-version "$OUT/node-version.txt" 15 node --version
run_step blockMesh-help "$OUT/blockMesh-help.txt" 15 blockMesh -help
run_step checkMesh-help "$OUT/checkMesh-help.txt" 15 checkMesh -help
run_step recipe-plan "$OUT/recipe-plan.json" 30 node "$MODULE/generate.mjs"
run_step generate "$OUT/generate.json" 30 node "$MODULE/generate.mjs" --out "$CASE"
run_step blockMesh "$CASE/log.blockMesh" 180 blockMesh -case "$CASE"
run_step checkMesh "$CASE/log.checkMesh" 180 checkMesh -case "$CASE" -allTopology -allGeometry
run_step audit-plan "$OUT/audit-plan.json" 45 node "$MODULE/audit.mjs" --case "$CASE"
mkdir -p "$(dirname "$ASSET")"
run_step audit-asset "$OUT/audit-asset.json" 45 node "$MODULE/audit.mjs" --case "$CASE" --out "$ASSET"
stage=complete
