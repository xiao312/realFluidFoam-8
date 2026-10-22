/**
 * Render the registered Liang Fig. 8(a) comparison with the campaign's shared renderer.
 *
 * Ten series are drawn: the five staged Cantera solves (computed, with visible markers)
 * and the five digitised paper series (dashed traces). The recipe is the campaign's own
 * frozen `liang-8a-cantera-recipe.json`, so the figure is reproduced with the same
 * smoothing, colours and legend order as the prepared asset, and the series table below
 * is the only thing this module replaces.
 *
 * The renderer interpolates for display only (`interpolation_is_evidence: false`); every
 * number quoted in the report comes from the solved profiles and the digitised rows.
 *
 * If `--compare` is given, the legend marks a computed case `unresolved` when the
 * comparison file reports any of its points outside the declared screen, and the receipt
 * records how many of how many. The label is derived from the comparison, so it cannot
 * say `compared` about a case the same run calls failed.
 *
 *   node render_fig8a.mjs --results R.json --reference REF.json --recipe RECIPE.json \
 *        --out-dir DIR --source-commit SHA [--run-job-id ID] [--compare compare.json]
 */
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { renderComparison } from '/forge/plots/render.mjs';

const args = new Map();
for (let i = 2; i < process.argv.length; i += 2) args.set(process.argv[i].replace(/^--/, ''), process.argv[i + 1]);
const need = key => {
  const value = args.get(key);
  if (!value) throw new Error(`Missing --${key}`);
  return value;
};

const resultsPath = need('results');
const referencePath = need('reference');
const recipePath = need('recipe');
const outDir = need('out-dir');
const commit = need('source-commit');
const jobId = args.get('run-job-id') || null;

const MODELS = {
  1: 'ideal gas',
  2: '+ SRK density',
  3: '+ SRK enthalpy',
  4: '+ Ely-Hanley conductivity',
  5: '+ Takahashi diffusion',
};

const sha256 = path => createHash('sha256').update(readFileSync(path)).digest('hex');

const sweep = JSON.parse(readFileSync(resultsPath, 'utf8'));
const reference = JSON.parse(readFileSync(referencePath, 'utf8'));
const recipe = JSON.parse(readFileSync(recipePath, 'utf8'));
if (!Array.isArray(sweep.results) || !sweep.results.length) throw new Error('No computed results');
if (!Array.isArray(reference.rows) || !reference.rows.length) throw new Error('No digitised reference rows');

// Per-case screen outcome, straight out of the comparison file that the report tabulates.
const comparePath = args.get('compare') || null;
const comparison = comparePath ? JSON.parse(readFileSync(comparePath, 'utf8')) : null;
const screenByStage = new Map();
for (const [stage, verdict] of Object.entries((comparison && comparison.stages) || {})) {
  screenByStage.set(Number(stage), verdict);
}

const series = [];
const solvedStages = new Set(
  sweep.results.map(row => row.stage),
);
for (const stage of [1, 2, 3, 4, 5]) {
  const computed = sweep.results
    .filter(row => row.stage === stage)
    .map(row => ({ x: row.phi, y: row.speed_cm_s }))
    .sort((a, b) => a.x - b.x);
  if (!computed.length) continue;
  const screen = screenByStage.get(stage) || null;
  const unresolved = Boolean(screen && screen.failed_points > 0);
  series.push({
    id: `cantera-${stage}`,
    label: unresolved
      ? `Case ${stage}: ${MODELS[stage]} (Cantera 3.2; unresolved - ${screen.failed_points} of ${screen.points} points outside the screen)`
      : `Case ${stage}: ${MODELS[stage]} (Cantera 3.2)`,
    origin: 'computed',
    engine: 'cantera',
    case: String(stage),
    ...(screen ? { comparison: unresolved ? 'unresolved' : 'compared' } : {}),
    points: computed,
    provenance: {
      origin: 'this work, staged SRK FreeFlame in the registered cantera32 image',
      model: MODELS[stage],
      source_commit: commit,
      samples: computed.length,
      pressure_atm: 100,
      unburned_temperature_K: 298,
      ...(screen
        ? {
            screened_points: screen.points,
            points_outside_screen: screen.failed_points,
            rms_cm_s: screen.rms_cm_s,
            max_abs_cm_s: screen.max_abs_cm_s,
            screen_status: unresolved ? 'unresolved' : 'within-screen',
          }
        : {}),
      ...(jobId ? { scheduler_job_id: jobId } : {}),
    },
  });
}
for (const stage of [1, 2, 3, 4, 5]) {
  const paper = reference.rows
    .filter(row => row.stage === stage)
    .map(row => ({ x: row.phi, y: row.speed_cm_s }))
    .sort((a, b) => a.x - b.x);
  if (!paper.length) continue;
  const kind = stage === 1 || stage === 5 ? 'traced curve' : 'symbol centres';
  // A paper trace whose stage was never solved is a reference, not a comparison: say so
  // in the legend rather than letting it read as a matched computed series.
  const unreferenced = !solvedStages.has(stage);
  series.push({
    id: `paper-${stage}`,
    label: unreferenced
      ? `Case ${stage}: ${MODELS[stage]} (paper; no computed counterpart - not compared)`
      : `Case ${stage}: ${MODELS[stage]} (paper)`,
    origin: 'paper',
    engine: 'paper',
    case: String(stage),
    points: paper,
    ...(unreferenced ? { comparison: 'unreferenced' } : {}),
    provenance: {
      origin: 'Liang et al. Fig. 8(a), raster digitisation of the campaign library crop',
      extraction: kind,
      reference_sha256: sha256(referencePath),
      raster_sha256: reference.raster.sha256,
      paper_sha256: reference.paper_sha256,
      uncertainty_cm_s: paper[0].uncertainty_cm_s,
      points: paper.length,
    },
  });
}

const plotting = recipe.series.slice();
for (const id of plotting) if (!series.some(s => s.id === id)) throw new Error(`Series ${id} unavailable`);
const table = { schema: 'forge-series-v1', target: 'liang-8a', units: { x: '1', y: 'cm/s' }, series };

mkdirSync(outDir, { recursive: true });
writeFileSync(join(outDir, 'liang-8a-data.json'), `${JSON.stringify(table, null, 2)}\n`);

const rendered = await renderComparison(table, recipe);
writeFileSync(join(outDir, 'liang-8a-cantera.svg'), rendered.svg);
const receipt = {
  ...rendered.receipt ?? rendered.recipe ?? { schema: 'forge-plot-render-v1' },
  figure: 'liang-8a',
  target: 'liang-8a',
  source_commit: commit,
  recipe_sha256: sha256(recipePath),
  recipe_id: recipe.id,
  recipe_source: 'campaign central payload asset liang-8a-cantera-recipe.json',
  results_sha256: sha256(resultsPath),
  reference_sha256: sha256(referencePath),
  ...(comparePath
    ? {
        comparison_sha256: sha256(comparePath),
        unresolved_series: series.filter(s => s.comparison === 'unresolved').map(s => s.id),
        screen: Object.fromEntries(
          [...screenByStage].map(([stage, v]) => [String(stage), { points: v.points, failed_points: v.failed_points }]),
        ),
      }
    : {}),
  series: series.map(s => ({ id: s.id, origin: s.origin, points: s.points.length })),
  interpolation_is_evidence: false,
  scientific_status: 'not_assessed',
};
writeFileSync(join(outDir, 'liang-8a-render-receipt.json'), `${JSON.stringify(receipt, null, 2)}\n`);
console.log(JSON.stringify({ svg_bytes: rendered.svg.length, series: series.length, out: outDir }));
