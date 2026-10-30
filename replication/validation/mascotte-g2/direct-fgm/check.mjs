import { readFile, writeFile, readdir } from 'node:fs/promises';
import { resolve } from 'node:path';

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
const times = (await readdir(root)).filter(name => /^\d+(?:\.\d*)?(?:e[-+]?\d+)?$/i.test(name))
  .map(name => ({ name, time: Number(name) })).filter(row => row.time > 0).sort((a, b) => a.time - b.time);
const latest = times.at(-1);
const finite = rows => rows.length > 0 && rows.every(row => Object.values(row).every(Number.isFinite));
async function fieldSummary(name) {
  const raw = await readFile(`${root}/${latest.name}/${name}`, 'utf8');
  const uniform = /internalField\s+uniform\s+([^;]+);/.exec(raw);
  let values;
  if (uniform) values = [Number(uniform[1])];
  else {
    const list = /internalField\s+nonuniform\s+List<scalar>\s+(\d+)\s*\(([\s\S]*?)\)\s*;/.exec(raw);
    if (!list) throw new Error(`Cannot parse ASCII scalar internal field ${name}`);
    values = list[2].trim().split(/\s+/).map(Number);
    if (values.length !== Number(list[1])) throw new Error(`Count mismatch in ${name}`);
  }
  let min = Infinity, max = -Infinity, sum = 0;
  for (const value of values) { min = Math.min(min, value); max = Math.max(max, value); sum += value; }
  return { min, max, cellArithmeticMean: sum / values.length, finite: values.every(Number.isFinite), count: values.length };
}
const fields = {};
if (latest) for (const name of ['T', 'p', 'rho', 'Z', 'c', 'Ha', 'CH4', 'O2', 'CO2', 'CO', 'OH']) fields[name] = await fieldSummary(name);
const mechanicalChecks = {
  cleanTimeZero: states[0]?.t === 0 && manifest.startTime === 0,
  reachedEndTime: Math.abs((states.at(-1)?.t ?? -1) - manifest.endTime) <= Math.max(1e-14, manifest.endTime * 1e-8),
  wroteEndTime: latest && Math.abs(latest.time - manifest.endTime) <= Math.max(1e-14, manifest.endTime * 1e-8),
  terminatedNormally: /\nEnd\s*(?:\n|$)/.test(log) && !/FOAM FATAL|Floating point exception/.test(log),
  finiteEnergyRecords: finite(states) && finite(equations),
  finiteFinalFields: Object.keys(fields).length === 11 && Object.values(fields).every(row => row.finite),
  positiveThermo: fields.T?.min > 0 && fields.p?.min > 0 && fields.rho?.min > 0,
};
const corrections = bounds.at(-1)?.cumulativeCorrections ?? null;
const report = { schema: 'forge-direct-warm-g2-diagnostic-v1', inputHashes: manifest.inputHashes,
  time: latest?.time ?? null, mechanicalChecks, fields, initialEnergy: states[0] ?? null,
  finalEnergy: states.at(-1) ?? null, finalEquation: equations.at(-1) ?? null,
  lookupBounds: bounds.at(-1) ?? null,
  scientificLimitations: manifest.approximations,
  pressureDepartureFromTable: fields.p ? Math.max(Math.abs(fields.p.min / manifest.pressure - 1), Math.abs(fields.p.max / manifest.pressure - 1)) : null,
  clippedLookup: corrections === null ? null : corrections > 0,
  status: Object.values(mechanicalChecks).every(Boolean) ? 'diagnostic-run-completed' : 'diagnostic-run-incomplete-or-failed',
  physicalValidationPassed: false, independentScienceApproval: false,
  interpretation: 'Completion and finite fields are execution evidence only. Inspect source signs, clipping, energy fluxes and profiles before accepting any physical claim.' };
await writeFile(`${root}/direct-g2-result.json`, JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report, null, 2));
if (!Object.values(mechanicalChecks).every(Boolean)) process.exitCode = 2;
