#!/usr/bin/env node
/**
 * Build the Cavalieri et al. (2025) Fig. 1 comparison for target `cavalieri2025-fig-1`.
 *
 * Four panels share one canvas that is the PDF form's own coordinate system, so the
 * composite plot is the four renderPaperComparison() bodies under one root element and no
 * coordinate transform is applied to the panels.  All panel geometry (frames, axis
 * domains, tick positions, curve widths, dash array, marker sizes, the one legend box) is
 * measured from the PDF vector art by digitise_fig1.py; nothing here is guessed.
 *
 * The published axis text is glyph outlines (the form has no Tj/TJ operator at all), so
 * the tick and axis labels are re-typeset here at the measured glyph height.  That is a
 * declared difference from the paper, not a measurement: `labels` in each recipe carries
 * the positions derived from the measured tick positions.
 *
 * Usage:
 *   node render_figures.mjs --vector figure1-vector.json --out-dir D --source-commit SHA \
 *        [--sweep sweep.json] [--run-job-id ID]
 *
 * --sweep is optional: without it the figure carries only the published curves and markers
 * (a geometry/fidelity check); with it the computed series are added.
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

const vectorPath = need('vector');
const vector = JSON.parse(readFileSync(vectorPath, 'utf8'));
const outDir = need('out-dir');
const commit = need('source-commit');
const jobId = args.get('run-job-id') || null;
const sweepPath = args.get('sweep') || null;
mkdirSync(outDir, { recursive: true });

// ---------------------------------------------------------------------------
// Measured canvas.  The form's BBox is the drawing area; +2 pt on each side keeps the
// outermost tick labels inside the export.
// ---------------------------------------------------------------------------
const FORM = vector.form.bbox;                 // [0, 0, 360, 276.108], y up
const PAD = 2.0;
// The published figure has one legend inside panel (a), on top of the density curve.  The
// shared renderer draws legend rows for the series of each rendered panel, so the legend is
// moved into a strip added below the paper's own drawing area: the measured panels keep
// their exact positions (no re-projection) and the added strip is declared here.
const LEGEND_STRIP_PT = 60;
// The panel titles are re-typeset above the frames of (a) and (b), which sit only 2.65 pt
// below the top of the form, so the canvas is extended upward instead of clipping them.
const TITLE_PAD_PT = 12;
const CANVAS_PT = {
  x: FORM[0] - PAD, y: FORM[1] - PAD - TITLE_PAD_PT,
  width: FORM[2] - FORM[0] + 2 * PAD,
  height: FORM[3] - FORM[1] + 2 * PAD + TITLE_PAD_PT + LEGEND_STRIP_PT,
};
const yDown = y => FORM[3] - y;                // PDF y-up -> SVG y-down
const CANVAS = {
  width: Math.round(CANVAS_PT.width * 2),
  height: Math.round(CANVAS_PT.height * 2),
  viewBox: [CANVAS_PT.x, CANVAS_PT.y, CANVAS_PT.width, CANVAS_PT.height],
};
const FONT = 'Times New Roman,serif';
// The axis glyphs in the form are 4.5-4.9 pt tall; a Times digit is about 0.7 em, so the
// measured type size is 6.5 pt.  Declared as re-typeset, not extracted.
const FONT_SIZE = 6.5;

const QUANTITY = {
  a: { label: 'Density (kg/m3)', letter: '(a)' },
  b: { label: 'cp (kJ/(kg K))', letter: '(b)' },
  // Panel (c) is plotted on the paper's own axis: the published ticks run 0, 0.5, 1, 1.5, 2
  // and the published axis label carries the multiplier, mu [Pa s] * 10^-4.  The plotted
  // numbers are therefore mu * 1e4, and the re-typeset title must say so; without it the
  // axis reads as Pa s and every value is off by four orders of magnitude.
  c: { label: 'Viscosity (1e-4 Pa s)', letter: '(c)' },
  d: { label: 'Conductivity (W/(m K))', letter: '(d)' },
};
const SERIES_KEY = { a: 'rho', b: 'cp', c: 'mu', d: 'kappa' };

// measured marker ring: outer circles 2.856-2.859 pt, inner discs 2.111-2.114 pt
const MARKER = { radius: 1.4285, width: 0.3715 };

// Legend band: the published legend sits inside panel (a), on top of the density curve,
// so it is moved into a strip added below the paper's own drawing area (which ends at
// SVG y 278.108).  Rows are drawn as y + i*rowHeight, and the renderer sets the legend
// type at FONT_SIZE, so rowHeight must exceed the type size or the row baselines collide.
// The six entries used here therefore occupy y 284.5 to 327.5 and the strip is 60 pt tall
// so the last row's descenders stay inside the viewBox.
const LEGEND_TOP = 284.5;
const LEGEND_ROW = 8.6;
const LEGEND_X = 22.0;

function panelGeometry(key) {
  const panel = vector.panels[key];
  const [left, topPdf, right, bottomPdf] = panel.frame;
  const [x0, x1] = panel.xlim;
  const [y0, y1] = panel.ylim;
  return {
    key, panel,
    frame: [left, yDown(bottomPdf), right, yDown(topPdf)],
    x: { domain: [x0, x1], ticks: [], major_ticks: panel.x_tick_positions.map((pt, index) => {
      void index;
      return x0 + (pt - left) / (right - left) * (x1 - x0);
    }) },
    y: { domain: [y0, y1], ticks: [], major_ticks: panel.y_tick_positions.map(pt => {
      return y0 + (pt - topPdf) / (bottomPdf - topPdf) * (y1 - y0);
    }) },
  };
}

const fmt = value => {
  if (Math.abs(value) >= 100) return String(Math.round(value));
  const text = String(Number(value.toPrecision(3)));
  return text;
};

// Extracted tick positions come from the vector art and can sit a fraction of a point
// outside the frame, which would otherwise print a spurious label such as -0.000492 next
// to the real 0 tick.  Ticks are therefore clamped onto the declared limits and
// de-duplicated before they are labelled.
function cleanTicks(values, lo, hi) {
  const span = hi - lo;
  const out = [];
  for (const value of values) {
    if (value < lo - 1e-3 * span || value > hi + 1e-3 * span) continue;
    const snapped = Math.min(hi, Math.max(lo, value));
    if (out.some(existing => Math.abs(existing - snapped) < 1e-3 * span)) continue;
    out.push(snapped);
  }
  return out;
}

function axisLabels(geometry) {
  const { panel } = geometry;
  const [left, top, right, bottom] = geometry.frame;
  const labels = [];
  const dx = (right - left) / (panel.xlim[1] - panel.xlim[0]);
  const dy = (bottom - top) / (panel.ylim[1] - panel.ylim[0]);
  for (const tick of cleanTicks(geometry.x.major_ticks, panel.xlim[0], panel.xlim[1])) {
    const x = left + (tick - panel.xlim[0]) * dx;
    const text = fmt(tick);
    labels.push({ x: x - text.length * 0.28 * FONT_SIZE, y: bottom + 6.8, text });
  }
  for (const tick of cleanTicks(geometry.y.major_ticks, panel.ylim[0], panel.ylim[1])) {
    const y = bottom - (tick - panel.ylim[0]) * dy;
    const text = fmt(tick);
    labels.push({ x: left - 1.1 - text.length * 0.55 * FONT_SIZE, y: y + 0.35 * FONT_SIZE, text });
  }
  const { label, letter } = QUANTITY[geometry.key];
  labels.push({ x: (left + right) / 2 - 9.0 * 0.28 * FONT_SIZE, y: bottom + 14.6, text: 'Temperature (K)' });
  // The published figure prints the panel letter BENEATH the x-axis title, centred on its
  // frame; the earlier revision of this renderer put it above the frame at the left edge.
  // The letter is measurably placed here now (x = frame centre, y = bottom + 22.4 pt, which
  // clears the 6.5 pt x-axis title at bottom + 14.6 pt by 7.8 pt).
  labels.push({ x: (left + right) / 2 - letter.length * 0.28 * FONT_SIZE, y: bottom + 22.4,
                text: letter });
  // The quantity title stays above the frame: the published figure sets it rotated 90 deg in
  // the left margin, and renderPaperComparison() emits horizontal <text> only.  This is a
  // declared difference, not a measurement -- see README.
  labels.push({ x: left, y: top - 3.4, text: label });
  return labels;
}

const recipeFor = geometry => {
  const { key, panel } = geometry;
  return {
    schema: 'forge-paper-style-v1',
    id: `cavalieri2025-fig-1${key}`,
    source: {
      sha256: vector.source_pdf_sha256,
      page: 7,
      method: `PDF vector geometry: form object ${vector.form.object} /Title (${vector.form.title}), `
        + `BBox [${FORM.join(' ')}], ${vector.path_count} paths. Frames, tick positions, curve `
        + 'widths, dash array and marker diameters are measured from the path geometry; axis '
        + 'text is re-typeset at the measured glyph height because the form contains no text '
        + 'operators.',
    },
    canvas: { ...CANVAS },
    frame: geometry.frame,
    x: geometry.x,
    y: geometry.y,
    gridWidth: 0.323,
    grid: 'none',
    font: { family: FONT, size: FONT_SIZE },
    // The published figure has ONE legend, inside panel (a) at the measured box
    // [141.06, 248.773, 165.037, 270.056] pt.  The shared renderer draws one legend per
    // renderPaperComparison() call, and that box sits on top of the panel (a) density
    // curve, so the four re-typeset legends are placed in the empty band between the two
    // panel rows (SVG y 120-142) instead.  The measured in-frame box is recorded in the
    // README as the published position; drawing it would hide data, which this figure
    // must not do.
    // Only panel (a) carries the shared legend.  The label set is identical for all four
    // panels, so one legend covers them; the other three calls get a legend placement
    // outside the viewBox so their rows are not drawn twice.
    legend: key === 'a'
      ? { x: LEGEND_X, y: LEGEND_TOP, rowHeight: LEGEND_ROW, sampleWidth: 7.45, textGap: 2.0 }
      : { x: -1000, y: -1000, rowHeight: LEGEND_ROW, sampleWidth: 7.45, textGap: 2.0 },
    labels: axisLabels(geometry),
  };
};

// ---------------------------------------------------------------------------
// Series
// ---------------------------------------------------------------------------
// The vector extraction reports each published circle once, but a few symbols are drawn as
// two circles at the same centre; a polyline/point series cannot repeat an abscissa, so exact
// duplicate centres are collapsed and the count is recorded rather than silently dropped.
const dedupe = (rows, where) => {
  const points = [];
  let removed = 0;
  for (const row of rows) {
    const point = { x: row[0], y: row[1] };
    const last = points[points.length - 1];
    if (last && last.x === point.x) {
      if (last.y !== point.y) throw new Error(`${where}: two different values at x=${point.x}`);
      removed += 1;
      continue;
    }
    if (last && point.x < last.x) throw new Error(`${where}: abscissae decrease at ${point.x}`);
    points.push(point);
  }
  return { points, removed };
};

const series = [];
const paperProvenance = (key, part) => ({
  origin: 'Cavalieri et al. (2025), Fig. 1, page 7',
  panel: QUANTITY[key].letter,
  extraction: part === 'curve'
    ? 'published model curve from the PDF path geometry (no resampling, no smoothing)'
    : 'published comparison symbols from the PDF circle geometry (filled 2.111 pt disc inside a '
      + '2.856 pt ring); each symbol keeps the abscissa at which it is drawn',
  asset: 'PDF vector form gr1.eps',
  source_pdf_sha256: vector.source_pdf_sha256,
  marker_diameters_pt: vector.marker_diameters,
});

for (const key of ['a', 'b', 'c', 'd']) {
  const geometry = panelGeometry(key);
  const panel = vector.panels[key];
  for (const fluid of ['o2', 'ch4']) {
    const { points: curve, removed: curveDuplicates } =
      dedupe(panel.curves[fluid], `panel ${key} ${fluid} curve`);
    if (!curve.length) throw new Error(`panel ${key}: empty ${fluid} curve`);
    series.push({
      id: `${key}-paper-${fluid}`,
      label: fluid === 'o2' ? 'paper: O2' : 'paper: CH4',
      origin: 'paper', engine: 'pdf-vector-geometry',
      mark: 'line', color: '#000000', lineWidth: panel.curve_line_width,
      ...(fluid === 'ch4' ? { dash: panel.curve_dash } : {}),
      provenance: { ...paperProvenance(key, 'curve'), points: curve.length,
                    duplicate_points_removed: curveDuplicates },
      points: curve,
    });
    const { points: markers, removed: markerDuplicates } =
      dedupe(panel.markers[fluid], `panel ${key} ${fluid} markers`);
    series.push({
      id: `${key}-paper-${fluid}-points`,
      label: fluid === 'o2' ? 'NIST: O2' : 'NIST: CH4',
      origin: 'paper', engine: 'pdf-vector-geometry',
      mark: 'points', color: '#000000', lineWidth: MARKER.width,
      markerRadius: MARKER.radius, markerWidth: MARKER.width,
      provenance: {
        ...paperProvenance(key, 'marker'),
        points: markers.length,
        worst_offset_pct: panel.marker_offset_pct[fluid === 'o2' ? 0 : 1],
        duplicate_centres_removed: markerDuplicates,
        excluded: panel.marker_excluded,
      },
      points: markers,
    });
  }
  void geometry;
}

if (sweepPath) {
  const sweep = JSON.parse(readFileSync(sweepPath, 'utf8'));
  if (sweep.schema !== 'forge-property-sweep-v1') throw new Error('unexpected sweep schema');
  for (const key of ['a', 'b', 'c', 'd']) {
    const column = SERIES_KEY[key];
    for (const fluid of ['o2', 'ch4']) {
      const rows = sweep.properties[column] && sweep.properties[column][fluid];
      if (!rows || !rows.length) throw new Error(`sweep has no ${column}.${fluid}`);
      const points = rows
        .map(([x, y]) => ({ x, y }))
        .filter(point => Number.isFinite(point.x) && Number.isFinite(point.y));
      if (points.length !== rows.length) throw new Error(`non-finite sweep sample in ${column}.${fluid}`);
      series.push({
        id: `${key}-computed-${fluid}`,
        label: `SRK+Chung: ${fluid === 'o2' ? 'O2' : 'CH4'}`,
        origin: 'computed', engine: 'srk-chung',
        mark: 'line', color: fluid === 'o2' ? '#c0392b' : '#2e86c1', lineWidth: 0.8,
        ...(fluid === 'ch4' ? { dash: [2, 2] } : {}),
        provenance: {
          origin: 'this work',
          model: sweep.model,
          source_commit: commit,
          ...(jobId ? { scheduler_job_id: jobId } : {}),
          samples: points.length,
          pressure_Pa: sweep.pressure_Pa,
        },
        points,
      });
    }
  }
}

// ---------------------------------------------------------------------------
// Render: four panels on one measured canvas, then one composite root element
// ---------------------------------------------------------------------------
const rendered = [];
for (const key of ['a', 'b', 'c', 'd']) {
  const geometry = panelGeometry(key);
  const recipe = recipeFor(geometry);
  const panelSeries = series.filter(item => item.id.startsWith(`${key}-`));
  if (!panelSeries.length) throw new Error(`panel ${key} has no series`);
  const out = renderPaperComparison(panelSeries, recipe);
  rendered.push({ key, geometry, recipe, out });
  writeFileSync(join(outDir, `cavalieri2025-fig-1${key}-recipe.json`), `${JSON.stringify(recipe, null, 2)}\n`);
  writeFileSync(join(outDir, `cavalieri2025-fig-1${key}-render-receipt.json`),
    `${JSON.stringify(out.receipt, null, 2)}\n`);
}

const inner = (svg, keepBackground) => {
  const body = svg.replace(/^<svg[^>]*>/, '').replace(/<\/svg>$/, '').replace(/<title>.*?<\/title>/, '');
  return keepBackground ? body
    : body.replace(/<rect x="[^"]*" y="[^"]*" width="[^"]*" height="[^"]*" fill="#ffffff"\/>/, '');
};
const [vx, vy, vw, vh] = CANVAS.viewBox;
const composite = '<svg xmlns="http://www.w3.org/2000/svg" '
  + `width="${CANVAS.width}" height="${CANVAS.height}" viewBox="${vx} ${vy} ${vw} ${vh}" role="img">`
  + '<title>cavalieri2025-fig-1: Cavalieri et al. (2025) Fig. 1, pure O2 and CH4 at 56 bar</title>'
  + rendered.map((item, index) => inner(item.out.svg, index === 0)).join('')
  + '</svg>';

const data = {
  schema: 'forge-series-v1',
  target: 'cavalieri2025-fig-1',
  units: {
    x: 'K',
    y: 'kg/m3 (a), kJ/(kg K) (b), 1e-4 Pa s (c), W/(m K) (d); series ids start with the panel letter',
    panels: { a: 'kg/m3', b: 'kJ/(kg K)', c: '1e-4 Pa s', d: 'W/(m K)' },
    panel_c_multiplier: {
      applied: 1e4,
      reason: 'the published panel (c) axis is labelled mu [Pa s] * 10^-4 with ticks 0-2, so the '
        + 'plotted ordinates are mu * 1e4; the data file stores the plotted numbers and the unit '
        + 'string above names the multiplier',
    },
  },
  provenance: {
    paper: 'Cavalieri et al. (2025) Fig. 1, digitised from the PDF form gr1.eps',
    paper_sha256: vector.source_pdf_sha256,
    digitisation: basename(vectorPath),
    digitisation_sha256: sha256(vectorPath),
    panels: 'a density, b cp, c viscosity, d conductivity',
    ...(sweepPath ? { sweep: basename(sweepPath), sweep_sha256: sha256(sweepPath) } : {}),
  },
  series,
};
const dataPath = join(outDir, 'cavalieri2025-fig-1-data.json');
writeFileSync(dataPath, `${JSON.stringify(data, null, 2)}\n`);

const svgPath = join(outDir, 'cavalieri2025-fig-1.svg');
writeFileSync(svgPath, composite);

const recipeComposite = {
  schema: 'forge-paper-style-v1-composite',
  id: 'cavalieri2025-fig-1',
  source_sha256: vector.source_pdf_sha256,
  composition: 'one root <svg> whose children are the unmodified bodies of the four '
    + 'renderPaperComparison() outputs; all four panels use the same canvas and viewBox (the '
    + 'PDF form coordinate system), so no coordinate transform is applied and only the first '
    + 'body keeps its background rect',
  panels: rendered.map(item => item.recipe),
};
const recipePath = join(outDir, 'cavalieri2025-fig-1-recipe.json');
writeFileSync(recipePath, `${JSON.stringify(recipeComposite, null, 2)}\n`);

const receipt = {
  schema: 'forge-figure-build-v1',
  target: 'cavalieri2025-fig-1',
  source_commit: commit,
  ...(jobId ? { scheduler_job_id: jobId } : {}),
  canvas: CANVAS,
  data: basename(dataPath), data_sha256: sha256(dataPath),
  plot: basename(svgPath), plot_sha256: sha256(svgPath),
  recipe: basename(recipePath), recipe_sha256: sha256(recipePath),
  panels: rendered.map(item => ({
    id: item.recipe.id,
    series: item.out.receipt.series,
    svg_sha256: createHash('sha256').update(item.out.svg).digest('hex'),
  })),
  font_availability: 'not_checked_by_renderer; axis text re-typeset at the measured glyph height',
};
writeFileSync(join(outDir, 'figure-build.json'), `${JSON.stringify(receipt, null, 2)}\n`);
for (const item of series) console.log(`${item.id}: ${item.points.length} points`);
console.log(`wrote ${svgPath} (${composite.length} bytes)`);
