#!/usr/bin/env node
/** Explicit finite-window statistics from immutable saved samples. */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { hash, discover, mergeFiles } from './samples.mjs';
import { timeWeights, moments, accumulate, finish } from './statistics.mjs';

function options(argv) {
  const result = { favre: false, apply: false };
  for (let i = 0; i < argv.length; ++i) {
    const name = argv[i];
    if (['--favre', '--apply'].includes(name)) result[name.slice(2)] = true;
    else if (['--case', '--run-record', '--start-s', '--end-s', '--max-gap-s', '--max-profile-gap-s', '--max-plane-gap-s', '--out'].includes(name) && argv[i + 1]) result[name.slice(2)] = argv[++i];
    else throw new Error(`Unknown or incomplete option ${name}`);
  }
  for (const key of ['case', 'run-record', 'start-s', 'end-s', 'max-gap-s', 'out']) if (!(key in result)) throw new Error(`Missing --${key}`);
  for (const key of ['start-s', 'end-s', 'max-gap-s']) result[key] = Number(result[key]);
  if (![result['start-s'], result['end-s'], result['max-gap-s']].every(Number.isFinite) || result['start-s'] < 0 || result['end-s'] <= result['start-s'] || result['max-gap-s'] <= 0) throw new Error('Invalid time window or maximum gap');
  for (const key of ['max-profile-gap-s', 'max-plane-gap-s']) {
    if (key in result) {
      result[key] = Number(result[key]);
      if (!Number.isFinite(result[key]) || result[key] <= 0) throw new Error(`--${key} requires a positive finite duration`);
    }
  }
  for (const key of ['case', 'run-record', 'out']) result[key] = path.resolve(result[key]);
  const relative = path.relative(result.case, result.out);
  if (relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative))) throw new Error('Derived output must be outside the retained case');
  return result;
}

function groupStatistics(group, settings) {
  const maximumGap = settings[group.geometry === 'plane' ? 'max-plane-gap-s' : 'max-profile-gap-s'] ?? settings['max-gap-s'];
  const quadrature = timeWeights(group.frames.map(f => f.time_s), settings['start-s'], settings['end-s'], maximumGap);
  const identities = {}, duplicateAudit = [], weighted = {}, favre = {};
  let first = null;
  for (const [frameIndex, frame] of group.frames.entries()) {
    const sample = mergeFiles(frame.files);
    Object.assign(identities, sample.hashes);
    duplicateAudit.push(...sample.audit.map(row => ({ time_s: frame.time_s, ...row })));
    if (!first) {
      first = sample;
      for (const field of sample.fields) {
        weighted[field] = moments(sample.rows.length);
        if (settings.favre && sample.fields.includes('rho')) favre[field] = moments(sample.rows.length);
      }
    } else if (JSON.stringify(sample.keys) !== JSON.stringify(first.keys) || JSON.stringify(sample.fields) !== JSON.stringify(first.fields) || JSON.stringify(sample.coordinates) !== JSON.stringify(first.coordinates)) {
      throw new Error(`${group.key}: coordinates or fields change across times; no missing-data fill is allowed`);
    }
    const timeWeight = quadrature.weights[frameIndex];
    const density = sample.fields.includes('rho') ? sample.rows.map(row => row.rho) : null;
    for (const field of sample.fields) {
      const values = sample.rows.map(row => row[field]);
      accumulate(weighted[field], values, timeWeight);
      if (favre[field]) accumulate(favre[field], values, timeWeight, density);
    }
  }
  const summary = { key: group.key, name: group.name, geometry: group.geometry,
    maximumGap_s: maximumGap,
    times_s: group.frames.map(f => f.time_s), quadrature, pointCount: first?.rows.length ?? 0,
    coordinates: first?.coordinates ?? [], fields: first?.fields ?? [],
    velocityComponents: first?.fields.includes('U_0') ? {
      U_0: 'Cartesian x velocity (m/s), axial for the declared x-aligned geometry',
      U_1: 'Cartesian y velocity (m/s)', U_2: 'Cartesian z velocity (m/s)',
      normalization: 'none; no planning inlet velocity consumed',
    } : null,
    removedExactDuplicateRows: duplicateAudit.reduce((sum, row) => sum + row.removedCount, 0),
    favre: settings.favre ? (first?.fields.includes('rho') ? 'actual-positive-co-located-density' : 'unavailable-no-rho') : 'not-requested',
    status: quadrature.duration_s > 0 ? (quadrature.gaps.length ? 'available-excluded-gaps' : 'available-inside-window-span') : 'unavailable-no-usable-interval',
    statisticalConvergenceEstablished: false };
  if (!(quadrature.duration_s > 0)) return { summary, identities, duplicateAudit, csv: null };
  const columns = [...first.coordinates], values = {};
  for (const coordinate of first.coordinates) values[coordinate] = first.rows.map(row => row[coordinate]);
  for (const field of first.fields) {
    const reynolds = finish(weighted[field]);
    columns.push(field + 'Mean', field + 'RMS');
    values[field + 'Mean'] = reynolds.mean; values[field + 'RMS'] = reynolds.rms;
    if (favre[field]) {
      const densityWeighted = finish(favre[field]);
      columns.push(field + 'FavreMean', field + 'FavreRMS');
      values[field + 'FavreMean'] = densityWeighted.mean; values[field + 'FavreRMS'] = densityWeighted.rms;
    }
  }
  const lines = [columns.join(',')];
  for (let i = 0; i < first.rows.length; ++i) lines.push(columns.map(name => values[name][i].toPrecision(17)).join(','));
  return { summary, identities, duplicateAudit, csv: lines.join('\n') + '\n' };
}

const settings = options(process.argv.slice(2));
const inputPath = path.join(settings.case, 'direct-g2-input.json');
const inputRaw = fs.readFileSync(inputPath), runRaw = fs.readFileSync(settings['run-record']);
const digest = raw => crypto.createHash('sha256').update(raw).digest('hex');
const caseInput = JSON.parse(inputRaw), run = JSON.parse(runRaw);
if (!run.jobId || !(run.source || run.runtime) || !Number.isFinite(run.lastCompletedTime_s) || run.lastCompletedTime_s < 0) throw new Error('Run record needs jobId, source/runtime and finite lastCompletedTime_s');
if (run.caseInput?.sha256 && digest(inputRaw) !== run.caseInput.sha256) throw new Error('Case input differs from run-record binding');
if (!Array.isArray(caseInput.observations?.radialPositions_m) || !Number.isFinite(caseInput.observations.nearAxisRadius_m)) throw new Error('Case lacks explicit named observation geometry');
const groups = discover(settings.case, settings['start-s'], settings['end-s'], run.lastCompletedTime_s, caseInput.observations);
const expected = ['line-nearAxis', ...caseInput.observations.radialPositions_m.map((_, i) => `line-radial${i}`), ...(caseInput.observations.imageGrid ? ['plane-midplane'] : [])];
const inputHashes = { [inputPath]: digest(inputRaw), [settings['run-record']]: digest(runRaw) };
const outputs = [], duplicateAudit = [], groupReports = [];
for (const group of groups) {
  const result = groupStatistics(group, settings);
  Object.assign(inputHashes, result.identities); duplicateAudit.push(...result.duplicateAudit);
  if (result.csv !== null) {
    result.summary.output = group.key + '.csv';
    outputs.push([result.summary.output, result.csv]);
  }
  groupReports.push(result.summary);
}
const here = path.dirname(fileURLToPath(import.meta.url));
const report = { schema: 'g2-saved-window-statistics/v1', mode: settings.apply ? 'applied' : 'read-only-plan',
  status: outputs.length ? 'statistics-derived-for-available-groups' : 'unavailable-no-usable-statistics',
  requestedWindow_s: [settings['start-s'], settings['end-s']], maximumGap_s: settings['max-gap-s'],
  geometryMaximumGaps_s: { line: settings['max-profile-gap-s'] ?? settings['max-gap-s'], plane: settings['max-plane-gap-s'] ?? settings['max-gap-s'] },
  method: 'Trapezoidal endpoint weights for sampled q and q²; stable weighted central moments; no gap bridging or extrapolation',
  varianceConvention: 'Population central moment, not standard error; Favre weights=time*rho when requested and present',
  runIdentity: run, caseInput, inputHashes, groups: groupReports,
  missingGroups: expected.filter(name => !groups.some(group => group.key === name)),
  sourceHashes: Object.fromEntries(['run.mjs', 'samples.mjs', 'statistics.mjs', 'README.md'].map(name => [name, hash(path.join(here, name))])),
  limitations: ['Saved-sample quadrature does not resolve fluctuations between writes.',
    'Transient-window RMS includes flow development and is not automatically turbulent fluctuation RMS.',
    'Partial/disjoint coverage is not a continuous full-window mean.', 'No statistical convergence or scientific acceptance is established.',
    'No LTE formula is applied to mean T/rho/OH; average instantaneous optical proxies separately.'],
  scientificAcceptance: false, statisticalConvergenceEstablished: false };
if (settings.apply) {
  for (const [file, expectedHash] of Object.entries(inputHashes)) if (hash(file) !== expectedHash) throw new Error(`Input changed before output: ${file}`);
  fs.mkdirSync(settings.out, { recursive: false });
  for (const [name, csv] of outputs) fs.writeFileSync(path.join(settings.out, name), csv);
  fs.writeFileSync(path.join(settings.out, 'duplicate-audit.json'), JSON.stringify(duplicateAudit, null, 2) + '\n');
  report.outputHashes = Object.fromEntries([...outputs.map(([name]) => name), 'duplicate-audit.json'].map(name => [name, hash(path.join(settings.out, name))]));
  fs.writeFileSync(path.join(settings.out, 'manifest.json'), JSON.stringify(report, null, 2) + '\n');
}
console.log(JSON.stringify({ schema: report.schema, mode: report.mode, out: settings.out,
  requestedWindow_s: report.requestedWindow_s, groups: groupReports, missingGroups: report.missingGroups,
  scientificAcceptance: false }, null, 2));
if (settings.apply && outputs.length === 0) process.exitCode = 2;
