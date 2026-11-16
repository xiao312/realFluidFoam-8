import test from 'node:test';
import assert from 'node:assert/strict';
import {geometry,taperLength,plan} from './recipe.mjs';
import {faceArea} from '../coarse-wedge/ascii-mesh.mjs';

test('tapered fluid topology, interfaces, boundary partition and inlet geometry',()=>{
  const g=geometry(),faces=new Map(),local=[[0,4,7,3],[1,2,6,5],[0,1,5,4],[3,7,6,2],[0,3,2,1],[4,5,6,7]];
  const key=f=>[...new Set(f)].sort((a,b)=>a-b).join(',');
  let cells=0;
  for(const b of g.blocks) {
    let volume=0;cells+=b.cells.reduce((a,v)=>a*v,1);
    for(const face of local.map(f=>f.map(i=>b.vertices[i]))) {
      if(new Set(face).size<3) continue;
      const points=face.map(i=>g.vertices[i]),area=faceArea(points);
      volume+=points[0].reduce((a,x,k)=>a+x*area[k],0)/3;
      faces.set(key(face),(faces.get(key(face))??0)+1);
    }
    assert.ok(volume>0);
  }
  assert.equal(cells,plan().expectedCells);
  assert.equal([...faces.values()].filter(n=>n===2).length,5);
  const external=new Set([...faces].filter(([,n])=>n===1).map(([k])=>k));
  for(const patch of Object.values(g.patches)) for(const f of patch) {
    if(new Set(f).size>=3) assert.ok(external.delete(key(f)), 'exactly one exterior patch');
  }
  assert.equal(external.size,0);
  assert.ok(Math.abs(taperLength-.003969897273732397)<1e-14);
  for(const [name,radii] of [['loxinlet',[0,.0018]],['ch4inlet',[.0028,.005]]]) {
    const points=g.patches[name][0].map(i=>g.vertices[i]);
    assert.ok(points.every(p=>p[0]===-taperLength));
    const area=faceArea(points);
    assert.ok(area[0]<0);
    const expected=(radii[1]**2-radii[0]**2)*Math.sin(5*Math.PI/180)/2;
    assert.ok(Math.abs(Math.hypot(...area)/expected-1)<1e-13);
  }
});
