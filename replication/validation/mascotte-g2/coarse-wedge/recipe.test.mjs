import test from 'node:test';
import assert from 'node:assert/strict';
import { geometry, expectedInlet, expectedCounts, expectedPatchFaces,
  recipe, blockMeshDictionary } from './recipe.mjs';
import { faceArea, parsePoints, parseFaces, parseLabels } from './ascii-mesh.mjs';

const localFaces = [[0,4,7,3], [1,2,6,5], [0,1,5,4], [3,7,6,2], [0,3,2,1], [4,5,6,7]];
const faceKey = labels => [...new Set(labels)].sort((a,b) => a-b).join(',');
test('actual recipe has positive blocks, matched interfaces and complete external patches', () => {
  const { vertices, blocks, patches } = geometry(), all = new Map();
  assert.equal(vertices.length, 18);
  assert.equal(blocks.reduce((sum,b) => sum+b.cells.reduce((a,v) => a*v,1),0), expectedCounts.cells);
  let totalVolume = 0;
  for (const block of blocks) {
    let volume = 0;
    for (const local of localFaces) {
      const labels = local.map(n => block.vertices[n]);
      if (new Set(labels).size < 3) continue;
      const v = labels.map(n => vertices[n]), area = faceArea(v);
      volume += v[0].reduce((sum, coordinate, k) => sum+coordinate*area[k],0)/3;
      const key = faceKey(labels); all.set(key,(all.get(key) ?? 0)+1);
    }
    assert.ok(volume > 0, 'vertex ordering must give positive oriented volume');
    totalVolume += volume;
  }
  assert.equal([...all.values()].filter(v=>v===2).length,3);
  const exterior = new Set([...all].filter(([,count])=>count===1).map(([key])=>key));
  for (const faces of Object.values(patches)) for (const face of faces) {
    if (new Set(face).size < 3) continue;
    assert.ok(exterior.delete(faceKey(face)), 'boundary face must exist once and be external');
  }
  assert.equal(exterior.size,0);
  const expectedVolume=.5*.025**2*Math.sin(5*Math.PI/180)*.2;
  assert.ok(Math.abs(totalVolume/expectedVolume-1)<1e-13);
  for (const name of ['loxinlet','ch4inlet']) {
    const area=faceArea(patches[name][0].map(n=>vertices[n]));
    assert.ok(area[0]<0);
    assert.ok(Math.abs(Math.hypot(...area)/expectedInlet(name).area-1)<1e-13);
  }
  assert.equal(Object.values(expectedPatchFaces).reduce((a,b)=>a+b,0),expectedCounts.faces-expectedCounts.internalFaces);
  assert.equal(recipe.axialCells*(recipe.radialCells.reduce((a,b)=>a+b,0)-1)+
    (recipe.axialCells-1)*recipe.radialCells.reduce((a,b)=>a+b,0),expectedCounts.internalFaces);
  assert.match(blockMeshDictionary(),/axisymmetric \{ type empty;/);
});

test('narrow ASCII reader rejects nonfinite points, wrong labels and binary data', () => {
  const head='FoamFile {format ascii; class vectorField;}\n';
  assert.deepEqual(parsePoints(Buffer.from(head+'2((0 0 0)(.2 1e-3 -1e-4))')),[[0,0,0],[.2,.001,-.0001]]);
  assert.throws(()=>parsePoints(Buffer.from(head+'1((NaN 0 0))')),/Nonfinite/);
  assert.throws(()=>parseFaces(Buffer.from(head+'1(3(0 1 2))'),2),/outside range/);
  assert.throws(()=>parseLabels(Buffer.from(head+'1(-1)')),/nonnegative/);
  assert.throws(()=>parsePoints(Buffer.from(head.replace('ascii','binary')+'0()')),/ASCII/);
});
