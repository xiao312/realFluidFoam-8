import { readFile, writeFile, readdir, access } from 'node:fs/promises';
import { resolve, join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { digest } from '../../fgm-of8/direct-verification/physical-input.mjs';

const options = {}, args = process.argv.slice(2);
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--apply') options.apply = true;
  else if (['--case', '--runtime', '--probe', '--solver'].includes(args[i]) && args[i + 1]) options[args[i].slice(2)] = resolve(args[++i]);
  else throw new Error('Use --case CASE --runtime FULL_BUILD --probe EXE --solver EXE [--apply]');
}
for (const key of ['case', 'runtime', 'probe', 'solver']) if (!options[key]) throw new Error(`Missing --${key}`);
const root = options.case, manifest = JSON.parse(await readFile(join(root, 'direct-g2-input.json')));
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
  runtimeSource: runtime.source, runtimeReceiptSha256: digest(receiptRaw), libraries: Object.fromEntries(libraries), binaries,
  thermoDictionarySha256: digest(thermo), tableSha256: manifest.inputHashes.table,
  localized: manifest.initialization.config.mode === 'localized-covered', physicalValidation: false };
if (!options.apply) { console.log(JSON.stringify({ dryRun: true, ...plan }, null, 2)); process.exit(0); }
if (!process.env.SLURM_JOB_ID) throw new Error('Initialization mutation requires the admitted Slurm allocation');
async function fieldHashes() {
  const result = {};
  for (const name of (await readdir(join(root, '0'))).sort()) result[name] = digest(await readFile(join(root, '0', name)));
  return result;
}
const before = await fieldHashes();
const start = { ...plan, jobId: process.env.SLURM_JOB_ID, startedAt: new Date().toISOString(), before };
await writeFile(join(root, 'cold-initialization-start.json'), JSON.stringify(start, null, 2) + '\n');
async function run(binary, arguments_, log) {
  const result = spawnSync(binary, arguments_, { encoding: 'utf8', maxBuffer: 8 * 1024 * 1024 });
  await writeFile(join(root, log), (result.stdout ?? '') + (result.stderr ?? ''));
  if (result.status !== 0) throw new Error(`${binary} failed (${result.status}): inspect ${log}; original attempt retained`);
}
if (plan.localized) await run('setFields', ['-case', root], 'log.ignition');
await run(options.probe, ['-case', root, '-initialize-Ha'], 'log.initialize-Ha');
const marker = await readFile(join(root, 'constant/fgmHaInitialization'));
const after = await fieldHashes();
if (after.Ha === before.Ha) throw new Error('Runtime probe did not replace the zero Ha placeholder');
await writeFile(join(root, 'cold-initialization.json'), JSON.stringify({ ...start,
  completedAt: new Date().toISOString(), after, markerSha256: digest(marker), initialized: true }, null, 2) + '\n');
console.log(JSON.stringify({ initialized: true, case: root, jobId: process.env.SLURM_JOB_ID }));
