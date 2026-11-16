import {readFile,readdir,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
const [directory,action]=process.argv.slice(2),apply=action==='--apply';
if(!directory||![undefined,'--apply'].includes(action))throw Error('Use NEW_CASE [--apply]; default read-only');
const root=resolve(directory),sha=b=>createHash('sha256').update(b).digest('hex');
const manifest=JSON.parse(await readFile(`${root}/direct-g2-input.json`));
if(manifest.startTime!==0||(await readdir(root)).some(n=>n.startsWith('processor')||(Number.isFinite(Number(n))&&Number(n)>0)))
  throw Error('Fresh timezero initialization before decomposition required');
const raw=await readFile(`${root}/ha-initialization-boundaries.csv`),lines=raw.toString().trim().split(/\r?\n/);
const header=lines.shift().split(','),rows=lines.map(s=>Object.fromEntries(s.split(',').map((v,i)=>[header[i],i===0?v:Number(v)])));
const path=`${root}/0/U`,before=await readFile(path);let after=before.toString();const inlets=[];
for(const name of ['ch4inlet','loxinlet']) {
  const matches=rows.filter(r=>r.patch===name),stream=manifest.streams[name],geometry=manifest.mesh.patches[name];
  if(matches.length!==1)throw Error(`Expected one executing boundary state: ${name}`);
  const row=matches[0],flow=stream.massFlow_kg_s;
  if(![row.area_m2,row.rho_kg_m3,flow].every(x=>Number.isFinite(x)&&x>0)||
    Math.abs(row.area_m2/geometry.area-1)>1e-8||Math.abs(row.T_K-stream.temperature)>1e-6||Math.abs(row.p_Pa/manifest.pressure-1)>1e-10)
    throw Error(`Executing boundary state/area differs from input: ${name}`);
  const velocity=flow/(row.rho_kg_m3*row.area_m2),pattern=new RegExp(`(${name}\\s*\\{)([^{}]+)(\\})`),match=after.match(pattern);
  if(!match||!match[2].includes('type flowRateInletVelocity;'))throw Error('Expected original mass-flow boundary');
  const body=match[2].replace(/rhoInlet\s+[^;]+;/,`rhoInlet ${row.rho_kg_m3};`)
    .replace(/value\s+uniform\s+\([^)]*\);/,`value uniform (${velocity} 0 0);`);
  after=after.replace(pattern,`$1${body}$3`);
  inlets.push({name,massFlow_kg_s:flow,density_kg_m3:row.rho_kg_m3,area_m2:row.area_m2,velocity_m_s:velocity,T_K:row.T_K,p_Pa:row.p_Pa});
}
const report={schema:'g2-executing-inlet-initialization/v1',startTime:0,CFD_steps:0,
  beforeSha256:sha(before),afterSha256:sha(after),initializerBoundarySha256:sha(raw),inlets,
  massFlowChanged:false,HaChanged:false,internalVelocityChanged:false,scientificAcceptance:false};
if(apply){
  if(!process.env.SLURM_JOB_ID||!root.startsWith('/workspace/cases/'))throw Error('Apply only in the admitted project case directory');
  await writeFile(`${root}/inlet-runtime-initialization.json`,JSON.stringify(report,null,2)+'\n',{flag:'wx'});
  await writeFile(path,after);
}
console.log(JSON.stringify({readOnly:!apply,...report},null,2));
