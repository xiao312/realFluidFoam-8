import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { digest } from '../../fgm-of8/direct-verification/physical-input.mjs';
const source = 'ce76de25f24cfd8572b04324b192ae9544a5dbc9';
const paths = ['src', 'applications/solvers/reactingFoamSolveZ',
  'replication/validation/realfluid-g2-thermo/probe'];
const repository = resolve(dirname(fileURLToPath(import.meta.url)), '../../../..');
const args = process.argv.slice(2);
if (args.length && (args.length !== 2 || args[0] !== '--out')) throw new Error('Use freeze.mjs [--out NEW_DIR]');
const git = (...args_) => {
  const result = spawnSync('git', args_, { cwd: repository, maxBuffer: 32 * 1024 * 1024 });
  if (result.status !== 0) throw new Error(result.stderr.toString());
  return result.stdout;
};
const entries = git('ls-tree', '-rz', '--long', source, '--', ...paths).toString().split('\0').filter(Boolean).map(line => {
  const match = /^(\d+) blob ([0-9a-f]{40})\s+(\d+)\t(.+)$/.exec(line);
  if (!match || !['100644', '100755', '120000'].includes(match[1])) throw new Error(`Unsupported source tree entry ${line}`);
  return { mode: match[1], blob: match[2], bytes: Number(match[3]), path: match[4] };
});
if (!args.length) { console.log(JSON.stringify({ dryRun: true, source, entries: entries.length }, null, 2)); process.exit(0); }
const out = resolve(args[1]); await mkdir(out);
git('-c', 'core.autocrlf=false', '-c', 'core.eol=lf', 'archive', '--format=tar', '--output', `${out}/candidate.tar`, source, ...paths);
const record = { schema: 'full-git-source-blobs-v1', source, paths, entries };
const raw = JSON.stringify(record, null, 2) + '\n';
await writeFile(`${out}/source-blobs.json`, raw);
const receipt = { source, sourceArchiveSha256: digest(await readFile(`${out}/candidate.tar`)), sourceBlobsSha256: digest(raw), entries: entries.length };
await writeFile(`${out}/freeze-receipt.json`, JSON.stringify(receipt, null, 2) + '\n');
console.log(JSON.stringify(receipt, null, 2));
