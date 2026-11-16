import {readFile,readdir} from 'node:fs/promises';
import {resolve} from 'node:path';
import {parsePoints,parseFaces,parseLabels} from '../coarse-wedge/ascii-mesh.mjs';
import {scalarValues} from '../direct-fgm/diagnostics.mjs';
import {readMesh} from './mesh.mjs';
import {ductCellCounts} from './recipe.mjs';

const [directory]=process.argv.slice(2);
if(!directory||process.argv.length!==3)throw Error('Use verify-priming.mjs FRESH_CASE');
const root=resolve(directory),input=JSON.parse(await readFile(`${root}/direct-g2-input.json`));
if(input.startTime!==0||!input.requiresDuctPriming||(await readdir(root)).some(n=>n.startsWith('processor')||(Number.isFinite(Number(n))&&Number(n)>0)))
  throw Error('Fresh inlet-resolved timezero case before decomposition required');
// Verify the bound original mesh identity before using its geometry classification.
const profile=input.mesh.resolutionProfile??'standard';
const sourceMesh=await readMesh(`${root}/constant/polyMesh`,profile);
if(sourceMesh.meshSha256!==input.mesh.meshSha256)throw Error('Copied case mesh differs from the bound asset');
const raw=Object.fromEntries(await Promise.all(['points','faces','owner','neighbour'].map(async n=>[n,await readFile(`${root}/constant/polyMesh/${n}`)])));
const points=parsePoints(raw.points),faces=parseFaces(raw.faces,points.length),owner=parseLabels(raw.owner),neighbour=parseLabels(raw.neighbour);
const count=input.mesh.cellCount;
const vertices=Array.from({length:count},()=>new Set());
faces.forEach((face,i)=>{for(const point of face){vertices[owner[i]].add(point);if(i<neighbour.length)vertices[neighbour[i]].add(point);}});
const fields={};
for(const name of ['Z','c','T','O2','CH4']) {
  fields[name]=scalarValues(await readFile(`${root}/0/${name}`),name);
  if(fields[name].length!==1&&fields[name].length!==count)throw Error(`Wrong cell count in ${name}`);
}
const value=(name,i)=>fields[name][fields[name].length===1?0:i];
const counts={oxygen:0,methane:0};
for(let i=0;i<count;i++) {
  const ids=[...vertices[i]],centre=[0,0,0];
  for(const id of ids)for(let k=0;k<3;k++)centre[k]+=points[id][k]/ids.length;
  if(centre[0]>=.01-1e-10||Math.hypot(centre[1],centre[2])>.0051)continue;
  const oxygen=Math.hypot(centre[1],centre[2])<.0026,name=oxygen?'loxinlet':'ch4inlet',state=input.streams[name];
  for(const [field,expected] of [['Z',state.z],['c',state.c],['T',state.temperature],['O2',oxygen?1:0],['CH4',oxygen?0:1]])
    if(!Number.isFinite(value(field,i))||Math.abs(value(field,i)-expected)>1e-9)
      throw Error(`Unprimed ${name} cell${i}: ${field}=${value(field,i)}, expected${expected}`);
  counts[oxygen?'oxygen':'methane']++;
}
const expected=ductCellCounts(profile);
if(counts.oxygen!==expected.oxygen||counts.methane!==expected.methane||count!==sourceMesh.cellCount)throw Error('Duct cell classification differs from measured recipe');
console.log(JSON.stringify({schema:'g2-duct-priming-check/v1',time:0,counts,CFD_steps:0,fields_modified:false,
  mesh_sha256:input.mesh.meshSha256,scientific_acceptance:false},null,2));
