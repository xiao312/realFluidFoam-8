import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';

const hash = bytes => createHash('sha256').update(bytes).digest('hex');
function keys(object, allowed, name) {
  if (!object || typeof object !== 'object' || Array.isArray(object)) throw new Error(`Invalid ${name}`);
  for (const key of Object.keys(object)) if (!allowed.includes(key)) throw new Error(`Unknown ${name}.${key}`);
}
function finite(value, name, min, max) {
  if (!Number.isFinite(value) || value < min || value > max) throw new Error(`Invalid ${name}`);
  return value;
}
export function observationConfig(input, endTime) {
  keys(input, ['profileInterval_s', 'fieldInterval_s', 'averageStart_s', 'radialPositions_m', 'imageGrid'], 'observations');
  const config = {
    profileInterval_s: input.profileInterval_s ?? endTime / 4,
    fieldInterval_s: input.fieldInterval_s ?? endTime / 4,
    averageStart_s: input.averageStart_s ?? null,
    radialPositions_m: input.radialPositions_m ?? [0.03, 0.06],
    imageGrid: input.imageGrid ?? null,
    axialCoordinate: 'raw registered mesh x; injector-exit paper transform not qualified',
    nearAxisRadius_m: 0.0001,
    instantaneousFields: ['T', 'rho', 'Z', 'c', 'OH', 'CH4', 'O2', 'CO2', 'CO', 'Ha', 'fgmTdiag'],
    meanFields: ['T', 'rho', 'Z', 'c', 'OH'],
  };
  for (const name of ['profileInterval_s', 'fieldInterval_s']) finite(config[name], name, Number.MIN_VALUE, endTime);
  const fullWrites = endTime / config.fieldInterval_s;
  if (Math.abs(fullWrites - Math.round(fullWrites)) > 1e-8) throw new Error('fieldInterval_s must divide endTime so the final fields are written');
  if (config.averageStart_s !== null) finite(config.averageStart_s, 'averageStart_s', 0, endTime * (1 - 1e-12));
  if (!Array.isArray(config.radialPositions_m) || !config.radialPositions_m.length || config.radialPositions_m.length > 20) throw new Error('Invalid radialPositions_m');
  config.radialPositions_m.forEach(x => finite(x, 'radial position', 0.0001, 0.1999));
  if (config.imageGrid !== null) {
    keys(config.imageGrid, ['axialPoints', 'radialPoints'], 'imageGrid');
    for (const [key, min, max] of [['axialPoints', 2, 801], ['radialPoints', 2, 201]]) {
      const value = finite(config.imageGrid[key], key, min, max);
      if (!Number.isInteger(value)) throw new Error(`Noninteger ${key}`);
    }
  }
  return config;
}
export function decompositionConfig(input, ranks) {
  keys(input, ['method', 'n', 'order'], 'decomposition');
  const config = { method: input.method ?? 'simple' };
  if (!['simple', 'hierarchical', 'scotch'].includes(config.method)) throw new Error('Unknown decomposition method');
  if (config.method === 'scotch') {
    if (input.n !== undefined || input.order !== undefined) throw new Error('scotch does not consume n/order');
  } else {
    config.n = input.n ?? [ranks, 1, 1];
    if (!Array.isArray(config.n) || config.n.length !== 3 || config.n.some(n => !Number.isInteger(n) || n < 1) ||
        config.n.reduce((a, b) => a * b, 1) !== ranks || config.n[2] !== 1) throw new Error('n must multiply to ranks and keep the one-cell wedge direction unsplit');
    if (config.method === 'hierarchical') {
      config.order = input.order ?? 'xyz';
      if (!['xyz', 'xzy', 'yxz', 'yzx', 'zxy', 'zyx'].includes(config.order)) {
        throw new Error('Invalid hierarchical order');
      }
    } else if (input.order !== undefined) throw new Error('simple does not consume order');
  }
  return config;
}
export async function loadRunControls(observationPath, decompositionPath, endTime, ranks) {
  const load = async path => {
    if (!path) return { input: {}, sha256: null };
    const raw = await readFile(path);
    return { input: JSON.parse(raw), sha256: hash(raw) };
  };
  const observations = await load(observationPath), decomposition = await load(decompositionPath);
  return {
    observations: observationConfig(observations.input, endTime),
    decomposition: decompositionConfig(decomposition.input, ranks),
    configurationHashes: { observations: observations.sha256, decomposition: decomposition.sha256 },
  };
}
export function decompositionDictionary(config, ranks) {
  return `numberOfSubdomains ${ranks};\nmethod ${config.method};\n` +
    (config.method === 'scotch' ? '' : `${config.method}Coeffs { n (${config.n.join(' ')}); delta 0.001; ${config.order ? `order ${config.order};` : ''} }\n`);
}
function sets(config, image = false) {
  if (image) {
    const { axialPoints: nx, radialPoints: ny } = config.imageGrid;
    const points = [];
    for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
      points.push(`(${0.0001 + i * 0.1998 / (nx - 1)} ${0.0001 + j * 0.0247 / (ny - 1)} 0)`);
    }
    // OF8 points returns only located fluid points. Keep holes, never fill solids.
    return `midplane { type points; ordered no; axis xyz; points (${points.join('\n')}); }`;
  }
  return `nearAxis { type lineUniform; axis x; start (0.0001 0.0001 0); end (0.1999 0.0001 0); nPoints 400; }\n` +
    config.radialPositions_m.map((x, i) => `radial${i} { type lineUniform; axis y; start (${x} 0.0001 0); end (${x} 0.0248 0); nPoints 200; }`).join('\n');
}
function sample(name, fields, config, mean = false, image = false) {
  return `${name} { type sets; libs ("libsampling.so");
 writeControl runTime; writeInterval ${image ? config.fieldInterval_s : config.profileInterval_s};
 ${mean ? `timeStart ${config.averageStart_s};` : ''}
 interpolationScheme cellPoint; setFormat csv; fields (${fields.join(' ')});
 sets (${sets(config, image)});
}\n`;
}
export function functionObjects(config) {
  let text = sample('instantaneousProfiles', config.instantaneousFields, config);
  if (config.imageGrid) text += sample('instantaneousImagePlane', ['T', 'rho', 'Z', 'c', 'OH'], config, false, true);
  if (config.averageStart_s !== null) {
    text = `timeAverage { type fieldAverage; libs ("libfieldFunctionObjects.so");
 timeStart ${config.averageStart_s}; executeControl timeStep; executeInterval 1; writeControl writeTime;
 restartOnRestart false; restartOnOutput false; periodicRestart false;
 base time; mean yes; prime2Mean no; fields (${config.meanFields.join(' ')});
}\n` + text;
    text += sample('timeMeanProfiles', config.meanFields.map(f => `${f}Mean`), config, true);
    if (config.imageGrid) text += sample('timeMeanImagePlane', config.meanFields.map(f => `${f}Mean`), config, true, true);
  }
  for (const patch of ['ch4inlet', 'loxinlet', 'outlet']) text += `massFlux_${patch} {
 type surfaceFieldValue; libs ("libfieldFunctionObjects.so"); writeControl timeStep; writeInterval 1;
 regionType patch; name ${patch}; operation sum; fields (phi); writeFields no; log no;
}\n`;
  return text;
}
