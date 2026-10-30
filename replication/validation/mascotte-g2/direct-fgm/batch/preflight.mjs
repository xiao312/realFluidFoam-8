import { readFile, access } from 'node:fs/promises';
import { createHash } from 'node:crypto';
const [path, mode] = process.argv.slice(2);
if (!path || !['--plan', '--apply'].includes(mode)) throw new Error('Use preflight.mjs MANIFEST --plan|--apply');
const input = JSON.parse(await readFile(path, 'utf8'));
if (input.schema !== 'forge-warm-g2-batch-v1' || !/^[a-f0-9]{40}$/.test(input.sourceCommit)) throw new Error('Invalid source manifest');
const fields = ['sourceArchive', 'buildDirectory', 'resultDirectory', 'casePrefix'];
const safePath = value => typeof value === 'string' && /^\/workspace\/[A-Za-z0-9_./-]+$/.test(value) && !value.split('/').includes('..');
for (const key of fields) if (!safePath(input[key])) throw new Error(`Unsafe/missing ${key}`);
for (const key of ['directory', 'metadata']) if (!safePath(input.table?.[key])) throw new Error(`Unsafe/missing table.${key}`);
const hashes = [input.sourceArchiveSha256, input.table.sha256, input.table.receiptSha256, input.table.metadataSha256];
if (hashes.some(value => !/^[a-f0-9]{64}$/.test(value ?? ''))) throw new Error('Explicit archive/table hashes required');
if (mode === '--plan') { console.log(JSON.stringify({ ...input, ranks: 4, totalMemoryGiB: 4, g2EndTime_s: 2e-5,
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
  input.table.directory, input.table.metadata, input.sourceCommit].join('\n'));
