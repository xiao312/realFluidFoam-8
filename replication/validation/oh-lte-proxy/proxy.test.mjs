import test from 'node:test';
import assert from 'node:assert/strict';
import { instantaneousProxy, averageProxies, validateSampling, excitationTemperature_K } from './proxy.mjs';
import { readCsv, mergeFields } from './csv.mjs';
const state = { x: .02, y: .004, z: 0, T: excitationTemperature_K/Math.log(2), rho: 2, OH: .01 };
const near = (a, b) => assert.ok(Math.abs(a-b) <= 2e-14*Math.max(1, Math.abs(b)), `${a} != ${b}`);

test('known exponent and molar units; OH is not relabelled as OH*', () => {
  const row = instantaneousProxy(state, 17);
  near(row.boltzmannFactor, .5);
  near(row.YOHstar_LTE_proxy, .005);
  near(row.cOH_mol_m3, 20/17);
  near(row.cOHstar_LTE_proxy_mol_m3, 10/17);
  assert.equal(instantaneousProxy({ ...state, OH: 0 }, 17).cOHstar_LTE_proxy_mol_m3, 0);
  assert.throws(() => instantaneousProxy({ ...state, rho: undefined }, 17), /rho/);
});

test('time weights act on instantaneous nonlinear proxies, not mean primitive fields', () => {
  const frames = [0, 1, 3].map((t, i) => ({ time_s: t,
    rows: [instantaneousProxy({ ...state, T: excitationTemperature_K/Math.log(2**(i+1)) }, 17)] }));
  const mean = averageProxies(frames)[0];
  near(mean.meanYOHstar_LTE_proxy, .01*((.5+.25)/2 + 2*(.25+.125)/2)/3);
  const averageT = (frames[0].rows[0].T_K+3*frames[1].rows[0].T_K+2*frames[2].rows[0].T_K)/6;
  assert.ok(Math.abs(mean.meanYOHstar_LTE_proxy-instantaneousProxy({ ...state, T: averageT }, 17).YOHstar_LTE_proxy) > 1e-5);
  frames[1].rows[0].x += .001;
  assert.throws(() => averageProxies(frames), /coordinates/);
});

test('missing/averaged/ambiguous producer data fail explicitly', () => {
  const good = { schema: 'oh-lte-samples/v1', sampling: { kind: 'instantaneous-cfd', instantaneous: true },
    provenance: { synthetic: true }, frames: [{ time_s: 0, files: ['synthetic.csv'] }], averaging: null };
  validateSampling(good);
  assert.throws(() => validateSampling({ ...good, sampling: { kind: 'time-mean', instantaneous: false } }), /instantaneous/);
  const a = readCsv('x,y,z,T,OH\n0,0,0,3000,0.01\n', 'synthetic-a');
  const b = readCsv('x,y,z,rho\n0,0,0,2\n', 'synthetic-b');
  assert.equal(mergeFields([a, b])[0].rho, 2);
  b[0].x = 1;
  assert.throws(() => mergeFields([a, b]), /coordinates/);
});
