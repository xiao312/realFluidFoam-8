import assert from 'node:assert/strict';
import { observationConfig, decompositionConfig, decompositionDictionary, functionObjects } from './observations.mjs';
import { scalarValues, differenceSummary } from './diagnostics.mjs';

const plain = observationConfig({}, 2e-5);
assert.equal(plain.averageStart_s, null);
assert.ok(!functionObjects(plain).includes('type fieldAverage'));
const measured = observationConfig({ profileInterval_s: 1e-6, fieldInterval_s: 1e-5,
  averageStart_s: 1e-5, imageGrid: { axialPoints: 3, radialPoints: 2 } }, 2e-5);
const text = functionObjects(measured);
assert.ok(text.includes('base time; mean yes; prime2Mean no;'));
assert.ok(text.includes('timeMeanImagePlane') && text.includes('fields (TMean rhoMean ZMean cMean OHMean)'));
assert.ok(text.includes('fields (T rho Z c OH)'));
assert.ok(measured.instantaneousFields.includes('rho'));
assert.ok(text.includes('type lineUniform;') && text.includes('type points; ordered no;'));
assert.ok(!text.includes('type uniform;') && !text.includes('type cloud;'));
assert.ok(text.indexOf('type fieldAverage') < text.indexOf('timeMeanProfiles'));
assert.throws(() => observationConfig({ averageStart_s: 2e-5 }, 2e-5), /Invalid/);
assert.throws(() => observationConfig({ averageStart: 0 }, 2e-5), /Unknown/);
assert.throws(() => observationConfig({ fieldInterval_s: 3e-6 }, 2e-5), /divide/);
assert.throws(() => decompositionConfig({ n: [8, 2, 2] }, 32), /wedge/);
assert.throws(() => decompositionConfig({ n: [8, 2, 1] }, 32), /multiply/);
const decomposition = decompositionConfig({ method: 'hierarchical', n: [8, 4, 1] }, 32);
assert.ok(decompositionDictionary(decomposition, 32).includes('n (8 4 1)'));
assert.equal(decompositionConfig({ method: 'scotch' }, 16).method, 'scotch');
const nonuniform = scalarValues('internalField nonuniform List<scalar> 2 (310 330);', 'T');
assert.deepEqual(differenceSummary(nonuniform, [300]), { cellArithmeticMean: 20,
  cellArithmeticRms: Math.sqrt(500), maxAbs: 30, count: 2 });
assert.throws(() => differenceSummary([1, 2], [1, 2, 3]), /sizes/);
assert.throws(() => scalarValues('internalField nonuniform List<scalar> 3 (1 2);', 'T'), /Count/);
console.log('Observation configuration and diagnostic parser checks passed; no physical validation claimed.');
