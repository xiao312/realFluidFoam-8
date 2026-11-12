import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { parsePoints, parseFaces, parseBoundary, faceArea } from '../../validation/mascotte-g2/coarse-wedge/ascii-mesh.mjs';

const [directory, mode='--plan']=process.argv.slice(2);
if(!directory||!['--plan','--apply'].includes(mode))throw Error('Usage: apply_inlet.mjs CASE [--plan|--apply]');
const root=path.resolve(directory),mesh=path.join(root,'constant/polyMesh');
for(const file of fs.readdirSync(root))if(/^\d/.test(file)&&file!=='0')throw Error('Refusing evolved CFD case');
const bytes=Object.fromEntries(['points','faces','boundary'].map(n=>[n,fs.readFileSync(path.join(mesh,n))]));
const points=parsePoints(bytes.points),faces=parseFaces(bytes.faces,points.length),patch=parseBoundary(bytes.boundary).fuel;
if(!patch||patch.type!=='patch'||patch.faces!==60)throw Error('Unexpected fuel patch topology');
const values=[],areas=[];
for(const face of faces.slice(patch.startFace,patch.startFace+patch.faces)){
  const v=face.map(i=>points[i]);let area=0;const centre=[0,0,0];
  for(let j=1;j<v.length-1;j++){
    const triangle=[v[0],v[j],v[j+1]];
    const weight=Math.hypot(...faceArea(triangle));
    area+=weight;
    for(let k=0;k<3;k++)centre[k]+=weight*(v[0][k]+v[j][k]+v[j+1][k])/3;
  }
  for(let k=0;k<3;k++)centre[k]/=area;
  const r2=centre[1]**2+centre[2]**2;
  const u=.23*(1-r2/.006**2);
  if(!(area>0)||!Number.isFinite(u)||u<0||u>.23||Math.abs(centre[0])>1e-12)throw Error('Invalid inlet face geometry');
  values.push(u);areas.push(area);
}
const receipt={schema:'maders-parabolic-inlet/v1',faces:values.length,
  area_m2:areas.reduce((a,b)=>a+b,0),
  mean_velocity_m_s:values.reduce((sum,u,i)=>sum+u*areas[i],0)/areas.reduce((a,b)=>a+b,0),
  nominal_continuum_mean_m_s:.115,maximum_velocity_m_s:Math.max(...values),
  formula:'U_x=.23*(1-r_faceCentre^2/.006^2)',
  mesh_hashes:Object.fromEntries(Object.entries(bytes).map(([n,b])=>[n,createHash('sha256').update(b).digest('hex')])),
  evolved_CFD_imported:false};
if(Math.abs(receipt.mean_velocity_m_s/.115-1)>.003)throw Error('Parabolic inlet quadrature differs materially from nominal flow');
console.log(JSON.stringify(receipt,null,2));
if(mode==='--apply'){
  const file=path.join(root,'0/U'),text=fs.readFileSync(file,'utf8');
  const placeholder='fuel { type fixedValue; value uniform (0.115 0 0); }';
  if(!text.includes(placeholder))throw Error('Missing fresh inlet placeholder');
  fs.writeFileSync(file,text.replace(placeholder,`fuel { type fixedValue; value nonuniform List<vector> ${values.length}\n(\n${values.map(u=>`(${u.toPrecision(17)} 0 0)`).join('\n')}\n); }`));
  fs.writeFileSync(path.join(root,'inlet-receipt.json'),JSON.stringify(receipt,null,2)+'\n');
}
