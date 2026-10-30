import { readFile, access } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { observationConfig, decompositionConfig } from '../observations.mjs';
const [file, mode] = process.argv.slice(2);
if (!file || !['--plan', '--apply'].includes(mode)) throw new Error('Use cold-preflight.mjs MANIFEST --plan|--apply');
const input = JSON.parse(await readFile(file));
if (input.schema !== 'forge-cold-g2-batch-v1' || !/^[a-f0-9]{40}$/.test(input.sourceCommit)) throw new Error('Invalid source manifest');
const ranks = input.ranks ?? 16, memory = input.memoryGiB ?? 16, endTime = input.g2?.endTime_s ?? 2e-6;
if (!Number.isInteger(ranks) || ranks < 1 || ranks > 32 || !Number.isInteger(memory) || memory < 1 || !(endTime > 0 && endTime <= 0.1)) throw new Error('Invalid admitted resources or end time');
const observations = input.g2?.observations ?? {}, ignition = input.g2?.reactingInitialization;
const caseControls = {};
for (const kind of ['transport','reacting']) {
 const custom=input.g2?.[kind]??{}, duration=custom.endTime_s??endTime;
 for(const key of Object.keys(custom))if(!['endTime_s','initialDt_s','maxDt_s','observations'].includes(key))throw new Error(`Unknown ${kind}.${key}`);
 const initial=custom.initialDt_s??Math.min(1e-9,duration/100), maximum=custom.maxDt_s??Math.min(1e-7,duration/20);
 if(![duration,initial,maximum].every(Number.isFinite)||!(initial>0&&initial<=maximum&&maximum<=duration&&duration<=0.1))throw new Error(`Invalid ${kind} time controls`);
 const selectedObservations=custom.observations??observations;
 observationConfig(selectedObservations,duration);
 caseControls[kind]={endTime_s:duration,initialDt_s:initial,maxDt_s:maximum,observations:selectedObservations};
}
if (!ignition || !['uniform-covered', 'localized-covered'].includes(ignition.mode)) throw new Error('Explicit reactingInitialization required');
const decomposition = decompositionConfig(input.g2?.decomposition ?? {method:'hierarchical',n:[ranks,1,1],order:'xyz'}, ranks);
const safe = value => typeof value === 'string' && /^\/workspace\/[A-Za-z0-9_./-]+$/.test(value) && !value.split('/').includes('..');
for (const value of [input.sourceArchive,input.buildDirectory,input.resultDirectory,input.casePrefix,input.runtimeDirectory,input.table?.directory,input.table?.metadata,input.thermo?.directory]) if (!safe(value)) throw new Error(`Unsafe/missing project path ${value}`);
const bindings = [[input.sourceArchive,input.sourceArchiveSha256],
 [`${input.runtimeDirectory}/build-qualification.json`,input.runtimeReceiptSha256],
 [`${input.table.directory}/physical.tbl`,input.table.sha256], [`${input.table.directory}/receipt.json`,input.table.receiptSha256],
 [input.table.metadata,input.table.metadataSha256], [`${input.thermo.directory}/thermophysicalProperties`,input.thermo.dictionarySha256],
 [`${input.thermo.directory}/manifest.json`,input.thermo.manifestSha256]];
if (bindings.some(([,hash]) => !/^[a-f0-9]{64}$/.test(hash??''))) throw new Error('Missing exact input hash');
if (mode === '--plan') { console.log(JSON.stringify({dryRun:true,...input,ranks,memoryGiB:memory,endTime,caseControls,decomposition,scientificAcceptance:false},null,2)); process.exit(0); }
for (const path of [input.buildDirectory,input.resultDirectory,`${input.casePrefix}-transport`,`${input.casePrefix}-reacting`]) {
 try { await access(path); } catch (error) { if(error.code==='ENOENT')continue; throw error; }
 throw new Error(`Output already exists: ${path}`);
}
for (const [path,hash] of bindings) if(createHash('sha256').update(await readFile(path)).digest('hex')!==hash) throw new Error(`Input hash mismatch ${path}`);
console.log([input.sourceArchive,input.buildDirectory,input.resultDirectory,input.casePrefix,input.runtimeDirectory,input.table.directory,
 input.table.metadata,input.thermo.directory,input.sourceCommit,ranks,memory,endTime,JSON.stringify(caseControls),JSON.stringify(decomposition),JSON.stringify(ignition),
 ...['transport','reacting'].flatMap(kind=>[caseControls[kind].endTime_s,caseControls[kind].initialDt_s,caseControls[kind].maxDt_s])].join('\n'));
