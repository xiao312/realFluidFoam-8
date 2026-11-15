import fs from 'node:fs';
import crypto from 'node:crypto';
const [root,variant,action]=process.argv.slice(2),apply=action==='--apply';
if(!root?.startsWith('/workspace/cases/g2-relaxed-long-s25-schmitt-')||!['defaultOff','tight'].includes(variant)||![undefined,'--apply'].includes(action))throw Error('Use owned fresh case defaultOff|tight [--apply]');
if(fs.readdirSync(root).some(n=>n.startsWith('processor')||(Number.isFinite(Number(n))&&Number(n)>0)))throw Error('Fresh undecomposed original-zero case required');
const factory=JSON.parse(fs.readFileSync(root+'/direct-g2-input.json','utf8'));if(factory.startTime!==0)throw Error('Original zero required');
const sha=x=>crypto.createHash('sha256').update(x).digest('hex'),changes=[];
if(variant==='tight'){
 const control=root+'/system/controlDict',solution=root+'/system/fvSolution';
 const beforeControl=fs.readFileSync(control,'utf8'),beforeSolution=fs.readFileSync(solution,'utf8');
 if(/\bwriteFgmSpeciesTransportAudit\s/.test(beforeControl)||!beforeSolution.includes('solvers {'))throw Error('Unexpected controls');
 changes.push({file:control,before:beforeControl,after:beforeControl+'\nwriteFgmSpeciesTransportAudit yes;\n'});
 changes.push({file:solution,before:beforeSolution,after:beforeSolution.replace('solvers {','solvers {\n Yi { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-12; relTol 0; }\n')});
}
const receipt={variant,CFDStartTime_s:0,auditEnabled:variant==='tight',YiLinearTolerance:variant==='tight'?1e-12:1e-8,otherTolerancesChanged:false,clippingOrAcceptanceChanged:false,scientificAcceptance:false,changes:changes.map(c=>({file:c.file,beforeSha256:sha(c.before),afterSha256:sha(c.after)}))};
if(apply){if(!process.env.SLURM_JOB_ID)throw Error('Slurm required');for(const c of changes)fs.writeFileSync(c.file,c.after);fs.writeFileSync(root+'/species-audit-input.json',JSON.stringify(receipt,null,2)+'\n',{flag:'wx'});}
console.log(JSON.stringify({readOnly:!apply,...receipt},null,2));
