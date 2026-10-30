/** Time quadrature and stable central moments; no temporal gap interpolation. */
export function timeWeights(times, start, end, maximumGap) {
  if (!(end > start && maximumGap > 0) || ![start, end, maximumGap, ...times].every(Number.isFinite)) {
    throw new Error('Require finite bounds, increasing window and positive maximum gap');
  }
  if (times.some((t, i) => t < start || t > end || (i && t <= times[i - 1]))) {
    throw new Error('Times must be strictly increasing and inside the requested window');
  }
  const weights = times.map(() => 0), included = [], gaps = [];
  for (let i = 1; i < times.length; ++i) {
    const duration = times[i] - times[i - 1];
    const interval = { start_s: times[i - 1], end_s: times[i], duration_s: duration };
    if (duration > maximumGap) gaps.push(interval);
    else {
      weights[i - 1] += duration / 2;
      weights[i] += duration / 2;
      included.push(interval);
    }
  }
  const duration = weights.reduce((a, b) => a + b, 0);
  return { weights, included, gaps, duration_s: duration,
    coverageFraction: duration / (end - start),
    availableBounds_s: times.length ? [times[0], times.at(-1)] : null,
    effectiveBounds_s: included.length ? [included[0].start_s, included.at(-1).end_s] : null,
    uncoveredBoundary_s: times.length ? [times[0] - start, end - times.at(-1)] : [end - start, 0],
    availableSampleCount: times.length, contributingSampleCount: weights.filter(w => w > 0).length };
}

export function moments(size) {
  return { weight: new Float64Array(size), mean: new Float64Array(size), m2: new Float64Array(size) };
}

export function accumulate(state, values, timeWeight, density = null) {
  if (values.length !== state.mean.length || (density && density.length !== values.length)) {
    throw new Error('Moment arrays have incompatible sizes');
  }
  for (let i = 0; i < values.length; ++i) {
    const w = timeWeight * (density ? density[i] : 1);
    if (!Number.isFinite(values[i]) || !Number.isFinite(w) || w < 0 || (density && !(density[i] > 0))) {
      throw new Error('Statistics require finite samples and positive instantaneous Favre density');
    }
    if (w === 0) continue;
    const total = state.weight[i] + w, delta = values[i] - state.mean[i];
    state.mean[i] += w / total * delta;
    state.m2[i] += w * delta * (values[i] - state.mean[i]);
    state.weight[i] = total;
  }
}

export function finish(state) {
  const rms = new Float64Array(state.mean.length);
  for (let i = 0; i < rms.length; ++i) {
    if (!(state.weight[i] > 0) || state.m2[i] < 0 || !Number.isFinite(state.m2[i])) {
      throw new Error('Moment calculation has invalid weight or central moment');
    }
    rms[i] = Math.sqrt(state.m2[i] / state.weight[i]);
  }
  return { mean: state.mean, rms };
}
