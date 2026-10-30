import { readFile, writeFile, cp, access } from 'node:fs/promises';
import { resolve } from 'node:path';
import { spawnSync } from 'node:child_process';

const [directoryArg, probe, apply] = process.argv.slice(2);
if (!directoryArg || !probe || (apply && apply !== '--apply')) throw new Error('Use negative-controls.mjs PAIRS_DIR PROBE [--apply]');
const directory = resolve(directoryArg);
const tests = [
  { name: 'transport', file: 'constant/thermophysicalTransport', before: 'model Fourier', after: 'model Fickian', expected: 'requires explicit laminar momentum' },
  { name: 'combustion', file: 'constant/combustionProperties', before: 'combustionModel fgmTable', after: 'combustionModel laminar', expected: 'requires explicit laminar momentum' },
  { name: 'runtime-edit', file: 'system/controlDict', before: 'runTimeModifiable no', after: 'runTimeModifiable yes', expected: 'requires absoluteEnthalpy' },
  { name: 'internal-access', option: '-read-Dimix', expected: 'Dimix was requested while fgmSkipUnusedDimix is enabled' },
  { name: 'boundary-access', option: '-read-boundary-Dimix', expected: 'Dimix was requested while fgmSkipUnusedDimix is enabled' },
];
if (!apply) { console.log(JSON.stringify({ dryRun: true, directory, probe, tests }, null, 2)); process.exit(0); }
if (!process.env.SLURM_JOB_ID) throw new Error('Negative runtime controls require an admitted Slurm allocation');
const results = [];
for (const test of tests) {
  const out = `${directory}/negative-${test.name}`;
  try { await access(out); throw new Error(`Refuse existing negative control ${out}`); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
  await cp(`${directory}/oxygen-optimized`, out, { recursive: true, errorOnExist: true, force: false });
  if (test.file) {
    const raw = await readFile(`${out}/${test.file}`, 'utf8');
    if (!raw.includes(test.before)) throw new Error('Negative-control precondition absent');
    await writeFile(`${out}/${test.file}`, raw.replace(test.before, test.after));
  }
  const result = spawnSync(probe, ['-case', out, ...(test.option ? [test.option] : [])], { encoding: 'utf8', timeout: 120000 });
  const log = (result.stdout ?? '') + (result.stderr ?? '');
  await writeFile(`${out}/log.negative-control`, log);
  const failedAsExpected = (result.status !== null && result.status !== 0) || result.signal === 'SIGABRT';
  const passed = !result.error && failedAsExpected && log.includes(test.expected);
  results.push({ name: test.name, status: result.status, signal: result.signal, passed, expected: test.expected });
}
const receipt = { schema: 'fgm-unused-diffusion-negative-controls-v1', passed: results.every(r => r.passed),
  results, scientificAcceptance: false };
await writeFile(`${directory}/negative-controls.json`, JSON.stringify(receipt, null, 2) + '\n');
console.log(JSON.stringify(receipt, null, 2));
if (!receipt.passed) process.exitCode = 1;
