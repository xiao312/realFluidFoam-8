import {readFileSync,writeFileSync,mkdirSync,openSync,closeSync,existsSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';

const options={},args=process.argv.slice(2);
for(let i=0;i<args.length;i++) {
  if(args[i]==='--plan')options.plan=true;
  else if(['--mechanism','--runtime','--python','--source-commit','--environment-sha256','--out','--integration-config'].includes(args[i])&&args[i+1])
    options[args[i].slice(2)]=args[++i];
  else throw Error(`Unknown/missing option ${args[i]}`);
}
for(const name of ['mechanism','runtime','python','source-commit','environment-sha256','out'])
  if(!options[name])throw Error(`Missing --${name}`);
if(!/^[a-f0-9]{40}$/.test(options['source-commit'])||!/^[a-f0-9]{64}$/.test(options['environment-sha256']))throw Error('Require exact source/environment identities');
const here=dirname(fileURLToPath(import.meta.url)),driver=resolve(here,'../direct-flamelet');
const hash=path=>createHash('sha256').update(readFileSync(path)).digest('hex');
const out=resolve(options.out),runtime=resolve(options.runtime),mechanism=resolve(options.mechanism);
const integration=resolve(options['integration-config']??resolve(here,'quench.json'));
const report={schema:'g2-diffusion-fgm-experiment/v1',source_commit:options['source-commit'],
  environment_sha256:options['environment-sha256'],mechanism_sha256:hash(mechanism),
  config_sha256:hash(resolve(here,'case.json')),integration_sha256:hash(integration),integration_config:integration,
  driver_sha256:hash(fileURLToPath(import.meta.url)),out,CFD_executed:false,scientific_acceptance:false,phases:[]};
if(options.plan){console.log(JSON.stringify({plan:true,...report},null,2));process.exit(0);}
if(!process.env.SLURM_JOB_ID)throw Error('Physical integration requires a FlamePilot Slurm allocation');
if(existsSync(out))throw Error('Use a new output directory');
mkdirSync(out);
report.job_id=process.env.SLURM_JOB_ID;
const save=()=>writeFileSync(resolve(out,'experiment.json'),JSON.stringify(report,null,2)+'\n');save();
function phase(name,seconds,arguments_) {
  const fd=openSync(resolve(out,`${name}.log`),'wx'),start=Date.now();
  const result=spawnSync('timeout',['--signal=TERM','--kill-after=15',String(seconds),options.python,...arguments_],
    {stdio:['ignore',fd,fd],env:process.env});closeSync(fd);
  report.phases.push({name,exit_code:result.status,signal:result.signal,error:result.error?.message,
    wall_s:(Date.now()-start)/1000,log_sha256:hash(resolve(out,`${name}.log`))});save();
  if(result.status!==0)throw Error(`${name} failed (${result.status}); actual logs/outputs retained`);
}
const common=['--config',resolve(here,'case.json'),'--mechanism',mechanism,
  '--mechanism-sha256',report.mechanism_sha256,'--source-commit',options['source-commit'],
  '--environment-sha256',options['environment-sha256']];
phase('physical-trajectory',1000,[resolve(driver,'unsteady.py'),...common,
  '--integration-config',integration,'--upstream-patch-receipt',resolve(runtime,'energy-patch.json'),
  '--upstream-cold-patch-receipt',resolve(runtime,'cold-patch.json'),'--out',resolve(out,'trajectory')]);
const original=resolve(out,'trajectory/family-manifest.json');
const manifest=JSON.parse(readFileSync(original));
manifest.branch_policy='post-peak-extinction/v1';
manifest.zeroEndpointPolicy='zero-progress-numerical-tail/v1';
manifest.selection_note='Physical post-peak extinction path; unchanged numerical-tail limits. Original manifest preserved.';
const selected=resolve(out,'trajectory/fgm-family-manifest.json');
writeFileSync(selected,JSON.stringify(manifest,null,2)+'\n');
report.original_family_manifest_sha256=hash(original);report.selected_manifest_sha256=hash(selected);save();
phase('table-export',400,[resolve(driver,'table.py'),'--manifest',selected,
  '--metadata',resolve(out,'trajectory/phase-metadata.json'),'--mechanism',mechanism,
  '--source-commit',options['source-commit'],'--out',resolve(out,'table')]);
report.status='table_exported_not_accepted';save();
console.log(JSON.stringify(report,null,2));
