import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { digest } from '../../fgm-of8/direct-verification/physical-input.mjs';

const directory = resolve(process.argv[2] ?? '');
if (process.argv.length !== 3) throw new Error('Use compare.mjs PAIRS_DIR');
const manifest = JSON.parse(await readFile(`${directory}/manifest.json`, 'utf8'));
if (manifest.schema !== 'fgm-unused-diffusion-parity-v1') throw new Error('Unexpected qualification manifest');
const csv = raw => {
  const [header, ...lines] = raw.trim().split(/\r?\n/), columns = header.split(',');
  const rows = lines.map(line => {
    const values = line.split(',').map(Number);
    if (values.length !== columns.length || values.some(v => !Number.isFinite(v))) throw new Error('Invalid numeric CSV');
    return Object.fromEntries(columns.map((key, i) => [key, values[i]]));
  });
  if (!rows.length) throw new Error('Empty numeric CSV');
  return rows;
};
const results = [], failures = [];
for (const sample of manifest.samples) {
  const pair = manifest.pairs.filter(row => row.sample === sample.name);
  if (pair.length !== 2) throw new Error('Incomplete paired input');
  const base = pair.find(row => row.mode === 'baseline'), optimized = pair.find(row => row.mode === 'optimized');
  if (JSON.stringify(base.initialHashes) !== JSON.stringify(optimized.initialHashes)) throw new Error('Pair input mismatch');
  for (const item of pair) for (const [file, expected] of Object.entries(item.initialHashes))
    if (digest(await readFile(`${directory}/${item.case}/${file}`)) !== expected) throw new Error(`Modified initial input: ${item.case}/${file}`);
  let maximumRelative = 0;
  const outputs = {};
  for (const file of ['cold-properties.csv', 'cold-inversion.csv']) {
    const aRaw = await readFile(`${directory}/${base.case}/${file}`), bRaw = await readFile(`${directory}/${optimized.case}/${file}`);
    const a = csv(aRaw.toString()), b = csv(bRaw.toString());
    if (a.length !== b.length || JSON.stringify(Object.keys(a[0])) !== JSON.stringify(Object.keys(b[0]))) throw new Error('Output dimensions differ');
    for (let i = 0; i < a.length; ++i) for (const key of Object.keys(a[i])) {
      const relative = Math.abs(a[i][key] - b[i][key]) / Math.max(1, Math.abs(a[i][key]));
      maximumRelative = Math.max(maximumRelative, relative);
      if (relative > manifest.numericalTolerance) failures.push(`${sample.name}/${file}/${i}/${key}`);
      if (key === 'error_K' && Math.max(Math.abs(a[i][key]), Math.abs(b[i][key])) > manifest.inversionTolerance_K)
        failures.push(`${sample.name}/enthalpy-inversion`);
    }
    outputs[file] = { baseline: digest(aRaw), optimized: digest(bRaw) };
  }
  const log = await readFile(`${directory}/${optimized.case}/log.probe`, 'utf8');
  if (!log.includes('FGM_DIMIX_POLICY calculation=suppressed access=forbidden')) throw new Error('Candidate policy execution marker absent');
  const timingA = csv(await readFile(`${directory}/${base.case}/thermo-correction-timing.csv`, 'utf8'))[0];
  const timingB = csv(await readFile(`${directory}/${optimized.case}/thermo-correction-timing.csv`, 'utf8'))[0];
  if (timingA.cells !== manifest.cells || timingB.cells !== manifest.cells || timingA.corrections !== manifest.timingCorrections ||
      timingB.corrections !== manifest.timingCorrections || timingA.wall_s <= 0 || timingB.wall_s <= 0) throw new Error('Timing inputs differ');
  results.push({ sample: sample.name, maximumRelative, baselineWall_s: timingA.wall_s,
    optimizedWall_s: timingB.wall_s, measuredCorrectionSpeedup: timingA.wall_s / timingB.wall_s, outputs });
}
const result = { schema: 'fgm-unused-diffusion-parity-result-v1', passed: failures.length === 0,
  numericalTolerance: manifest.numericalTolerance, results, failures,
  scientificAcceptance: false, cfdParityQualified: false, negativeControlsQualified: false };
await writeFile(`${directory}/parity-result.json`, JSON.stringify(result, null, 2) + '\n');
console.log(JSON.stringify(result, null, 2));
if (!result.passed) process.exitCode = 1;
