import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { resolve } from 'node:path';

const [inputPath, option, outputPath] = process.argv.slice(2);
if (!inputPath || (option && (option !== '--out' || !outputPath))) {
  throw new Error('Usage: thermo-export.mjs INPUT.json [--out NEW_DIR]');
}
const raw = await readFile(inputPath);
const data = JSON.parse(raw);
if (!/^[a-f0-9]{64}$/.test(data.mechanismSha256 ?? '')) throw new Error('Missing mechanismSha256');
if (!Array.isArray(data.species) || !data.species.length) throw new Error('Missing species records');
const names = data.species.map(s => s.name);
if (new Set(names).size !== names.length || names.some(n => typeof n !== 'string' || !n.length || /[\r\n"\\]/.test(n))) {
  throw new Error('Species names must be unique nonempty strings without quotes or escapes');
}
const forkR = 8314.47;
const referenceR = data.gasConstant_J_kmol_K;
if (!(referenceR > 8000 && referenceR < 9000)) throw new Error('Missing or invalid gasConstant_J_kmol_K');
const rows = data.species.map(species => {
  const thermo = species.thermo;
  const weights = species.molecularWeight_kg_kmol;
  if (!thermo || thermo.model !== 'NASA7' || !(weights > 0)) throw new Error(`Unsupported thermo: ${species.name}`);
  const ranges = thermo.temperatureRanges;
  if (!Array.isArray(ranges) || ranges.length !== 3 ||
      !ranges.every(Number.isFinite) || !(ranges[0] > 0 && ranges[0] < ranges[1] && ranges[1] < ranges[2])) {
    throw new Error(`Invalid NASA7 temperature ranges: ${species.name}`);
  }
  for (const key of ['lowCoeffs', 'highCoeffs']) {
    if (!Array.isArray(thermo[key]) || thermo[key].length !== 7 || !thermo[key].every(Number.isFinite)) {
      throw new Error(`Invalid NASA7 ${key}: ${species.name}`);
    }
  }
  const a = thermo.lowCoeffs;
  const t = 298.15;
  const hOverR = a[0] * t + a[1] * t ** 2 / 2 + a[2] * t ** 3 / 3 +
    a[3] * t ** 4 / 4 + a[4] * t ** 5 / 5 + a[5];
  return { name: species.name, molecularWeight_kg_kmol: weights,
    formationEnthalpyReference_J_kg: hOverR * referenceR / weights,
    formationEnthalpyFork_J_kg: hOverR * forkR / weights,
    formationReferenceWithinDeclaredRange: ranges[0] <= t && t <= ranges[1] };
});
const manifest = {
  schema: 'forge-of8-thermo-export-v1', inputSha256: createHash('sha256').update(raw).digest('hex'),
  mechanism: data.mechanism ?? null, phase: data.phase ?? null,
  mechanismSha256: data.mechanismSha256, sourceCommit: data.sourceCommit ?? null,
  sourceEnvironmentSha256: data.environmentSha256 ?? null,
  species: names, speciesCount: names.length,
  thermo: 'janaf', equationOfState: 'perfectGas', energy: 'sensibleEnthalpy',
  referenceGasConstant_J_kmol_K: referenceR, forkGasConstant_J_kmol_K: forkR,
  gasConstantRelativeDifference: (forkR - referenceR) / referenceR,
  gasConstantQualification: 'fork source constant; actual linked runtime must be measured separately',
  transport: { model: 'const', mu_Pa_s: 1.8e-5, Pr: 0.72,
    qualification: 'declared diagnostic only; not matching Cantera mixture transport' },
  formationEnthalpies: rows, executedInOpenFoam: false,
};
if (!outputPath) {
  console.log(JSON.stringify(manifest, null, 2));
  process.exit(0);
}
const out = resolve(outputPath);
await mkdir(out); // Never overwrite a previously qualified input directory.
const q = value => JSON.stringify(value);
let dictionary = `FoamFile { version 2.0; format ascii; class dictionary; object thermophysicalProperties; }
// Exact NASA7 coefficients and molecular weights from the recorded input.
// Constant transport is only a declared diagnostic approximation.
thermoType { type hePsiThermo; mixture multiComponentMixture; transport const;
 thermo janaf; equationOfState perfectGas; specie specie; energy sensibleEnthalpy; }
inertSpecie ${q(names.includes('N2') ? 'N2' : names.at(-1))};
species (${names.map(q).join(' ')});
`;
for (const species of data.species) {
  const thermo = species.thermo;
  const [low, common, high] = thermo.temperatureRanges;
  dictionary += `${q(species.name)} {
 specie { molWeight ${species.molecularWeight_kg_kmol}; }
 thermodynamics { Tlow ${low}; Thigh ${high}; Tcommon ${common};
  highCpCoeffs (${thermo.highCoeffs.join(' ')});
  lowCpCoeffs (${thermo.lowCoeffs.join(' ')}); }
 transport { mu 1.8e-5; Pr 0.72; }
}
`;
}
await writeFile(`${out}/thermophysicalProperties`, dictionary);
await writeFile(`${out}/thermo-export.json`, JSON.stringify(manifest, null, 2) + '\n');
console.log(JSON.stringify({ output: out, ...manifest }, null, 2));
