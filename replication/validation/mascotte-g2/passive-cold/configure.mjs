import fs from 'node:fs';
import {createHash} from 'node:crypto';

const [root, tableDirectory, action] = process.argv.slice(2);
const apply = action === '--apply';
if (!root || !tableDirectory || ![undefined, '--apply'].includes(action)) {
  throw Error('Use NEW_CASE TABLE_DIRECTORY [--apply]');
}
if (fs.readdirSync(root).some(name => name.startsWith('processor')
    || (Number.isFinite(Number(name)) && Number(name) > 0))
    || fs.existsSync(root + '/passive-cold-input.json')) {
  throw Error('A fresh undecomposed factory case is required');
}
const read = name => fs.readFileSync(name, 'utf8');
const hash = value => createHash('sha256').update(value).digest('hex');
const factory = JSON.parse(read(root + '/direct-g2-input.json'));
const manifest = JSON.parse(read(tableDirectory + '/manifest.json'));
const table = read(tableDirectory + '/passive.tbl');
if (manifest.schema !== 'analytic-passive-cold-table/v1'
    || hash(table) !== manifest.tableSha256 || factory.startTime !== 0
    || factory.initialization.config.mixtureFraction !== 1
    || factory.energyForm !== 'absoluteEnthalpy'
    || factory.closure !== 'steady-flamelet') {
  throw Error('Explicit original-zero absolute-Ha passive control required');
}
const species = manifest.species;
const headerNames = table.match(/^species\s+\d+\s+(.+)$/m)?.[1].trim().split(/\s+/);
const tableRows = table.match(/^points 2\s*\ndata\s*\n([\s\S]+)\nend\s*$/m)?.[1]
  .trim().split('\n').map(line => line.trim().split(/\s+/).map(Number));
if (!Array.isArray(species) || JSON.stringify(headerNames) !== JSON.stringify(species)
    || tableRows?.length !== 2 || !species.includes('O2') || !species.includes('CH4')
    || Number(table.match(/^pressure-pa (\S+)$/m)?.[1]) !== factory.pressure) {
  throw Error('Passive table inventory/conditions differ');
}
for (let i = 0; i < 2; i++) {
  const row = tableRows[i], pure = i === 0 ? 'O2' : 'CH4';
  const temperature = factory.streams[i === 0 ? 'loxinlet' : 'ch4inlet'].temperature;
  if (row.length !== species.length + 3 || !row.every(Number.isFinite)
      || row[0] !== i || row[1] !== temperature || row[2] !== 0
      || species.some((name, index) => row[index + 3] !== (name === pure ? 1 : 0))) {
    throw Error('Passive endpoints, zero source and exact affine composition required');
  }
}
if (!/internalField\s+uniform\s+1\s*;/.test(read(root + '/0/Z'))) {
  throw Error('Original pure-CH4 chamber initialization required');
}
const changes = [];
function change(name, after) {
  const before = read(root + '/' + name);
  changes.push({name, before, after, beforeSha256: hash(before), afterSha256: hash(after)});
}
change('constant/steady.tbl', table);
for (const name of species) {
  const background = name === 'CH4' ? 1 : 0;
  let text = read(root + '/0/' + name);
  text = text.replace(/internalField\s+uniform\s+[^;]+;/,
    'internalField uniform ' + background + ';');
  for (const [patch, value] of [['ch4inlet', background], ['loxinlet', name === 'O2' ? 1 : 0]]) {
    const expression = new RegExp('(' + patch + '\\s*\\{[^}]*value\\s+uniform\\s+)[^;]+;');
    if (!expression.test(text)) throw Error('Missing species inlet: ' + name + '/' + patch);
    text = text.replace(expression, (_, prefix) => prefix + value + ';');
  }
  change('0/' + name, text);
}
let controls = read(root + '/system/controlDict');
if (!controls.includes('fgmEnergyForm absoluteEnthalpy;')
    || !controls.includes('fgmProgressSourceEnabled no;')
    || !controls.includes('fgmRequireHaInitialization yes;')) {
  throw Error('Absolute-Ha initialization and no progress source remain required');
}
const additions = {
  conserveTabulatedDensity: 'yes', projectTabulatedZRoundoff: 'yes',
  writeMixtureFractionBudget: 'yes', writeFgmTiming: 'yes',
  fgmThermoCorrectionPasses: '3', fgmIgnitionTime: '-1',
  realFluidDensityTimeCorrection: 'yes', realFluidInnerThermoCorrectors: 'yes',
  realFluidDifferentialPressure: 'yes', realFluidPressureDensityConstraint: 'enthalpy',
  realFluidPressureThermoRefresh: 'yes'
};
for (const [name, value] of Object.entries(additions)) {
  if (new RegExp('\\b' + name + '\\s').test(controls)) throw Error('Factory flag already set: ' + name);
  controls += '\n' + name + ' ' + value + ';\n';
}
change('system/controlDict', controls);
const record = {
  schema: 'g2-passive-cold-absolute-Ha-control/v1', CFDStartTime_s: 0,
  factoryManifestSha256: hash(read(root + '/direct-g2-input.json')),
  actualTableManifest: manifest, tableSha256: hash(table),
  composition: 'Y_CH4=Z;Y_O2=1-Z;all other species zero',
  energyForm: 'absoluteEnthalpy', chemicalSource: 0,
  thermodynamics: 'Unchanged full53 author SRK thermo; zero inactive species',
  numericalTableModel: 'steadyFlamelet reader reused as passive affine composition lookup',
  interpretation: 'No flamelet calculation, reaction, physical chi solve, paper mean or unique causal proof',
  changes: changes.map(({name, beforeSha256, afterSha256}) => ({name, beforeSha256, afterSha256})),
  scientificAcceptance: false
};
if (apply) {
  if (!process.env.SLURM_JOB_ID) throw Error('Apply requires an admitted Slurm allocation');
  fs.copyFileSync(root + '/constant/steady.tbl', root + '/factory-steady.tbl', fs.constants.COPYFILE_EXCL);
  for (const entry of changes) fs.writeFileSync(root + '/' + entry.name, entry.after);
  fs.writeFileSync(root + '/passive-cold-input.json', JSON.stringify(record, null, 2) + '\n', {flag: 'wx'});
}
console.log(JSON.stringify({readOnly: !apply, ...record}, null, 2));
