import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { loadPhysicalTable, digest } from '../../fgm-of8/direct-verification/physical-input.mjs';

const options = {}, args = process.argv.slice(2);
for (let i = 0; i < args.length; i += 2) {
  if (!['--table-dir', '--metadata', '--thermo-dir', '--out'].includes(args[i]) || !args[i + 1])
    throw new Error('Use --table-dir DIR --metadata FILE --thermo-dir SRK [--out NEW_DIR]');
  options[args[i].slice(2)] = resolve(args[i + 1]);
}
for (const key of ['table-dir', 'metadata', 'thermo-dir']) if (!options[key]) throw new Error(`Missing ${key}`);
const table = await loadPhysicalTable(options['table-dir'], options.metadata);
const thermoRaw = await readFile(`${options['thermo-dir']}/manifest.json`);
const thermo = JSON.parse(thermoRaw);
if (thermo.equationOfState !== 'soaveRedlichKwong' || thermo.mechanism_sha256 !== table.metadata.mechanismSha256)
  throw new Error('Matched full SRK export and physical table required');
const names = table.metadata.species.map(s => s.name);
if (JSON.stringify(thermo.species.map(s => s.name)) !== JSON.stringify(names)) throw new Error('Species order mismatch');
const pressure = table.receipt.case.pressure_pa;
const samples = [
  ['oxygen', 0, 0, 1], ['methane', 1, 0, 1], ['mixed-unburnt', 0.1, 0, 1],
  ['mixed-reacted', 0.2, 0.8, 1], ['mixed-pressure-low', 0.2, 0.8, 0.9],
  ['mixed-pressure-high', 0.2, 0.8, 1.1],
].map(([name, z, eta, pressureFactor]) => ({ name, ...table.lookup(z, eta), pressure_Pa: pressure * pressureFactor }));
const low = Math.max(...thermo.species.map(s => s.effectiveMinimumTemperature_K));
const high = Math.min(...thermo.species.map(s => s.effectiveMaximumTemperature_K));
for (const state of samples) {
  if (!(state.temperature - 0.1 >= low && state.temperature + 0.5 <= high) ||
      state.y.some(y => y < 0) || !(state.pressure_Pa > 0)) throw new Error(`Unqualified state bounds: ${state.name}`);
}
const manifest = { schema: 'fgm-unused-diffusion-parity-v1', samples, cells: 128,
  timingCorrections: 20, inputHashes: table.inputHashes, thermoManifestSha256: digest(thermoRaw),
  numericalTolerance: 1e-12, inversionTolerance_K: 1e-5, scientificAcceptance: false };
if (!options.out) { console.log(JSON.stringify({ dryRun: true, ...manifest }, null, 2)); process.exit(0); }
await mkdir(options.out);
const header = object => `FoamFile { version 2.0; format ascii; class dictionary; object ${object}; }\n`;
const here = dirname(fileURLToPath(import.meta.url));
const pairs = [];
for (const state of samples) {
  for (const mode of ['baseline', 'optimized']) {
    const caseName = `${state.name}-${mode}`, caseDir = `${options.out}/${caseName}`;
    const result = spawnSync(process.execPath, [resolve(here, '../probe/prepare.mjs'),
      '--thermo-dir', options['thermo-dir'], '--species', 'O2', '--cells', String(manifest.cells), '--out', caseDir],
    { encoding: 'utf8' });
    if (result.status !== 0) throw new Error(result.stderr || result.stdout || 'Base probe preparation failed');
    for (const [name, value] of [...names.map((n, i) => [n, state.y[i]]), ['p', state.pressure_Pa], ['T', state.temperature]]) {
      const file = `${caseDir}/0/${name}`, raw = await readFile(file, 'utf8');
      if (!/internalField uniform [^;]+;/.test(raw)) throw new Error(`Unexpected field template ${name}`);
      await writeFile(file, raw.replace(/internalField uniform [^;]+;/, `internalField uniform ${value};`));
    }
    await writeFile(`${caseDir}/constant/probeProperties`, header('probeProperties') +
      `pressure ${state.pressure_Pa}; temperatures (${state.temperature}); increments (-0.1 -0.001 0.001 0.1); initialGuessOffset 0.5; timingCorrections ${manifest.timingCorrections};\n`);
    await writeFile(`${caseDir}/constant/momentumTransport`, header('momentumTransport') + 'simulationType laminar;\n');
    await writeFile(`${caseDir}/constant/thermophysicalTransport`, header('thermophysicalTransport') + 'laminar { model Fourier; }\n');
    await writeFile(`${caseDir}/constant/combustionProperties`, header('combustionProperties') + 'combustionModel fgmTable;\n');
    await writeFile(`${caseDir}/system/controlDict`, (await readFile(`${caseDir}/system/controlDict`, 'utf8')) +
      `fgmEnergyForm absoluteEnthalpy; fgmSkipUnusedDimix ${mode === 'optimized' ? 'yes' : 'no'};\n`);
    const initialHashes = {};
    for (const file of [...names.map(n => `0/${n}`), '0/p', '0/T', '0/Ha', 'constant/thermophysicalProperties', 'constant/probeProperties'])
      initialHashes[file] = digest(await readFile(`${caseDir}/${file}`));
    const record = { schema: 'fgm-unused-diffusion-case-v1', name: caseName, mode, state,
      cells: manifest.cells, timingCorrections: manifest.timingCorrections,
      initialHashes, inputHashes: manifest.inputHashes, thermoManifestSha256: manifest.thermoManifestSha256,
      scientificAcceptance: false, qualification: 'Frozen physical p/T/Y property probe; no flame or CFD integration is performed.' };
    // Replace the base pure-O2 receipt, since the new fields are explicitly mixed.
    await writeFile(`${caseDir}/probe-input.json`, JSON.stringify(record, null, 2) + '\n');
    await writeFile(`${caseDir}/initialization-input.json`, JSON.stringify({ ...record,
      qualification: 'Property-only case; not an authorized Ha initialization input.' }, null, 2) + '\n');
    pairs.push({ sample: state.name, mode, case: caseName, initialHashes });
  }
}
await writeFile(`${options.out}/manifest.json`, JSON.stringify({ ...manifest, pairs }, null, 2) + '\n');
console.log(JSON.stringify({ created: options.out, cases: pairs.length, scientificAcceptance: false }, null, 2));
