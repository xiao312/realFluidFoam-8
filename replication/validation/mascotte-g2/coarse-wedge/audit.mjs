import { mkdir, copyFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { readMesh, checkEvidence, inspectCoarseMesh } from './mesh.mjs';

const args = process.argv.slice(2), options = {};
for (let i = 0; i < args.length; i += 2) {
  if (!['--case', '--out'].includes(args[i]) || !args[i + 1]) throw new Error('Use --case EXECUTED_MESH_CASE [--out NEW_MESH_ASSET]');
  options[args[i].slice(2)] = resolve(args[i + 1]);
}
if (!options.case) throw new Error('Missing --case');
const root = options.case;
const evidence = await checkEvidence(root, 'system/blockMeshDict');
const mesh = await readMesh(`${root}/constant/polyMesh`);
const manifest = { ...mesh, schema: 'coarse-g2-qualified-mesh-asset/v1',
  evidence,
  qualification: 'Actual mesh-tool completion plus measured geometry; not CFD or paper validation' };
if (options.out) {
  await mkdir(options.out); await mkdir(`${options.out}/polyMesh`);
  await copyFile(`${root}/system/blockMeshDict`, `${options.out}/blockMeshDict`);
  for (const name of ['coarse-mesh-recipe.json', 'log.blockMesh', 'log.checkMesh']) await copyFile(`${root}/${name}`, `${options.out}/${name}`);
  for (const file of mesh.files) await copyFile(`${root}/constant/polyMesh/${file.name}`, `${options.out}/polyMesh/${file.name}`);
  await writeFile(`${options.out}/manifest.json`, JSON.stringify(manifest, null, 2) + '\n');
  await checkEvidence(options.out); await inspectCoarseMesh(options.out);
}
console.log(JSON.stringify({ dryRun: !options.out, ...manifest }, null, 2));
