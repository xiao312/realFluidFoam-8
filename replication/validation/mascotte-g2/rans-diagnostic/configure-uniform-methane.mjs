import {readFile,readdir,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
const [directory,action]=process.argv.slice(2),apply=action==='--apply';
if(!directory||![undefined,'--apply'].includes(action))throw Error('Use CASE [--apply]');
const root=resolve(directory),names=await readdir(root),sha=b=>createHash('sha256').update(b).digest('hex');
const raw=await readFile(root+'/direct-g2-input.json'),m=JSON.parse(raw);
if(m.startTime!==0||m.pressure!==5610000||m.closure!=='fgm'||!m.ransDiagnostic||
  m.uniformMethaneControl||names.some(n=>n.startsWith('processor')||n.startsWith('cold-initialization')||
    (Number.isFinite(Number(n))&&Number(n)>0)))throw Error('Fresh 5.61MPa RANS FGM case before Ha initialization required');
if(m.streams.ch4inlet.temperature!==288||m.streams.loxinlet.temperature!==85||
  m.initial.z!==1||m.initial.c!==0)throw Error('Original cold uniform-CH4 chamber control required');
const control=await readFile(root+'/system/controlDict','utf8');
const ignition=Number(/fgmIgnitionTime\s+([^;]+);/.exec(control)?.[1]);
if(!(Number.isFinite(ignition)&&ignition>m.endTime))throw Error('Chemistry must be paused beyond the declared endpoint');
const rhoCH4=41.75775004549757,rhoO2=1181.226802270155;
const originalLox=m.streams.loxinlet,flow=originalLox.massFlow_kg_s*rhoCH4/rhoO2;
const changed={},original={};
function scalar(text,value){
  const field=/internalField\s+(?:uniform\s+[^;]+|nonuniform\s+List<scalar>\s+\d+\s*\([^]*?\))\s*;/;
  if(!field.test(text))throw Error('Missing initial scalar field');
  return text.replace(field,`internalField uniform ${value};`)
    .replace(/\b(value|inletValue)\s+uniform\s+[^;]+;/g,(_,key)=>`${key} uniform ${value};`);
}
const table=await readFile(root+'/constant/physical.tbl','utf8');
const species=/^species\s+(.+)$/m.exec(table)?.[1].trim().split(/\s+/);
if(!species?.includes('CH4'))throw Error('Physical table species header required');
for(const name of [...species,'T','Z','c']){
  const path='0/'+name,text=await readFile(root+'/'+path,'utf8');original[path]=text;
  changed[path]=scalar(text,name==='T'?288:(name==='CH4'||name==='Z'?1:0));
}
const upath='0/U',u=await readFile(root+'/'+upath,'utf8');original[upath]=u;
const patch=/(loxinlet\s*\{)([^{}]+)(\})/,match=patch.exec(u);
if(!match||!/massFlowRate\s+[\d.eE+-]+\s*;/.test(match[2]))throw Error('Original constant LOX-named mass flow required');
changed[upath]=u.replace(patch,`$1${match[2].replace(/massFlowRate\s+[^;]+;/,`massFlowRate ${flow};`)}$3`);
m.streams.loxinlet={...m.streams.ch4inlet,massFlow_kg_s:flow,
  fullAnnulusMassFlow_kg_s:originalLox.fullAnnulusMassFlow_kg_s*rhoCH4/rhoO2,
  meanVelocity_m_s:flow/(m.mesh.patches.loxinlet.area*rhoCH4),density:rhoCH4,
  estimateQualification:'Executing qualified pure-methane reference; refreshed again by the actual inlet initializer'};
const report={schema:'g2-uniform-methane-control/v1',CFDStart:0,CFD_steps:0,
  chemistryPausedRequired:true,temperature_K:288,pressure_Pa:5610000,composition:'pure CH4',
  loxNamedPassageNowContainsMethane:true,executingReferenceDensities_kg_m3:{CH4:rhoCH4,O2:rhoO2},
  newLoxNamedMassFlow_kg_s:flow,volumeInletVelocitiesPreserved:true,
  densityReference:'Qualified309 runtime pure-stream properties at original85/288K/5.61MPa',
  baselineManifestSha256:sha(raw),scientificAcceptance:false,acceptanceChanged:false,
  changes:Object.keys(changed).map(p=>({path:p,beforeSha256:sha(original[p]),afterSha256:sha(changed[p])}))};
m.uniformMethaneControl=report;
m.approximations.push('Uniform288K methane in both passages and chamber: single-fluid numerical isolation, not G2');
if(apply){
  if(!process.env.SLURM_JOB_ID||!root.startsWith('/workspace/cases/'))throw Error('Admitted project case required');
  await writeFile(root+'/uniform-methane-control.json',JSON.stringify(report,null,2)+'\n',{flag:'wx'});
  for(const p of Object.keys(changed))await writeFile(root+'/'+p,changed[p]);
  await writeFile(root+'/direct-g2-input.json',JSON.stringify(m,null,2)+'\n');
}
console.log(JSON.stringify({readOnly:!apply,...report},null,2));
