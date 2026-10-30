import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';

const options = {};
for (let i = 2; i < process.argv.length; i += 2) {
  const key = process.argv[i];
  if (!['--phase', '--author', '--eos', '--out', '--minimum-temperature', '--maximum-temperature'].includes(key) || !process.argv[i + 1]) {
    throw new Error('Usage: export.mjs --phase FILE --author FILE --eos SRK|PR [--minimum-temperature K] [--maximum-temperature K] [--out NEW_DIR]');
  }
  if (key in options) throw new Error(`Duplicate option: ${key}`);
  options[key] = process.argv[i + 1];
}
for (const required of ['--phase', '--author', '--eos']) if (!options[required]) throw new Error(`Missing ${required}`);
if (!['SRK', 'PR'].includes(options['--eos'])) throw new Error('EOS must be explicit SRK or PR');
const minimum = options['--minimum-temperature'] === undefined ? null : Number(options['--minimum-temperature']);
if (minimum !== null && (!Number.isFinite(minimum) || minimum <= 0)) throw new Error('Invalid minimum temperature');
const maximum = options['--maximum-temperature'] === undefined ? null : Number(options['--maximum-temperature']);
if (maximum !== null && (!Number.isFinite(maximum) || maximum <= 0)) throw new Error('Invalid maximum temperature');
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const phaseRaw = await readFile(options['--phase']);
const authorRaw = await readFile(options['--author']);
const phase = JSON.parse(phaseRaw);
if (!Array.isArray(phase.species) || !/^[a-f0-9]{64}$/.test(phase.mechanismSha256 ?? '')) throw new Error('Invalid phase metadata');
// The fixed author file has one unindented species name per block; species such
// as CH2(S) are deliberately retained, not tokenized as parenthesized lists.
const authorText = authorRaw.toString('utf8').replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/[^\n]*/g, '');
const starts = [...authorText.matchAll(/^(\S+)\s*\r?\n\{/gm)];
const author = new Map();
const keys = ['Tc', 'Pc', 'Vc', 'omega', 'kappai', 'miui', 'sigmvi'];
for (let i = 0; i < starts.length; i++) {
  const name = starts[i][1];
  const body = authorText.slice(starts[i].index, starts[i + 1]?.index);
  const match = body.match(/dataForRealGas\s*\{([^}]+)\}/);
  if (!match || author.has(name)) throw new Error(`Missing/duplicate author block ${name}`);
  const data = {};
  for (const key of keys) {
    const value = match[1].match(new RegExp(`\\b${key}\\s+([^;\\s]+)\\s*;`));
    if (!value || !Number.isFinite(Number(value[1]))) throw new Error(`Invalid ${name}.${key}`);
    data[key] = Number(value[1]);
  }
  if (!(data.Tc > 0 && data.Pc > 0 && data.Vc > 0)) throw new Error(`Invalid critical state for ${name}`);
  author.set(name, data);
}
const seen = new Set();
const species = phase.species.map(entry => {
  if (seen.has(entry.name) || !author.has(entry.name) || /["\\\r\n]/.test(entry.name)) throw new Error(`Invalid/missing species ${entry.name}`);
  seen.add(entry.name);
  const t = entry.thermo;
  if (t?.model !== 'NASA7' || !(entry.molecularWeight_kg_kmol > 0)) throw new Error(`Unsupported thermo ${entry.name}`);
  if (t.temperatureRanges.length !== 3 || !t.temperatureRanges.every(Number.isFinite)) throw new Error('Invalid ranges');
  for (const key of ['lowCoeffs', 'highCoeffs']) if (t[key].length !== 7 || !t[key].every(Number.isFinite)) throw new Error('Invalid NASA coefficients');
  const low = minimum === null ? t.temperatureRanges[0] : Math.min(minimum, t.temperatureRanges[0]);
  const high = maximum === null ? t.temperatureRanges[2] : Math.max(maximum, t.temperatureRanges[2]);
  if (!(low < t.temperatureRanges[1] && t.temperatureRanges[1] < high)) throw new Error('Invalid interval order');
  if (!entry.composition || !Object.keys(entry.composition).length || !Object.values(entry.composition).every(n => Number.isFinite(n) && n > 0)) throw new Error(`Invalid elemental composition for ${entry.name}`);
  return { ...entry, effectiveMinimumTemperature_K: low, effectiveMaximumTemperature_K: high, dataForRealGas: author.get(entry.name) };
});
const eos = options['--eos'];
const manifest = { schema: 'direct-realfluid-thermo-v1', phase_sha256: hash(phaseRaw), author_sha256: hash(authorRaw),
  mechanism_sha256: phase.mechanismSha256, source_commit: phase.sourceCommit,
  equationOfState: eos === 'SRK' ? 'soaveRedlichKwong' : 'PengRobinson', mixture: `${eos}chungTakaMixture`,
  transport: 'chungTaka', thermo: 'rfJanaf', energy: 'sensibleEnthalpy', speciesCount: species.length,
  parameterUnits: { Tc: 'K', Pc: 'MPa as required by rfSpecie dictionary', Vc: 'cm3/mol in author input' },
  minimumTemperatureOverride_K: minimum, maximumTemperatureOverride_K: maximum, species,
  qualification: 'Prepared input only; actual full-fork loading, cold-state properties and energy inversion remain unqualified.' };
if (!options['--out']) {
  console.log(JSON.stringify({ ...manifest, species: species.map(s => ({ name: s.name, dataForRealGas: s.dataForRealGas, effectiveMinimumTemperature_K: s.effectiveMinimumTemperature_K, effectiveMaximumTemperature_K: s.effectiveMaximumTemperature_K })) }, null, 2));
  process.exit(0);
}
await mkdir(options['--out']);
let dictionary = `FoamFile { version 2.0; format ascii; class dictionary; object thermophysicalProperties; }
thermoType { type hePsiThermo; mixture ${manifest.mixture}; transport chungTaka;
 thermo rfJanaf; equationOfState ${manifest.equationOfState}; specie rfSpecie; energy sensibleEnthalpy; }
inertSpecie ${JSON.stringify(seen.has('N2') ? 'N2' : species.at(-1).name)};
species (${species.map(s => JSON.stringify(s.name)).join(' ')});
`;
for (const entry of species) {
  const t = entry.thermo;
  dictionary += `${JSON.stringify(entry.name)} {
 specie { molWeight ${entry.molecularWeight_kg_kmol}; }
 thermodynamics { Tlow ${entry.effectiveMinimumTemperature_K}; Tcommon ${t.temperatureRanges[1]}; Thigh ${entry.effectiveMaximumTemperature_K};
 lowCpCoeffs (${t.lowCoeffs.join(' ')}); highCpCoeffs (${t.highCoeffs.join(' ')}); }
 dataForRealGas { ${keys.map(k => `${k} ${entry.dataForRealGas[k]};`).join(' ')} }
 elements { ${Object.entries(entry.composition ?? {}).map(([name,count]) => `${name} ${count};`).join(' ')} }
}
`;
}
await writeFile(`${options['--out']}/thermophysicalProperties`, dictionary);
await writeFile(`${options['--out']}/manifest.json`, JSON.stringify(manifest, null, 2)+'\n');
console.log(JSON.stringify({ output: options['--out'], species: species.length, dictionary_sha256: hash(dictionary), qualification: manifest.qualification }));
