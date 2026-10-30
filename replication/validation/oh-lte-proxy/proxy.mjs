// Mueller (2015), Eq. 18. Population proxy only; no radiative calibration.
export const constants = Object.freeze({
  planck_J_s: 6.62607015e-34,
  lightSpeed_m_s: 299792458,
  boltzmann_J_K: 1.380649e-23,
  wavelength_m: 308e-9,
});
export const excitationTemperature_K = constants.planck_J_s*constants.lightSpeed_m_s
  / (constants.wavelength_m*constants.boltzmann_J_K);

export function instantaneousProxy(sample, molecularWeight_kg_kmol) {
  for (const key of ['x', 'y', 'z', 'T', 'rho', 'OH']) {
    if (!Number.isFinite(sample[key])) throw new Error(`Missing or nonfinite instantaneous ${key}`);
  }
  if (!(sample.T > 0 && sample.rho > 0 && sample.OH >= 0 && sample.OH <= 1)) {
    throw new Error('Require positive instantaneous T/rho and OH mass fraction in [0,1]');
  }
  if (!(Number.isFinite(molecularWeight_kg_kmol) && molecularWeight_kg_kmol > 0)) {
    throw new Error('OH molecular weight must be positive finite kg/kmol');
  }
  const boltzmannFactor = Math.exp(-excitationTemperature_K/sample.T);
  const cOH_mol_m3 = 1000*sample.rho*sample.OH/molecularWeight_kg_kmol;
  if (!Number.isFinite(cOH_mol_m3)) throw new Error('OH concentration overflow');
  return { x: sample.x, y: sample.y, z: sample.z,
    T_K: sample.T, rho_kg_m3: sample.rho, Y_OH: sample.OH,
    boltzmannFactor, cOH_mol_m3,
    YOHstar_LTE_proxy: sample.OH*boltzmannFactor,
    cOHstar_LTE_proxy_mol_m3: cOH_mol_m3*boltzmannFactor,
    excitationUnderflow: sample.OH > 0 && boltzmannFactor === 0 ? 1 : 0 };
}

export function validateSampling(manifest) {
  if (manifest.schema !== 'oh-lte-samples/v1' || manifest.sampling?.instantaneous !== true ||
      !['instantaneous-cfd', 'physical-flamelet-snapshot'].includes(manifest.sampling?.kind)) {
    throw new Error('Require oh-lte-samples/v1 and explicit instantaneous sampling; mean fields are unsupported');
  }
  if (!manifest.provenance || typeof manifest.provenance !== 'object' ||
      Array.isArray(manifest.provenance) || Object.keys(manifest.provenance).length === 0) {
    throw new Error('Record explicit run/derivation provenance');
  }
  if (!Array.isArray(manifest.frames) || !manifest.frames.length) throw new Error('No instantaneous frames');
  for (let i = 0; i < manifest.frames.length; i++) {
    const frame = manifest.frames[i];
    if (!Number.isFinite(frame.time_s) || frame.time_s < 0 ||
        (i && frame.time_s <= manifest.frames[i-1].time_s) ||
        !Array.isArray(frame.files) || !frame.files.length ||
        frame.files.some(path => typeof path !== 'string' || !path)) {
      throw new Error('Frames need nonnegative increasing time_s and nonempty CSV paths');
    }
  }
  if (manifest.averaging !== null && manifest.averaging !== undefined) {
    const average = manifest.averaging;
    if (manifest.frames.length < 2 || average.method !== 'trapezoidal-samples' ||
        average.start_s !== manifest.frames[0].time_s || average.end_s !== manifest.frames.at(-1).time_s) {
      throw new Error('Averaging needs >=2 frames and an explicit window matching retained endpoints');
    }
  }
}

export function averageProxies(frames) {
  if (frames.length < 2) throw new Error('At least two instantaneous frames required for sampled averaging');
  const duration = frames.at(-1).time_s-frames[0].time_s;
  const rows = frames[0].rows.map(row => ({ x: row.x, y: row.y, z: row.z,
    meanYOHstar_LTE_proxy: 0, meanCOHstar_LTE_proxy_mol_m3: 0 }));
  for (let i = 1; i < frames.length; i++) {
    const previous = frames[i-1], next = frames[i], dt = next.time_s-previous.time_s;
    if (!(dt > 0) || next.rows.length !== rows.length) throw new Error('Average requires matching ordered samples');
    for (let j = 0; j < rows.length; j++) {
      const left = previous.rows[j], right = next.rows[j];
      if (['x', 'y', 'z'].some(key => right[key] !== rows[j][key] || left[key] !== rows[j][key])) {
        throw new Error('Average does not fill missing points or interpolate changed sample coordinates');
      }
      rows[j].meanYOHstar_LTE_proxy += .5*dt*(left.YOHstar_LTE_proxy+right.YOHstar_LTE_proxy)/duration;
      rows[j].meanCOHstar_LTE_proxy_mol_m3 += .5*dt*(left.cOHstar_LTE_proxy_mol_m3+right.cOHstar_LTE_proxy_mol_m3)/duration;
    }
  }
  return rows;
}
