import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { constants, excitationTemperature_K, instantaneousProxy, averageProxies, validateSampling } from './proxy.mjs';
import { readCsv, mergeFields, writeCsv } from './csv.mjs';

const args = process.argv.slice(2), options = {};
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--apply') options.apply = true;
  else if (['--manifest', '--out'].includes(args[i]) && args[i+1] && !args[i+1].startsWith('--')) options[args[i].slice(2)] = args[++i];
  else throw new Error(`Unknown/missing option ${args[i]}`);
}
if (!options.manifest || !options.out) throw new Error('Usage: run.mjs --manifest INPUT.json --out NEW_DIR [--apply]');
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const inputs = {};
async function consume(path) {
  const bytes = await readFile(path); inputs[path] = hash(bytes); return bytes.toString('utf8');
}
const manifestPath = resolve(options.manifest), base = dirname(manifestPath);
const manifest = JSON.parse(await consume(manifestPath));
validateSampling(manifest);
if (typeof manifest.phaseMetadata !== 'string') throw new Error('phaseMetadata path is required');
const metadata = JSON.parse(await consume(resolve(base, manifest.phaseMetadata)));
const species = metadata.species?.filter(species => species.name === 'OH');
if (!species || species.length !== 1) throw new Error('Exact phase metadata must contain one OH species');
const molecularWeight = species[0].molecularWeight_kg_kmol;
const frames = [];
for (const frame of manifest.frames) {
  const tables = [];
  for (const name of frame.files) {
    const path = resolve(base, name); tables.push(readCsv(await consume(path), path));
  }
  const samples = mergeFields(tables);
  const rows = samples.map(sample => ({ time_s: frame.time_s, ...instantaneousProxy(sample, molecularWeight) }));
  frames.push({ time_s: frame.time_s, rows });
}
const mean = manifest.averaging ? averageProxies(frames) : null;
const gaps = frames.slice(1).map((frame, i) => frame.time_s-frames[i].time_s);
const receipt = { schema: 'oh-lte-proxy-result/v1',
  interpretation: 'Instantaneous 308 nm thermal-equilibrium population approximation; uncalibrated optical proxy',
  sourcePaper: { title: 'Mueller and Pfitzner (2015)', page: 9, equation: 18,
    pdf_sha256: '889bba9dc807b9197efcabbebba5a06f1dbf9d55c26582d19c88fbd10f15a8b9' },
  constants, excitationTemperature_K, molecularWeight_OH_kg_kmol: molecularWeight,
  units: { YOHstar_LTE_proxy: 'dimensionless', cOHstar_LTE_proxy_mol_m3: 'mol/m3', coordinates: 'm', time: 's' },
  sampling: manifest.sampling, provenance: manifest.provenance, inputHashes: inputs,
  frames: frames.map(frame => ({ time_s: frame.time_s, points: frame.rows.length,
    excitationUnderflowCount: frame.rows.reduce((sum, row) => sum+row.excitationUnderflow, 0) })),
  averaging: mean ? { ...manifest.averaging, duration_s: gaps.reduce((sum, gap) => sum+gap, 0),
    samples: frames.length, minimumGap_s: Math.min(...gaps), maximumGap_s: Math.max(...gaps),
    operatorOrder: 'instantaneous population transform, then trapezoidal time integration',
    statisticalConvergenceEstablished: false } : null,
  lineOfSight: 'not computed: radial support and optical assumptions not qualified',
  opticalCalibration: false, scientificAcceptance: false, sourceHashes: {}, outputHashes: {} };
for (const name of ['run.mjs', 'proxy.mjs', 'csv.mjs']) {
  receipt.sourceHashes[name] = hash(await readFile(resolve(dirname(fileURLToPath(import.meta.url)), name)));
}
if (!options.apply) {
  console.log(JSON.stringify({ mode: 'read-only-plan', output: resolve(options.out), ...receipt }, null, 2));
} else {
  const out = resolve(options.out);
  await mkdir(dirname(out), { recursive: true });
  await mkdir(out); // Existing result directories are immutable.
  const artifacts = frames.map((frame, i) => [`instant-${String(i).padStart(4, '0')}.csv`, writeCsv(frame.rows)]);
  if (mean) artifacts.push(['time-mean.csv', writeCsv(mean)]);
  for (const [name, text] of artifacts) {
    await writeFile(resolve(out, name), text, { flag: 'wx' }); receipt.outputHashes[name] = hash(text);
  }
  await writeFile(resolve(out, 'receipt.json'), JSON.stringify(receipt, null, 2)+'\n', { flag: 'wx' });
  console.log(JSON.stringify({ output: out, frames: frames.length, mean: Boolean(mean), scientificAcceptance: false }));
}
