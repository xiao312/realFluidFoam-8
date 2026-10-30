import test from 'node:test';
import assert from 'node:assert/strict';
import { timeWeights, moments, accumulate, finish } from './statistics.mjs';

test('unequal actual intervals produce time-weighted Reynolds and Favre moments', () => {
  const q = timeWeights([0, 1, 3], 0, 3, 2);
  assert.deepEqual(q.weights, [.5, 1.5, 1]);
  const reynolds = moments(1), favre = moments(1);
  [0, 2, 4].forEach((value, i) => {
    accumulate(reynolds, [value], q.weights[i]);
    accumulate(favre, [value], q.weights[i], [[1], [2], [3]][i]);
  });
  assert.ok(Math.abs(finish(reynolds).mean[0] - 7 / 3) < 1e-14);
  assert.ok(Math.abs(finish(reynolds).rms[0] ** 2 - 17 / 9) < 1e-14);
  assert.ok(Math.abs(finish(favre).mean[0] - 18 / 6.5) < 1e-14);
  assert.equal(q.coverageFraction, 1);
});

test('large gaps and uncovered boundaries are not filled; constants have zero RMS', () => {
  const q = timeWeights([1, 2, 8, 9], 0, 10, 2);
  assert.equal(q.duration_s, 2);
  assert.equal(q.coverageFraction, .2);
  assert.deepEqual(q.uncoveredBoundary_s, [1, 1]);
  assert.equal(q.gaps[0].duration_s, 6);
  const state = moments(1);
  q.weights.forEach(w => accumulate(state, [3500], w));
  assert.equal(finish(state).rms[0], 0);
  assert.equal(timeWeights([1], 0, 10, 2).duration_s, 0);
});

test('50us profiles and 500us planes retain distinct declared gap limits', () => {
  const profile = timeWeights([0, 50e-6, 500e-6, 550e-6], 0, 1e-3, 75e-6);
  const plane = timeWeights([0, 500e-6, 1e-3], 0, 1e-3, 750e-6);
  assert.equal(profile.gaps.length, 1);
  assert.ok(Math.abs(profile.duration_s - 100e-6) < 1e-18);
  assert.equal(plane.gaps.length, 0);
  assert.equal(plane.duration_s, 1e-3);
  assert.equal(timeWeights([0, 500e-6, 1e-3], 0, 1e-3, 75e-6).duration_s, 0);
});
