import {readFile,writeFile,readdir} from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
const [directory,endRaw,...flags]=process.argv.slice(2),end=Number(endRaw);
if(!directory||!Number.isFinite(end)||end<=0||flags.some(f=>!['--apply','--uniform','--muscl'].includes(f)))throw Error('Use FRESH_CONTACT_CASE END_TIME [--uniform] [--muscl] [--apply]');
const root=path.resolve(directory),uniform=flags.includes('--uniform'),apply=flags.includes('--apply'),listing=await readdir(root);
if(listing.includes('contact-double-flux.json')||listing.includes('initial-thermo.csv')||listing.some(n=>/^processor/.test(n)||(Number.isFinite(Number(n))&&Number(n)>0)))throw Error('Configure a new undecomposed contact before initialization');
const muscl=flags.includes('--muscl');
const changes=[];
async function change(name,transform){const file=path.join(root,name),before=await readFile(file,'utf8');changes.push({file,before,after:transform(before)});}
await change('system/controlDict',s=>{
 if(!/startFrom startTime;startTime 0;/.test(s)||!s.includes('application reactingFoamSolveZ;'))throw Error('Expected original time-zero contact controls');
 return s.replace('application reactingFoamSolveZ;','application realFluidContactDF;')
  .replace('endTime .02;',`endTime ${end};`)
  .replace('writeControl adjustableRunTime;writeInterval .005;',`writeControl adjustableRunTime;writeInterval ${Math.min(.005,end)};`)
  .replace('writeControl runTime;writeInterval .001;',`writeControl runTime;writeInterval ${Math.min(.001,end/5)};`)
  +`\ncontactDFInviscid yes;\nmaxAcousticCo .3;\ncontactDFReconstruction ${muscl?'limitedLinear':'firstOrder'};\n`;
});
if(uniform){
 await change('constant/contactInput',s=>s.replace('densityInversion yes;','densityInversion no;'));
 await change('0/T',s=>s.replace(/uniform\s+100\b/g,'uniform 150'));
 for(const [name,value]of [['O2',1],['H2',0]])await change(`0/${name}`,s=>s.replace(/internalField\s+(?:uniform\s+[^;]+|nonuniform\s+List<scalar>\s+\d+\s*\([\s\S]*?\))\s*;/,`internalField uniform ${value};`));
}
const sha=s=>createHash('sha256').update(s).digest('hex');
const receipt={schema:'contact-double-flux-input/v1',startTime_s:0,endTime_s:end,uniformQualification:uniform,algorithm:'HLLC-common-mass-momentum,cell-local-double-flux-energy,SSPRK3',reconstruction:muscl?'limitedLinear':'firstOrder',inviscid:true,acousticCo:.3,trueEOS:'executing SRK Chung mixture',energy:'absoluteHa,quasi-conservative defect explicitly measured',scientificAcceptance:false,acceptanceLimitsChanged:false,changes:changes.map(c=>({file:c.file,beforeSha256:sha(c.before),afterSha256:sha(c.after)}))};
if(!apply){console.log(JSON.stringify({readOnly:true,...receipt},null,2));process.exit(0);}
if(!process.env.SLURM_JOB_ID)throw Error('Allocated preparation required');
for(const c of changes)await writeFile(c.file,c.after);
await writeFile(`${root}/contact-double-flux.json`,JSON.stringify(receipt,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify(receipt));
