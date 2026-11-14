import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {loadSteadyTable} from '../steady-flamelet/input.mjs';

const [original, metadataPath, option, output] = process.argv.slice(2);
if (!original || !metadataPath || ![undefined, '--out'].includes(option)
    || (option === '--out' && !output)) {
  throw Error('Use ORIGINAL_TABLE_DIR PHASE_JSON [--out NEW_DIRECTORY]');
}
const input = await loadSteadyTable(original, metadataPath);
const metadataRaw = await fs.readFile(metadataPath);
const hash = value => createHash('sha256').update(value).digest('hex');
const names = input.metadata.species.map(species => species.name);
const text = input.raw.toString();
const header = text.split(/^points\s+\d+\s*$/m)[0];
if (!header || !header.startsWith('FORGE_STEADY_FLAMELET 1\n')) {
  throw Error('Expected the verified original table header');
}
const points = [0, 1].map(z => {
  const state = input.lookup(z);
  const y = names.map(name => name === (z === 0 ? 'O2' : 'CH4') ? 1 : 0);
  return {z, temperature: state.temperature, source: 0, y};
});
const table = header + 'points 2\ndata\n'
  + points.map(row => [row.z, row.temperature, row.source, ...row.y].join(' ')).join('\n')
  + '\nend\n';
const manifest = {
  schema: 'analytic-passive-cold-table/v1',
  originalHeaderTableSha256: hash(input.raw), metadataSha256: hash(metadataRaw),
  mechanismSha256: input.metadata.mechanismSha256, tableSha256: hash(table),
  species: names, composition: 'Y_CH4=Z;Y_O2=1-Z;all other species zero',
  chemicalSource: 'identically zero', nodes: 2,
  originalPhysicalCompositionUsed: false, originalPhysicalProfileModified: false,
  chi: {value: input.chi, definition: input.chiDefinition,
    interpretation: 'Copied format/condition label; inactive in passive lookup, no dissipation solve'},
  temperaturePolicy: 'Endpoints retained; interpolated T diagnostic only, CFD uses runtime SRK Ha inversion',
  scientificAcceptance: false
};
if (output) {
  await fs.mkdir(output);
  await fs.writeFile(output + '/passive.tbl', table);
  await fs.writeFile(output + '/manifest.json', JSON.stringify(manifest, null, 2) + '\n');
}
console.log(JSON.stringify({readOnly: !output, ...manifest}, null, 2));
