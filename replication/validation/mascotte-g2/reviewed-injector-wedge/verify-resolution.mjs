// Geometry/default-compatibility checks only; executed mesh audit remains required.
import assert from 'node:assert/strict';
import {plan,geometry,ductCellCounts} from './recipe.mjs';

const standard=plan(),coarse=plan('debug-coarse');
assert.equal(standard.expectedCells,17840);
assert.equal(standard.recipeSha256,'ee1cc2cfb22ebb64285b808b72292c52448b3a0890e6ee56bb0ade040adfc4cb');
assert.equal(standard.dictionarySha256,'236a597cebe24c9a75bc0352996a1751fd46681408943e416fac08a62058d5b4');
assert.equal(coarse.expectedCells,4460);
assert.notEqual(coarse.recipeSha256,standard.recipeSha256);
assert.notEqual(coarse.dictionarySha256,standard.dictionarySha256);
const a=geometry(),b=geometry('debug-coarse');
assert.deepEqual(a.vertices,b.vertices);
assert.deepEqual(a.patches,b.patches);
assert.deepEqual(a.blocks.map(({cells,...g})=>g),b.blocks.map(({cells,...g})=>g));
assert.deepEqual(ductCellCounts(),{oxygen:640,methane:800});
assert.deepEqual(ductCellCounts('debug-coarse'),{oxygen:160,methane:200});
assert.throws(()=>plan('unknown'),/Unknown resolution profile/);
console.log(JSON.stringify({standard,coarse,geometryDefinitionsIdentical:true,
  defaultIdentityUnchanged:true,meshToolsExecuted:false,scientificAcceptance:false},null,2));
