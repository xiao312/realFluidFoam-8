import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const rootIndex = process.argv.indexOf('--root'), baseIndex = process.argv.indexOf('--base');
if (rootIndex < 0 || baseIndex < 0) throw Error('Pass --root evidence-directory and --base HTTP-origin/');
const root = path.resolve(process.argv[rootIndex + 1]);
const base = new URL(process.argv[baseIndex + 1]);
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const parseModule = text => JSON.parse(text.replace(/^export default /, '').replace(/;\s*$/, ''));
const get = async name => {
  const response = await fetch(new URL(name, base));
  if (!response.ok) throw Error(`HTTP ${response.status}: ${name}`);
  return Buffer.from(await response.arrayBuffer());
};
const backups = fs.readdirSync(root).filter(n => n.startsWith('before-import-')).sort();
if (!backups.length) throw Error('No original catalogue backup');
const old = parseModule(fs.readFileSync(path.join(root, backups[0], 'data.js'), 'utf8'));
const html = (await get('index.html')).toString();
const entry = html.match(/src="(argos-[a-f0-9]+\.js)"/)[1];
const bundle = (await get(entry)).toString();
const module = bundle.match(/from"\.\/(data-[a-f0-9]+\.js)"/)[1];
const data = parseModule((await get(module)).toString());
const targets = JSON.parse(fs.readFileSync(path.join(root, 'selected-targets.json')));
if (data.figures.length !== old.figures.length + 4 || data.papers.length !== old.papers.length) throw Error('Catalogue count mismatch');
if (!data.figures.every(f => f.caption)) throw Error('Missing caption');
const oldIds = new Set(old.figures.map(f => f.id));
if (JSON.stringify(data.figures.filter(f => oldIds.has(f.id)).map(f => f.id)) !== JSON.stringify(old.figures.map(f => f.id))) throw Error('Existing target order changed');
for (const previous of old.figures) {
  const current = data.figures.find(f => f.id === previous.id);
  if (!current || current.caption !== previous.caption || current.result_image !== previous.result_image) throw Error('Existing comparison changed: ' + previous.id);
}
const checks = [];
async function verify(file, expected) {
  if (hash(await get(file)) !== expected) throw Error('Hash mismatch: ' + file);
  checks.push(file);
}
for (const t of targets) {
  const f = data.figures.find(f => f.id === t.id);
  if (!f || f.development_state.human_acceptance !== 'not_assessed' || f.evidence_binding.scientificAcceptance) throw Error('Missing target or false acceptance');
  if (!f.plot_plan || !f.conditions_registered || !f.original_caption.text) throw Error('Incomplete target specification');
  if (f.statistic !== 'instantaneous' && !f.views[0].label.includes('mean pending')) throw Error('Instantaneous preview presented as mean');
  await verify(f.paper_image, f.paper_image_sha256);
  await verify(f.original_caption.image, f.original_caption.image_sha256);
  await verify(f.result_image, f.result_image_sha256);
  await verify(f.data, f.data_sha256);
  const evidence = JSON.parse((await get(f.data)).toString());
  if (evidence.newCFDExecution || evidence.scientificAcceptance) throw Error('Wrong execution or science claim');
  for (const a of evidence.rawAssets) await verify(a.file, a.sha256);
}
const receipt = { at: new Date().toISOString(), targets: data.figures.length, papers: data.papers.length,
  oldTargetsPreserved: oldIds.size, newTargets: targets.map(t => t.id), checks,
  existingCaptionsAndPrimaryImagesPreserved: true, scientificAcceptance: false };
fs.writeFileSync(path.join(root, 'served-import-check.json'), JSON.stringify(receipt, null, 2) + '\n');
console.log(JSON.stringify({ targets: receipt.targets, papers: receipt.papers, oldTargetsPreserved: oldIds.size, assetsChecked: checks.length }));
