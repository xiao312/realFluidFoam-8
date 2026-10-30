// Fixed-mesh Euler accounting. No acceptance limits or missing-sample filling.
export function parseSolverLog(text) {
  const result = { states: [], equations: [], times: [], audits: [] };
  const names = { energyState: 'states', energyEquation: 'equations', energyResidualAudit: 'audits' };
  text.split(/\r?\n/).forEach((raw, index) => {
    const time = /^Time = (\S+)\s*$/.exec(raw);
    if (time) {
      const value = Number(time[1]);
      if (!Number.isFinite(value)) throw new Error(`Nonfinite time on line ${index + 1}`);
      result.times.push({ line: index + 1, token: time[1], value });
    }
    const label = Object.keys(names).find(name => raw.startsWith(name + ' '));
    if (!label) return;
    const values = Object.fromEntries([...raw.matchAll(/(\w+)=([^\s]+)/g)].map(([, key, value]) => [key, Number(value)]));
    if (!Number.isFinite(values.t) || !Object.values(values).every(Number.isFinite)) throw new Error(`Malformed ${label} on line ${index + 1}`);
    result[names[label]].push({ line: index + 1, values, raw });
  });
  return result;
}

export function parseFlux(text, identity) {
  if (!/#\s*Time\s+sum\(phi\)/.test(text)) throw new Error(`Expected signed sum(phi) header: ${identity}`);
  return text.split(/\r?\n/).flatMap((raw, index) => {
    if (!raw.trim() || raw.trim().startsWith('#')) return [];
    const columns = raw.trim().split(/\s+/);
    if (columns.length !== 2 || !columns.map(Number).every(Number.isFinite)) throw new Error(`Malformed phi row: ${identity}:${index + 1}`);
    return [{ token: columns[0], timeName: Number(columns[0]), flux_kg_s: Number(columns[1]), line: index + 1, identity }];
  });
}

const ratio = (value, scale) => scale > 0 ? value / scale : null;
const required = (row, keys, label) => {
  for (const key of keys) if (!Number.isFinite(row[key])) throw new Error(`Missing ${label}.${key}`);
};
function stats(rows, key) {
  const values = rows.map(row => row[key]).filter(Number.isFinite);
  return values.length ? { count: values.length, signedSum: values.reduce((a, b) => a + b, 0),
    absoluteSum: values.reduce((a, b) => a + Math.abs(b), 0), maximumAbsolute: values.reduce((a, b) => Math.max(a, Math.abs(b)), 0) } : null;
}

export function auditConservation(records, fluxByPatch = {}, coverage = {}) {
  const { states, equations, times } = records;
  const issues = [], steps = [], fluxMaps = {};
  if (states.length < 2) issues.push('Fewer than two completed energy states');
  for (const [patch, rows] of Object.entries(fluxByPatch)) {
    const map = new Map();
    for (const row of rows) {
      const old = map.get(row.timeName);
      if (old && old.flux_kg_s !== row.flux_kg_s) throw new Error(`Conflicting repeated phi row for ${patch} at ${row.token}`);
      if (!old) map.set(row.timeName, { ...row, duplicateRows: [] });
      else old.duplicateRows.push(row);
    }
    fluxMaps[patch] = map;
  }
  let cumulativeEnergy = 0, cumulativeMass = 0, cumulativeMassKnown = 0;
  let energyComplete = states.length >= 2 && states[0].values.t === 0;
  let massComplete = energyComplete && Object.keys(fluxMaps).length > 0;
  let cumulativeEnergyThroughput = 0, cumulativeMassThroughput = 0;
  let timeCursor = 0, equationCursor = 0;
  for (let i = 1; i < states.length; ++i) {
    const prior = states[i - 1], current = states[i], a = prior.values, b = current.values;
    required(a, ['t', 'volume', 'mass', 'H', 'K', 'PV', 'E', 'Hchemical'], 'previous energyState');
    required(b, ['t', 'volume', 'mass', 'H', 'K', 'PV', 'E', 'Hchemical'], 'energyState');
    if (!(b.t > a.t) || !(current.line > prior.line)) throw new Error('Nonmonotone/restarted energy history; segment the retained logs explicitly');
    if (a.volume !== b.volume) throw new Error('Moving/changed volume is outside this Euler audit');
    while (timeCursor < times.length && times[timeCursor].line <= prior.line) ++timeCursor;
    while (equationCursor < equations.length && equations[equationCursor].line <= prior.line) ++equationCursor;
    const markers = [], outer = [];
    while (timeCursor < times.length && times[timeCursor].line < current.line) markers.push(times[timeCursor++]);
    while (equationCursor < equations.length && equations[equationCursor].line < current.line) outer.push(equations[equationCursor++]);
    const row = { index: i, previousTime_s: a.t, time_s: b.t, dt_s: b.t - a.t,
      stateLine: current.line, timeMarkers: markers, outerEquationLines: outer.map(e => e.line),
      energyStatus: 'missing-step-or-equation', massStatus: 'missing-step-or-flux' };
    steps.push(row);
    if (markers.length !== 1 || !outer.length || outer.some(e => e.values.t !== b.t)) {
      energyComplete = massComplete = false;
      issues.push(`Step ending ${b.t}: expected one Time marker and matching outer energy equations`);
      continue;
    }
    const q = outer.at(-1).values, dt = row.dt_s;
    required(q, ['ddtW', 'convectionW', 'diffusionW', 'kineticW', 'pressureW', 'sourceW', 'residualW', 'residualL1W'], 'energyEquation');
    const deltaH = b.H - a.H, deltaK = b.K - a.K, deltaPV = b.PV - a.PV, deltaE = b.E - a.E;
    const kineticFluxEstimate = q.kineticW - deltaK / dt;
    const terms = q.ddtW + q.convectionW + q.diffusionW + q.kineticW + q.pressureW - q.sourceW;
    const enthalpyLag = deltaH - dt * q.ddtW, pressureLag = -deltaPV - dt * q.pressureW;
    const energyDefect = deltaE + dt * (q.convectionW + q.diffusionW + kineticFluxEstimate - q.sourceW);
    const throughput = dt * (Math.abs(q.convectionW) + Math.abs(q.diffusionW) + Math.abs(kineticFluxEstimate) + Math.abs(q.sourceW));
    const sensibleScale = Math.abs(b.H - b.Hchemical) + Math.abs(b.K) + Math.abs(b.PV);
    cumulativeEnergy += energyDefect; cumulativeEnergyThroughput += throughput;
    Object.assign(row, { energyStatus: 'accounted-with-staging-limitations', selectedEquationLine: outer.at(-1).line,
      timeName: markers[0].token, printedTimeOffset_s: markers[0].value - b.t,
      deltaH_J: deltaH, deltaK_J: deltaK, deltaPV_J: deltaPV, deltaE_J: deltaE,
      kineticBoundaryPowerEstimate_W: kineticFluxEstimate, equationTermSum_W: terms,
      loggedEquationResidual_W: q.residualW, loggedEquationResidualL1_W: q.residualL1W,
      equationTermMinusResidual_W: terms - q.residualW,
      assembledTermDefect_J: dt * terms, loggedEquationDefect_J: dt * q.residualW,
      enthalpyCouplingDifference_J: enthalpyLag, pressureCouplingDifference_J: pressureLag,
      finalStateEnergyDefect_J: energyDefect,
      decompositionArithmeticDifference_J: energyDefect - (dt * terms + enthalpyLag + pressureLag),
      storedEnergyIdentityDifference_J: b.E - (b.H + b.K - b.PV),
      energyThroughputScale_J: throughput, sensibleInventoryScale_J: sensibleScale,
      defectPerThroughput: ratio(energyDefect, throughput), defectPerSensibleInventory: ratio(energyDefect, sensibleScale),
      cumulativeEnergyDefect_J: energyComplete ? cumulativeEnergy : null,
      knownEnergyDefectSum_J: cumulativeEnergy,
      cumulativeDefectPerThroughput: energyComplete ? ratio(cumulativeEnergy, cumulativeEnergyThroughput) : null });
    const patchRows = {}, missing = [];
    for (const [patch, map] of Object.entries(fluxMaps)) {
      const sample = map.get(markers[0].value);
      if (!sample) missing.push(patch); else patchRows[patch] = sample;
    }
    row.patchFluxSamples = patchRows; row.missingFluxPatches = missing;
    if (!Object.keys(fluxMaps).length || missing.length) {
      massComplete = false; issues.push(`Step ending ${b.t}: missing phi for ${missing.join(', ') || 'all patches'}`); continue;
    }
    const netFlux = Object.values(patchRows).reduce((sum, item) => sum + item.flux_kg_s, 0);
    const flowScale = dt * Object.values(patchRows).reduce((sum, item) => sum + Math.abs(item.flux_kg_s), 0);
    const massDefect = b.mass - a.mass + dt * netFlux;
    cumulativeMass += massDefect; cumulativeMassKnown += dt * netFlux; cumulativeMassThroughput += flowScale;
    Object.assign(row, { massStatus: 'sampled-patches-accounted', netOutwardMassFlow_kg_s: netFlux,
      eulerBoundaryMass_kg: dt * netFlux, finalStateMassDefect_kg: massDefect,
      massThroughputScale_kg: flowScale, massDefectPerThroughput: ratio(massDefect, flowScale),
      massDefectPerInventory: ratio(massDefect, Math.abs(a.mass)),
      cumulativeMassDefect_kg: massComplete ? cumulativeMass : null, knownMassDefectSum_kg: cumulativeMass,
      cumulativeEulerBoundaryMass_kg: massComplete ? cumulativeMassKnown : null,
      cumulativeMassDefectPerThroughput: massComplete ? ratio(cumulativeMass, cumulativeMassThroughput) : null });
  }
  const trailingTimes = times.filter(row => row.line > (states.at(-1)?.line ?? 0));
  const statistics = {};
  for (const key of ['finalStateEnergyDefect_J', 'enthalpyCouplingDifference_J', 'pressureCouplingDifference_J',
    'assembledTermDefect_J', 'loggedEquationDefect_J', 'equationTermMinusResidual_W', 'finalStateMassDefect_kg']) statistics[key] = stats(steps, key);
  return { schema: 'g2-discrete-conservation-v1', status: energyComplete && massComplete ? 'sampled-history-accounted' : 'incomplete-evidence',
    scientificAcceptance: false, startsAtZero: states[0]?.values.t === 0,
    completedThroughTime_s: states.at(-1)?.values.t ?? null, trailingTimes,
    energyHistoryComplete: energyComplete, massSampleHistoryComplete: massComplete,
    boundaryCoverage: coverage, allBoundaryFluxesIndependentlyVerified: false,
    kineticFluxQualification: 'Estimate subtracts final-state kinetic change from an earlier-stage explicit term; kinetic staging error is not independently separable',
    cumulativeEnergyDefect_J: energyComplete ? cumulativeEnergy : null,
    cumulativeMassDefect_kg: massComplete ? cumulativeMass : null,
    issues, statistics, steps, records, fluxByPatch };
}
