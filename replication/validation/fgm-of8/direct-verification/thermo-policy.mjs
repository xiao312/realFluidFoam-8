// Preserve NASA7 coefficients and transition temperatures. Only an explicit
// diagnostic request may extend inversion limits beyond the published ranges.
export function nasaInversionPolicy(metadata, option) {
  const requested = option === undefined ? null : String(option).split(',').map(Number);
  if (requested && (requested.length !== 2 || !requested.every(Number.isFinite) ||
      !(requested[0] > 0 && requested[1] > requested[0]))) {
    throw new Error('Use --nasa-extrapolation MIN_K,MAX_K with finite positive ordered bounds');
  }
  const species = metadata.species.map(s => {
    const original = s.thermo.temperatureRanges;
    if (s.thermo.model !== 'NASA7' || original.length !== 3 ||
        !original.every(Number.isFinite) || !(0 < original[0] && original[0] < original[1] && original[1] < original[2])) {
      throw new Error(`Invalid NASA7 ranges for ${s.name}`);
    }
    return { name: s.name, originalRange_K: [...original],
      effectiveRange_K: requested ? [Math.min(original[0], requested[0]), original[1], Math.max(original[2], requested[1])] : [...original] };
  });
  return { mode: requested ? 'explicit-diagnostic-extrapolation' : 'original-species-ranges',
    requestedRange_K: requested, coefficientsChanged: false, transitionTemperaturesChanged: false,
    originalMixtureIntersection_K: [Math.max(...species.map(s => s.originalRange_K[0])), Math.min(...species.map(s => s.originalRange_K[2]))],
    effectiveMixtureIntersection_K: [Math.max(...species.map(s => s.effectiveRange_K[0])), Math.min(...species.map(s => s.effectiveRange_K[2]))],
    species,
    qualification: requested ? 'NASA polynomial extrapolation as used by the flamelet evaluation; not experimental caloric validation' : 'No extrapolation authorized' };
}
