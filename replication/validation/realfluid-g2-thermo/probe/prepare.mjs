import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { createHash } from 'node:crypto';

const options = {}, args = process.argv.slice(2);
for (let i = 0; i < args.length; i += 2) {
  if (!['--thermo-dir', '--species', '--out', '--boundary', '--cells'].includes(args[i]) || !args[i + 1]) throw new Error('Use --thermo-dir DIR --species O2|CH4 [--out NEW_CASE] [--boundary gradient|fixed|bad-ha] [--cells N]');
  options[args[i].slice(2)] = args[i + 1];
}
if (!options['thermo-dir'] || !['O2', 'CH4'].includes(options.species)) throw new Error('Explicit thermo directory and O2|CH4 species required');
const boundary = options.boundary ?? 'gradient';
const cells = Number(options.cells ?? 1);
if (!Number.isInteger(cells) || cells < 1 || cells > 512) throw new Error('Probe cells must be an integer1..512');
if (!['gradient', 'fixed', 'bad-ha'].includes(boundary)) throw new Error('Unknown boundary qualification mode');
const directory = resolve(options['thermo-dir']);
const [dictionary, raw] = await Promise.all([readFile(`${directory}/thermophysicalProperties`), readFile(`${directory}/manifest.json`)]);
const manifest = JSON.parse(raw);
if (manifest.schema !== 'direct-realfluid-thermo-v1' ||
    !['PengRobinson', 'soaveRedlichKwong'].includes(manifest.equationOfState) ||
    !manifest.species.some(row => row.name === options.species)) throw new Error('Unsupported real-fluid input manifest');
const temperatures = options.species === 'O2'
  ? [85, 90, 100, 120, 140, 150, 155, 160, 165, 170, 180, 200, 250, 288, 300, 400, 600]
  : [200, 250, 288, 300, 400, 600];
const increments = [-0.1, -0.001, 0.001, 0.1];
const low = Math.max(...manifest.species.map(s => s.effectiveMinimumTemperature_K));
const high = Math.min(...manifest.species.map(s => s.effectiveMaximumTemperature_K));
if (!(Math.min(...temperatures) - 0.1 >= low && Math.max(...temperatures) + 0.5 <= high)) {
  throw new Error(`Requested probe exceeds effective inversion range ${low}..${high} K; prepare a separately declared extrapolation input first`);
}
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const selected = manifest.species.find(s => s.name === options.species);
const plan = { schema: 'direct-realfluid-cold-probe-v1', species: options.species, pressure_Pa: 5610000, boundaryMode: boundary,
  cells,
  temperatures_K: temperatures, increments_K: increments, initialGuessOffset_K: 0.5,
  equationOfState: manifest.equationOfState, mixture: manifest.mixture,
  volumeTranslated: false, originalNasaRange_K: selected.thermo.temperatureRanges,
  extrapolatedTemperatures_K: temperatures.filter(t => t < selected.thermo.temperatureRanges[0] || t > selected.thermo.temperatureRanges[2]),
  statesWithExtrapolatedInversionTargets_K: temperatures.filter(t => t + Math.min(...increments) < selected.thermo.temperatureRanges[0] ||
    t + Math.max(...increments) > selected.thermo.temperatureRanges[2]),
  effectiveInversionRange_K: [low, high], sourceDictionarySha256: hash(dictionary),
  sourceManifestSha256: hash(raw), mechanismSha256: manifest.mechanism_sha256,
  inputAuthorSha256: manifest.author_sha256, numericalInversionTolerance_K: 1e-5,
  scientificValidation: false };
if (!options.out) { console.log(JSON.stringify({ dryRun: true, ...plan }, null, 2)); process.exit(0); }
const out = resolve(options.out);
await mkdir(out);
for (const folder of ['0', 'constant', 'system']) await mkdir(`${out}/${folder}`);
const header = (object, cls = 'dictionary') => `FoamFile { version 2.0; format ascii; class ${cls}; object "${object}"; }\n`;
const put = (path, content) => writeFile(`${out}/${path}`, content);
async function field(name, dimensions, value) {
  const fixed = name === 'T' && boundary !== 'gradient' || name === 'Ha' && boundary === 'fixed';
  await put(`0/${name}`, header(name, 'volScalarField') + `dimensions [${dimensions}];
internalField uniform ${value}; boundaryField { walls { ${fixed ? `type fixedValue; value uniform ${value};` : 'type zeroGradient;'} } }\n`);
}
await field('p', '1 -1 -2 0 0 0 0', plan.pressure_Pa);
await field('T', '0 0 0 1 0 0 0', options.species === 'O2' ? 85 : 288);
await field('Ha', '0 2 -2 0 0 0 0', 0); // Explicit placeholder for -initialize-Ha only.
for (const species of manifest.species) await field(species.name, '0 0 0 0 0 0 0', species.name === options.species ? 1 : 0);
await put('constant/thermophysicalProperties', dictionary);
await put('constant/probeProperties', header('probeProperties') + `pressure ${plan.pressure_Pa};
temperatures (${temperatures.join(' ')}); increments (${increments.join(' ')}); initialGuessOffset 0.5;\n`);
await put('system/blockMeshDict', header('blockMeshDict') + `convertToMeters 1;
vertices ((0 0 0) (0.001 0 0) (0.001 0.001 0) (0 0.001 0)
 (0 0 0.001) (0.001 0 0.001) (0.001 0.001 0.001) (0 0.001 0.001));
blocks (hex (0 1 2 3 4 5 6 7) (${cells} 1 1) simpleGrading (1 1 1)); edges ();
boundary (walls { type wall; faces ((0 4 7 3) (1 2 6 5) (0 1 5 4) (3 7 6 2) (0 3 2 1) (4 5 6 7)); });
mergePatchPairs ();\n`);
await put('system/controlDict', header('controlDict') + `application realFluidG2ThermoProbe;
startFrom startTime; startTime 0; stopAt endTime; endTime 0; deltaT 1;
writeControl timeStep; writeInterval 1; writeFormat ascii; writePrecision 16;
writeCompression off; runTimeModifiable no;\n`);
await put('system/fvSchemes', header('fvSchemes') + `ddtSchemes { default Euler; }
gradSchemes { default Gauss linear; } divSchemes { default none; }
laplacianSchemes { default Gauss linear corrected; } interpolationSchemes { default linear; }
snGradSchemes { default corrected; } fluxRequired { default no; }\n`);
await put('system/fvSolution', header('fvSolution') + 'solvers {}\n');
await put('probe-input.json', JSON.stringify(plan, null, 2) + '\n');
await put('initialization-input.json', JSON.stringify({schema:'full-runtime-ha-qualification-v1',startTime:0,
  thermodynamics:{mode:'cold-real-fluid',requiresRuntimeHaInitialization:true,dictionarySha256:hash(dictionary)},
  initialization:{config:{mode:'uniform-prescribed'}},inputHashes:{table:null},physicalValidation:false},null,2)+'\n');
console.log(JSON.stringify({ created: out, ...plan }, null, 2));
