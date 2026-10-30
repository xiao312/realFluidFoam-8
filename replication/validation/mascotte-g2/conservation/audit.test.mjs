import test from 'node:test';
import assert from 'node:assert/strict';
import { auditConservation, parseSolverLog, parseFlux } from './core.mjs';

// Independent ideal-gas receiving vessel: V=1, R=1, Cv=2, Cp=3,
// initial m=1,T=10; inlet mdot=1,T=10,U=2, no outlet/heat.
// Incoming total specific enthalpy=32, so E=22+32t and m=1+t.
// This gives PV=10+15t, H=30+45t,K=2+2t from the EOS/caloric laws.
const state = t => `energyState t=${t} volume=1 mass=${1 + t} H=${30 + 45 * t} K=${2 + 2 * t} PV=${10 + 15 * t} E=${22 + 32 * t} Hchemical=0`;
const equation = (t, ddt, pressure) => `energyEquation t=${t} ddtW=${ddt} convectionW=-30 diffusionW=0 kineticW=0 pressureW=${pressure} sourceW=0 residualW=0 residualL1W=0`;
const log = [state(0), 'Time = 0.125', equation(0.125, 43, -13), equation(0.125, 44, -14), state(0.125),
  'Time = 0.5', equation(0.5, 43, -13), equation(0.5, 44, -14), state(0.5), 'End'].join('\n');
const flux = { inlet: parseFlux('# Time sum(phi)\n0 -1\n0.125 -1\n0.5 -1\n', 'independent-vessel') };

test('open-vessel analytic first law with variable dt and final pressure staging', () => {
  const report = auditConservation(parseSolverLog(log), flux);
  assert.equal(report.energyHistoryComplete, true);
  assert.equal(report.massSampleHistoryComplete, true);
  assert.equal(report.cumulativeEnergyDefect_J, 0);
  assert.equal(report.cumulativeMassDefect_kg, 0);
  assert.deepEqual(report.steps.map(row => row.dt_s), [0.125, 0.375]);
  assert.deepEqual(report.steps.map(row => row.kineticBoundaryPowerEstimate_W), [-2, -2]);
  assert.deepEqual(report.steps.map(row => row.enthalpyCouplingDifference_J), [0.125, 0.375]);
  assert.deepEqual(report.steps.map(row => row.pressureCouplingDifference_J), [-0.125, -0.375]);
  assert.equal(report.records.equations.length, 4);
});

test('missing completed time is not replaced by a longer Euler step', () => {
  const records = parseSolverLog(log.replace(state(0.125) + '\n', ''));
  const report = auditConservation(records, flux);
  assert.equal(report.status, 'incomplete-evidence');
  assert.equal(report.cumulativeEnergyDefect_J, null);
  assert.equal(report.cumulativeMassDefect_kg, null);
  assert.equal(report.steps[0].finalStateEnergyDefect_J, undefined);
  assert.equal(report.steps[0].timeMarkers.length, 2);
  assert.equal(report.records.equations.length, 4);
});
