import { readFile } from 'node:fs/promises';
import { digest } from '../../fgm-of8/direct-verification/physical-input.mjs';

export async function realFluidInput(directory, input) {
  if (!directory) throw new Error('cold-real-fluid requires --thermo-dir');
  const dictionary = await readFile(`${directory}/thermophysicalProperties`);
  const raw = await readFile(`${directory}/manifest.json`), manifest = JSON.parse(raw);
  const mixture = { PengRobinson: 'PRchungTakaMixture', soaveRedlichKwong: 'SRKchungTakaMixture' };
  if (manifest.schema !== 'direct-realfluid-thermo-v1' || !mixture[manifest.equationOfState] ||
      manifest.mixture !== mixture[manifest.equationOfState] || manifest.thermo !== 'rfJanaf' ||
      manifest.transport !== 'chungTaka' || manifest.energy !== 'sensibleEnthalpy' ||
      manifest.phase_sha256 !== input.inputHashes.metadata || manifest.mechanism_sha256 !== input.inputHashes.mechanism) {
    throw new Error('Real-fluid dictionary manifest is not bound to this exact table phase/mechanism');
  }
  if (JSON.stringify(manifest.species.map(s => s.name)) !== JSON.stringify(input.metadata.species.map(s => s.name))) throw new Error('Real-fluid species order differs');
  for (let i = 0; i < manifest.species.length; i++) {
    const a = manifest.species[i], b = input.metadata.species[i];
    if (a.molecularWeight_kg_kmol !== b.molecularWeight_kg_kmol || JSON.stringify(a.thermo) !== JSON.stringify(b.thermo)) throw new Error(`Real-fluid NASA/weight mismatch for ${b.name}`);
  }
  const text = dictionary.toString().replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/[^\n]*/g, '');
  const type = /thermoType\s*\{([^{}]+)\}/.exec(text)?.[1] ?? '';
  for (const [key, value] of Object.entries({ type: 'hePsiThermo', mixture: manifest.mixture,
    thermo: 'rfJanaf', transport: 'chungTaka', equationOfState: manifest.equationOfState, specie: 'rfSpecie', energy: 'sensibleEnthalpy' })) {
    if (!new RegExp(`\\b${key}\\s+${value}\\s*;`).test(type)) throw new Error(`Dictionary runtime ${key} disagrees with manifest`);
  }
  const pressure = input.receipt.case.pressure_pa;
  const conditions = pressure === 5610000 ? { oxygen:85, methane:288 }
    : pressure === 5600000 ? { oxygen:83, methane:300 } : null;
  if (!conditions) throw new Error('Cold G2 requires registered5.61MPa/85/288K or Schmitt5.6MPa/83/300K conditions');
  const low = Math.max(...manifest.species.map(s => s.effectiveMinimumTemperature_K));
  const high = Math.min(...manifest.species.map(s => s.effectiveMaximumTemperature_K));
  if (!(low <= conditions.oxygen && high > conditions.methane)) throw new Error('Declared full-mixture inversion bounds do not cover cold streams');
  for (const [name, species, temperature, z] of [['fuel', 'CH4', conditions.methane, 1], ['oxidizer', 'O2', conditions.oxygen, 0]]) {
    const declared = input.receipt.case[name], state = input.lookup(z, 0);
    if (declared?.temperature_k !== temperature || JSON.stringify(declared.mole_fractions) !== JSON.stringify({ [species]: 1 })) throw new Error(`Cold table receipt ${name} is not the required pure stream`);
    if (Math.abs(state.temperature - temperature) > 1e-6 || state.y.some((v, i) => Math.abs(v - (input.metadata.species[i].name === species ? 1 : 0)) > 1e-12)) throw new Error(`Actual table ${name} endpoint disagrees with cold receipt`);
  }
  return { dictionary, rawManifest: raw, manifest,
    record: { mode: 'cold-real-fluid', equationOfState: manifest.equationOfState, mixture: manifest.mixture,
      dictionarySha256: digest(dictionary), manifestSha256: digest(raw),
      metadataSha256: manifest.phase_sha256, authorSha256: manifest.author_sha256,
      effectiveInversionRange_K: [low, high],
      originalNasaBounds: manifest.species.map(s => ({ name: s.name, range_K: [s.thermo.temperatureRanges[0], s.thermo.temperatureRanges[2]] })),
      requiresRuntimeHaInitialization: true, runtimeQualified: false, volumeTranslated: false,
      qualification: 'Cold stream conditions match. Actual PR/SRK runtime, property/inversion behavior and source-table thermal consistency remain separate diagnostics.' } };
}

export async function initializationInput(path, input) {
  const raw = path ? await readFile(path) : null;
  const config = raw ? JSON.parse(raw) : { mode: 'uniform-covered', mixtureFraction: 0.2, hotEta: 0.5 };
  const allowed = ['mode', 'mixtureFraction', 'hotEta', 'boxMin_m', 'boxMax_m'];
  for (const key of Object.keys(config)) if (!allowed.includes(key)) throw new Error(`Unknown initialization.${key}`);
  const eta = config.mode === 'uniform-cmin' ? 0 : config.hotEta;
  if (!['uniform-covered', 'uniform-cmin', 'localized-covered'].includes(config.mode) || !Number.isFinite(config.mixtureFraction) ||
      !(config.mixtureFraction > 0 && config.mixtureFraction < 1) || !Number.isFinite(eta) || eta < 0 || eta > 1 ||
      (config.mode !== 'uniform-cmin' && eta === 0) || (config.mode === 'uniform-cmin' && config.hotEta !== undefined)) throw new Error('Invalid covered initialization state');
  const hot = input.lookup(config.mixtureFraction, eta);
  const background = config.mode === 'localized-covered' ? input.lookup(config.mixtureFraction, 0) : hot;
  if (config.mode === 'localized-covered') {
    for (const key of ['boxMin_m', 'boxMax_m']) if (!Array.isArray(config[key]) || config[key].length !== 3 || !config[key].every(Number.isFinite)) throw new Error(`Invalid initialization.${key}`);
    if (config.boxMin_m.some((v, i) => v >= config.boxMax_m[i]) || config.boxMin_m[0] < 0 || config.boxMax_m[0] > 0.2 ||
        config.boxMin_m[1] < 0 || config.boxMax_m[1] > 0.025 || config.boxMin_m[2] < -0.0011 || config.boxMax_m[2] > 0.0011) throw new Error('Ignition box must be inside the declared mesh extent');
    const inletMax = Math.max(input.lookup(0, 0).temperature, input.lookup(1, 0).temperature);
    if (background.temperature > inletMax + 50 || hot.temperature < 1000 || hot.temperature - background.temperature < 300) throw new Error('Covered states do not provide the declared cold-background/hot-kernel recipe');
  } else if (config.boxMin_m || config.boxMax_m) throw new Error('Uniform initialization does not consume an ignition box');
  return { config, sha256: raw ? digest(raw) : null, hot, background,
    interpretation: config.mode === 'localized-covered'
      ? 'Table Cmin background and covered hot state in an explicit raw-coordinate box; no evolved CFD, no rounding Cmin to zero.'
      : config.mode === 'uniform-cmin'
        ? 'Uniform actual table Cmin state, retaining any tiny positive C; source-disabled transport diagnostic, not a flame.'
        : 'Uniform table-covered partly reacted fill; startup coupling only, not physical flame morphology.' };
}

export function ignitionDictionary(initialization, names) {
  const { config, hot } = initialization;
  if (config.mode !== 'localized-covered') return null;
  const fields = [['T', hot.temperature], ['Z', hot.z], ['c', hot.c], ...names.map((name, i) => [name, hot.y[i]])];
  return `FoamFile { version 2.0; format ascii; class dictionary; object setFieldsDict; }
defaultFieldValues ();
regions (boxToCell { box (${config.boxMin_m.join(' ')}) (${config.boxMax_m.join(' ')});
 fieldValues (${fields.map(([name, value]) => `volScalarFieldValue "${name}" ${value}`).join('\n')}); });\n`;
}
