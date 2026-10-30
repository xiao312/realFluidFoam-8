/** Named numeric OpenFOAM sampled CSVs; exact coordinates, no gap filling. */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

export const hash = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const coordinateNames = ['x', 'y', 'z'];

export function readCsv(file) {
  const raw = fs.readFileSync(file), digest = crypto.createHash('sha256').update(raw).digest('hex');
  const lines = raw.toString('utf8').replace(/^\uFEFF/, '').split(/\r?\n/).map(v => v.trim()).filter(Boolean);
  while (lines.length && lines[0].startsWith('#') && !lines[0].includes(',')) lines.shift();
  if (lines.length < 2) throw new Error(`Empty sampled CSV: ${file}`);
  const names = lines.shift().replace(/^#\s*/, '').split(',').map(v => v.trim());
  const coordinates = coordinateNames.filter(name => names.includes(name));
  if (!coordinates.length || new Set(names).size !== names.length || names.some(n => !/^[A-Za-z][A-Za-z0-9_]*$/.test(n))) {
    throw new Error(`Unsupported or duplicate numeric sample headers: ${file}`);
  }
  const rows = new Map(), duplicates = [];
  lines.forEach((line, index) => {
    const cells = line.split(',');
    if (cells.length !== names.length || cells.some(v => !v.trim())) throw new Error(`Ragged sample row: ${file}:${index + 2}`);
    const values = cells.map(Number);
    if (!values.every(Number.isFinite)) throw new Error(`Nonfinite sample: ${file}:${index + 2}`);
    const row = Object.fromEntries(names.map((name, i) => [name, values[i]]));
    const key = coordinates.map(name => row[name]).join('|');
    const previous = rows.get(key);
    if (previous) {
      if (!names.every(name => row[name] === previous.values[name])) throw new Error(`Conflicting duplicate coordinate: ${file}:${index + 2}`);
      duplicates.push({ removedRow: index + 2, retainedRow: previous.line, coordinate: coordinates.map(name => row[name]) });
    } else rows.set(key, { values: row, line: index + 2 });
  });
  if (hash(file) !== digest) throw new Error(`Input changed during read: ${file}`);
  return { names, coordinates, rows, sha256: digest, duplicates };
}

export function mergeFiles(files) {
  const hashes = {}, audit = [], merged = new Map();
  let coordinates = null;
  for (const file of files) {
    const data = readCsv(file);
    hashes[file] = data.sha256;
    audit.push({ file, removedCount: data.duplicates.length, removed: data.duplicates });
    if (coordinates && JSON.stringify(coordinates) !== JSON.stringify(data.coordinates)) throw new Error('Split files have different coordinate columns');
    coordinates = data.coordinates;
    if (merged.size && (merged.size !== data.rows.size || [...merged.keys()].some(key => !data.rows.has(key)))) {
      throw new Error('Split files have different coordinate sets; no spatial filling permitted');
    }
    for (const [key, row] of data.rows) {
      const previous = merged.get(key) ?? {};
      for (const [field, value] of Object.entries(row.values)) {
        if (field in previous && previous[field] !== value) throw new Error(`Conflicting split field ${field} at ${key}`);
        previous[field] = value;
      }
      merged.set(key, previous);
    }
  }
  const rows = [...merged.entries()].sort((a, b) => {
    for (const name of coordinates) if (a[1][name] !== b[1][name]) return a[1][name] - b[1][name];
    return 0;
  });
  return { coordinates, keys: rows.map(([key]) => key), rows: rows.map(([, row]) => row),
    fields: Object.keys(rows[0][1]).filter(name => !coordinates.includes(name)).sort(), hashes, audit };
}

export function discover(caseDir, start, end, completed, observations) {
  const groups = new Map();
  for (const [category, geometry] of [['instantaneousProfiles', 'line'], ['instantaneousImagePlane', 'plane']]) {
    const directory = path.join(caseDir, 'postProcessing', category);
    if (!fs.existsSync(directory)) continue;
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      if (!entry.isDirectory() || !/^\d+(?:\.\d*)?(?:e[-+]?\d+)?$/i.test(entry.name)) continue;
      const time = Number(entry.name);
      if (time < start || time > end) continue;
      if (time > completed) throw new Error(`Sample ${time} exceeds last completed CFD time ${completed}`);
      const folder = path.join(directory, entry.name), files = new Map();
      for (const name of fs.readdirSync(folder).sort()) {
        const match = /^(nearAxis|radial\d+|midplane)(?:_|\.|$)/.exec(name);
        if (!name.endsWith('.csv') || !match) continue;
        const sample = match[1];
        if (sample.startsWith('radial') && Number(sample.slice(6)) >= observations.radialPositions_m.length) {
          throw new Error(`Unregistered sample ${sample}`);
        }
        if ((geometry === 'plane') !== (sample === 'midplane')) throw new Error(`Geometry/category mismatch for ${sample}`);
        if (!files.has(sample)) files.set(sample, []);
        files.get(sample).push(path.join(folder, name));
      }
      for (const [name, paths] of files) {
        const key = `${geometry}-${name}`;
        if (!groups.has(key)) groups.set(key, { key, name, geometry, frames: [] });
        const group = groups.get(key);
        if (group.frames.some(frame => frame.time_s === time)) throw new Error(`Duplicate numeric sample time for ${key}`);
        group.frames.push({ time_s: time, files: paths });
      }
    }
  }
  return [...groups.values()].map(group => ({ ...group, frames: group.frames.sort((a, b) => a.time_s - b.time_s) }));
}
