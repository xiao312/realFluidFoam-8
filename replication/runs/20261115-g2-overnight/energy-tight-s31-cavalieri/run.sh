#!/usr/bin/env bash
set -euo pipefail
mode=${1:?};Cr=100;phase=full;[[ $Cr == 1 || $Cr == 100 ]];[[ $phase == smoke || $phase == full ]]
input=$G2_RELAXED_INPUT;out=$G2_RELAXED_OUT;build=$G2_RELAXED_BUILD;parent=$build
export G2_COLD_TABLE=/workspace/inputs/steady-flamelet-r3/table
export G2_COLD_MESH=/workspace/mesh-assets/paper-exit-wedge-10000-r1
export G2_COLD_ORIGINAL_THERMO=/workspace/inputs/steady-flamelet-r3/thermo
export G2_COLD_MODULE=$build/source/replication/validation/mascotte-g2/direct-fgm
case=/workspace/cases/g2-relaxed-energy-tight-s31-cavalieri-$mode
end=0.0003;cap=1800;obs=$input/observations.json
[[ ! -e $case ]]
dtmax=5e-7
args=(--closure steady-flamelet --steady-endpoint-policy endpoint64epsilon --table-dir "$G2_COLD_TABLE" --metadata "$G2_COLD_TABLE/phase-metadata.json"
 --mesh-dir "$G2_COLD_MESH" --mesh-mode paper-exit-wedge-10000-v1 --thermo-mode cold-real-fluid --thermo-dir "$G2_COLD_ORIGINAL_THERMO"
 --initialization "$input/initialization.json" --bounds error --chemistry table --ranks 32 --source-integration explicit --skip-unused-diffusion yes
 --transport-tolerance 1e-8 --end-time "$end" --initial-dt 1e-7 --max-dt "$dtmax" --max-co 1 --outer 2 --observations "$obs" --decomposition "$input/decomposition.json")
node "$G2_COLD_MODULE/prepare.mjs" "${args[@]}" > "$out/cr$Cr-$phase-factory-plan.json"
node "$G2_COLD_MODULE/prepare.mjs" "${args[@]}" --out "$case" > "$out/cr$Cr-$phase-factory.json"
node "$input/configure-flow.mjs" "$case" "$Cr" > "$out/cr$Cr-$phase-relaxation-plan.json"
node "$input/configure-flow.mjs" "$case" "$Cr" --apply > "$out/cr$Cr-$phase-relaxation.json"
node "$input/configure-predictor-step.mjs" "$case" > "$out/cr$Cr-$phase-predictor-plan.json"
node "$input/configure-predictor-step.mjs" "$case" --apply > "$out/cr$Cr-$phase-predictor-control.json"
node "$input/configure-clock.mjs" "$case" "$mode" > "$out/source-clock-plan.json"
node "$input/configure-clock.mjs" "$case" "$mode" --apply > "$out/source-clock-input.json"
node "$input/configure-output.mjs" "$case" > "$out/output-plan.json"
node "$input/configure-output.mjs" "$case" --apply > "$out/output-control.json"
node "$input/configure-audit.mjs" "$case" tight > "$out/species-audit-plan.json"
node "$input/configure-audit.mjs" "$case" tight --apply > "$out/species-audit-input.json"
# Read both exact solver entries through the executing OF8 dictionary parser.
for entry in Yi YiFinal Z ZFinal h hFinal Ha HaFinal;do
 value=$(foamDictionary "$case/system/fvSolution" -entry "solvers.$entry.tolerance" -value)
 node -e 'if(Number(process.argv[1])!==1e-12)throw Error("Species tolerance binding failed")' "$value"
 printf '%s tolerance=%s\n' "$entry" "$value" >> "$out/species-tolerance-bindings.txt"
done
checkMesh -case "$case" > "$case/log.checkMesh" 2>&1
"$parent/bin/realFluidG2ThermoProbe" -case "$case" -initialize-Ha > "$case/log.initialize-Ha" 2>&1
node "$input/initialize-boundary-velocity.mjs" "$case" > "$out/cr$Cr-$phase-inlet-plan.json"
node "$input/initialize-boundary-velocity.mjs" "$case" --apply > "$out/cr$Cr-$phase-inlet.json"
# Hash original-zero active dictionaries and fields BEFORE decomposition/execution.
(cd "$case";find 0 constant system -type f -print0 | sort -z | xargs -0 sha256sum > active-timezero.sha256)
decomposePar -case "$case" > "$case/log.decompose" 2>&1
MPI_ARGS=(--mca plm isolated --mca ras '^slurm' --host localhost:32 --bind-to none --mca btl self,vader,tcp --mca orte_tmpdir_base "$TMPDIR/mpi" -np 32)
printf 'CFD_START phase=%s clean_timezero=1 end=%s job=%s utc=%s\n' "$phase" "$end" "$SLURM_JOB_ID" "$(date -u +%FT%TZ)"
if timeout --signal=TERM --kill-after=30 "$cap" mpirun "${MPI_ARGS[@]}" "$build/bin/reactingFoamSolveZ" -case "$case" -parallel > "$case/log.solver" 2>&1;then rc=0;else rc=$?;fi
printf '%s\n' "$rc" > "$case/solver-exit.txt"
printf '{"Cr":%s,"phase":"%s","solverExit":%s,"startTime":0,"scientificAcceptance":false}\n' "$Cr" "$phase" "$rc" >> "$out/phases.jsonl"
if [[ $rc != 0 ]];then tail -50 "$case/log.solver";exit "$rc";fi
reconstructPar -case "$case" -latestTime > "$case/log.reconstruct" 2>&1
printf 'CFD_RETURN phase=%s utc=%s\n' "$phase" "$(date -u +%FT%TZ)"
