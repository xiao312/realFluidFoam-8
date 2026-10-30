import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';

export const digest = raw => createHash('sha256').update(raw).digest('hex');

export async function loadPhysicalTable(directory, metadataPath) {
  const [raw, receiptRaw, metadataRaw] = await Promise.all([
    readFile(`${directory}/physical.tbl`), readFile(`${directory}/receipt.json`), readFile(metadataPath),
  ]);
  const receipt = JSON.parse(receiptRaw);
  const metadata = JSON.parse(metadataRaw);
  if (receipt.schema !== 'physical-family-table/v1' ||
      digest(raw) !== receipt.artifacts['physical.tbl'] ||
      digest(metadataRaw) !== receipt.metadata_sha256 ||
      metadata.mechanismSha256 !== receipt.mechanism_sha256) throw new Error('Physical input identity mismatch');
  const headers = {}, blocks = {};
  let current = null;
  for (const line of raw.toString().split(/\r?\n/)) {
    const parts = line.replace(/#.*/, '').trim().split(/\s+/);
    if (!parts[0]) continue;
    if (parts[0] === 'block') { current = parts.slice(1).join(' '); blocks[current] = []; }
    else if (parts[0] === 'end') current = null;
    else if (current) blocks[current].push(parts.map(Number));
    else headers[parts[0]] = parts.slice(1);
  }
  if (headers.schema?.[0] !== 'forge-fgm-table-v2' ||
      headers['progress-coordinate']?.[0] !== 'mass-fraction-mapped') throw new Error('A physical v2 table is required');
  const names = metadata.species.map(s => s.name);
  if (JSON.stringify(headers.species) !== JSON.stringify(names)) throw new Error('Table and thermo species order differ');
  const z = headers.z.map(Number), eta = headers.c.map(Number);
  const cMin = headers['c-min'].map(Number), cMax = headers['c-max'].map(Number);
  if (z.length !== Number(headers.nZ[0]) || eta.length !== Number(headers.nC[0]) ||
      cMin.length !== z.length || cMax.length !== z.length) throw new Error('Invalid table axes');
  for (const key of [...names.map(n => `Y ${n}`), 'Sc', 'Q', 'Tdiag']) {
    if (!blocks[key] || blocks[key].length !== z.length ||
        blocks[key].some(row => row.length !== eta.length || row.some(v => !Number.isFinite(v)))) {
      throw new Error(`Invalid physical block ${key}`);
    }
  }
  const bracket = (axis, x) => {
    if (x < axis[0] || x > axis.at(-1)) throw new Error('Lookup outside physical table');
    let i = 0;
    while (i < axis.length - 2 && x > axis[i + 1]) i++;
    return [i, (x - axis[i]) / (axis[i + 1] - axis[i])];
  };
  const interpolate = (row, i, w) => row[i] * (1 - w) + row[i + 1] * w;
  const lookup = (mixture, progressFraction) => {
    const [i, wz] = bracket(z, mixture), [j, wc] = bracket(eta, progressFraction);
    const value = key => interpolate([
      interpolate(blocks[key][i], j, wc), interpolate(blocks[key][i + 1], j, wc)], 0, wz);
    const lower = interpolate(cMin, i, wz), upper = interpolate(cMax, i, wz);
    const y = names.map(name => value(`Y ${name}`));
    const c = lower + progressFraction * (upper - lower);
    const fromSpecies = headers['progress-species'].reduce((sum, name) => sum + y[names.indexOf(name)], 0);
    if (Math.abs(y.reduce((a, b) => a + b, 0) - 1) > 1e-8 || Math.abs(c - fromSpecies) > 1e-8) {
      throw new Error('Physical table composition/progress inconsistency');
    }
    return { z: mixture, eta: progressFraction, c, lower, upper, y,
      source: value('Sc'), qFormation: value('Q'), temperature: value('Tdiag') };
  };
  return { raw, receipt, metadata, lookup, inputHashes: {
    table: digest(raw), receipt: digest(receiptRaw), metadata: digest(metadataRaw),
    mechanism: metadata.mechanismSha256,
  } };
}

export function thermoState(metadata, y, temperature) {
  let enthalpy = 0, cp = 0, gasConstant = 0;
  for (let i = 0; i < y.length; i++) {
    const s = metadata.species[i], r = metadata.gasConstant_J_kmol_K / s.molecularWeight_kg_kmol;
    const a = temperature < s.thermo.temperatureRanges[1] ? s.thermo.lowCoeffs : s.thermo.highCoeffs;
    const t = temperature;
    const h = r * (a[0] * t + a[1] * t ** 2 / 2 + a[2] * t ** 3 / 3 + a[3] * t ** 4 / 4 + a[4] * t ** 5 / 5 + a[5]);
    enthalpy += y[i] * h;
    cp += y[i] * r * (a[0] + a[1] * t + a[2] * t ** 2 + a[3] * t ** 3 + a[4] * t ** 4);
    gasConstant += y[i] * r;
  }
  return { enthalpy, internalEnergy: enthalpy - gasConstant * temperature, cp,
    cv: cp - gasConstant, gasConstant };
}
