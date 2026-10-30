import { readFile, readdir } from 'node:fs/promises';

export function scalarValues(raw, name) {
  const uniform = /internalField\s+uniform\s+([^;]+);/.exec(raw);
  if (uniform) return [Number(uniform[1])];
  const list = /internalField\s+nonuniform\s+List<scalar>\s+(\d+)\s*\(([\s\S]*?)\)\s*;/.exec(raw);
  if (!list) throw new Error(`Cannot parse ASCII scalar internal field ${name}`);
  const values = list[2].trim().split(/\s+/).map(Number);
  if (values.length !== Number(list[1])) throw new Error(`Count mismatch in ${name}`);
  return values;
}
export function differenceSummary(left, right) {
  const count = Math.max(left.length, right.length);
  if ([left, right].some(a => a.length !== 1 && a.length !== count)) throw new Error('Field sizes differ');
  let sum = 0, sum2 = 0, maxAbs = 0;
  for (let i = 0; i < count; i++) {
    const delta = left[left.length === 1 ? 0 : i] - right[right.length === 1 ? 0 : i];
    if (!Number.isFinite(delta)) throw new Error('Nonfinite field difference');
    sum += delta; sum2 += delta * delta; maxAbs = Math.max(maxAbs, Math.abs(delta));
  }
  return { cellArithmeticMean: sum / count, cellArithmeticRms: Math.sqrt(sum2 / count), maxAbs, count };
}
async function fluxSeries(root, patch) {
  const directory = `${root}/postProcessing/massFlux_${patch}`;
  const values = new Map();
  for (const time of await readdir(directory)) {
    if (!Number.isFinite(Number(time))) continue;
    for (const name of await readdir(`${directory}/${time}`)) {
      if (!name.endsWith('.dat')) continue;
      for (const line of (await readFile(`${directory}/${time}/${name}`, 'utf8')).split(/\r?\n/)) {
        if (!line.trim() || line.trim().startsWith('#')) continue;
        const row = line.trim().split(/\s+/).map(Number);
        if (row.length !== 2 || !row.every(Number.isFinite)) throw new Error(`Malformed phi history ${patch}/${time}/${name}`);
        if (values.has(row[0]) && values.get(row[0]) !== row[1]) throw new Error(`Conflicting repeated phi time ${patch}`);
        values.set(row[0], row[1]);
      }
    }
  }
  return [...values].sort((a, b) => a[0] - b[0]).map(([time, flux]) => ({ time, flux }));
}
export async function inletAndMassAudit(root, manifest, states) {
  const patches = ['ch4inlet', 'loxinlet', 'outlet'];
  const series = {};
  try { for (const patch of patches) series[patch] = await fluxSeries(root, patch); }
  catch (error) { return { status: 'unavailable-or-invalid', reason: error.message }; }
  const inlets = {};
  for (const patch of patches.slice(0, 2)) {
    const expectedOutwardFlux_kg_s = -manifest.streams[patch].massFlow_kg_s;
    const rows = series[patch];
    let maxRelativeError = 0;
    for (const row of rows) maxRelativeError = Math.max(maxRelativeError, Math.abs(row.flux / expectedOutwardFlux_kg_s - 1));
    inlets[patch] = { expectedOutwardFlux_kg_s, samples: rows.length,
      maxRelativeError: rows.length ? maxRelativeError : null,
      latestOutwardFlux_kg_s: rows.at(-1)?.flux ?? null };
  }
  const lookup = Object.fromEntries(patches.map(p => [p, new Map(series[p].map(r => [r.time, r.flux]))]));
  const rows = series.outlet.filter(row => patches.every(p => lookup[p].has(row.time))).map(row => ({
    time: row.time, flux: patches.reduce((sum, p) => sum + lookup[p].get(row.time), 0),
  }));
  const stateAt = time => states.find(row => Math.abs(row.t - time) <= Math.max(1e-14, Math.abs(time) * 1e-8));
  const start = rows[0], end = rows.at(-1), initial = start && stateAt(start.time), final = end && stateAt(end.time);
  let integral = 0;
  for (let i = 1; i < rows.length; i++) integral += (rows[i].time - rows[i - 1].time) * (rows[i].flux + rows[i - 1].flux) / 2;
  const closed = rows.length > 1 && initial && final;
  return { status: 'measured', inlets,
    massBalance: closed ? { startTime_s: start.time, endTime_s: end.time, samples: rows.length,
      massChange_kg: final.mass - initial.mass, outwardFluxIntegral_kg: integral,
      residual_kg: final.mass - initial.mass + integral,
      residualOverInitialMass: (final.mass - initial.mass + integral) / initial.mass,
      interpretation: 'Trapezoidal boundary-flux quadrature over the common recorded interval; not the exact assembled FV balance or an energy balance.' }
      : { status: 'insufficient common boundary/state samples', samples: rows.length } };
}
export async function averagingAudit(root, latest, config, ranks) {
  if (config?.averageStart_s == null) return { enabled: false, interpretation: 'Every profile and image is instantaneous.' };
  try {
    const parse = raw => {
      const fields = {};
      for (const name of config.meanFields) {
        const block = new RegExp(`\\b${name}\\s*\\{([^{}]*)\\}`).exec(raw)?.[1];
        const totalTime = Number(/totalTime\s+([^;]+);/.exec(block ?? '')?.[1]);
        const totalIter = Number(/totalIter\s+([^;]+);/.exec(block ?? '')?.[1]);
        if (!(totalTime > 0) || !Number.isInteger(totalIter) || totalIter < 1) throw new Error(`Missing actual average counters for ${name}`);
        fields[name] = { accumulatedTime_s: totalTime, steps: totalIter };
      }
      return fields;
    };
    const paths = ranks > 1 ? Array.from({ length: ranks }, (_, rank) => `${root}/processor${rank}/${latest}/uniform/timeAverageProperties`)
      : [`${root}/${latest}/uniform/timeAverageProperties`];
    const fields = parse(await readFile(paths[0], 'utf8'));
    for (const path of paths.slice(1)) {
      if (JSON.stringify(parse(await readFile(path, 'utf8'))) !== JSON.stringify(fields)) throw new Error('Processor average counters disagree');
    }
    return { enabled: true, configuredStartTime_s: config.averageStart_s, propertiesFiles: paths, fields,
      interpretation: 'Time-weighted running means over the retained counters; statistical convergence has not been established.' };
  } catch (error) { return { enabled: true, status: 'actual averaging counters unavailable', reason: error.message }; }
}
