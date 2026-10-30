import { readFile, writeFile, readdir } from 'node:fs/promises';
import { resolve } from 'node:path';
import { scalarValues, differenceSummary, inletAndMassAudit, averagingAudit } from './diagnostics.mjs';

const [directory] = process.argv.slice(2);
if (!directory) throw new Error('Usage: check.mjs RECONSTRUCTED_CASE');
const root = resolve(directory);
const manifest = JSON.parse(await readFile(`${root}/direct-g2-input.json`, 'utf8'));
const log = await readFile(`${root}/log.solver`, 'utf8');
function records(prefix) {
  return log.split(/\r?\n/).filter(line => line.startsWith(prefix)).map(line => {
    const values = {};
    for (const pair of line.slice(prefix.length).trim().split(/\s+/)) {
      const [key, value] = pair.split('=');
      if (key && value !== undefined) values[key] = Number(value);
    }
    return values;
  });
}
const states = records('energyState '), equations = records('energyEquation '), bounds = records('fgmBounds ');
const source = records('fgmAppliedSource ');
const times = (await readdir(root)).filter(name => /^\d+(?:\.\d*)?(?:e[-+]?\d+)?$/i.test(name))
  .map(name => ({ name, time: Number(name) })).filter(row => row.time > 0).sort((a, b) => a.time - b.time);
const latest = times.at(-1);
const finite = rows => rows.length > 0 && rows.every(row => Object.values(row).every(Number.isFinite));
const fieldValues = {};
async function fieldSummary(name) {
  const raw = await readFile(`${root}/${latest.name}/${name}`, 'utf8');
  const values = scalarValues(raw, name);
  if (['T', 'fgmTdiag'].includes(name)) fieldValues[name] = values;
  let min = Infinity, max = -Infinity, sum = 0;
  for (const value of values) { min = Math.min(min, value); max = Math.max(max, value); sum += value; }
  return { min, max, cellArithmeticMean: sum / values.length, finite: values.every(Number.isFinite), count: values.length };
}
const fields = {};
if (latest) for (const name of ['T', 'p', 'rho', 'Z', 'c', 'Ha', 'CH4', 'O2', 'CO2', 'CO', 'OH', 'fgmTdiag']) fields[name] = await fieldSummary(name);
const mechanicalChecks = {
  cleanTimeZero: states[0]?.t === 0 && manifest.startTime === 0,
  reachedEndTime: Math.abs((states.at(-1)?.t ?? -1) - manifest.endTime) <= Math.max(1e-14, manifest.endTime * 1e-8),
  wroteEndTime: latest && Math.abs(latest.time - manifest.endTime) <= Math.max(1e-14, manifest.endTime * 1e-8),
  terminatedNormally: /\nEnd\s*(?:\n|$)/.test(log) && !/FOAM FATAL|Floating point exception/.test(log),
  finiteEnergyRecords: finite(states) && finite(equations),
  finiteFinalFields: Object.keys(fields).length === 12 && Object.values(fields).every(row => row.finite),
  positiveThermo: fields.T?.min > 0 && fields.p?.min > 0 && fields.rho?.min > 0,
};
if (manifest.chemistry) mechanicalChecks.declaredSourceMode = source.length > 0 && source.every(row =>
  Number.isFinite(row.tabulatedKg_s) && Number.isFinite(row.appliedKg_s) &&
  row.enabled === (manifest.chemistry === 'table' ? 1 : 0) &&
  (manifest.chemistry !== 'disabled' || row.appliedKg_s === 0));
const corrections = bounds.at(-1)?.cumulativeCorrections ?? null;
const temperatureDeparture = latest && fields.T.finite && fields.fgmTdiag.finite
  ? { units: 'K', definition: 'executing thermo T minus table diagnostic T',
    ...differenceSummary(fieldValues.T, fieldValues.fgmTdiag),
    interpretation: 'Measures departure from the two-coordinate manifold; no enthalpy-coordinate correction or acceptance threshold is implied.' }
  : null;
const report = { schema: 'forge-direct-warm-g2-diagnostic-v1', inputHashes: manifest.inputHashes,
  time: latest?.time ?? null, mechanicalChecks, fields, initialEnergy: states[0] ?? null,
  finalEnergy: states.at(-1) ?? null, finalEquation: equations.at(-1) ?? null,
  lookupBounds: bounds.at(-1) ?? null,
  temperatureDepartureFromTable: temperatureDeparture,
  boundaryMass: await inletAndMassAudit(root, manifest, states),
  averaging: latest ? await averagingAudit(root, latest.name, manifest.observations, manifest.ranks) : null,
  scientificLimitations: manifest.approximations,
  pressureDepartureFromTable: fields.p ? Math.max(Math.abs(fields.p.min / manifest.pressure - 1), Math.abs(fields.p.max / manifest.pressure - 1)) : null,
  clippedLookup: corrections === null ? null : corrections > 0,
  chemistry: manifest.chemistry ?? 'table', lastAppliedSource: source.at(-1) ?? null,
  thermodynamics: manifest.thermodynamics ?? {mode:'warm-ideal'},
  coldInitialization: manifest.thermodynamics?.mode === 'cold-real-fluid'
    ? JSON.parse(await readFile(`${root}/cold-initialization.json`, 'utf8')) : null,
  status: Object.values(mechanicalChecks).every(Boolean) ? 'diagnostic-run-completed' : 'diagnostic-run-incomplete-or-failed',
  physicalValidationPassed: false, independentScienceApproval: false,
  interpretation: 'Completion and finite fields are execution evidence only. Inspect source signs, clipping, energy fluxes and profiles before accepting any physical claim.' };
await writeFile(`${root}/direct-g2-result.json`, JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report, null, 2));
if (!Object.values(mechanicalChecks).every(Boolean)) process.exitCode = 2;
