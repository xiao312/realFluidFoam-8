#!/usr/bin/env node
/**
 * Build the paper-comparison figures for Mueller & Pfitzner (2015) Fig. 1(a)
 * (O2 density) and Fig. 1(b) (O2 cp) from the raw sweep produced by
 * run_properties.py.
 *
 * Nothing is fitted, smoothed or interpolated: the computed series are the raw
 * CSV samples, the reference series are the campaign library's vector
 * extraction of the published curves, and the SVG is produced only by
 * renderPaperComparison() from the frozen Forge renderer.
 *
 * Usage:
 *   node render_figures.mjs --density-csv F --cp-csv F --reference-dir D \
 *        --out-dir D --source-commit SHA [--run-job-id ID]
 */
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { basename, join } from 'node:path';
import { renderPaperComparison } from '/forge/plots/paper-style.mjs';

const args = new Map();
for (let i = 2; i < process.argv.length; i += 2) {
  const key = process.argv[i];
  if (!key.startsWith('--')) throw new Error(`Unexpected argument ${key}`);
  args.set(key.slice(2), process.argv[i + 1]);
}
const need = key => {
  const value = args.get(key);
  if (!value) throw new Error(`Missing --${key}`);
  return value;
};
const sha256 = path => createHash('sha256').update(readFileSync(path)).digest('hex');

const TARGETS = [
  {
    target: 'muller2015-fig1a-density',
    recipe: 'muller2015-fig1a-density-props-r2-recipe.json',
    series: 'muller2015-fig1a-density-props-r2-series.json',
    paper: 'muller2015-fig1a-density-paper.png',
    caption: 'muller2015-fig1-original-caption.png',
    csv: need('density-csv'),
    units: { x: 'K', y: 'kg/m3' },
    computed: [
      { id: 'computed-vta', label: 'this work: PR-VTA', column: 'rho_VTA_kg_m3',
        color: '#c0392b', lineWidth: 0.8, mark: 'line',
        model: 'PR EoS + Abudour volume translation (paper Eqs. 8-13)' },
      { id: 'computed-pr', label: 'this work: PR', column: 'rho_PR_kg_m3',
        color: '#2e86c1', lineWidth: 0.8, mark: 'line', dash: [2, 2],
        model: 'uncorrected PR EoS (paper Eq. 8)' },
    ],
    paperSeries: [
      // Published geometry measured from the PDF graphics state: both curves are
      // stroked at 0.59776 pt, the dashed one carries the PDF's own dash array
      // [2.98883 2.98883], and the NIST rings are 4.154 pt across (11.5 px at the
      // 200 dpi reference raster) stroked at 0.59776 pt, i.e. radius 2.077 pt.
      { id: 'paper-vta', source: 'paper-vta', label: 'paper: PR-VTA',
        color: '#000000', lineWidth: 0.59776, mark: 'line' },
      { id: 'paper-pr', source: 'paper-pr', label: 'paper: PR',
        color: '#000000', lineWidth: 0.59776, mark: 'line', dash: [2.98883, 2.98883] },
      { id: 'paper-nist', source: 'paper-nist', label: 'paper: NIST',
        color: '#000000', lineWidth: 0.59776, mark: 'points',
        markerRadius: 2.077, markerWidth: 0.59776 },
    ],
  },
  {
    target: 'muller2015-fig1b-cp',
    recipe: 'muller2015-fig1b-cp-props-r2-recipe.json',
    series: 'muller2015-fig1b-cp-props-r2-series.json',
    paper: 'muller2015-fig1b-cp-paper.png',
    caption: 'muller2015-fig1-original-caption.png',
    csv: need('cp-csv'),
    units: { x: 'K', y: 'J/(kg K)' },
    computed: [
      { id: 'computed-cp', label: 'this work: cp (PR)', column: 'cp_PR_J_kgK',
        color: '#c0392b', lineWidth: 0.8, mark: 'line',
        model: 'PR EoS departure functions, uncorrected PR volume (paper Sec. 2.2)' },
    ],
    paperSeries: [
      // the paper draws the Fig. 1(b) PR cp curve dashed, as in Fig. 1(a)
      { id: 'paper-pr', source: 'paper-pr', label: 'paper: cp (PR)',
        color: '#000000', lineWidth: 0.59776, mark: 'line',
        dash: [2.98883, 2.98883] },
      { id: 'paper-nist', source: 'paper-nist', label: 'paper: NIST',
        color: '#000000', lineWidth: 0.59776, mark: 'points',
        markerRadius: 2.077, markerWidth: 0.59776 },
    ],
  },
];

function readCsv(path) {
  const lines = readFileSync(path, 'utf8').trim().split('\n');
  const head = lines[0].split(',');
  return { head, rows: lines.slice(1).map(line => {
    const cells = line.split(',');
    if (cells.length !== head.length) throw new Error(`Bad CSV row: ${line}`);
    const row = {};
    head.forEach((key, i) => { row[key] = Number(cells[i]); });
    return row;
  }) };
}

const refDir = need('reference-dir');
const outDir = need('out-dir');
const commit = need('source-commit');
const jobId = args.get('run-job-id') || null;
mkdirSync(outDir, { recursive: true });

const report = { schema: 'forge-figure-build-v1', source_commit: commit, figures: [] };

for (const spec of TARGETS) {
  const { rows, head } = readCsv(spec.csv);
  for (const c of spec.computed) {
    if (!head.includes(c.column)) throw new Error(`Column ${c.column} absent from ${spec.csv}`);
  }
  const refPath = join(refDir, spec.series);
  const ref = JSON.parse(readFileSync(refPath, 'utf8'));
  const refById = new Map(ref.series.map(s => [s.id, s]));

  const paperProvenance = s => ({
    origin: 'Mueller & Pfitzner (2015), Fig. 1, page 3',
    extraction: 'vector plot-path extraction, campaign library asset',
    asset: spec.series,
    asset_series_id: s.id,
    note: s.note || (s.id === 'paper-nist'
      ? 'marker centres; no interpolated reference points'
      : 'curve samples along the published vector path'),
  });

  // Draw order = legend order: the published curves first, then the computed
  // series (thinner, so the reference stroke stays visible where they agree),
  // then the published markers on top - the same order as the paper's caption.
  const series = [];
  for (const p of spec.paperSeries.filter(p => p.mark !== 'points')) {
    const src = refById.get(p.source);
    if (!src) throw new Error(`Reference series ${p.source} missing`);
    series.push({
      id: p.id, label: p.label, origin: 'paper',
      provenance: paperProvenance(src),
      mark: p.mark, color: p.color, lineWidth: p.lineWidth,
      ...(p.dash ? { dash: p.dash } : {}),
      ...(p.mark !== 'line' ? { markerRadius: p.markerRadius, markerWidth: p.markerWidth } : {}),
      points: src.points.map(q => ({ x: q.x, y: q.y })),
    });
  }
  for (const c of spec.computed) {
    const seen = new Set();
    const points = [];
    for (const row of rows) {
      const x = row.T_K;
      const y = row[c.column];
      if (!Number.isFinite(x) || !Number.isFinite(y)) throw new Error('Non-finite sample');
      if (seen.has(x)) continue;
      seen.add(x);
      points.push({ x, y });
    }
    series.push({
      id: c.id, label: c.label, origin: 'computed',
      provenance: {
        origin: 'this work, same source revision as the committed module',
        model: c.model,
        source_commit: commit,
        csv: basename(spec.csv),
        column: c.column,
        samples: points.length,
        ...(jobId ? { scheduler_job_id: jobId } : {}),
      },
      mark: c.mark, color: c.color, lineWidth: c.lineWidth,
      ...(c.dash ? { dash: c.dash } : {}),
      points,
    });
  }
  for (const p of spec.paperSeries.filter(p => p.mark === 'points')) {
    const src = refById.get(p.source);
    if (!src) throw new Error(`Reference series ${p.source} missing`);
    series.push({
      id: p.id, label: p.label, origin: 'paper',
      provenance: paperProvenance(src),
      mark: p.mark, color: p.color, lineWidth: p.lineWidth,
      markerRadius: p.markerRadius, markerWidth: p.markerWidth,
      points: src.points.map(q => ({ x: q.x, y: q.y })),
    });
  }

  const data = {
    schema: 'forge-series-v1',
    target: spec.target,
    units: spec.units,
    series,
  };
  const dataPath = join(outDir, `${spec.target}-data.json`);
  writeFileSync(dataPath, `${JSON.stringify(data, null, 2)}\n`);

  const recipe = JSON.parse(readFileSync(join(refDir, spec.recipe), 'utf8'));
  const rendered = renderPaperComparison(series, recipe);
  const svgPath = join(outDir, `${spec.target}.svg`);
  writeFileSync(svgPath, rendered.svg);

  const receiptPath = join(outDir, `${spec.target}-render-receipt.json`);
  writeFileSync(receiptPath, `${JSON.stringify(rendered.receipt, null, 2)}\n`);

  report.figures.push({
    target: spec.target,
    data: basename(dataPath), data_sha256: sha256(dataPath),
    svg: basename(svgPath), svg_sha256: sha256(svgPath),
    recipe: spec.recipe, recipe_sha256: sha256(join(refDir, spec.recipe)),
    reference_series_sha256: sha256(refPath),
    paper_figure: spec.paper, paper_figure_sha256: sha256(join(refDir, spec.paper)),
    paper_caption: spec.caption, paper_caption_sha256: sha256(join(refDir, spec.caption)),
    render_receipt: rendered.receipt,
  });
  console.log(`${spec.target}: ${series.map(s => `${s.id}(${s.points.length})`).join(' ')} -> ${svgPath}`);
}

writeFileSync(join(outDir, 'figure-build.json'), `${JSON.stringify(report, null, 2)}\n`);
console.log(`wrote ${join(outDir, 'figure-build.json')}`);
