import { readFile, writeFile, readdir } from 'node:fs/promises';
import { resolve } from 'node:path';

const [directory, logPath] = process.argv.slice(2);
if (!directory || !logPath) throw new Error('Usage: check.mjs CASE SOLVER_LOG');
const root = resolve(directory);
const input = JSON.parse(await readFile(`${root}/source-split-input.json`, 'utf8'));
if (input.schema !== 'fgm-source-split-case-v1') throw new Error('Wrong input schema');
const log = await readFile(logPath, 'utf8'), checks = [], failures = [];
const add = (name, value, limit) => checks.push({ name, measured: value, limit,
  pass: Number.isFinite(value) && value <= limit });
function rows(label) {
  return log.split(/\r?\n/).filter(line => line.startsWith(`${label} `)).map(line =>
    Object.fromEntries([...line.matchAll(/(\w+)=([^\s]+)/g)].map(([, key, value]) =>
      [key, Number.isFinite(Number(value)) ? Number(value) : value])));
}
const energy = rows('energyState'), equations = rows('energyEquation');
const history = rows('fgmSourceOldTime'), stages = rows('fgmSourceStage');
const bounds = rows('fgmBounds'), audit = rows('energyResidualAudit');
const profiles = [], times = (await readdir(root)).filter(name => Number.isFinite(Number(name)) && Number(name) > 0)
  .sort((a, b) => Number(a) - Number(b));
async function field(time, name) {
  const text = (await readFile(`${root}/${time}/${name}`, 'utf8'))
    .replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/[^\n]*/g, '');
  const uniform = text.match(/internalField\s+uniform\s+([^;]+);/);
  const nonuniform = text.match(/internalField\s+nonuniform\s+List<scalar>\s+(\d+)\s*\(([^]*?)\)\s*;/);
  const values = uniform ? Array(input.cells).fill(Number(uniform[1]))
    : nonuniform ? nonuniform[2].trim().split(/\s+/).map(Number) : [];
  if (values.length !== input.cells || values.some(x => !Number.isFinite(x))) throw new Error(`Invalid ${time}/${name}`);
  return values;
}
try {
  for (const time of times) {
    const values = {};
    for (const name of ['c', 'Z', 'T', 'p', 'Ha', 'rho']) values[name] = await field(time, name);
    for (let cell = 0; cell < input.cells; cell++) profiles.push({ t: Number(time), cell,
      x: input.length*(cell+.5)/input.cells, ...Object.fromEntries(Object.entries(values).map(([k, v]) => [k, v[cell]])) });
  }
} catch (error) { failures.push(error.message); }
const steps = Math.round(input.endTime/input.dt), first = energy[0], last = energy.at(-1);
add('missing_energy_records', Math.abs(energy.length-(steps+1)), 0);
add('complete_written_steps', Math.abs(times.length-steps), 0);
add('field_read_failures', failures.length, 0);
add('finite_energy_records', energy.some(r => Object.values(r).some(v => typeof v !== 'number')) ? 1 : 0, 0);
add('solver_completed', /\nEnd\s*\n/.test(log) ? 0 : 1, 0);
add('positive_thermodynamic_fields', profiles.some(r => !(r.T > 0 && r.p > 0 && r.rho > 0)) ? 1 : 0, 0);
add('progress_coverage', profiles.some(r => r.c < input.states[r.cell].cMin || r.c > input.states[r.cell].cMax) ? 1 : 0, 0);
if (first && last) {
  add('time_zero', Math.abs(first.t), 1e-15);
  add('end_time', Math.abs(last.t-input.endTime), input.dt*1e-5);
  add('mass_relative_drift', Math.max(...energy.map(r => Math.abs(r.mass-first.mass)/Math.abs(first.mass))), input.thresholds.massRelative);
  add('energy_per_chemical_change', Math.abs(last.E-first.E)/Math.max(Math.abs(last.Hchemical-first.Hchemical), 1e-12), input.thresholds.energyPerChemicalChange);
  add('physical_progress_changed', Math.abs(last.cmean-first.cmean) > 1e-12 ? 0 : 1, 0);
}
add('energy_equations_present', equations.length ? 0 : 1, 0);
add('energy_equation_relative_residual', Math.max(...equations.map(r => Math.abs(r.residualL1W)/Math.max(1,
  ...['ddtW', 'convectionW', 'diffusionW', 'kineticW', 'pressureW', 'sourceW'].map(k => Math.abs(r[k]))))), input.thresholds.equationResidualRelative);
add('no_extra_chemical_energy_source', Math.max(...equations.map(r => Math.abs(r.sourceW))), input.thresholds.sourceEnergyW);
add('residual_audit_count', Math.abs(audit.length-equations.length), 0);
add('lookup_records_present', bounds.length ? 0 : 1, 0);
add('lookup_clipping', Math.max(...bounds.map(r => r.cumulativeCorrections)), input.thresholds.lookupCorrections);
if (input.integration === 'strangFixedState') {
  add('first_stage_once_per_step', Math.abs(stages.filter(s => s.stage === 'firstHalf').length-steps), 0);
  add('second_stage_each_outer', Math.abs(stages.filter(s => s.stage === 'secondHalf').length-steps*input.outer), 0);
  add('old_time_audit_each_outer', Math.abs(history.length-steps*input.outer), 0);
  add('old_time_immutable', Math.max(...history.flatMap(r => [Math.abs(r.deltaC), Math.abs(r.deltaZ), Math.abs(r.deltaRho)])), input.thresholds.oldTimeAbsolute);
  add('half_stage_duration', Math.max(...stages.map(r => Math.abs(r.duration-.5*input.dt))), input.dt*1e-12);
  const expected = Array.from({ length: steps }, (_, i) => (i+1)*input.dt);
  add('stage_time_or_outer_errors', expected.reduce((total, t) => {
    const at = r => Math.abs(r.t-t) <= input.dt*1e-5;
    const h = history.filter(at);
    return total + (stages.filter(r => at(r) && r.stage === 'firstHalf').length !== 1 ? 1 : 0)
      + (stages.filter(r => at(r) && r.stage === 'secondHalf').length !== input.outer ? 1 : 0)
      + (JSON.stringify(h.map(r => r.outer)) !== JSON.stringify(Array.from({ length: input.outer }, (_, i) => i+1)) ? 1 : 0);
  }, 0), 0);
}
const execution = [...log.matchAll(/ExecutionTime = ([\d.e+-]+) s\s+ClockTime = ([\d.e+-]+) s/g)].at(-1);
const result = { schema: 'fgm-source-split-result-v1', input, status: checks.every(x => x.pass) ? 'pass' : 'fail',
  checks, failures, initial: first ?? null, final: last ?? null, energy,
  runtime: execution ? { cpuSeconds: Number(execution[1]), wallSeconds: Number(execution[2]) } : null,
  finalProfile: profiles.filter(p => Math.abs(p.t-input.endTime) <= input.dt*1e-5),
  qualification: 'bounded ideal-thermo CFD using cold-inlet physical table; not SRK/PR or paper agreement',
  scientificAcceptance: false };
await writeFile(`${root}/source-split-result.json`, JSON.stringify(result, null, 2)+'\n');
const columns = ['t', 'cell', 'x', 'c', 'Z', 'T', 'p', 'Ha', 'rho'];
await writeFile(`${root}/source-split-profiles.csv`, [columns.join(','), ...profiles.map(r => columns.map(k => r[k]).join(','))].join('\n')+'\n');
console.log(JSON.stringify({ status: result.status, checks, failures }));
process.exitCode = result.status === 'pass' ? 0 : 1;
