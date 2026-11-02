// Complete retained short-log parity. No solver process or field mutation.
import {readFile,writeFile,mkdir,readdir,symlink,open} from 'node:fs/promises';
import {openSync,closeSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {scanSolverLog} from './reader.mjs';
import {conservationRecords} from './conservation.mjs';
import {parseSolverLog} from './operator/conservation/core.mjs';
import {writeJson} from './json.mjs';

const [configPath,action]=process.argv.slice(2),here=dirname(fileURLToPath(import.meta.url));
if(!configPath||![undefined,'--apply'].includes(action))throw Error('Use qualify.mjs CONFIG [--apply]');
const config=JSON.parse(await readFile(configPath)),hash=b=>createHash('sha256').update(b).digest('hex');
for(const name of ['referenceCase','originalPacket','originalDirectChecker','conservationManifest','output'])
 if(!config[name]?.startsWith('/workspace/'))throw Error(`Require workspace path:${name}`);
const out=resolve(config.output),reference=resolve(config.referenceCase);
if(config.sourceLogSha256!=='d5eac4dd3a06c280da0bfdea53a1122f476bcc2d635b57cf9785536d5fff0b7d')throw Error('Unexpected retained full-log identity');
if(!action){console.log(JSON.stringify({readOnly:true,...config,postprocessingOnly:true,solverExecution:false}));process.exit(0);}
if(!process.env.SLURM_JOB_ID)throw Error('Full-log regression belongs in an admitted allocation');
await mkdir(out);
const raw=await readFile(`${reference}/log.solver`);assert.equal(hash(raw),config.sourceLogSha256);
const scanned=await scanSolverLog(`${reference}/log.solver`);
assert.equal(scanned.identity.sha256,hash(raw));
assert.deepEqual(conservationRecords(scanned),parseSolverLog(raw.toString()));
const rawLines=raw.toString().split(/\r?\n/);
for(const name of Object.keys(scanned.groups))assert.deepEqual(scanned.lines(name),rawLines.filter(line=>line.startsWith(name+' ')));
const reports=['direct-g2-result.json','endpoint-qualification.json','density-consistency-result.json','projection-ledger-result.json'];
async function shadow(name,replaceLog=false){
 const target=`${out}/${name}`;await mkdir(target);
 for(const entry of await readdir(reference)){
  if(reports.includes(entry)||(replaceLog&&entry==='log.solver'))continue;
  await symlink(`${reference}/${entry}`,`${target}/${entry}`);
 }
 await writeFile(`${target}/POSTPROCESSING_ONLY.txt`,'Read-only source-field links; no CFD is executed or restarted here.\n',{flag:'wx'});
 return target;
}
async function run(name,script,args){
 const log=`${out}/${name}.log`,fd=openSync(log,'wx');let result;
 try{result=spawnSync(process.execPath,['--max-old-space-size=8192',script,...args],{stdio:['ignore',fd,fd],timeout:180000});}
 finally{closeSync(fd);}
 return {name,script,args,status:result.status,signal:result.signal,log};
}
const runs=[],paths={};
for(const mode of ['original','streamed']){
 const current=paths[mode]=await shadow(mode);
 const direct=mode==='original'?config.originalDirectChecker:`${here}/../direct-fgm/check.mjs`;
 const packet=mode==='original'?config.originalPacket:`${here}/operator`;
 const calls=[['direct',direct,[current,...(mode==='streamed'?['--stream-log']:[])]],
  ['endpoint',`${packet}/check-endpoint.mjs`,[current,'enabled','0']],
  ['density',`${packet}/check.mjs`,[current,'candidate','0']],
  ['projection',`${packet}/check-projection.mjs`,[current,'cold']],
  ['conservation',`${packet}/conservation/audit.mjs`,[config.conservationManifest,'--out',`${out}/${mode}-conservation`]]];
 for(const [name,script,args] of calls){
  const result=await run(mode+'-'+name,script,args);runs.push(result);
  if(result.status!==0){await writeJson(`${out}/failure.json`,{runs,failed:result,scientificAcceptance:false});throw Error(`Actual checker failed:${result.name}`);}
 }
}
const compared=[];
function canonical(value,current){
 const normalized=JSON.parse(JSON.stringify(value).replaceAll(current,reference));
 delete normalized.logInputIdentity;return normalized;
}
for(const file of reports){
 const original=JSON.parse(await readFile(`${paths.original}/${file}`)),streamed=JSON.parse(await readFile(`${paths.streamed}/${file}`));
 assert.deepEqual(canonical(original,paths.original),canonical(streamed,paths.streamed),file);
 compared.push({file,allMetricsAndVerdictsExactlyEqual:true});
}
const oldAudit=JSON.parse(await readFile(`${out}/original-conservation/report.json`));
const newAudit=JSON.parse(await readFile(`${out}/streamed-conservation/report.json`));
delete oldAudit.auditor;delete newAudit.auditor;delete newAudit.logInputIdentity;
assert.deepEqual(oldAudit,newAudit,'All conservation metrics, line mappings, verdicts and record values');
assert.equal(hash(await readFile(`${out}/original-conservation/steps.csv`)),hash(await readFile(`${out}/streamed-conservation/steps.csv`)));
compared.push({file:'conservation/report.json and steps.csv',allMetricsAndVerdictsExactlyEqual:true});
for(const mode of ['original','streamed']){
 const target=`${out}/${mode}-wrapper`;await mkdir(target);
 const packet=mode==='original'?config.originalPacket:`${here}/operator`;
 const result=await run(mode+'-audit-wrapper',`${packet}/audit-run.mjs`,
  [reference,'/workspace/build/z-projection-r1',target,`${packet}/conservation`]);
 runs.push(result);assert.equal(result.status,0,JSON.stringify(result));
}
const oldWrapped=JSON.parse(await readFile(`${out}/original-wrapper/conservation-full/report.json`));
const newWrapped=JSON.parse(await readFile(`${out}/streamed-wrapper/conservation-full/report.json`));
delete oldWrapped.auditor;delete newWrapped.auditor;delete newWrapped.logInputIdentity;
assert.deepEqual(oldWrapped,newWrapped,'Audit wrapper full scientific report');
const wrappedSummary=JSON.parse(await readFile(`${out}/streamed-wrapper/conservation-summary.json`));
assert.equal(wrappedSummary.perStepRecordsRetained,oldWrapped.steps.length);
assert.deepEqual(wrappedSummary.statistics,oldWrapped.statistics);
compared.push({file:'audit-run wrapper complete report and small summary',allMetricsAndVerdictsExactlyEqual:true});
const negative=await shadow('missing-energy-state',true);
await writeFile(`${negative}/log.solver`,rawLines.filter(line=>!line.startsWith('energyState ')).join('\n'),{flag:'wx'});
const refusal=await run('required-record-refusal',`${here}/../direct-fgm/check.mjs`,[negative,'--stream-log']);
assert.equal(refusal.status,2);
const refused=JSON.parse(await readFile(`${negative}/direct-g2-result.json`));
assert.equal(refused.mechanicalChecks.cleanTimeZero,false);assert.equal(refused.mechanicalChecks.finiteEnergyRecords,false);
const {sourceLineMappings,markerSourceLines,...identity}=scanned.identity;
const ratio=80,projection={basis:'Fresh8ms/retained100us ratio80; actual step growth can differ',
 records:identity.retainedRecords*ratio,recordBytes:identity.retainedRecordBytes*ratio,markerBytes:identity.markerBytes*ratio};
projection.fitsDeclaredBounds=projection.records<=identity.limits.records&&projection.recordBytes<=identity.limits.retainedBytes&&projection.markerBytes<=identity.limits.markerBytes;
await writeJson(`${out}/qualification.json`,{passed:true,postprocessingJobId:process.env.SLURM_JOB_ID,originalScienceJobId:'126435330',
 identity,compared,runs,requiredRecordRefusal:refusal,projection8ms:projection,scientificAcceptance:false,solverExecuted:false});
console.log(JSON.stringify({passed:true,compared:compared.length,identity,projection8ms:projection,solverExecuted:false,scientificAcceptance:false}));
