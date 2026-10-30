import {readFile, writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
const [pairPath, executable, mode='--plan']=process.argv.slice(2);
if(!pairPath||!executable||!['--plan','--apply'].includes(mode))throw Error('Use audit-setup.mjs PAIRS PROBE [--plan|--apply]');
const root=resolve(pairPath),m=JSON.parse(await readFile(`${root}/manifest.json`));
if(m.schema!=='fgm-unused-diffusion-parity-v1')throw Error('Unexpected physical manifest');
const a=m.samples.find(s=>s.name==='oxygen'),b=m.samples.find(s=>s.name==='mixed-reacted');
const names=JSON.parse(await readFile(`${root}/oxygen-baseline/probe-input.json`)).state.y;
if(!a||!b||a.y.length!==53||b.y.length!==53||names.length!==53)throw Error('Expected physical53species states');
const thermo=await readFile(`${root}/oxygen-baseline/constant/thermophysicalProperties`,'utf8');
const speciesText=/\bspecies\s*\(([\s\S]*?)\)\s*;/.exec(thermo)?.[1];
const species=speciesText?[...speciesText.matchAll(/"([^"]+)"/g)].map(m=>m[1]):null;
if(species?.length!==53)throw Error('Cannot read ordered physical species');
const states=[a,b,a], dictionary=`FoamFile {version 2.0; format ascii; class dictionary; object mixtureSetupAudit;}\nspecies (${species.map(n=>JSON.stringify(n)).join(' ')});\npressures (${states.map(s=>s.pressure_Pa).join(' ')});\ntemperatures (${states.map(s=>s.temperature).join(' ')});\nmassFractions (${states.map(s=>'('+s.y.join(' ')+')').join('\n')});\n`;
if(mode==='--plan'){console.log(JSON.stringify({dryRun:true,states:states.map(s=>({name:s.name,p:s.pressure_Pa,T:s.temperature})),species}));process.exit(0);}
if(!process.env.SLURM_JOB_ID)throw Error('Compiled physical audit requires Slurm');
const runs={},failures=[];
function execute(args,path){const r=spawnSync(executable,args,{encoding:'utf8',maxBuffer:10*1024*1024});return {r,text:r.stdout+'\n'+r.stderr,path};}
for(const variant of ['baseline','optimized']){
 const path=`${root}/oxygen-${variant}`;
 await writeFile(`${path}/constant/mixtureSetupAudit`,dictionary,{flag:'wx'});
 const audit=execute(['-case',path,'-audit-mixture-setup'],path);
 await writeFile(`${path}/log.setup-audit`,audit.text,{flag:'wx'});
 if(audit.r.status!==0)throw Error(`${variant} concrete mixture audit failed: see log.setup-audit`);
 const raw=await readFile(`${path}/mixture-setup.csv`,'utf8'),[header,...lines]=raw.trim().split(/\r?\n/);
 const keys=header.split(','),rows=lines.map(l=>Object.fromEntries(l.split(',').map((v,i)=>[keys[i],Number(v)])));
 if(rows.length!==6||rows.some(r=>Object.values(r).some(v=>!Number.isFinite(v))))throw Error('Invalid concrete property rows');
 const negative=execute(['-case',path,'-read-raw-Dimix'],path);
 await writeFile(`${path}/log.raw-dimix`,negative.text,{flag:'wx'});
 const guarded=variant==='baseline'?negative.r.status===0:negative.r.status!==0&&/Raw Dimix requested without prepared mass-diffusion data/.test(negative.text);
 if(!guarded)failures.push(`${variant}: raw Dimix result did not match explicit policy`);
 runs[variant]={rows,rawExit:negative.r.status,rawSignal:negative.r.signal,rawGuardPassed:guarded,sha256:createHash('sha256').update(raw).digest('hex')};
}
const matrix=['TcmdRows','PcmdRows','MmdRows','sigmdRows'];
for(let i=0;i<6;i++)for(const key of Object.keys(runs.baseline.rows[i])){
 const a=runs.baseline.rows[i][key],b=runs.optimized.rows[i][key];
 if(matrix.includes(key)){if(a!==53||b!==0)failures.push(`${i}/${key}: matrix sizes ${a}/${b}`);}
 else if(a!==b)failures.push(`${i}/${key}: changed active property ${a}/${b}`);
}
for(const variant of ['baseline','optimized'])for(let location=0;location<2;location++)for(const key of Object.keys(runs[variant].rows[location])){
 if(key!=='state'&&runs[variant].rows[location][key]!==runs[variant].rows[4+location][key])failures.push(`${variant}/${location}/${key}: A changed after B`);
}
const result={passed:failures.length===0,failures,runs,comparison:'Exact numerical equality of active properties and X/Y; four omitted matrix row counts explicitly differ',scientificAcceptance:false};
await writeFile(`${root}/setup-audit-result.json`,JSON.stringify(result,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({passed:result.passed,failures,scientificAcceptance:false}));
if(!result.passed)process.exitCode=1;
