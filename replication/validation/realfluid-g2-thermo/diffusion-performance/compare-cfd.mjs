import { readFile, writeFile, readdir } from 'node:fs/promises';
import { resolve } from 'node:path';
import { scalarValues } from '../../mascotte-g2/direct-fgm/diagnostics.mjs';
import { digest } from '../../fgm-of8/direct-verification/physical-input.mjs';
const root = resolve(process.argv[2] ?? '');
if (process.argv.length !== 3) throw new Error('Use compare-cfd.mjs CFD_PAIR_DIR');
const m = JSON.parse(await readFile(`${root}/manifest.json`));
if (m.schema !== 'fgm-unused-diffusion-cfd-pair-v1') throw new Error('Wrong CFD pair manifest');
const relativeError = (a, b) => Math.abs(a - b) / Math.max(1, Math.abs(a));
const records = (log, label) => log.split(/\r?\n/).filter(s => s.startsWith(label + ' ')).map(line => {
  const row = Object.fromEntries([...line.matchAll(/(\w+)=([^\s]+)/g)].map(([, key, value]) => [key, Number(value)]));
  if (!Object.values(row).every(Number.isFinite)) throw new Error(`Nonfinite ${label}`);
  return row;
});
function vector(raw) {
  const uniform = /internalField\s+uniform\s+\(([^)]+)\)\s*;/.exec(raw);
  const nonuniform = /internalField\s+nonuniform\s+List<vector>\s+(\d+)\s*\(([\s\S]*?)\)\s*;/.exec(raw);
  if (uniform) return uniform[1].trim().split(/\s+/).map(Number);
  if (!nonuniform) throw new Error('Unsupported vector field');
  const values = [...nonuniform[2].matchAll(/\(([^)]+)\)/g)].flatMap(match => match[1].trim().split(/\s+/).map(Number));
  if (values.length !== Number(nonuniform[1]) * 3) throw new Error('Vector count mismatch');
  return values;
}
const failures = [], measurements = [], runs = {};
for (const mode of m.cases) {
  const path = `${root}/${mode}`, log = await readFile(`${path}/log.solver`, 'utf8');
  if (!/\nEnd\s*(?:\n|$)/.test(log) || /FOAM FATAL|Floating point exception/.test(log)) failures.push(`${mode}: abnormal solver termination`);
  for (const [file, expected] of Object.entries(m.inputs[mode])) {
    if (file !== '0/Ha' && digest(await readFile(`${path}/${file}`)) !== expected) throw new Error(`Changed input ${mode}/${file}`);
  }
  const states = records(log, 'energyState'), bounds = records(log, 'fgmBounds'), source = records(log, 'fgmAppliedSource');
  if (states.length < 2 || states[0].t !== 0 || Math.abs(states.at(-1).t - m.endTime) > 1e-16) failures.push(`${mode}: time-zero/end-time mismatch`);
  if (!bounds.length || bounds.some(r => r.cumulativeCorrections !== 0)) failures.push(`${mode}: missing bounds or clipped lookup`);
  if (!source.length || source.some(r => r.enabled !== 0 || r.appliedKg_s !== 0)) failures.push(`${mode}: progress source not disabled`);
  const times = (await readdir(path)).filter(n => Number.isFinite(Number(n)) && Number(n) > 0).sort((a, b) => Number(a) - Number(b));
  if (times.length !== 4 || Math.abs(Number(times.at(-1)) - m.endTime) > 1e-16) failures.push(`${mode}: expected four written times absent`);
  const clocks = [...log.matchAll(/ClockTime = ([0-9.eE+-]+) s/g)].map(match => Number(match[1]));
  runs[mode] = { states, bounds, source, times, solverReportedWall_s: clocks.at(-1) ?? null,
    advancingStepWall_s: clocks.length > 1 ? clocks.at(-1) - clocks[0] : null,
    massRelativeDrift: Math.max(...states.map(r => Math.abs(r.mass / states[0].mass - 1))),
    energyRelativeDrift: Math.max(...states.map(r => relativeError(states[0].E, r.E))),
    initialHaSha256: digest(await readFile(`${path}/0/Ha`)) };
}
if (JSON.stringify(runs.baseline.times) !== JSON.stringify(runs.optimized.times)) throw new Error('Written times differ');
if (runs.baseline.initialHaSha256 !== runs.optimized.initialHaSha256) failures.push('Full-SRK initialized Ha fields differ');
for (const time of runs.baseline.times) for (const field of [...m.fields, 'U']) {
  const leftRaw = await readFile(`${root}/baseline/${time}/${field}`), rightRaw = await readFile(`${root}/optimized/${time}/${field}`);
  const left = field === 'U' ? vector(leftRaw.toString()) : scalarValues(leftRaw.toString(), field);
  const right = field === 'U' ? vector(rightRaw.toString()) : scalarValues(rightRaw.toString(), field);
  const uniformCount = field === 'U' ? 3 : 1, count = m.cells * uniformCount;
  if ([left, right].some(v => ![uniformCount, count].includes(v.length) || !v.every(Number.isFinite))) throw new Error(`Invalid field ${time}/${field}`);
  let maximumRelative = 0;
  for (let i = 0; i < count; ++i) maximumRelative = Math.max(maximumRelative,
    relativeError(left[left.length === uniformCount ? i % uniformCount : i], right[right.length === uniformCount ? i % uniformCount : i]));
  if (maximumRelative > m.relativeTolerance) failures.push(`${time}/${field}: parity`);
  if (['T', 'p', 'rho'].includes(field) && [left, right].some(v => Math.min(...v) <= 0)) failures.push(`${time}/${field}: nonpositive thermo`);
  measurements.push({ time: Number(time), field, maximumRelative, leftSha256: digest(leftRaw), rightSha256: digest(rightRaw) });
}
for (const key of ['states', 'bounds', 'source']) {
  const a = runs.baseline[key], b = runs.optimized[key];
  if (a.length !== b.length) throw new Error(`Record count differs: ${key}`);
  let maximumRelative = 0;
  for (let i = 0; i < a.length; ++i) {
    if (JSON.stringify(Object.keys(a[i])) !== JSON.stringify(Object.keys(b[i]))) throw new Error('Record keys differ');
    for (const field of Object.keys(a[i])) maximumRelative = Math.max(maximumRelative, relativeError(a[i][field], b[i][field]));
  }
  if (maximumRelative > m.relativeTolerance) failures.push(`Integrated ${key} parity`);
  measurements.push({ records: key, maximumRelative });
}
const summary = mode => ({ ...runs[mode], states: { initial: runs[mode].states[0], final: runs[mode].states.at(-1) },
  bounds: runs[mode].bounds.at(-1), source: runs[mode].source.at(-1) });
const receipt = { schema: 'fgm-unused-diffusion-cfd-parity-v1', passed: !failures.length, failures, measurements,
  baseline: summary('baseline'), optimized: summary('optimized'), relativeTolerance: m.relativeTolerance,
  scientificAcceptance: false, qualification: 'Equivalence of fresh source-disabled physical-table transport diagnostics only' };
await writeFile(`${root}/cfd-parity-result.json`, JSON.stringify(receipt, null, 2) + '\n');
console.log(JSON.stringify(receipt, null, 2));
if (!receipt.passed) process.exitCode = 1;
