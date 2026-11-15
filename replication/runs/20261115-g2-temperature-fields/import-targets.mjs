import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

// Explicit local roots only. This importer cannot submit jobs or publish remotely.
function argument(name) {
  const i = process.argv.indexOf(name);
  if (i < 0 || !process.argv[i + 1]) throw Error(`Required argument: ${name}`);
  return path.resolve(process.argv[i + 1]);
}
const root = argument('--root');
const site = argument('--site');
const catalog = argument('--catalog');
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const read = file => fs.readFileSync(file, 'utf8');
const json = file => JSON.parse(read(file));
const data = JSON.parse(read(path.join(site, 'data.js')).replace(/^export default /, '').replace(/;\s*$/, ''));
const central = json(catalog);
const targets = json(path.join(root, 'selected-targets.json'));
const field = json(path.join(root, 'temperature-field-evidence.json'));
const oldIds = data.figures.map(f => f.id);
if (new Set(oldIds).size !== oldIds.length || targets.length !== 4) throw Error('Catalogue identity mismatch');
if (!field.cases.every(c => c.mappedCellsExactlyOnce && c.time_s === .005 && c.CFDStartTime_s === 0)) throw Error('Unqualified field mapping');
if (field.scientificAcceptance) throw Error('Renderer cannot approve science');
const additions = targets.filter(t => !oldIds.includes(t.id));
if (!process.argv.includes('--apply')) {
  console.log(JSON.stringify({ readOnly: true, existing: oldIds.length, additions: additions.map(t => t.id), total: oldIds.length + additions.length }));
  process.exit(0);
}

const backup = path.join(root, 'before-import-' + new Date().toISOString().replace(/[:.]/g, '-'));
fs.mkdirSync(backup);
for (const name of ['data.js', 'index.html', 'site-manifest.json']) fs.copyFileSync(path.join(site, name), path.join(backup, name));
fs.copyFileSync(catalog, path.join(backup, 'catalog.json'));
const assets = [];
function asset(name) {
  const source = path.resolve(root, name);
  if (!source.startsWith(root + path.sep)) throw Error('Input escapes evidence root');
  const bytes = fs.readFileSync(source), hash = sha(bytes);
  const stem = path.basename(name, path.extname(name)).replace(/[^a-zA-Z0-9_-]/g, '-');
  const file = `assets/${stem}-${hash.slice(0, 12)}${path.extname(name)}`;
  fs.writeFileSync(path.join(site, file), bytes); assets.push(file);
  return { file, sha256: hash };
}
const evidence = structuredClone(field);
evidence.referenceTargets = targets;
evidence.newCFDExecution = false;
evidence.rawAssets = ['schmitt-collection.json', 'cavalieri-collection.json', 'selected-targets.json',
  'schmitt-selected-mesh-T.tar.gz', 'cavalieri-selected-mesh-T.tar.gz'].map(asset);
fs.writeFileSync(path.join(root, 'site-field-evidence.json'), JSON.stringify(evidence, null, 2) + '\n');
const ev = asset('site-field-evidence.json');
const images = Object.fromEntries(['schmitt', 'cavalieri'].map(c => [c, asset(c + '-temperature-nearfield-5ms.png')]));
const combined = asset('g2-temperature-fields-5ms.png');
const notes = {
  muller2015: 'Current Schmitt-settings run, not a separately matched Müller case. Five-millisecond instantaneous preview; PR-VTA, turbulence and flamelet differences remain.',
  cavalieri2025: 'Current Cavalieri-settings run at 5 ms. Actual cell temperatures, no smoothing. Upper TF/G2 paper case only. LES/PDF and developed-statistics differences remain.',
  degiorgi2014: 'Current Cavalieri-settings diagnostic, not an EDC/RANS replication. Experimental backlight shows morphology, not calibrated temperature. A matched mean is unavailable.'
};
for (const [index, t] of targets.entries()) {
  const paper = data.papers.find(p => p.id === t.paper);
  if (!paper || paper.pdf_sha256 !== t.source_pdf_sha256) throw Error('Paper hash mismatch');
  const original = asset(t.paper_image), caption = asset(t.original_caption.image);
  if (original.sha256 !== t.paper_image_sha256 || caption.sha256 !== t.original_caption.image_sha256) throw Error('Crop hash mismatch');
  const isMean = t.statistic !== 'instantaneous';
  const note = notes[t.paper] + (isMean ? ' This preview is instantaneous; the target requires a developed mean. No mean-field acceptance is claimed.' : ' A snapshot cannot establish statistical agreement.');
  const im = images[t.currentCase];
  const view = { id: 'current-5ms-temperature-field', label: isMean ? '5 ms instantaneous preview — mean pending' : 'Current 5 ms instantaneous field', image: im.file, image_sha256: im.sha256, data: ev.file, data_sha256: ev.sha256, note };
  const target = { ...t, paper_image: original.file, original_caption: { ...t.original_caption, text: t.caption, image: caption.file },
    status: 'review', priority: 'normal', order: t.paper === 'degiorgi2014' ? 129 : 63 + index,
    topic: 'mascotte', stage: t.paper === 'degiorgi2014' ? 'context' : 'statistics', role: 'temperature-field', selected: true,
    conditions: `${t.conditions_registered.p_MPa} MPa; O2 85 K / 44.4 g/s; CH4 288 K / 143.1 g/s; ${t.statistic}.`,
    dependencies: ['schmitt2020-fig-6', t.currentCase === 'cavalieri' ? 'cavalieri2025-fig-6' : 'schmitt2020-fig-21'],
    diagnosticAllowedBeforeDependenciesPass: true, rights: paper.rights, question: t.title, plot_plan: t.plot_spec, note,
    result_image: im.file, result_image_sha256: im.sha256, data: ev.file, data_sha256: ev.sha256, views: [view],
    development_state: { numerical: 'needs_work', agent_review: 'not_assessed', human_acceptance: 'not_assessed' },
    evidence_binding: { job: field.cases.find(c => c.case === t.currentCase).sourceJob, CFDStartTime_s: 0, sampleTime_s: .005,
      solverSource: 'bcff75687fe33bc74e86886c0684bae2edb072d9', statistic: 'instantaneous', developedMeansAvailable: false, scientificAcceptance: false } };
  for (const list of [data.figures, central.targets]) {
    const i = list.findIndex(f => f.id === t.id);
    if (i < 0) list.push(structuredClone(target)); else list[i] = structuredClone(target);
  }
}
// Add field inspection without replacing established line-profile comparisons.
for (const list of [data.figures, central.targets]) for (const id of ['schmitt2020-fig-21', 'cavalieri2025-fig-6', 'sharma2023-fig-4b']) {
  const f = list.find(f => f.id === id); if (!f) throw Error('Existing G2 target missing');
  const im = images[id.startsWith('schmitt') ? 'schmitt' : 'cavalieri'];
  const view = { id: 'current-5ms-temperature-field', label: 'Full temperature field — 5 ms instantaneous', image: im.file, image_sha256: im.sha256,
    data: ev.file, data_sha256: ev.sha256, note: 'Actual finite-volume cell values on the retained mesh. Off-axis global maxima differ from near-axis samples. No smoothing or new CFD.' };
  f.views = [...(f.views ?? []).filter(v => v.id !== view.id), view];
}
// Insert new entries into their stage without reordering any existing target.
const newIds = new Set(targets.map(t => t.id));
const orderedNew = data.figures.filter(f => newIds.has(f.id)).sort((a, b) => a.order - b.order);
data.figures = data.figures.filter(f => !newIds.has(f.id));
for (const f of orderedNew) {
  const sameStage = data.figures.map((v, j) => ({ v, j })).filter(x => x.v.stage === f.stage && x.v.topic === f.topic);
  const next = sameStage.find(x => x.v.order > f.order);
  const index = next ? next.j : sameStage.length ? sameStage.at(-1).j + 1 : data.figures.length;
  data.figures.splice(index, 0, f);
}
central.targets = data.figures.map(f => central.targets.find(t => t.id === f.id));
central.target_ids = data.figures.map(f => f.id);
central.temperature_field_extension = { at: new Date().toISOString(), authority: 'Owner requested published G2 temperature fields', targets: targets.map(t => t.id), experimentalBoundary: 'Existing Singla emission/backlight is morphology, not thermometry.' };
if (!oldIds.every(id => data.figures.some(f => f.id === id)) || !data.figures.every(f => f.caption)) throw Error('Existing catalogue/caption lost');
fs.writeFileSync(catalog, JSON.stringify(central, null, 2) + '\n');
data.central_ladder.target_ids = central.target_ids;
data.central_ladder.summary.registered = data.figures.length;
data.central_ladder.summary.temperature_field_previews = 4;
data.central_ladder.catalog_sha256 = sha(fs.readFileSync(catalog));
data.temperature_field_extension = { ...central.temperature_field_extension, combinedImage: combined.file };
data.captured_at = new Date().toISOString(); delete data.snapshot_sha256;
data.snapshot_sha256 = sha(JSON.stringify(data));
const serialized = 'export default ' + JSON.stringify(data).replaceAll('<', '\\u003c') + ';\n';
const module = 'data-' + data.snapshot_sha256.slice(0, 16) + '.js';
fs.writeFileSync(path.join(site, 'data.js'), serialized); fs.writeFileSync(path.join(site, module), serialized);
const bundle = read(path.join(site, 'argos.js')).replace('from"./data.js"', 'from"./' + module + '"');
if (!bundle.includes(module)) throw Error('UI module binding failed');
const entry = 'argos-' + sha(bundle).slice(0, 16) + '.js';
fs.writeFileSync(path.join(site, entry), bundle);
fs.writeFileSync(path.join(site, 'index.html'), read(path.join(site, 'index.html')).replace(/src="argos(?:-[a-f0-9]+)?\.js"/, 'src="' + entry + '"'));
const manifest = json(path.join(site, 'site-manifest.json'));
for (const name of [...assets, 'data.js', module, entry, 'index.html']) manifest.files[name] = sha(fs.readFileSync(path.join(site, name)));
manifest.snapshot_sha256 = data.snapshot_sha256;
fs.writeFileSync(path.join(site, 'site-manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
fs.writeFileSync(path.join(root, 'import-receipt.json'), JSON.stringify({ at: new Date().toISOString(), backup, oldIds, addedIds: additions.map(t => t.id), totalTargets: data.figures.length, papers: data.papers.length, assets, scientificAcceptance: false }, null, 2) + '\n');
console.log(JSON.stringify({ backup, targets: data.figures.length, papers: data.papers.length, assets: assets.length, scientificAcceptance: false }));
