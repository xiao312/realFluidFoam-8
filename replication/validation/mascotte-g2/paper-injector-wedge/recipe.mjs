import { createHash } from 'node:crypto';

export const recipe = Object.freeze({
  schema: 'g2-tapered-injector-wedge/v1',
  oxygenUpstreamRadius_m: .0018, oxygenExitRadius_m: .0025,
  taperHalfAngle_deg: 10, methaneRadii_m: [.0028, .005],
  chamberRadius_m: .025, chamberLength_m: .2, halfAngle_deg: 2.5,
  upstreamCells: 40, axialCells: 200, radialCells: [8, 6, 10, 26],
  angleSource: 'Sharma2023 Figure3; interpreted as angle to the axis',
  geometryQualified: false, squareChamber: false,
  limitations: ['No upstream straight duct or precursor', 'No square chamber or nozzle',
    'Axisymmetric, coarse mesh; no LES qualification', 'No conjugate lip heat transfer'],
});
export const taperLength = (recipe.oxygenExitRadius_m-recipe.oxygenUpstreamRadius_m)
  / Math.tan(recipe.taperHalfAngle_deg*Math.PI/180);
export const hash = data => createHash('sha256').update(data).digest('hex');
export const header = name => `FoamFile { version 2.0; format ascii; class dictionary; object ${name}; }\n`;
export const patchTypes = { loxinlet: 'patch', ch4inlet: 'patch', outlet: 'patch',
  geom: 'wall', noslipwalls: 'wall', slipwalls: 'wall', axisymmetric: 'empty',
  planeMinus: 'wedge', planePlus: 'wedge' };

export function geometry() {
  const vertices=[], indices=new Map(), blocks=[];
  const patches=Object.fromEntries(Object.keys(patchTypes).map(name=>[name,[]]));
  const angle=recipe.halfAngle_deg*Math.PI/180;
  function point(x,r,side) {
    const key=`${x}/${r}/${r===0?0:side}`;
    if (!indices.has(key)) {
      indices.set(key,vertices.length);
      vertices.push([x,r*Math.cos(angle),side*r*Math.sin(angle)]);
    }
    return indices.get(key);
  }
  // Four chamber bands; the upstream solid separator is deliberately not meshed.
  function block(x0,x1,r0,r1,s0,s1,nx,nr) {
    const v=[point(x0,r0,-1),point(x1,s0,-1),point(x1,s1,-1),point(x0,r1,-1),
      point(x0,r0,1),point(x1,s0,1),point(x1,s1,1),point(x0,r1,1)];
    blocks.push({vertices:v,cells:[nx,nr,1]});
    patches.planeMinus.push([v[0],v[3],v[2],v[1]]);
    patches.planePlus.push([v[4],v[5],v[6],v[7]]);
    return {inlet:[v[0],v[4],v[7],v[3]],outlet:[v[1],v[2],v[6],v[5]],
      inner:[v[0],v[1],v[5],v[4]],outer:[v[3],v[7],v[6],v[2]]};
  }
  const radii=[0,.0025,.0028,.005,.025];
  for (let i=0;i<4;i++) {
    const f=block(0,.2,radii[i],radii[i+1],radii[i],radii[i+1],200,recipe.radialCells[i]);
    patches.outlet.push(f.outlet);
    if(i===0) patches.axisymmetric.push(f.inner);
    if(i===1) patches.geom.push(f.inlet);
    if(i===3) patches.noslipwalls.push(f.inlet,f.outer);
  }
  const oxygen=block(-taperLength,0,0,.0018,0,.0025,40,8);
  patches.loxinlet.push(oxygen.inlet);
  patches.axisymmetric.push(oxygen.inner);
  patches.geom.push(oxygen.outer);
  const methane=block(-taperLength,0,.0028,.005,.0028,.005,40,10);
  patches.ch4inlet.push(methane.inlet);
  patches.geom.push(methane.inner);
  patches.noslipwalls.push(methane.outer);
  return {vertices,blocks,patches};
}

export function dictionary() {
  const g=geometry(),tuple=x=>`(${x.join(' ')})`;
  return header('blockMeshDict')+'convertToMeters 1;\nvertices\n(\n'+g.vertices.map(tuple).join('\n')+
    '\n);\nblocks\n(\n'+g.blocks.map(b=>`hex ${tuple(b.vertices)} ${tuple(b.cells)} simpleGrading (1 1 1)`).join('\n')+
    '\n);\nedges ();\nboundary\n(\n'+Object.entries(g.patches).map(([name,faces])=>
      `${name} { type ${patchTypes[name]}; faces (${faces.map(tuple).join(' ')}); }`).join('\n')+
    '\n);\nmergePatchPairs ();\n';
}

export function plan() {
  return {recipe,taperLength_m:taperLength,coordinateOrigin:'injector exit x=0',
    upstreamPlane_m:-taperLength,expectedCells:10720,
    expectedFullInletArea_m2:{oxygen:Math.PI*.0018**2,methane:Math.PI*(.005**2-.0028**2)},
    recipeSha256:hash(JSON.stringify(recipe)),dictionarySha256:hash(dictionary()),
    CFD_executed:false,meshToolsExecuted:false};
}
