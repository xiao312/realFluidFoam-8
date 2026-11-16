import {readFile,readdir,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';

const [directory,flag,durationText,action]=process.argv.slice(2);
if(!directory||flag!=='--duration'||![undefined,'--apply'].includes(action))
  throw Error('Use CASE --duration SECONDS [--apply]; default read-only');
const root=resolve(directory),duration=Number(durationText),apply=action==='--apply';
const sha=b=>createHash('sha256').update(b).digest('hex');
const manifestPath=root+'/direct-g2-input.json',manifestBytes=await readFile(manifestPath);
const manifest=JSON.parse(manifestBytes),names=await readdir(root);
if(manifest.startTime!==0||manifest.meshMode!=='g2-tapered-injector-wedge-v1'||
  names.some(n=>n.startsWith('processor')||(Number.isFinite(Number(n))&&Number(n)>0)))
  throw Error('Original-zero undecomposed tapered-injector case required');
if(!(duration>0&&duration<manifest.endTime)||manifest.inletStartup)
  throw Error('Finite positive ramp duration below endTime and no previous ramp required');
const inletBytes=await readFile(root+'/inlet-runtime-initialization.json');
const inlet=JSON.parse(inletBytes),path=root+'/0/U',before=await readFile(path);
if(inlet.afterSha256!==sha(before)||inlet.CFD_steps!==0)
  throw Error('Executing-EOS boundary initialization must be the latest velocity operation');
if(!/internalField\s+uniform\s+\(0\s+0\s+0\)\s*;/.test(before.toString()))
  throw Error('Uniform stationary original velocity required; no passage priming');
let after=before.toString();
const finalTargets={};
for(const name of ['loxinlet','ch4inlet']){
  const flow=manifest.streams[name].massFlow_kg_s;
  if(!(Number.isFinite(flow)&&flow>0))throw Error('Invalid final mass flow');
  const pattern=new RegExp(`(${name}\\s*\\{)([^{}]+)(\\})`),match=after.match(pattern);
  if(!match||!match[2].includes('type flowRateInletVelocity;')||
    !/massFlowRate\s+[\d.eE+-]+\s*;/.test(match[2]))throw Error('Expected scalar mass-flow boundary');
  const body=match[2].replace(/massFlowRate\s+[^;]+;/,
    `massFlowRate table ((0 0) (${duration} ${flow}) (${manifest.endTime} ${flow}));`)
    .replace(/value\s+uniform\s+\([^)]*\);/,'value uniform (0 0 0);');
  after=after.replace(pattern,`$1${body}$3`);finalTargets[name]=flow;
}
manifest.inletStartup={mode:'linear-mass-flow-ramp-from-rest',duration_s:duration,
  finalTargets_kg_s:finalTargets,initialInternalVelocity_m_s:[0,0,0],
  baselineInletReceiptMeaning:'Executing-EOS density and full-flow velocity targets; ramp overrides actual initial boundary velocity to zero.',
  expectedInletFlow:'target*min(t/duration,1)',paperSteadyInletsOnlyAfter_s:duration};
const report={schema:'g2-inlet-ramp/v1',startTime:0,CFD_steps:0,
  beforeVelocitySha256:sha(before),afterVelocitySha256:sha(after),
  baselineManifestSha256:sha(manifestBytes),executingInletReceiptSha256:sha(inletBytes),
  startup:manifest.inletStartup,thermodynamicsChanged:false,acceptanceChanged:false,scientificAcceptance:false};
if(apply){
  if(!process.env.SLURM_JOB_ID||!root.startsWith('/workspace/cases/'))
    throw Error('Apply only in the admitted project case directory');
  await writeFile(root+'/inlet-ramp.json',JSON.stringify(report,null,2)+'\n',{flag:'wx'});
  await writeFile(path,after);await writeFile(manifestPath,JSON.stringify(manifest,null,2)+'\n');
}
console.log(JSON.stringify({readOnly:!apply,...report},null,2));
