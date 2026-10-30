import { readFile, writeFile, readdir } from 'node:fs/promises';
import { resolve } from 'node:path';

const [caseArg, logArg] = process.argv.slice(2);
if (!caseArg || !logArg) throw new Error('Usage: check.mjs CASE SOLVER_LOG');
const caseDir = resolve(caseArg);
const manifest = JSON.parse(await readFile(`${caseDir}/verification-input.json`, 'utf8'));
const log = await readFile(logArg, 'utf8');
function records(label) {
  return log.split(/\r?\n/).filter(line => line.startsWith(label + ' ')).map(line => {
    const row = Object.fromEntries([...line.matchAll(/(\w+)=([^\s]+)/g)]
      .map(([, key, value]) => [key, Number(value)]));
    if (Object.values(row).some(v => !Number.isFinite(v))) throw new Error(`Nonfinite ${label}`);
    return row;
  });
}
const states = records('energyState');
const equations = records('energyEquation');
if (states.length < 2 || !equations.length) throw new Error('Missing actual in-solver energy records');
const initial = states[0];
const final = states.at(-1);
const checks = [];
const add = (name, measured, limit) => checks.push({ name, measured, limit,
  pass: Number.isFinite(measured) && measured <= limit });
const relative = (actual, expected) => Math.abs(actual - expected) / Math.max(Math.abs(expected), 1e-30);
add('initial_time_zero', Math.abs(initial.t), 1e-15);
add('reached_end_time', Math.abs(final.t - manifest.endTime), manifest.deltaT * 1e-5);
add('mass_relative_drift', Math.max(...states.map(r => relative(r.mass, initial.mass))),
  manifest.thresholds.massRelative);
const equationRelative = equations.map(row => Math.abs(row.residualL1W) /
  Math.max(1, ...['ddtW', 'convectionW', 'diffusionW', 'kineticW', 'pressureW', 'sourceW']
    .map(key => Math.abs(row[key]))));
add('assembled_equation_relative_residual', Math.max(...equationRelative),
  manifest.thresholds.equationResidualRelative);
const rho0 = initial.mass / initial.volume;
const analytical = {};
if (manifest.kind === 'heating' || manifest.kind === 'conversion') {
  const cv = manifest.cp - manifest.gasConstant / manifest.molWeight;
  analytical.cv = cv;
  const conversion = manifest.kind === 'conversion';
  const effectiveHeating = conversion ? manifest.progressSource * manifest.chemicalEnergyDrop_J_kg_progress : manifest.heatRelease;
  analytical.temperatureIncrement = effectiveHeating * final.t / (rho0 * cv);
  analytical.energyIncrement = conversion ? 0 : manifest.heatRelease * initial.volume * final.t;
  analytical.progressIncrement = manifest.progressSource * final.t / rho0;
  if (conversion) {
    // Normalize the conserved total energy error by the actual chemical
    // conversion scale, not by a large arbitrary formation-energy offset.
    const scale = effectiveHeating * initial.volume * final.t;
    add('total_energy_error_per_conversion_energy', Math.abs(final.E - initial.E) / scale,
      manifest.thresholds.energyRelative);
    add('no_table_Q_in_absolute_energy_equation', Math.max(...equations.map(r => Math.abs(r.sourceW))), 1e-20);
  } else {
    add('energy_increment_relative_error', relative(final.E - initial.E,
      analytical.energyIncrement), manifest.thresholds.energyRelative);
  }
  add('temperature_increment_relative_error', relative(final.Tmean - initial.Tmean,
    analytical.temperatureIncrement), manifest.thresholds.temperatureIncrementRelative);
  add('progress_source_relative_error', relative(final.cmean - initial.cmean,
    analytical.progressIncrement), manifest.thresholds.progressIncrementRelative);
} else if (manifest.kind === 'physical-conversion') {
  const chemicalChange = Math.abs(final.Hchemical - initial.Hchemical);
  add('total_energy_error_per_chemical_change', Math.abs(final.E - initial.E) / Math.max(chemicalChange, 1e-12),
    manifest.thresholds.energyRelative);
  add('no_table_Q_in_absolute_energy_equation', Math.max(...equations.map(r => Math.abs(r.sourceW))), 1e-20);
  add('pressure_drift_from_fixed_table_pressure', Math.max(...states.map(r =>
    relative(r.pmean, manifest.sourcePressure))), manifest.thresholds.pressureRelative);
  add('physical_progress_changed', Math.abs(final.cmean - initial.cmean) > 1e-12 ? 0 : 1, 0);
  const bounds = records('fgmBounds');
  if (!bounds.length) throw new Error('Missing physical lookup bound records');
  add('no_lookup_clipping', Math.max(...bounds.map(r => r.cumulativeCorrections)), 0);
  analytical.note = 'Actual finite-rate manifold state; conservation test, not a homogeneous kinetics or flame-speed validation';
  analytical.temperatureChange = final.Tmean - initial.Tmean;
  analytical.progressChange = final.cmean - initial.cmean;
  analytical.chemicalEnergyChange = final.Hchemical - initial.Hchemical;
} else {
  const times = (await readdir(caseDir)).filter(name => /^\d+(?:\.\d+)?(?:e[-+]?\d+)?$/i.test(name))
    .sort((a, b) => Number(a) - Number(b));
  const last = times.at(-1);
  add('written_field_at_end_time', Math.abs(Number(last) - manifest.endTime), 1e-12);
  const field = (await readFile(`${caseDir}/${last}/Z`, 'utf8'))
    .replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/[^\n]*/g, '');
  const nonuniform = field.match(/internalField\s+nonuniform\s+List<scalar>\s+(\d+)\s*\(([^]*?)\)\s*;/);
  if (!nonuniform) throw new Error('Missing nonuniform written Z');
  const z = nonuniform[2].trim().split(/\s+/).map(Number);
  if (Number(nonuniform[1]) !== manifest.cells || z.length !== manifest.cells ||
      z.some(v => !Number.isFinite(v))) throw new Error('Invalid written Z length or values');
  const diffusivity = manifest.mu / (manifest.pr * rho0);
  const waveNumber = 2 * Math.PI / manifest.length;
  const amplitude = 0.2 * Math.exp(-diffusivity * waveNumber ** 2 * final.t);
  const expected = z.map((_, i) => 0.5 + amplitude * Math.sin(waveNumber *
    (manifest.length * (i + 0.5) / manifest.cells - manifest.velocity * final.t)));
  analytical.diffusivity = diffusivity;
  analytical.amplitude = amplitude;
  add('Z_continuum_rms_absolute', Math.sqrt(z.reduce((sum, v, i) =>
    sum + (v - expected[i]) ** 2, 0) / z.length), manifest.thresholds.zRmsAbsolute);
  add('Z_mean_drift', Math.abs(z.reduce((a, b) => a + b, 0) / z.length - 0.5), 1e-7);
  analytical.profile = z.map((value, i) => ({ x: manifest.length * (i + 0.5) / manifest.cells,
    computed: value, analytical: expected[i] }));
}
const result = {
  schema: 'forge-direct-of8-verification-result-v1',
  status: checks.every(c => c.pass) ? 'pass' : 'fail',
  qualification: 'numerical verification only; not independent review or scientific acceptance',
  kind: manifest.kind, input: manifest, initial, final, stateCount: states.length,
  equationCount: equations.length, analytical, checks,
};
await writeFile(`${caseDir}/verification.json`, JSON.stringify(result, null, 2) + '\n');
console.log(JSON.stringify({ status: result.status, kind: result.kind, checks }, null, 2));
process.exitCode = result.status === 'pass' ? 0 : 1;
