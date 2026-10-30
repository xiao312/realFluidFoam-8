import { readFile, writeFile, copyFile } from 'node:fs/promises';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { loadPhysicalTable, thermoState } from './physical-input.mjs';

const args = process.argv.slice(2), options = {};
for (let i = 0; i < args.length; i += 2) {
  if (!['--table-dir', '--metadata', '--out'].includes(args[i]) || !args[i + 1]) throw new Error('Invalid arguments');
  options[args[i].slice(2)] = args[i + 1];
}
if (!options['table-dir'] || !options.metadata) throw new Error('Use --table-dir DIR --metadata FILE [--out NEW_CASE]');
const input = await loadPhysicalTable(resolve(options['table-dir']), resolve(options.metadata));
const state = input.lookup(0.2, 0.5);
const pressure = input.receipt.case.pressure_pa;
const properties = thermoState(input.metadata, state.y, state.temperature);
const rho = pressure / (properties.gasConstant * state.temperature);
if (!(pressure > 0 && rho > 0 && properties.cv > 0 && state.upper > state.lower) ||
    !(Math.abs(state.source) > 1e-12)) throw new Error('Selected physical state has no usable reaction/progress span');
const available = state.source > 0 ? state.upper - state.c : state.c - state.lower;
let duration = Math.min(1e-5, 0.02 * available * rho / Math.abs(state.source));
let predictedDrift;
for (let attempt = 0; attempt < 30; attempt++) {
  const nextC = state.c + state.source * duration / rho;
  const next = input.lookup(state.z, (nextC - state.lower) / (state.upper - state.lower));
  let temperature = state.temperature;
  for (let iteration = 0; iteration < 20; iteration++) {
    const trial = thermoState(input.metadata, next.y, temperature);
    const correction = (trial.internalEnergy - properties.internalEnergy) / trial.cv;
    temperature -= correction;
    if (!(temperature > 0 && Number.isFinite(temperature))) throw new Error('Invalid projected constant-volume thermo state');
    if (Math.abs(correction) < 1e-9) break;
  }
  const nextThermo = thermoState(input.metadata, next.y, temperature);
  predictedDrift = Math.abs(rho * nextThermo.gasConstant * temperature / pressure - 1);
  if (predictedDrift <= 0.001) break;
  duration /= 2;
}
if (!(predictedDrift <= 0.001 && duration > 1e-14)) throw new Error('Could not find a bounded pressure-drift interval');
const plan = { kind: 'physical-conversion', initial: state, pressure,
  density: rho, absoluteEnthalpy: properties.enthalpy, endTime: duration,
  deltaT: duration / 20, predictedPressureDrift: predictedDrift,
  pressureQualification: 'constant-volume evolution; fixed table chemistry pressure; actual drift <=0.2%',
  inputHashes: input.inputHashes, physicalAcceptance: false };
if (!options.out) { console.log(JSON.stringify(plan, null, 2)); process.exit(0); }
const out = resolve(options.out), here = dirname(fileURLToPath(import.meta.url));
function run(script, arguments_) {
  const result = spawnSync(process.execPath, [resolve(here, script), ...arguments_], { encoding: 'utf8' });
  if (result.status !== 0) throw new Error(result.stderr || result.stdout || `Failed ${script}`);
}
run('prepare.mjs', ['--out', out, '--kind', 'heating']);
run('thermo-export.mjs', [resolve(options.metadata), '--out', `${out}/thermo-input`]);
await copyFile(`${out}/thermo-input/thermophysicalProperties`, `${out}/constant/thermophysicalProperties`);
await writeFile(`${out}/constant/constant.tbl`, input.raw);
const boundary = 'boundaryField { left { type cyclic; } right { type cyclic; } transverse { type empty; } }';
async function field(name, dims, value) {
  await writeFile(`${out}/0/${name}`, `FoamFile { version 2.0; format ascii; class volScalarField; object "${name}"; }
dimensions [${dims}]; internalField uniform ${value};\n${boundary}\n`);
}
for (let i = 0; i < state.y.length; i++) await field(input.metadata.species[i].name, '0 0 0 0 0 0 0', state.y[i]);
await field('p', '1 -1 -2 0 0 0 0', pressure);
await field('T', '0 0 0 1 0 0 0', state.temperature);
await field('Z', '0 0 0 0 0 0 0', state.z);
await field('c', '0 0 0 0 0 0 0', state.c);
await field('Ha', '0 2 -2 0 0 0 0', properties.enthalpy);
let control = await readFile(`${out}/system/controlDict`, 'utf8');
control = control.replace(/endTime [^;]+;/, `endTime ${duration};`)
  .replace(/deltaT [^;]+;/, `deltaT ${duration / 20};`)
  .replace(/writeInterval [^;]+;/, 'writeInterval 2;')
  .replace('fgmEnergyForm sensibleEnthalpy;', 'fgmEnergyForm absoluteEnthalpy;');
await writeFile(`${out}/system/controlDict`, control);
const manifest = JSON.parse(await readFile(`${out}/verification-input.json`, 'utf8'));
Object.assign(manifest, plan, { temperature: state.temperature, energyForm: 'absoluteEnthalpy',
  tableKind: 'finite-rate-physical-table', sourcePressure: pressure,
  heatRelease: state.qFormation, progressSource: state.source, cp: properties.cp,
  gasConstant: input.metadata.gasConstant_J_kmol_K,
  molWeight: input.metadata.gasConstant_J_kmol_K / properties.gasConstant,
  thresholds: { ...manifest.thresholds, energyRelative: 0.01, pressureRelative: 0.002 } });
delete manifest.chemicalEnergyDrop_J_kg_progress;
await writeFile(`${out}/verification-input.json`, JSON.stringify(manifest, null, 2) + '\n');
console.log(JSON.stringify({ created: out, ...plan }, null, 2));
