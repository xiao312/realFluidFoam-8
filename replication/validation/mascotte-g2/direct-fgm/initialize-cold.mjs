import { readFile, writeFile, readdir, access, copyFile } from 'node:fs/promises';
import { resolve, join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { openSync, closeSync, writeSync } from 'node:fs';
import { digest } from '../../fgm-of8/direct-verification/physical-input.mjs';

const options = {}, args = process.argv.slice(2);
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--apply') options.apply = true;
  else if (args[i] === '--parallel-ranks' && args[i+1]) options.ranks = Number(args[++i]);
  else if (['--case', '--runtime', '--probe', '--solver', '--input-manifest'].includes(args[i]) && args[i + 1]) options[args[i].slice(2)] = resolve(args[++i]);
  else throw new Error('Use --case CASE --runtime FULL_BUILD --probe EXE --solver EXE [--parallel-ranks N] [--input-manifest FILE] [--apply]');
}
for (const key of ['case', 'runtime', 'probe', 'solver']) if (!options[key]) throw new Error(`Missing --${key}`);
const ranks = options.ranks ?? 1;
if (!Number.isInteger(ranks) || ranks<1 || ranks>32) throw new Error('parallel-ranks must be1..32');
const root = options.case, manifestPath=options['input-manifest']??join(root,'direct-g2-input.json');
const manifestRaw=await readFile(manifestPath), manifest=JSON.parse(manifestRaw);
if (manifest.startTime !== 0 || manifest.thermodynamics?.mode !== 'cold-real-fluid' || !manifest.thermodynamics.requiresRuntimeHaInitialization) throw new Error('A prepared fresh cold-real-fluid case is required');
const entries = await readdir(root);
if (!entries.includes('0') || entries.some(name => /^processor\d+$/.test(name) || (/^\d/.test(name) && Number(name) !== 0 && Number.isFinite(Number(name))))) throw new Error('Initialization requires an undecomposed time-zero-only case');
for (const name of ['constant/fgmHaInitialization', 'cold-initialization.json', 'cold-initialization-start.json']) {
  try { await access(join(root, name)); } catch (error) { if (error.code === 'ENOENT') continue; throw error; }
  throw new Error(`Existing ${name}; preserve this attempt and prepare a new case`);
}
const thermo = await readFile(join(root, 'constant/thermophysicalProperties'));
if (digest(thermo) !== manifest.thermodynamics.dictionarySha256) throw new Error('Case thermo dictionary changed after preparation');
const ha = await readFile(join(root, '0/Ha'), 'utf8');
if (!/internalField\s+uniform\s+0\s*;/.test(ha)) throw new Error('Expected explicit uninitialized Ha placeholder');
const receiptRaw = await readFile(join(options.runtime, 'build-qualification.json'));
const runtime = JSON.parse(receiptRaw);
if (runtime.compile_link_help_passed !== true || runtime.custom_library_count !== 15 || !Array.isArray(runtime.products)) throw new Error('Complete qualified full-fork library build is required');
const libraries = new Map();
for (const product of runtime.products.filter(p => /^lib\/lib[^/]+\.so$/.test(p.file))) {
  const file = join(options.runtime, product.file), raw = await readFile(file);
  if (raw.length !== product.bytes || digest(raw) !== product.sha256) throw new Error(`Full-library product identity mismatch: ${product.file}`);
  libraries.set(product.file.slice(4), { path: file, sha256: product.sha256 });
}
if (libraries.size !== 15) throw new Error('Incomplete full-library product inventory');
const binaries = {};
for (const name of ['probe', 'solver']) {
  const binary = options[name], raw = await readFile(binary);
  const result = spawnSync('ldd', [binary], { encoding: 'utf8' });
  if (result.status !== 0 || /not found/.test(result.stdout)) throw new Error(`Unresolved ${name} runtime: ${result.stderr || result.stdout}`);
  const resolved = new Set();
  for (const line of result.stdout.split('\n')) {
    const match = /^\s*(\S+)\s+=>\s+(\S+)/.exec(line);
    if (match && libraries.has(match[1])) {
      if (resolve(match[2]) !== resolve(libraries.get(match[1]).path)) throw new Error(`Mixed stock/full runtime: ${line.trim()}`);
      resolved.add(match[1]);
    }
  }
  for (const lib of ['libspecie.so', 'libfluidThermophysicalModels.so', 'libreactionThermophysicalModels.so', ...(name === 'solver' ? ['libcombustionModels.so'] : [])]) {
    if (!resolved.has(lib)) throw new Error(`${name} does not resolve required full library ${lib}`);
  }
  binaries[name] = { path: binary, sha256: digest(raw), bytes: raw.length, ldd: result.stdout };
}
const plan = { schema: 'direct-cold-ha-initialization/v1', case: root, startTime: 0,
  ranks, manifestSha256:digest(manifestRaw),
  runtimeSource: runtime.source, runtimeReceiptSha256: digest(receiptRaw), libraries: Object.fromEntries(libraries), binaries,
  thermoDictionarySha256: digest(thermo), tableSha256: manifest.inputHashes.table,
  localized: manifest.initialization.config.mode === 'localized-covered', physicalValidation: false };
if (!options.apply) { console.log(JSON.stringify({ dryRun: true, ...plan }, null, 2)); process.exit(0); }
if (!process.env.SLURM_JOB_ID) throw new Error('Initialization mutation requires the admitted Slurm allocation');
if (ranks>1 && (Number(process.env.SLURM_NTASKS)!==ranks || Number(process.env.SLURM_JOB_NUM_NODES??1)!==1)) throw new Error('Parallel initialization must match the single-node admission');
if (ranks>1) {
  const linked=(text,name)=>text.split('\n').find(line=>line.trim().startsWith(name))?.match(/=>\s+(\S+)/)?.[1];
  for(const name of ['libPstream.so','libmpi.so']){
    const path=linked(binaries.probe.ldd,name);
    if(!path?.startsWith('/')||path.includes('/dummy/')||path!==linked(binaries.solver.ldd,name))throw new Error(`Probe/solver MPI linkage mismatch ${name}`);
  }
}
async function fieldHashes() {
  const result = {};
  for (const name of (await readdir(join(root, '0'))).sort()) result[name] = digest(await readFile(join(root, '0', name)));
  return result;
}
const before = await fieldHashes();
const start = { ...plan, jobId: process.env.SLURM_JOB_ID, startedAt: new Date().toISOString(), before };
await writeFile(join(root, 'cold-initialization-start.json'), JSON.stringify(start, null, 2) + '\n');
async function run(binary, arguments_, log) {
  const descriptor = openSync(join(root, log), 'wx');
  let result;
  try {
    writeSync(descriptor, `INITIALIZATION_PROCESS_START utc=${new Date().toISOString()} binary=${binary}\n`);
    result = spawnSync(binary, arguments_, { stdio: ['ignore', descriptor, descriptor] });
    writeSync(descriptor, `INITIALIZATION_PROCESS_EXIT utc=${new Date().toISOString()} status=${result.status} signal=${result.signal ?? 'none'} error=${result.error?.message ?? 'none'}\n`);
  } finally { closeSync(descriptor); }
  if (result.status !== 0) throw new Error(`${binary} failed (${result.status}): inspect ${log}; original attempt retained`);
}
if (plan.localized) await run('setFields', ['-case', root], 'log.ignition');
const rankOutputs=[];
if(ranks>1){
  await run('decomposePar',['-case',root],'log.initialize-decompose');
  await run('/usr/bin/mpirun',['--mca','plm','isolated','--mca','ras','^slurm','--host',`localhost:${ranks}`,
    '--bind-to','none','--mca','btl','self,vader,tcp','--mca','orte_tmpdir_base',join(process.env.TMPDIR??root,'initialize-mpi'),
    '-np',String(ranks),options.probe,'-case',root,'-initialize-Ha','-parallel'],'log.initialize-Ha');
  for(let rank=0;rank<ranks;rank++){
    const prefix=join(root,`processor${rank}`), rawMarker=await readFile(join(prefix,'constant/fgmHaInitialization'));
    const text=rawMarker.toString(), field=await readFile(join(prefix,'0/Ha'));
    if(!new RegExp(`preparedRank\\s+${rank}\\s*;`).test(text)||!new RegExp(`preparedRanks\\s+${ranks}\\s*;`).test(text)||!/preparedTime\s+0\s*;/.test(text))throw new Error(`Rank${rank} marker mismatch`);
    if(/internalField\s+uniform\s+0\s*;/.test(field.toString()))throw new Error(`Rank${rank} retained placeholder Ha`);
    rankOutputs.push({rank,HaSha256:digest(field),markerSha256:digest(rawMarker),
      boundaryAuditSha256:digest(await readFile(join(prefix,'ha-initialization-boundaries.csv')))});
  }
  // OF8 excludes time zero by default, even with an explicit -time selector.
  await run('reconstructPar',['-case',root,'-withZero','-time','0','-fields','(Ha)'],'log.initialize-reconstruct-Ha');
  await copyFile(join(root,'processor0/constant/fgmHaInitialization'),join(root,'constant/fgmHaInitialization'));
}else await run(options.probe, ['-case', root, '-initialize-Ha'], 'log.initialize-Ha');
const marker = await readFile(join(root, 'constant/fgmHaInitialization'));
const after = await fieldHashes();
if (after.Ha === before.Ha) throw new Error('Runtime probe did not replace the zero Ha placeholder');
await writeFile(join(root, 'cold-initialization.json'), JSON.stringify({ ...start,
  completedAt: new Date().toISOString(), after, rankOutputs, markerSha256: digest(marker), initialized: true }, null, 2) + '\n');
console.log(JSON.stringify({ initialized: true, case: root, jobId: process.env.SLURM_JOB_ID }));
