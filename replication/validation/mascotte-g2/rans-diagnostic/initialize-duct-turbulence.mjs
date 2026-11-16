import {readFile,readdir,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';

const [directory,action]=process.argv.slice(2);
if(!directory||![undefined,'--apply'].includes(action)||process.argv.length>4)
  throw Error('Use FRESH_CASE [--apply]; default read-only');
const root=resolve(directory),sha=b=>createHash('sha256').update(b).digest('hex');
const names=await readdir(root);
if(names.includes('duct-turbulence-initialization.json')||names.some(n=>/^processor/.test(n)||(Number.isFinite(Number(n))&&Number(n)>0)))
  throw Error('Fresh undecomposed case with no prior turbulence priming required');
const manifestFile=root+'/direct-g2-input.json',manifestRaw=await readFile(manifestFile),manifest=JSON.parse(manifestRaw);
const config=manifest.ransDiagnostic?.config;
if(manifest.startTime!==0||manifest.meshMode!=='g2-tapered-injector-wedge-v1'||config?.model!=='kEpsilon'||config.transport!=='eddyDiffusivity')
  throw Error('Explicit original-zero inlet-resolved kEpsilon case required');
const velocityRaw=await readFile(root+'/0/U'),zRaw=await readFile(root+'/0/Z');
const primingRaw=await readFile(root+'/duct-velocity-initialization.json'),priming=JSON.parse(primingRaw);
if(priming.afterUSha256!==sha(velocityRaw)||priming.meshSha256!==manifest.mesh.meshSha256||priming.evolvedStateUsed!==false)
  throw Error('Actual primed velocity or mesh differs from bound receipt');
const inletRaw=await readFile(root+'/inlet-runtime-initialization.json'),inlet=JSON.parse(inletRaw);
if(sha(inletRaw)!==priming.inletReceiptSha256)throw Error('Executing inlet state changed');
const count=manifest.mesh.cellCount;
function list(raw,type,components){
  const text=raw.toString(),match=text.match(new RegExp(`internalField\\s+nonuniform\\s+List<${type}>\\s+(\\d+)\\s*\\(([\\s\\S]*?)\\)\\s*;`));
  if(!match||Number(match[1])!==count)throw Error('Explicit bound nonuniform '+type+' field required');
  const values=match[2].replace(/[()]/g,' ').trim().split(/\s+/).map(Number);
  if(values.length!==count*components||values.some(v=>!Number.isFinite(v)))throw Error('Wrong field count/nonfinite input');
  return values;
}
const velocity=list(velocityRaw,'vector',3),z=list(zRaw,'scalar',1),fields={},changed={},ranges={};
for(const field of ['k','epsilon','nut','alphat']){
  const bytes=await readFile(root+'/0/'+field),text=bytes.toString();
  if(sha(bytes)!==manifest.ransDiagnostic.files['0/'+field].afterSha256)
    throw Error('Turbulence field differs from original preparation: '+field);
  const match=text.match(/internalField\s+uniform\s+([^;]+);/);
  if(!match||!Number.isFinite(Number(match[1])))throw Error('Original uniform seed required');
  fields[field]={bytes,text,values:Array(count).fill(Number(match[1]))};
}
const counts={loxinlet:0,ch4inlet:0},cmu=.09;
for(let i=0;i<count;i++){
  const speed=Math.hypot(...velocity.slice(3*i,3*i+3));
  if(speed===0)continue; // Chamber is still the exact original zero-velocity seed.
  const stream=z[i]===0?'loxinlet':z[i]===1?'ch4inlet':null;
  if(!stream)throw Error('Moving cell is not a primed pure-stream passage');
  const state=inlet.inlets.filter(s=>s.name===stream);
  if(state.length!==1)throw Error('Missing executing pure-stream density');
  const {intensity,length_m:length}=config.inlets[stream],density=state[0].density_kg_m3;
  const k=1.5*(intensity*speed)**2,epsilon=cmu**.75*k**1.5/length;
  const nut=cmu*k*k/epsilon,alphat=density*nut/config.Prt;
  if(![k,epsilon,nut,alphat].every(v=>Number.isFinite(v)&&v>0))throw Error('Invalid declared turbulence state');
  for(const [key,value]of Object.entries({k,epsilon,nut,alphat}))fields[key].values[i]=value;
  counts[stream]++;
}
if(counts.loxinlet!==priming.counts.oxygen||counts.ch4inlet!==priming.counts.methane)
  throw Error('Turbulence and velocity passage classifications differ');
for(const [name,field]of Object.entries(fields)){
  changed[name]=field.text.replace(/internalField\s+uniform\s+[^;]+;/,
    `internalField nonuniform List<scalar>\n${count}\n(\n${field.values.join('\n')}\n);`);
  ranges[name]={minimum:Math.min(...field.values),maximum:Math.max(...field.values)};
}
const report={schema:'g2-primed-passage-turbulence/v1',startTime:0,CFD_steps:0,
  cells:count,ductCells:counts,ranges,formula:'k=1.5(I|U|)^2; epsilon=Cmu^0.75*k^1.5/L; nut=Cmu*k^2/epsilon; alphat=rho*nut/Prt',
  velocitySha256:sha(velocityRaw),mixtureFractionSha256:sha(zRaw),primingSha256:sha(primingRaw),
  originalManifestSha256:sha(manifestRaw),
  fields:Object.fromEntries(Object.entries(fields).map(([n,f])=>[n,{beforeSha256:sha(f.bytes),afterSha256:sha(changed[n])}])),
  chamberSeedsChanged:false,boundaryConditionsChanged:false,thermodynamicsChanged:false,
  tableOrChemistryChanged:false,scientificAcceptance:false,readOnly:action!=='--apply'};
if(action==='--apply'){
  if(!process.env.SLURM_JOB_ID||!root.startsWith('/workspace/cases/'))throw Error('Apply requires admitted case');
  for(const [name,value]of Object.entries(changed))await writeFile(root+'/0/'+name,value);
  await writeFile(root+'/duct-turbulence-initialization.json',JSON.stringify(report,null,2)+'\n',{flag:'wx'});
  manifest.initialTurbulence=report;await writeFile(manifestFile,JSON.stringify(manifest,null,2)+'\n');
}
console.log(JSON.stringify(report,null,2));
