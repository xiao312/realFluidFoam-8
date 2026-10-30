import { readFile, writeFile, readdir, lstat, readlink, realpath, symlink, mkdir, access, rm } from 'node:fs/promises';
import { resolve, dirname, relative } from 'node:path';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
const [file, action = '--plan'] = process.argv.slice(2);
if (!file || !['--plan', '--inputs', '--source', '--prepare-build', '--receipt'].includes(action)) throw new Error('Invalid package command');
const m = JSON.parse(await readFile(file, 'utf8'));
if (m.schema !== 'fgm-diffusion-allocation-v1' || m.source !== 'ce76de25f24cfd8572b04324b192ae9544a5dbc9') throw new Error('Unexpected frozen candidate');
if (!/^[a-f0-9]{40}$/.test(m.packageSource ?? '') || !/^[a-f0-9]{64}$/.test(m.packageArchiveSha256 ?? '')) throw new Error('Qualification script source/archive identity required');
for (const key of ['sourceArchive', 'sourceBlobs', 'fullRuntime', 'build', 'out', 'table', 'metadata', 'thermo']) {
  if (typeof m[key] !== 'string' || !m[key].startsWith('/workspace/') || resolve(m[key]) !== m[key]) throw new Error(`Expected normalized project path: ${key}`);
}
const hash = raw => createHash('sha256').update(raw).digest('hex');
const checkFile = async (path, expected) => {
  const raw = await readFile(path); if (hash(raw) !== expected) throw new Error(`Hash mismatch: ${path}`); return raw;
};
const full = JSON.parse(await checkFile(`${m.fullRuntime}/build-qualification.json`, m.fullReceiptSha256));
const retained = full.products.filter(p => /^lib\/lib[^/]+\.so$/.test(p.file));
if (full.source !== '282aa996a78939cbdaf591520231fb2c0476567d' || !full.compile_link_help_passed || retained.length !== 15) throw new Error('Unqualified retained runtime');
const blobs = JSON.parse(await checkFile(m.sourceBlobs, m.sourceBlobsSha256));
if (blobs.source !== m.source || blobs.schema !== 'full-git-source-blobs-v1') throw new Error('Wrong blob manifest');
if (['--plan', '--inputs'].includes(action)) {
  await checkFile(m.sourceArchive, m.sourceArchiveSha256);
  for (const p of retained) { const raw = await checkFile(`${m.fullRuntime}/${p.file}`, p.sha256); if (raw.length !== p.bytes) throw new Error('Product size mismatch'); }
  for (const path of [m.build, m.out]) {
    try { await access(path); throw new Error(`Refuse existing output ${path}`); } catch (e) { if (e.code !== 'ENOENT') throw e; }
  }
  if (action === '--plan') console.log(JSON.stringify({ dryRun: true, ...m, retainedLibraries: 13, rebuiltLibraries: 2, entries: blobs.entries.length }, null, 2));
  else console.log([m.sourceArchive, m.build, m.out, m.fullRuntime, m.table, m.metadata, m.thermo, m.source].join('\n'));
  process.exit(0);
}
if (!process.env.SLURM_JOB_ID) throw new Error('Mutation requires admitted Slurm allocation');
const source = `${m.build}/source`;
if (action === '--source') {
  for (const entry of blobs.entries) {
    const path = resolve(source, entry.path);
    if (!path.startsWith(source + '/')) throw new Error('Source path escape');
    const stat = await lstat(path);
    const raw = entry.mode === '120000' ? Buffer.from(await readlink(path)) : await readFile(path);
    if ((entry.mode === '120000') !== stat.isSymbolicLink() || raw.length !== entry.bytes) throw new Error(`Source type/size mismatch ${entry.path}`);
    const blob = createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex');
    if (blob !== entry.blob) throw new Error(`Source blob mismatch ${entry.path}`);
  }
  await writeFile(`${m.build}/source-verification.json`, JSON.stringify({ source: m.source, entries: blobs.entries.length,
    sourceArchiveSha256: m.sourceArchiveSha256, sourceBlobsSha256: m.sourceBlobsSha256, allBlobsMatch: true }, null, 2) + '\n');
  console.log(`Verified ${blobs.entries.length} exact Git source blobs`);
} else if (action === '--prepare-build') {
  const verified = JSON.parse(await readFile(`${m.build}/source-verification.json`));
  if (!verified.allBlobsMatch || verified.source !== m.source) throw new Error('Source audit absent');
  const modules = [], removed = [];
  async function walk(dir) {
    for (const entry of await readdir(dir, { withFileTypes: true })) {
      const path = `${dir}/${entry.name}`;
      if (entry.name === 'lnInclude' || (dir.endsWith('/Make') && entry.name.startsWith('linux'))) {
        if (!path.startsWith(source + '/')) throw new Error('Generated-path escape');
        await rm(path, { recursive: true, force: false }); removed.push(relative(source, path));
      } else if (entry.isDirectory()) {
        if (entry.name === 'Make') { try { await access(`${path}/options`); modules.push(dirname(path)); } catch (e) { if (e.code !== 'ENOENT') throw e; } }
        await walk(path);
      }
    }
  }
  await walk(source);
  const selected = ['src/thermophysicalModels/basic', 'src/thermophysicalModels/reactionThermo',
    'applications/solvers/reactingFoamSolveZ', 'replication/validation/realfluid-g2-thermo/probe'];
  const changes = [];
  for (const module of selected) {
    const path = `${source}/${module}/Make/options`, before = await readFile(path, 'utf8');
    let after = before.replace(/^(LIB_LIBS|EXE_LIBS)[ \t]*=[ \t]*/gm, '$1 = -B"/usr/lib/x86_64-linux-gnu/" -L"$(FOAM_LIBBIN)" ');
    after = after.replace(/^EXE_INC[ \t]*=[ \t]*/m, 'EXE_INC = -isystem "/usr/include/x86_64-linux-gnu" ');
    after += '\nLIB_PLATFORMS = $(FOAM_USER_LIBBIN)\n';
    if (after === before) throw new Error('No compiler adjustment');
    await writeFile(path, after); changes.push({ file: relative(source, path), beforeSha256: hash(before), afterSha256: hash(after) });
  }
  await writeFile(`${m.build}/build-adjustments.json`, JSON.stringify({ source: m.source, changes, removedGenerated: removed }, null, 2) + '\n');
  for (const p of retained) if (!['lib/libfluidThermophysicalModels.so', 'lib/libreactionThermophysicalModels.so'].includes(p.file))
    await symlink(`${m.fullRuntime}/${p.file}`, `${m.build}/${p.file}`);
  for (const module of modules) if (module.startsWith(`${source}/src/`)) {
    const result = spawnSync('wmakeLnInclude', ['-u', module], { encoding: 'utf8' });
    if (result.status !== 0) throw new Error(result.stderr || result.stdout || `Cannot generate headers: ${module}`);
  }
} else if (action === '--receipt') {
  const products = [];
  for (const file of [...retained.map(p => p.file), 'bin/reactingFoamSolveZ', 'bin/realFluidG2ThermoProbe']) {
    const path = `${m.build}/${file}`, raw = await readFile(path);
    const result = spawnSync('ldd', [path], { encoding: 'utf8' });
    if (result.status || result.stdout.includes('not found')) throw new Error(`Unresolved product ${file}`);
    if (file.startsWith('bin/')) for (const required of ['specie', 'fluidThermophysicalModels', 'reactionThermophysicalModels'])
      if (!result.stdout.includes(`lib${required}.so =>`)) throw new Error(`Required full-runtime binding absent: ${file}/${required}`);
    await writeFile(`${m.build}/logs/${file.replaceAll('/', '-')}.ldd`, result.stdout);
    for (const p of retained) {
      const name = p.file.slice(4), line = result.stdout.split('\n').find(row => row.trim().startsWith(name + ' =>'));
      if (line) {
        const actual = line.match(/=>\s+(\S+)/)?.[1];
        if (!actual || await realpath(actual) !== await realpath(`${m.build}/${p.file}`)) throw new Error(`Library binding mismatch ${file}: ${name}`);
      }
    }
    const inherited = retained.find(p => p.file === file);
    const reused = inherited && !['lib/libfluidThermophysicalModels.so', 'lib/libreactionThermophysicalModels.so'].includes(file);
    if (reused && (hash(raw) !== inherited.sha256 || raw.length !== inherited.bytes)) throw new Error('Retained library changed');
    products.push({ file, bytes: raw.length, sha256: hash(raw), reused: Boolean(reused),
      source: reused ? full.source : m.source });
  }
  const receipt = { source: m.source, packageSource: m.packageSource, packageArchiveSha256: m.packageArchiveSha256, custom_library_count: 15, products,
    sourceArchiveSha256: m.sourceArchiveSha256, sourceBlobsSha256: m.sourceBlobsSha256,
    retainedRuntimeReceiptSha256: m.fullReceiptSha256, rebuiltLibraries: ['fluidThermophysicalModels', 'reactionThermophysicalModels'],
    compile_link_help_passed: true, physical_validation: false };
  await writeFile(`${m.build}/build-qualification.json`, JSON.stringify(receipt, null, 2) + '\n');
  console.log('Selective full-runtime build receipt:15 libraries,13 retained,2 rebuilt; physical qualification pending');
}
