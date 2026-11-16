import { createHash } from 'node:crypto';

export const recipe=Object.freeze({schema:'g2-reviewed-legacy-injector/v1',
 oxygenUpstreamRadius_m:.0016,oxygenExitRadius_m:.0025,taperStart_m:.005,injectorExit_m:.01,
 methaneRadii_m:[.0028,.005],casingRadius_m:.0065,chamberRadius_m:.025,chamberLength_m:.2,
 halfAngle_deg:2.5,upstreamCells:40,nearAxialCells:100,farAxialCells:150,
 radialCells:[8,4,10,4,30],geometryQualified:false,
 referenceMeshSha256:'1802701301b481669595ffd4550f64cffbd40461bd4aedd8f15023e99a484de9',
 limitations:['Axisymmetric wedge, square-chamber corners absent','No nozzle or conjugate solid heat transfer','Legacy3.2mm upstream oxygen bore, not paper3.6mm']});
export const taperLength=.005;
export const hash = data => createHash('sha256').update(data).digest('hex');
export const header = name => `FoamFile { version 2.0; format ascii; class dictionary; object ${name}; }\n`;
export const patchTypes = { loxinlet: 'patch', ch4inlet: 'patch', outlet: 'patch',
  geom: 'wall', noslipwalls: 'wall', slipwalls: 'wall', axisymmetric: 'empty',
  planeMinus: 'wedge', planePlus: 'wedge' };

export function recipeForProfile(profile='standard') {
  if(profile==='standard')return recipe;
  if(profile==='debug-coarse')return Object.freeze({...recipe,
    upstreamCells:20,nearAxialCells:50,farAxialCells:75,
    radialCells:[4,2,5,2,15],resolutionProfile:'debug-coarse'});
  throw Error(`Unknown resolution profile ${profile}; use standard or debug-coarse`);
}

export function ductCellCounts(profile='standard') {
  const selected=recipeForProfile(profile);
  return {oxygen:2*selected.upstreamCells*selected.radialCells[0],
    methane:2*selected.upstreamCells*selected.radialCells[2]};
}

export function geometry(profile='standard') {
  const selected=recipeForProfile(profile);
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
  function block(x0,x1,r0,r1,s0,s1,nx,nr,grading=1) {
    const v=[point(x0,r0,-1),point(x1,s0,-1),point(x1,s1,-1),point(x0,r1,-1),
      point(x0,r0,1),point(x1,s0,1),point(x1,s1,1),point(x0,r1,1)];
    blocks.push({vertices:v,cells:[nx,nr,1],grading});
    patches.planeMinus.push([v[0],v[3],v[2],v[1]]);patches.planePlus.push([v[4],v[5],v[6],v[7]]);
    return {inlet:[v[0],v[4],v[7],v[3]],outlet:[v[1],v[2],v[6],v[5]],
      inner:[v[0],v[1],v[5],v[4]],outer:[v[3],v[7],v[6],v[2]]};
  }
  const radii=[0,.0025,.0028,.005,.0065,.025];
  for(let i=0;i<5;i++)for(const [x0,x1,nx,g]of [[.01,.03,selected.nearAxialCells,1],[.03,.2,selected.farAxialCells,4]]){
    const f=block(x0,x1,radii[i],radii[i+1],radii[i],radii[i+1],nx,selected.radialCells[i],g);
    if(x1===.2)patches.outlet.push(f.outlet);
    if(i===0)patches.axisymmetric.push(f.inner);
    if(i===4)patches.geom.push(f.outer);
    if(x0===.01&&(i===1||i===3))patches.noslipwalls.push(f.inlet);
  }
  for(const [x0,x1,r0,r1]of [[0,.005,.0016,.0016],[.005,.01,.0016,.0025]]){
    const o=block(x0,x1,0,r0,0,r1,selected.upstreamCells,selected.radialCells[0]);if(x0===0)patches.loxinlet.push(o.inlet);
    patches.axisymmetric.push(o.inner);patches.noslipwalls.push(o.outer);
    const f=block(x0,x1,.0028,.005,.0028,.005,selected.upstreamCells,selected.radialCells[2]);if(x0===0)patches.ch4inlet.push(f.inlet);
    patches.noslipwalls.push(f.inner,f.outer);
    const p=block(x0,x1,.0065,.025,.0065,.025,selected.upstreamCells,selected.radialCells[4]);if(x0===0)patches.slipwalls.push(p.inlet);
    patches.noslipwalls.push(p.inner);patches.geom.push(p.outer);
  }
  return {vertices,blocks,patches};
}

export function dictionary(profile='standard') {
  const g=geometry(profile),tuple=x=>`(${x.join(' ')})`;
  return header('blockMeshDict')+'convertToMeters 1;\nvertices\n(\n'+g.vertices.map(tuple).join('\n')+
    '\n);\nblocks\n(\n'+g.blocks.map(b=>`hex ${tuple(b.vertices)} ${tuple(b.cells)} simpleGrading (${b.grading} 1 1)`).join('\n')+
    '\n);\nedges ();\nboundary\n(\n'+Object.entries(g.patches).map(([name,faces])=>
      `${name} { type ${patchTypes[name]}; faces (${faces.map(tuple).join(' ')}); }`).join('\n')+
    '\n);\nmergePatchPairs ();\n';
}

export function plan(profile='standard'){
 const selected=recipeForProfile(profile),g=geometry(profile);
 return {recipe:selected,coordinateOrigin:'raw legacy x; injector exit at .01m',
 expectedCells:g.blocks.reduce((sum,b)=>sum+b.cells.reduce((a,n)=>a*n,1),0),
 paperAxialOrigin_m:.01,recipeSha256:hash(JSON.stringify(selected)),
 dictionarySha256:hash(dictionary(profile)),CFD_executed:false,meshToolsExecuted:false};}
