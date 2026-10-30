import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
const [output, ...paths] = process.argv.slice(2);
if (!output || !paths.length) throw new Error('Usage: compare.mjs OUTPUT_JSON CASE...');
const cases = [], failures = [], comparisons = [];
for (const path of paths) {
  try { cases.push({ path, ...JSON.parse(await readFile(`${path}/source-split-result.json`, 'utf8')) }); }
  catch (error) { failures.push({ path, error: error.message }); }
}
function compare(kind, name, leftDt, leftOuter, rightDt, rightOuter, threshold) {
  const find = (dt, outer) => cases.filter(r => r.input.kind === kind && r.input.dt === dt
    && r.input.outer === outer && r.input.integration === 'strangFixedState');
  const left = find(leftDt, leftOuter), right = find(rightDt, rightOuter);
  if (left.length !== 1 || right.length !== 1) { failures.push({ kind, name, error: 'Missing or duplicate required case' }); return; }
  const a = left[0], b = right[0], n = a.input.cells;
  if (a.finalProfile.length !== n || b.finalProfile.length !== n ||
      JSON.stringify(a.input.inputHashes) !== JSON.stringify(b.input.inputHashes)) {
    failures.push({ kind, name, error: 'Incomplete final fields or differing input identity' }); return;
  }
  const rms = field => Math.sqrt(a.finalProfile.reduce((s, r, i) => s+(r[field]-b.finalProfile[i][field])**2, 0)/n);
  const cspanRms = Math.sqrt(a.finalProfile.reduce((s, r, i) =>
    s+((r.c-b.finalProfile[i].c)/(a.input.states[i].cMax-a.input.states[i].cMin))**2, 0)/n);
  comparisons.push({ kind, name, left: a.path, right: b.path, cspanRms,
    temperatureRms_K: rms('T'), densityRms_kg_m3: rms('rho'), absoluteEnthalpyRms_J_kg: rms('Ha'),
    threshold: a.input.thresholds[threshold], pass: a.status === 'pass' && b.status === 'pass' && cspanRms <= a.input.thresholds[threshold] });
}
for (const kind of ['0d', '1d']) {
  for (const outer of [1, 2, 3]) compare(kind, `dt-outer${outer}`, 25e-9, outer, 50e-9, outer, 'timestepCspanRms');
  for (const dt of [25e-9, 50e-9]) for (const outer of [1, 2])
    compare(kind, `outer${outer}-vs3-dt${dt}`, dt, outer, dt, 3, 'outerCspanRms');
}
const result = { schema: 'fgm-source-split-comparison-v1', failures, comparisons,
  cases: cases.map(r => ({ path: r.path, kind: r.input.kind, dt: r.input.dt, outer: r.input.outer,
    integration: r.input.integration, status: r.status, runtime: r.runtime, checks: r.checks })),
  status: failures.length === 0 && comparisons.length === 14 && comparisons.every(r => r.pass) ? 'pass' : 'fail',
  scientificAcceptance: false, note: 'Euler transport and density/pressure coupling; no second-order accuracy claim' };
await writeFile(resolve(output), JSON.stringify(result, null, 2)+'\n');
console.log(JSON.stringify({ status: result.status, comparisons: comparisons.length, failures }));
process.exitCode = result.status === 'pass' ? 0 : 1;
