import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { loadPhysicalTable, digest } from '../../fgm-of8/direct-verification/physical-input.mjs';
const [manifestFile, apply] = process.argv.slice(2);
if (!manifestFile || (apply && apply !== '--apply')) throw new Error('Use prepare-cfd.mjs MANIFEST [--apply]');
const m = JSON.parse(await readFile(manifestFile, 'utf8'));
const table = await loadPhysicalTable(m.table, m.metadata);
const thermo = JSON.parse(await readFile(`${m.thermo}/manifest.json`));
const dictionary = await readFile(`${m.thermo}/thermophysicalProperties`);
if (thermo.equationOfState !== 'soaveRedlichKwong' || thermo.mechanism_sha256 !== table.metadata.mechanismSha256) throw new Error('Matched SRK/physical table required');
const names = table.metadata.species.map(row => row.name);
if (JSON.stringify(names) !== JSON.stringify(thermo.species.map(row => row.name))) throw new Error('Thermo species differ');
const controls = m.cfdParity ?? {};
for (const key of Object.keys(controls)) if (!['chemistry', 'sourceIntegration', 'deltaT_s', 'initialEta'].includes(key)) throw new Error(`Unknown cfdParity.${key}`);
const chemistry = controls.chemistry ?? 'disabled', sourceIntegration = controls.sourceIntegration ?? 'explicit';
const cells = 48, deltaT = controls.deltaT_s ?? 1e-9, endTime = 20 * deltaT, eta = controls.initialEta ?? 0.8;
if (!['disabled', 'table'].includes(chemistry) || !['explicit', 'strangFixedState'].includes(sourceIntegration) ||
    !Number.isFinite(deltaT) || deltaT <= 0 || deltaT > 5e-8 || !Number.isFinite(eta) || eta <= .03 || eta >= .97 ||
    (sourceIntegration === 'strangFixedState' && chemistry !== 'table')) throw new Error('Invalid bounded cfdParity controls');
const states = Array.from({ length: cells }, (_, i) => table.lookup(0.2 + 0.005 * Math.sin(2 * Math.PI * (i + 0.5) / cells), eta));
const low = Math.max(...thermo.species.map(s => s.effectiveMinimumTemperature_K)), high = Math.min(...thermo.species.map(s => s.effectiveMaximumTemperature_K));
if (states.some(s => s.temperature <= low || s.temperature >= high || s.y.some(y => y < 0))) throw new Error('Initial physical states outside thermo coverage');
const plan = { schema: 'fgm-unused-diffusion-cfd-pair-v1', cells, deltaT, endTime, startTime: 0,
  pressure_Pa: table.receipt.case.pressure_pa, velocity_m_s: 1, eta,
  initialMixtureFraction: '0.2 + 0.005*sin(2*pi*(i+0.5)/48)', inputHashes: table.inputHashes,
  thermoDictionarySha256: digest(dictionary), chemistry, sourceIntegration,
  caloricClosureRequired: chemistry === 'table',
  relativeTolerance: 1e-12, scientificAcceptance: false, cases: ['baseline', 'optimized'] };
if (!apply) { console.log(JSON.stringify({ dryRun: true, ...plan }, null, 2)); process.exit(0); }
if (!process.env.SLURM_JOB_ID) throw new Error('CFD case preparation requires allocated qualification');
const root = `${m.out}/cfd`; await mkdir(root);
const here = dirname(fileURLToPath(import.meta.url));
const header = (object, cls = 'dictionary') => `FoamFile { version 2.0; format ascii; class ${cls}; object "${object}"; }\n`;
const boundaries = 'boundaryField { left { type cyclic; } right { type cyclic; } transverse { type empty; } }\n';
const inputs = {};
for (const mode of plan.cases) {
  const out = `${root}/${mode}`;
  const result = spawnSync(process.execPath, [resolve(here, '../../fgm-of8/direct-verification/prepare.mjs'),
    '--kind', 'contact', '--cells', String(cells), '--delta-t', String(deltaT), '--out', out], { encoding: 'utf8' });
  if (result.status !== 0) throw new Error(result.stderr || result.stdout || 'Base periodic mesh preparation failed');
  async function scalar(name, dimensions, values) {
    const internal = Array.isArray(values) ? `nonuniform List<scalar>\n${values.length}\n(\n${values.join('\n')}\n)` : `uniform ${values}`;
    await writeFile(`${out}/0/${name}`, header(name, 'volScalarField') + `dimensions [${dimensions}]; internalField ${internal};\n${boundaries}`);
  }
  for (let i = 0; i < names.length; ++i) await scalar(names[i], '0 0 0 0 0 0 0', states.map(s => s.y[i]));
  for (const [name, dimensions, values] of [
    ['Z', '0 0 0 0 0 0 0', states.map(s => s.z)], ['c', '0 0 0 0 0 0 0', states.map(s => s.c)],
    ['T', '0 0 0 1 0 0 0', states.map(s => s.temperature)], ['p', '1 -1 -2 0 0 0 0', plan.pressure_Pa], ['Ha', '0 2 -2 0 0 0 0', 0],
  ]) await scalar(name, dimensions, values);
  await writeFile(`${out}/constant/thermophysicalProperties`, dictionary);
  await writeFile(`${out}/constant/constant.tbl`, table.raw);
  await writeFile(`${out}/constant/thermophysicalTransport`, header('thermophysicalTransport') + 'laminar { model Fourier; }\n');
  let control = await readFile(`${out}/system/controlDict`, 'utf8');
  control = control.replace(/endTime [^;]+;/, `endTime ${endTime};`).replace(/writeInterval [^;]+;/, 'writeInterval 5;')
    .replace('fgmEnergyForm sensibleEnthalpy;', 'fgmEnergyForm absoluteEnthalpy;');
  control += `fgmSkipUnusedDimix ${mode === 'optimized' ? 'yes' : 'no'}; fgmProgressSourceEnabled ${chemistry === 'table' ? 'yes' : 'no'}; fgmRequireHaInitialization yes;\n`;
  control += `fgmSourceIntegration ${sourceIntegration};\n`;
  if (chemistry === 'table') control += 'writeFgmThermoClosure yes; fgmThermoClosureRelativeLimit 1e-8;\n';
  await writeFile(`${out}/system/controlDict`, control);
  const solution = await readFile(`${out}/system/fvSolution`, 'utf8');
  await writeFile(`${out}/system/fvSolution`, solution.replace('pRef 101325;', `pRef ${plan.pressure_Pa};`));
  const hashes = {};
  for (const file of [...names.map(n => `0/${n}`), ...['p', 'T', 'U', 'Ha', 'Z', 'c'].map(n => `0/${n}`),
    'constant/thermophysicalProperties', 'constant/constant.tbl', 'system/fvSchemes', 'system/fvSolution']) hashes[file] = digest(await readFile(`${out}/${file}`));
  inputs[mode] = hashes;
  await writeFile(`${out}/verification-input.json`, JSON.stringify({ ...plan, mode, qualification: 'Parity diagnostic only; no synthetic analytical chemistry expectation.' }, null, 2) + '\n');
}
if (JSON.stringify(inputs.baseline) !== JSON.stringify(inputs.optimized)) throw new Error('Prepared CFD inputs differ');
await writeFile(`${root}/manifest.json`, JSON.stringify({ ...plan, inputs, fields: ['T', 'p', 'rho', 'h', 'Ha', 'Z', 'c', ...names] }, null, 2) + '\n');
console.log(JSON.stringify({ created: root, ...plan }, null, 2));
