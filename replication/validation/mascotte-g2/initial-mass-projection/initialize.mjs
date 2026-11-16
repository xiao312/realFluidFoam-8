import {readFile,readdir,writeFile,access,realpath} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';

const [directory,executable,action]=process.argv.slice(2);
if(!directory||!executable||![undefined,'--apply'].includes(action)||process.argv.length>5)
  throw Error('Use FRESH_CASE HELPER_EXECUTABLE [--apply]; default read-only');
const root=await realpath(resolve(directory)),helper=await realpath(resolve(executable));
const hash=b=>createHash('sha256').update(b).digest('hex');
const listing=await readdir(root);
if(listing.some(n=>/^processor/.test(n)||(Number.isFinite(Number(n))&&Number(n)>0)))
  throw Error('Original-zero undecomposed case required');
for(const name of ['initial-mass-projection.json','initial-mass-projection-metrics.json','0/phi']){
  try{await access(`${root}/${name}`);}catch(e){if(e.code==='ENOENT')continue;throw e;}
  throw Error(`Existing ${name}; no repeated or evolved projection`);
}
const input=JSON.parse(await readFile(`${root}/direct-g2-input.json`));
if(input.startTime!==0||input.meshMode!=='reviewed-legacy-injector-v1')
  throw Error('Explicit reviewed-mesh original-zero binding required');
const inlet=JSON.parse(await readFile(`${root}/inlet-runtime-initialization.json`));
if(inlet.startTime!==0||inlet.CFD_steps!==0)throw Error('Executing EOS inlet initialization required');
async function snapshot(){
  const records={};
  async function walk(relative){
    for(const e of await readdir(`${root}/${relative}`,{withFileTypes:true})){
      const name=`${relative}/${e.name}`;
      if(e.isSymbolicLink())throw Error(`Symlink not supported in protected input: ${name}`);
      if(e.isDirectory())await walk(name);
      else if(e.isFile())records[name]=hash(await readFile(`${root}/${name}`));
    }
  }
  for(const name of ['0','constant','system'])await walk(name);
  return records;
}
const before=await snapshot(),helperSha256=hash(await readFile(helper));
const plan={schema:'g2-initial-mass-projection/v1',readOnly:action!=='--apply',case:root,
  helper,helperSha256,before,CFD_steps:0,evolvedStateUsed:false,
  allowedFieldChanges:['0/U','0/phi'],scientificAcceptance:false};
if(action==='--apply'){
  if(!process.env.SLURM_JOB_ID||!root.startsWith('/workspace/cases/'))
    throw Error('Apply only inside an admitted project case');
  const result=spawnSync(helper,['-case',root,'-apply'],{encoding:'utf8',maxBuffer:8*1024*1024});
  await writeFile(`${root}/initial-mass-projection.log`,(result.stdout??'')+(result.stderr??''),{flag:'wx'});
  if(result.error||result.status!==0)throw Error(`Projection failed; inspect retained log: ${result.error??result.status}`);
  const after=await snapshot();
  for(const name of new Set([...Object.keys(before),...Object.keys(after)]))
    if(!['0/U','0/phi'].includes(name)&&before[name]!==after[name])throw Error(`Protected input changed: ${name}`);
  if(!after['0/phi'])throw Error('Face flux absent');
  const metrics=JSON.parse(await readFile(`${root}/initial-mass-projection-metrics.json`));
  if(metrics.CFD_steps!==0||metrics.scientificAcceptance!==false
    ||!Number.isFinite(metrics.divergenceAfter_kg_s)||!(metrics.inward_kg_s>0)
    ||metrics.divergenceAfter_kg_s/metrics.inward_kg_s>1e-8
    ||Math.abs(metrics.netBoundary_kg_s)/metrics.inward_kg_s>1e-8)throw Error('Projection metrics failed');
  Object.assign(plan,{after,metrics});
  await writeFile(`${root}/initial-mass-projection.json`,JSON.stringify(plan,null,2)+'\n',{flag:'wx'});
}
console.log(JSON.stringify(plan,null,2));
