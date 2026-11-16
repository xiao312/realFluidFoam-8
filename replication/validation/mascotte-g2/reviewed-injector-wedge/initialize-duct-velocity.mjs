import {readFile,readdir,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {parsePoints,parseFaces,parseLabels} from '../coarse-wedge/ascii-mesh.mjs';
import {readMesh} from './mesh.mjs';
import {recipe,hash,ductCellCounts} from './recipe.mjs';

const [directory,action]=process.argv.slice(2);
if(!directory||![undefined,'--apply'].includes(action)||process.argv.length>4)
  throw Error('Use FRESH_CASE [--apply]; default read-only');
const root=resolve(directory),listing=await readdir(root);
if(listing.includes('duct-velocity-initialization.json')||listing.some(n=>/^processor/.test(n)||(Number.isFinite(Number(n))&&Number(n)>0)))
  throw Error('Fresh undecomposed case with no prior velocity priming required');
const manifestPath=`${root}/direct-g2-input.json`,manifestRaw=await readFile(manifestPath),input=JSON.parse(manifestRaw);
if(input.startTime!==0||input.meshMode!=='reviewed-legacy-injector-v1'||!input.requiresDuctPriming)
  throw Error('Original-zero explicitly bound tapered-injector case required');
const profile=input.mesh.resolutionProfile??'standard';
const mesh=await readMesh(`${root}/constant/polyMesh`,profile);
if(mesh.meshSha256!==input.mesh.meshSha256)throw Error('Mesh differs from the case binding');
const inletRaw=await readFile(`${root}/inlet-runtime-initialization.json`),inlet=JSON.parse(inletRaw);
const boundaryRaw=await readFile(`${root}/ha-initialization-boundaries.csv`);
if(inlet.startTime!==0||inlet.CFD_steps!==0||inlet.initializerBoundarySha256!==hash(boundaryRaw))
  throw Error('Executing EOS inlet receipt is absent, changed or not a time-zero result');
const streams={};
for(const name of ['loxinlet','ch4inlet']){
  const matches=inlet.inlets.filter(s=>s.name===name);
  if(matches.length!==1)throw Error(`Missing unique executing inlet ${name}`);
  const state=matches[0],declared=input.streams[name],area=mesh.patches[name].area;
  if(![state.density_kg_m3,state.massFlow_kg_s,state.velocity_m_s,area].every(v=>Number.isFinite(v)&&v>0)
    ||Math.abs(state.massFlow_kg_s/declared.massFlow_kg_s-1)>1e-12
    ||Math.abs(state.area_m2/area-1)>1e-10
    ||Math.abs(state.velocity_m_s*state.density_kg_m3*area/state.massFlow_kg_s-1)>1e-12)
    throw Error(`Executing mass-flow/area/density mismatch for ${name}`);
  streams[name]=state;
}
const raw=Object.fromEntries(await Promise.all(['points','faces','owner','neighbour'].map(async name=>[name,await readFile(`${root}/constant/polyMesh/${name}`)])));
const points=parsePoints(raw.points),faces=parseFaces(raw.faces,points.length),owner=parseLabels(raw.owner),neighbour=parseLabels(raw.neighbour);
const count=mesh.cellCount,vertices=Array.from({length:count},()=>new Set());
faces.forEach((face,i)=>{for(const id of face){vertices[owner[i]].add(id);if(i<neighbour.length)vertices[neighbour[i]].add(id);}});
const file=`${root}/0/U`,before=await readFile(file),text=before.toString();
if(!/\bclass\s+volVectorField\s*;/.test(text)||!/^internalField\s+uniform\s+\(0\s+0\s+0\)\s*;/m.test(text))
  throw Error('Expected original uniform zero internal U; no evolved velocity may be imported');
const boundary=text.slice(text.indexOf('boundaryField'));
if(!boundary.includes('type flowRateInletVelocity;'))throw Error('Declared mass-flow velocity boundaries required');
const values=Array.from({length:count},()=>[0,0,0]),counts={oxygen:0,methane:0};
let minOxygen=Infinity,maxOxygen=0,maxRadial=0;
const taperSlope=(recipe.oxygenExitRadius_m-recipe.oxygenUpstreamRadius_m)/(.01-.005),sine=Math.sin(2*recipe.halfAngle_deg*Math.PI/180);
for(let i=0;i<count;i++){
  const ids=[...vertices[i]],center=[0,0,0];
  for(const id of ids)for(let k=0;k<3;k++)center[k]+=points[id][k]/ids.length;
  const [x,y,z]=center,r=Math.hypot(y,z);
  if(x>=.01-1e-10||r>.0051)continue;
  if(x < -1e-10)throw Error('Unexpected upstream cell extent');
  if(r<.0026){
    const slope=x<.005?0:taperSlope;
    const radius=recipe.oxygenUpstreamRadius_m+Math.max(0,x-.005)*slope;
    if(!(radius>0&&r<radius))throw Error('Oxygen cell outside taper');
    const state=streams.loxinlet,area=.5*sine*radius**2;
    const axial=state.massFlow_kg_s/(state.density_kg_m3*area),radial=axial*r*slope/radius;
    values[i]=[axial,r?radial*y/r:0,r?radial*z/r:0];
    minOxygen=Math.min(minOxygen,axial);maxOxygen=Math.max(maxOxygen,axial);maxRadial=Math.max(maxRadial,radial);counts.oxygen++;
  }else{
    if(r<recipe.methaneRadii_m[0]*Math.cos(recipe.halfAngle_deg*Math.PI/180)-1e-10||r>recipe.methaneRadii_m[1])
      throw Error('Methane cell outside annulus');
    values[i]=[streams.ch4inlet.velocity_m_s,0,0];counts.methane++;
  }
}
const expected=ductCellCounts(profile);
if(counts.oxygen!==expected.oxygen||counts.methane!==expected.methane)throw Error('Duct cell counts differ from qualified geometry');
if(values.some(v=>v.some(x=>!Number.isFinite(x))))throw Error('Nonfinite analytic initial velocity');
const after=text.replace(/^internalField\s+uniform\s+\(0\s+0\s+0\)\s*;/m,
  `internalField nonuniform List<vector>\n${count}\n(\n${values.map(v=>`(${v.join(' ')})`).join('\n')}\n);`);
if(after.slice(after.indexOf('boundaryField'))!==boundary)throw Error('Velocity boundary conditions changed');
const report={schema:'g2-analytic-duct-velocity/v1',startTime:0,CFD_steps:0,counts,
  model:'constant-density mass-flow-consistent plug/taper analytic profile; chamber and outer pocket at rest',
  centerEvaluation:'arithmetic mean of actual cell vertices; no discrete projection claimed',
  oxygenAxialRange_m_s:[minOxygen,maxOxygen],oxygenMaxRadial_m_s:maxRadial,
  methaneAxial_m_s:streams.ch4inlet.velocity_m_s,streams,
  beforeUSha256:hash(before),afterUSha256:hash(after),meshSha256:mesh.meshSha256,
  inletReceiptSha256:hash(inletRaw),originalManifestSha256:hash(manifestRaw),
  initialKineticEnergyChanged:true,HaChanged:false,thermodynamicFieldsChanged:false,
  boundaryConditionsChanged:false,chamberVelocityChanged:false,evolvedStateUsed:false,
  scientificAcceptance:false,steadyFlowClaimed:false};
if(action==='--apply'){
  if(!process.env.SLURM_JOB_ID||!root.startsWith('/workspace/cases/'))throw Error('Apply only inside admitted project case');
  await writeFile(`${root}/duct-velocity-initialization.json`,JSON.stringify(report,null,2)+'\n',{flag:'wx'});
  await writeFile(file,after);
  input.initialVelocity=report;await writeFile(manifestPath,JSON.stringify(input,null,2)+'\n');
}
console.log(JSON.stringify({readOnly:action!=='--apply',...report},null,2));
