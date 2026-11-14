import { mkdir, writeFile, readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { mode, recipe, recipeSha256, expectedCounts, expectedPatchFaces,
  blockMeshDictionary, expectedInlet, digest, header } from './recipe.mjs';

const args = process.argv.slice(2);
if (args.length && (args.length !== 2 || args[0] !== '--out')) throw new Error('Use [--out NEW_MESH_CASE]; no argument is read-only');
const dictionary = blockMeshDictionary();
const plan = { schema: 'paper-exit-g2-mesh-recipe/v1', mode, recipe, recipeSha256,
  dictionarySha256: digest(dictionary), generatorSha256: digest(await readFile(fileURLToPath(import.meta.url))),
  expectedCounts, expectedPatchFaces,
  expectedInlets: { loxinlet: expectedInlet('loxinlet'), ch4inlet: expectedInlet('ch4inlet') },
  state: 'dictionary-prepared; blockMesh/checkMesh not executed', paperGeometryQualified: false };
if (args.length) {
  const out = resolve(args[1]);
  await mkdir(out);
  await mkdir(`${out}/system`);
  await mkdir(`${out}/constant`);
  await writeFile(`${out}/system/blockMeshDict`, dictionary);
  await writeFile(`${out}/system/controlDict`, header('controlDict') +
    'application blockMesh; startFrom startTime; startTime 0; stopAt endTime; endTime 1; deltaT 1;\n' +
    'writeControl timeStep; writeInterval 1; writeFormat ascii; writePrecision 16; writeCompression off;\n');
  await writeFile(`${out}/system/fvSchemes`, header('fvSchemes') + 'gradSchemes { default Gauss linear; }\n');
  await writeFile(`${out}/system/fvSolution`, header('fvSolution') + 'solvers {}\n');
  await writeFile(`${out}/paper-exit-mesh-recipe.json`, JSON.stringify(plan, null, 2) + '\n');
}
console.log(JSON.stringify({ dryRun: !args.length, ...plan }, null, 2));
