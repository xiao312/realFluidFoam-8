import { readFile, access } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { observationConfig, decompositionConfig } from '../observations.mjs';
const [path, mode] = process.argv.slice(2);
if (!path || !['--plan', '--apply'].includes(mode)) throw new Error('Use preflight.mjs MANIFEST --plan|--apply');
const input = JSON.parse(await readFile(path, 'utf8'));
if (input.schema !== 'forge-warm-g2-batch-v1' || !/^[a-f0-9]{40}$/.test(input.sourceCommit)) throw new Error('Invalid source manifest');
const ranks = input.ranks ?? 4, memoryGiB = input.memoryGiB ?? 4;
const endTime = input.g2?.endTime_s ?? 2e-5;
if (!Number.isInteger(ranks) || ranks < 1 || ranks > 32 || !Number.isInteger(memoryGiB) || memoryGiB < 1 ||
    !Number.isFinite(endTime) || endTime <= 0 || endTime > 0.1) throw new Error('Invalid ranks, memoryGiB or G2 endTime_s');
for (const key of Object.keys(input.g2 ?? {})) if (!['endTime_s', 'observations', 'decomposition', 'nasaExtrapolation_K'].includes(key)) throw new Error(`Unknown g2.${key}`);
const nasaBounds = input.g2?.nasaExtrapolation_K;
if (nasaBounds && (!Array.isArray(nasaBounds) || nasaBounds.length !== 2 || !nasaBounds.every(Number.isFinite) ||
    !(nasaBounds[0] > 0 && nasaBounds[1] > nasaBounds[0]))) throw new Error('Invalid g2.nasaExtrapolation_K');
const observations = input.g2?.observations ?? {};
observationConfig(observations, endTime);
const defaultDecomposition = [16, 32].includes(ranks)
  ? { method: 'hierarchical', n: [8, ranks / 8, 1], order: 'xyz' } : { method: 'simple', n: [ranks, 1, 1] };
const decomposition = decompositionConfig(input.g2?.decomposition ?? defaultDecomposition, ranks);
const contactCells = Math.max(80, 4 * ranks);
const fields = ['sourceArchive', 'buildDirectory', 'resultDirectory', 'casePrefix'];
const safePath = value => typeof value === 'string' && /^\/workspace\/[A-Za-z0-9_./-]+$/.test(value) && !value.split('/').includes('..');
for (const key of fields) if (!safePath(input[key])) throw new Error(`Unsafe/missing ${key}`);
for (const key of ['directory', 'metadata']) if (!safePath(input.table?.[key])) throw new Error(`Unsafe/missing table.${key}`);
const hashes = [input.sourceArchiveSha256, input.table.sha256, input.table.receiptSha256, input.table.metadataSha256];
if (hashes.some(value => !/^[a-f0-9]{64}$/.test(value ?? ''))) throw new Error('Explicit archive/table hashes required');
if (mode === '--plan') { console.log(JSON.stringify({ ...input, ranks, totalMemoryGiB: memoryGiB, g2EndTime_s: endTime,
  contactCells, observations, decomposition, mpiExpectedReduction: ranks * (ranks - 1) / 2,
  librarySha256: '3b0f1926a977f48701587cd323093d592dcb2a4020efd198e81ea72889d3d16d',
  mutates: false, qualification: 'Plan only; input hashes are checked at execution before any case creation' }, null, 2)); process.exit(0); }
for (const path of [input.buildDirectory, input.resultDirectory,
  ...['heating', 'contact', 'conversion', 'physical', 'contact-mpi', 'g2'].map(suffix => `${input.casePrefix}-${suffix}`)]) {
  try { await access(path); throw new Error(`Refusing existing output ${path}`); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
}
const files = [[input.sourceArchive, input.sourceArchiveSha256],
  [`${input.table.directory}/physical.tbl`, input.table.sha256],
  [`${input.table.directory}/receipt.json`, input.table.receiptSha256],
  [input.table.metadata, input.table.metadataSha256]];
for (const [file, expected] of files) {
  const actual = createHash('sha256').update(await readFile(file)).digest('hex');
  if (actual !== expected) throw new Error(`Input hash mismatch ${file}`);
}
// Safe literal path lines, consumed by readarray; never evaluated as shell code.
console.log([input.sourceArchive, input.buildDirectory, input.resultDirectory, input.casePrefix,
  input.table.directory, input.table.metadata, input.sourceCommit, ranks, endTime, contactCells, memoryGiB,
  JSON.stringify(observations), JSON.stringify(decomposition), nasaBounds ? nasaBounds.join(',') : 'original'].join('\n'));
