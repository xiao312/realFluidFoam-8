import { readFile, writeFile, copyFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { loadPhysicalTable, thermoState } from '../fgm-of8/direct-verification/physical-input.mjs';

const options = {}, args = process.argv.slice(2);
const allowed = ['table-dir', 'metadata', 'out', 'kind', 'delta-t', 'end-time', 'outer', 'integration'];
for (let i = 0; i < args.length; i += 2) {
  const key = args[i].slice(2);
  if (!args[i].startsWith('--') || !allowed.includes(key) || !args[i+1]) throw new Error('Invalid argument');
  options[key] = args[i+1];
}
if (!options['table-dir'] || !options.metadata) throw new Error('Use --table-dir DIR --metadata FILE [--out NEW_CASE]');
const kind = options.kind ?? '0d', dt = Number(options['delta-t'] ?? 25e-9);
const endTime = Number(options['end-time'] ?? 500e-9), outer = Number(options.outer ?? 2);
const integration = options.integration ?? 'strangFixedState';
if (!['0d', '1d'].includes(kind) || ![25e-9, 50e-9].includes(dt) ||
    ![1, 2, 3].includes(outer) || !(endTime >= dt && endTime <= 1e-5) ||
    !['explicit', 'strangFixedState'].includes(integration)) throw new Error('Invalid bounded qualification controls');
const input = await loadPhysicalTable(resolve(options['table-dir']), resolve(options.metadata));
const cells = kind === '0d' ? 8 : 80, velocity = kind === '0d' ? 0 : 10;
const length = kind === '0d' ? 0.1 : 1e-4;
const states = Array.from({ length: cells }, (_, i) => {
  const eta = 0.5 + (kind === '1d' ? 0.03*Math.sin(2*Math.PI*(i+0.5)/cells) : 0);
  const state = input.lookup(0.2, eta);
  state.thermo = thermoState(input.metadata, state.y, state.temperature);
  if (!(state.upper > state.lower && state.thermo.cv > 0 && state.temperature >= 200 && state.temperature <= 6000)) {
    throw new Error('Actual selected table state lies outside this ideal-thermo qualification range');
  }
  return state;
});
const pressure = input.receipt.case.pressure_pa;
if (!(pressure > 0 && Number.isFinite(pressure))) throw new Error('Missing table pressure');
const plan = { schema: 'fgm-source-split-case-v1', startTime: 0, kind, cells, length, velocity,
  dt, endTime, outer, integration, pressure, inputHashes: input.inputHashes,
  thresholds: { massRelative: 1e-7, energyPerChemicalChange: 0.01,
    equationResidualRelative: 1e-6, sourceEnergyW: 1e-20,
    oldTimeAbsolute: 0, lookupCorrections: 0,
    timestepCspanRms: 0.02, outerCspanRms: 0.01 },
  assumptions: ['ideal-gas CFD thermo matches table mechanism', 'global Euler transport',
    'unity-Lewis diffusion', 'no second-order CFD claim', 'fixed-density source stages only'],
  validation: 'pending', scientificAcceptance: false };
if (!options.out) { console.log(JSON.stringify({ dryRun: true, ...plan }, null, 2)); process.exit(0); }
const out = resolve(options.out);
const base = fileURLToPath(new URL('../fgm-of8/direct-verification/', import.meta.url));
function run(script, argv) {
  const result = spawnSync(process.execPath, [resolve(base, script), ...argv], { encoding: 'utf8' });
  if (result.status !== 0) throw new Error(result.stderr || result.stdout || `Failed ${script}`);
}
run('prepare.mjs', ['--out', out, '--kind', 'heating', '--cells', String(cells), '--delta-t', String(dt)]);
run('thermo-export.mjs', [resolve(options.metadata), '--out', `${out}/thermo-input`]);
await copyFile(`${out}/thermo-input/thermophysicalProperties`, `${out}/constant/thermophysicalProperties`);
await writeFile(`${out}/constant/constant.tbl`, input.raw);
// Bind the retained copy explicitly, including when the case is decomposed.
const combustion = (await readFile(`${out}/constant/combustionProperties`, 'utf8'))
  .replace('table "constant.tbl";', `table "${out.replaceAll('\\', '/')}/constant/constant.tbl";`);
await writeFile(`${out}/constant/combustionProperties`, combustion);
const boundary = 'boundaryField { left { type cyclic; } right { type cyclic; } transverse { type empty; } }';
async function field(name, dimensions, values, vector = false) {
  const raw = vector ? `uniform (${velocity} 0 0)` : `nonuniform List<scalar>\n${cells}\n(\n${values.join('\n')}\n)`;
  await writeFile(`${out}/0/${name}`, `FoamFile { version 2.0; format ascii; class ${vector ? 'volVectorField' : 'volScalarField'}; object "${name}"; }
dimensions [${dimensions}]; internalField ${raw};\n${boundary}\n`);
}
for (let i = 0; i < input.metadata.species.length; i++) {
  await field(input.metadata.species[i].name, '0 0 0 0 0 0 0', states.map(s => s.y[i]));
}
for (const [name, dimensions, pick] of [
  ['p', '1 -1 -2 0 0 0 0', () => pressure], ['T', '0 0 0 1 0 0 0', s => s.temperature],
  ['Z', '0 0 0 0 0 0 0', s => s.z], ['c', '0 0 0 0 0 0 0', s => s.c],
  ['Ha', '0 2 -2 0 0 0 0', s => s.thermo.enthalpy],
]) await field(name, dimensions, states.map(pick));
await field('U', '0 1 -1 0 0 0 0', [], true);
let mesh = await readFile(`${out}/system/blockMeshDict`, 'utf8');
if (kind === '1d') mesh = mesh.replaceAll('(0.1 ', '(0.0001 ');
await writeFile(`${out}/system/blockMeshDict`, mesh);
let control = await readFile(`${out}/system/controlDict`, 'utf8');
control = control.replace(/endTime [^;]+;/, `endTime ${endTime};`)
  .replace(/writeInterval [^;]+;/, 'writeInterval 1;')
  .replace('fgmEnergyForm sensibleEnthalpy;', 'fgmEnergyForm absoluteEnthalpy;');
control += `\nfgmSourceIntegration ${integration};\nfgmProgressSourceEnabled yes;\n`;
control += `functions { sourceDensity { type writeObjects;
 libs ("libutilityFunctionObjects.so"); objects (rho); writeOption anyWrite;
 writeControl timeStep; writeInterval 1; } }\n`;
await writeFile(`${out}/system/controlDict`, control);
const solution = (await readFile(`${out}/system/fvSolution`, 'utf8'))
  .replace(/nOuterCorrectors \d+;/, `nOuterCorrectors ${outer};`).replace(/pRef [^;]+;/, `pRef ${pressure};`);
await writeFile(`${out}/system/fvSolution`, solution);
const receipt = JSON.stringify({ ...plan,
  states: states.map(s => ({ z: s.z, eta: s.eta, c: s.c, source: s.source, temperature: s.temperature,
    cMin: s.lower, cMax: s.upper, Ha: s.thermo.enthalpy,
    density: pressure/(s.thermo.gasConstant*s.temperature) })) }, null, 2)+'\n';
await writeFile(`${out}/source-split-input.json`, receipt);
// Replace the base generator's analytic-test receipt; its criteria do not apply.
await writeFile(`${out}/verification-input.json`, receipt);
console.log(JSON.stringify({ created: out, ...plan }, null, 2));
