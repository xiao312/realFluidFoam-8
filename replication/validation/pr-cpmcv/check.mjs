import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

// This is a scalar source regression, not a substitute for a compiled OF8 probe.
const defaultHeader = new URL('../../../src/thermophysicalModels/specie/equationOfState/PengRobinson/PengRobinsonI.H', import.meta.url);
const args = process.argv.slice(2);
assert(args.length === 0 || (args.length === 2 && args[0] === '--header'),
  'Usage: node check.mjs [--header TRUSTED_LOCAL_HEADER]');
const header = args[1] ?? fileURLToPath(defaultHeader);
const text = readFileSync(header, 'utf8');
const marker = 'Foam::PengRobinson<Specie>::CpMCv';
const start = text.indexOf(marker);
assert(start >= 0 && text.indexOf(marker, start + marker.length) === -1, 'Expected one CpMCv definition');
const opening = text.indexOf('{', start);
let depth = 1;
let end = opening + 1;
for (; end < text.length && depth; end++) {
  if (text[end] === '{') depth++;
  if (text[end] === '}') depth--;
}
assert.equal(depth, 0, 'Unclosed CpMCv definition');
const body = text.slice(opening + 1, end - 1);

function sourceFunction(sourceBody) {
  const javascript = sourceBody.replace(/\/\/[^\n]*/g, '')
    .replace(/\bconst scalar\b/g, 'const').replace(/\bscalar\b/g, 'let')
    .replace(/this->Z\(p, T\)/g, 'Zvalue').replace(/this->R\(\)/g, '(RR/W)');
  assert(!javascript.includes('this->'), 'Unsupported source expression');
  return new Function('p', 'T', 'RR', 'W', 'b_', 'coef1_', 'coef2_', 'coef3_',
    'Zvalue', 'sqr', 'sqrt', javascript);
}

const implementation = sourceFunction(body);
const legacyBody = body.replace(/const scalar M\s*=\s*[^;]+;/,
  'const scalar M = (sqr(Z) + B*Z)/(Z - B);');
const legacy = sourceFunction(legacyBody);
const RR = 8314.47006650545; // Retained OF8 gas constant, J/(kmol K).
const pressure = 5.61e6;
const tolerance = 2e-7;
const fluids = [
  { name: 'O2', W: 31.998, Tc: 154.58, Pc: 5.043e6, omega: 0.025,
    temperatures: [85, 90, 100, 120, 140, 150, 155, 160, 165, 170, 180, 200, 250, 288, 300, 400, 600] },
  { name: 'CH4', W: 16.043, Tc: 190.6, Pc: 4.61e6, omega: 0.011,
    temperatures: [200, 250, 288, 300, 400, 600] },
];

function parameters(fluid) {
  const { Tc, Pc, omega } = fluid;
  const k = 0.37464 + 1.54226 * omega - 0.26992 * omega ** 2;
  const a = 0.45724 * (RR * Tc) ** 2 / Pc;
  return { k, a, b: 0.07780 * RR * Tc / Pc,
    c1: a * (1 + k) ** 2, c2: 2 * a * k * (1 + k) / Math.sqrt(Tc), c3: a * k ** 2 / Tc };
}

// Reference pressure does not use M, N, A, B or the CpMCv expression.
function pressureAt(T, v, fluid, par) {
  const attraction = par.a * (1 + par.k * (1 - Math.sqrt(T / fluid.Tc))) ** 2;
  return RR * T / (v - par.b) - attraction / (v * v + 2 * par.b * v - par.b ** 2);
}

function molarVolume(T, fluid, par) {
  let low = par.b * (1 + 1e-9);
  let high = 100 * RR * T / pressure;
  assert(pressureAt(T, low, fluid, par) > pressure && pressureAt(T, high, fluid, par) < pressure);
  // These pressures exceed both pure-fluid critical pressures; use the stable root.
  for (let i = 0; i < 150; i++) {
    const middle = (low + high) / 2;
    if (pressureAt(T, middle, fluid, par) > pressure) low = middle;
    else high = middle;
  }
  const v = (low + high) / 2;
  assert(Math.abs(pressureAt(T, v, fluid, par) / pressure - 1) < 1e-11);
  return v;
}

function derivative(fn, x, step) {
  return (fn(x - 2 * step) - 8 * fn(x - step) + 8 * fn(x + step) - fn(x + 2 * step)) / (12 * step);
}

function reference(T, v, fluid, par, stepFraction) {
  const dpdT = derivative(t => pressureAt(t, v, fluid, par), T, T * stepFraction);
  const dpdv = derivative(volume => pressureAt(T, volume, fluid, par), v, v * stepFraction);
  assert(dpdv < 0, 'Reference state must be mechanically stable');
  return -T * dpdT ** 2 / (dpdv * fluid.W);
}

const results = [];
for (const fluid of fluids) {
  const par = parameters(fluid);
  for (const T of fluid.temperatures) {
    const v = molarVolume(T, fluid, par);
    const expected = reference(T, v, fluid, par, 1e-5);
    const second = reference(T, v, fluid, par, 5e-6);
    const parameters = [pressure, T, RR, fluid.W, par.b, par.c1, par.c2, par.c3,
      pressure * v / (RR * T), x => x * x, Math.sqrt];
    const actual = implementation(...parameters);
    const old = legacy(...parameters);
    const relativeError = Math.abs(actual / expected - 1);
    const derivativeStepError = Math.abs(second / expected - 1);
    results.push({ fluid: fluid.name, T_K: T, expected_J_kg_K: expected,
      actual_J_kg_K: actual, relativeError, derivativeStepError,
      legacyRelativeError: Math.abs(old / expected - 1) });
  }
}
const failures = results.filter(r => !Number.isFinite(r.actual_J_kg_K)
  || r.actual_J_kg_K <= 0 || r.relativeError > tolerance || r.derivativeStepError > tolerance);
const legacyFailures = results.filter(r => r.legacyRelativeError > tolerance);
const summary = { schema: 'pr-cpmcv-pressure-identity-v1', header, states: results.length,
  relativeTolerance: tolerance, maxRelativeError: Math.max(...results.map(r => r.relativeError)),
  maxDerivativeStepError: Math.max(...results.map(r => r.derivativeStepError)),
  legacyRejectedStates: legacyFailures.length, failures };
console.log(JSON.stringify(summary, null, 2));
assert(legacyFailures.some(r => r.fluid === 'O2' && r.T_K === 165), 'Negative control must reject the known failure');
assert.equal(failures.length, 0, 'Source CpMCv violates the independent PR pressure-derivative identity');
