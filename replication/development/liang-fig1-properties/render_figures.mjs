#!/usr/bin/env node
/**
 * Build the Liang et al. (2019) Fig. 1 comparison for target `liang-1`.
 *
 * Panel (a): density of O2 at 100 atm, paper model + paper experiments + this work (SRK)
 *            with the PR density as a second equation-of-state variant.
 * Panel (b): thermal conductivity of O2 at 100 atm, paper model + paper experiments +
 *            this work (Ely-Hanley with SRK volumes).
 *
 * The paper figure is a raster, so the "paper" series come from digitize_fig1.py, and no
 * point is invented here.  Geometry (canvas, viewBox, frames, legend) is measured from the
 * embedded raster: pixel -> point with x = 50.733 + 0.24 px, y = 54.012 + 0.24 py, which
 * is the placement rectangle of the 775x1371 px image in the PDF page.
 *
 * Both panels share one canvas and one viewBox, so the composite plot is the two
 * renderPaperComparison() bodies under one root element; nothing is re-projected.
 *
 * Usage:
 *   node render_figures.mjs --probe fig1-probe.csv --digitised digitised.json \
 *        --pr-csv oxygen-properties.csv --out-dir D --source-commit SHA [--run-job-id ID]
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

// ---------------------------------------------------------------------------
// Measured geometry of Liang et al. (2019) Fig. 1 in PDF page points.
// ---------------------------------------------------------------------------
const PX_PER_PT = 1 / 0.24;
const ORIGIN = { x: 50.733, y: 54.012 };
const px = value => ORIGIN.x + value / PX_PER_PT;
const py = value => ORIGIN.y + value / PX_PER_PT;
const FONT = 'Times New Roman,serif';
const FONT_SIZE = 6.4;

// 0.24 pt/px of the embedded raster; the viewBox is 4 pt wider than the frame column so the
// last x tick label and the legend rows stay inside the drawing area.
const CANVAS = { width: 792, height: 1413, viewBox: [50.733, 44.0, 190.0, 339.0] };

const CAL = JSON.parse(readFileSync(
  '/workspace/science/replication/development/liang-properties/figure1-calibration.json', 'utf8'));
const axisValue = (axis, pixel) => CAL.calibration[axis].value_intercept + CAL.calibration[axis].value_per_pixel * pixel;
const axisPixel = (axis, value) => (value - CAL.calibration[axis].value_intercept) / CAL.calibration[axis].value_per_pixel;

const PANELS = [
  {
    id: 'liang-1a-density',
    letter: '(a)',
    letterAt: [px(151), py(518.5)],
    frame: [px(90), py(0), px(750), py(603.5)],
    quantity: 'Density (kg/m3)',
    x: { domain: [axisValue('density_x', 90), axisValue('density_x', 750)], ticks: [],
         major_ticks: [400, 600, 800, 1000] },
    y: { domain: [0, axisValue('density_y', 0)], ticks: [],
         major_ticks: [0, 50, 100, 150, 200] },
    legend: { x: px(430), y: py(88), rowHeight: 7.4, sampleWidth: 9, textGap: 2.9 },
    series: ['a-paper-model', 'a-paper-experiment', 'a-computed-srk', 'a-computed-pr'],
  },
  {
    id: 'liang-1b-conductivity',
    letter: '(b)',
    letterAt: [px(658), py(785)],
    frame: [px(90), py(710), px(750), py(1313)],
    quantity: 'Thermal Conductivity (W/(m K))',
    x: { domain: [axisValue('conductivity_x', 90), axisValue('conductivity_x', 750)], ticks: [],
         major_ticks: [200, 400, 600, 800, 1000] },
    y: { domain: [axisValue('conductivity_y', 1313), axisValue('conductivity_y', 710)],
         ticks: [], major_ticks: [0.02, 0.04, 0.06, 0.08, 0.1, 0.12, 0.14] },
    legend: { x: px(360), y: py(830), rowHeight: 7.4, sampleWidth: 9, textGap: 2.9 },
    series: ['b-paper-model', 'b-paper-experiment', 'b-computed-eh'],
  },
];

function axisLabels(panel) {
  const [left, top, right, bottom] = panel.frame;
  const labels = [];
  for (const tick of panel.x.major_ticks) {
    const x = left + (tick - panel.x.domain[0]) / (panel.x.domain[1] - panel.x.domain[0]) * (right - left);
    const text = String(tick);
    const width = text.length * 0.55 * FONT_SIZE;
    const start = Math.min(x - width / 2, CANVAS.viewBox[0] + CANVAS.viewBox[2] - 0.6 - width);
    labels.push({ x: start, y: bottom + 4.6, text });
  }
  for (const tick of panel.y.major_ticks) {
    const y = bottom - (tick - panel.y.domain[0]) / (panel.y.domain[1] - panel.y.domain[0]) * (bottom - top);
    const text = String(tick);
    labels.push({ x: left - 1.2 - text.length * 0.55 * FONT_SIZE, y: y + 0.35 * FONT_SIZE, text });
  }
  labels.push({ x: (left + right) / 2 - 8.2 * 0.28 * FONT_SIZE, y: bottom + 11.6, text: 'Temperature (K)' });
  labels.push({ x: left, y: top - 2.4, text: panel.quantity });
  labels.push({ x: panel.letterAt[0], y: panel.letterAt[1], text: panel.letter });
  return labels;
}

const recipeFor = panel => ({
  schema: 'forge-paper-style-v1',
  id: panel.id,
  source: {
    sha256: '24163be0124e0fa6cd28ddb1d369b813e64e82bd7446e9f9218a340445aca6fe',
    page: 3,
    method: 'embedded JPEG raster (775x1371 px, sha256 b28ef871c4ad92031d7eeaf24e8a20d0fde6e83f9842c88c0f98ea645068c9ea); '
      + 'axis calibration refitted from ../liang-properties/figure1-calibration.json ticks; '
      + 'frames, tick positions and legend from dark-pixel measurements of the raster; '
      + 'axis text placed by measurement because the raster has no vector glyphs; '
      + 'no grid lines (the published figure has inward minor ticks only)',
  },
  canvas: { ...CANVAS },
  frame: panel.frame,
  x: panel.x,
  y: panel.y,
  gridWidth: 0.4,
  // The published figure has inward major/minor ticks but no grid; the renderer has no
  // minor ticks, so the axis ticks are drawn as measured text labels only and the grid is
  // left empty instead of inventing lines the paper does not have.
  grid: 'none',
  font: { family: FONT, size: FONT_SIZE },
  legend: panel.legend,
  labels: axisLabels(panel),
});

// ---------------------------------------------------------------------------
// Data
// ---------------------------------------------------------------------------
function readCsv(path) {
  const lines = readFileSync(path, 'utf8').split('\n').filter(line => line.trim() && !line.startsWith('#'));
  const head = lines[0].split(',');
  return { head, rows: lines.slice(1).map(line => {
    const cells = line.split(',');
    if (cells.length !== head.length) throw new Error(`Bad CSV row: ${line}`);
    const row = {};
    head.forEach((key, i) => { row[key] = Number(cells[i]); });
    return row;
  }) };
}

const probe = readCsv(need('probe'));
const prCsv = args.get('pr-csv') ? readCsv(args.get('pr-csv')) : null;
const digitised = JSON.parse(readFileSync(need('digitised'), 'utf8'));
const outDir = need('out-dir');
const commit = need('source-commit');
const jobId = args.get('run-job-id') || null;
mkdirSync(outDir, { recursive: true });

const paperProvenance = (panel, part) => ({
  origin: 'Liang, Li & Law (2019), Fig. 1, page 3',
  panel,
  extraction: part === 'model'
    ? 'digitised model curve: Zhang-Suen ridge of the thin-run line mask, triangles and inward ticks rejected by erosion-core shape'
    : 'filled triangle centres from 3x3-erosion cores; no interpolated reference points',
  asset: 'embedded JPEG XObject of the paper PDF',
  embedded_jpeg_sha256: digitised.source.embedded_jpeg_sha256,
  calibration: 'liang-properties/figure1-calibration.json, ticks refitted (worst residual '
    + `${digitised.calibration_max_abs_residual_px.toFixed(2)} px)`,
  gaps: part === 'model'
    ? (panel === 'a' ? digitised.panels.density : digitised.panels.conductivity).model_gaps
      .map(gap => [Number(gap.x_range[0].toFixed(1)), Number(gap.x_range[1].toFixed(1))])
    : [],
});

function paperModelSeries(id, label, key, panel) {
  const segments = digitised.panels[key].model_segments;
  // A 1 px ridge can hold several pixels on the same column where the published curve is
  // nearly vertical; those are averaged at that column and the count is recorded, because a
  // polyline of a single-valued function cannot represent a vertical stroke exactly.
  const raw = segments.flat().map(point => ({ x: point.x, y: point.y }));
  const points = [];
  let merged = 0;
  for (const point of raw) {
    const last = points[points.length - 1];
    if (last && Math.abs(last.x - point.x) < 1e-9) {
      last.y = (last.y + point.y) / 2;
      merged += 1;
    } else {
      if (last && point.x < last.x) throw new Error(`${id}: abscissae not increasing`);
      points.push({ ...point });
    }
  }
  return {
    id, label, origin: 'paper', engine: 'digitised-paper-figure',
    mark: 'line', color: '#000000', lineWidth: 1.2,
    provenance: { ...paperProvenance(panel, 'model'), segments: segments.length,
                  bridged_gaps: paperProvenance(panel, 'model').gaps,
                  same_column_averaged_pixels: merged, ridge_pixels: raw.length },
    points,
  };
}

function paperExperimentSeries(id, label, key, panel) {
  return {
    id, label, origin: 'paper', engine: 'digitised-paper-figure',
    mark: 'points', color: '#000000', lineWidth: 0.7, markerRadius: 1.9, markerWidth: 0.7,
    provenance: paperProvenance(panel, 'experiment'),
    points: digitised.panels[key].experiments.map(point => ({ x: point.x, y: point.y })),
  };
}

const computedSeries = (id, label, column, rows, options) => {
  const points = [];
  for (const row of rows) {
    const x = row.T_K, y = row[column];
    if (!Number.isFinite(x) || !Number.isFinite(y)) throw new Error('Non-finite computed sample');
    if (points.length && !(x > points[points.length - 1].x)) continue;
    points.push({ x, y });
  }
  return {
    id, label, origin: 'computed', engine: options.engine,
    mark: 'line', color: options.color, lineWidth: options.lineWidth,
    ...(options.dash ? { dash: options.dash } : {}),
    provenance: {
      origin: 'this work, same source revision as the committed module',
      model: options.model,
      source_commit: commit,
      csv: basename(need('probe')),
      column,
      samples: points.length,
      ...(jobId ? { scheduler_job_id: jobId } : {}),
    },
    points,
  };
};

const series = [
  paperModelSeries('a-paper-model', 'paper model', 'density', 'a'),
  paperExperimentSeries('a-paper-experiment', 'paper exp.', 'density', 'a'),
  computedSeries('a-computed-srk', 'SRK, this work', 'rho_srk_kg_m3', probe.rows,
    { engine: 'srk', color: '#c0392b', lineWidth: 0.8,
      model: 'SRK EoS (SrkKernel.h) at 100 atm, pure O2' }),
];
if (prCsv) {
  // Peng-Robinson density at the same pressure, from the validated oxygen-properties module.
  const pr = [];
  for (const row of prCsv.rows) {
    if (Math.abs(row.p_Pa - 10132500) > 1) continue;
    if (!Number.isFinite(row.rho_PR_kg_m3)) continue;
    pr.push({ x: row.T_K, y: row.rho_PR_kg_m3 });
  }
  pr.sort((a, b) => a.x - b.x);
  series.push({
    id: 'a-computed-pr', label: 'PR, this work', origin: 'computed', engine: 'peng-robinson',
    mark: 'line', color: '#2e86c1', lineWidth: 0.8, dash: [2, 2],
    provenance: {
      origin: 'this work, oxygen-properties module',
      model: 'uncorrected Peng-Robinson EoS at the same pressure, independent implementation',
      source_commit: commit, csv: basename(args.get('pr-csv')), column: 'rho_PR_kg_m3',
      samples: pr.length,
    },
    points: pr,
  });
}
series.push(
  paperModelSeries('b-paper-model', 'paper model', 'conductivity', 'b'),
  paperExperimentSeries('b-paper-experiment', 'paper exp.', 'conductivity', 'b'),
  computedSeries('b-computed-eh', 'Ely-Hanley, this work', 'lambda_eh_W_mK', probe.rows,
    { engine: 'ely-hanley', color: '#c0392b', lineWidth: 0.8,
      model: 'Ely-Hanley conductivity (ElyHanley.H) with SRK molar volumes, pure O2 at 100 atm' }),
);

const data = {
  schema: 'forge-series-v1',
  target: 'liang-1',
  units: { x: 'K', y: 'kg/m3 in panel (a), W/(m K) in panel (b)' },
  provenance: {
    paper: 'Liang, Li & Law (2019) Fig. 1, digitised from the embedded JPEG raster',
    computed: 'this work, SRK / Ely-Hanley from repository headers at 100 atm',
    panels: 'series ids starting with a- belong to panel (a), b- to panel (b)',
    paper_sha256: digitised.source.paper_sha256,
    digitisation_sha256: sha256(need('digitised')),
    probe_csv_sha256: sha256(need('probe')),
  },
  series,
};
const dataPath = join(outDir, 'liang-1-data.json');
writeFileSync(dataPath, `${JSON.stringify(data, null, 2)}\n`);

// ---------------------------------------------------------------------------
// Render: two panels on one measured canvas, then one composite root element
// ---------------------------------------------------------------------------
const rendered = [];
for (const panel of PANELS) {
  const recipe = recipeFor(panel);
  const panelSeries = panel.series.map(id => {
    const found = series.find(item => item.id === id);
    if (!found) throw new Error(`Panel ${panel.id} references missing series ${id}`);
    return found;
  });
  const out = renderPaperComparison(panelSeries, recipe);
  rendered.push({ panel, recipe, out });
  writeFileSync(join(outDir, `${panel.id}-recipe.json`), `${JSON.stringify(recipe, null, 2)}\n`);
  writeFileSync(join(outDir, `${panel.id}-render-receipt.json`), `${JSON.stringify(out.receipt, null, 2)}\n`);
}

const inner = (svg, keepBackground) => {
  const body = svg.replace(/^<svg[^>]*>/, '').replace(/<\/svg>$/, '').replace(/<title>.*?<\/title>/, '');
  return keepBackground ? body : body.replace(/<rect x="[^"]*" y="[^"]*" width="[^"]*" height="[^"]*" fill="#ffffff"\/>/, '');
};
const [vx, vy, vw, vh] = CANVAS.viewBox;
const composite = '<svg xmlns="http://www.w3.org/2000/svg" '
  + `width="${CANVAS.width}" height="${CANVAS.height}" viewBox="${vx} ${vy} ${vw} ${vh}" role="img">`
  + '<title>liang-1: Liang, Li and Law (2019) Fig. 1, O2 at 100 atm</title>'
  + inner(rendered[0].out.svg, true)
  + inner(rendered[1].out.svg, false)
  + '</svg>';
const svgPath = join(outDir, 'liang-1.svg');
writeFileSync(svgPath, composite);

const recipeComposite = {
  schema: 'forge-paper-style-v1-composite',
  id: 'liang-1',
  source_sha256: '24163be0124e0fa6cd28ddb1d369b813e64e82bd7446e9f9218a340445aca6fe',
  composition: 'one root <svg> whose children are the unmodified bodies of the two '
    + 'renderPaperComparison() outputs; both panels use the same canvas and viewBox, so no '
    + 'coordinate transform is applied and the second body keeps no background rect',
  panels: rendered.map(item => item.recipe),
};
const recipePath = join(outDir, 'liang-1-recipe.json');
writeFileSync(recipePath, `${JSON.stringify(recipeComposite, null, 2)}\n`);

const receipt = {
  schema: 'forge-figure-build-v1',
  target: 'liang-1',
  source_commit: commit,
  ...(jobId ? { scheduler_job_id: jobId } : {}),
  data: basename(dataPath), data_sha256: sha256(dataPath),
  plot: basename(svgPath), plot_sha256: sha256(svgPath),
  recipe: basename(recipePath), recipe_sha256: sha256(recipePath),
  panels: rendered.map(({ panel, out }) => ({
    id: panel.id,
    series: out.receipt.series,
    svg_sha256: createHash('sha256').update(out.svg).digest('hex'),
  })),
  font_availability: 'not_checked_by_renderer',
};
writeFileSync(join(outDir, 'figure-build.json'), `${JSON.stringify(receipt, null, 2)}\n`);
for (const item of series) console.log(`${item.id}: ${item.points.length} points`);
console.log(`wrote ${svgPath} (${composite.length} bytes)`);
